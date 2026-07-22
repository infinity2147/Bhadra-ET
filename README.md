# SMRITI — The Unified Asset & Operations Brain

**ET AI Hackathon 2026 · Problem Statement 8 — AI for Industrial Knowledge Intelligence**

> *Every plant already has the knowledge to prevent its next failure — it's trapped in
> twelve systems and three retiring engineers' heads. SMRITI (Sanskrit: स्मृति, "memory")
> is the brain that holds all of it: ask it in plain language, it answers on the drawing
> itself with citations you can trust, and it taps you on the shoulder before a failure
> pattern repeats. We didn't build a search box. We built the plant's institutional
> memory — one that never retires.*

This market was validated at **$3.1B** when Schneider Electric/AVEVA acquired Cognite
(June 2026). The incumbents are heavyweight, Western, enterprise-priced, 9–12-month
rollouts. SMRITI is a working slice that (a) reads the whole document estate **visually —
no OCR, drawings included**, (b) is **India-first** (real OISD / Factories Act / PESO
clauses), (c) turns the plant's own near-misses into **warnings before the next
incident**, and (d) **proves it works** — a live faithfulness dashboard against a
vanilla-RAG baseline.

---

## Submission deliverables (ET AI Hackathon 2026 · PS8)

| Deliverable | Where |
|---|---|
| **Working prototype** | `smriti/` — run it (below); live at `http://localhost:8000` |
| **Pitch deck** (10 slides, ~4–5 min) | [`docs/pitch-deck.html`](smriti/docs/pitch-deck.html) — open in a browser, press **F** for fullscreen; **P**→Ctrl/Cmd-P exports PDF |
| **Pitch + demo script** (timed) | [`docs/pitch-script.md`](smriti/docs/pitch-script.md) — slide narration + exact live-demo walkthrough |
| **Architecture diagram** | [`docs/architecture.html`](smriti/docs/architecture.html) — standalone, prints to one page |
| **Design decisions** (grounded) | [`docs/decisions.md`](smriti/docs/decisions.md) — every stack choice tied to research/constraints |
| **Corpus design** | [`docs/corpus-design.md`](smriti/docs/corpus-design.md) |
| **Full system handoff** (detailed) | [`docs/HANDOFF.md`](smriti/docs/HANDOFF.md) + [`docs/HANDOFF-2.md`](smriti/docs/HANDOFF-2.md) |
| **Evaluation** (reproducible) | `eval/golden_qa.json` · `eval/harness.py` · `eval/results.json` |
| **Demo video** | recorded from the deck + live prototype using the script above |

> To turn the deck / architecture into **PDF**: open the HTML in Chrome → Print → *Save as PDF*
> (deck is sized for landscape slides; architecture for one landscape page).

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION   mobile-first PWA · streaming chat · Drawing Viewer w/ live   │
│                overlays & feed tracing · reasoning-trace panel · dashboards │
├────────────────────────────────────────────────────────────────────────────┤
│ AGENTS         2 Expert Copilot   3 Maintenance/RCA                         │
│  (§5)          4 Compliance       5 Lessons-Learned + proactive monitor     │
│                1 Ingestion/KG     — all evidence-constrained, all cited     │
├────────────────────────────────────────────────────────────────────────────┤
│ RETRIEVAL      intent router (haiku) ──► ┌ text: hybrid dense+BM25 (RRF)    │
│ FABRIC (§3)                              ├ graph: typed traversal (IKG)     │
│                                          └ visual: ColPali late interaction │
│                merge ► cross-encoder rerank ► provenance ► drawing overlays │
├────────────────────────────────────────────────────────────────────────────┤
│ KNOWLEDGE      Industrial Knowledge Graph (typed ontology, provenance on    │
│ STORE          every node/edge, SUPERSEDES version chains)                  │
│                Qdrant embedded: text (dense+sparse) · visual (multivector   │
│                MaxSim) · DrawingRegion index (pixels ⇄ graph nodes)         │
├────────────────────────────────────────────────────────────────────────────┤
│ INGESTION      per-type parsers: CMMS structured map · layout-aware PDF ·   │
│                P&ID digitizer contract · scanned → visual-only · email →    │
│                LLM extraction vs typed schema · entity resolution           │
├────────────────────────────────────────────────────────────────────────────┤
│ SOURCES        P&IDs · work orders · SOPs (rev chains) · inspections ·      │
│                incidents/near-misses · OEM manuals (scanned) · permits ·    │
│                email · OISD/Factories-Act/PESO clauses (real, sourced)      │
└────────────────────────────────────────────────────────────────────────────┘
```

**One query, end to end:** user asks → router classifies intent & tags → tri-modal
fan-out → merge + rerank → provenance attached (doc, page, bbox, graph nodes) →
answer streams with inline `[c#]` citations → if a drawing is in evidence, the viewer
renders it with regions highlighted and the feed path traced → every step logged to
the reasoning trace and the eval harness.

## What makes it not-another-RAG-chatbot

1. **Tri-modal fusion** — the winning demo question (*"P-101 keeps tripping on high
   temperature — what feeds it, has this happened before, and what does the manual say
   to check?"*) needs the drawing graph (connectivity) **+** work-order history
   **+** a **visually retrieved** scanned OEM page, in one cited answer. A
   connectivity-only P&ID tool cannot produce it; neither can a text-only RAG.
2. **OCR-free visual retrieval across the whole corpus** — every page is indexed as an
   image (ColPali-family `colSmol-256M`, patch-level MaxSim in Qdrant). Scanned,
   stamped, skewed OEM pages and a real 1958 legacy drawing are retrieved on visual
   signal alone.
3. **The graph reasons across documents no human connects** — RCA walks
   `MAINTAINED_BY` / `INSPECTED_BY` / `SIMILAR_TO` edges to surface the monsoon seal
   pattern across **P-101, P-103 and P-107**, and the proactive monitor matches
   tomorrow's confined-space permit against near-miss precursor signatures from 2019
   and 2022 — a warning issued *before* the work.
4. **India-first regulatory intelligence** — 18 real clauses (OISD-STD-116/129/132/105,
   Factories Act 1948 §§31/36/36A/37/38/40, SMPV(U) 2016, Petroleum Rules 2002), each
   with its source URL and verbatim flag, mapped to equipment by `GOVERNED_BY` edges
   and evaluated against actual records. It even catches that the plant's own
   inspection plan assumes a 5-year interval where OISD-129 cl. 11.1 requires annual.
5. **Trust as a feature** — every sentence cites; citations click through to the exact
   page; confidence is scored; "insufficient evidence" is a first-class answer; and an
   eval dashboard shows measured faithfulness/citation-correctness vs a baseline.
6. **Built to be used, not just demoed** — the copilot is **multi-turn** (ask "why does
   P-101 fail?" then "what about P-103?" — the follow-up is resolved against the
   conversation via a fast-model query rewrite), and an **Asset Explorer** lets you
   browse every equipment item → its health timeline, governing regulations and the
   P&ID it sits on, with one-click jumps into RCA or the copilot. It's a navigable
   operations brain, not a search box.
7. **Built to run for years, not just to demo — continuous intake** (`intake.py`).
   A customer files new records every day, so the fabric grows continuously:
   - **Drop in any document** (one or many) and SMRITI **classifies each one
     itself** — work order, inspection, incident, permit, SOP, manual, regulation
     — and extracts it into the *same typed record the corpus build produces*. So
     an uploaded work order lands in the failure timeline, an incident's precursors
     feed Warnings, a new SOP revision supersedes the old one — not a dead
     "generic" node.
   - **Bulk CMMS import** — a CSV/JSON export from SAP&nbsp;PM / Maximo maps
     column→field (no per-row LLM), so *years* of work orders / inspections load in
     one shot.
   Unknown assets are auto-stubbed so nothing is orphaned; everything is indexed
   (text + visual, no OCR) and Warnings/Compliance recompute. This is Agent 1
   (§5.1) working incrementally, the way a plant actually runs it.

## Repository layout

```
smriti/
├── backend/smriti/      config · llm (CLI/SDK backends) · ontology · graph ·
│                        stores · retrieval · copilot · rca · lessons ·
│                        compliance · ingest · extraction · api
├── frontend/            vanilla-JS PWA (no build step)
├── corpus/              the fictional-but-coherent "Refinery Unit 4" estate
│                        (127 documents; real regulatory clauses with sources)
├── scripts/             gen_corpus.py · pid_svg.py · pdf_author.py
├── eval/                golden_qa.json (33 expert Q&As) · harness.py · results.json
└── docs/                decisions.md (grounded stack choices) · corpus-design.md
```

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # or use repo venv
cd smriti
../.venv/bin/python scripts/gen_corpus.py            # build the document estate
cd backend && ../../.venv/bin/python -m smriti.ingest # build fabric (add --no-visual for quick start)
../../.venv/bin/python -m uvicorn smriti.api:app --port 8000
# open http://localhost:8000  (phone: same LAN, http://<mac-ip>:8000)
```

LLM auth: uses `ANTHROPIC_API_KEY` if set, otherwise falls back to the local
`claude` CLI (Claude Code subscription). Eval: `python eval/harness.py`.

### Measured results (33-question golden set, LLM-judged)

| metric | SMRITI | vanilla RAG baseline |
|---|---|---|
| faithfulness | **96.6%** | 95.6% |
| citation correctness | **96.6%** | 95.3% |
| expected-point coverage | **86.4%** | 84.2% |

Both systems share the answer model and corpus, so aggregate deltas are honest and
modest; the fabric's wins concentrate where it should: **multi-modal fusion +15 pts,
proactive warnings +17 pts, honest partial-evidence answers +50 pts, RCA +5 pts**
coverage over baseline. Two caveats we state rather than hide: the text-only judge
cannot score what the drawing overlays show (the visual category under-credits
SMRITI), and judging uses the same model family as answering.

## Honest scoping

- Hero P&IDs carry digitizer-*output* ground truth authored with the drawings
  (the production CV pipeline — symbol detection → tag association → line tracing —
  is specified in `docs/decisions.md`); the long tail of drawings is covered by
  visual retrieval + page-region grounding.
- Graph store is NetworkX with the Neo4j-portable typed-ontology/provenance contract
  (8 GB RAM demo machine); swap is a storage-layer change.
- Scale path: MUVERA fixed-dim encodings + int8 for the multivector index,
  LazyGraphRAG-style incremental indexing, RBAC on the audit-logged tool bus.

## The 4-minute demo

1. **Cold open (30s)** — "$3.1B for Cognite last month; we built the sharper slice."
   Graph chip shows the fabric: ~300 nodes, ~440 edges, 126 chunks, 101 visual pages.
2. **The wow (45s)** — phone: ask the P-101 trip question → answer streams, D-CW-104
   lights up (CT-101 → STR-101 → P-101 traced), monsoon trip WOs cited, **scanned**
   BurgFlow troubleshooting page retrieved visually. Tap a citation → source page.
3. **The reasoning (45s)** — RCA tab on P-101 → failure timeline, evidence-ranked
   causes, **"same pattern on P-103 & P-107 — fleet-wide seal review"**.
4. **The foresight (45s)** — Warnings tab → *tomorrow's* TK-401 confined-space permit
   matches the 2019/2022 near-miss precursor signature (2 h purge vs 4 h minimum).
5. **The credibility (30s)** — Evals tab: SMRITI vs vanilla RAG, LLM-judged.
6. **The close (15s)** — Compliance tab: one-click OISD audit pack; gaps found include
   the PSV-1101 overdue test *and* the plant's own interval assumption contradicting
   OISD-129. "Institutional memory that never retires."
