# Reference Dataset — "Bharat Petrochem Ltd., Refinery Unit 4" (illustrative plant)

Every document in the corpus refers to the same equipment tags, people, and history so the
knowledge graph forms real cross-document links. This file is the single source of truth for
dataset consistency; the generator script (`scripts/gen_corpus.py`) and hand-written documents
must follow it exactly.

**Real-world grounding rule:** equipment physics, failure modes, and regulatory clauses are
real (ISO 14224 failure taxonomy, real OISD/Factories Act clauses from research). Only the
plant, people, and event history are fictional.

## Plant overview

Unit 4 — Crude Distillation Unit (CDU) support systems, commissioned 1998, Mumbai coastal
site (monsoon June–September; this seasonality drives the planted failure pattern).

Areas:
- **Area 1** — Cooling Water System (the primary P&ID)
- **Area 2** — Crude Preheat & Heat Exchange
- **Area 3** — Fuel Storage (OISD-116/129 apply)
- **Area 4** — Effluent Treatment (confined-space near-miss history lives here)

## Equipment register (tags recur in EVERY document type)

| Tag | Type | Service | Notes |
|---|---|---|---|
| P-101 | Centrifugal pump | Cooling water supply A | Primary equipment. Recurring monsoon mechanical-seal failures |
| P-102 | Centrifugal pump | Cooling water supply B (standby) | Healthy twin — the contrast case |
| P-103 | Centrifugal pump | Cooling water booster | Same seal model as P-101 → cross-asset pattern |
| P-107 | Centrifugal pump | Effluent transfer, Area 4 | Same seal model → third leg of fleet pattern |
| E-201 | Shell & tube exchanger | CW/crude interchanger | Fouling drives P-101 high-temp trips |
| E-202 | Shell & tube exchanger | Trim cooler | |
| T-301 | Fixed-roof storage tank | HSD (diesel) storage, Area 3 | OISD-129 inspection schedule |
| T-302 | Fixed-roof storage tank | Naphtha storage, Area 3 | Fire protection per OISD-116 |
| PSV-1101 | Pressure safety valve | On P-101 discharge header | **Planted compliance gap: test overdue** (OISD-132) |
| PSV-3101 | Pressure safety valve | On T-301 | In-date — the contrast case |
| CT-101 | Cooling tower | CW return | Source of monsoon ingress/fouling |
| STR-101 | Basket strainer | P-101 suction | Blocking → cavitation precursor |
| TK-401 | Equalization tank | Effluent, Area 4 | **Confined space** — near-miss history |
| V-205 | Knock-out drum | Area 2 | Background equipment |
| MOV-110 | Motor-operated valve | CW header isolation | Background |

Instrument tags on the hero P&ID: TI-1103 (P-101 discharge temp), PI-1101 (suction pressure),
FI-1102 (CW flow), LI-3011 (T-301 level).

## The primary P&ID (Drawing D-CW-104 rev 3)

"Cooling Water System — Unit 4, Area 1". Composed as clean SVG from standard symbols
(research agent confirms source), rendered to PNG for the visual index.

Topology (drives `FEEDS_INTO` edges and drawing-overlay tracing):

```
CT-101 → STR-101 → P-101 → PSV-1101 (branch) → E-201 → [crude side to Area 2]
                 ↘ P-102 (standby, parallel) ↗
E-201 CW return → CT-101 (loop closed)
P-103 boosts CW to Area 2 header (tap after E-201)
```

Every symbol gets a DrawingRegion entry {bbox, tag} — hand-curated ground truth standing in
for the CV digitizer output (honest scoping).

Second drawing D-ET-401 rev 1: Area 4 effluent system (TK-401, P-107) — simpler, supports the
confined-space and fleet-seal narratives.

## History patterns (what the agents surface)

### Pattern A — Monsoon seal failures (diagnostics / RCA)
Work orders across 2019–2025: P-101 mechanical seal replaced Jul 2019, Aug 2021, Jul 2023,
Sep 2024, Jun 2025 (5 CM work orders, all June–September). P-103 seal failures Aug 2022,
Jul 2024. P-107 seal failure Sep 2023. All three use seal model "BurgFlow MS-40D".
Root thread: monsoon → CW turbidity ↑ → STR-101 fouling → intermittent cavitation →
seal face damage. Inspection reports on STR-101 corroborate (high differential pressure
readings in monsoon months). E-201 fouling reports explain the high-temp trips of the
copilot question. OEM manual (BurgFlow pump IOM) checklist page: "high discharge
temperature — check cooler fouling, strainer ΔP, seal flush line" — the visually-retrieved page.

### Pattern B — Confined-space near-miss precursors (Agent 5)
- NM-2019-07 (TK-401 entry, Aug 2019): gas test passed at entry, H2S alarm 40 min in —
  purge had been shortened due to schedule pressure; sludge disturbance re-released gas.
- NM-2022-31 (TK-401 entry, Sep 2022): same signature — monsoon-season high sludge load,
  shortened purge, positive gas reading mid-job.
- Precursor signature: {confined-space entry, Area 4, monsoon window, purge < 4h, sludge
  present}. A *scheduled* permit for TK-401 entry "tomorrow" matches it.

### Pattern C — Compliance gaps (Agent 4)
Planted against real clauses (from regulatory research):
1. PSV-1101 last tested > allowed interval (OISD-132 pressure-relief testing periodicity) → GAP.
2. Fire drill record for Area 3 older than required frequency (Factories Act s.38 + state rules /
   OISD-116) → GAP.
3. T-301 external inspection approaching due date (OISD-129) → WARNING (time-aware).
4. Everything else demonstrably satisfied with citable evidence → the register isn't all red.

### Pattern D — SOP version chain (temporal versioning)
SOP-CW-012 "P-101/P-102 Operation & Changeover": rev 1 (2015), rev 2 (2021, adds strainer
ΔP check), rev 3 (2025-04, adds monsoon-mode weekly seal-flush verification — the *lesson
learned* from Pattern A written back into procedure). "What is the current procedure?" must
return rev 3 and be able to show the evolution.

### Pattern E — The retiring expert (knowledge attribution)
Senior reliability engineer "R. K. Sharma" (retiring): authored the sharpest RCA notes
(WO-2023 seal failure closeout: "suspect strainer bypass during monsoon — third time I've
seen this since 2019") and an email thread explaining the CW turbidity mechanism. His name
on `AUTHORED_BY` edges makes the knowledge-attribution story concrete.

## Document inventory (generator targets)

| Type | Count | Format | Notes |
|---|---|---|---|
| P&IDs | 2 | SVG→PNG + curated region JSON | D-CW-104 r3, D-ET-401 r1 |
| Work orders | ~55 | structured JSON + rendered PDF | incl. Patterns A history + routine noise |
| Inspection reports | ~18 | PDF (text) | STR-101 ΔP series, E-201 fouling, T-301, PSVs |
| SOPs | 12 | PDF (text, numbered steps) | incl. SOP-CW-012 rev chain, confined-space entry SOP-ET-005 |
| Incidents/near-miss | 10 | PDF | incl. NM-2019-07, NM-2022-31 + noise |
| OEM manual extracts | 3 | PDF (scanned-look pages for visual retrieval) | BurgFlow IOM w/ troubleshooting checklist |
| Regulatory clauses | 12–20 | structured JSON (real clause text + source URL) | from research agent |
| Email archive | ~8 | .eml-style text | Sharma thread, RFI about MOV-110 |
| Permits | 4 | PDF | incl. tomorrow's TK-401 confined-space permit |

## Golden Q&A set (evaluation)

Categories: factual lookup (10), multi-hop graph (10), visual/drawing (8), RCA (7),
compliance (5), temporal/version (5). Representative questions:
- "P-101 keeps tripping on high temperature — what feeds it, has this happened before, and
  what does the manual say to check?"
- "Why does P-101 keep failing?"
- "Prepare us for an OISD audit on the fuel storage area."
- "What is the current procedure for P-101 changeover?"
Each entry: {question, expected_answer_points[], required_citations[], modality_expected}.
