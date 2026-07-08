// v3 invention cockpit — pick a topic + lens + prompt → invent (rule-based) → simulate → render.
// The stage shows a live scorecard bar chart of all 10 topics; cards show the verdict + design.

import { TOPICS, TOPIC_IDS, LENSES, invent, simulate } from './catalog.js';

const $ = (id) => document.getElementById(id);
const scores = {};                 // tid -> {score, passed, fidelity}
let selected = TOPIC_IDS[0];

// Optional Python backend (FastAPI). If it's up, 'Invent + Simulate' routes there so the real
// LLM lenses + critique loop run (and your local Qwen, if wired). Otherwise the browser proposer.
// Default: same origin — so `bci serve` (API + cockpit on one port) works with zero config.
const API = localStorage.getItem('bciv3_api') || location.origin;
let apiUp = false, apiProvider = null;

async function probeApi() {
  try {
    const r = await fetch(API + '/api/health', { signal: AbortSignal.timeout(1200) });
    if (!r.ok) return;
    const h = await r.json();
    apiUp = true; apiProvider = h.backends?.provider || null;
    $('backend').textContent = apiProvider ? `${apiProvider} (backend)` : 'backend (no LLM)';
  } catch { apiUp = false; }
}

// The chosen LLM model, or '' to use the backend/.env default. Auto-detected from the provider.
const modelVal = () => ($('model') && $('model').value) || '';

async function loadModels() {
  const sel = $('model'), lbl = $('model-lbl'), hint = $('model-hint');
  if (!sel) return;
  if (!apiUp) {                                   // browser-only mode — no live model list
    sel.innerHTML = '<option value="">backend only</option>';
    sel.disabled = true; if (lbl) lbl.style.opacity = 0.5;
    if (hint) hint.textContent = '(run bci serve)';
    return;
  }
  try {
    const r = await fetch(API + '/api/models', { signal: AbortSignal.timeout(4000) });
    const d = await r.json();
    const models = d.models || [];
    sel.innerHTML = '';
    if (!models.length) {                          // no LLM wired — default to .env / rule-based
      sel.innerHTML = '<option value="">provider default</option>';
      sel.disabled = true; if (hint) hint.textContent = d.provider ? '(none detected)' : '(no LLM)';
      return;
    }
    for (const m of models) {
      const o = document.createElement('option'); o.value = m; o.textContent = m;
      sel.appendChild(o);
    }
    sel.value = d.current && models.includes(d.current) ? d.current : models[0];
    sel.disabled = false; if (lbl) lbl.style.opacity = 1;
    if (hint) hint.textContent = `· ${models.length} detected`;
    syncEngineLabel();
  } catch {
    sel.innerHTML = '<option value="">provider default</option>'; sel.disabled = true;
  }
}

// reflect the active provider + chosen model in the engine card
function syncEngineLabel() {
  if (!apiUp) return;
  const m = modelVal();
  $('backend').textContent = apiProvider ? `${apiProvider}${m ? ' · ' + m : ''} (backend)` : 'backend (no LLM)';
}

// ---- populate selectors ----
for (const tid of TOPIC_IDS) {
  const o = document.createElement('option');
  o.value = tid; o.textContent = TOPICS[tid].title;
  $('topic').appendChild(o);
}
for (const ln of LENSES) {
  const o = document.createElement('option'); o.value = ln; o.textContent = ln;
  $('lens').appendChild(o);
}
$('lens').value = 'biomimicry';

// ---- chart ----
const canvas = $('chart'), ctx = canvas.getContext('2d');
function resize() {
  const r = canvas.getBoundingClientRect(), dpr = Math.min(devicePixelRatio, 2);
  canvas.width = r.width * dpr; canvas.height = r.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}
addEventListener('resize', resize);

function draw() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  // central band, clear of the left controls card (~282px) and right verdict card (~262px)
  const x0 = 300, x1 = w - 285, padT = 78, padB = 26;
  const n = TOPIC_IDS.length, rowH = (h - padT - padB) / n, barH = 16;
  // title (centered in the band)
  ctx.textAlign = 'center'; ctx.font = '700 15px "Hanken Grotesk", sans-serif'; ctx.fillStyle = '#0d0d0f';
  ctx.fillText('Invented designs graded by the law simulator', (x0 + x1) / 2, 40);
  ctx.textAlign = 'left';
  const xmid = x0 + (x1 - x0) * 0.5;
  ctx.strokeStyle = '#c9c9d0'; ctx.setLineDash([4, 4]); ctx.beginPath();
  ctx.moveTo(xmid, padT - 10); ctx.lineTo(xmid, h - padB); ctx.stroke(); ctx.setLineDash([]);
  ctx.font = '10px "JetBrains Mono", monospace'; ctx.fillStyle = '#9a9aa2';
  ctx.fillText('pass ≥ 0.5', xmid + 4, padT - 14);

  TOPIC_IDS.forEach((tid, i) => {
    const y = padT + i * rowH, s = scores[tid], by = y + rowH / 2 - barH / 2 + 6;
    // label ABOVE the bar (always in the clear band)
    ctx.font = (tid === selected ? '700 ' : '') + '12px "Hanken Grotesk", sans-serif';
    ctx.fillStyle = tid === selected ? '#635bff' : '#33333b';
    ctx.fillText((i + 1) + '. ' + TOPICS[tid].title.replace(/ \(.*\)/, ''), x0, y + 10);
    // track + bar
    ctx.fillStyle = '#e7e7ea'; roundRect(x0, by, x1 - x0, barH, 5); ctx.fill();
    if (s) {
      const bw = (x1 - x0) * s.score;
      ctx.fillStyle = s.passed ? '#0e9f6e' : '#e0332d';
      roundRect(x0, by, bw, barH, 5); ctx.fill();
      ctx.font = '10px "JetBrains Mono", monospace'; ctx.fillStyle = '#6f6f78';
      ctx.textAlign = 'right'; ctx.fillText(s.fidelity, x1, by + barH + 12); ctx.textAlign = 'left';
    }
  });
}
function roundRect(x, y, w, h, r) {
  r = Math.min(r, h / 2, w / 2); if (w < 0) w = 0;
  ctx.beginPath(); ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}

// ---- run one invention (backend if up → real LLM lenses; else browser proposer) ----
function runLocal(tid) {
  const cand = invent(tid, $('prompt').value);
  const s = simulate(tid, cand);
  scores[tid] = { score: s.score, passed: s.passed, fidelity: TOPICS[tid].fidelity };
  return { cand, s };
}

function saveLocal(tid, cand, s) {   // browser fallback when no backend — light record to localStorage
  const id = 'loc_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
  const rec = { id, topic: tid, title: cand.title, params: cand.params,
    score: { passed: s.passed, score: +(+s.score).toFixed(4), fidelity: TOPICS[tid].fidelity, limiting: s.limiting } };
  const all = JSON.parse(localStorage.getItem('bciv3_saved') || '[]');
  all.push(rec); localStorage.setItem('bciv3_saved', JSON.stringify(all));
  return rec;
}

async function runOne(tid, { save = false } = {}) {
  if (apiUp) {
    try {
      const ep = save ? '/api/record' : '/api/invent';
      const r = await fetch(API + ep, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ topic: tid, prompt: $('prompt').value, lens: $('lens').value,
                               backend: 'auto', model: modelVal() || null,
                               ground: $('ground') ? $('ground').checked : false }),
        signal: AbortSignal.timeout(180000),
      });
      const d = await r.json();
      if (d.error) throw new Error(d.error);
      if (save) {
        const rec = d.record;
        scores[tid] = { score: rec.score.score, passed: rec.score.passed, fidelity: rec.score.fidelity };
        return { cand: { title: rec.title, params: rec.params, mechanism: rec.mechanism, assumptions: rec.assumptions,
                         risks: rec.risks, lens: rec.lens, backend: rec.backend, provider: rec.provider },
          s: rec.score, detail: rec.detail, parts: rec.parts, citations: rec.citations, grounded: rec.grounded,
          id: rec.id, saved: true, store: d.store };
      }
      const res = d.result, cand = { ...d.candidate };
      scores[tid] = { score: res.score, passed: res.passed, fidelity: res.fidelity };
      return { cand, s: { score: res.score, passed: res.passed, limiting: res.limiting, metrics: res.metrics } };
    } catch (e) {
      apiUp = false; $('backend').textContent = 'rule-based (browser)';
    }
  }
  const { cand, s } = runLocal(tid);
  const saved = save ? saveLocal(tid, cand, s) : null;
  return { cand, s, detail: null, parts: null, id: saved && saved.id, saved: !!saved, store: 'browser (localStorage)' };
}

function showVerdict(tid, cand, s, extra = {}) {
  const t = TOPICS[tid];
  $('v-title').textContent = t.title;
  const pass = $('v-pass'); pass.textContent = s.passed ? 'PASS ✓' : 'FAIL ✗';
  pass.className = 'pill ' + (s.passed ? 'pass' : 'fail');
  $('v-fid').textContent = t.fidelity;
  $('v-score').textContent = s.score.toFixed(3);
  $('v-limit').textContent = s.limiting;
  $('v-tags').innerHTML = t.layer.map((l) => `<span class="tag ${l}">${l}</span>`).join('');
  $('v-metrics').innerHTML = Object.entries(s.metrics).map(([k, v]) =>
    `<div class="statrow"><span>${k}</span><b>${fmt(v)}</b></div>`).join('');
  // candidate aside
  $('c-title').textContent = cand.title;
  $('c-domain').textContent = `${t.domain} · laws: ${t.laws.join(', ')}`;
  $('c-params').innerHTML = Object.entries(cand.params).map(([k, v]) =>
    `<div class="kv"><span>${k}</span><b>${fmt(v)}</b></div>`).join('');
  const li = (arr, fb) => (arr && arr.length ? arr : fb).map((x) => `<li>${esc(x)}</li>`).join('');
  $('c-assume').innerHTML = li(cand.assumptions, ['spec-aware proposal', 'assumptions unverified in vivo']);
  $('c-risks').innerHTML = li(cand.risks, ['passes = physically admissible, not proven in a living brain']);
  // mechanism (LLM path) + provenance
  const via = cand.backend === 'llm' ? `${cand.provider || 'llm'} · lens: ${cand.lens || '?'}`
            : cand.backend === 'llm-refine' ? 'llm (refined)' : 'rule-based';
  $('c-mech').innerHTML = cand.mechanism ? `<div class="eyebrow" style="margin-top:.6rem">Mechanism</div><p class="small" style="color:var(--ink-2)">${esc(cand.mechanism)}</p>` : '';
  $('c-via').textContent = 'via ' + via;
  // multi-domain detail (from the backend record) + parts + save status
  const det = extra.detail, parts = extra.parts;
  $('c-detail').innerHTML = det ? '<hr class="divider"/><div class="eyebrow">Law simulator · biophysics · physics · electronics</div>' +
    ['biophysics', 'physics', 'electronics', 'biology'].filter((k) => det[k] && det[k] !== '—')
      .map((k) => `<div class="detsec"><span class="lbl">${k}</span><p>${esc(det[k])}</p></div>`).join('') : '';
  $('c-parts').innerHTML = (parts && parts.length) ? '<div class="eyebrow" style="margin-top:.5rem">Parts</div>' +
    parts.map((p) => `<div class="part"><b>${esc(p.name)}</b><span>${esc(p.role)}</span></div>`).join('') : '';
  const cites = extra.citations;
  $('c-cites').innerHTML = (cites && cites.length)
    ? `<div class="eyebrow" style="margin-top:.5rem">Grounded in literature (${cites.length})</div>` +
      cites.slice(0, 8).map((c) => `<span class="cite"><span class="src">${esc(c.source)}</span>` +
        `<a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.title)}</a></span>`).join('')
    : (extra.grounded === false && $('ground') && $('ground').checked
        ? '<div class="eyebrow" style="margin-top:.5rem">Literature</div><div class="muted small">no results (offline or sources unreachable)</div>' : '');
  $('c-saved').textContent = extra.saved ? `✓ auto-saved to ${extra.store || 'database'} (id ${String(extra.id).slice(0, 10)})` : '';
}

function esc(s) { return String(s).replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c])); }

function fmt(v) {
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (typeof v !== 'number') return String(v);
  if (v !== 0 && (Math.abs(v) >= 1e5 || Math.abs(v) < 1e-3)) return v.toExponential(2);
  return (Math.round(v * 1000) / 1000).toString();
}

// ---- events ----
const setStatus = (t) => { const e = $('invent-status'); if (e) e.textContent = t; };

async function inventSelected() {
  selected = $('topic').value;
  const grounding = $('ground') && $('ground').checked;
  $('invent').disabled = true;
  $('invent').textContent = '⏳ working…';
  // show the pipeline steps so the simulator (last step) is visible
  setStatus(apiUp
    ? (grounding ? '① 🔎 searching literature  →  ② 🧠 inventing (LLM)  →  ③ ⚖️ simulating…'
                 : '① 🧠 inventing (LLM)  →  ② ⚖️ simulating…')
    : '⚖️ simulating (rule-based)…');
  const out = await runOne(selected, { save: true });     // auto-save every invention
  showVerdict(selected, out.cand, out.s, out); draw();
  setStatus('✓ ⚖️ simulated — verdict + biophysics/physics/electronics on the right');
  setTimeout(() => setStatus(''), 5000);
  $('invent').disabled = false;
  $('invent').textContent = '✨ Invent + Simulate';
}
$('topic').addEventListener('change', inventSelected);
$('invent').addEventListener('click', inventSelected);
$('all').addEventListener('click', async () => {
  $('all').textContent = '… grading all';
  for (const tid of TOPIC_IDS) { await runOne(tid); draw(); }
  const { cand, s } = await runOne(selected); showVerdict(selected, cand, s); draw();
  $('all').textContent = 'grade all 10 topics';
});

// ---- lens tournament (3 / 5 / 10 lenses) ----
let nLenses = 5;
document.querySelectorAll('#lensn button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('#lensn button').forEach((x) => x.classList.remove('on'));
  b.classList.add('on'); nLenses = +b.dataset.n;
}));

async function tournament() {
  const tid = $('topic').value, box = $('tourn');
  const head = `<hr class="divider"/><div class="eyebrow">Lens tournament · ${nLenses} lenses</div>`;
  box.innerHTML = head + '<div class="muted small">running…</div>';
  $('tournament').textContent = '… running tournament';
  let ranked = null, note = '';
  if (apiUp) {
    try {
      const r = await fetch(API + '/api/rank', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ topic: tid, prompt: $('prompt').value, backend: 'auto',
                               n_lenses: nLenses, model: modelVal() || null }),
        signal: AbortSignal.timeout(180000),
      });
      const d = await r.json();
      if (!d.error) ranked = d.ranked;
    } catch { apiUp = false; }
  }
  if (!ranked) {
    ranked = LENSES.slice(0, nLenses).map((ln) => {
      const c = invent(tid, $('prompt').value), s = simulate(tid, c);
      return { lens: ln, passed: s.passed, score: +s.score.toFixed(3), limiting: s.limiting };
    }).sort((a, b) => b.score - a.score);
    note = '<div class="muted small" style="margin:.2rem 0">Browser proposer is lens-agnostic — run <b>bci serve</b> with a local LLM for real per-lens diversity.</div>';
  }
  box.innerHTML = head + note + ranked.map((r) =>
    `<div class="tourn-row"><span class="dot ${r.passed ? 'p' : 'f'}"></span>` +
    `<span class="ln">${esc(r.lens)}</span><span class="sc">${(+r.score).toFixed(3)}</span></div>`).join('');
  $('tournament').textContent = '🏆 Run lens tournament';
}
$('tournament').addEventListener('click', tournament);

// ---- saved inventions, grouped by the 10 innovation categories ----
async function loadGroups() {
  if (apiUp) {
    try {
      const r = await fetch(API + '/api/inventions/grouped', { signal: AbortSignal.timeout(4000) });
      const d = await r.json();
      if (d.groups) return { groups: d.groups, store: d.store };
    } catch { apiUp = false; }
  }
  const all = JSON.parse(localStorage.getItem('bciv3_saved') || '[]');
  const groups = {}; TOPIC_IDS.forEach((t) => (groups[t] = []));
  all.forEach((r) => (groups[r.topic] = groups[r.topic] || []).push(r));
  TOPIC_IDS.forEach((t) => groups[t].sort((a, b) => b.score.score - a.score.score));
  return { groups, store: 'browser (localStorage)' };
}

const savedById = {};       // id → full record, for the click-to-read detail view

async function renderSaved() {
  const { groups, store } = await loadGroups();
  $('saved-store').textContent = 'store: ' + store;
  const box = $('saved-groups');
  Object.keys(savedById).forEach((k) => delete savedById[k]);
  box.innerHTML = TOPIC_IDS.map((tid, i) => {
    const rows = groups[tid] || [];
    rows.forEach((r) => { savedById[r.id] = r; });
    const inner = rows.length ? rows.map((r) =>
      `<div class="inv-row" data-id="${esc(r.id)}" title="click to read the full invention"><span class="dot ${r.score.passed ? 'p' : 'f'}"></span>` +
      `<span class="ti">${esc(r.title || TOPICS[tid].title)}</span>` +
      `<span class="sc">${(+r.score.score).toFixed(3)}</span>` +
      `<button class="del" data-id="${esc(r.id)}" title="delete">🗑</button></div>`).join('')
      : '<div class="cat-empty">no saved inventions yet</div>';
    return `<div class="cat"><h3>${i + 1}. ${esc(TOPICS[tid].title)} <span class="n">${rows.length}</span></h3>${inner}</div>`;
  }).join('');
  box.querySelectorAll('.del').forEach((btn) =>
    btn.addEventListener('click', (e) => { e.stopPropagation(); deleteInv(btn.dataset.id); }));
  box.querySelectorAll('.inv-row').forEach((row) =>
    row.addEventListener('click', () => openInvDetail(savedById[row.dataset.id])));
}

function _list(title, arr) {
  return (arr && arr.length) ? `<div class="id-sec"><h4>${title}</h4><ul>${arr.map((x) => `<li>${esc(x)}</li>`).join('')}</ul></div>` : '';
}

function openInvDetail(rec) {
  if (!rec) return;
  const s = rec.score || {}, d = rec.detail || {};
  const domains = ['biophysics', 'physics', 'electronics', 'biology'].filter((k) => d[k] && d[k] !== '—')
    .map((k) => `<div class="id-domain"><span class="dl">${k}</span><span>${esc(d[k])}</span></div>`).join('');
  const params = Object.entries(rec.params || {}).map(([k, v]) =>
    `<span class="k">${esc(k)}</span><span class="v">${esc(typeof v === 'number' ? (+v).toLocaleString() : v)}</span>`).join('');
  const parts = (rec.parts || []).map((p) => `<li><b>${esc(p.name)}</b> — ${esc(p.role)}</li>`).join('');
  const cites = (rec.citations || []).map((c) =>
    `<span class="id-cite"><span class="src">${esc(c.source)}</span><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.title)}</a></span>`).join('');
  const via = rec.backend === 'llm' ? `${rec.provider || 'llm'} · lens ${rec.lens || '?'}` : rec.backend || '—';
  $('invdetail-body').innerHTML =
    `<div class="eyebrow">${esc(TOPIC_TITLE(rec.topic))}</div>` +
    `<h2>${esc(rec.title || '')}</h2>` +
    `<div class="id-meta"><span>${esc(rec.domain || '')}</span><span>via <b>${esc(via)}</b></span>` +
    `<span>${s.passed ? 'PASS ✓' : 'FAIL ✗'} · score <b>${s.score}</b> · ${esc(s.fidelity || '')}</span>` +
    `<span>limiting: ${esc(s.limiting || '')}</span>${rec.grounded ? '<span>🔎 grounded</span>' : ''}` +
    `<span>${esc(String(rec.ts || '').slice(0, 19).replace('T', ' '))}</span></div>` +
    (rec.prompt ? `<div class="id-sec"><h4>Prompt</h4><p>${esc(rec.prompt)}</p></div>` : '') +
    (rec.mechanism ? `<div class="id-sec"><h4>Mechanism</h4><p>${esc(rec.mechanism)}</p></div>` : '') +
    (domains ? `<div class="id-sec"><h4>Law simulator · biophysics · physics · electronics</h4>${domains}</div>` : '') +
    (params ? `<div class="id-sec"><h4>Parameters</h4><div class="id-kv">${params}</div></div>` : '') +
    _list('Materials', rec.materials) +
    _list('Protocol steps', rec.protocol_steps) +
    (parts ? `<div class="id-sec"><h4>Parts</h4><ul>${parts}</ul></div>` : '') +
    _list('Assumptions', rec.assumptions) +
    _list('Risks', rec.risks) +
    (cites ? `<div class="id-sec"><h4>Grounded in literature (${rec.citations.length})</h4>${cites}</div>` : '');
  $('invdetail').hidden = false;
}

$('close-invdetail').addEventListener('click', () => { $('invdetail').hidden = true; });
$('invdetail').addEventListener('click', (e) => { if (e.target.id === 'invdetail') $('invdetail').hidden = true; });

async function deleteInv(id) {
  if (apiUp && !String(id).startsWith('loc_')) {
    try { await fetch(API + '/api/inventions/' + encodeURIComponent(id), { method: 'DELETE' }); } catch { apiUp = false; }
  }
  if (String(id).startsWith('loc_') || !apiUp) {
    const all = JSON.parse(localStorage.getItem('bciv3_saved') || '[]').filter((r) => r.id !== id);
    localStorage.setItem('bciv3_saved', JSON.stringify(all));
  }
  renderSaved();
}

$('open-saved').addEventListener('click', () => { $('saved').hidden = false; renderSaved(); });
$('close-saved').addEventListener('click', () => { $('saved').hidden = true; });
$('saved').addEventListener('click', (e) => { if (e.target.id === 'saved') $('saved').hidden = true; });

// ---- benchmark leaderboard ----
const TOPIC_TITLE = (t) => (TOPICS[t] ? TOPICS[t].title : t);

function renderLeaderboard(res) {
  const rows = Object.entries(res.per_topic || {})
    .sort((a, b) => (b[1].mean_score - a[1].mean_score));
  const head = `<div class="bench-head"><span>model <b>${esc(res.model || res.provider || 'rule-based')}</b></span>` +
    `<span>samples/topic <b>${res.samples_per_topic}</b></span>` +
    `<span>mean pass-rate <b>${res.mean_pass_rate}</b></span>` +
    `<span>mean score <b>${res.mean_score}</b></span></div>`;
  const body = rows.map(([tid, t]) =>
    `<tr><td>${esc(TOPIC_TITLE(tid))}</td>` +
    `<td>${t.pass_rate}</td>` +
    `<td>${t.mean_score.toFixed(3)} <span class="bench-bar" style="width:${Math.round(t.mean_score * 60)}px"></span></td>` +
    `<td>${t.best_score.toFixed(3)}</td><td>${t.samples}</td></tr>`).join('');
  return head + `<table class="bench-table"><thead><tr><th>topic</th><th>pass-rate</th><th>mean</th><th>best</th><th>n</th></tr></thead><tbody>${body}</tbody></table>`;
}

async function runBench() {
  if (!apiUp) { $('bench-result').innerHTML = '<div class="muted small">Benchmarking needs the Python backend — run <b>bci serve</b>.</div>'; return; }
  const samples = Math.max(1, Math.min(10, +$('bench-samples').value || 2));
  $('run-bench').disabled = true;
  $('bench-status').textContent = `running ${samples}×10 = ${samples * 10} inventions…`;
  try {
    const r = await fetch(API + '/api/bench', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ samples, backend: 'auto', ground: false }),
      signal: AbortSignal.timeout(600000),
    });
    const res = await r.json();
    $('bench-result').innerHTML = renderLeaderboard(res);
    $('bench-status').textContent = 'done · saved to benchmarks';
    loadBenchHistory();
  } catch (e) {
    $('bench-status').textContent = 'failed (' + (e.name || 'error') + ')';
  }
  $('run-bench').disabled = false;
}

async function loadBenchHistory() {
  if (!apiUp) { $('bench-history').innerHTML = '<div class="muted small">—</div>'; return; }
  try {
    const r = await fetch(API + '/api/benchmarks?limit=10', { signal: AbortSignal.timeout(4000) });
    const rows = (await r.json()).benchmarks || [];
    $('bench-history').innerHTML = rows.length ? rows.map((b) =>
      `<div class="bench-run"><span>${esc(String(b.ts || '').slice(0, 19).replace('T', ' '))} · ${esc(b.model || b.provider || 'rule-based')}</span>` +
      `<span>pass <b>${b.mean_pass_rate}</b> · score <b>${b.mean_score}</b> · n=${b.samples_per_topic}</span></div>`).join('')
      : '<div class="muted small">no runs yet</div>';
  } catch { $('bench-history').innerHTML = '<div class="muted small">—</div>'; }
}

$('open-bench').addEventListener('click', () => { $('bench').hidden = false; loadBenchHistory(); });
$('close-bench').addEventListener('click', () => { $('bench').hidden = true; });
$('bench').addEventListener('click', (e) => { if (e.target.id === 'bench') $('bench').hidden = true; });
$('run-bench').addEventListener('click', runBench);

// ---- init ----
$('topic').value = selected;
if ($('model')) $('model').addEventListener('change', syncEngineLabel);
(async () => {
  await probeApi();
  await loadModels();
  const { cand, s } = await runOne(selected); showVerdict(selected, cand, s); draw();
})();
resize();
