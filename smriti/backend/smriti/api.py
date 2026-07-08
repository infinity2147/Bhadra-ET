"""SMRITI HTTP API + frontend host.

Endpoints (spec §5 interfaces):
  POST /api/ask              SSE stream: trace -> deltas -> final answer object
  GET  /api/equipment/{tag}/context
  POST /api/rca              {tag, symptom} -> structured RCA
  GET  /api/patterns         lessons-learned clusters + priorities
  GET  /api/warnings         proactive precursor warnings (live monitor)
  GET  /api/compliance/register
  POST /api/compliance/audit-package   {scope}
  GET  /api/graph/stats, /api/graph/neighborhood/{id}
  GET  /api/eval/latest      eval harness results for the dashboard
  POST /api/ingest           upload a new document (LLM extraction path)
  /renders/*                 page images for citation click-through
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from . import compliance, config, lessons, rca
from .graph import get_graph

app = FastAPI(title="SMRITI — Unified Asset & Operations Brain")


class NoCacheStatic(BaseHTTPMiddleware):
    """Never let a browser serve a stale frontend during a live demo."""
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/static", "/renders")) or request.url.path == "/":
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app.add_middleware(NoCacheStatic)

FRONTEND = config.ROOT / "frontend"


@app.post("/api/ask")
async def api_ask(body: dict):
    from .copilot import ask
    query = (body.get("query") or "").strip()
    history = body.get("history") or []

    def gen():
        try:
            for event in ask(query, history=history):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/equipment")
async def equipment_list():
    kg = get_graph()
    return sorted(
        ({"tag": n["id"], "type": n.get("equipment_type"),
          "service": n.get("service"), "area": n.get("area"),
          "criticality": n.get("criticality")}
         for n in kg.nodes_by_type("Equipment")),
        key=lambda e: e["tag"])


def _invalidate_derived_caches():
    """Drop cached agent outputs so they recompute after the fabric changes."""
    for name in ("patterns.json", "warnings.json", "compliance_register.json",
                 "audit_package.json"):
        p = config.DATA_DIR / name
        if p.exists():
            p.unlink()


@app.post("/api/equipment")
async def add_equipment(body: dict):
    """Add a new asset to the fabric — appears immediately in Assets, RCA, search."""
    from . import stores
    from .ingest import normalize_tag
    from .ontology import Provenance
    kg = get_graph()
    tag = normalize_tag((body.get("tag") or "").strip())
    if not tag:
        return JSONResponse({"error": "tag is required"}, status_code=400)
    if kg.node(tag):
        return JSONResponse({"error": f"{tag} already exists"}, status_code=409)
    area = (body.get("area") or "").strip() or "Unassigned"
    prov = Provenance(source_doc_id="manual_entry", extractor="manual")
    props = {k: body.get(k) for k in ("equipment_type", "service", "manufacturer",
                                      "model", "install_date", "criticality",
                                      "seal_model") if body.get(k)}
    props.setdefault("criticality", "medium")
    kg.add_node(tag, "Equipment", prov, area=area, **props)
    if not kg.node(area):
        kg.add_node(area, "Area", prov, name=area)
    kg.add_edge(tag, area, "LOCATED_IN", prov)
    kg.save()
    # make it retrievable in Ask
    from .ingest import _next_chunk_id
    stores.upsert_text_chunks([{
        "id": _next_chunk_id(),
        "text": f"Equipment {tag} ({props.get('equipment_type','')}) — "
                f"{props.get('service','')}. Area {area}. Manufacturer "
                f"{props.get('manufacturer','')} model {props.get('model','')}. "
                f"Criticality {props.get('criticality')}.",
        "doc_id": tag, "doc_type": "equipment", "page": 1, "entity_tags": [tag]}])
    return {"ok": True, "tag": tag, "area": area, **props}


@app.get("/api/equipment/{tag}/context")
async def equipment_context(tag: str):
    kg = get_graph()
    node = kg.node(tag)
    if not node:
        return JSONResponse({"error": "unknown tag"}, status_code=404)
    nb = kg.neighborhood(tag, depth=1)
    from . import stores
    return {"equipment": node, "neighborhood": nb,
            "regions": stores.regions_for(tag=tag)}


@app.get("/api/equipment/{tag}/summary")
async def equipment_summary(tag: str):
    """Composed asset view: metadata, health timeline, governing regs, drawing overlay."""
    from . import rca, retrieval
    kg = get_graph()
    node = kg.node(tag)
    if not node:
        return JSONResponse({"error": "unknown tag"}, status_code=404)

    timeline = rca.failure_timeline(tag)
    wos = [e for e in timeline if e["kind"] in ("PM", "CM", "breakdown")]
    insp = [e for e in timeline if e["kind"].startswith("inspection")]
    inc = [e for e in timeline if e["kind"].startswith("incident")]
    breakdowns = [e for e in timeline if e["kind"] in ("CM", "breakdown")]

    # governing regulatory clauses (+ status from the compliance cache if present)
    reg_status = {}
    reg_cache = config.DATA_DIR / "compliance_register.json"
    if reg_cache.exists():
        for r in json.loads(reg_cache.read_text()):
            reg_status[(r["standard"], r["clause"])] = r["status"]
    governing = []
    for e in kg.edges_of(tag, "GOVERNED_BY", "out"):
        c = kg.node(e["dst"])
        if c and c.get("standard"):
            governing.append({"standard": c["standard"], "clause": c["clause"],
                              "title": c["title"],
                              "status": reg_status.get((c["standard"], c["clause"]))})

    overlays = retrieval.build_overlays([tag], [])

    return {
        "equipment": {k: node.get(k) for k in
                      ("id", "equipment_type", "service", "manufacturer", "model",
                       "install_date", "area", "criticality", "seal_model")},
        "stats": {"work_orders": len(wos), "inspections": len(insp),
                  "incidents": len(inc), "breakdowns": len(breakdowns),
                  "last_event": timeline[-1]["date"] if timeline else None},
        "timeline": list(reversed(timeline)),
        "governing": governing,
        "drawings": overlays,
    }


@app.post("/api/rca")
async def api_rca(body: dict):
    result = rca.run_rca(body.get("tag", ""), body.get("symptom", ""))
    if body.get("confirm"):
        rca.confirm_rca(result)
    return result


@app.get("/api/patterns")
async def api_patterns():
    return {"patterns": lessons.build_patterns(),
            "priorities": lessons.prevention_priorities()}


@app.get("/api/warnings")
async def api_warnings(refresh: bool = False):
    path = config.DATA_DIR / "warnings.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    return lessons.evaluate_upcoming()


@app.get("/api/compliance/register")
async def api_register(refresh: bool = False):
    return compliance.build_register(force=refresh)


@app.post("/api/compliance/audit-package")
async def api_audit(body: dict):
    return compliance.audit_package(body.get("scope", ""))


@app.get("/api/graph/stats")
async def graph_stats():
    kg = get_graph()
    ingest_report = {}
    if config.INGEST_LOG_PATH.exists():
        ingest_report = json.loads(config.INGEST_LOG_PATH.read_text())
    return {"stats": kg.stats(), "ingest": {
        k: v for k, v in ingest_report.items() if k != "email_extraction"}}


@app.get("/api/graph/neighborhood/{node_id}")
async def graph_neighborhood(node_id: str, depth: int = 1):
    return get_graph().neighborhood(node_id, depth=depth)


@app.get("/api/eval/latest")
async def eval_latest():
    path = config.ROOT / "eval" / "results.json"
    if path.exists():
        return json.loads(path.read_text())
    return JSONResponse({"error": "eval not yet run"}, status_code=404)


def _index_visual(doc_id: str, pages: list[dict]) -> int:
    """OCR-free visual index for an uploaded PDF's rendered pages (best effort)."""
    if not config.VISUAL_ENABLED or not any(p.get("render") for p in pages):
        return 0
    try:
        import hashlib
        from PIL import Image
        from . import stores
        vm = stores.visual_model()
        vpoints = []
        for p in pages:
            if not p.get("render"):
                continue
            img = Image.open(config.RENDER_DIR / p["render"]).convert("RGB")
            emb = vm.embed_images([img])[0]
            vid = int(hashlib.md5(f"{doc_id}#p{p['page']}".encode()).hexdigest()[:15], 16)
            vpoints.append({"id": vid, "doc_id": doc_id, "page": p["page"],
                            "render": p["render"], "multivector": emb})
        stores.upsert_visual_pages(vpoints)
        return len(vpoints)
    except Exception:
        return 0


@app.post("/api/ingest")
async def api_ingest(files: list[UploadFile], visual: bool = True):
    """Continuous document intake — drop in ANY number of WO/inspection/SOP/incident/
    permit/manual files. Each is classified and materialised into the SAME typed
    records the corpus build produces, so it lands in the timeline, warnings and
    compliance immediately (spec §5.1, made continuous). Derived caches are
    invalidated so Warnings/Compliance recompute against the new records."""
    from .ingest import render_pdf
    from . import intake

    reports = []
    for file in files:
        suffix = Path(file.filename or "upload.pdf").suffix or ".pdf"
        doc_id = Path(file.filename or "upload").stem.replace(" ", "_")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        if suffix.lower() == ".pdf":
            pages = render_pdf(tmp_path, doc_id)      # page PNGs for citation click-through
            text = "\n".join(p["text"] for p in pages)
        else:
            text = tmp_path.read_text(errors="ignore")
            pages = [{"page": 1, "text": text, "render": None}]

        report = intake.ingest_document(doc_id, text, pages)   # classify → typed records
        report["pages"] = len(pages)
        if visual:
            report["visual_pages"] = _index_visual(doc_id, pages)
        reports.append(report)

    _invalidate_derived_caches()
    return {"ingested": len(reports), "documents": reports}


@app.post("/api/ingest/table")
async def api_ingest_table(file: UploadFile, record_type: str):
    """Bulk CMMS-export intake: a CSV/JSON of many work orders / inspections /
    incidents / permits / equipment → typed records, column-mapped, NO per-row
    LLM. This is how years of history load. record_type ∈
    {work_order, inspection, incident, permit, equipment}."""
    from . import intake
    raw = await file.read()
    try:
        rows = intake.parse_table(raw, file.filename or "upload.csv")
    except Exception as exc:
        return JSONResponse({"error": f"could not parse table: {exc}"}, status_code=400)
    result = intake.ingest_table(rows, record_type)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    _invalidate_derived_caches()
    return result


app.mount("/renders", StaticFiles(directory=str(config.RENDER_DIR)), name="renders")


@app.get("/")
async def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")
