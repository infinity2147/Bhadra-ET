# SMRITI — Pitch & Demo Script (4–5 minutes)

**Format:** first the deck (slides 1–8, ~2 min), then the live product demo (~2.5 min),
then close on slide 10 (~15 s). Open the deck at `smriti/docs/pitch-deck.html`
(press **F** for fullscreen), have the app running at **http://localhost:8000** in a
second tab. Total target: **4:30**.

> Timing markers are cumulative. Words in **bold** are the beats to hit; you don't
> need to read verbatim — hit the beats, sound like an engineer, not a narrator.

---

## PART 1 — THE PITCH (slides, ~2:00)

### Slide 1 · Title  (0:00–0:15)
> "This is **SMRITI** — Sanskrit for *memory*. Every plant already has the knowledge
> to prevent its next failure. The problem is it's trapped. SMRITI is the brain that
> holds all of it — and answers in plain language, with citations you can trust."

### Slide 2 · The problem  (0:15–0:40)
> "A refinery's knowledge lives in **twelve disconnected systems** and in the heads of
> **engineers about to retire**. P&IDs, work orders, SOPs, incident reports, scanned
> OEM manuals, email. None of it talks to each other. So the same failure repeats —
> and nobody connects today's job to the near-miss from 2019."

### Slide 3 · Market  (0:40–1:00)
> "This isn't a hypothesis. Last month, **Schneider and AVEVA bought Cognite for
> $3.1 billion**. But the incumbents are heavy, Western, and priced for nine-to-twelve-month
> rollouts. SMRITI is the **sharper, India-first slice** — real OISD and Factories Act
> compliance, it reads drawings visually, and it turns near-misses into warnings."

### Slide 4 · What it is  (1:00–1:25)
> "SMRITI is **not another RAG chatbot**. One question fans out across three modalities —
> **text, a knowledge graph, and the drawings themselves** — fused into one answer,
> rendered **on the P&ID, with citations**. The winning question — *why does P-101 trip?* —
> needs drawing connectivity **plus** work-order history **plus** a visually-retrieved
> scanned manual page. A text-only RAG simply cannot produce that."

### Slide 5 · Architecture  (1:25–1:45)
> "Here's how. Every source is ingested by type into a **typed knowledge graph with
> provenance on every fact**, and indexed three ways in Qdrant — dense text, sparse
> keyword, and **OCR-free visual**. A query routes across all three, merges, reranks,
> and five agents reason on top: copilot, diagnostics, compliance, and a proactive
> warnings monitor. **It runs fully local — no cloud dependency.**"

### Slide 6 · Continuous intake  (1:45–1:58) — *optional if tight on time*
> "And it's **built to run for years, not just demo**. New records flow in live through
> typed forms or bulk CMMS export, writing the *same graph structure* as the core data —
> so a new incident is analyzable, and a new permit can fire a warning, **instantly**."

### Slide 7 · Compliance  (skip if tight, or 5 s)
> "It's India-first: **18 real regulatory clauses, each with its source**, mapped to
> equipment — it even catches where the plant's own inspection interval contradicts OISD."

### Slide 8 · Proof  (1:58–2:15)
> "And we **measured** it. Against a vanilla RAG baseline, same model and corpus, on a
> 33-question expert golden set, LLM-judged. Faithfulness and citations edge ahead;
> where the fabric earns its keep the gaps are large — **+15 points on multi-modal fusion,
> +17 on proactive warnings**. And we state our caveats rather than hide them."

---

## PART 2 — THE LIVE DEMO  (slide 9 → the app, ~2:15–4:15)

> Advance to **slide 9** ("Let's open the brain"), then switch to the browser tab at
> **http://localhost:8000**. Reload once so it's fresh.

### Beat A · The wow — tri-modal answer on the drawing  (2:15–3:00)
1. On **Ask**, click the first suggested question (or type):
   *"P-101 keeps tripping on high temperature — what feeds it, has this happened before, and what does the manual say to check?"*
2. **Talk over the reasoning trace as it runs:**
   > "Watch it think — it's **routing**, searching text, **traversing the graph**, and
   > **reading the drawings**. Three modalities, one pipeline."
3. When the answer streams:
   > "It streams a cited answer — it traces the feed path **CT-101 → STR-101 → P-101** on
   > the drawing, cites the **monsoon trip work orders**, and pulls a **scanned OEM
   > troubleshooting page — retrieved on visual signal, no OCR.**"
4. Click one **[c#] citation** → the source page opens.
   > "Every claim clicks through to its source. That's trust as a feature."

### Beat B · Reasoning — Diagnostics  (3:00–3:30)
1. Left nav → **Diagnostics** → select **P-101** → **Analyze**.
2. > "This is graph-native root-cause. A **visual failure timeline** of every work order,
   > inspection and incident. Evidence-ranked causes, each citing record IDs. And the
   > key move —" (point to the cross-asset callout) — "**the same seal pattern is on
   > P-103 and P-107. It recommends a fleet-wide seal review.** No human had connected those three."

### Beat C · The money shot — log a permit, watch a warning fire LIVE  (3:30–4:15)
1. Left nav → **Add data** → **Permit** tab. (**Planned date is pre-filled to tomorrow.**)
2. Fill: **Permit type** = confined space entry · **Equipment tag** = TK-401 ·
   **Area** = Area 4 · **Scope of work** = *"Desludging entry; forced-air purge
   shortened to ~2 h due to schedule pressure."*
3. Click **Raise permit.** When the toast appears:
   > "I just entered that — nothing scripted. And SMRITI **matched it against the plant's
   > own history** and fired a warning."
4. Click **View →** on the toast (or nav → **Warnings**):
   > "It re-assembled the **precursor signature of the 2019 and 2022 H2S near-misses** —
   > shortened purge, monsoon, confined space — and it's telling us **before the work**:
   > minimum four-hour purge. *That* is institutional memory working as foresight."
5. *(Optional 10 s)* nav → **Diagnostics/Assets** to show a just-logged incident already in a timeline.

> Switch back to the deck, advance to **slide 10**.

---

## PART 3 — CLOSE  (slide 10, ~4:15–4:30)
> "We didn't build a search box. We built the plant's memory — one that reads its
> drawings, reasons across its history, **proves** its answers, and warns before the next
> failure. **Institutional memory that never retires.** Thank you."

---

## Operator checklist (before you hit record)
- [ ] Server running: `cd smriti/backend && ../../.venv/bin/python -m uvicorn smriti.api:app --port 8000`
- [ ] App loads at http://localhost:8000; fabric chip shows ~318 nodes.
- [ ] Deck open at `smriti/docs/pitch-deck.html`, press **F** for fullscreen.
- [ ] Pre-run the P-101 Ask question **once** off-camera to warm the models (first call is slow).
- [ ] Know **tomorrow's date** for the permit field.
- [ ] Two tabs ready: deck + app. Screen-record at 1080p, landscape.
- [ ] If a call is slow on camera, talk over the reasoning trace — that *is* the story.

## Fallback if something is slow live
- The Ask answer can take ~30–50 s on a cold model. Warm it first (checklist), or narrate
  the trace. If it stalls, cut to **Diagnostics** (fast, no long LLM stream) and come back.
- The permit→warning step makes a few LLM calls; give it a beat. It's the strongest moment — don't rush it.
