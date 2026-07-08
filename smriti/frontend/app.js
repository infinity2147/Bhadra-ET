/* SMRITI frontend — vanilla JS, no build step. */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

/* ---------------- sidebar nav (with #hash deep links) ---------------- */
const SECTION_TITLES = {
  ask: "Ask the plant's memory",
  rca: "Root Cause Analysis",
  warn: "Proactive Warnings",
  comp: "Compliance Register",
  eval: "Evaluation — measured, not claimed",
};
function activateView(v) {
  $$(".nav-item").forEach(t => t.classList.toggle("active", t.dataset.view === v));
  $$(".view").forEach(s => s.classList.toggle("active", s.id === `view-${v}`));
  const title = $("#section-title");
  if (title && SECTION_TITLES[v]) title.textContent = SECTION_TITLES[v];
  document.querySelector(".app")?.classList.remove("nav-open");  // close mobile drawer
  history.replaceState(null, "", `#${v}`);
  if (v === "comp") loadCompliance();
  if (v === "warn") { loadPatterns(); loadWarnings(false); }
  if (v === "eval") loadEvals();
  if (v === "rca") loadEquipment();
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
  const v = location.hash.slice(1);
  if (["rca", "warn", "comp", "eval"].includes(v)) activateView(v);
});

/* ---------------- helpers ---------------- */
function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
function md(s) { // minimal: **bold**, newlines preserved by CSS
  return esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
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

/* ---------------- ASK (SSE chat) ---------------- */
const thread = $("#thread");
$("#ask-form").addEventListener("submit", e => { e.preventDefault(); sendAsk(); });
$$(".sugg").forEach(b => b.addEventListener("click", () => {
  $("#ask-input").value = b.textContent.trim();
  sendAsk();
}));

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
      <details class="trace" open><summary>reasoning trace</summary>
        <div class="tsteps"></div></details>
      <div class="bubble"><span class="thinking">thinking…</span></div>
      <div class="extras"></div>
    </div>`);
  const msgEl = $(`#${id}`);
  const bubble = $(".bubble", msgEl);
  const tsteps = $(".tsteps", msgEl);
  thread.scrollTop = thread.scrollHeight;

  let acc = "";
  try {
    const resp = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q }),
    });
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
    bubble.innerHTML = `<span style="color:var(--serious-text)">connection error: ${esc(err.message)}</span>`;
  }
  $("#ask-send").disabled = false;

  function handleEvent(ev) {
    if (ev.type === "trace") {
      const bits = [];
      if (ev.step === "route") bits.push(`<b>router</b> → ${ev.modalities?.join(" + ")} · intent ${esc(ev.intent)} ${ev.tags?.length ? "· tags " + ev.tags.join(", ") : ""}`);
      else if (ev.step === "text_search") bits.push(`<b>text</b> hybrid dense+BM25 → ${ev.hits?.map(h => h[0]).slice(0, 5).join(", ")}`);
      else if (ev.step === "graph_traverse") bits.push(`<b>graph</b> traversed ${ev.tags?.join(", ")} → ${ev.items} evidence sets`);
      else if (ev.step === "visual_search") bits.push(ev.error ? `<b>visual</b> unavailable` : `<b>visual</b> ColPali page match (no OCR) → ${ev.hits?.map(h => `${h[0]} p${String(h[1]).replace("p","")}`).join(", ") || "none"}`);
      else if (ev.step === "rerank") bits.push(`<b>rerank</b> cross-encoder kept ${ev.kept?.map(k => k[0]).slice(0, 6).join(", ")}`);
      else if (ev.step === "drawing_overlay") bits.push(`<b>overlay</b> preparing ${ev.drawings?.join(", ")}`);
      else return;
      tsteps.insertAdjacentHTML("beforeend", `<div class="tstep">${bits[0]}</div>`);
    } else if (ev.type === "delta") {
      acc += ev.text;
      bubble.innerHTML = md(acc);
      thread.scrollTop = thread.scrollHeight;
    } else if (ev.type === "final") {
      lastCitations = ev.all_evidence;
      bubble.innerHTML = citeChips(md(ev.answer), ev.all_evidence);
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
  $("#rca-out").innerHTML = `<div class="card"><span class="thinking">walking the graph, reasoning over history…</span></div>`;
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
    <div class="card">
      <h4>#${c.rank} — ${esc(c.cause)}</h4>
      <div>${esc(c.mechanism)}</div>
      <div class="evidence-links">${(c.evidence || []).map(id =>
        `<span class="cite" data-evd="${esc(id)}">${esc(id)}</span>`).join(" ")}</div>
    </div>`).join("");
  const timeline = (r.timeline || []).map(e => `
    <tr><td>${esc(e.date)}</td><td><span class="cite" data-evd="${esc(e.id)}">${esc(e.id)}</span></td>
    <td>${esc(e.kind)}</td><td>${esc(e.what)}</td></tr>`).join("");
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
    ${cross.found ? `<div class="card warn-card">
      <h4>⚡ Cross-asset pattern detected</h4>
      <div>${esc(cross.detail)}</div>
      <div style="margin-top:6px"><b>Fleet recommendation:</b> ${esc(cross.recommendation)}</div>
    </div>` : ""}
    <h3 style="margin:14px 2px 8px">Evidence-ranked causes</h3>${causes}
    <div class="card">
      <h4>Actions</h4>
      <b>Corrective</b><ul>${(r.corrective_actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
      <b>Preventive</b><ul>${(r.preventive_actions || []).map(a => `<li>${esc(a)}</li>`).join("")}</ul>
    </div>
    <h3 style="margin:14px 2px 8px">Failure timeline</h3>
    <div class="card" style="overflow-x:auto">
      <table class="evaltab"><tr><th>date</th><th>record</th><th>type</th><th>event</th></tr>${timeline}</table>
    </div>`;
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
  $("#comp-out").innerHTML = `<div class="card"><span class="thinking">evaluating clauses against plant records…</span></div>`;
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
