8 AI for Industrial Knowledge Intelligence: Unified Asset &
Operations Brain
Theme: Industrial Intelligence / Document Management / Knowledge Engineering / Quality
PROBLEM CONTEXT
A 2024 McKinsey global survey found that professionals in asset-intensive industries spend an average
of 35% of their working hours searching for information, clarifying instructions, or recreating
documents that already exist somewhere in the organisation. In India specifically, a NASSCOM-EY
study of manufacturing and energy companies found that the average large plant operates across 7
to 12 disconnected document systems — P&IDs and engineering drawings in one place, maintenance
work orders in another, operating procedures in a third, inspection records in a fourth, and regulatory
submissions scattered across email archives. BIS Research estimated that this fragmentation
contributes to 18–22% of unplanned downtime events in Indian heavy industry, as maintenance teams
make decisions without complete equipment history or failure pattern context. Then there is the
knowledge cliff: an estimated 25% of India's experienced industrial engineers and operators will retire
within the next decade, taking decades of undocumented operational knowledge with them. Once
gone, it cannot be recovered. Knowledge fragmentation in industrial operations is not a file
management problem. It is a safety problem, a quality problem, and an operational efficiency problem
— and it compounds over time. The organisations that solve it first will have a structural advantage in
how they operate, maintain, and improve their assets.
CHALLENGE STATEMENT
Build an AI-powered Industrial Knowledge Intelligence platform that ingests heterogeneous
documents — engineering drawings, maintenance records, safety procedures, inspection reports,
operating instructions, project files — across structured and unstructured formats, and makes their
collective intelligence queryable, actionable, and continuously updated at the point of need, across
any device or function.
WHAT YOU MAY BUILD
Participants may explore areas such as:
• Universal Document Ingestion & Knowledge Graph Agent — AI pipeline that processes
PDFs, P&IDs, scanned forms, spreadsheets, and email archives — extracting entities
(equipment tags, process parameters, regulatory references, personnel, dates) and building
a unified knowledge graph that maintains relationships across document types and updates
automatically as new records arrive.
• Expert Knowledge Copilot — RAG-powered conversational AI that answers operational,
maintenance, and engineering queries across the full document corpus — with source
citations, confidence scores, and direct links to the originating documents. Built to work on
mobile for field technicians, not just desktops for engineers.
• Maintenance Intelligence & RCA Agent — AI agent that fuses work order history,
equipment failure records, OEM manuals, inspection findings, and real-time operating
conditions to generate predictive maintenance recommendations, Root Cause Analysis (RCA)
support, and optimised maintenance schedules — reducing unplanned downtime by
connecting the dots that no individual team member can connect alone.
• Quality & Regulatory Compliance Intelligence — Agentic system that maps regulatory
requirements (Factory Act, OISD, PESO, environmental norms, quality standards) against
current procedures, equipment states, and inspection records — identifying compliance
gaps, auto-generating compliance evidence packages for audits, and flagging quality
deviations before they escalate.
• Lessons Learned & Failure Intelligence Engine — AI agent that analyses incident reports,
near-miss records, audit findings, and quality non-conformances across the organisation's
history and external industry databases — identifying systemic patterns invisible to any
individual review, and proactively pushing relevant warnings to operational teams before
similar conditions recur.
These examples are illustrative only.
SUGGESTED TECHNOLOGIES
• RAG (Retrieval-Augmented Generation) over heterogeneous industrial document corpora
• Knowledge Graphs & Industrial Ontology Engineering
• Computer Vision (P&ID parsing, drawing digitisation)
• OCR & Document Intelligence (structured + unstructured)
• Quality Management System (QMS) Integration
• Agentic AI for maintenance and compliance workflows
EXPECTED DELIVERABLES
• Working Prototype
• Architecture Diagram
• Presentation Deck
• Demo Video
Evaluation Focus Entity extraction accuracy across document types, query answer quality on domain-
expert benchmark questions, knowledge graph linkage completeness, time-to-answer versus traditional
search, compliance gap detection accuracy, and demonstrated improvement in cross-functional
knowledge discovery — ideally validated with real industrial document samples.
JUDGING CRITERIA
Criteria Weight
Innovation 25%
Business Impact 25%
Technical Excellence 20%
Scalability 15%
User Experience 15%

# SMRITI — The Unified Asset & Operations Brain
### Product Specification & Build Directive for Industrial Knowledge Intelligence
**ET AI Hackathon 2026 — Problem Statement 8**

> **Codename:** SMRITI (Sanskrit: स्मृति, "memory") — the plant's institutional memory that never retires. *(Renamed from an earlier working title "Cortex" to avoid a direct collision with SymphonyAI IRIS Foundry's knowledge graph, which is literally branded "Cortex" — see §1.5. Do a 60-second name sanity-check before finalising; alternatives: SUTRA, KOSH, GYAN.)*
> **One-line pitch:** *The living brain of an industrial plant — every drawing, work order, procedure, inspection report, and near-miss fused into one graph you can talk to, that shows you the answer on the drawing itself, and warns you before the failure repeats.*
> **Document type:** Full product + engineering specification. Written to be consumed directly by an AI build agent (Fable) and by the engineering team. Nothing here is aspirational hand-waving; every capability has a concrete pipeline, data model, and acceptance test.
> **Reading order for the build agent:** §1 → §2 → §3 (build the spine first) → §5 (agents) → §9 (phasing). Do not begin coding agents before the Knowledge Fabric (§3) exists.

---

## §0. How to use this document

This is a **directive spec**, not a brief. It is structured so an autonomous build agent can implement it section by section without needing to re-derive design decisions.

Each of the five sub-agents (§5.1–§5.5) is specified with a fixed schema:
- **Mandate** — the single sentence that defines the agent
- **Primary user & job-to-be-done**
- **Inputs / Outputs** (typed)
- **The Innovation** — what makes this non-obvious, i.e. the thing 90% of hackathon teams will *not* build
- **Pipeline** — step-by-step processing, with model/algorithm choices
- **Data contracts** — schemas the agent reads and writes
- **Interfaces** — API surface + UI surface
- **Failure & edge-case handling**
- **Acceptance tests** — what "working" means, measurable
- **Demo beat** — the exact moment this agent earns a reaction from a judge

Terminology: **Fabric** = the shared knowledge layer (§3). **Agent** = a reasoning worker that reads/writes the Fabric. **Grounding** = binding an answer to its exact source location (page region, drawing coordinate, graph node) so it can be cited and shown.

---

## §1. Vision & the winning thesis

### 1.1 The problem, restated sharply
Asset-intensive plants don't lack data — they drown in it, scattered across 7–12 disconnected systems (P&IDs, maintenance work orders, SOPs, inspection reports, regulatory submissions, email). Professionals lose ~35% of their working hours searching, clarifying, or recreating documents that already exist. Fragmentation drives ~18–22% of unplanned downtime, because a maintenance decision gets made without the equipment's full history in view. And a "knowledge cliff" looms: a large share of veteran engineers retire within the decade, taking undocumented know-how with them. **This is not a document-management problem. It is a safety, quality, and continuity problem, and it compounds.**

### 1.2 What everyone else will build (and why they lose)
The default 2026 hackathon answer to PS8 is: *"upload PDFs → chunk → embed → vector search → chat."* It works, it demos, and it finishes mid-pack — because it scores nothing on **Innovation (25%)**. It's a commodity. Judges have seen forty of them.

### 1.3 What SMRITI builds (and why it wins)
SMRITI treats the plant's knowledge as a **single living graph fused across three retrieval modalities**, and puts agents on top of it that don't just *answer* — they **show, reason, and warn**.

Three things make it categorically different from a RAG chatbot, and each maps directly to a judging axis:

1. **Tri-modal retrieval fabric** *(→ Technical Excellence)* — text semantic search **+** knowledge-graph traversal **+** *visual* document retrieval that reads drawings as images, no OCR. Most teams do one. We fuse three and let a router pick.
2. **Visual grounding — the answer lives on the drawing, fused with the history** *(→ Innovation, User Experience)* — the drawing-lookup alone is now a commodity (PNID.IO, DiagramIQ do it). SMRITI's edge is answering questions that need the drawing graph *and* the unstructured history *and* a visually-retrieved manual page *together*, all shown on the drawing with citations. See §1.5 and §5.2 for why this fusion is the defensible line.
3. **The graph reasons across documents no human connects** *(→ Business Impact)* — root-cause analysis and failure-pattern warnings that fuse a work order + an inspection finding + an OEM manual + a near-miss from three years ago. This is the anti-knowledge-cliff engine.

### 1.4 The sellable narrative (memorize this)
> *"Every plant already has the knowledge to prevent its next failure — it's just trapped in twelve systems and three retiring engineers' heads. SMRITI is the brain that holds all of it, that you can ask in plain language, that answers you on the drawing itself with a citation you can trust, and that taps you on the shoulder before a failure pattern repeats. We didn't build a search box. We built the plant's institutional memory — one that never retires."*

### 1.5 Competitive landscape — grounded, verified as of mid-2026 (read this before pitching)
**This is NOT a greenfield idea. It is a validated, actively-consolidating commercial category. Treat that as a weapon, not a wound — but never pretend the category doesn't exist, because a sharp judge knows it does.**

*Industrial platforms doing essentially this whole concept:*
- **Cognite** (Data Fusion unified data model + industrial knowledge graph + Atlas AI agentic layer) — **acquired by Schneider Electric / AVEVA for $3.1B, announced 30 June 2026.** Their thesis is verbatim ours: "industrial AI needs a unified, contextualized data foundation, not more models." Use this as your opening Business-Impact slide — the market was validated at $3.1B *last month*.
- **Siemens Industrial Copilot** — natural-language maintenance troubleshooting, Senseye predictive maintenance, nine copilots unveiled at CES 2026, Microsoft + NVIDIA "Industrial AI Operating System." Multimodal image analysis and agentic autonomy are on their *roadmap* (not broadly shipped) — that gap is your opening.
- **SymphonyAI IRIS Foundry** — Vision-AI P&ID digitization → asset hierarchy → knowledge graph they literally brand **"Cortex"** → RCA / fault tracing / agents. This is the closest match to our full stack (and the reason we renamed).
- **Acuvate DiagramIQ** and **PNID.IO** — P&ID → knowledge graph (Neo4j / DEXPI), conversational Copilot access, tags linked to SAP work orders and PI sensor values *on the drawing*. **PNID.IO's public marketing example is literally "What does Pump V-1005 feed into? — answered in seconds."** That is almost exactly our headline demo beat (§5.2). We must out-execute or re-angle it, not present it as invented.
- Also live: **iDrawings (IPS), ioMosaic SmartPFID, Cadmatic + Semantum** — all doing intelligent P&ID conversion.

*Enterprise knowledge-assistant platforms (the Copilot layer):* Glean ($7.2B, Enterprise Graph + Agents), Onyx (open-source, air-gapped), Cohere North, Writer (own Palmyra LLM + KG-RAG), Vectara, plus AWS Bedrock KB / Azure AI Search / Google Gemini Enterprise. Market ≈ $1.94B (2025) → ~$9.86B (2030). Table stakes here: hybrid retrieval, reranking, citations, permissions-aware access, multi-step agentic retrieval (Self-RAG/ReAct).

**So what is genuinely still open — where our differentiation is real, not imagined:**
1. **OCR-free visual late-interaction retrieval (ColPali family) across the *entire heterogeneous corpus*, not just P&IDs.** Incumbents do *structured* drawing digitization + *separate* text RAG. Reading every page — scanned forms, stamped inspection reports, dense drawings — as an image with patch-level MaxSim is still leading-edge and not what DiagramIQ/PNID.IO do. **Genuine technical edge (defensible, not a moat.)**
2. **Proactive precursor-warning loop (Agent 5).** Hindsight→foresight from the org's own near-misses. Siemens is heading here; few ship it. **Defensible as novel application.**
3. **India-first regulatory intelligence — the strongest wedge for *this* hackathon.** Every incumbent above is Western/generic. Native OISD / DGMS / Factory Act / PESO compliance mapping and audit-evidence generation is a real, unserved gap and it aligns perfectly with an Indian (ET) judging panel. **Lean into this hard.**
4. **Eval / faithfulness / audit-admissibility discipline.** MIT: ~95% of enterprise GenAI pilots never reach P&L impact; ~70% of RAG systems have no systematic eval. Showing a live faithfulness + citation-correctness dashboard vs a baseline is a maturity signal almost no hackathon team — and few products — demonstrate.
5. **Lean, open, low-cost, deployable in 15 days** vs $3.1B enterprise suites with 9–12-month rollouts.

**The honest pitch reframe (do NOT claim to have invented the plant brain):**
> *"This exact market was validated at $3.1 billion last month. But the incumbents are heavyweight, Western, enterprise-priced, and take 9–12 months to deploy. We built a working slice in 15 days that (a) reads the whole document estate visually — no OCR, drawings included, (b) is built India-first for OISD/Factory Act/DGMS compliance, (c) turns the plant's own near-misses into warnings *before* the next incident, and (d) we can prove it works — here's our faithfulness dashboard against a baseline. Not a demo that breaks under a real question."*

This reframe is stronger than "we invented X," because it is true, it shows you did your homework (judges reward that), and it converts the crowded market into evidence of demand.

---

## §2. System architecture (the whole picture)

SMRITI is a layered system. **Build bottom-up.** Everything above the Fabric is an agent that is meaningless without it.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PRESENTATION            Field mobile PWA · Engineer desktop · Command wall │
│                          Streaming answers · Drawing viewer w/ overlays     │
├──────────────────────────────────────────────────────────────────────────┤
│  AGENT LAYER (§5)                                                           │
│   1 Ingestion+KG   2 Expert Copilot   3 Maintenance/RCA                     │
│   4 Compliance     5 Lessons-Learned/Failure Intelligence                   │
│   ── all agents share the Orchestrator + Tool bus + Eval harness ──         │
├──────────────────────────────────────────────────────────────────────────┤
│  RETRIEVAL FABRIC (§3)   ┌ Text/semantic (dense+sparse hybrid)              │
│   "Tri-modal router" ────┼ Graph (entity/relation traversal, communities)  │
│                          └ Visual (ColPali-family late interaction, no OCR) │
│   + Reranker  + Grounding/provenance service  + Temporal versioning         │
├──────────────────────────────────────────────────────────────────────────┤
│  KNOWLEDGE STORE         Vector DB (multi-vector) · Graph DB · Object store │
│                          · Relational metadata · Drawing region index       │
├──────────────────────────────────────────────────────────────────────────┤
│  INGESTION PIPELINE (§3.4)  Parsers per type → entity/relation extraction   │
│                             → P&ID digitizer → embedders → graph builder    │
├──────────────────────────────────────────────────────────────────────────┤
│  SOURCES   PDFs · P&IDs/GA drawings · CMMS work orders · SOPs · inspection  │
│            reports · OEM manuals · near-miss/incident logs · email · Excel  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Data flow, one query, end to end:**
User asks → Orchestrator classifies intent → Tri-modal router fans out to text/graph/visual retrievers → results merged + reranked → Grounding service attaches provenance (doc id, page, region bbox, graph node ids) → answer LLM streams a response with inline citations → if a drawing is in the evidence set, the Drawing Viewer renders it with the relevant regions highlighted → every step is logged to the Eval harness.

---

## §3. The Knowledge Fabric — the spine (build this first)

This is 60% of the engineering value and the thing that makes every agent possible. **If the hackathon clock runs out, a superb Fabric + two agents beats a weak Fabric + five agents.**

### 3.1 The Industrial Knowledge Graph (IKG) — ontology
The graph is the heart. It is what lets SMRITI "connect dots no individual can connect." Define a **typed ontology** up front (do not let entities be free-text blobs).

**Node types (with key properties):**
- `Equipment` — tag (e.g. `P-101`), type, manufacturer, model, install_date, location/area, criticality, parent_system
- `System` / `Area` — hierarchical (Unit → System → Equipment), hazardous-area classification
- `Document` — id, type (P&ID, WO, SOP, inspection, OEM_manual, incident, permit, regulatory), version, effective_date, source_system
- `DrawingRegion` — parent Document, bbox coordinates, page, detected symbol class, linked Equipment tag *(this is what enables highlight-on-drawing)*
- `Procedure` — SOP steps, hazards, required permits
- `WorkOrder` — id, equipment, date, type (PM/CM/breakdown), findings, parts, labor, downtime
- `Inspection` — equipment, date, method, measurements, findings, pass/fail
- `Incident` / `NearMiss` — date, equipment/area, category, root cause, corrective actions
- `Failure Mode` — canonical (aligned to ISO 14224 / FMEA taxonomy where possible)
- `RegulatoryClause` — source (Factory Act, OISD, PESO, environmental, quality std), clause id, requirement text
- `Person` / `Role` — for knowledge attribution & the retiring-expert capture
- `Parameter` — process params (pressure, temp, flow) with units & normal ranges

**Edge types (the value is in the relationships):**
`FEEDS_INTO`, `PART_OF`, `LOCATED_IN`, `DESCRIBED_BY` (equipment→doc), `MAINTAINED_BY` (equipment→WO), `INSPECTED_BY`, `GOVERNED_BY` (equipment/procedure→regulatory clause), `HAS_FAILURE_MODE`, `CAUSED_BY`, `REMEDIED_BY`, `SIMILAR_TO` (incident↔incident, learned), `AUTHORED_BY`, `SUPERSEDES` (version chain), `REFERENCED_IN` (RFI/cross-doc).

> **Design rule:** Every fact SMRITI states must be traceable to at least one node or edge with a source Document + region. No ungrounded assertions. This is the trust layer and it is non-negotiable — it's also what makes intelligence packages audit-admissible (§5.4).

### 3.2 Tri-modal retrieval — the technical differentiator

**(a) Text / semantic retriever.** Hybrid dense + sparse. Dense embeddings (a strong general or domain-adapted embedding model) for semantic recall; BM25/SPLADE sparse for exact tag/part-number/clause-number matching (critical in industrial text where `P-101` vs `P-107` matters). Fuse via Reciprocal Rank Fusion. Chunk with **layout-aware, structure-preserving** chunking (tables and step lists kept intact — never blindly split a numbered SOP).

**(b) Graph retriever (GraphRAG).** Extract entities/relations at ingest, build the IKG, compute **hierarchical communities** for global/thematic questions and support **multi-hop traversal** for relational questions ("what else shares the cooling loop that feeds P-101?"). Use an efficient graph-RAG approach (LightRAG / LazyGraphRAG-style dual-level retrieval and cheap indexing rather than full community summarization on every ingest) so indexing stays hackathon-feasible; layer an **agentic graph-search** loop for deep multi-hop queries. For professional-domain grounding, a KAG-style (knowledge-augmented) approach that mixes graph structure with text keeps answers precise.

**(c) Visual retriever (the crowd-beater).** Use a **ColPali-family late-interaction visual retriever** (e.g. ColQwen3 / ColModernVBERT for efficiency, or Nemotron-ColEmbed tier for accuracy). Each page/drawing is rendered as an image and encoded into **patch-level multi-vector embeddings**; query-to-page relevance is scored with **MaxSim late interaction** — *no OCR*, so tables, stamps, dense P&IDs, and handwritten annotations that OCR destroys are retrieved on their visual signal. This is what lets SMRITI retrieve *the right drawing* reliably.
- **Scaling note for the team:** multi-vector storage is heavy (~1k patch vectors/page). For the hackathon corpus size this is fine on a single GPU; if scale is demoed, mention **MUVERA** (fixed-dimensional encodings so multi-vector can ride standard ANN) and int8 quantization as the production path. Use a vector DB with native multi-vector/MaxSim support (Qdrant or Milvus).

**(d) The router.** A lightweight intent classifier (LLM or trained head) routes each query: factual-lookup → text; relational/"how are these connected"/RCA → graph; "show me / where on the drawing / visual" → visual; complex → **all three in parallel, then merge**. Merge → cross-encoder **rerank** → dedupe by provenance. The router decision is logged and shown in a "reasoning trace" panel (great for the demo — judges *see* the system think).

### 3.3 Visual grounding & the Drawing Viewer *(innovation centerpiece)*
This is the feature that wins the room. Two layers:

1. **Page-region grounding via late interaction.** Because ColPali-style models keep per-patch embeddings, we know *which patches* of a page matched the query. Propagate patch relevance → region (recent "patch-to-region relevance propagation" work does exactly this) → draw a highlight box on the rendered page. Effect: the answer *and* the exact spot it came from, on any document, for free from the retriever we already run.
2. **Structured P&ID grounding via the digitizer (§3.4c).** For P&IDs specifically, we don't stop at a highlight — we have the *graph* of the drawing (symbols, tags, line connectivity). So "what feeds P-101" traces `FEEDS_INTO` edges and highlights the actual upstream equipment and connecting lines on the drawing. This is the "operations brain," not a viewer.

**Drawing Viewer component:** renders drawing (image or vector), overlays (a) retrieval highlight boxes, (b) clickable equipment tags that open that equipment's full graph neighborhood (all its WOs, inspections, incidents, governing clauses), (c) animated connection tracing. Clicking any highlighted element = instant context. This single component demonstrates all three innovations at once.

### 3.4 Ingestion pipeline (per-type, not one-size-fits-all)
A generic "PDF → text" loader is why most RAG systems are mediocre on industrial docs. Route by type:

- **(a) Text/office docs (SOPs, reports, manuals, email, Excel):** layout-aware parse → structure-preserving chunk → entity/relation extraction (LLM with a typed-schema prompt aligned to §3.1) → embed → write nodes/edges. Tables extracted as structured rows, not flattened strings.
- **(b) Scanned/mixed PDFs:** dual-path — index the page **visually** (ColPali, no OCR) *and* run OCR for the text index, so both retrievers can hit it. This redundancy is cheap insurance.
- **(c) P&IDs / engineering drawings (the hard, differentiating path):**
  1. **Symbol detection** — object detector (YOLO-family / keypoint-based) trained/fine-tuned on a symbol set (bootstrap from public P&ID datasets such as PID2Graph; augment with synthetic symbols).
  2. **Text/tag detection & association** — detect tag text, associate each tag to its nearest symbol.
  3. **Line/connection detection** — trace pipe/signal lines and reconstruct **connectivity**; a transformer relation approach (Relationformer-style) or detector + graph-search yields the topology directly as a graph.
  4. **Emit** `Equipment` + `DrawingRegion` nodes and `FEEDS_INTO`/`PART_OF` edges into the IKG, each region carrying page + bbox for the viewer.
  > For hackathon scope, it's acceptable to run full structural parsing on a **curated set of hero drawings** used in the demo, and fall back to visual-retrieval-only grounding on the long tail. Say so honestly; judges respect scoping, not fakery.
- **(d) CMMS/structured data (work orders, inspections):** map directly to typed nodes/edges; these are your highest-signal RCA fuel.

### 3.5 Trust, provenance & versioning (the enterprise-grade layer)
- **Citations everywhere:** every answer sentence carries source Document id + region/node ids; UI renders click-through citations. No citation → the sentence is flagged low-confidence.
- **Confidence scoring:** combine retrieval score + reranker score + answer-model self-consistency; surface a confidence badge.
- **Temporal versioning (anti-knowledge-cliff):** documents carry `effective_date` + `SUPERSEDES` chains, so SMRITI answers "what is the *current* procedure" correctly and can show how a procedure evolved — capturing institutional change over time.
- **Hallucination guardrail:** answers are constrained to retrieved evidence; an "insufficient evidence" response is a first-class, *good* outcome, not a failure.

### 3.6 Evaluation harness (your unfair advantage — build it early)
You have production RAG experience; **make the eval harness visible in the demo** — it signals real engineering maturity that hackathon teams almost never show.
- **Retrieval metrics:** recall@k, MRR, NDCG per modality; a "which modality won" breakdown.
- **Answer metrics:** faithfulness/groundedness (is every claim supported by retrieved evidence?), answer-relevance, citation-correctness.
- **Domain benchmark:** hand-craft a **golden set** of ~40–60 domain-expert Q&A pairs over your corpus (§8), including hard multi-hop and drawing questions. Report scores live.
- **Baseline comparison:** show SMRITI vs a naive vanilla-RAG baseline on the same golden set. The delta *is* your Technical Excellence argument.

---

## §4. Cross-cutting agent infrastructure

All five agents share one substrate — build it once:

- **Orchestrator:** receives a user goal, decomposes into sub-tasks, selects agents/tools, manages a shared scratchpad, streams intermediate reasoning to the UI. Use a plan-act-observe loop; expose the plan as a visible "reasoning trace."
- **Tool bus:** typed tools every agent can call — `retrieve(query, modality)`, `graph_query(cypher/traversal)`, `get_equipment_context(tag)`, `get_drawing_regions(doc, tag)`, `cite(node_ids)`, `write_finding(...)`. Agents never touch stores directly; they go through tools (keeps everything logged + eval-able).
- **Streaming:** token streaming + step streaming (the user watches the router pick modalities, the graph get traversed, the drawing get highlighted). Streaming is a UX weapon — it turns a 6-second wait into a "watch it think" moment.
- **Memory:** per-session conversational memory + a long-term "org memory" (resolved RFIs, confirmed RCAs) that feeds back into the Fabric so SMRITI gets smarter with use.
- **Guardrails & RBAC:** role-aware answers (a field tech and a plant manager see appropriately scoped context); safety-critical answers always show the governing regulatory clause.

---

## §5. The five sub-agents — full specifications

### §5.1 Agent 1 — Universal Ingestion & Knowledge Graph Agent
**Mandate:** Turn any heterogeneous document into typed, linked, grounded knowledge in the IKG — automatically, continuously, and with provenance.

- **Primary user:** the system itself + a knowledge admin who curates.
- **Job-to-be-done:** "Make everything we own instantly queryable and connected, and keep it current as new records arrive."
- **Inputs:** PDFs, P&IDs/drawings, scanned forms, spreadsheets, CMMS exports, email archives, OEM manuals.
- **Outputs:** IKG nodes/edges, multi-vector visual index entries, text chunks + embeddings, DrawingRegion index, ingest report (what was extracted, confidence, unresolved entities).

**The Innovation:** it is *multimodal and graph-building*, not a loader. It produces a **connected graph with drawing-level grounding**, resolves entities across documents (the `P-101` in a work order is *the same node* as the `P-101` symbol on the P&ID), and updates incrementally with version chains. Almost no team will build cross-document entity resolution or P&ID→graph.

**Pipeline:**
1. Classify document type → route to the correct parser (§3.4).
2. Extract text/layout/tables; for drawings run the digitizer (symbols → tags → connections → subgraph).
3. **Entity & relation extraction** with a typed-schema LLM prompt (schema = §3.1). Enforce the ontology; reject/queue free-text entities that don't map.
4. **Entity resolution / canonicalization** — link mentions of the same equipment/system/clause across documents into single nodes (tag normalization + embedding similarity + LLM adjudication for ambiguous cases).
5. **Write** to graph + vector + region stores; attach provenance (doc, page, bbox) to every node/edge.
6. **Version reconciliation** — detect supersession (new SOP rev) → set `SUPERSEDES`, adjust `effective_date`.
7. Emit ingest report + confidence; low-confidence items go to a human-review queue.

**Data contracts:** writes all node/edge types (§3.1); each carries `{source_doc_id, page, bbox?, extractor, confidence, effective_date}`.

**Interfaces:** `POST /ingest` (file → job), `GET /ingest/{job}` (status + report), admin review UI (accept/merge/split entities — every correction improves resolution).

**Edge cases:** low-res scans (fall back to visual-only index + flag), conflicting facts across docs (keep both, link with `SUPERSEDES`/`CONFLICTS_WITH`, surface conflict to user rather than silently picking), unknown symbols (log to review, still index visually).

**Acceptance tests:** entity-extraction precision/recall vs a hand-labeled subset; cross-document entity-resolution accuracy (does `P-101` unify?); P&ID connectivity F1 on hero drawings; ingest of a *new* revision correctly supersedes the old.

**Demo beat:** drop a messy folder (a P&ID + 3 work orders + an SOP + an email) → watch the graph *assemble live* as nodes and edges appear and the pump on the drawing lights up linked to its work-order history. "That folder just became a brain."

---

### §5.2 Agent 2 — Expert Knowledge Copilot
**Mandate:** Answer any operational, maintenance, engineering, or compliance question across the entire corpus — with citations, confidence, and, where relevant, the answer shown *on the drawing* — on mobile for the field and desktop for the office.

- **Primary user:** field technician (mobile), engineer, operator, shift supervisor.
- **Job-to-be-done:** "Get me the exact, trustworthy answer from all our documents in seconds, not a 40-minute search."
- **Inputs:** natural-language query (typed or voice), optional context (my equipment, my location, my role).
- **Outputs:** streamed grounded answer, inline click-through citations, confidence badge, drawing overlay when relevant, "related" graph neighborhood, suggested follow-ups.

**The Innovation:** the **tri-modal router + visual grounding**, and — critically — a question that a P&ID-graph tool *alone cannot answer.* Connectivity-only tools (PNID.IO, DiagramIQ) can tell you what a pump feeds, because that's in the drawing graph. SMRITI's edge is **fusing the drawing graph with the unstructured history**: it answers "what feeds this and *why does it keep failing and what did we do last time*," pulling connectivity from the graph, failure history from work orders, the fix from an OEM manual page retrieved *visually*, and a governing safety clause — in one cited, streamed answer, shown on the drawing. The differentiator is the *fusion across modalities*, not the drawing lookup (which is now commoditised).

**Pipeline:**
1. Intent classify → router picks modality/modalities (§3.2d).
2. Retrieve (parallel fan-out) → merge → rerank → attach provenance.
3. If drawing evidence present → resolve DrawingRegions → prepare overlay payload.
4. Answer LLM generates response **constrained to retrieved evidence**, emitting inline citation markers bound to node/region ids.
5. Stream tokens + step trace; render citations + overlay; compute confidence.
6. If evidence insufficient → say so, show closest partial matches, offer to widen search. (A confident "I don't have that" beats a confident wrong answer — and demos as trustworthiness.)

**Interfaces:** `POST /ask` (SSE stream), `GET /citation/{id}` (opens source at region), `GET /equipment/{tag}/context`. UI: chat + Drawing Viewer + citation drawer + reasoning-trace panel.

**Edge cases:** ambiguous tag ("the pump" — ask which, or show candidates), out-of-corpus question (decline + offer web/OEM if configured), conflicting sources (present both with versions), voice in noisy plant (confirm transcription before acting).

**Acceptance tests:** golden-set answer accuracy + faithfulness; citation-correctness (does the cited region actually support the claim?); time-to-answer vs traditional search (target: seconds vs minutes — measure it); drawing-overlay correctness on hero drawings.

**Demo beat:** on a phone, voice-ask *"P-101 keeps tripping on high temperature — what feeds it, has this happened before, and what does the manual say to check?"* → the answer streams: the P&ID appears with P-101 and its upstream cooling-water source highlighted and the feed line traced (graph); a cited line reads "same high-temp trip logged twice last monsoon (WO-4471, WO-4620) — root cause: fouled cooler" (history); a **visually-retrieved OEM manual page** is shown with the exact checklist region highlighted — *no OCR* (visual); and a governing safety note is cited. Tap any citation → the source opens at the exact spot. **This is the winning 30 seconds — and no connectivity-only competitor can produce it, because it needs all three modalities fused.**

---

### §5.3 Agent 3 — Maintenance Intelligence & RCA Agent
**Mandate:** Fuse work-order history, failure records, OEM manuals, inspection findings, and current operating conditions to explain *why* something failed and *what to do*, and to schedule maintenance smarter — connecting dots no single technician can.

- **Primary user:** maintenance planner, reliability engineer, technician mid-job.
- **Job-to-be-done:** "Don't just tell me it failed — tell me why, whether it'll happen again, and what to do, using everything we know."
- **Inputs:** equipment tag or symptom, optional live conditions; reads WO/inspection/incident/OEM/parameter nodes.
- **Outputs:** structured **RCA** (failure mode → probable causes ranked with evidence → recommended corrective + preventive actions), predicted recurrence risk, optimized maintenance recommendation, all cited to source records.

**The Innovation:** **graph-native root-cause reasoning.** It doesn't retrieve a paragraph; it walks `Equipment → HAS_FAILURE_MODE → CAUSED_BY → REMEDIED_BY` and `SIMILAR_TO` edges across the entire history + external failure taxonomies (ISO 14224/FMEA) to produce a *reasoned, evidence-ranked* RCA. It surfaces patterns like "this bearing fails every monsoon season across 4 similar pumps" that are invisible to anyone reading one work order.

**Pipeline:**
1. Resolve target equipment + pull its full graph neighborhood (WOs, inspections, incidents, failure modes, similar assets).
2. Assemble a **failure timeline** from WO/inspection dates + findings.
3. Hypothesize causes: LLM reasons over the neighborhood + FMEA taxonomy → candidate causes.
4. **Evidence-rank** each cause by supporting records (frequency, recency, similarity to prior confirmed RCAs).
5. Cross-asset pattern check via `SIMILAR_TO` (same failure on sister equipment?).
6. Recommend corrective + preventive actions (pull from OEM manuals + prior successful remedies); estimate recurrence risk.
7. Emit structured, cited RCA; optionally write a confirmed RCA back to the Fabric (org memory).

**Interfaces:** `POST /rca` (tag/symptom → RCA object), `GET /equipment/{tag}/health` (timeline + risk), `POST /maintenance/optimize` (schedule suggestion). UI: RCA report with expandable evidence, failure timeline, cross-asset pattern callout.

**Edge cases:** sparse history (state low confidence, lean on OEM + taxonomy), conflicting past RCAs (show both + outcomes), novel failure (no precedent → reason from first principles + flag as new pattern to capture).

**Acceptance tests:** RCA quality vs reliability-engineer baseline on seeded cases; does it recover the *known* root cause on planted scenarios; cross-asset pattern detection recall; recommendation usefulness rating.

**Demo beat:** "Why does P-101 keep failing?" → SMRITI lays out a timeline, ranks "monsoon-season seal degradation" as the top cause with 3 cited work orders, then adds: *"the same pattern appears on P-103 and P-107 — recommend fleet-wide seal upgrade."* A dot no human connected.

---

### §5.4 Agent 4 — Quality & Regulatory Compliance Intelligence
**Mandate:** Continuously map regulatory and quality requirements (Factory Act, OISD, PESO, environmental norms, quality standards) against current procedures, equipment states, and inspection records — find gaps *before* an audit, auto-assemble audit evidence packages, and flag quality deviations before they escalate.

- **Primary user:** compliance officer, quality manager, plant manager, auditor.
- **Job-to-be-done:** "Tell me where we're non-compliant before the auditor does, and hand me the evidence pack."
- **Inputs:** regulatory corpus + current procedures/equipment/inspection state; audit scope selection.
- **Outputs:** compliance gap register (clause → requirement → current state → gap → severity → recommended action), auto-generated **audit evidence package** (clause-by-clause with cited source documents), quality-deviation alerts.

**The Innovation:** **requirement-to-reality graph mapping.** Regulatory clauses are nodes; `GOVERNED_BY` edges link them to the equipment/procedures they constrain. The agent evaluates *satisfaction* of each clause against actual records and produces a live, cited gap register — and, on demand, an **audit-ready evidence package** assembled automatically. Turning a weeks-long manual audit prep into minutes is a razor-sharp Business Impact story.

**Pipeline:**
1. Ingest & structure the regulatory corpus into `RegulatoryClause` nodes (requirement text + applicability rules).
2. Map clauses → governed equipment/procedures via `GOVERNED_BY` (LLM + rules).
3. For each clause, gather evidence of compliance (procedures, inspection records, certificates, permits) via graph + retrieval.
4. **Evaluate satisfaction:** satisfied / partial / gap / expired — with reasoning + citations.
5. Rank gaps by severity (safety-critical first) + regulatory exposure.
6. On "prepare for audit": assemble clause-by-clause evidence package (PDF/report) with every citation resolved.
7. Continuous mode: re-evaluate on new ingest; alert on new gaps or expiring certificates.

**Interfaces:** `GET /compliance/register`, `POST /compliance/audit-package` (scope → document), `GET /compliance/gaps?severity=`. UI: gap register (filter by standard/severity), clause detail with evidence, one-click evidence-pack export.

**Edge cases:** ambiguous applicability (flag for review, don't guess), missing evidence (that *is* the gap — report it), expired certificates (time-aware alerts), overlapping standards (dedupe requirements, note the strictest).

**Acceptance tests:** gap-detection accuracy vs planted non-compliances; evidence-package completeness (every claimed-satisfied clause has a real cited source); false-positive rate (compliance flagged as gap) kept low.

**Demo beat:** "Prepare us for an OISD audit on the fuel storage area" → a cited, clause-by-clause evidence pack generates in seconds, and the register flags *"3 gaps: fire-drill record expired, one relief-valve inspection overdue"* — each linked to the source. "That's a week of a compliance officer's work, done live."

---

### §5.5 Agent 5 — Lessons-Learned & Failure Intelligence Engine
**Mandate:** Analyze incident reports, near-misses, audit findings, and quality non-conformances across the org's full history *and* external industry databases to find systemic patterns invisible to any single review — and **proactively push relevant warnings to teams before similar conditions recur.**

- **Primary user:** safety/reliability leadership, plant manager, operators (as alert recipients).
- **Job-to-be-done:** "Make sure we never repeat a failure we've already seen — and warn the crew *before* it happens again."
- **Inputs:** incident/near-miss/audit/NCR corpus + external industry incident references; current operating context for proactive matching.
- **Outputs:** systemic pattern reports, ranked prevention priorities, and **proactive contextual warnings** ("conditions now resemble the precursors of incident INC-2019-14").

**The Innovation:** it's **proactive and cross-corpus**, closing the loop from hindsight to foresight. It clusters incidents by latent pattern (not just keyword), links them via learned `SIMILAR_TO` edges, mines precursor signatures, and — the differentiator — **monitors current conditions and pushes a warning when a known precursor pattern reassembles.** This is the literal antidote to "data present, but unacted upon."

**Pipeline:**
1. Normalize all incidents/near-misses/NCRs into structured `Incident` nodes (category, equipment/area, root cause, corrective actions, precursors).
2. **Cluster** by semantic + structural similarity → identify systemic patterns; write `SIMILAR_TO` edges.
3. **Precursor mining:** for recurring patterns, extract the conditions/sequence that preceded them.
4. Cross-reference external industry incident databases for patterns not yet seen internally (learn from others' failures).
5. Rank prevention priorities by frequency × severity × preventability.
6. **Proactive monitor:** match current context (active work, equipment state, season, recent findings) against precursor signatures → push targeted warnings to the right roles with the historical evidence attached.
7. Feed confirmed lessons back into the Fabric so the Copilot and RCA agent inherit them.

**Interfaces:** `GET /patterns`, `GET /prevention-priorities`, `POST /monitor/evaluate` (context → warnings), webhook/push for alerts. UI: pattern explorer (clusters + timelines), prevention-priority board, live warning feed.

**Edge cases:** small history (blend with external data, mark low confidence), over-alerting (tune precursor thresholds; every alert carries evidence + a dismiss-with-reason that tunes future sensitivity), privacy/attribution (anonymize where needed).

**Acceptance tests:** pattern-detection recall on planted recurring incidents; precursor-match precision (does a warning fire on genuine precursor conditions?); false-alert rate; "did it catch the repeat" on a held-out incident.

**Demo beat:** SMRITI proactively surfaces: *"A confined-space entry is scheduled tomorrow in Area 4. In 2019 and 2022, entries under similar gas-purge conditions produced two near-misses (NM-2019-07, NM-2022-31). Recommend extended purge verification."* — a warning issued *before* the work, from memory the plant already had. The closing line of the pitch writes itself.


---

## §6. Data model reference (for the build agent)

**Graph (property-graph, e.g. Neo4j/Memgraph):** node & edge types per §3.1. Every node/edge carries a `provenance` object `{source_doc_id, page, bbox, extractor, confidence, effective_date, superseded_by}`.

**Vector store (Qdrant/Milvus — needs native multi-vector/MaxSim):**
- `text_chunks` collection: dense + sparse vectors, payload `{doc_id, chunk, page, section, entity_tags[]}`.
- `visual_pages` collection: multi-vector (per-patch) embeddings, payload `{doc_id, page, render_uri, patch_grid}`.

**Object store:** original files + rendered page images + drawing overlays.

**Relational/metadata:** documents, ingest jobs, users/roles, audit log of every tool call + agent action (this powers both RBAC and the eval harness).

**DrawingRegion index:** `{region_id, doc_id, page, bbox, symbol_class, equipment_tag, graph_node_id}` — the join between pixels and knowledge.

**Canonical answer object (what agents return):**
```json
{
  "answer": "streamed text with [c1][c2] markers",
  "citations": [{"id":"c1","node_id":"...","doc_id":"...","page":3,"bbox":[..],"snippet":"..."}],
  "modalities_used": ["graph","visual"],
  "confidence": 0.87,
  "drawing_overlays": [{"doc_id":"...","page":1,"highlights":[..],"traced_edges":[..]}],
  "reasoning_trace": [ /* plan-act-observe steps for the UI panel */ ],
  "insufficient_evidence": false
}
```

---

## §7. Recommended tech stack (concrete, current)

- **Orchestration/agents:** an agent framework (LangGraph-style state machine) or a lean custom orchestrator — prefer explicit, inspectable plan-act-observe over opaque autonomy (you want to *show* the reasoning).
- **LLM:** a strong reasoning model for extraction/RCA/answers; a small fast model for the intent router.
- **Text embeddings:** a top open embedding model (domain-adaptable); SPLADE/BM25 for sparse.
- **Visual retrieval:** ColQwen3 / ColModernVBERT (efficiency) or Nemotron-ColEmbed tier (accuracy); vLLM pooling endpoint for serving; MUVERA + int8 quantization if scale is demoed.
- **Reranker:** a cross-encoder reranker.
- **Graph:** Neo4j or Memgraph; a LightRAG/LazyGraphRAG-style layer for cheap graph indexing + dual-level retrieval; agentic graph-search for deep multi-hop.
- **Vector DB:** Qdrant (simplest multi-vector) or Milvus.
- **P&ID digitizer:** YOLO-family/keypoint detector for symbols + tag association + line/connection reconstruction (Relationformer-style or detector+graph-search); bootstrap from public P&ID datasets (e.g. PID2Graph).
- **Frontend:** streaming chat (SSE), a canvas/SVG **Drawing Viewer** with overlay + tracing, reasoning-trace panel, mobile-first PWA for field use.
- **Eval:** a RAG-eval library (faithfulness/relevance/citation) + your custom golden-set harness with the live baseline comparison.

---

## §8. Synthetic + sourced corpus strategy

You don't need a real plant's systems — you need a *coherent, connected* corpus so the graph lights up. Build a **single fictional plant** ("Refinery Unit 4") with internally consistent records:
- 1–3 **hero P&IDs** (real-style, from public sources or drawn), fully digitized — these carry the visual-grounding demo.
- 15–30 **equipment** items with tags that recur across documents.
- 40–80 **work orders** + inspection reports with deliberate patterns (recurring seal failures, seasonal issues) so RCA and Lessons-Learned have something real to find.
- 10–20 **SOPs** (with version chains for the temporal feature).
- A **regulatory subset** (a handful of real OISD/Factory Act clauses) mapped to the equipment for the compliance demo.
- 8–15 **incidents/near-misses** with planted precursor patterns for Agent 5.
- The **golden Q&A set** (§3.6) derived from all of the above — including the exact demo questions.
> Consistency is everything: the `P-101` on the drawing must be the `P-101` in the work orders and the incidents. That coherence is what makes the graph feel alive.

---

## §9. Build phasing — exhaustive spec, winnable execution

The spec covers all five agents in full because SMRITI *is* all five. But engineering time is finite; **build in this order so that at every checkpoint you have something demoable**, and so depth beats breadth if the clock bites.

- **Phase 0 — Fabric spine (days 1–4, non-negotiable):** ontology, ingestion for text + one hero-P&ID digitized, tri-modal retrieval, provenance, Drawing Viewer skeleton, eval harness scaffold. *Checkpoint: you can retrieve and cite.*
- **Phase 1 — The hero loop (days 4–8):** Agent 1 (ingestion+KG) + Agent 2 (Copilot with visual grounding). *Checkpoint: the winning 30-second demo (§5.2) works end to end.* If nothing else shipped, you already have a strong entry.
- **Phase 2 — The reasoning agents (days 8–12):** Agent 3 (RCA) + Agent 5 (Lessons-Learned/proactive warning). These two carry the "connects dots + prevents repeats" narrative and the biggest Business-Impact beats.
- **Phase 3 — Compliance + polish (days 12–15):** Agent 4 (compliance/audit pack), reasoning-trace panel, baseline-comparison numbers, mobile polish, demo video.

**Rule:** a superb Phase 1 + partial Phase 2 beats five half-built agents. Depth is scored; coverage is not. The exhaustive spec is what you *hand Fable*; the phasing is what you *demo*.

---

## §10. Judging-criteria alignment (design the scorecard into the build)

| Criterion | Weight | Where SMRITI earns it |
|---|---|---|
| **Innovation** | 25% | Not "we invented the plant brain" (the category is validated — §1.5). The novel, defensible pieces: OCR-free visual retrieval across the *whole* corpus, tri-modal *fusion* answers connectivity-only tools can't give, proactive precursor warnings, and India-first regulatory intelligence. Frame as "sharper wedge," not "first mover." |
| **Business Impact** | 25% | Open with the $3.1B Cognite/Schneider deal (30 June 2026) as market proof, then: kills the 35%-search-waste, the 18–22% fragmentation-driven downtime, the knowledge cliff; audit prep in minutes; prevents *repeat* failures. Quantify with the eval deltas. |
| **Technical Excellence** | 20% | Hybrid+graph+visual retrieval, entity resolution, versioning, **live eval vs baseline** — mature-engineering signals judges rarely see. |
| **Scalability** | 15% | MUVERA/quantization path for visual index, LazyGraphRAG cheap indexing, incremental ingest, typed ontology that generalizes across industries. Say it in the architecture diagram. |
| **User Experience** | 15% | Mobile-first field PWA, streaming "watch it think," click-through citations, the Drawing Viewer. The demo *feels* effortless. |

---

## §11. The demo script (the 4 minutes that win)

1. **Cold open (30s):** "Last month, Schneider Electric paid $3.1 billion for Cognite to build exactly this — the industrial knowledge brain. The market's real. But those platforms are Western, heavyweight, and take a year to deploy. We built a sharper slice in 15 days." Drop a messy folder → the graph assembles live (Agent 1).
2. **The wow (45s):** Phone. Voice-ask *"P-101 keeps tripping on high temp — what feeds it, has this happened before, and what does the manual say to check?"* → streamed cited answer fusing graph (feed line traced on the P&ID) + history (prior monsoon trips) + a **visually-retrieved OEM manual page, no OCR** (Agent 2). Tap a citation → source opens. *"A drawing-lookup tool can't answer that — it needs all three modalities."*
3. **The reasoning (45s):** "Why does it keep failing?" → timeline + evidence-ranked RCA + **cross-asset pattern** "P-103 and P-107 too" (Agent 3).
4. **The foresight (45s):** SMRITI proactively warns about tomorrow's confined-space entry matching 2019/2022 near-miss precursors (Agent 5). *"It remembered so the crew didn't have to."*
5. **The credibility (30s):** flash the eval dashboard — SMRITI vs vanilla RAG on the golden set (Agent 2/3 faithfulness + citation-correctness deltas). "We measured it."
6. **The close (15s):** "One-click OISD audit pack" generates (Agent 4). "We didn't build a search box. We built the plant's institutional memory — one that never retires."

---

## §12. Risks & honest mitigations

- **P&ID parsing is hard** → scope full structural parsing to hero drawings; visual-retrieval grounding covers the long tail. Never fake it.
- **Multi-vector storage is heavy** → fine at hackathon scale; cite MUVERA/quantization as the production answer.
- **Graph indexing cost** → use LazyGraphRAG/LightRAG-style cheap indexing, not full community summarization on every ingest.
- **Hallucination** → evidence-constrained answers + "insufficient evidence" as a valid output + citation-correctness in eval.
- **"This already exists" (the pitch killer)** → §1.5 is your defense. Never claim to have invented the category; open with the $3.1B validation and win on the specific wedges (visual fusion, India-regulatory, proactive warnings, provable eval). A judge who knows Cognite/PNID.IO will reward the honesty and punish the bluff.
- **Name collision** → "Cortex" is taken (SymphonyAI). Ship as SMRITI (or your pick) after a 60-second check.
- **Scope creep (the real killer)** → obey §9 phasing. Depth over breadth.

---

*End of specification. Build the Fabric first. Make the drawing light up. Then let the agents reason on top.*