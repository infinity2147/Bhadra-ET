"""Agent 1 — Universal Ingestion & Knowledge Graph builder (spec §5.1).

Routes every corpus document through its type-appropriate parser (spec §3.4):
  (a) text/office docs   -> pymupdf parse -> structure-preserving chunks
  (b) scanned/mixed      -> dual path: visual index (no OCR) + any parseable text
  (c) P&ID drawings      -> curated digitizer ground truth (regions + connectivity)
  (d) CMMS/structured    -> direct typed node/edge mapping (highest-signal RCA fuel)
  (e) email/unstructured -> LLM entity/relation extraction against the ontology

Every node/edge carries Provenance{source_doc_id, page, bbox, extractor,
confidence, effective_date}. Cross-document entity resolution: canonical tag
normalization + exact-tag matching (all corpus mentions use canonical tags;
the LLM extractor is instructed to reuse them).
"""
from __future__ import annotations

import json
import re
import time

import fitz

from . import config, stores
from .extraction import extract as llm_extract
from .graph import KnowledgeGraph, get_graph
from .ontology import Provenance

TAG_RE = re.compile(r"\b(?:P|E|T|V|TK|CT|STR|PSV|MOV|PI|TI|FI|LI)-\d{3,4}\b")

_chunk_counter = 0
_visual_counter = 0


def _next_chunk_id() -> int:
    global _chunk_counter
    _chunk_counter += 1
    return _chunk_counter


def normalize_tag(t: str) -> str:
    return t.upper().replace("–", "-").replace("—", "-").strip()


def tags_in(text: str) -> list[str]:
    return sorted({normalize_tag(m) for m in TAG_RE.findall(text)})


# ---------------------------------------------------------------- helpers
def render_pdf(pdf_path, doc_id: str) -> list[dict]:
    """Render each page to PNG for citations + visual index. Returns page infos."""
    out = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            name = f"{doc_id}_p{i}.png"
            dest = config.RENDER_DIR / name
            if not dest.exists():
                page.get_pixmap(dpi=110).save(str(dest))
            out.append({"page": i, "render": name,
                        "text": page.get_text("text")})
    return out


def add_document_node(kg: KnowledgeGraph, doc_id: str, doc_type: str,
                      effective_date: str | None, extractor: str, **props):
    prov = Provenance(source_doc_id=doc_id, extractor=extractor,
                      effective_date=effective_date)
    kg.add_node(doc_id, "Document", prov, doc_type=doc_type,
                effective_date=effective_date, **props)
    return prov


def link_tags(kg: KnowledgeGraph, doc_id: str, text: str, prov: Provenance,
              edge_type: str = "DESCRIBED_BY"):
    for tag in tags_in(text):
        if kg.node(tag):
            kg.add_edge(tag, doc_id, edge_type, prov)


def queue_chunks(pending: list, doc_id: str, doc_type: str, pages: list[dict],
                 sectioned: list[tuple[str, int]] | None = None):
    """sectioned: optional [(text, page)] to keep structure (steps/fields) intact."""
    if sectioned is None:
        sectioned = [(p["text"], p["page"]) for p in pages if p["text"].strip()]
    for text, page in sectioned:
        text = text.strip()
        if not text:
            continue
        pending.append({"id": _next_chunk_id(), "text": text[:4000], "doc_id": doc_id,
                        "doc_type": doc_type, "page": page,
                        "entity_tags": tags_in(text)})


# ---------------------------------------------------------------- per-type ingestion
def ingest_equipment(kg: KnowledgeGraph, report: dict):
    data = json.loads((config.CORPUS_DIR / "equipment.json").read_text())
    prov = Provenance(source_doc_id="equipment.json", extractor="structured_map")
    areas = set()
    for eq in data:
        kg.add_node(eq["tag"], "Equipment", prov,
                    equipment_type=eq["type"], service=eq["service"],
                    manufacturer=eq["manufacturer"], model=eq["model"],
                    install_date=eq["install_date"], area=eq["area"],
                    criticality=eq["criticality"],
                    seal_model=eq.get("seal_model"))
        areas.add(eq["area"])
        kg.add_edge(eq["tag"], eq["area"], "LOCATED_IN", prov)
    for a in sorted(areas):
        kg.add_node(a, "Area", prov, name=a)
    report["equipment"] = len(data)


def ingest_people(kg: KnowledgeGraph, report: dict):
    people = json.loads((config.CORPUS_DIR / "people.json").read_text())
    prov = Provenance(source_doc_id="people.json", extractor="structured_map")
    for p in people.values():
        kg.add_node(p["name"], "Person", prov, role=p["role"])
    report["people"] = len(people)


def ingest_drawings(kg: KnowledgeGraph, report: dict, pending_chunks: list,
                    visual_queue: list):
    ddir = config.CORPUS_DIR / "drawings"
    regions_index = []
    n = 0
    for rj in sorted(ddir.glob("*.regions.json")):
        meta = json.loads(rj.read_text())
        doc_id = meta["drawing_number"]
        prov = add_document_node(kg, doc_id, "PID", None, "digitizer_ground_truth",
                                 title=meta["title"], rev=meta["rev"],
                                 render=meta["image"], width=meta["width"],
                                 height=meta["height"])
        # copy render into serving dir
        src_png = ddir / meta["image"]
        dest = config.RENDER_DIR / meta["image"]
        if not dest.exists():
            dest.write_bytes(src_png.read_bytes())
        visual_queue.append({"doc_id": doc_id, "page": 1, "render": meta["image"],
                             "path": src_png})
        for r in meta["regions"]:
            tag = normalize_tag(r["tag"])
            rid = f"{doc_id}:{tag}"
            rprov = Provenance(source_doc_id=doc_id, page=1, bbox=r["bbox"],
                               extractor="digitizer_ground_truth")
            kg.add_node(rid, "DrawingRegion", rprov, equipment_tag=tag,
                        symbol_class=r["symbol_class"], bbox=r["bbox"])
            kg.add_edge(doc_id, rid, "HAS_REGION", rprov)
            if kg.node(tag):
                kg.add_edge(tag, doc_id, "DESCRIBED_BY", rprov)
            regions_index.append({"region_id": rid, "doc_id": doc_id, "page": 1,
                                  "bbox": r["bbox"], "symbol_class": r["symbol_class"],
                                  "equipment_tag": tag, "render": meta["image"]})
        for e in meta["connectivity"]:
            src, dst = normalize_tag(e["src"]), normalize_tag(e["dst"])
            for node in (src, dst):
                if not kg.node(node):  # off-sheet connections (e.g. AREA-2-HDR)
                    kg.add_node(node, "System", prov, name=node, offsheet=True)
            kg.add_edge(src, dst, "FEEDS_INTO", prov, via=e.get("via", ""))
        # searchable text stand-in for the drawing (title + tag list)
        queue_chunks(pending_chunks, doc_id, "PID",
                     [], [(f"Drawing {doc_id} rev {meta['rev']}: {meta['title']}. "
                           f"Shows: " + ", ".join(r['tag'] for r in meta['regions']), 1)])
        n += 1
    # legacy scanned drawing: visual-only path (no regions, no OCR) — the long tail
    legacy = ddir / "OMRE-legacy-PID.jpg"
    if legacy.exists():
        doc_id = "OMRE-legacy-PID"
        add_document_node(kg, doc_id, "PID", None, "visual_only",
                          title="Legacy scanned P&ID (1958 OMRE, public domain sample)",
                          render=legacy.name)
        dest = config.RENDER_DIR / legacy.name
        if not dest.exists():
            dest.write_bytes(legacy.read_bytes())
        visual_queue.append({"doc_id": doc_id, "page": 1, "render": legacy.name,
                             "path": legacy})
        n += 1
    stores.save_regions(regions_index)
    report["drawings"] = n
    report["drawing_regions"] = len(regions_index)


def ingest_work_orders(kg: KnowledgeGraph, report: dict, pending_chunks: list):
    wos = json.loads((config.CORPUS_DIR / "work_orders" / "work_orders.json").read_text())
    people = json.loads((config.CORPUS_DIR / "people.json").read_text())
    for wo in wos:
        doc_id = wo["id"]
        prov = add_document_node(kg, doc_id, "WO", wo["date"], "structured_map",
                                 title=wo["title"])
        kg.add_node(doc_id + ":rec", "WorkOrder", prov, wo_id=doc_id,
                    equipment=wo["equipment"], date=wo["date"], wo_type=wo["wo_type"],
                    title=wo["title"], findings=wo["findings"], parts=wo["parts"],
                    downtime_h=wo["downtime_h"])
        if kg.node(wo["equipment"]):
            kg.add_edge(wo["equipment"], doc_id + ":rec", "MAINTAINED_BY", prov)
            kg.add_edge(wo["equipment"], doc_id, "DESCRIBED_BY", prov)
        closer = people.get(wo["closed_by"], {}).get("name")
        if closer and kg.node(closer):
            kg.add_edge(doc_id, closer, "AUTHORED_BY", prov)
        link_tags(kg, doc_id, wo["findings"], prov)
        text = (f"Work order {doc_id} ({wo['wo_type']}) on {wo['equipment']} dated "
                f"{wo['date']}: {wo['title']}. Findings: {wo['findings']} "
                f"Parts: {wo['parts']}. Downtime {wo['downtime_h']} h. "
                f"Closed by {closer or 'n/a'}.")
        queue_chunks(pending_chunks, doc_id, "WO", [], [(text, 1)])
        # renders for citation click-through
        pdf = config.CORPUS_DIR / "work_orders" / f"{doc_id}.pdf"
        if pdf.exists():
            render_pdf(pdf, doc_id)
    report["work_orders"] = len(wos)


def ingest_inspections(kg: KnowledgeGraph, report: dict, pending_chunks: list):
    insps = json.loads((config.CORPUS_DIR / "inspections" / "inspections.json").read_text())
    for i in insps:
        doc_id = i["id"]
        prov = add_document_node(kg, doc_id, "inspection", i["date"], "structured_map")
        kg.add_node(doc_id + ":rec", "Inspection", prov, equipment=i["equipment"],
                    date=i["date"], method=i["method"], result=i["result"],
                    text=i["text"])
        if kg.node(i["equipment"]):
            kg.add_edge(i["equipment"], doc_id + ":rec", "INSPECTED_BY", prov)
            kg.add_edge(i["equipment"], doc_id, "DESCRIBED_BY", prov)
        link_tags(kg, doc_id, i["text"], prov)
        queue_chunks(pending_chunks, doc_id, "inspection", [],
                     [(f"Inspection {doc_id} of {i['equipment']} on {i['date']} "
                       f"({i['method']}), result {i['result']}: {i['text']}", 1)])
        pdf = config.CORPUS_DIR / "inspections" / f"{doc_id}.pdf"
        if pdf.exists():
            render_pdf(pdf, doc_id)
    report["inspections"] = len(insps)


def ingest_sops(kg: KnowledgeGraph, report: dict, pending_chunks: list):
    sops = json.loads((config.CORPUS_DIR / "sops" / "sops.json").read_text())
    by_id: dict[str, list] = {}
    for s in sops:
        by_id.setdefault(s["id"], []).append(s)
    n = 0
    for sid, revs in by_id.items():
        revs.sort(key=lambda s: s["rev"])
        prev_doc = None
        for s in revs:
            doc_id = f"{sid}_rev{s['rev']}"
            prov = add_document_node(kg, doc_id, "SOP", s["date"], "structured_map",
                                     title=s["title"], rev=s["rev"], sop_id=sid,
                                     superseded=(s is not revs[-1]))
            kg.add_node(doc_id + ":proc", "Procedure", prov, sop_id=sid,
                        rev=s["rev"], title=s["title"], steps=s["steps"],
                        hazards=s["hazards"], effective_date=s["date"])
            if prev_doc:
                kg.add_edge(doc_id, prev_doc, "SUPERSEDES", prov)
            prev_doc = doc_id
            # steps kept intact in one chunk (structure-preserving)
            text = (f"{sid} rev {s['rev']} (effective {s['date']}"
                    f"{', SUPERSEDED' if s is not revs[-1] else ', CURRENT'}): "
                    f"{s['title']}. Steps: " + " ".join(s["steps"])
                    + f" Hazards: {s['hazards']}")
            queue_chunks(pending_chunks, doc_id, "SOP", [], [(text, 1)])
            link_tags(kg, doc_id, text, prov)
            pdf = config.CORPUS_DIR / "sops" / f"{doc_id}.pdf"
            if pdf.exists():
                render_pdf(pdf, doc_id)
            n += 1
    report["sops"] = n


def ingest_incidents(kg: KnowledgeGraph, report: dict, pending_chunks: list):
    incs = json.loads((config.CORPUS_DIR / "incidents" / "incidents.json").read_text())
    for inc in incs:
        doc_id = inc["id"]
        prov = add_document_node(kg, doc_id, "incident", inc["date"], "structured_map",
                                 title=inc["title"])
        kg.add_node(doc_id + ":rec", "Incident", prov, incident_id=doc_id,
                    date=inc["date"], area=inc["area"], equipment=inc["equipment"],
                    category=inc["category"], title=inc["title"],
                    narrative=inc["narrative"], root_cause=inc["root_cause"],
                    precursors=inc["precursors"], actions=inc["actions"])
        if kg.node(inc["equipment"]):
            kg.add_edge(doc_id + ":rec", inc["equipment"], "INVOLVES", prov)
            kg.add_edge(inc["equipment"], doc_id, "DESCRIBED_BY", prov)
        if kg.node(inc["area"]):
            kg.add_edge(doc_id + ":rec", inc["area"], "INVOLVES", prov)
        link_tags(kg, doc_id, inc["narrative"] + " " + inc["precursors"], prov)
        text = (f"{inc['category']} {doc_id} on {inc['date']} at {inc['area']} "
                f"({inc['equipment']}): {inc['title']}. {inc['narrative']} "
                f"Root cause: {inc['root_cause']} Precursor conditions: "
                f"{inc['precursors']}. Actions: {inc['actions']}")
        queue_chunks(pending_chunks, doc_id, "incident", [], [(text, 1)])
        pdf = config.CORPUS_DIR / "incidents" / f"{doc_id}.pdf"
        if pdf.exists():
            render_pdf(pdf, doc_id)
    report["incidents"] = len(incs)


def ingest_permits(kg: KnowledgeGraph, report: dict, pending_chunks: list):
    permits = json.loads((config.CORPUS_DIR / "permits" / "permits.json").read_text())
    for p in permits:
        doc_id = p["id"]
        prov = add_document_node(kg, doc_id, "permit", p["date"], "structured_map",
                                 ptype=p["ptype"], equipment=p["equipment"],
                                 area=p["area"], date=p["date"], text=p["text"])
        if kg.node(p["equipment"]):
            kg.add_edge(doc_id, p["equipment"], "INVOLVES", prov)
        text = (f"Permit to work {doc_id} ({p['ptype']}) dated {p['date']} for "
                f"{p['equipment']} in {p['area']}: {p['text']}")
        queue_chunks(pending_chunks, doc_id, "permit", [], [(text, 1)])
        pdf = config.CORPUS_DIR / "permits" / f"{doc_id}.pdf"
        if pdf.exists():
            render_pdf(pdf, doc_id)
    report["permits"] = len(permits)


def ingest_regulatory(kg: KnowledgeGraph, report: dict, pending_chunks: list):
    path = config.CORPUS_DIR / "regulatory" / "clauses.json"
    clauses = json.loads(path.read_text())
    for c in clauses:
        doc_id = c["id"]
        prov = add_document_node(kg, doc_id, "regulatory", None, "structured_map",
                                 standard=c["standard"], clause=c["clause"],
                                 title=c["title"], source_url=c["source_url"])
        kg.add_node(doc_id + ":clause", "RegulatoryClause", prov,
                    standard=c["standard"], clause=c["clause"], title=c["title"],
                    requirement=c["requirement"], activity=c["activity"],
                    verbatim=c["verbatim"], source_url=c["source_url"],
                    source_tier=c["source_tier"], note=c.get("note"))
        for target in c["applies_to"]:
            if kg.node(target):
                kg.add_edge(target, doc_id + ":clause", "GOVERNED_BY", prov)
        text = (f"Regulatory requirement {c['standard']} {c['clause']} - {c['title']}: "
                f"{c['requirement']} (applies to: {', '.join(c['applies_to'])})")
        queue_chunks(pending_chunks, doc_id, "regulatory", [], [(text, 1)])
    report["regulatory_clauses"] = len(clauses)


def ingest_manuals(kg: KnowledgeGraph, report: dict, pending_chunks: list,
                   visual_queue: list):
    """Scanned-look OEM pages: dual path — visual index (no OCR) + text index."""
    mdir = config.CORPUS_DIR / "manuals"
    manuals = json.loads((mdir / "manuals.json").read_text())
    raw = {m["id"]: m for m in json.loads(
        (config.CORPUS_DIR / "manuals" / "manuals.json").read_text())}
    for m in manuals:
        doc_id = m["id"]
        prov = add_document_node(kg, doc_id, "OEM_manual", None, "structured_map",
                                 title=m["title"])
        pdf = mdir / f"{doc_id}.pdf"
        pages = render_pdf(pdf, doc_id)
        for p in pages:
            visual_queue.append({"doc_id": doc_id, "page": p["page"],
                                 "render": p["render"],
                                 "path": config.RENDER_DIR / p["render"]})
        # text side of the dual path (here: embedded text layer / OCR equivalent)
        queue_chunks(pending_chunks, doc_id, "OEM_manual", pages)
        link_tags(kg, doc_id, " ".join(p["text"] for p in pages), prov)
    report["manuals"] = len(manuals)


def ingest_emails(kg: KnowledgeGraph, report: dict, pending_chunks: list,
                  use_llm: bool = True):
    """Unstructured path: LLM entity/relation extraction against the ontology."""
    edir = config.CORPUS_DIR / "email"
    emails = json.loads((edir / "emails.json").read_text())
    known = [n["id"] for n in kg.nodes_by_type("Equipment")]
    extraction_log = []
    for e in emails:
        doc_id = e["id"]
        body = "\n".join(e["body"])
        text = f"Email {e['date']} from {e['frm']} to {e['to']}. Subject: {e['subject']}. {body}"
        prov = add_document_node(kg, doc_id, "email", e["date"], "llm_extraction",
                                 subject=e["subject"], frm=e["frm"])
        queue_chunks(pending_chunks, doc_id, "email", [], [(text, 1)])
        link_tags(kg, doc_id, text, prov)
        if not use_llm:
            continue
        try:
            ext = llm_extract(doc_id, text, known)
        except Exception as exc:  # extraction failure must not sink ingestion
            extraction_log.append({"doc": doc_id, "error": str(exc)})
            continue
        eprov = Provenance(source_doc_id=doc_id, extractor="llm_extraction",
                           confidence=0.8, effective_date=e["date"])
        for ent in ext["entities"]:
            kg.add_node(normalize_tag(ent["id"]) if TAG_RE.fullmatch(ent["id"] or "")
                        else ent["id"], ent["type"], eprov, **ent.get("props", {}))
        for rel in ext["relations"]:
            src = normalize_tag(rel["src"]) if TAG_RE.fullmatch(rel["src"]) else rel["src"]
            dst = normalize_tag(rel["dst"]) if TAG_RE.fullmatch(rel["dst"]) else rel["dst"]
            if kg.node(src) and kg.node(dst):
                kg.add_edge(src, dst, rel["type"], eprov)
        extraction_log.append({"doc": doc_id, "entities": len(ext["entities"]),
                               "relations": len(ext["relations"]),
                               "rejected": len(ext["rejected"]),
                               "summary": ext["summary"]})
    report["emails"] = len(emails)
    report["email_extraction"] = extraction_log


# ---------------------------------------------------------------- build
def build(use_llm_for_emails: bool = True, visual: bool = True) -> dict:
    t0 = time.time()
    kg = get_graph()
    report: dict = {}
    pending_chunks: list[dict] = []
    visual_queue: list[dict] = []

    ingest_equipment(kg, report)
    ingest_people(kg, report)
    ingest_drawings(kg, report, pending_chunks, visual_queue)
    ingest_work_orders(kg, report, pending_chunks)
    ingest_inspections(kg, report, pending_chunks)
    ingest_sops(kg, report, pending_chunks)
    ingest_incidents(kg, report, pending_chunks)
    ingest_permits(kg, report, pending_chunks)
    ingest_regulatory(kg, report, pending_chunks)
    ingest_manuals(kg, report, pending_chunks, visual_queue)
    ingest_emails(kg, report, pending_chunks, use_llm=use_llm_for_emails)

    stores.upsert_text_chunks(pending_chunks)
    report["text_chunks"] = len(pending_chunks)

    # visual index covers the ENTIRE corpus: every rendered page, plus drawings
    # and scanned manuals (queued explicitly above) — OCR-free late interaction.
    queued = {q["render"] for q in visual_queue}
    for png in sorted(config.RENDER_DIR.glob("*_p*.png")):
        if png.name in queued:
            continue
        doc_id, _, pno = png.stem.rpartition("_p")
        visual_queue.append({"doc_id": doc_id, "page": int(pno),
                             "render": png.name, "path": png})

    if visual and config.VISUAL_ENABLED:
        import hashlib
        from PIL import Image

        def vid_of(doc_id: str, page: int) -> int:
            return int(hashlib.md5(f"{doc_id}#p{page}".encode()).hexdigest()[:15], 16)

        # incremental: only embed pages not already in the collection
        # (keyed on payload, robust to the point-id scheme)
        existing: set[tuple] = set()
        if stores.client().collection_exists(config.VISUAL_COLLECTION):
            recs, _ = stores.client().scroll(config.VISUAL_COLLECTION,
                                             limit=100000, with_payload=True)
            existing = {(r.payload["doc_id"], r.payload["page"]) for r in recs}
        todo = [q for q in visual_queue
                if (q["doc_id"], q["page"]) not in existing]
        vm = stores.visual_model() if todo else None
        pages = []
        for q in todo:
            img = Image.open(q["path"]).convert("RGB")
            emb = vm.embed_images([img])[0]
            pages.append({"id": vid_of(q["doc_id"], q["page"]),
                          "doc_id": q["doc_id"], "page": q["page"],
                          "render": q["render"], "multivector": emb})
        stores.upsert_visual_pages(pages)
        report["visual_pages"] = len(existing) + len(pages)
        report["visual_pages_new"] = len(pages)

    kg.save()
    report["graph"] = kg.stats()
    report["elapsed_s"] = round(time.time() - t0, 1)
    config.INGEST_LOG_PATH.write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    import sys
    r = build(use_llm_for_emails="--no-llm" not in sys.argv,
              visual="--no-visual" not in sys.argv)
    print(json.dumps({k: v for k, v in r.items() if k != "email_extraction"}, indent=1))
