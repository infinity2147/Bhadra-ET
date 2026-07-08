"""Agent 4 — Quality & Regulatory Compliance Intelligence (spec §5.4).

Requirement-to-reality mapping: every RegulatoryClause node is linked by
GOVERNED_BY edges to the equipment/areas it constrains. For each clause the
agent gathers the actual records (work orders, inspections, permits, emails)
touching those targets, then evaluates satisfaction with citations. Missing
evidence IS the gap. Output: a live gap register + one-click audit evidence
package.
"""
from __future__ import annotations

import datetime as dt
import json

from . import config, llm
from .graph import get_graph

EVAL_PROMPT = """You are a plant compliance auditor. Evaluate whether Refinery Unit 4
satisfies this regulatory requirement TODAY ({today}), based only on the evidence.

REQUIREMENT [{clause_id}] {standard} {clause} - {title}:
"{requirement}"
Governs: {targets}
{note}

EVIDENCE ON FILE (plant records touching the governed items):
{evidence}

Judgment rules:
- "satisfied": current, dated records demonstrate compliance.
- "partial": some evidence but incomplete, stale, or covers only some targets.
- "gap": evidence shows non-compliance, an overdue interval, or NO evidence exists
  (missing evidence is itself a gap).
- If plant records assume a different interval than the requirement states, flag
  the conflict explicitly - that is a finding, not a reason to pass.
- Compute date arithmetic carefully against today's date.

Return ONLY JSON:
{{"status": "satisfied|partial|gap",
  "severity": "low|medium|high",
  "reasoning": "<3-5 sentences with specific dates and record ids>",
  "evidence_ids": ["<record ids that support the judgment>"],
  "gap_detail": "<if not satisfied: exactly what is missing/overdue>",
  "recommended_action": "<concrete next step with a deadline>"}}"""


def _records_for_targets(targets: list[str]) -> list[dict]:
    kg = get_graph()
    out, seen = [], set()
    for t in targets:
        nb = kg.neighborhood(t, depth=1)
        for n in nb["nodes"]:
            if not n or n["id"] in seen:
                continue
            seen.add(n["id"])
            if n.get("type") == "WorkOrder":
                out.append({"id": n.get("wo_id", n["id"]), "date": n.get("date"),
                            "text": f"WO {n.get('wo_id', n['id'])} ({n.get('wo_type','')}) on "
                                    f"{n.get('equipment','')}: {n.get('title','')}. "
                                    f"{(n.get('findings') or '')[:300]}"})
            elif n.get("type") == "Inspection":
                out.append({"id": n["id"].split(":")[0], "date": n.get("date"),
                            "text": f"Inspection of {n.get('equipment','')} on {n.get('date','?')} "
                                    f"({n.get('method','')}, {n.get('result','')}): "
                                    f"{(n.get('text') or '')[:300]}"})
            elif n.get("type") == "Document" and n.get("doc_type") in ("permit", "email"):
                out.append({"id": n["id"], "date": n.get("date") or n.get("effective_date"),
                            "text": f"{n.get('doc_type')} {n['id']}: "
                                    f"{(n.get('text') or n.get('subject') or '')[:300]}"})
    return sorted(out, key=lambda r: str(r.get("date") or ""), reverse=True)


def build_register(force: bool = False) -> list[dict]:
    cache = config.DATA_DIR / "compliance_register.json"
    if cache.exists() and not force:
        return json.loads(cache.read_text())
    kg = get_graph()
    today = dt.date.today().isoformat()
    register = []
    for clause in kg.nodes_by_type("RegulatoryClause"):
        if not clause.get("requirement") or not clause.get("standard"):
            continue  # bare mention extracted from email/text — not evaluatable
        clause_doc = clause["id"].split(":")[0]
        targets = [e["src"] for e in kg.edges_of(clause["id"], "GOVERNED_BY", "in")]
        records = _records_for_targets(targets)
        ev_text = "\n".join(f"- [{r['id']}] ({r['date']}): {r['text']}"
                            for r in records[:20]) or "(NO RECORDS FOUND)"
        try:
            verdict = llm.complete_json(EVAL_PROMPT.format(
                today=today, clause_id=clause_doc, standard=clause["standard"],
                clause=clause["clause"], title=clause["title"],
                requirement=clause["requirement"],
                targets=", ".join(targets) or "(none mapped)",
                note=f"Context note: {clause['note']}" if clause.get("note") else "",
                evidence=ev_text), model=config.MODEL_STRONG)
        except Exception as exc:
            verdict = {"status": "partial", "severity": "low",
                       "reasoning": f"evaluation error: {exc}", "evidence_ids": [],
                       "gap_detail": "", "recommended_action": "re-run evaluation"}
        register.append({
            "clause_id": clause_doc, "standard": clause["standard"],
            "clause": clause["clause"], "title": clause["title"],
            "requirement": clause["requirement"], "verbatim": clause.get("verbatim"),
            "source_url": clause.get("source_url"),
            "source_tier": clause.get("source_tier"),
            "targets": targets, **verdict,
            "evaluated_on": today,
        })
    order = {"gap": 0, "partial": 1, "satisfied": 2}
    sev = {"high": 0, "medium": 1, "low": 2}
    register.sort(key=lambda r: (order.get(r["status"], 3),
                                 sev.get(r["severity"], 3)))
    cache.write_text(json.dumps(register, indent=1))
    return register


def audit_package(scope: str = "") -> dict:
    """Clause-by-clause evidence pack, optionally filtered by area/standard text."""
    register = build_register()
    scope_l = scope.lower()
    rows = [r for r in register
            if not scope or scope_l in r["standard"].lower()
            or any(scope_l in t.lower() for t in r["targets"])
            or scope_l in " ".join(r["targets"]).lower()]
    kg = get_graph()
    package = {"scope": scope or "all", "generated": dt.datetime.now().isoformat(),
               "plant": "Bharat Petrochem Ltd - Refinery Unit 4",
               "summary": {"total": len(rows),
                           "gaps": sum(1 for r in rows if r["status"] == "gap"),
                           "partial": sum(1 for r in rows if r["status"] == "partial"),
                           "satisfied": sum(1 for r in rows if r["status"] == "satisfied")},
               "clauses": rows}
    (config.DATA_DIR / "audit_package.json").write_text(json.dumps(package, indent=1))
    return package
