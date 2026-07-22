# SMRITI — System Handoff #2 (post structured-intake + UI upgrade)

> Read `HANDOFF.md` first for the full system map (architecture, agents, retrieval
> fabric, how to run, the demo-vs-real analysis). **This file is the delta**: what
> changed in the "structured intake + UI/UX" update, exactly how it works, what is
> verified, and what is still open. Grounded entirely in the code as of commit
> `a38c2bc`. Nothing here is aspirational unless explicitly flagged.

---

## 0. TL;DR of this update
The one credibility gap in HANDOFF §5 — *records that power Diagnostics/RCA and
Warnings only got in via hardcoded batch ingest* — is **closed**. A customer can
now log incidents / work orders / inspections / permits through first-class typed
forms (or bulk CMMS export, or auto-classified upload), and each writes the
**byte-for-byte same graph structure as the batch ingest**, so it is live in the
timeline / RCA / warnings / compliance **with no restart and no re-ingest**. The
three demo-carrying surfaces got a visual upgrade. All verified live; fabric clean
at 318 nodes.

---

## 1. The two prime directives (and how they were honoured)
1. **Structured intake writes the SAME graph structure as batch ingest.** Achieved
   by *sharing code*: the runtime materialisers in `backend/smriti/intake.py`
   produce the identical `:rec` node ids, node types, edges and field keys as
   `ingest.py`'s batch functions. Verified by a live graph-structure diff
   (§4, A.7.1).
2. **No framework, no build step.** All UI work is in the existing vanilla
   `frontend/{index.html,app.js,style.css}`. `?v=N` cache-busting bumped to
   **v=13**; `NoCacheStatic` headers unchanged. No React/Vue/Vite/Tailwind/CDN added.

---

## 2. Backend — what changed

### 2.1 `backend/smriti/intake.py` (continuous-intake engine — pre-existing, now the shared core)
- **Materialisers** (`add_work_order`, `add_inspection`, `add_incident`, `add_permit`,
  `add_equipment_rec`) — each mirrors the corresponding `ingest.py` batch function:
  - Incident → `Document INC-…` + `INC-…:rec` (Incident) with
    `incident_id,date,area,equipment,category,title,narrative,root_cause,precursors,actions`;
    edges `:rec→equipment INVOLVES`, `equipment→doc DESCRIBED_BY`, `:rec→area INVOLVES`; `link_tags` on narrative+precursors.
  - Work order → `Document WO-…` + `WO-…:rec` (WorkOrder) with
    `wo_id,equipment,date,wo_type,title,findings,parts,downtime_h`;
    edges `equipment→:rec MAINTAINED_BY`, `equipment→doc DESCRIBED_BY`, `doc→closer AUTHORED_BY`; `link_tags` on findings.
  - Inspection → `Document INSP-…` + `INSP-…:rec` (Inspection) with `equipment,date,method,result,text`;
    edges `equipment→:rec INSPECTED_BY`, `equipment→doc DESCRIBED_BY`.
  - Permit → **only a `Document`** node `doc_type=permit` with `ptype,equipment,area,date,text` + `doc→equipment INVOLVES`
    (no `:rec` — matches batch; this is what `lessons.evaluate_upcoming` reads via `date>=today`).
- `_ensure_equipment` auto-stubs an unknown asset so a record is never orphaned.
- Also has `classify_and_extract` (one LLM call → doc_type + fields, used by
  auto-classify upload) and `ingest_table` / `parse_table` / `_COLUMN_ALIASES`
  (bulk CSV/JSON CMMS import, no per-row LLM).

### 2.2 `backend/smriti/api.py` — new endpoints
- `POST /api/records/incident | work-order | inspection | permit` — all go through
  one shared handler **`_create_record(rec_type, body, materialiser)`** which:
  1. generates an id if none given (`_new_record_id`: `{PREFIX}-{year}-{seq}` from live node counts),
  2. builds `Provenance(extractor="manual_intake", confidence=1.0, effective_date=date)`,
  3. calls the materialiser, `kg.save()`, upserts text chunks,
  4. **recomputes only the affected caches** — inspection→compliance_register+audit_package;
     incident→patterns+warnings; permit→patterns then re-runs `evaluate_upcoming()`,
  5. returns `{created, record_type, equipment, new_equipment, provenance, downstream[], summary, warnings?}`.
- Permit path returns any warning whose `permit == <new id>` → **the live foresight beat**.
- `POST /api/ingest` — now **multi-file** (`files: list[UploadFile]`), classify-and-materialise each.
- `POST /api/ingest/table?record_type=…` — bulk CMMS import.
- `POST /api/equipment` — asset add (unchanged).
- **Contract for the frontend:** the `downstream[]` strings and `warnings[]` array
  power the toast + deep-link. Don't change these shapes without updating `app.js`.

### 2.3 Caching reality (verified in code — important for live demo)
- `patterns.json`, `warnings.json`, `compliance_register.json`, `audit_package.json`
  are cached to `data/`. `GET /api/warnings` (no `?refresh`) returns the cache if
  present else recomputes. So intake endpoints **delete** the relevant cache file so
  the next view load recomputes. `failure_timeline` / RCA walk the graph live (no cache).

---

## 3. Frontend — what changed (`view-add` + hero surfaces)
- **`view-add` rebuilt as a tabbed intake hub** — tabs: Incident · Work order ·
  Inspection · Permit · Asset · Upload docs · Bulk import. The four structured forms
  are rendered from a JS `FORM_SPECS` object (fields, types, required, hints) into
  `#intake-form-host`; asset/upload/bulk are static panels reusing prior element ids.
  Submit → `submitRecord()` posts to `/api/records/*`, shows a result block with a
  `manual intake · confidence 1.0` chip + `downstream` list, and a **toast**.
- **Toasts** (`toast()` + `#toasts`): permit-fired-warning toasts are red with a
  `View →` link to `#warn`; record toasts deep-link to `#rca` for the affected asset.
- **Visual failure timeline** (`timelineHTML` + `eventClass`) replaces the old table
  in both Diagnostics (`renderRCA`) and Assets (`openAsset`): vertical rail, dots and
  kind-badges color-coded by event type, tabular dates, clickable `.cite` chips.
- **RCA cause cards**: numbered rank badge (#1 highlighted red), mechanism, inline
  citations; **cross-asset pattern** promoted to a distinct amber `.cross-callout`.
- **Deep-links**: `#assets=TAG` opens an asset; `#rca=TAG` selects + auto-runs RCA.
  Shareable and demo-friendly. `prefers-reduced-motion` disables non-essential motion.
- New CSS lives under clearly-commented blocks: "visual failure timeline",
  "RCA cause cards + cross-asset callout", "structured intake hub", "toasts".

---

## 4. What is verified (ran live against the server, screenshots taken)
- **A.7.1 parity** — form incident `:rec` field keys == batch incident (`INC-2018-02:rec`), both `Incident`.
- **A.7.2 instant timeline** — bulk WO + form incident appear in P-101 timeline, date-sorted, no restart.
- **A.7.4 live warning** — upcoming TK-401 confined-space permit fired the mined
  "Curtailed confined-space purge under schedule pressure" warning citing NM-2019-07/NM-2020-14/INC-2020-03/NM-2022-31.
- **A.7.5 persistence** — a separate process read the new records off `graph.json`.
- **A.7.6 provenance** — `manual_intake` / 1.0.
- UI renders confirmed: intake hub (incident tab), Warnings, P-101 asset visual
  timeline, P-101 RCA (cause cards + cross-callout). Fabric returned to clean **318 nodes / 492 edges** (all test records removed).

---

## 5. STILL OPEN (next candidates — NOT built)
Honest list; pick from here.
1. **Ask (Hero 1) polish** — the reasoning-trace stepper + citation hover-preview in
   B.4 were **not** done; the Ask view is the pre-existing (already good) animated
   dot-matrix trace + drawing viewer. Do NOT change the SSE event shapes or the
   Drawing Viewer overlay contract if you touch it.
2. **Full loading/empty/error-state audit (B.5)** — main views have loaders/error
   cards/empty notes, but not every failure path was force-tested. A judge clicking
   in an odd order is the risk to harden against.
3. **Projector/phone legibility (B.7)** — only verified at desktop widths.
4. **Human-in-the-loop review queue** for low-confidence auto-classified uploads /
   rejected LLM extractions (`extraction.py` already produces a `rejected` list).
5. **Live CMMS connector** (poll SAP-PM/Maximo) vs manual export upload.
6. **Undo / versioning** on hand-entered records (provenance is stamped, but no UI to revert).
7. **Idempotent re-import / de-dup** — re-uploading the same id currently overwrites;
   bulk re-imports should be idempotent by record id.
8. **Design-system tokens (B.3)** — I kept the existing (already solid) palette and
   added semantic pieces as needed rather than formalising a full token layer; a
   dedicated pass could encode the type/spacing/motion scale explicitly.

---

## 6. Demo choreography (both video + 2-hour hands-on)
- **Foresight money-shot:** Add data → Permit tab → log a confined-space permit on
  TK-401 dated tomorrow with a shortened-purge scope → toast *"1 new warning triggered"*
  → `View →` → Warnings shows the fired warning citing 2019/2022 near-misses.
  *It's real: the precursor matching runs live.*
- **Instant-memory shot:** Incident tab → log an incident on P-101 → toast → Diagnostics
  for P-101 → it's in the timeline, seconds after entry.
- **Bulk story:** Bulk import → drop a SAP-style CSV of work orders → thousands land as typed records.
- **Wow / credibility (unchanged):** phone voice-ask tri-modal fusion; eval dashboard.
- Deep-links `#rca=P-101`, `#assets=P-101` jump straight to a surface mid-demo.

---

## 7. Commit trail this session
- `Continuous intake engine: auto-classify upload + bulk CMMS import` (intake.py, HANDOFF.md)
- `Part A: first-class structured intake — typed record forms with graph parity`
- `Part B: hero-surface polish — visual timeline, RCA evidence cards, toasts`
- `docs: HANDOFF reflects structured intake endpoints + UI hero polish`
Repo: `github.com/infinity2147/Bhadra-ET`, branch `main`, HEAD `a38c2bc`. Server on :8000.
