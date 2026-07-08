"""Vector stores and embedding models.

- Text: Qdrant embedded collection with named dense (bge-small) + sparse (BM25)
  vectors, fused with RRF via Qdrant's hybrid query API.
- Visual: Qdrant multivector collection (MaxSim comparator) holding
  colSmol-256M patch embeddings per rendered page — OCR-free late interaction.
- Region index: JSON join between drawing pixels and graph nodes.

All models are lazy singletons so the API process only pays for what it uses.
"""
from __future__ import annotations

import json
import threading
from typing import Optional

from qdrant_client import QdrantClient, models as qm

from . import config

_lock = threading.Lock()
_client: Optional[QdrantClient] = None
_dense = None
_sparse = None
_rerank = None
_visual = None


def client() -> QdrantClient:
    global _client
    with _lock:
        if _client is None:
            _client = QdrantClient(path=str(config.QDRANT_PATH))
        return _client


def dense_model():
    global _dense
    if _dense is None:
        from fastembed import TextEmbedding
        _dense = TextEmbedding(config.DENSE_MODEL)
    return _dense


def sparse_model():
    global _sparse
    if _sparse is None:
        from fastembed import SparseTextEmbedding
        _sparse = SparseTextEmbedding(config.SPARSE_MODEL)
    return _sparse


def reranker():
    global _rerank
    if _rerank is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _rerank = TextCrossEncoder(config.RERANK_MODEL)
    return _rerank


class VisualRetriever:
    """colSmol-256M late-interaction visual retriever (ColPali family)."""

    def __init__(self):
        import torch
        from colpali_engine.models import ColIdefics3, ColIdefics3Processor
        self.torch = torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        dtype = torch.float16 if self.device == "mps" else torch.float32
        self.model = ColIdefics3.from_pretrained(
            config.VISUAL_MODEL, torch_dtype=dtype, device_map=self.device).eval()
        self.processor = ColIdefics3Processor.from_pretrained(config.VISUAL_MODEL)

    def embed_images(self, pil_images: list) -> list:
        out = []
        with self.torch.no_grad():
            for img in pil_images:  # one at a time: 8 GB RAM budget
                batch = self.processor.process_images([img]).to(self.device)
                emb = self.model(**batch)          # (1, n_patches, dim)
                out.append(emb[0].float().cpu().numpy())
        return out

    def embed_query(self, text: str):
        with self.torch.no_grad():
            batch = self.processor.process_queries([text]).to(self.device)
            emb = self.model(**batch)
        return emb[0].float().cpu().numpy()


def visual_model() -> VisualRetriever:
    global _visual
    if _visual is None:
        _visual = VisualRetriever()
    return _visual


# ---------------------------------------------------------------- collections
def ensure_collections(visual_dim: Optional[int] = None):
    c = client()
    if not c.collection_exists(config.TEXT_COLLECTION):
        c.create_collection(
            collection_name=config.TEXT_COLLECTION,
            vectors_config={"dense": qm.VectorParams(size=384, distance=qm.Distance.COSINE)},
            sparse_vectors_config={"sparse": qm.SparseVectorParams(
                modifier=qm.Modifier.IDF)},
        )
    if visual_dim and not c.collection_exists(config.VISUAL_COLLECTION):
        c.create_collection(
            collection_name=config.VISUAL_COLLECTION,
            vectors_config=qm.VectorParams(
                size=visual_dim, distance=qm.Distance.COSINE,
                multivector_config=qm.MultiVectorConfig(
                    comparator=qm.MultiVectorComparator.MAX_SIM),
                hnsw_config=qm.HnswConfigDiff(m=0),  # brute force: exact at this scale
            ),
        )


def upsert_text_chunks(chunks: list[dict]):
    """chunks: [{id:int, text, doc_id, page, section, entity_tags[]}]"""
    ensure_collections()
    texts = [ch["text"] for ch in chunks]
    dense = list(dense_model().embed(texts))
    sparse = list(sparse_model().embed(texts))
    points = []
    for ch, dv, sv in zip(chunks, dense, sparse):
        points.append(qm.PointStruct(
            id=ch["id"],
            vector={"dense": dv.tolist(),
                    "sparse": qm.SparseVector(indices=sv.indices.tolist(),
                                              values=sv.values.tolist())},
            payload={k: v for k, v in ch.items() if k != "id"},
        ))
    client().upsert(config.TEXT_COLLECTION, points=points)


def search_text(query: str, limit: int = config.TOP_K_TEXT) -> list[dict]:
    """Hybrid dense+sparse with reciprocal rank fusion."""
    ensure_collections()
    dq = list(dense_model().embed([query]))[0]
    sq = list(sparse_model().embed([query]))[0]
    res = client().query_points(
        config.TEXT_COLLECTION,
        prefetch=[
            qm.Prefetch(query=dq.tolist(), using="dense", limit=limit * 2),
            qm.Prefetch(query=qm.SparseVector(indices=sq.indices.tolist(),
                                              values=sq.values.tolist()),
                        using="sparse", limit=limit * 2),
        ],
        query=qm.FusionQuery(fusion=qm.Fusion.RRF),
        limit=limit, with_payload=True,
    )
    return [{"score": p.score, "id": p.id, **(p.payload or {})} for p in res.points]


def upsert_visual_pages(pages: list[dict]):
    """pages: [{id:int, doc_id, page, render, multivector(np (n,dim))}]"""
    if not pages:
        return
    dim = pages[0]["multivector"].shape[1]
    ensure_collections(visual_dim=dim)
    points = [qm.PointStruct(
        id=p["id"], vector=p["multivector"].tolist(),
        payload={"doc_id": p["doc_id"], "page": p["page"], "render": p["render"]},
    ) for p in pages]
    client().upsert(config.VISUAL_COLLECTION, points=points)


def search_visual(query: str, limit: int = config.TOP_K_VISUAL) -> list[dict]:
    if not config.VISUAL_ENABLED or not client().collection_exists(config.VISUAL_COLLECTION):
        return []
    qv = visual_model().embed_query(query)
    res = client().query_points(config.VISUAL_COLLECTION, query=qv.tolist(),
                                limit=limit, with_payload=True)
    return [{"score": p.score, "id": p.id, **(p.payload or {})} for p in res.points]


def rerank(query: str, candidates: list[dict], text_key: str = "text",
           top_k: int = config.TOP_K_FINAL) -> list[dict]:
    if not candidates:
        return []
    scores = list(reranker().rerank(query, [c[text_key] for c in candidates]))
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:top_k]


def chunk_text(doc_id: str, page: int) -> Optional[str]:
    """Dual-path join: fetch the text-index content of a page that the visual
    retriever matched by appearance (spec §3.4b)."""
    res, _ = client().scroll(
        config.TEXT_COLLECTION,
        scroll_filter=qm.Filter(must=[
            qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id)),
            qm.FieldCondition(key="page", match=qm.MatchValue(value=page)),
        ]), limit=1, with_payload=True)
    if res:
        return res[0].payload.get("text")
    # fall back to any chunk of the document (single-page docs)
    res, _ = client().scroll(
        config.TEXT_COLLECTION,
        scroll_filter=qm.Filter(must=[
            qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id)),
        ]), limit=1, with_payload=True)
    return res[0].payload.get("text") if res else None


# ---------------------------------------------------------------- region index
def load_regions() -> list[dict]:
    if config.REGION_INDEX_PATH.exists():
        return json.loads(config.REGION_INDEX_PATH.read_text())
    return []


def save_regions(regions: list[dict]):
    config.REGION_INDEX_PATH.write_text(json.dumps(regions))


def regions_for(doc_id: Optional[str] = None, tag: Optional[str] = None) -> list[dict]:
    out = []
    for r in load_regions():
        if doc_id and r["doc_id"] != doc_id:
            continue
        if tag and r.get("equipment_tag") != tag:
            continue
        out.append(r)
    return out
