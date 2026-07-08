"""Agent 5 — Lessons-Learned & Failure Intelligence (spec §5.5).

Hindsight -> foresight loop:
1. cluster incidents by semantic similarity of narrative+precursors, write
   learned SIMILAR_TO edges into the Fabric;
2. mine a precursor signature for each recurring cluster;
3. proactively match upcoming work (permits dated today/future) and current
   context (season) against those signatures — pushing warnings with the
   historical evidence attached BEFORE the work happens.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np

from . import config, llm, stores
from .graph import get_graph
from .ontology import Provenance

SIM_THRESHOLD = 0.72

SIGNATURE_PROMPT = """These plant incidents/near-misses cluster together:

{events}

Return ONLY JSON:
{{
 "pattern_name": "<short name>",
 "systemic_pattern": "<2-3 sentences: the organisational/technical pattern>",
 "precursor_signature": ["<condition 1>", "<condition 2>", ...],
 "prevention": "<the single highest-leverage prevention>",
 "severity": "low|medium|high",
 "preventability": "low|medium|high"
}}"""

MATCH_PROMPT = """You are a proactive safety monitor. Decide whether the planned work
below re-assembles the precursor signature of a known incident pattern.

PLANNED WORK:
{work}

CURRENT CONTEXT: date {today} (month {month} — {season} season in coastal Maharashtra).

KNOWN PATTERN: {pattern_name}
Precursor signature: {signature}
Historical events: {history}

Return ONLY JSON:
{{"match": true/false, "matched_conditions": ["..."],
  "missing_conditions": ["..."],
  "warning": "<if match: 2-3 sentence field-ready warning naming the historical
              events and the specific condition to fix>",
  "recommended_action": "<concrete action>", "urgency": "low|medium|high"}}"""


def _incidents() -> list[dict]:
    return [n for n in get_graph().nodes_by_type("Incident")]


def build_patterns(force: bool = False) -> dict:
    """Cluster incidents, write SIMILAR_TO edges, mine precursor signatures."""
    cache = config.DATA_DIR / "patterns.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text())
    incs = _incidents()
    texts = [f"{n.get('category','')} at {n.get('area','')} {n.get('equipment','')}: "
             f"{n.get('narrative','')} Precursors: {n.get('precursors','')}"
             for n in incs]
    vecs = np.array([v for v in stores.dense_model().embed(texts)])
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    sim = vecs @ vecs.T

    kg = get_graph()
    # greedy clustering on the similarity graph
    n = len(incs)
    assigned = [-1] * n
    clusters: list[list[int]] = []
    for i in range(n):
        if assigned[i] >= 0:
            continue
        cluster = [i]
        assigned[i] = len(clusters)
        for j in range(i + 1, n):
            if assigned[j] < 0 and sim[i, j] >= SIM_THRESHOLD:
                cluster.append(j)
                assigned[j] = len(clusters)
                prov = Provenance(source_doc_id="lessons_agent",
                                  extractor="similarity_clustering",
                                  confidence=float(sim[i, j]))
                kg.add_edge(incs[i]["incident_id"] + ":rec",
                            incs[j]["incident_id"] + ":rec", "SIMILAR_TO", prov,
                            similarity=float(round(sim[i, j], 3)))
        clusters.append(cluster)
    kg.save()

    patterns = []
    for ci, cluster in enumerate(clusters):
        members = [incs[i] for i in cluster]
        if len(members) < 2:
            continue  # a pattern needs recurrence
        events_text = "\n".join(
            f"- {m['incident_id']} ({m['date']}, {m['area']}, {m['equipment']}): "
            f"{m['title']}. {m['narrative'][:280]} Precursors: {m['precursors']}"
            for m in members)
        sig = llm.complete_json(SIGNATURE_PROMPT.format(events=events_text),
                                model=config.MODEL_STRONG)
        sig["members"] = [m["incident_id"] for m in members]
        sig["dates"] = [m["date"] for m in members]
        patterns.append(sig)
    result = {"patterns": patterns,
              "n_incidents": n,
              "singletons": [incs[c[0]]["incident_id"] for c in clusters
                             if len(c) == 1]}
    cache.write_text(json.dumps(result, indent=1))
    return result


def _season(month: int) -> str:
    return "monsoon" if 6 <= month <= 9 else "dry"


def evaluate_upcoming(today: dt.date | None = None) -> list[dict]:
    """Match scheduled/future work against precursor signatures -> warnings."""
    today = today or dt.date.today()
    kg = get_graph()
    patterns = build_patterns().get("patterns", [])
    warnings = []
    upcoming = []
    for d in kg.nodes_by_type("Document"):
        if d.get("doc_type") == "permit" and d.get("date"):
            pdate = dt.date.fromisoformat(d["date"])
            if pdate >= today:
                upcoming.append(d)
    for work in upcoming:
        work_desc = (f"Permit {work['id']} ({work.get('ptype')}) dated {work.get('date')} "
                     f"on {work.get('equipment')} in {work.get('area')}: "
                     f"{work.get('text','')}")
        for pat in patterns:
            try:
                m = llm.complete_json(MATCH_PROMPT.format(
                    work=work_desc, today=today.isoformat(), month=today.month,
                    season=_season(today.month),
                    pattern_name=pat["pattern_name"],
                    signature="; ".join(pat["precursor_signature"]),
                    history=", ".join(f"{i} ({d})" for i, d in
                                      zip(pat["members"], pat["dates"]))),
                    model=config.MODEL_STRONG)
            except Exception:
                continue
            if m.get("match"):
                warnings.append({
                    "permit": work["id"], "date": work.get("date"),
                    "equipment": work.get("equipment"), "area": work.get("area"),
                    "pattern": pat["pattern_name"],
                    "historical_events": pat["members"],
                    "matched_conditions": m.get("matched_conditions", []),
                    "warning": m.get("warning", ""),
                    "recommended_action": m.get("recommended_action", ""),
                    "urgency": m.get("urgency", "medium"),
                })
    (config.DATA_DIR / "warnings.json").write_text(json.dumps(warnings, indent=1))
    return warnings


def prevention_priorities() -> list[dict]:
    pats = build_patterns().get("patterns", [])
    score = {"low": 1, "medium": 2, "high": 3}
    ranked = sorted(pats, key=lambda p: (score.get(p.get("severity"), 1)
                                         * len(p.get("members", []))
                                         * score.get(p.get("preventability"), 1)),
                    reverse=True)
    return [{"pattern": p["pattern_name"], "events": p["members"],
             "severity": p.get("severity"), "preventability": p.get("preventability"),
             "prevention": p.get("prevention"),
             "systemic_pattern": p.get("systemic_pattern")} for p in ranked]
