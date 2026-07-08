# SMRITI — Grounded Implementation Decisions

The product spec is `../../read.md` (§ numbers below refer to it). This doc records only the
decisions where the real environment or research changed the spec's suggested stack, with the
evidence. Machine: Apple Silicon Mac, 8 GB RAM, 12 GB free disk, no Docker daemon, no API key,
Claude Code subscription auth available via `claude` CLI.

| Spec suggestion (§7) | Decision | Why (verified) |
|---|---|---|
| Strong LLM + small router LLM | `claude` CLI headless (`claude -p --setting-sources "" --output-format json/stream-json`) wrapping subscription auth. Router: `claude-haiku-4-5-20251001`; extraction/answers: sonnet-tier (env-configurable). SDK path kept behind `ANTHROPIC_API_KEY` for portability. | No API key, no `ant` CLI on machine; Python SDK auth fails; CLI verified working incl. JSON + SSE-style streaming. `--setting-sources ""` skips user hooks/plugins (27k→6.7k token overhead). |
| ColQwen3 / ColModernVBERT / Nemotron-ColEmbed + vLLM | **`vidore/colSmol-256M`** via `colpali-engine==0.3.17`, `torch==2.5.1` (MPS-safe pin), fp32/CPU or fp16/MPS | ColQwen3/colpali-v1.3/colnomic are 3–8B (~6–16 GB) — impossible on 8 GB. colSmol-256M is the smallest officially supported ColPali-family model (~1 GB, <2 GB peak), Apache/MIT. vLLM has no macOS support. Fallback if needed: fastembed `answerdotai/answerai-colbert-small-v1` (text-only late interaction, ONNX CPU). |
| Qdrant or Milvus (server) | **Qdrant embedded local mode** (`QdrantClient(path=...)`) — multivector MaxSim supported since v1.10, no Docker | Docker daemon not running; embedded mode verified to support `MultiVectorComparator.MAX_SIM`. At ~300 pages the index is ~160 MB — trivial. |
| Text embeddings + SPLADE/BM25 | fastembed: dense `BAAI/bge-small-en-v1.5` (0.067 GB) + sparse `Qdrant/bm25`; RRF fusion | Best small-model quality/speed on CPU; SPLADE++ measured ~3 s/doc on CPU (impractical). |
| Cross-encoder reranker | fastembed `Xenova/ms-marco-MiniLM-L-6-v2` (0.08 GB, ~100–300 ms / 50 candidates CPU) | bge-reranker-base is 1 GB and ~10× slower on CPU. |
| Neo4j or Memgraph | **NetworkX MultiDiGraph** in-process, JSON-persisted, typed by our ontology layer | Neo4j = JVM + hundreds of MB RAM; graph is <10k nodes at hackathon scale, traversals are trivial in NetworkX. The ontology/provenance contracts (§3.1) are enforced in our code, not the DB. Production path: same contracts on Neo4j. |
| P&ID digitizer (YOLO + Relationformer) | Hero drawings are **generated as SVG by our own script**, which emits pixel-exact DrawingRegion + connectivity ground truth; rendered to PNG for the visual index. CV digitizer described in architecture as the production path. | Spec §3.4c explicitly allows curated hero drawings ("Say so honestly; judges respect scoping"). Training/running detectors on 8 GB with no GPU in-scope time is not credible; hand-labeled regions are the same data contract the digitizer would emit. |
| RAG-eval library (ragas) | **Custom LLM-judge harness** (~150 lines): claim-level faithfulness + citation-correctness + answer relevance, Claude as judge, plus vanilla-RAG baseline comparison | ragas v0.4 drags langchain + needs SDK auth; our judge runs over the same CLI client. Metric definitions documented in eval/README. |
| PDFs / parsing | `pymupdf` (parse + `page.get_pixmap(dpi=150)` render + PDF *authoring* for the synthetic corpus), `pdfplumber` fallback for tables | 8–12× faster than pdfplumber, low RAM; also lets the corpus generator author real PDFs so ingestion is honest (parses real files, not pre-baked JSON). |
| Frontend framework | Vanilla JS + SVG single-page PWA served by FastAPI (no build step) | Node 25 exists but node_modules + build eats scarce disk; SSE chat, SVG overlay drawing viewer, and trace panel don't need React. Mobile-first CSS. |

Regulatory corpus (§5.4): real clause text/identifiers researched from OISD/Factories Act/PESO
sources (see `corpus/regulatory/` with source URLs per clause) — not invented.

Corpus design: `corpus-design.md`. Build order follows spec §9 phasing exactly.
