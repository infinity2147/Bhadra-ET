# SMRITI — System Handoff (for a fresh Claude context)

> Purpose: give another model the *complete, honest* picture of what SMRITI is,
> what a user sees on the frontend, how the backend actually works, and — most
> importantly — **exactly where the "demo" ends and "real product" begins**, so
> the next round of work targets the right gap. Grounded entirely in the code as
> of this commit; nothing here is aspirational unless explicitly flagged.

---

## 0. One-paragraph what-it-is

SMRITI ("स्मृति", memory) is an **industrial knowledge-intelligence platform** for
ET AI Hackathon 2026, Problem Statement 8. It fuses a plant's whole document
estate — P&ID drawings, work orders, SOPs, inspections, incidents/near-misses,
OEM manuals, permits, emails, and real Indian regulatory clauses — into **one
typed knowledge graph plus a tri-modal retrieval fabric** (text + graph + visual)
you can talk to. Five agents sit on top: Ingestion/KG, Expert Copilot,
Diagnostics/RCA, Compliance, and Lessons-Learned/Warnings. It runs fully local,
no Docker, no cloud, LLM via the `claude` CLI (subscription) or `ANTHROPIC_API_KEY`.

---

## 1. How to run it (verified)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd smriti
../.venv/bin/python scripts/gen_corpus.py                 # (re)build the document estate on disk
cd backend && ../../.venv/bin/python -m smriti.ingest      # build the fabric (add --no-visual to skip ColPali)
../../.venv/bin/python -m uvicorn smriti.api:app --port 8000
# open http://localhost:8000
```

- `corpus/` and `data/` are **git-ignored** — they must be regenerated on a fresh
  clone before the app has anything to show. `gen_corpus.py` writes `corpus/`;
  `python -m smriti.ingest` writes `data/` (graph + Qdrant + renders).
- Eval: `../../.venv/bin/python eval/harness.py` (writes `eval/results.json`).
- LLM auth: `llm.py` uses `ANTHROPIC_API_KEY` if set, else shells out to the
  local `claude` CLI headless (`claude -p --output-format json`). `MODEL_FAST =
  claude-haiku-4-5-20251001`, `MODEL_STRONG = claude-sonnet-5`.

---

## 2. What the user sees (frontend) — screen by screen

Vanilla JS/HTML/SVG PWA, **no build step**. Left sidebar nav + main column.
Files: [frontend/index.html](../frontend/index.html), `frontend/app.js`,
`frontend/style.css` (light theme, `--s1 #2a78d6` / `--s2 #1baf7a`). Assets are
cache-busted with `?v=N`; the server sends `no-cache` on `/static`, `/renders`, `/`.

| Nav item | View | What it shows | Backed by |
|---|---|---|---|
| **Ask** | `view-ask` | Streaming chat over the fabric. Answer streams token-by-token with inline `[c#]` citations; a **reasoning-trace** animates the real pipeline phases (Routing → Searching → Traversing graph → Reading drawings → Ranking → Answering); if a drawing is in evidence, a **Drawing Viewer** renders it with regions highlighted + feed path traced; citations click through to the exact source page. **Multi-turn** — follow-ups like "what about P-103?" are resolved against history. | `POST /api/ask` (SSE) → `copilot.ask()` |
| **Assets** | `view-assets` | Browsable list of every Equipment node → click one → composed **health view**: metadata, stats (WOs / breakdowns / inspections / incidents / last event), full **timeline**, governing regulations w/ status, and the P&ID it sits on with overlays. Cross-links to Diagnostics / Ask. | `GET /api/equipment`, `GET /api/equipment/{tag}/summary` |
| **Diagnostics** (was "Root Cause Analysis") | `view-rca` | Pick an asset (+ optional symptom) → **Analyze** → graph-native RCA: failure timeline, evidence-ranked causes (each citing WO/INSP/incident ids), **cross-asset pattern** across sister equipment (shared seal model / type), corrective + preventive actions, recurrence risk, confidence. | `POST /api/rca` → `rca.run_rca()` |
| **Warnings** | `view-warn` | **Proactive** warnings: upcoming permits (dated today/future) matched against precursor signatures mined from the plant's own incident history, with historical events attached. Plus systemic patterns + prevention priorities. | `GET /api/warnings`, `GET /api/patterns` → `lessons.py` |
| **Compliance** | `view-comp` | Register of **real** OISD / Factories Act / PESO clauses mapped to Unit-4 equipment, each evaluated against actual records (compliant / gap / overdue). "Generate audit pack" for a scope. | `GET /api/compliance/register`, `POST /api/compliance/audit-package` |
| **Evaluation** | `view-eval` | Measured metrics (faithfulness / citation-correctness / coverage), LLM-judged, SMRITI tri-modal vs a vanilla single-vector RAG baseline over the same corpus + model. | `GET /api/eval/latest` |
| **Add data** | `view-add` | Two cards: **New asset** form (register equipment) and **Upload document** dropzone (PDF/text). See §5 — this is where the demo-vs-real gap lives. | `POST /api/equipment`, `POST /api/ingest` |

---

## 3. Backend architecture — how it actually works

Package: `backend/smriti/`. FastAPI app in [api.py](../backend/smriti/api.py).

```
INGESTION (Agent 1, ingest.py + extraction.py)
  per-type parsers → typed nodes/edges + text chunks + visual pages
        │
        ▼
KNOWLEDGE STORE
  • Industrial Knowledge Graph — NetworkX (graph.py), typed ontology (ontology.py),
    Provenance{source_doc_id, page, bbox, extractor, confidence, effective_date}
    on every node/edge; SUPERSEDES version chains for SOPs.
  • Qdrant embedded (stores.py): TEXT collection (dense bge-small + sparse BM25),
    VISUAL collection (ColPali colSmol-256M multivector, MaxSim), regions index.
        │
        ▼
RETRIEVAL FABRIC (retrieval.py)
  contextualize (fast-model query rewrite for multi-turn)
   → intent router (haiku) → tri-modal fan-out:
       text: hybrid dense+BM25, RRF fusion
       graph: typed neighborhood traversal
       visual: colSmol late-interaction MaxSim over page images (OCR-FREE)
   → merge → cross-encoder rerank → provenance → drawing overlays
        │
        ▼
AGENTS
  2 copilot.py   — Expert Copilot (SSE streaming, evidence-constrained, cited, multi-turn)
  3 rca.py       — Diagnostics/RCA (graph-native, writes confirmed RCAs back as org memory)
  4 compliance.py— clause↔equipment mapping evaluated against records
  5 lessons.py   — cluster incidents → mine precursor signatures → match upcoming work
```

### The knowledge graph (`graph.py`, `ontology.py`)
- `KnowledgeGraph` wraps a NetworkX `MultiDiGraph`. `add_node`, `add_edge`,
  `node`, `nodes_by_type`, `edges_of`, `neighborhood(id, depth, edge_types)`,
  `stats()`, `save()` / load (pickled to `data/`).
- Node types (ontology): Equipment, Area, Person, Document, DrawingRegion,
  WorkOrder, Inspection, Incident, Procedure, RegulatoryClause, FailureMode,
  System, … Edge types: LOCATED_IN, DESCRIBED_BY, HAS_REGION, FEEDS_INTO,
  MAINTAINED_BY, INSPECTED_BY, INVOLVES, AUTHORED_BY, SUPERSEDES, GOVERNED_BY,
  SIMILAR_TO, HAS_FAILURE_MODE, CAUSED_BY, …
- **Records are separate nodes from documents**: e.g. a work order produces both a
  `Document` node `WO-…` and a `WorkOrder` record node `WO-…:rec`. The `:rec`
  node holds the structured fields; the `Document` node is what a citation points
  at. This `:rec` convention matters — see §5.

### Retrieval detail (`retrieval.py`)
- `contextualize(query, history)` — fast-model REWRITE resolves pronouns/ellipsis
  to a standalone question before retrieval (this is what makes multi-turn work).
- `retrieve(query, trace, history)` — routes intent, fans out to the three
  modalities, RRF-merges text, reranks with a cross-encoder, attaches provenance,
  and calls `build_overlays()` to map cited equipment/regions onto drawings.

### Copilot (`copilot.py`)
- `ask(query, stream_tokens=True, history=None)` yields `trace` events (one per
  pipeline phase, drives the animated loader), `delta` events (streamed answer
  tokens), and a `final` event (answer + citations + overlays). Answer is
  evidence-constrained; "insufficient evidence" is a first-class output.

### Compliance (`compliance.py`)
- `build_register(force)` joins `RegulatoryClause` nodes (via `GOVERNED_BY` edges)
  to their equipment and evaluates status against records. Cached to
  `data/compliance_register.json`. Real clauses w/ source URLs live in
  `corpus/regulatory/clauses.json`.

### Lessons / Warnings (`lessons.py`)
- `build_patterns()` embeds incident narrative+precursors, greedily clusters by
  cosine ≥ 0.72, writes learned `SIMILAR_TO` edges, and mines a
  `precursor_signature` per recurring cluster (strong model). Cached.
- `evaluate_upcoming()` finds permits dated ≥ today and asks the model whether
  each **re-assembles a known precursor signature** → warning with historical
  events + recommended action. **Reads the incident `precursors` field.**

---

## 4. Data flow: one "Ask" query, end to end
user query → `contextualize` (rewrite vs history) → intent router → {text hybrid,
graph traversal, visual MaxSim} in parallel → RRF merge → cross-encoder rerank →
provenance attached (doc, page, bbox, graph nodes) → answer streams with `[c#]`
citations → drawing overlays rendered if a drawing is in evidence → every step
emitted as a trace event to the UI and logged for eval.

---

## 5. ⚠️ THE DEMO-vs-REAL GAP (read this before planning next work)

This is the single most important section. The user's live question was: *"where
is the incident history coming from, how is it ingested, and how does NEW data
get in for real use?"*

### How the data you see today got in (demo path)
- All history is **generated** by `scripts/gen_corpus.py` into `corpus/*.json`.
- The high-signal records (incidents, work orders, inspections) are ingested by
  **direct JSON→typed-node maps with NO LLM** — [ingest_incidents](../backend/smriti/ingest.py#L266),
  [ingest_work_orders](../backend/smriti/ingest.py#L181),
  [ingest_inspections](../backend/smriti/ingest.py#L211). This is why they carry
  **complete structured fields** (`date`, `category`, `narrative`, `root_cause`,
  `precursors`, `actions`, `downtime_h`, `result`, …).
- The **timeline** shown in Diagnostics/Assets = [rca.failure_timeline()](../backend/smriti/rca.py#L55)
  walking `MAINTAINED_BY`/`INSPECTED_BY`/`INVOLVES` edges and **sorting the `:rec`
  nodes by their `date` field**. Nothing more.
- **Warnings** depend on the incident `precursors` field existing and being
  meaningful.

### How new data gets in today — and why it's not yet "real"
Two intake paths exist ([api.py](../backend/smriti/api.py)):

1. `POST /api/equipment` ("New asset" form) — adds an Equipment node with
   **metadata only**. No history, no incidents.
2. `POST /api/ingest` ("Upload document") — runs the file through **generic LLM
   extraction** ([extraction.py](../backend/smriti/extraction.py)). The schema
   prompt knows the *ontology* (node/edge types) but **not** the record-specific
   structured fields that `ingest_incidents`/`ingest_work_orders` populate.

**Consequence (the gap):** if someone uploads an incident-report PDF, the LLM may
create an `Incident` node, but it will **not reliably populate** `date`,
`category`, `precursors`, `root_cause`, nor create the `:rec` suffix node the
timeline expects. Therefore an uploaded incident **may not appear in the failure
timeline and almost certainly will not trigger a Warning** — because both read
exactly the fields the generic extractor doesn't guarantee. The upload path is
correct for the *unstructured long tail* (emails, manuals, scanned reports), but
it is **not** the right intake for the records that actually drive diagnostics and
foresight.

### ✅ STATUS: this gap is now CLOSED — see `intake.py`
The continuous-intake engine [backend/smriti/intake.py](../backend/smriti/intake.py)
was built to fix exactly this. Two runtime paths, both reusing one set of
materialisers that mirror the corpus mappers (same `:rec` node ids, same fields,
same edges), so a runtime record is indistinguishable from a build-time one:

1. **`ingest_document(doc_id, text, pages)`** — drop in ANY document. ONE
   strong-model call (`classify_and_extract`) BOTH classifies it (work_order |
   inspection | incident | permit | sop | equipment | oem_manual | regulatory |
   email | generic) AND extracts the type-appropriate structured fields. A
   type-specific materialiser then creates the correct typed `:rec` node + edges.
   Verified: an uploaded incident text → `Incident` node with `precursors`
   populated, appears in `failure_timeline`, `feeds_warnings: true`. Wired to
   `POST /api/ingest` (now **multi-file**: `files: list[UploadFile]`).
2. **`ingest_table(rows, rec_type)`** — the CMMS-export path. CSV/JSON of many
   records → column-mapped to fields (fuzzy header aliases in `_COLUMN_ALIASES`,
   handles SAP/Maximo headers like "WO No", "Functional Location", "Short Text"),
   materialised with **NO per-row LLM**. Verified: 2-row SAP-style CSV → 2
   WorkOrder `:rec` nodes on P-101, timeline grew 9→11, `last_event` updated.
   Wired to `POST /api/ingest/table?record_type=…`.

Unknown assets referenced by a record are auto-stubbed (`_ensure_equipment`) so a
record is never orphaned. SOP uploads auto-supersede the prior revision. Frontend
"Add data" view exposes both (multi-file dropzone with per-file "Detected: <type>
→ <id> — now in the timeline" results; bulk card with a record-type selector).

### Still open (next candidates, NOT built)
- **Human-in-the-loop review queue** for low-confidence classifications /
  rejected extractions (the `rejected` list exists in `extraction.py`).
- **Live CMMS connector** (poll SAP-PM/Maximo on a schedule) vs manual export upload.
- **Undo/versioning** on hand-entered records for auditability.
- **De-dup on re-upload** (same doc_id currently overwrites — usually fine, but
  bulk re-imports should be idempotent by record id).

---

## 6. Honest scoping already documented
- Hero P&IDs use authored **digitizer-output ground truth** (regions +
  connectivity); the production CV pipeline (symbol detection → tag association →
  line tracing) is specified in `docs/decisions.md`, not run at demo time. The
  long tail of drawings is covered by visual retrieval + page-region grounding.
- Graph store is NetworkX with a Neo4j-portable typed-ontology/provenance
  contract (8 GB demo machine); swap is a storage-layer change.
- Eval: aggregate deltas over vanilla RAG are modest and honest (same model +
  corpus); wins concentrate in multi-modal fusion, proactive warnings, and honest
  partial-evidence answers. Two stated caveats: the text-only judge can't score
  what drawing overlays show, and judge shares the answer model family.

---

## 7. Repository map
```
smriti/
├── backend/smriti/   config · llm · ontology · graph · stores · retrieval ·
│                     copilot · rca · lessons · compliance · ingest · extraction · api
├── frontend/         index.html · app.js · style.css (vanilla PWA, no build)
├── corpus/           GENERATED (git-ignored) — Refinery Unit 4 estate + real reg clauses
├── data/             GENERATED (git-ignored) — graph pickle + Qdrant + page renders
├── scripts/          gen_corpus.py · pid_svg.py · pdf_author.py · demo_prep.sh
├── eval/             golden_qa.json · harness.py · results.json
└── docs/             decisions.md · corpus-design.md · HANDOFF.md (this file)
```

---

## 8. State at handoff
- Fabric: ~318 graph nodes (clean; test node P-205 removed after verification).
- All 5 agents verified working live at `localhost:8000`.
- Repo: `github.com/infinity2147/Bhadra-ET`, branch `main`, clean history
  (venv/data/corpus git-ignored).
- **Open decision for the user:** which direction to take the "make it real"
  week — the strongest lever is §5.1 (structured intake for incidents/WOs/
  inspections), which is the exact gap the user identified.
```
