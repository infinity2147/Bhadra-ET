# SMRITI — Technical Overview

*The Unified Asset & Operations Brain — a process plant's institutional memory that
reads its drawings, reasons across its history, proves its answers, and warns before
the next failure repeats.*

---

## 1. Overview

Every process plant already holds the knowledge to prevent its next failure. That
knowledge is fragmented across a dozen disconnected systems — the CMMS, the drawing
vault, the document-management system, inspection databases, incident logs, vendor
manuals, permit books and email — and, critically, in the experience of senior
engineers who are retiring.

**SMRITI** (Sanskrit: स्मृति, "memory") fuses that entire estate into **one typed
knowledge graph and a tri-modal retrieval fabric**. It answers questions in plain
language — on the drawing itself, with citations you can click through to the exact
source page — explains *why* an asset keeps failing, maps equipment to real regulations
and checks compliance against actual records, and turns the plant's own near-misses
into warnings issued **before** the work happens.

SMRITI runs **fully local** (no cloud dependency, no Docker required), so it fits an
air-gapped plant network.

## 2. The problem it solves

| Symptom | Consequence |
|---|---|
| **Siloed** — nothing is connected | The drawing showing what feeds a pump lives nowhere near that pump's failure history or the manual that says how to fix it. |
| **Undigitised** — the richest data is images | P&IDs and scanned OEM manuals are pictures; keyword search and text RAG are blind to them. |
| **Tribal** — memory walks out the door | When the engineer who "has seen this three times since 2019" retires, that pattern-recognition retires too. |
| **Reactive** — failures repeat | The same near-miss recurs because nobody connects tomorrow's permit to an incident three monsoons ago. |

## 3. What makes it different

Not another RAG chatbot. A single question fans out across three modalities — **text**,
a **knowledge graph**, and the **drawings themselves** — is fused and reranked, then
answered on the P&ID with inline citations. The signature question shows why one
modality is not enough:

> *"P-101 keeps tripping on high temperature — what feeds it, has this happened before,
> and what does the manual say to check?"*

Answering it requires **drawing connectivity** (what feeds P-101) **+** **work-order
history** (has this happened) **+** a **visually-retrieved scanned OEM page** (what to
check). A connectivity-only P&ID tool cannot produce it; neither can a text-only RAG.

- **Fusion** — three modalities, one cited answer.
- **Vision** — OCR-free visual retrieval across the whole corpus.
- **Reasoning** — the graph connects records no human links.
- **Trust** — every sentence cites; "insufficient evidence" is a valid answer.

## 4. System architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the diagram. The system is six layers,
all running in-process:

1. **Sources** — P&IDs, work orders (CMMS), SOPs with revision chains, inspections,
   incidents/near-misses, scanned OEM manuals, permits, email, and regulatory clauses.
2. **Ingestion (Agent 1)** — per-type parsers; LLM entity/relation extraction against
   the typed schema; entity resolution by canonical tag. **Continuous intake** adds
   structured forms, bulk CMMS import and auto-classifying upload at runtime.
3. **Knowledge store** — the Industrial Knowledge Graph (NetworkX, typed ontology,
   provenance on every node/edge, `SUPERSEDES` version chains) plus Qdrant embedded:
   text (dense bge-small + sparse BM25) and visual (colSmol-256M multivector, MaxSim),
   plus a DrawingRegion index joining pixels to graph nodes.
4. **Retrieval fabric** — intent router → text ‖ graph ‖ visual fan-out → RRF fusion →
   cross-encoder rerank → provenance + drawing overlays.
5. **Agents** — Expert Copilot, Diagnostics/RCA, Compliance, Lessons & Proactive
   Warnings — all evidence-constrained and cited.
6. **Interface** — a vanilla-JS PWA: streaming chat with `[c#]` citations, a Drawing
   Viewer with live overlays and feed-path tracing, a reasoning-trace panel, dashboards.

### One query, end to end

The router classifies intent and tags → tri-modal fan-out → merge + cross-encoder
rerank → provenance attached (doc, page, bbox, graph nodes) → the answer streams with
inline `[c#]` citations → if a drawing is in evidence, the viewer renders it with
regions highlighted and the feed path traced → every step is logged to the reasoning
trace and to the evaluation harness. The copilot is multi-turn: a follow-up such as
"what about P-103?" is resolved against the conversation via a fast-model query rewrite.

## 5. Knowledge graph & ontology

The graph is typed and provenanced. Node types include Equipment, Area, System, Person,
Document, DrawingRegion, WorkOrder, Inspection, Incident, Procedure, RegulatoryClause,
FailureMode and Parameter; edges include `FEEDS_INTO`, `LOCATED_IN`, `MAINTAINED_BY`,
`INSPECTED_BY`, `GOVERNED_BY`, `SIMILAR_TO`, `HAS_FAILURE_MODE`, `SUPERSEDES`,
`INVOLVES` and `AUTHORED_BY`.

A record and its citable document are **separate nodes**: a work order produces both a
`Document` node (the citation target) and a `WorkOrder` record node with a `:rec` suffix
holding the structured fields. Every node and edge carries a `Provenance` object
(`source_doc_id`, `page`, `bbox`, `extractor`, `confidence`, `effective_date`).

## 6. Tri-modal retrieval fabric

- **Text** — bge-small dense vectors + BM25 sparse, fused with Reciprocal Rank Fusion;
  semantics and exact-keyword both matter in a plant.
- **Graph** — neighborhood walks over typed edges surface connectivity and history no
  flat index holds (e.g. the fleet-wide seal pattern).
- **Visual** — every page embedded as an image (colSmol-256M, patch-level MaxSim);
  scanned, stamped and skewed pages are retrieved on visual signal alone, no OCR.
- **Fusion** — candidates merge and pass a cross-encoder reranker; provenance and
  drawing overlays are attached before answering.

## 7. The agents

| # | Agent | Responsibility |
|---|---|---|
| 1 | **Ingestion / KG** | Builds and grows the fabric — batch at install and incrementally at runtime. |
| 2 | **Expert Copilot** | Streaming, multi-turn, evidence-constrained Q&A with inline citations and drawing overlays. |
| 3 | **Diagnostics / RCA** | Graph-native root-cause: failure timeline, evidence-ranked causes citing record IDs, cross-asset patterns; confirmed RCAs written back as organisational memory. |
| 4 | **Compliance** | Maps real clauses to equipment and evaluates status against actual records; generates audit packs. |
| 5 | **Lessons & Proactive Warnings** | Clusters incidents, mines precursor signatures, matches upcoming permits against them — warning before the work. |

## 8. Continuous intake

A plant files new records every day, so intake is a first-class, always-on capability.
Its guiding rule is **graph parity**: a hand-entered record writes the *same graph
structure* (same `:rec` node IDs, node types, edges and field keys) as the batch
ingest — so a new record is instantly in timelines, analysable by RCA and eligible for
warning-matching, with **no restart and no re-ingest**.

- **Structured forms** — typed endpoints `/api/records/{incident,work-order,inspection,permit}`,
  stamped `manual_intake · confidence 1.0` for audit.
- **Bulk CMMS import** — a CSV/JSON export from SAP PM / Maximo maps column→field with
  no per-row LLM; years of history load in one operation.
- **Auto-classifying upload** — drop any document; one model call classifies it and
  extracts it into the correct typed record; the unstructured long tail (email, manuals)
  is text- and visually-indexed.

When an upcoming permit re-assembles the precursor signature of past incidents, the
Lessons agent fires a warning immediately — foresight from the plant's own history.

## 9. India-first regulatory intelligence

Eighteen real clauses — **OISD-STD-116/129/132/105**, **Factories Act 1948
§§31/36/37/38/40**, **SMPV(U) 2016**, **Petroleum Rules 2002** — each carrying its source
and a verbatim flag, mapped to equipment by `GOVERNED_BY` edges and evaluated against
actual records. SMRITI surfaces real gaps — for example, an inspection plan assuming a
5-year interval where OISD-129 requires annual, or a pressure-relief valve whose test is
overdue (OISD-132) — each cited to the clause, while the compliant majority remains
demonstrable.

## 10. Reference dataset

SMRITI ships with a coherent reference plant so the system is usable out of the box.
Equipment physics, failure modes and regulations are real (ISO-14224 failure taxonomy;
researched OISD/Factories Act/PESO clauses with sources); the plant, people and event
history are illustrative. Every document references the same tags, people and history so
the graph forms genuine cross-document links. See [corpus-design.md](corpus-design.md).

| Type | Count |
|---|---|
| P&IDs | 2 (SVG→PNG + curated DrawingRegion ground truth) |
| Work orders | 53 |
| Inspections | 23 |
| SOPs | 12 (with a rev-1→3 version chain) |
| Incidents / near-miss | 10 |
| OEM manuals | 3 (scanned-look, for visual retrieval) |
| Regulatory clauses | 18 (real text + source) |
| Email | 8 |
| Permits | 4 |

## 11. Evaluation

An LLM-judge harness scores claim-level faithfulness, citation correctness and
expected-point coverage over a golden question set, comparing SMRITI against a vanilla
single-vector RAG baseline that shares the same answer model and corpus — so the deltas
are honest.

| Metric | SMRITI | Vanilla RAG baseline |
|---|---|---|
| Faithfulness | **96.6%** | 95.6% |
| Citation correctness | **96.6%** | 95.3% |
| Expected-point coverage | **86.4%** | 84.2% |

Aggregate deltas are modest because both share the answer model; the fabric's wins
concentrate where it should — multi-modal fusion +15 pts, proactive warnings +17 pts,
honest partial-evidence answers +50 pts, RCA +5 pts coverage. Two stated caveats: a
text-only judge cannot score what the drawing overlays show (under-crediting the visual
answers), and judging uses the same model family as answering. Run it with
`python eval/harness.py`.

## 12. Engineering decisions

Every stack choice is tied to a verified constraint (target: an 8 GB machine, no Docker,
CPU/MPS only). Highlights — full rationale in [decisions.md](decisions.md):

- **Visual model** `colSmol-256M` — the smallest supported ColPali-family model (~1 GB),
  where 3–8B alternatives are infeasible on 8 GB.
- **Vector store** Qdrant embedded — multivector MaxSim without a Docker daemon.
- **Text** bge-small + BM25 with RRF; cross-encoder MiniLM reranker — best quality/speed on CPU.
- **Graph** NetworkX behind a Neo4j-portable typed-ontology/provenance contract.
- **LLM** Anthropic SDK (`ANTHROPIC_API_KEY`) or the local `claude` CLI; router on a fast
  model, extraction/answers on a strong model.
- **Frontend** vanilla JS + SVG PWA, no build step.

## 13. Production & scale

The graph layer ports directly to Neo4j (same typed-ontology/provenance contract) —
swapping the store is a storage-layer change. Scale path: MUVERA fixed-dimension
encodings + int8 for the multivector index, incremental indexing, and RBAC on an
audit-logged tool bus. The visual layer is production-ready; the CV digitizer
(symbol detection → tag association → line tracing) that produces connectivity ground
truth for new drawings is specified in [decisions.md](decisions.md). Roadmap also
includes a human-in-the-loop review queue for low-confidence extractions, a live CMMS
connector, and undo/versioning on hand-entered records.

## 14. Getting started

See the [README](../README.md) for full setup. In short:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd smriti && ../.venv/bin/python scripts/gen_corpus.py
cd backend && ../../.venv/bin/python -m smriti.ingest
../../.venv/bin/python -m uvicorn smriti.api:app --port 8000    # http://localhost:8000
```
