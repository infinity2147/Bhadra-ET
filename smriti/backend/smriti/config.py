"""Central configuration for SMRITI. Everything overridable via env vars."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # smriti/
CORPUS_DIR = Path(os.environ.get("SMRITI_CORPUS", ROOT / "corpus"))
DATA_DIR = Path(os.environ.get("SMRITI_DATA", ROOT / "data"))   # indexes, graph, renders
GRAPH_PATH = DATA_DIR / "graph.json"
QDRANT_PATH = DATA_DIR / "qdrant"
RENDER_DIR = DATA_DIR / "renders"                    # page PNGs served to the UI
REGION_INDEX_PATH = DATA_DIR / "regions.json"
INGEST_LOG_PATH = DATA_DIR / "ingest_log.json"
ORG_MEMORY_PATH = DATA_DIR / "org_memory.json"

# LLM backend ---------------------------------------------------------------
# "cli"  -> claude CLI subprocess with subscription auth (default on this machine)
# "sdk"  -> anthropic SDK (requires ANTHROPIC_API_KEY)
LLM_BACKEND = os.environ.get("SMRITI_LLM_BACKEND",
                             "sdk" if os.environ.get("ANTHROPIC_API_KEY") else "cli")
MODEL_FAST = os.environ.get("SMRITI_MODEL_FAST", "claude-haiku-4-5-20251001")
MODEL_STRONG = os.environ.get("SMRITI_MODEL_STRONG", "claude-sonnet-5")

# Retrieval models ----------------------------------------------------------
DENSE_MODEL = "BAAI/bge-small-en-v1.5"               # 384-dim, fastembed ONNX
SPARSE_MODEL = "Qdrant/bm25"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
VISUAL_MODEL = os.environ.get("SMRITI_VISUAL_MODEL", "vidore/colSmol-256M")
VISUAL_ENABLED = os.environ.get("SMRITI_VISUAL", "1") == "1"

TEXT_COLLECTION = "text_chunks"
VISUAL_COLLECTION = "visual_pages"

TOP_K_TEXT = 12          # per retriever before rerank
TOP_K_VISUAL = 4
TOP_K_FINAL = 8          # evidence given to the answer model

for _d in (DATA_DIR, RENDER_DIR):
    _d.mkdir(parents=True, exist_ok=True)
