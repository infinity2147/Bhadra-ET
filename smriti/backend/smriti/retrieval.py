"""Tri-modal retrieval fabric (spec §3.2).

route()   — fast-model intent classifier picks modalities
retrieve()— fans out to text / graph / visual retrievers, merges, reranks,
            attaches provenance, and prepares drawing-overlay payloads.

Every step is appended to a reasoning trace the UI renders live.
"""
from __future__ import annotations

import json
from typing import Optional

from . import config, llm, stores
from .graph import get_graph

ROUTER_PROMPT = """Classify this industrial plant query for retrieval routing.

Query: {query}

Modalities:
- "text": factual lookup in documents (procedures, records, values, history)
- "graph": relational/connectivity/causal questions (what feeds X, what shares Y,
  failure patterns across equipment, compliance mapping)
- "visual": the user wants to SEE something, mentions drawings/diagrams/pages,
  or the answer likely lives on a drawing or scanned manual page

Also detect equipment tags mentioned (canonical like P-101) and overall intent.

Return ONLY JSON:
{{"modalities": ["text"|"graph"|"visual", ...], "intent": "factual|relational|rca|compliance|visual|proactive|other", "tags": ["P-101", ...]}}"""


def route(query: str) -> dict:
    kg = get_graph()
    tags_exact = kg.find_equipment(query)
    try:
        r = llm.complete_json(ROUTER_PROMPT.format(query=query),
                              model=config.MODEL_FAST)
        modalities = [m for m in r.get("modalities", []) if m in
                      ("text", "graph", "visual")] or ["text"]
        tags = sorted(set(tags_exact) | {t for t in r.get("tags", [])
                                         if kg.node(t)})
        return {"modalities": modalities, "intent": r.get("intent", "other"),
                "tags": tags}
    except Exception:
        # router failure degrades to full fan-out, never to a dead end
        return {"modalities": ["text", "graph", "visual"], "intent": "other",
                "tags": tags_exact}


REWRITE_PROMPT = """Rewrite the user's latest question into a standalone question for
document retrieval, resolving pronouns and ellipsis ("it", "that pump", "why?",
"what about P-103") using the conversation. Keep equipment tags explicit.

Conversation so far:
{history}

Latest question: {query}

Return ONLY the rewritten standalone question, nothing else."""


def contextualize(query: str, history: list[dict]) -> str:
    """Resolve a follow-up against prior turns → a standalone retrieval query."""
    if not history:
        return query
    convo = "\n".join(f"{m['role']}: {m['content'][:400]}" for m in history[-6:])
    try:
        rewritten = llm.complete(
            REWRITE_PROMPT.format(history=convo, query=query),
            model=config.MODEL_FAST).strip().strip('"')
        # guard against the model over-rewriting a already-complete question
        return rewritten if 3 <= len(rewritten) <= 400 else query
    except Exception:
        return query


def graph_evidence(tags: list[str], intent: str) -> list[dict]:
    """Turn graph neighborhoods/traces into citable evidence items."""
    kg = get_graph()
    items = []
    for tag in tags[:3]:
        node = kg.node(tag)
        if not node:
            continue
        upstream = kg.trace(tag, "FEEDS_INTO", "in", depth=3)
        downstream = kg.trace(tag, "FEEDS_INTO", "out", depth=3)
        if upstream or downstream:
            lines = [f"{e['src']} FEEDS_INTO {e['dst']}"
                     f"{' via ' + e['via'] if e.get('via') else ''}"
                     for e in upstream + downstream]
            src_doc = (upstream + downstream)[0]["provenance"][0]["source_doc_id"]
            items.append({
                "doc_id": src_doc, "doc_type": "graph", "page": 1,
                "text": f"Connectivity of {tag} (from drawing graph): "
                        + "; ".join(dict.fromkeys(lines)),
                "graph_nodes": [tag],
                "graph_edges": upstream + downstream,
            })
        nb = kg.neighborhood(tag, depth=1,
                             edge_types=["MAINTAINED_BY", "INSPECTED_BY",
                                         "GOVERNED_BY", "INVOLVES",
                                         "HAS_FAILURE_MODE"])
        recs = [n for n in nb["nodes"]
                if n and n.get("type") in ("WorkOrder", "Inspection", "Incident",
                                           "RegulatoryClause")]
        if recs:
            summary_bits = []
            for r in sorted(recs, key=lambda n: str(n.get("date", "")),
                            reverse=True)[:14]:
                if r["type"] == "WorkOrder":
                    summary_bits.append(f"WO {r['wo_id']} ({r['date']}, {r['wo_type']}): {r['title']}")
                elif r["type"] == "Inspection":
                    summary_bits.append(f"Inspection {r['id'].split(':')[0]} ({r['date']}): {r['result']}")
                elif r["type"] == "Incident":
                    summary_bits.append(f"{r['incident_id']} ({r['date']}): {r['title']}")
                else:
                    summary_bits.append(f"{r['standard']} {r['clause']}: {r['title']}")
            items.append({
                "doc_id": f"graph:{tag}", "doc_type": "graph", "page": 1,
                "text": f"Graph records linked to {tag}: " + " | ".join(summary_bits),
                "graph_nodes": [tag] + [r["id"] for r in recs],
            })
    return items


def retrieve(query: str, trace: Optional[list] = None,
             history: Optional[list] = None) -> dict:
    trace = trace if trace is not None else []
    search_query = contextualize(query, history or [])
    if search_query != query:
        trace.append({"step": "contextualize", "rewritten": search_query})
    routing = route(search_query)
    trace.append({"step": "route", **routing})

    evidence: list[dict] = []
    if "text" in routing["modalities"] or True:  # text always contributes
        hits = stores.search_text(search_query, limit=config.TOP_K_TEXT)
        trace.append({"step": "text_search",
                      "hits": [(h["doc_id"], round(h["score"], 3)) for h in hits[:8]]})
        evidence.extend(hits)
    if "graph" in routing["modalities"] and routing["tags"]:
        g_items = graph_evidence(routing["tags"], routing["intent"])
        trace.append({"step": "graph_traverse", "tags": routing["tags"],
                      "items": len(g_items)})
        evidence.extend(g_items)
    visual_hits = []
    if "visual" in routing["modalities"]:
        try:
            visual_hits = stores.search_visual(search_query, limit=config.TOP_K_VISUAL)
            trace.append({"step": "visual_search",
                          "hits": [(h["doc_id"], f"p{h['page']}",
                                    round(h["score"], 2)) for h in visual_hits]})
        except Exception as exc:
            trace.append({"step": "visual_search", "error": str(exc)[:200]})

    # merge + rerank; visual pages matched by APPEARANCE, their content joins
    # from the dual-path text index so the answer model can actually quote them
    for vh in visual_hits:
        vh["doc_type"] = "visual_page"
        content = stores.chunk_text(vh["doc_id"], vh["page"])
        vh["text"] = (f"[Retrieved VISUALLY by page appearance — no OCR used in "
                      f"retrieval] {vh['doc_id']} page {vh['page']}: "
                      + (content[:1100] if content else "(image-only document, "
                         "e.g. a legacy scanned drawing — content visible to the "
                         "user in the viewer)"))
        evidence.append(vh)

    # dedupe by (doc_id, page)
    seen, deduped = set(), []
    for e in evidence:
        key = (e["doc_id"], e.get("page", 1), e.get("doc_type"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)

    ranked = stores.rerank(search_query, deduped, top_k=config.TOP_K_FINAL)
    # keep visual pages in evidence even if the cross-encoder dislikes their
    # synthetic description — they matched on appearance, not words.
    kept_ids = {id(e) for e in ranked}
    for vh in visual_hits[:2]:
        if id(vh) not in kept_ids:
            ranked.append(vh)
    trace.append({"step": "rerank",
                  "kept": [(e["doc_id"], round(e.get("rerank_score", 0), 2))
                           for e in ranked]})

    overlays = build_overlays(routing["tags"], ranked)
    if overlays:
        trace.append({"step": "drawing_overlay",
                      "drawings": [o["doc_id"] for o in overlays]})
    return {"routing": routing, "evidence": ranked, "overlays": overlays,
            "trace": trace}


def build_overlays(tags: list[str], evidence: list[dict]) -> list[dict]:
    """Highlight boxes + traced FEEDS_INTO edges on any drawing in evidence
    or any drawing that depicts a queried tag (spec §3.3)."""
    kg = get_graph()
    drawings: dict[str, dict] = {}

    def ensure(doc_id: str) -> Optional[dict]:
        if doc_id in drawings:
            return drawings[doc_id]
        node = kg.node(doc_id)
        if not node or node.get("doc_type") != "PID" or not node.get("render"):
            return None
        drawings[doc_id] = {"doc_id": doc_id, "render": node["render"],
                            "width": node.get("width"), "height": node.get("height"),
                            "highlights": [], "traced_edges": []}
        return drawings[doc_id]

    for tag in tags:
        for region in stores.regions_for(tag=tag):
            d = ensure(region["doc_id"])
            if d is None:
                continue
            d["highlights"].append({"tag": tag, "bbox": region["bbox"],
                                    "primary": True})
            # trace upstream feed and highlight those regions too
            for e in kg.trace(tag, "FEEDS_INTO", "in", depth=3):
                for r2 in stores.regions_for(doc_id=region["doc_id"], tag=e["src"]):
                    d["highlights"].append({"tag": e["src"], "bbox": r2["bbox"],
                                            "primary": False})
                d["traced_edges"].append({"src": e["src"], "dst": e["dst"]})
    # drawings that were themselves retrieved visually
    for e in evidence:
        if e.get("doc_type") == "visual_page":
            ensure(e["doc_id"])
    # dedupe highlights
    for d in drawings.values():
        seen, uniq = set(), []
        for h in d["highlights"]:
            if h["tag"] not in seen:
                seen.add(h["tag"])
                uniq.append(h)
        d["highlights"] = uniq
        dseen, dedges = set(), []
        for ed in d["traced_edges"]:
            k = (ed["src"], ed["dst"])
            if k not in dseen:
                dseen.add(k)
                dedges.append(ed)
        d["traced_edges"] = dedges
    return list(drawings.values())
