# SMRITI — Unified Asset & Operations Brain

**SMRITI** (Sanskrit: स्मृति, "memory") is an industrial knowledge-intelligence platform.
It fuses a process plant's entire document estate — P&ID drawings, work orders, SOPs,
inspections, incidents and near-misses, scanned OEM manuals, permits, email and
regulatory clauses — into **one typed knowledge graph and a tri-modal retrieval fabric**
you can query in plain language.

It answers **on the drawing itself, with citations you can click through to the source
page**, reasons across the plant's full history to explain *why* an asset keeps failing,
maps equipment to real Indian regulations (OISD / Factories Act / PESO) and evaluates
compliance against actual records, and converts the plant's own near-misses into
**warnings issued before the work happens**.

SMRITI runs **fully local** — no cloud dependency, no Docker required — so it fits an
air-gapped plant network.

---

## Key capabilities

- **Tri-modal retrieval** — every question fans out across **text** (hybrid dense + BM25),
  a **knowledge graph** (typed traversal), and the **drawings themselves** (OCR-free
  visual retrieval), fused and reranked into one cited answer.
- **OCR-free visual understanding** — every page is indexed as an image (ColPali-family
  `colSmol-256M`, patch-level MaxSim). Scanned, stamped and skewed manual pages and legacy
  drawings are retrieved on visual signal alone.
- **Graph-native diagnostics (RCA)** — walks maintenance, inspection and incident history
  plus sister equipment to surface cross-asset failure patterns, with every cause citing
  record IDs.
- **Proactive warnings** — mines precursor signatures from the plant's incident history and
  matches upcoming permits against them, warning *before* the job.
- **India-first compliance** — real OISD-STD-116/129/132/105, Factories Act 1948, SMPV(U)
  2016 and Petroleum Rules 2002 clauses (each with its source), mapped to equipment and
  evaluated against actual records.
- **Continuous intake** — log incidents / work orders / inspections / permits through typed
  forms, bulk-import CMMS exports (CSV/JSON), or drop any document and it self-classifies.
  New records are live instantly — in timelines, diagnostics, warnings and compliance —
  with **no restart or re-ingest**.
- **Trust as a feature** — every sentence cites; citations resolve to the exact page/region;
  "insufficient evidence" is a first-class answer; retrieval quality is measured against a
  baseline.

---

## Architecture

Diagram: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (PDF: `docs/architecture.pdf`).
Full technical write-up: [`docs/OVERVIEW.md`](docs/OVERVIEW.md) (PDF: `docs/OVERVIEW.pdf`).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ SOURCES     P&IDs · work orders · SOPs (rev chains) · inspections · incidents  │
│             OEM manuals (scanned) · permits · email · OISD/Factories-Act/PESO  │
├──────────────────────────────────────────────────────────────────────────────┤
│ INGESTION   per-type parsers · LLM entity/relation extraction · entity         │
│             resolution — plus continuous intake (forms · bulk CMMS · upload)   │
├──────────────────────────────────────────────────────────────────────────────┤
│ KNOWLEDGE   Industrial Knowledge Graph (typed ontology, provenance on every    │
│ STORE       node/edge, SUPERSEDES version chains)                              │
│             Qdrant embedded — text (dense + BM25) · visual (multivector MaxSim)│
│             · DrawingRegion index (pixels ⇄ graph nodes)                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ RETRIEVAL   intent router → text ‖ graph ‖ visual → RRF fusion →               │
│             cross-encoder rerank → provenance → drawing overlays               │
├──────────────────────────────────────────────────────────────────────────────┤
│ AGENTS      1 Ingestion/KG · 2 Expert Copilot · 3 Diagnostics/RCA ·            │
│             4 Compliance · 5 Lessons & Proactive Warnings                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ INTERFACE   streaming chat with [c#] citations · Drawing Viewer w/ live        │
│             overlays · reasoning-trace panel · dashboards (vanilla-JS PWA)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**One query, end to end:** the router classifies intent and tags → tri-modal fan-out →
merge + rerank → provenance attached (doc, page, bbox, graph nodes) → the answer streams
with inline `[c#]` citations → if a drawing is in evidence, the viewer renders it with
regions highlighted and the feed path traced.

---

## Requirements

- **Python 3.11+**
- ~2 GB free disk (models + indexes), 8 GB RAM
- An LLM backend, either:
  - the **Anthropic API** (`ANTHROPIC_API_KEY` set), or
  - the local **`claude` CLI** (Claude Code subscription) — used automatically if no key is set.
- No Docker, no GPU required (Apple-Silicon MPS used automatically if present).

## Installation & setup

```bash
git clone https://github.com/infinity2147/Bhadra-ET.git
cd Bhadra-ET
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Build the knowledge fabric from the bundled reference dataset:

```bash
cd smriti
../.venv/bin/python scripts/gen_corpus.py                 # generate the reference document estate
cd backend
../../.venv/bin/python -m smriti.ingest                   # build graph + text + visual indexes
#                                    add --no-visual for a faster first run (skips the visual index)
```

## Running

```bash
../../.venv/bin/python -m uvicorn smriti.api:app --port 8000
# open http://localhost:8000   (on the LAN / a phone: http://<host-ip>:8000)
```

## Configuration

Everything is overridable via environment variables (`smriti/backend/smriti/config.py`):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | if set, uses the Anthropic SDK backend |
| `SMRITI_LLM_BACKEND` | `sdk` if key set, else `cli` | `sdk` or `cli` (local `claude`) |
| `SMRITI_MODEL_FAST` | `claude-haiku-4-5-20251001` | router / query-rewrite model |
| `SMRITI_MODEL_STRONG` | `claude-sonnet-5` | extraction / answer / RCA model |
| `SMRITI_VISUAL` | `1` | set `0` to disable OCR-free visual retrieval |
| `SMRITI_VISUAL_MODEL` | `vidore/colSmol-256M` | visual retriever |
| `SMRITI_CORPUS` / `SMRITI_DATA` | `smriti/corpus` · `smriti/data` | source docs · indexes/graph/renders |

---

## Using SMRITI

| Surface | What it does |
|---|---|
| **Ask** | Streaming, multi-turn Q&A over the whole fabric, with inline citations and a live Drawing Viewer. |
| **Assets** | Browse every equipment item → composed health view: metadata, history timeline, governing regulations and the P&ID it sits on. |
| **Diagnostics** | Graph-native root-cause analysis — failure timeline, evidence-ranked causes, cross-asset patterns. |
| **Warnings** | Upcoming work matched against precursor signatures mined from incident history. |
| **Compliance** | Real regulatory clauses mapped to equipment and evaluated against records; one-click audit packs. |
| **Evaluation** | Retrieval/answer quality measured against a vanilla-RAG baseline. |
| **Add data** | Typed intake forms, bulk CMMS import, and auto-classifying document upload. |

### Adding your own data

- **Structured forms** (`Add data` → Incident / Work order / Inspection / Permit / Asset) —
  write typed records that are immediately live in timelines, diagnostics, warnings and compliance.
- **Bulk import** — a CSV/JSON export from SAP PM / Maximo / your CMMS; columns are mapped to
  typed records with no per-row LLM call.
- **Document upload** — drop any PDF/text; SMRITI classifies it and extracts it into the
  correct typed record, or indexes the unstructured long tail (email, manuals) for retrieval.

Hand-entered records carry provenance (`manual_intake`, confidence `1.0`) for audit.

---

## Evaluation

An LLM-judge harness scores claim-level faithfulness, citation correctness and expected-point
coverage against a golden question set, comparing SMRITI to a vanilla single-vector RAG
baseline over the same corpus and answer model.

```bash
../../.venv/bin/python eval/harness.py      # writes eval/results.json
```

| Metric | SMRITI | Vanilla RAG baseline |
|---|---|---|
| Faithfulness | **96.6%** | 95.6% |
| Citation correctness | **96.6%** | 95.3% |
| Expected-point coverage | **86.4%** | 84.2% |

Aggregate deltas are modest because both systems share the answer model; the fabric's wins
concentrate in multi-modal fusion (+15 pts), proactive warnings (+17 pts) and honest
partial-evidence answers (+50 pts). Stated caveats: a text-only judge under-credits the
visual answers, and the judge shares the answer model family.

---

## Project structure

```
smriti/
├── backend/smriti/   config · llm · ontology · graph · stores · retrieval ·
│                     copilot · rca · lessons · compliance · ingest · intake · api
├── frontend/         vanilla-JS PWA (no build step)
├── corpus/           reference document estate (generated by scripts/gen_corpus.py)
├── data/             graph + Qdrant indexes + page renders (generated by ingest)
├── scripts/          gen_corpus.py · pid_svg.py · pdf_author.py
├── eval/             golden_qa.json · harness.py · results.json
└── docs/             architecture · overview · decisions · corpus-design
```

## Documentation

- [`docs/OVERVIEW.md`](docs/OVERVIEW.md) — full technical overview (PDF: `docs/OVERVIEW.pdf`)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system architecture (PDF: `docs/architecture.pdf`)
- [`docs/decisions.md`](docs/decisions.md) — engineering decisions and their rationale
- [`docs/corpus-design.md`](docs/corpus-design.md) — the reference dataset

## Production & scale

The graph layer uses NetworkX behind a typed-ontology/provenance contract that ports directly
to Neo4j — swapping the store is a storage-layer change. Scale path: MUVERA fixed-dimension
encodings + int8 for the multivector index, incremental indexing, and RBAC on an
audit-logged tool bus. The P&ID visual layer is production-ready; the symbol-detection →
tag-association → line-tracing CV digitizer for connectivity ground truth is specified in
[`docs/decisions.md`](docs/decisions.md).
