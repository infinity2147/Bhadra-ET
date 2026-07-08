"""Runtime intake — the 'used for years' path (spec §5.1, made continuous).

The batch corpus build (`ingest.py`) maps fixed `corpus/*.json` files to typed
`:rec` nodes at install time. That is not how a customer runs it: they file new
work orders, inspections, SOPs, incident reports and permits *every day*. This
module makes that same typed-node creation available at runtime, two ways:

  1. ingest_document(filename, text, pages) — drop in ANY document. One strong-
     model call BOTH classifies it (WO | inspection | SOP | incident | permit |
     OEM manual | email | regulatory | equipment | generic) AND extracts the
     type-appropriate structured fields. It is then materialised into the SAME
     `:rec` graph nodes + edges the corpus mappers create — so it appears in the
     failure timeline, is eligible for precursor/warning matching, and is
     evaluated by compliance. No "upload a PDF and hope the generic extractor
     guesses."

  2. ingest_table(rows, rec_type) — the real CMMS-export path. A CSV/JSON export
     of thousands of work orders / inspections maps column→field directly (fuzzy
     header matching), NO per-row LLM call. This is how years of history load.

Both paths reuse one set of materialisers, so a runtime record is
indistinguishable from a build-time one downstream.
"""
from __future__ import annotations

import csv
import io
import json
import re

from . import config, llm, stores
from .graph import KnowledgeGraph, get_graph
from .ingest import _next_chunk_id, link_tags, normalize_tag, tags_in
from .ontology import Provenance

# ---------------------------------------------------------------- classify + extract (one call)
CLASSIFY_EXTRACT_PROMPT = """You are the intake engine of an industrial plant knowledge
graph. Read the document and do BOTH: (1) classify it, (2) extract its structured fields.

Choose exactly one doc_type:
- "work_order"  : maintenance job / repair / PM/CM record (CMMS work order)
- "inspection"  : inspection / test report (thickness, vibration, NDT, PSV test…)
- "incident"    : incident, near-miss, accident, safety event
- "permit"      : permit to work (confined space, hot work, height…)
- "sop"         : standard operating procedure / method statement (has steps)
- "oem_manual"  : OEM / vendor equipment manual or datasheet
- "regulatory"  : a regulation / standard clause (OISD, Factories Act, PESO…)
- "equipment"   : an asset register / equipment list / nameplate data
- "email"       : correspondence / memo
- "generic"     : none of the above

Known equipment tags in this plant (reuse EXACTLY if referenced): {known_tags}

Extract the fields that fit the chosen type (omit unknown fields; ISO dates YYYY-MM-DD):
- work_order : {{id, equipment, date, wo_type(PM|CM|breakdown), title, findings, parts, downtime_h(number), closed_by}}
- inspection : {{id, equipment, date, method, result(pass|fail|advisory|…), text}}
- incident   : {{id, date, area, equipment, category, title, narrative, root_cause, precursors, actions}}
- permit     : {{id, ptype, equipment, area, date, text}}
- sop        : {{id, rev(number), date, title, steps(list of strings), hazards}}
- equipment  : {{tag, equipment_type, service, manufacturer, model, install_date, area, criticality, seal_model}}
- others     : leave record empty; content is indexed as-is.

Return ONLY JSON:
{{"doc_type":"...", "record":{{...}}, "equipment_tags":["P-101",...],
  "confidence":0.0-1.0, "summary":"<one line: what this adds>"}}

DOCUMENT ({doc_id}):
---
{text}
---"""


def classify_and_extract(doc_id: str, text: str, known_tags: list[str]) -> dict:
    prompt = CLASSIFY_EXTRACT_PROMPT.format(
        known_tags=", ".join(sorted(known_tags)) or "(none yet)",
        doc_id=doc_id, text=text[:6000])
    res = llm.complete_json(prompt, model=config.MODEL_STRONG)
    res.setdefault("doc_type", "generic")
    res.setdefault("record", {})
    res.setdefault("equipment_tags", [])
    res.setdefault("summary", "")
    return res


# ---------------------------------------------------------------- helpers
def _ensure_equipment(kg: KnowledgeGraph, tag: str, prov: Provenance,
                      new_equipment: list) -> str | None:
    """Never orphan a record: if it names an unknown asset, create a stub so the
    record links and shows up. Real plants add assets over time."""
    tag = normalize_tag(tag or "")
    if not tag:
        return None
    if not kg.node(tag):
        kg.add_node(tag, "Equipment", prov, area="Unassigned", criticality="medium")
        if not kg.node("Unassigned"):
            kg.add_node("Unassigned", "Area", prov, name="Unassigned")
        kg.add_edge(tag, "Unassigned", "LOCATED_IN", prov)
        new_equipment.append(tag)
    return tag


def _gen_id(prefix: str, doc_id: str, rec: dict) -> str:
    rid = str(rec.get("id") or rec.get("tag") or "").strip()
    if rid:
        return normalize_tag(rid) if re.fullmatch(r"[A-Za-z]{1,4}-\d{3,4}", rid) else rid
    stem = re.sub(r"[^A-Za-z0-9]+", "-", doc_id).strip("-")[:24] or "REC"
    return f"{prefix}-{stem}"


# ---------------------------------------------------------------- materialisers
# Each returns a dict summary; each mirrors the corresponding corpus mapper in
# ingest.py EXACTLY (node ids, :rec suffix, edge types/directions) so downstream
# (rca.failure_timeline, lessons, compliance) treats it as first-class.

def add_work_order(kg, rec, prov, chunks, new_equipment) -> dict:
    doc_id = _gen_id("WO", prov.source_doc_id, rec)
    eq = _ensure_equipment(kg, rec.get("equipment", ""), prov, new_equipment)
    kg.add_node(doc_id, "Document", prov, doc_type="WO", title=rec.get("title", ""),
                effective_date=rec.get("date"))
    kg.add_node(doc_id + ":rec", "WorkOrder", prov, wo_id=doc_id, equipment=eq,
                date=rec.get("date", ""), wo_type=rec.get("wo_type", "CM"),
                title=rec.get("title", ""), findings=rec.get("findings", ""),
                parts=rec.get("parts", ""), downtime_h=rec.get("downtime_h", 0) or 0)
    if eq:
        kg.add_edge(eq, doc_id + ":rec", "MAINTAINED_BY", prov)
        kg.add_edge(eq, doc_id, "DESCRIBED_BY", prov)
    closer = (rec.get("closed_by") or "").strip()      # batch links closer -> AUTHORED_BY
    if closer and kg.node(closer):
        kg.add_edge(doc_id, closer, "AUTHORED_BY", prov)
    link_tags(kg, doc_id, rec.get("findings", ""), prov)   # mirror batch tag-linking
    text = (f"Work order {doc_id} ({rec.get('wo_type','CM')}) on {eq} dated "
            f"{rec.get('date','')}: {rec.get('title','')}. Findings: "
            f"{rec.get('findings','')} Parts: {rec.get('parts','')}. "
            f"Downtime {rec.get('downtime_h',0)} h.")
    chunks.append(_chunk(doc_id, "WO", text, eq))
    return {"type": "WorkOrder", "id": doc_id, "equipment": eq, "in_timeline": bool(eq)}


def add_inspection(kg, rec, prov, chunks, new_equipment) -> dict:
    doc_id = _gen_id("INSP", prov.source_doc_id, rec)
    eq = _ensure_equipment(kg, rec.get("equipment", ""), prov, new_equipment)
    kg.add_node(doc_id, "Document", prov, doc_type="inspection",
                effective_date=rec.get("date"))
    kg.add_node(doc_id + ":rec", "Inspection", prov, equipment=eq,
                date=rec.get("date", ""), method=rec.get("method", ""),
                result=rec.get("result", ""), text=rec.get("text", ""))
    if eq:
        kg.add_edge(eq, doc_id + ":rec", "INSPECTED_BY", prov)
        kg.add_edge(eq, doc_id, "DESCRIBED_BY", prov)
    text = (f"Inspection {doc_id} of {eq} on {rec.get('date','')} "
            f"({rec.get('method','')}), result {rec.get('result','')}: {rec.get('text','')}")
    chunks.append(_chunk(doc_id, "inspection", text, eq))
    return {"type": "Inspection", "id": doc_id, "equipment": eq, "in_timeline": bool(eq)}


def add_incident(kg, rec, prov, chunks, new_equipment) -> dict:
    doc_id = _gen_id("INC", prov.source_doc_id, rec)
    eq = _ensure_equipment(kg, rec.get("equipment", ""), prov, new_equipment)
    area = (rec.get("area") or "").strip()
    kg.add_node(doc_id, "Document", prov, doc_type="incident", title=rec.get("title", ""),
                effective_date=rec.get("date"))
    kg.add_node(doc_id + ":rec", "Incident", prov, incident_id=doc_id,
                date=rec.get("date", ""), area=area, equipment=eq,
                category=rec.get("category", "incident"), title=rec.get("title", ""),
                narrative=rec.get("narrative", ""), root_cause=rec.get("root_cause", ""),
                precursors=rec.get("precursors", ""), actions=rec.get("actions", ""))
    if eq:
        kg.add_edge(doc_id + ":rec", eq, "INVOLVES", prov)
        kg.add_edge(eq, doc_id, "DESCRIBED_BY", prov)
    if area:
        if not kg.node(area):
            kg.add_node(area, "Area", prov, name=area)
        kg.add_edge(doc_id + ":rec", area, "INVOLVES", prov)
    link_tags(kg, doc_id, f"{rec.get('narrative','')} {rec.get('precursors','')}", prov)
    text = (f"{rec.get('category','incident')} {doc_id} on {rec.get('date','')} at "
            f"{area} ({eq}): {rec.get('title','')}. {rec.get('narrative','')} "
            f"Root cause: {rec.get('root_cause','')} Precursor conditions: "
            f"{rec.get('precursors','')}. Actions: {rec.get('actions','')}")
    chunks.append(_chunk(doc_id, "incident", text, eq))
    return {"type": "Incident", "id": doc_id, "equipment": eq,
            "in_timeline": bool(eq), "feeds_warnings": bool(rec.get("precursors"))}


def add_permit(kg, rec, prov, chunks, new_equipment) -> dict:
    doc_id = _gen_id("PTW", prov.source_doc_id, rec)
    eq = _ensure_equipment(kg, rec.get("equipment", ""), prov, new_equipment)
    area = (rec.get("area") or "").strip()
    kg.add_node(doc_id, "Document", prov, doc_type="permit", ptype=rec.get("ptype", ""),
                equipment=eq, area=area, date=rec.get("date", ""), text=rec.get("text", ""))
    if eq:
        kg.add_edge(doc_id, eq, "INVOLVES", prov)
    text = (f"Permit to work {doc_id} ({rec.get('ptype','')}) dated {rec.get('date','')} "
            f"for {eq} in {area}: {rec.get('text','')}")
    chunks.append(_chunk(doc_id, "permit", text, eq))
    # a future-dated permit is what the proactive monitor scans
    return {"type": "Permit", "id": doc_id, "equipment": eq, "feeds_warnings": True}


def add_sop(kg, rec, prov, chunks, new_equipment) -> dict:
    sid = str(rec.get("id") or _gen_id("SOP", prov.source_doc_id, rec))
    rev = int(rec.get("rev") or 1)
    # supersede the latest existing rev of the same SOP id
    prev = None
    best = -1
    for d in kg.nodes_by_type("Document"):
        if d.get("sop_id") == sid and int(d.get("rev", 0)) > best:
            best, prev = int(d.get("rev", 0)), d["id"]
    doc_id = f"{sid}_rev{rev}"
    steps = rec.get("steps") or []
    if isinstance(steps, str):
        steps = [s.strip() for s in re.split(r"\n|\d+\.", steps) if s.strip()]
    kg.add_node(doc_id, "Document", prov, doc_type="SOP", title=rec.get("title", ""),
                rev=rev, sop_id=sid, effective_date=rec.get("date"), superseded=False)
    kg.add_node(doc_id + ":proc", "Procedure", prov, sop_id=sid, rev=rev,
                title=rec.get("title", ""), steps=steps, hazards=rec.get("hazards", ""),
                effective_date=rec.get("date"))
    if prev:
        kg.add_edge(doc_id, prev, "SUPERSEDES", prov)
        pn = kg.node(prev)
        if pn:
            pn["superseded"] = True
    text = (f"{sid} rev {rev} (effective {rec.get('date','')}, CURRENT): "
            f"{rec.get('title','')}. Steps: " + " ".join(steps)
            + f" Hazards: {rec.get('hazards','')}")
    chunks.append(_chunk(doc_id, "SOP", text, None))
    for t in tags_in(text):
        if kg.node(t):
            kg.add_edge(t, doc_id, "DESCRIBED_BY", prov)
    return {"type": "Procedure(SOP)", "id": doc_id, "rev": rev,
            "supersedes": prev, "in_search": True}


def add_equipment_rec(kg, rec, prov, chunks, new_equipment) -> dict:
    tag = normalize_tag(str(rec.get("tag") or rec.get("id") or ""))
    if not tag:
        return {"type": "Equipment", "error": "no tag"}
    exists = kg.node(tag) is not None
    area = (rec.get("area") or "Unassigned").strip()
    props = {k: rec[k] for k in ("equipment_type", "service", "manufacturer", "model",
                                 "install_date", "criticality", "seal_model")
             if rec.get(k)}
    props.setdefault("criticality", "medium")
    kg.add_node(tag, "Equipment", prov, area=area, **props)
    if not kg.node(area):
        kg.add_node(area, "Area", prov, name=area)
    kg.add_edge(tag, area, "LOCATED_IN", prov)
    if not exists:
        new_equipment.append(tag)
    text = (f"Equipment {tag} ({props.get('equipment_type','')}) — {props.get('service','')}. "
            f"Area {area}. Manufacturer {props.get('manufacturer','')} "
            f"model {props.get('model','')}. Criticality {props.get('criticality')}.")
    chunks.append(_chunk(tag, "equipment", text, tag))
    return {"type": "Equipment", "id": tag, "new": not exists, "in_assets": True}


def _chunk(doc_id, doc_type, text, eq) -> dict:
    return {"id": _next_chunk_id(), "text": text[:4000], "doc_id": doc_id,
            "doc_type": doc_type, "page": 1,
            "entity_tags": tags_in(text) or ([eq] if eq else [])}


_MATERIALISERS = {
    "work_order": add_work_order, "inspection": add_inspection,
    "incident": add_incident, "permit": add_permit, "sop": add_sop,
    "equipment": add_equipment_rec,
}


# ---------------------------------------------------------------- document intake
def ingest_document(doc_id: str, text: str, pages: list[dict] | None = None) -> dict:
    """Classify a single document and materialise it as typed graph records.
    Returns a report the UI can show ('detected: Work Order → WO-… now in timeline')."""
    kg = get_graph()
    known = [n["id"] for n in kg.nodes_by_type("Equipment")]
    cx = classify_and_extract(doc_id, text, known)
    dtype = cx["doc_type"]
    prov = Provenance(source_doc_id=doc_id, extractor="intake_classifier",
                      confidence=float(cx.get("confidence", 0.7)),
                      effective_date=cx.get("record", {}).get("date"))
    chunks: list[dict] = []
    new_equipment: list[str] = []
    created: list[dict] = []

    mat = _MATERIALISERS.get(dtype)
    if mat and cx.get("record"):
        created.append(mat(kg, cx["record"], prov, chunks, new_equipment))
    else:
        # unstructured long tail (email/manual/regulatory/generic): keep the
        # document, index its text, link any known tags it mentions.
        kg.add_node(doc_id, "Document", prov, doc_type=dtype)
        chunks.append(_chunk(doc_id, dtype, text[:4000], None))
        for t in tags_in(text):
            if kg.node(t):
                kg.add_edge(t, doc_id, "DESCRIBED_BY", prov)
        created.append({"type": dtype, "id": doc_id, "in_search": True})

    # link any additionally referenced known tags
    for t in cx.get("equipment_tags", []):
        t = normalize_tag(t)
        if kg.node(t) and kg.node(doc_id):
            kg.add_edge(t, doc_id, "DESCRIBED_BY", prov)
    kg.save()
    if chunks:
        stores.upsert_text_chunks(chunks)
    return {"doc_id": doc_id, "detected_type": dtype,
            "confidence": cx.get("confidence"), "summary": cx.get("summary", ""),
            "created": created, "new_equipment": new_equipment,
            "text_chunks": len(chunks)}


# ---------------------------------------------------------------- bulk table intake
# fuzzy header → schema field (the realistic SAP-PM / Maximo export path)
_COLUMN_ALIASES = {
    "work_order": {
        "id": ["id", "wo", "wo_id", "wo_no", "wo_number", "order", "order_no", "work_order"],
        "equipment": ["equipment", "tag", "asset", "asset_no", "functional_location", "floc"],
        "date": ["date", "wo_date", "created", "created_on", "completion_date", "actual_finish"],
        "wo_type": ["wo_type", "type", "order_type", "maintenance_type", "activity_type"],
        "title": ["title", "description", "short_text", "summary", "subject"],
        "findings": ["findings", "notes", "remarks", "long_text", "work_done", "resolution"],
        "parts": ["parts", "materials", "components", "spare_parts"],
        "downtime_h": ["downtime_h", "downtime", "downtime_hours", "outage_h", "hours"],
        "closed_by": ["closed_by", "technician", "performed_by", "assignee"],
    },
    "inspection": {
        "id": ["id", "insp", "inspection_id", "insp_no", "report_no", "cert_no"],
        "equipment": ["equipment", "tag", "asset", "asset_no", "functional_location"],
        "date": ["date", "insp_date", "inspection_date", "test_date"],
        "method": ["method", "technique", "type", "inspection_type", "ndt_method"],
        "result": ["result", "outcome", "status", "verdict", "pass_fail"],
        "text": ["text", "findings", "remarks", "observations", "notes", "comments"],
    },
    "incident": {
        "id": ["id", "incident_id", "inc_no", "event_id", "report_no", "nm_no"],
        "date": ["date", "incident_date", "event_date", "occurred_on"],
        "area": ["area", "location", "unit", "zone"],
        "equipment": ["equipment", "tag", "asset", "asset_no"],
        "category": ["category", "type", "incident_type", "classification"],
        "title": ["title", "description", "summary", "subject", "short_text"],
        "narrative": ["narrative", "details", "description_long", "what_happened", "sequence"],
        "root_cause": ["root_cause", "cause", "rca", "root_cause_analysis"],
        "precursors": ["precursors", "contributing_factors", "conditions", "precursor"],
        "actions": ["actions", "corrective_actions", "capa", "recommendations", "follow_up"],
    },
    "permit": {
        "id": ["id", "permit_id", "ptw", "ptw_no", "permit_no"],
        "ptype": ["ptype", "type", "permit_type", "work_type"],
        "equipment": ["equipment", "tag", "asset"],
        "area": ["area", "location", "unit"],
        "date": ["date", "permit_date", "issue_date", "valid_from"],
        "text": ["text", "description", "scope", "work_description", "remarks"],
    },
    "equipment": {
        "tag": ["tag", "id", "equipment", "asset", "asset_no", "functional_location"],
        "equipment_type": ["equipment_type", "type", "category", "class", "object_type"],
        "service": ["service", "duty", "function", "description"],
        "manufacturer": ["manufacturer", "make", "oem", "vendor"],
        "model": ["model", "model_no", "type_no"],
        "install_date": ["install_date", "commissioned", "installation_date", "start_up"],
        "area": ["area", "location", "unit", "plant_section"],
        "criticality": ["criticality", "critical", "priority", "abc"],
        "seal_model": ["seal_model", "seal", "mechanical_seal"],
    },
}


def _norm_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (h or "").strip().lower()).strip("_")


def _map_row(row: dict, rec_type: str) -> dict:
    aliases = _COLUMN_ALIASES.get(rec_type, {})
    norm = {_norm_header(k): v for k, v in row.items()}
    rec = {}
    for field, names in aliases.items():
        for n in names:
            if norm.get(n) not in (None, ""):
                rec[field] = norm[n]
                break
    if "downtime_h" in rec:
        try:
            rec["downtime_h"] = float(rec["downtime_h"])
        except (ValueError, TypeError):
            rec["downtime_h"] = 0
    return rec


def parse_table(raw: bytes, filename: str) -> list[dict]:
    """CSV or JSON(-array) → list of row dicts. No LLM."""
    name = (filename or "").lower()
    txt = raw.decode("utf-8", errors="ignore")
    if name.endswith(".json") or txt.lstrip()[:1] in "[{":
        data = json.loads(txt)
        return data if isinstance(data, list) else data.get("rows", [data])
    return list(csv.DictReader(io.StringIO(txt)))


def ingest_table(rows: list[dict], rec_type: str) -> dict:
    """Bulk: map each row to a typed record and materialise. One text-index
    upsert at the end. This is the 'load years of CMMS history' path."""
    if rec_type not in _MATERIALISERS:
        return {"error": f"unsupported record type {rec_type!r}; "
                         f"one of {sorted(_MATERIALISERS)}"}
    kg = get_graph()
    mat = _MATERIALISERS[rec_type]
    chunks: list[dict] = []
    new_equipment: list[str] = []
    created: list[dict] = []
    errors = 0
    for i, row in enumerate(rows):
        rec = _map_row(row, rec_type)
        if not rec:
            errors += 1
            continue
        prov = Provenance(source_doc_id=f"bulk:{rec_type}", extractor="bulk_import",
                          effective_date=rec.get("date"))
        try:
            created.append(mat(kg, rec, prov, chunks, new_equipment))
        except Exception:
            errors += 1
    kg.save()
    if chunks:
        stores.upsert_text_chunks(chunks)
    return {"record_type": rec_type, "rows": len(rows), "created": len(created),
            "errors": errors, "new_equipment": new_equipment,
            "sample": created[:8]}
