"""Agent 3 — Maintenance Intelligence & RCA (spec §5.3).

Graph-native root-cause reasoning: walks the equipment's full neighborhood
(work orders, inspections, incidents), builds a failure timeline, checks
sister equipment for cross-asset patterns (shared seal model / equipment type),
then has the strong model produce an evidence-ranked RCA. Every cause must
cite record ids that exist in the graph. Confirmed RCAs are written back to
the Fabric as org memory (HAS_FAILURE_MODE / CAUSED_BY / REMEDIED_BY edges).
"""
from __future__ import annotations

import json

from . import config, llm
from .graph import get_graph
from .ontology import Provenance

RCA_PROMPT = """You are a senior reliability engineer producing a Root Cause Analysis.

TARGET EQUIPMENT: {tag} ({etype}, service: {service}, installed {install})
SYMPTOM / QUESTION: {symptom}

FAILURE TIMELINE (chronological, from CMMS and inspection records):
{timeline}

CROSS-ASSET CONTEXT (sister equipment sharing design features):
{cross_asset}

INCIDENT HISTORY linked to this equipment:
{incidents}

Produce a structured RCA. Every cause MUST reference supporting record ids from
the data above (wo/inspection/incident ids). Rank causes by evidence strength
(frequency x recency x consistency). Use ISO-14224-style failure mode naming.

Return ONLY JSON:
{{
 "failure_mode": "<canonical failure mode>",
 "summary": "<3-4 sentence plain-language explanation of why this keeps happening>",
 "causes": [
   {{"cause": "...", "rank": 1, "evidence": ["WO-...", "INSP-..."],
     "mechanism": "<one sentence causal mechanism>"}}
 ],
 "cross_asset_pattern": {{"found": true/false,
   "detail": "<which sister equipment shows the same pattern, with record ids>",
   "recommendation": "<fleet-wide action if warranted>"}},
 "corrective_actions": ["..."],
 "preventive_actions": ["..."],
 "recurrence_risk": {{"level": "low|medium|high",
   "rationale": "<seasonality / unresolved causes>"}},
 "confidence": 0.0-1.0
}}"""


def failure_timeline(tag: str) -> list[dict]:
    kg = get_graph()
    nb = kg.neighborhood(tag, depth=1,
                         edge_types=["MAINTAINED_BY", "INSPECTED_BY", "INVOLVES"])
    events = []
    for n in nb["nodes"]:
        if not n:
            continue
        if n.get("type") == "WorkOrder":
            events.append({"date": n["date"], "id": n["wo_id"], "kind": n["wo_type"],
                           "what": n["title"], "detail": n["findings"][:400],
                           "downtime_h": n.get("downtime_h", 0)})
        elif n.get("type") == "Inspection":
            events.append({"date": n["date"], "id": n["id"].split(":")[0],
                           "kind": "inspection/" + n.get("result", ""),
                           "what": n.get("method", ""), "detail": n.get("text", "")[:300]})
        elif n.get("type") == "Incident":
            events.append({"date": n["date"], "id": n["incident_id"],
                           "kind": "incident/" + n.get("category", ""),
                           "what": n.get("title", ""),
                           "detail": n.get("narrative", "")[:300]})
    return sorted(events, key=lambda e: e["date"])


def sister_equipment(tag: str) -> list[dict]:
    kg = get_graph()
    me = kg.node(tag)
    if not me:
        return []
    sisters = []
    for eq in kg.nodes_by_type("Equipment"):
        if eq["id"] == tag:
            continue
        shared = []
        if me.get("seal_model") and eq.get("seal_model") == me.get("seal_model"):
            shared.append(f"seal model {me['seal_model']}")
        if eq.get("equipment_type") == me.get("equipment_type"):
            shared.append(f"type {me.get('equipment_type')}")
        if shared:
            cm_events = [e for e in failure_timeline(eq["id"])
                         if e["kind"] in ("CM", "breakdown")
                         or e["kind"].startswith("incident")]
            sisters.append({"tag": eq["id"], "shared": shared,
                            "failure_events": cm_events})
    return sisters


def run_rca(tag: str, symptom: str = "") -> dict:
    kg = get_graph()
    node = kg.node(tag)
    if not node:
        return {"error": f"unknown equipment {tag}"}
    timeline = failure_timeline(tag)
    sisters = sister_equipment(tag)
    incidents = [e for e in timeline if e["kind"].startswith("incident")]

    cross_lines = []
    for s in sisters:
        if s["failure_events"]:
            evs = "; ".join(f"{e['id']} ({e['date']}): {e['what']}"
                            for e in s["failure_events"][:5])
            cross_lines.append(f"{s['tag']} (shares {', '.join(s['shared'])}): {evs}")
        else:
            cross_lines.append(f"{s['tag']} (shares {', '.join(s['shared'])}): "
                               "no failure events on record — healthy contrast case")

    prompt = RCA_PROMPT.format(
        tag=tag, etype=node.get("equipment_type"), service=node.get("service"),
        install=node.get("install_date"),
        symptom=symptom or "recurring failures - explain the pattern",
        timeline="\n".join(f"- {e['date']} [{e['id']}] ({e['kind']}) {e['what']}: "
                           f"{e['detail']}" for e in timeline) or "(none)",
        cross_asset="\n".join(cross_lines) or "(none)",
        incidents="\n".join(f"- {e['date']} [{e['id']}] {e['what']}: {e['detail']}"
                            for e in incidents) or "(none)")
    rca = llm.complete_json(prompt, model=config.MODEL_STRONG)
    rca["equipment"] = tag
    rca["timeline"] = timeline
    rca["sisters"] = [{"tag": s["tag"], "shared": s["shared"],
                       "n_failures": len(s["failure_events"])} for s in sisters]
    return rca


def confirm_rca(rca: dict) -> None:
    """Write a confirmed RCA back into the Fabric (org memory, spec §4)."""
    kg = get_graph()
    tag = rca["equipment"]
    prov = Provenance(source_doc_id=f"rca:{tag}", extractor="rca_agent",
                      confidence=float(rca.get("confidence", 0.7)))
    fm_id = f"FM:{rca['failure_mode'].lower().replace(' ', '_')[:60]}"
    kg.add_node(fm_id, "FailureMode", prov, name=rca["failure_mode"])
    kg.add_edge(tag, fm_id, "HAS_FAILURE_MODE", prov)
    for cause in rca.get("causes", []):
        for rec in cause.get("evidence", []):
            if kg.node(rec + ":rec"):
                kg.add_edge(fm_id, rec + ":rec", "CAUSED_BY", prov,
                            cause=cause["cause"])
    kg.save()
