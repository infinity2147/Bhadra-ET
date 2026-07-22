# SMRITI — Engineering Decisions

This document records the component choices where the deployment environment or research
changed the default approach, with the rationale. Target environment: an Apple-Silicon
Mac, 8 GB RAM, no Docker daemon, no cloud API key required (the local `claude` CLI is
used when `ANTHROPIC_API_KEY` is not set). Every choice below is constrained by "must run
locally on a modest machine, no GPU."

| Component | Baseline approach | Decision | Why (verified) |
|---|---|---|---|
| **LLM access** | Strong LLM + small router LLM | `claude` CLI headless (`claude -p --setting-sources "" --output-format json/stream-json`) wrapping subscription auth; Anthropic SDK path behind `ANTHROPIC_API_KEY` for portability. Router: `claude-haiku-4-5`; extraction/answers: sonnet-tier (env-configurable). | Works with no API key; CLI verified incl. JSON + streaming. `--setting-sources ""` skips user hooks/plugins (27k→6.7k token overhead). |
| **Visual model** | ColQwen3 / ColModernVBERT + vLLM | **`vidore/colSmol-256M`** via `colpali-engine`, `torch==2.5.1` (MPS-safe), fp32/CPU or fp16/MPS | ColQwen3/colpali-v1.3 are 3–8B (~6–16 GB) — infeasible on 8 GB. colSmol-256M is the smallest officially supported ColPali-family model (~1 GB, <2 GB peak), Apache/MIT. vLLM has no macOS support. |
| **Vector store** | Qdrant / Milvus (server) | **Qdrant embedded local mode** (`QdrantClient(path=...)`) — multivector MaxSim, no Docker | No Docker daemon; embedded mode supports `MultiVectorComparator.MAX_SIM` (v1.10+). At ~300 pages the index is ~160 MB. |
| **Text embeddings** | dense + SPLADE/BM25 | fastembed: dense `BAAI/bge-small-en-v1.5` + sparse `Qdrant/bm25`; RRF fusion | Best small-model quality/speed on CPU; SPLADE++ measured ~3 s/doc on CPU (impractical). |
| **Reranker** | cross-encoder | fastembed `Xenova/ms-marco-MiniLM-L-6-v2` (~100–300 ms / 50 candidates, CPU) | bge-reranker-base is 1 GB and ~10× slower on CPU. |
| **Graph store** | Neo4j / Memgraph | **NetworkX MultiDiGraph** in-process, JSON-persisted, typed by the ontology layer | Neo4j = JVM + hundreds of MB RAM; the graph is well under 10k nodes and traversals are trivial in NetworkX. The ontology/provenance contracts are enforced in code, so the same contracts port to Neo4j in production. |
| **P&ID digitizer** | YOLO + Relationformer CV pipeline | Reference drawings are authored as SVG that emits pixel-exact DrawingRegion + connectivity ground truth, rendered to PNG for the visual index. The CV digitizer is the production path. | The authored regions are the same data contract a CV digitizer would emit; the long tail of drawings is covered by visual retrieval + page-region grounding. |
| **Evaluation** | RAG-eval library (ragas) | **Custom LLM-judge harness** (~150 lines): claim-level faithfulness + citation correctness + answer coverage, plus a vanilla-RAG baseline comparison | ragas drags in langchain and needs SDK auth; the judge runs over the same LLM client as the app. |
| **PDF / parsing** | pdfplumber | `pymupdf` (parse + `get_pixmap` render + PDF authoring), `pdfplumber` fallback for tables | 8–12× faster than pdfplumber, low RAM; also authors the reference corpus so ingestion parses real files rather than pre-baked JSON. |
| **Frontend** | React/Vue + bundler | Vanilla JS + SVG single-page PWA served by FastAPI (no build step) | SSE chat, the SVG Drawing Viewer and the trace panel don't need a framework; no build tooling to install or break. Mobile-first CSS. |

The regulatory corpus uses real clause text and identifiers researched from OISD /
Factories Act / PESO sources (see `corpus/regulatory/` with a source URL per clause).

Reference dataset design: [corpus-design.md](corpus-design.md).
