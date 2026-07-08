/* SMRITI frontend — vanilla JS, no build step. */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

/* ---------------- sidebar nav (with #hash deep links) ---------------- */
const SECTION_TITLES = {
  ask: "Ask the plant's memory",
  assets: "Asset Explorer",
  rca: "Equipment Diagnostics",
  warn: "Proactive Warnings",
  comp: "Compliance Register",
  eval: "Evaluation — measured, not claimed",
  add: "Add to the knowledge fabric",
};
function activateView(v) {
  $$(".nav-item").forEach(t => t.classList.toggle("active", t.dataset.view === v));
  $$(".view").forEach(s => s.classList.toggle("active", s.id === `view-${v}`));
  const title = $("#section-title");
  if (title && SECTION_TITLES[v]) title.textContent = SECTION_TITLES[v];
  document.body.classList.toggle("on-ask", v === "ask");
  document.querySelector(".app")?.classList.remove("nav-open");  // close mobile drawer
  history.replaceState(null, "", `#${v}`);
  if (v === "comp") loadCompliance();
  if (v === "warn") { loadPatterns(); loadWarnings(false); }
  if (v === "eval") loadEvals();
  if (v === "rca") loadEquipment();
  if (v === "assets") loadAssets();
  if (v === "add") loadAddForm();
}
$$(".nav-item").forEach(tab =>
  tab.addEventListener("click", () => activateView(tab.dataset.view)));

/* mobile hamburger */
$("#hamburger")?.addEventListener("click", () =>
  document.querySelector(".app").classList.toggle("nav-open"));
document.addEventListener("click", e => {
  const app = document.querySelector(".app");
  if (app?.classList.contains("nav-open") &&
      !e.target.closest(".sidebar") && !e.target.closest("#hamburger")) {
    app.classList.remove("nav-open");
  }
});

window.addEventListener("DOMContentLoaded", () => {
  const raw = location.hash.slice(1);
  const [v, arg] = raw.split("=");   // e.g. #assets=P-101 deep-links to an asset
  if (["assets", "rca", "warn", "comp", "eval", "add"].includes(v)) {
    activateView(v);
    if (v === "assets" && arg) setTimeout(() => openAsset(decodeURIComponent(arg)), 200);
    if (v === "rca" && arg) setTimeout(() => {
      const s = $("#rca-tag"); if (s) s.value = decodeURIComponent(arg); $("#rca-run")?.click();
    }, 300);
  } else document.body.classList.add("on-ask");
});

/* ---------------- helpers ---------------- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function md(s) { // minimal: **bold**, newlines preserved by CSS
  return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
}
/* classify a timeline event by kind → semantic color class + label */
function eventClass(kind = "") {
  const k = String(kind).toLowerCase();
  if (k.startsWith("incident") || k.includes("near")) return { c: "risk", t: "incident" };
  if (k.includes("fail")) return { c: "risk", t: "inspection · fail" };
  if (k === "breakdown") return { c: "serious", t: "breakdown" };
  if (k === "cm") return { c: "serious", t: "corrective (CM)" };
  if (k === "pm") return { c: "good", t: "preventive (PM)" };
  if (k.startsWith("inspection")) return { c: "s1", t: k.replace("/", " · ") };
  return { c: "s1", t: kind || "record" };
}
/* vertical, color-coded failure/history timeline (events newest-first) */
function timelineHTML(events, limit = 40) {
  const evs = (events || []).slice(0, limit);
  if (!evs.length) return `<div class="empty-note">No recorded history yet.</div>`;
  return `<div class="vtimeline">` + evs.map(e => {
    const { c, t } = eventClass(e.kind);
    return `<div class="vt-item vt-${c}">
      <div class="vt-dot"></div>
      <div class="vt-card">
        <div class="vt-top"><span class="vt-date">${esc(e.date || "—")}</span>
          <span class="vt-kind vt-${c}">${esc(t)}</span>
          <span class="cite" data-evd="${esc(e.id)}">${esc(e.id)}</span></div>
        <div class="vt-what">${esc(e.what || "")}</div>
        ${e.detail ? `<div class="vt-detail">${esc(String(e.detail).slice(0, 180))}</div>` : ""}
      </div></div>`;
  }).join("") + `</div>`;
}
function citeChips(text, citations) {
  return text.replace(/\[(c\d+)\]/g, (_, id) => {
    const c = citations.find(x => x.id === id);
    if (!c) return "";
    return `<span class="cite" data-cite="${id}">${esc(c.doc_id)}</span>`;
  });
}
async function getJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}
function setBadge(id, n) {
  const el = $(`#${id}`);
  if (!el) return;
  if (n > 0) { el.textContent = n; el.hidden = false; }
  else { el.hidden = true; }
}

/* animated dot-matrix "thinking" symbol — cells pulse in a wave from the centre */
function matrixHTML(cls = "", color = "") {
  let cells = "";
  for (let i = 0; i < 25; i++) {
    const r = Math.floor(i / 5), c = i % 5;
    const d = Math.hypot(r - 2, c - 2);        // ring distance from centre
    cells += `<i style="animation-delay:${(d * 0.14).toFixed(2)}s"></i>`;
  }
  const style = color ? ` style="--mc:${color}"` : "";
  return `<div class="matrix ${cls}"${style}>${cells}</div>`;
}
/* small inline loader for panels (RCA / compliance / warnings) */
function loaderHTML(label, color) {
  return `<span class="phase-inline">${matrixHTML("sm", color)}${esc(label)}</span>`;
}

/* ---------------- graph chip ---------------- */
getJSON("/api/graph/stats").then(d => {
  const s = d.stats, ig = d.ingest;
  $("#graph-chip").innerHTML =
    `${s.nodes} nodes · ${s.edges} edges<br>${ig.text_chunks ?? "?"} chunks · ${ig.visual_pages ?? 0} visual pages`;
}).catch(() => { $("#graph-chip").textContent = "fabric offline"; });

/* prime sidebar badges from caches (cheap — no rebuild) */
getJSON("/api/warnings").then(w => setBadge("warn-count", w.length)).catch(() => {});
getJSON("/api/compliance/register").then(r =>
  setBadge("comp-count", r.filter(x => x.status === "gap").length)).catch(() => {});

/* welcome hero animated mark */
const heroMark = $("#hero-mark");
if (heroMark) heroMark.innerHTML = matrixHTML("hero");

/* ---------------- citation drawer ---------------- */
let lastCitations = [];
document.addEventListener("click", e => {
  const el = e.target.closest("[data-cite]");
  if (el) {
    const c = lastCitations.find(x => x.id === el.dataset.cite);
    if (c) openDrawer(c);
  }
  const ev = e.target.closest("[data-evd]");
  if (ev) openDrawer({ doc_id: ev.dataset.evd, page: 1, snippet: ev.dataset.snip || "" });
});
function openDrawer(c) {
  $("#drawer-title").textContent = `${c.doc_id} · p${c.page || 1}`;
  const render = c.render || `${c.doc_id}_p${c.page || 1}.png`;
  $("#drawer-body").innerHTML = `
    ${c.doc_type ? `<span class="chip">${esc(c.doc_type)}</span>` : ""}
    ${c.snippet ? `<p class="snippet">${esc(c.snippet)}</p>` : ""}
    <img src="/renders/${esc(render)}"
         onerror="this.style.display='none'"
         alt="source page">`;
  $("#drawer").classList.remove("hidden");
  $("#scrim").classList.remove("hidden");
}
$("#drawer-close").addEventListener("click", closeDrawer);
$("#scrim").addEventListener("click", closeDrawer);
function closeDrawer() {
  $("#drawer").classList.add("hidden");
  $("#scrim").classList.add("hidden");
}

/* ---------------- ASK (SSE chat, multi-turn) ---------------- */
const thread = $("#thread");
let conversation = [];   // [{role:"user"|"assistant", content}] — sent for follow-ups
$("#ask-form").addEventListener("submit", e => { e.preventDefault(); sendAsk(); });
document.addEventListener("click", e => {
  const s = e.target.closest(".sugg");
  if (s) { $("#ask-input").value = s.textContent.trim(); sendAsk(); }
});
$("#new-chat")?.addEventListener("click", () => {
  conversation = [];
  thread.innerHTML = `
    <div class="welcome">
      <div class="hero-mark">${matrixHTML("hero")}</div>
      <h2>Ask the plant&rsquo;s memory</h2>
      <p>Every drawing, work order, procedure, inspection, near-miss and
         regulation of Unit 4 — fused into one graph you can talk to.</p>
      <div class="suggestions">
        <button class="sugg">P-101 keeps tripping on high temperature — what feeds it, has this happened before, and what does the manual say to check?</button>
        <button class="sugg">Why does P-101 keep failing?</button>
        <button class="sugg">What is the current procedure for P-101 / P-102 changeover?</button>
        <button class="sugg">Is there any risk with the confined space entry planned for TK-401 tomorrow?</button>
      </div>
    </div>`;
});

async function sendAsk() {
  const q = $("#ask-input").value.trim();
  if (!q) return;
  $("#ask-input").value = "";
  $("#ask-send").disabled = true;
  $(".welcome")?.remove();

  thread.insertAdjacentHTML("beforeend",
    `<div class="msg user"><div class="bubble">${esc(q)}</div></div>`);
  const id = `m${Date.now()}`;
  thread.insertAdjacentHTML("beforeend", `
    <div class="msg assistant" id="${id}">
      <div class="phase" id="${id}-phase">
        ${matrixHTML()}
        <div>
          <div class="phase-label">Understanding your question</div>
          <div class="phase-sub">preparing tri-modal retrieval</div>
        </div>
      </div>
      <details class="trace"><summary>reasoning trace</summary>
        <div class="tsteps"></div></details>
      <div class="bubble" hidden></div>
      <div class="extras"></div>
    </div>`);
  const msgEl = $(`#${id}`);
  const bubble = $(".bubble", msgEl);
  const tsteps = $(".tsteps", msgEl);
  const phaseEl = $(`#${id}-phase`);
  let bubbleShown = false;

  // map a live trace event → the animated phase (label, sub, matrix colour)
  const MC = { blue: "#2a78d6", teal: "#1baf7a", amber: "#d97706" };
  function setPhase(label, sub, color) {
    if (!phaseEl) return;
    phaseEl.querySelector(".phase-label").textContent = label;
    phaseEl.querySelector(".phase-sub").textContent = sub || "";
    if (color) phaseEl.querySelector(".matrix").style.setProperty("--mc", color);
  }
  thread.scrollTop = thread.scrollHeight;

  let acc = "";
  try {
    const resp = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, history: conversation.slice(-6) }),
    });
    conversation.push({ role: "user", content: q });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) >= 0) {
        const frame = buf.slice(0, idx); buf = buf.slice(idx + 2);
        if (!frame.startsWith("data: ")) continue;
        handleEvent(JSON.parse(frame.slice(6)));
      }
    }
  } catch (err) {
    phaseEl?.remove();
    bubble.hidden = false;
    bubble.innerHTML = `<span style="color:var(--serious-text)">connection error: ${esc(err.message)}</span>`;
  }
  $("#ask-send").disabled = false;

  function handleEvent(ev) {
    if (ev.type === "trace") {
      let bits = "";
      if (ev.step === "contextualize") {
        setPhase("Reading the conversation", `resolved to: ${ev.rewritten}`, MC.blue);
        bits = `<b>context</b> follow-up resolved → "${esc(ev.rewritten)}"`;
      } else if (ev.step === "route") {
        const primary = ev.modalities?.[0];
        const color = primary === "graph" ? MC.teal : primary === "visual" ? MC.amber : MC.blue;
        setPhase(`Routing → ${ev.modalities?.join(" + ")}`,
                 `intent: ${ev.intent}${ev.tags?.length ? " · " + ev.tags.join(", ") : ""}`, color);
        bits = `<b>router</b> → ${ev.modalities?.join(" + ")} · intent ${esc(ev.intent)} ${ev.tags?.length ? "· tags " + ev.tags.join(", ") : ""}`;
      } else if (ev.step === "text_search") {
        setPhase("Searching documents", "hybrid dense + BM25", MC.blue);
        bits = `<b>text</b> hybrid dense+BM25 → ${ev.hits?.map(h => h[0]).slice(0, 5).join(", ")}`;
      } else if (ev.step === "graph_traverse") {
        setPhase("Traversing knowledge graph", `${ev.tags?.join(", ")} → ${ev.items} evidence sets`, MC.teal);
        bits = `<b>graph</b> traversed ${ev.tags?.join(", ")} → ${ev.items} evidence sets`;
      } else if (ev.step === "visual_search") {
        setPhase("Reading drawings", "ColPali late interaction · no OCR", MC.amber);
        bits = ev.error ? `<b>visual</b> unavailable` : `<b>visual</b> ColPali page match (no OCR) → ${ev.hits?.map(h => `${h[0]} p${String(h[1]).replace("p","")}`).join(", ") || "none"}`;
      } else if (ev.step === "rerank") {
        setPhase("Ranking evidence", "cross-encoder rerank", MC.blue);
        bits = `<b>rerank</b> cross-encoder kept ${ev.kept?.map(k => k[0]).slice(0, 6).join(", ")}`;
      } else if (ev.step === "drawing_overlay") {
        setPhase("Marking up the drawing", ev.drawings?.join(", "), MC.amber);
        bits = `<b>overlay</b> preparing ${ev.drawings?.join(", ")}`;
      } else return;
      tsteps.insertAdjacentHTML("beforeend", `<div class="tstep">${bits}</div>`);
    } else if (ev.type === "delta") {
      if (!bubbleShown) {           // first token: retire the loader, reveal the answer
        setPhase("Answering", "grounded in cited evidence", MC.blue);
        bubble.hidden = false;
        bubbleShown = true;
      }
      acc += ev.text;
      bubble.innerHTML = md(acc);
      thread.scrollTop = thread.scrollHeight;
    } else if (ev.type === "final") {
      phaseEl?.remove();
      bubble.hidden = false;
      lastCitations = ev.all_evidence;
      bubble.innerHTML = citeChips(md(ev.answer), ev.all_evidence);
      conversation.push({ role: "assistant", content: ev.answer.slice(0, 900) });
      const conf = ev.confidence;
      const cls = conf >= 0.7 ? "hi" : conf >= 0.45 ? "mid" : "lo";
      const mods = ev.modalities_used.map(m => `<span class="chip mod">${m}</span>`).join("");
      const extras = $(".extras", msgEl);
      extras.innerHTML = `
        <div class="meta-row">
          <span class="chip conf ${cls}">confidence ${(conf * 100).toFixed(0)}%</span>
          ${mods}
          ${ev.insufficient_evidence ? `<span class="chip" style="color:var(--serious-text)">insufficient evidence — honest no-answer</span>` : ""}
          <span class="chip">${ev.citations.length} citations</span>
        </div>`;
      for (const ov of ev.drawing_overlays || []) renderOverlay(extras, ov);
      $("details.trace", msgEl).open = false;
      thread.scrollTop = thread.scrollHeight;
    } else if (ev.type === "error") {
      bubble.innerHTML = `<span style="color:var(--serious-text)">${esc(ev.error)}</span>`;
    }
  }
}

function renderOverlay(container, ov) {
  const W = ov.width || 2400, H = ov.height || 1520;
  const boxes = (ov.highlights || []).map(h => `
    <rect class="hl-box ${h.primary ? "primary" : ""}"
      x="${h.bbox[0]}" y="${h.bbox[1]}"
      width="${h.bbox[2] - h.bbox[0]}" height="${h.bbox[3] - h.bbox[1]}"/>
    <text x="${h.bbox[0]}" y="${h.bbox[1] - 8}" fill="#b45309"
      font-size="26" font-weight="bold">${esc(h.tag)}</text>`).join("");
  const centers = {};
  (ov.highlights || []).forEach(h => {
    centers[h.tag] = [(h.bbox[0] + h.bbox[2]) / 2, (h.bbox[1] + h.bbox[3]) / 2];
  });
  const lines = (ov.traced_edges || []).map(e => {
    const a = centers[e.src], b = centers[e.dst];
    if (!a || !b) return "";
    return `<line class="trace-line" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
  }).join("");
  container.insertAdjacentHTML("beforeend", `
    <div class="drawing-card">
      <div class="dhead"><span>📐 ${esc(ov.doc_id)} — answer shown on the drawing</span>
        <span>feed path traced</span></div>
      <div class="drawing-wrap">
        <img src="/renders/${esc(ov.render)}" alt="${esc(ov.doc_id)}">
        <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${lines}${boxes}</svg>
      </div>
    </div>`);
}

/* ---------------- RCA ---------------- */
let equipmentLoaded = false;
async function loadEquipment() {
  if (equipmentLoaded) return;
  const eq = await getJSON("/api/equipment");
  $("#rca-tag").innerHTML = eq.map(e =>
    `<option value="${e.tag}">${e.tag} — ${esc(e.service)}</option>`).join("");
  equipmentLoaded = true;
}
$("#rca-run").addEventListener("click", async () => {
  const btn = $("#rca-run");
  btn.disabled = true; btn.textContent = "analyzing…";
  $("#rca-out").innerHTML = `<div class="card">${loaderHTML("Walking the graph, reasoning over history…", "#1baf7a")}</div>`;
  try {
    const rca = await getJSON("/api/rca", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tag: $("#rca-tag").value, symptom: $("#rca-symptom").value }),
    });
    renderRCA(rca);
  } catch (e) {
    $("#rca-out").innerHTML = `<div class="card">error: ${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Analyze";
});
function renderRCA(r) {
  const causes = (r.causes || []).map(c => `
    <div class="card cause-card">
      <div class="cause-rank">${c.rank}</div>
      <div class="cause-body">
        <h4>${esc(c.cause)}</h4>
        <div>${esc(c.mechanism)}</div>
        <div class="evidence-links">evidence: ${(c.evidence || []).map(id =>
          `<span class="cite" data-evd="${esc(id)}">${esc(id)}</span>`).join(" ")}</div>
      </div>
    </div>`).join("");
  const cross = r.cross_asset_pattern || {};
  $("#rca-out").innerHTML = `
    <div class="card">
      <h4>${esc(r.equipment)} — ${esc(r.failure_mode || "")}</h4>
      <div>${md(r.summary || "")}</div>
      <div class="meta-row">
        <span class="chip">recurrence risk: <b>${esc(r.recurrence_risk?.level)}</b></span>
        <span class="chip">confidence ${((r.confidence || 0) * 100).toFixed(0)}%</span>
      </div>
      <div class="sub" style="margin-top:6px">${esc(r.recurrence_risk?.rationale || "")}</div>
    </div>
    ${cross.found ? `<div class="cross-callout">
      <div class="cross-icon">⚡</div>
      <div><h4>Cross-asset pattern detected</h4>
      <div>${esc(cross.detail)}</div>
      <div style="margin-top:6px"><b>Fleet recommendation:</b> ${esc(cross.recommendation)}</div></div>
    </div>` : ""}
    <h3 style="margin:14px 2px 8px">Evidence-ranked causes</h3>${causes}
    <div class="card">
      <h4>Actions</h4>
      <b>Corrective</b><ul>${(r.corrective_actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
      <b>Preventive</b><ul>${(r.preventive_actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
    </div>
    <h3 style="margin:14px 2px 8px">Failure timeline</h3>
    ${timelineHTML(r.timeline)}`;
}

/* ---------------- WARNINGS ---------------- */
$("#warn-refresh").addEventListener("click", () => loadWarnings(true));
async function loadWarnings(refresh = false) {
  const btn = $("#warn-refresh");
  btn.disabled = true; btn.textContent = "evaluating precursors…";
  try {
    const warns = await getJSON(`/api/warnings${refresh ? "?refresh=1" : ""}`);
    setBadge("warn-count", warns.length);
    $("#warn-out").innerHTML = warns.length ? warns.map(w => `
      <div class="card warn-card ${w.urgency === "high" ? "urgent" : ""}">
        <div class="meta-row" style="margin:0 0 6px">
          <span class="badge ${esc(w.urgency)}">⚠ ${esc(w.urgency)} urgency</span>
          <span class="chip">${esc(w.permit)} · ${esc(w.date)}</span>
          <span class="chip">${esc(w.equipment)} · ${esc(w.area)}</span>
        </div>
        <h4>${esc(w.pattern)}</h4>
        <div>${md(w.warning)}</div>
        <div style="margin-top:6px"><b>Do this:</b> ${esc(w.recommended_action)}</div>
        <div class="evidence-links">history: ${(w.historical_events || []).map(id =>
          `<span class="cite" data-evd="${esc(id)}">${esc(id)}</span>`).join(" ")}</div>
      </div>`).join("")
      : `<div class="card">No precursor matches for upcoming work. ✔</div>`;
  } catch (e) {
    $("#warn-out").innerHTML = `<div class="card">error: ${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Evaluate upcoming work";
}
async function loadPatterns() {
  try {
    const d = await getJSON("/api/patterns");
    $("#patterns-out").innerHTML = (d.priorities || []).map(p => `
      <div class="card">
        <h4>${esc(p.pattern)}</h4>
        <div class="meta-row" style="margin:0 0 6px">
          <span class="badge ${esc(p.severity)}">severity ${esc(p.severity)}</span>
          <span class="chip">preventability ${esc(p.preventability)}</span>
        </div>
        <div>${esc(p.systemic_pattern || "")}</div>
        <div style="margin-top:6px"><b>Prevention:</b> ${esc(p.prevention)}</div>
        <div class="evidence-links">${(p.events || []).map(id =>
          `<span class="cite" data-evd="${esc(id)}">${esc(id)}</span>`).join(" ")}</div>
      </div>`).join("") || `<div class="card">building patterns…</div>`;
  } catch (e) {
    $("#patterns-out").innerHTML = `<div class="card">patterns pending first run</div>`;
  }
}

/* ---------------- COMPLIANCE ---------------- */
let compLoaded = false;
async function loadCompliance(refresh = false) {
  if (compLoaded && !refresh) return;
  $("#comp-out").innerHTML = `<div class="card">${loaderHTML("Evaluating clauses against plant records…", "#2a78d6")}</div>`;
  try {
    const reg = await getJSON(`/api/compliance/register${refresh ? "?refresh=1" : ""}`);
    const counts = { gap: 0, partial: 0, satisfied: 0 };
    reg.forEach(r => counts[r.status] = (counts[r.status] || 0) + 1);
    setBadge("comp-count", counts.gap);
    $("#comp-summary").innerHTML = `
      <div class="tile"><div class="num" style="color:var(--crit-text)">${counts.gap}</div><div class="lbl">🔴 gaps</div></div>
      <div class="tile"><div class="num" style="color:var(--warn-text)">${counts.partial}</div><div class="lbl">🟡 partial</div></div>
      <div class="tile"><div class="num" style="color:var(--good-text)">${counts.satisfied}</div><div class="lbl">🟢 satisfied</div></div>
      <div class="tile"><div class="num">${reg.length}</div><div class="lbl">clauses mapped</div></div>`;
    $("#comp-out").innerHTML = reg.map(r => `
      <div class="card">
        <div class="meta-row" style="margin:0 0 6px">
          <span class="badge ${esc(r.status)}">${r.status === "gap" ? "✖" : r.status === "partial" ? "◐" : "✔"} ${esc(r.status)}</span>
          <span class="badge ${esc(r.severity)}">${esc(r.severity)}</span>
          <span class="chip">${esc(r.standard)} ${esc(r.clause)}</span>
          ${r.verbatim ? `<span class="chip">verbatim text</span>` : ""}
        </div>
        <h4>${esc(r.title)}</h4>
        <div class="sub">"${esc(r.requirement.slice(0, 220))}${r.requirement.length > 220 ? "…" : ""}"
          <a href="${esc(r.source_url)}" target="_blank" style="color:var(--s1)">source ↗</a></div>
        <div style="margin-top:6px">${esc(r.reasoning)}</div>
        ${r.gap_detail ? `<div style="margin-top:4px;color:var(--serious-text)"><b>Gap:</b> ${esc(r.gap_detail)}</div>` : ""}
        <div style="margin-top:4px"><b>Action:</b> ${esc(r.recommended_action)}</div>
        <div class="evidence-links">governs: ${r.targets.map(t => `<span class="chip">${esc(t)}</span>`).join(" ")}
          · evidence: ${(r.evidence_ids || []).map(id =>
            `<span class="cite" data-evd="${esc(id)}">${esc(id)}</span>`).join(" ") || "none on file"}</div>
      </div>`).join("");
    compLoaded = true;
  } catch (e) {
    $("#comp-out").innerHTML = `<div class="card">register build in progress or error: ${esc(e.message)}</div>`;
  }
}
$("#audit-btn").addEventListener("click", async () => {
  const btn = $("#audit-btn");
  btn.disabled = true; btn.textContent = "assembling…";
  const pack = await getJSON("/api/compliance/audit-package", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scope: $("#audit-scope").value }),
  });
  btn.disabled = false; btn.textContent = "Generate audit pack";
  const blob = new Blob([JSON.stringify(pack, null, 1)], { type: "application/json" });
  const a = Object.assign(document.createElement("a"), {
    href: URL.createObjectURL(blob),
    download: `audit-pack-${(pack.scope || "all").replace(/\W+/g, "-")}.json`,
  });
  a.click();
  alert(`Audit pack: ${pack.summary.total} clauses — ${pack.summary.gaps} gaps, ` +
        `${pack.summary.partial} partial, ${pack.summary.satisfied} satisfied. Downloaded.`);
});

/* ---------------- EVALS (dataviz: 2 series, legend, thin bars, direct values) */
async function loadEvals() {
  try {
    const d = await getJSON("/api/eval/latest");
    const m = d.aggregate;
    const delta = (a, b) => ((a - b) >= 0 ? "+" : "") + ((a - b) * 100).toFixed(0) + " pts";
    $("#eval-tiles").innerHTML = `
      <div class="tile"><div class="num">${(m.smriti.faithfulness * 100).toFixed(0)}%</div>
        <div class="lbl">faithfulness</div>
        <div class="delta up">${delta(m.smriti.faithfulness, m.baseline.faithfulness)} vs baseline</div></div>
      <div class="tile"><div class="num">${(m.smriti.citation_correctness * 100).toFixed(0)}%</div>
        <div class="lbl">citation correctness</div>
        <div class="delta up">${delta(m.smriti.citation_correctness, m.baseline.citation_correctness)} vs baseline</div></div>
      <div class="tile"><div class="num">${(m.smriti.answer_coverage * 100).toFixed(0)}%</div>
        <div class="lbl">expected-point coverage</div>
        <div class="delta up">${delta(m.smriti.answer_coverage, m.baseline.answer_coverage)} vs baseline</div></div>
      <div class="tile"><div class="num">${d.n_questions}</div><div class="lbl">golden questions</div></div>`;
    const metrics = [
      ["faithfulness", "Faithfulness (claims supported by evidence)"],
      ["citation_correctness", "Citation correctness (cited source supports claim)"],
      ["answer_coverage", "Expected-point coverage (domain answer key)"],
    ];
    $("#eval-chart").innerHTML = `
      <div class="chart-title">SMRITI vs vanilla RAG baseline</div>
      <div class="chart-sub">same corpus, same answer model — only the retrieval fabric differs · LLM-judged</div>
      <div class="legend">
        <span><span class="key" style="background:var(--s1)"></span>SMRITI (tri-modal fabric)</span>
        <span><span class="key" style="background:var(--s2)"></span>baseline (single-vector RAG)</span>
      </div>
      ${metrics.map(([k, label]) => `
        <div class="bar-group">
          <div class="bar-label">${label}</div>
          <div class="bar-track"><div class="bar s1" style="width:${m.smriti[k] * 82}%"></div>
            <span class="bar-val">${(m.smriti[k] * 100).toFixed(0)}%</span></div>
          <div class="bar-track"><div class="bar s2" style="width:${m.baseline[k] * 82}%"></div>
            <span class="bar-val">${(m.baseline[k] * 100).toFixed(0)}%</span></div>
        </div>`).join("")}`;
    $("#eval-table").innerHTML = `
      <div class="card" style="overflow-x:auto">
      <table class="evaltab">
        <tr><th>question</th><th>category</th><th>SMRITI faith.</th><th>base faith.</th><th>SMRITI cover.</th><th>base cover.</th></tr>
        ${d.per_question.map(q => `
          <tr><td>${esc(q.question.slice(0, 70))}…</td><td>${esc(q.category)}</td>
          <td>${(q.smriti.faithfulness * 100).toFixed(0)}%</td>
          <td>${(q.baseline.faithfulness * 100).toFixed(0)}%</td>
          <td>${(q.smriti.answer_coverage * 100).toFixed(0)}%</td>
          <td>${(q.baseline.answer_coverage * 100).toFixed(0)}%</td></tr>`).join("")}
      </table></div>`;
  } catch (e) {
    $("#eval-tiles").innerHTML = `<div class="tile"><div class="num">—</div>
      <div class="lbl">run eval/harness.py to populate this dashboard</div></div>`;
    $("#eval-chart").innerHTML = "";
    $("#eval-table").innerHTML = "";
  }
}

/* ---------------- ASSETS EXPLORER ---------------- */
let assetsLoaded = false;
async function loadAssets(force = false) {
  if (assetsLoaded && !force) return;
  const list = $("#assets-list");
  list.innerHTML = `<div style="padding:14px">${loaderHTML("loading assets…")}</div>`;
  try {
    const eq = await getJSON("/api/equipment");
    const byArea = {};
    eq.forEach(e => (byArea[e.area || "Unassigned"] ??= []).push(e));
    list.innerHTML = Object.keys(byArea).sort().map(area => `
      <div class="assets-group-label">${esc(area)}</div>
      ${byArea[area].map(e => `
        <button class="asset-item" data-asset="${esc(e.tag)}">
          <span class="asset-dot ${esc(e.criticality || "low")}"></span>
          <span>
            <div class="a-tag">${esc(e.tag)}</div>
            <div class="a-svc">${esc(e.service || e.type || "")}</div>
          </span>
        </button>`).join("")}`).join("");
    assetsLoaded = true;
    // auto-open the hero asset first time
    if (!$(".asset-item.active")) openAsset("P-101");
  } catch (e) {
    list.innerHTML = `<div style="padding:14px">error: ${esc(e.message)}</div>`;
  }
}
document.addEventListener("click", e => {
  const it = e.target.closest(".asset-item");
  if (it) openAsset(it.dataset.asset);
});

async function openAsset(tag) {
  $$(".asset-item").forEach(a => a.classList.toggle("active", a.dataset.asset === tag));
  const out = $("#assets-detail");
  out.innerHTML = `<div class="card">${loaderHTML("composing asset view…", "#2a78d6")}</div>`;
  try {
    const d = await getJSON(`/api/equipment/${encodeURIComponent(tag)}/summary`);
    const eqp = d.equipment, st = d.stats;
    const crit = eqp.criticality || "low";
    const metas = [
      ["Type", eqp.equipment_type], ["Service", eqp.service],
      ["Manufacturer", eqp.manufacturer], ["Model", eqp.model],
      ["Installed", eqp.install_date], ["Area", eqp.area],
      ...(eqp.seal_model ? [["Seal", eqp.seal_model]] : []),
    ].filter(([, v]) => v);
    const drawings = (d.drawings || []).map(ov => {
      const c = document.createElement("div"); renderOverlay(c, ov); return c.innerHTML;
    }).join("");
    const timeline = timelineHTML(d.timeline, 24);
    const regs = d.governing.map(g => `
      <div class="card">
        <div class="meta-row" style="margin:0 0 4px">
          <span class="chip">${esc(g.standard)} ${esc(g.clause)}</span>
          ${g.status ? `<span class="badge ${esc(g.status)}">${esc(g.status)}</span>` : ""}
        </div>
        <div>${esc(g.title)}</div>
      </div>`).join("") || `<div class="sub">No mapped regulatory clauses.</div>`;

    out.innerHTML = `
      <div class="asset-hero">
        <span class="asset-dot ${esc(crit)}" style="width:14px;height:14px;margin-top:8px"></span>
        <div><h2>${esc(eqp.id)}</h2>
          <div class="sub">${esc(eqp.service || "")} · criticality ${esc(crit)}</div></div>
      </div>
      <div class="tiles" style="padding:0;margin:12px 0">
        <div class="tile"><div class="num">${st.work_orders}</div><div class="lbl">work orders</div></div>
        <div class="tile"><div class="num" ${st.breakdowns ? 'style="color:var(--crit-text)"' : ""}>${st.breakdowns}</div><div class="lbl">breakdowns / CM</div></div>
        <div class="tile"><div class="num">${st.inspections}</div><div class="lbl">inspections</div></div>
        <div class="tile"><div class="num" ${st.incidents ? 'style="color:var(--warn-text)"' : ""}>${st.incidents}</div><div class="lbl">incidents</div></div>
      </div>
      <div class="asset-actions">
        <button class="primary" onclick="goRCA('${esc(eqp.id)}')">Run diagnostics</button>
        <button class="primary" style="background:var(--surface-2);color:var(--s1-deep);border:1px solid var(--s1-line)" onclick="askAbout('${esc(eqp.id)}')">Ask about ${esc(eqp.id)}</button>
      </div>
      <div class="asset-metagrid">
        ${metas.map(([k, v]) => `<div class="m"><div class="k">${esc(k)}</div><div class="v">${esc(v)}</div></div>`).join("")}
      </div>
      ${drawings ? `<h3 style="margin:16px 2px 6px">On the drawing</h3>${drawings}` : ""}
      <h3 style="margin:16px 2px 6px">Governing regulations</h3>${regs}
      <h3 style="margin:16px 2px 6px">History timeline</h3>
      ${timeline}`;
    out.scrollTop = 0;
  } catch (e) {
    out.innerHTML = `<div class="card">error: ${esc(e.message)}</div>`;
  }
}

/* cross-links from an asset into the reasoning agents */
function goRCA(tag) {
  activateView("rca");
  loadEquipment().then(() => { $("#rca-tag").value = tag; $("#rca-run").click(); });
}
function askAbout(tag) {
  activateView("ask");
  $("#ask-input").value = `Give me a full status on ${tag} — recent failures, root cause, and any compliance issues.`;
  $("#ask-input").focus();
}

/* ---------------- ADD DATA (assets + document upload) ---------------- */
function refreshGraphChip() {
  getJSON("/api/graph/stats").then(d => {
    const s = d.stats, ig = d.ingest;
    $("#graph-chip").innerHTML =
      `${s.nodes} nodes · ${s.edges} edges<br>${ig.text_chunks ?? "?"} chunks · ${ig.visual_pages ?? 0} visual pages`;
  }).catch(() => {});
}
/* after the fabric changes, force the derived views to reload next time */
function invalidateFabricViews() {
  assetsLoaded = false; equipmentLoaded = false; compLoaded = false;
  refreshGraphChip();
}

/* ---------------- toast notifications ---------------- */
function toast(html, kind = "ok", ms = 9000) {
  const host = $("#toasts");
  if (!host) return;
  const el = document.createElement("div");
  el.className = `toast toast-${kind}`;
  el.innerHTML = `<div class="toast-body">${html}</div>
    <button class="toast-x" aria-label="dismiss">✕</button>`;
  el.querySelector(".toast-x").onclick = () => el.remove();
  host.appendChild(el);
  requestAnimationFrame(() => el.classList.add("in"));
  if (ms) setTimeout(() => { el.classList.remove("in"); setTimeout(() => el.remove(), 300); }, ms);
}

/* ---------------- structured intake hub ---------------- */
const TODAY = new Date().toISOString().slice(0, 10);
const TOMORROW = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
const FORM_SPECS = {
  incident: {
    endpoint: "/api/records/incident", title: "Log an incident / near-miss",
    blurb: "Feeds the failure timeline, RCA and — via its precursors — the proactive warning engine.",
    submit: "Log incident", icon: "warn",
    fields: [
      { k: "date", label: "Date", type: "date", val: TODAY, req: true, half: true },
      { k: "equipment", label: "Equipment tag", ph: "e.g. P-101", req: true, half: true, tag: true },
      { k: "area", label: "Area", ph: "e.g. Area 1", half: true },
      { k: "category", label: "Category", type: "select", half: true,
        opts: ["near-miss", "mechanical", "process-upset", "fire", "gas-release", "electrical", "other"] },
      { k: "title", label: "Title", ph: "one-line summary" },
      { k: "narrative", label: "What happened", type: "area", ph: "Sequence of events…" },
      { k: "root_cause", label: "Root cause", type: "area", ph: "Why it happened…" },
      { k: "precursors", label: "Precursor conditions", type: "area", req: true,
        hint: "Warnings match future work against these — be specific (season, state, missed step).",
        ph: "e.g. monsoon; purge < 4 h; standby not aligned; gas test passed" },
      { k: "actions", label: "Corrective actions", type: "area", ph: "What was/should be done…" },
      { k: "downtime_h", label: "Downtime (h)", type: "number", half: true },
    ],
  },
  work_order: {
    endpoint: "/api/records/work-order", title: "Log a work order",
    blurb: "Lands in the equipment's maintenance timeline and becomes evidence for Diagnostics/RCA.",
    submit: "Log work order", icon: "s1",
    fields: [
      { k: "date", label: "Date", type: "date", val: TODAY, req: true, half: true },
      { k: "equipment", label: "Equipment tag", ph: "e.g. P-101", req: true, half: true, tag: true },
      { k: "wo_type", label: "Type", type: "select", half: true, opts: ["CM", "PM", "breakdown"] },
      { k: "downtime_h", label: "Downtime (h)", type: "number", half: true },
      { k: "title", label: "Title", ph: "e.g. Mechanical seal replacement" },
      { k: "findings", label: "Findings / work performed", type: "area", ph: "What was found and done…" },
      { k: "parts", label: "Parts used", ph: "e.g. mechanical seal, bearing", half: true },
      { k: "closed_by", label: "Closed by", ph: "technician name", half: true },
    ],
  },
  inspection: {
    endpoint: "/api/records/inspection", title: "Record an inspection",
    blurb: "Adds to the equipment's inspection history and re-evaluates its compliance status.",
    submit: "Record inspection", icon: "s1",
    fields: [
      { k: "date", label: "Date", type: "date", val: TODAY, req: true, half: true },
      { k: "equipment", label: "Equipment tag", ph: "e.g. T-301", req: true, half: true, tag: true },
      { k: "method", label: "Method", ph: "e.g. UT thickness, vibration, PSV pop test", half: true },
      { k: "result", label: "Result", type: "select", half: true, opts: ["pass", "advisory", "fail"] },
      { k: "text", label: "Findings / measurements", type: "area", ph: "Readings, observations…" },
    ],
  },
  permit: {
    endpoint: "/api/records/permit", title: "Raise a permit to work",
    blurb: "An upcoming permit is matched live against the plant's own incident precursor signatures.",
    submit: "Raise permit", icon: "warn",
    fields: [
      { k: "date", label: "Planned date", type: "date", val: TOMORROW, req: true, half: true,
        hint: "Today or later → evaluated as upcoming work." },
      { k: "ptype", label: "Permit type", type: "select", half: true,
        opts: ["confined space entry", "hot work", "work at height", "electrical isolation", "excavation", "other"] },
      { k: "equipment", label: "Equipment tag", ph: "e.g. TK-401", half: true, tag: true },
      { k: "area", label: "Area", ph: "e.g. Area 4", half: true },
      { k: "text", label: "Scope of work", type: "area",
        ph: "Describe the job, conditions and any deviations (e.g. shortened purge)…" },
    ],
  },
};

let intakeTab = "incident";
function fieldHTML(f) {
  const req = f.req ? ` <span class="req">*</span>` : "";
  const hint = f.hint ? `<span class="fld-hint">${esc(f.hint)}</span>` : "";
  let ctrl;
  if (f.type === "select")
    ctrl = `<select data-k="${f.k}">${f.opts.map(o => `<option value="${esc(o)}">${esc(o)}</option>`).join("")}</select>`;
  else if (f.type === "area")
    ctrl = `<textarea data-k="${f.k}" rows="3" placeholder="${esc(f.ph || "")}"></textarea>`;
  else
    ctrl = `<input data-k="${f.k}" type="${f.type || "text"}" placeholder="${esc(f.ph || "")}"
             value="${esc(f.val || "")}"${f.tag ? ' list="tag-list"' : ""}>`;
  return `<label class="${f.half ? "half" : "full"}${f.type === "area" ? " full" : ""}">
    ${esc(f.label)}${req}${ctrl}${hint}</label>`;
}
function renderIntakeForm(tab) {
  const spec = FORM_SPECS[tab], host = $("#intake-form-host");
  if (!spec || !host) return;
  host.innerHTML = `<div class="card intake-card">
    <h4>${esc(spec.title)}</h4>
    <p class="sub" style="margin-bottom:14px">${esc(spec.blurb)}</p>
    <datalist id="tag-list"></datalist>
    <div class="form intake-fields">${spec.fields.map(fieldHTML).join("")}</div>
    <button class="primary intake-submit" style="margin-top:14px">${esc(spec.submit)}</button>
    <div class="add-result intake-result"></div>
  </div>`;
  // populate tag datalist
  getJSON("/api/equipment").then(eq => {
    const dl = $("#tag-list", host);
    if (dl) dl.innerHTML = eq.map(e => `<option value="${esc(e.tag)}">`).join("");
  }).catch(() => {});
  $(".intake-submit", host).onclick = () => submitRecord(tab, spec, host);
}

async function submitRecord(tab, spec, host) {
  const body = {};
  $$("[data-k]", host).forEach(el => { const v = el.value.trim(); if (v) body[el.dataset.k] = el.dataset.k === "downtime_h" ? Number(v) : v; });
  const out = $(".intake-result", host), btn = $(".intake-submit", host);
  const missing = spec.fields.filter(f => f.req && !body[f.k]);
  if (missing.length) {
    out.innerHTML = `<div class="result-err">Required: ${missing.map(f => esc(f.label)).join(", ")}.</div>`;
    return;
  }
  btn.disabled = true;
  out.innerHTML = loaderHTML("writing typed record · linking graph · recomputing…", "#2a78d6");
  try {
    const r = await fetch(spec.endpoint, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || d.detail || `HTTP ${r.status}`);
    out.innerHTML = `<div class="result-ok">
      <b>${esc(d.created)}</b> logged
      <span class="prov-chip">${esc(d.provenance?.extractor || "manual_intake")} · confidence ${d.provenance?.confidence ?? 1.0}</span>
      <ul class="downstream">${(d.downstream || []).map(x => `<li>${esc(x)}</li>`).join("")}</ul>
    </div>`;
    // toast + deep link to the most relevant view
    const warned = (d.warnings || []).length;
    if (warned) {
      toast(`⚠️ <b>${warned} new warning${warned > 1 ? "s" : ""} triggered</b> by ${esc(d.created)} —
        matches the plant's own precursor history.
        <a href="#warn" onclick="activateView('warn')">View →</a>`, "risk", 14000);
    } else if (d.equipment) {
      toast(`<b>${esc(d.created)}</b> logged → now in <b>${esc(d.equipment)}</b>'s timeline.
        <a href="#" onclick="activateView('rca');setTimeout(()=>{const s=document.getElementById('rca-tag');if(s){s.value='${esc(d.equipment)}';}},150)">Open Diagnostics →</a>`, "ok");
    } else {
      toast(`<b>${esc(d.created)}</b> logged into the fabric.`, "ok");
    }
    // reset non-date fields
    $$("[data-k]", host).forEach(el => { if (el.type !== "date" && el.tagName !== "SELECT") el.value = ""; });
    invalidateFabricViews();
  } catch (e) {
    out.innerHTML = `<div class="result-err">${esc(e.message)}</div>`;
  }
  btn.disabled = false;
}

function switchIntakeTab(tab) {
  intakeTab = tab;
  $$(".itab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
  const structured = FORM_SPECS[tab];
  $("#intake-form-host").hidden = !structured;
  $$(".intake-panel[data-panel]").forEach(p => p.hidden = p.dataset.panel !== tab);
  if (structured) renderIntakeForm(tab);
  else if (tab === "asset") loadAssetDatalist();
}
$$("#intake-tabs .itab").forEach(t => t.addEventListener("click", () => switchIntakeTab(t.dataset.tab)));

function loadAssetDatalist() {
  getJSON("/api/equipment").then(eq => {
    const areas = [...new Set(eq.map(e => e.area).filter(Boolean))].sort();
    const dl = $("#area-list");
    if (dl) dl.innerHTML = areas.map(a => `<option value="${esc(a)}">`).join("");
  }).catch(() => {});
}
function loadAddForm() { switchIntakeTab(intakeTab); }

$("#add-asset-btn")?.addEventListener("click", async () => {
  const body = {
    tag: $("#f-tag").value, equipment_type: $("#f-type").value,
    service: $("#f-service").value, area: $("#f-area").value,
    criticality: $("#f-crit").value, manufacturer: $("#f-mfr").value,
    model: $("#f-model").value, install_date: $("#f-install").value,
  };
  const btn = $("#add-asset-btn"), out = $("#add-asset-result");
  if (!body.tag.trim()) { out.innerHTML = `<div class="result-err">Tag is required.</div>`; return; }
  btn.disabled = true; out.innerHTML = loaderHTML("adding to the fabric…", "#2a78d6");
  try {
    const r = await fetch("/api/equipment", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    out.innerHTML = `<div class="result-ok"><b>${esc(d.tag)}</b> added to
      <b>${esc(d.area)}</b> — now live in Assets, Diagnostics and search.
      <a href="#assets" onclick="activateView('assets');setTimeout(()=>openAsset('${esc(d.tag)}'),150)">Open ${esc(d.tag)} →</a></div>`;
    ["f-tag","f-type","f-service","f-mfr","f-model","f-install"].forEach(i => $("#"+i).value = "");
    invalidateFabricViews();
  } catch (e) {
    out.innerHTML = `<div class="result-err">${esc(e.message)}</div>`;
  }
  btn.disabled = false;
});

/* upload documents (multi-file, auto-classified) */
const dz = $("#dropzone"), docFile = $("#doc-file"), upBtn = $("#upload-btn");
let pendingFiles = [];
const TYPE_LABEL = {
  work_order: "Work order", inspection: "Inspection", incident: "Incident / near-miss",
  permit: "Permit to work", sop: "SOP (procedure)", equipment: "Equipment",
  oem_manual: "OEM manual", regulatory: "Regulation", email: "Email", generic: "Document",
};
function setFiles(list) {
  pendingFiles = Array.from(list || []);
  const n = pendingFiles.length;
  $("#dz-text").textContent = n
    ? (n === 1 ? `${pendingFiles[0].name} (${(pendingFiles[0].size/1024).toFixed(0)} KB)`
               : `${n} files selected`)
    : "Drop files here, or click to choose (multiple allowed)";
  upBtn.disabled = !n;
}
dz?.addEventListener("click", () => docFile.click());
docFile?.addEventListener("change", () => setFiles(docFile.files));
["dragover","dragenter"].forEach(ev => dz?.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("drag"); }));
["dragleave","drop"].forEach(ev => dz?.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("drag"); }));
dz?.addEventListener("drop", e => { if (e.dataTransfer.files.length) setFiles(e.dataTransfer.files); });

function docResultHTML(doc) {
  const type = TYPE_LABEL[doc.detected_type] || doc.detected_type;
  const lands = (doc.created || []).map(c => {
    if (c.in_timeline) return "now in the failure timeline";
    if (c.feeds_warnings) return "feeding Warnings";
    if (c.in_assets) return "now in Assets";
    if (c.supersedes) return `current revision (supersedes ${esc(c.supersedes)})`;
    if (c.in_search) return "searchable in Ask";
    return "indexed";
  });
  const ids = (doc.created || []).map(c => esc(c.id)).filter(Boolean).join(", ");
  return `<div class="result-ok" style="margin-bottom:8px">
    <span class="ent" style="background:#2a78d611;border-color:#2a78d644">Detected: <b>${esc(type)}</b></span>
    <b>${esc(doc.doc_id)}</b> → <b>${ids || "indexed"}</b>${lands.length ? " — " + lands.join(", ") + "." : "."}
    ${doc.new_equipment?.length ? `<br>New asset(s): <b>${doc.new_equipment.map(esc).join(", ")}</b>.` : ""}
    <br><span class="sub">${esc(doc.summary || "")}</span>
  </div>`;
}

upBtn?.addEventListener("click", async () => {
  if (!pendingFiles.length) return;
  const out = $("#upload-result");
  upBtn.disabled = true;
  out.innerHTML = loaderHTML(`classifying · extracting typed records · indexing (${pendingFiles.length} file${pendingFiles.length>1?"s":""})…`, "#d97706");
  try {
    const fd = new FormData();
    pendingFiles.forEach(f => fd.append("files", f));
    const r = await fetch("/api/ingest", { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || d.detail || `HTTP ${r.status}`);
    out.innerHTML = (d.documents || []).map(docResultHTML).join("")
      + `<div style="margin-top:4px" class="sub">${d.ingested} document(s) ingested — ask about them in
         <a href="#" onclick="activateView('ask')">Ask</a>, or open <a href="#" onclick="activateView('assets')">Assets</a>.</div>`;
    setFiles([]); docFile.value = "";
    invalidateFabricViews();
  } catch (e) {
    out.innerHTML = `<div class="result-err">${esc(e.message)}</div>`;
  }
  upBtn.disabled = false;
});

/* bulk table import (CMMS export → typed records, no per-row LLM) */
const bulkDz = $("#bulk-dropzone"), bulkFile = $("#bulk-file"), bulkBtn = $("#bulk-btn");
let pendingBulk = null;
function setBulk(f) {
  pendingBulk = f;
  $("#bulk-dz-text").textContent = f ? `${f.name} (${(f.size/1024).toFixed(0)} KB)` : "Drop a CSV/JSON here, or click to choose";
  bulkBtn.disabled = !f;
}
bulkDz?.addEventListener("click", () => bulkFile.click());
bulkFile?.addEventListener("change", () => setBulk(bulkFile.files[0]));
["dragover","dragenter"].forEach(ev => bulkDz?.addEventListener(ev, e => { e.preventDefault(); bulkDz.classList.add("drag"); }));
["dragleave","drop"].forEach(ev => bulkDz?.addEventListener(ev, e => { e.preventDefault(); bulkDz.classList.remove("drag"); }));
bulkDz?.addEventListener("drop", e => { if (e.dataTransfer.files[0]) setBulk(e.dataTransfer.files[0]); });

bulkBtn?.addEventListener("click", async () => {
  if (!pendingBulk) return;
  const rtype = $("#bulk-type").value, out = $("#bulk-result");
  bulkBtn.disabled = true;
  out.innerHTML = loaderHTML("mapping columns · materialising typed records…", "#1baf7a");
  try {
    const fd = new FormData();
    fd.append("file", pendingBulk);
    const r = await fetch(`/api/ingest/table?record_type=${encodeURIComponent(rtype)}`, { method: "POST", body: fd });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || d.detail || `HTTP ${r.status}`);
    out.innerHTML = `<div class="result-ok">
      <b>${d.created}</b> ${esc(TYPE_LABEL[d.record_type] || d.record_type)} record(s) imported from
      ${d.rows} row(s)${d.errors ? `, ${d.errors} skipped` : ""}.
      ${d.new_equipment?.length ? `<br>New asset(s) created: <b>${d.new_equipment.map(esc).join(", ")}</b>.` : ""}
      <br><span class="sub">Live now — visible in Assets, Diagnostics timelines, Warnings and Compliance.</span>
    </div>`;
    setBulk(null); bulkFile.value = "";
    invalidateFabricViews();
  } catch (e) {
    out.innerHTML = `<div class="result-err">${esc(e.message)}</div>`;
  }
  bulkBtn.disabled = false;
});
