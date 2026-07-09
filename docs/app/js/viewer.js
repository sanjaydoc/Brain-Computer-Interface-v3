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

// Static repo-data fallback: when no backend is running (e.g. GitHub Pages), the cockpit reads a
// committed snapshot of the library from ../data/*.json so the demo shows real inventions & prototypes.
const _staticCache = {};
async function loadStatic(name) {
  if (name in _staticCache) return _staticCache[name];
  try {
    const r = await fetch('../data/' + name + '.json', { signal: AbortSignal.timeout(8000) });
    _staticCache[name] = r.ok ? await r.json() : null;
  } catch { _staticCache[name] = null; }
  return _staticCache[name];
}

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
// The approach constraint: 'noninvasive' (biomolecules) | 'invasive' (electrodes) | '' (n/a).
const constraintVal = () => ($('constraint') ? $('constraint').value : 'noninvasive');
// Recommended constraint for a topic: software/data topics don't interface with the brain, so the
// non-invasive/invasive distinction doesn't apply ('' = not applicable); everything else defaults
// to non-invasive (this is a non-invasive brain-mapping program).
const recommendedConstraint = (tid) => ((TOPICS[tid] && TOPICS[tid].domain) === 'software' ? '' : 'noninvasive');

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
                               backend: 'auto', model: modelVal() || null, constraint: constraintVal() || null,
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
// Reset the panels to a neutral "ready" state for a topic — WITHOUT inventing. Inventing only ever
// happens when the user clicks ✨ Invent + Simulate, so nothing fires on topic-change or page-load.
function showReady(tid) {
  selected = tid;
  const t = TOPICS[tid];
  if ($('constraint')) $('constraint').value = recommendedConstraint(tid);   // auto-pick per topic
  $('v-title').textContent = t.title;
  const pass = $('v-pass'); pass.textContent = '—'; pass.className = 'pill';
  $('v-fid').textContent = t.fidelity;
  $('v-score').textContent = '—';
  $('v-limit').textContent = '—';
  $('v-tags').innerHTML = t.layer.map((l) => `<span class="tag ${l}">${l}</span>`).join('');
  $('v-metrics').innerHTML = 'press ✨ Invent + Simulate →';
  // clear any previous candidate so stale details don't sit under a new topic
  ['c-domain', 'c-via', 'c-mech', 'c-params', 'c-detail', 'c-parts', 'c-cites', 'c-saved'].forEach((id) => { if ($(id)) $(id).innerHTML = ''; });
  $('c-title').textContent = '—';
}
function onTopicChange() {
  showReady($('topic').value);
  setStatus('topic selected — add a prompt (optional) and hit ✨ Invent + Simulate');
  setTimeout(() => setStatus(''), 4000);
}
$('topic').addEventListener('change', onTopicChange);
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
                               n_lenses: nLenses, model: modelVal() || null, constraint: constraintVal() || null }),
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
  // static repo snapshot (GitHub Pages / offline) — merge any locally-invented records on top
  const stat = await loadStatic('inventions');
  const groups = {}; TOPIC_IDS.forEach((t) => (groups[t] = []));
  let store = 'browser (localStorage)';
  if (stat && stat.groups) {
    TOPIC_IDS.forEach((t) => { groups[t] = (stat.groups[t] || []).slice(); });
    store = stat.store || 'repo data (static)';
  }
  const all = JSON.parse(localStorage.getItem('bciv3_saved') || '[]');
  all.forEach((r) => (groups[r.topic] = groups[r.topic] || []).push(r));
  TOPIC_IDS.forEach((t) => groups[t].sort((a, b) => (b.score?.score || 0) - (a.score?.score || 0)));
  return { groups, store };
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
    const inner = rows.length ? rows.map((r, j) =>
      `<div class="inv-row" data-id="${esc(r.id)}" title="click to read the full invention"><span class="dot ${r.score.passed ? 'p' : 'f'}"></span>` +
      `<span class="num">#${j + 1}</span>` +
      `<span class="ti">${esc(r.title || TOPICS[tid].title)}</span>` +
      `<span class="dt">${esc(String(r.ts || '').slice(0, 16).replace('T', ' '))}</span>` +
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

// ---- synthesis: unlock at 10/10, then fuse into one end-to-end system ----
async function loadSynthStatus() {
  const grid = $('synth-progress'), btn = $('run-synth'), gate = $('synth-gate');
  if (!apiUp) {
    const protos = await loadStatic('syntheses');
    if (protos && protos.length) {
      grid.innerHTML =
        `<div class="synth-meter"><i style="width:100%"></i></div>` +
        `<p class="muted small" style="margin:.4rem 0">All 10 blockers have a passing design in this repo snapshot. ` +
        `Browse the pre-built prototypes below — each is clickable, with a PDF export. ` +
        `To fuse a <b>new</b> combination live, run the Python backend (<code>bci serve</code>).</p>`;
      btn.disabled = true; gate.textContent = '✓ 10/10 · demo prototypes (read-only)';
    } else {
      grid.innerHTML = '<div class="muted small">Synthesis reads saved passing designs from the database — run the Python backend (<b>bci serve</b>) to use it.</div>';
      btn.disabled = true; gate.textContent = 'backend only';
    }
    return;
  }
  try {
    const r = await fetch(API + '/api/synthesis', { signal: AbortSignal.timeout(8000) });
    const st = await r.json();
    const cands = st.candidates || {};
    const pct = Math.round(100 * st.solved_count / st.total);
    grid.innerHTML =
      `<div class="synth-meter"><i style="width:${pct}%"></i></div>` +
      `<p class="muted small" style="margin:.2rem 0 .5rem">Pick which invention feeds each topic — mix combinations to make different prototypes. Defaults to the best-scoring.</p>` +
      `<div class="synth-pick">${TOPIC_IDS.map((tid, i) => {
        const list = cands[tid] || [];
        const on = list.length > 0;
        const opts = list.map((c, j) =>
          `<option value="${esc(c.id)}">#${j + 1} · ${esc((c.title || TOPICS[tid].title).slice(0, 40))} · ${esc(String(c.ts || '').slice(0, 16).replace('T', ' '))} · ${(+c.score).toFixed(3)}</option>`).join('');
        const sel = on
          ? `<select class="psel" data-topic="${tid}">${opts}</select>`
          : `<span class="psel-locked">🔒 solve this blocker first</span>`;
        return `<div class="synth-prow ${on ? 'on' : ''}"><span class="dot ${on ? 'on' : 'off'}">${on ? '✓' : ''}</span>` +
               `<span class="pt">${i + 1}. ${esc(TOPICS[tid].title)}</span>${sel}</div>`;
      }).join('')}</div>`;
    btn.disabled = !st.complete;
    gate.textContent = st.complete ? '✓ all 10 passing — pick & synthesize'
      : `🔒 ${st.solved_count}/${st.total} solved — pass all 10 to unlock`;
  } catch {
    grid.innerHTML = '<div class="muted small">could not load progress</div>'; btn.disabled = true;
  }
}

function renderSynthResult(res) {
  if (res.error) return `<div class="muted small" style="margin-top:1rem">🔒 ${esc(res.error)}</div>`;
  const s = res.system || {};
  const phases = (res.pipeline || []).map((ph) =>
    `<div class="phase"><h5>${esc(ph.phase)}</h5><div class="phase-why">${esc(ph.why)}</div>` +
    ph.stages.map((st) => {
      const parts = (st.parts || []).slice(0, 2).map((p) => esc(p.name)).join(' · ');
      return `<div class="snode"><div class="st">${esc(st.title)}</div><div class="sr">${esc(st.role)}</div>` +
             (parts ? `<div class="sp">${parts}</div>` : '') + `</div>`;
    }).join('') + `</div>`).join('<div class="arrow">→</div>');
  const how = (s.how_it_works || []).map((x) => `<li>${esc(x)}</li>`).join('');
  const bom = (res.bill_of_materials || []).map((p) =>
    `<div class="bi"><span><b>${esc(p.name)}</b> — ${esc(p.role || '')}</span><span class="ph">${esc(p.phase)}</span></div>`).join('');
  const safety = res.safety && res.safety.title
    ? `<div class="muted small" style="margin:.4rem 0">🛡 Safety envelope: <b>${esc(res.safety.title)}</b> keeps intensity, mechanical index, and viral dose within limits across the whole chain.</div>` : '';
  const saved = res.id ? `<div class="mono small" style="color:var(--venv); margin:.3rem 0">✓ saved as prototype · id ${esc(String(res.id).slice(0, 10))}</div>` : '';
  return saved + `<div class="sys-name">${esc(s.system_name || 'End-to-End System')}</div>` +
    `<div class="sys-over">${esc(s.overview || '')}</div>` +
    `<div class="schematic"><span class="safety-tag">🛡 Human-safety envelope · whole chain</span><div class="flow">${phases}</div></div>` +
    (s.integration_notes ? `<div class="muted small">${esc(s.integration_notes)}</div>` : '') + safety +
    `<div class="id-sec how"><h4>How it works — end to end</h4><ol>${how}</ol></div>` +
    `<div class="id-sec"><h4>Bill of materials (${(res.bill_of_materials || []).length} parts)</h4><div class="bom">${bom}</div></div>` +
    ((s.open_risks && s.open_risks.length) ? `<div class="id-sec"><h4>Open risks</h4><ul>${s.open_risks.map((r) => `<li>${esc(r)}</li>`).join('')}</ul></div>` : '') +
    `<div class="mono small muted" style="margin-top:.5rem">built via ${esc(s.engine || 'template')} · ${res.total} blockers fused</div>`;
}

const protoById = {};       // id → full prototype record, for click-to-view

function openPrototype(id) {
  const p = protoById[id];
  if (!p) return;
  const when = esc(String(p.ts || '').slice(0, 19).replace('T', ' '));
  $('synth-result').innerHTML = `<div class="eyebrow" style="margin-top:1rem">📁 Saved prototype · ${when}</div>` + renderSynthResult(p);
  $('synth-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Build a clean, standalone printable document for one prototype and open the browser's
// print dialog (→ "Save as PDF"). No external libraries — works offline under `bci serve`.
function exportPrototypePdf(id) {
  const p = protoById[id];
  if (!p) return;
  const s = p.system || {};
  const when = esc(String(p.ts || '').slice(0, 19).replace('T', ' '));
  const name = esc(s.system_name || 'End-to-End System');
  const pipeline = (p.pipeline || []).map((ph) =>
    `<div class="phase"><h3>${esc(ph.phase)} — ${esc(ph.why || '')}</h3><ul>` +
    (ph.stages || []).map((st) => `<li><b>${esc(st.title)}</b> — ${esc(st.role || '')}</li>`).join('') +
    `</ul></div>`).join('');
  const how = (s.how_it_works || []).map((x) => `<li>${esc(x)}</li>`).join('');
  const bom = (p.bill_of_materials || []).map((b) =>
    `<tr><td>${esc(b.name || '')}</td><td>${esc(b.role || '')}</td><td>${esc(b.phase || '')}</td></tr>`).join('');
  const safety = p.safety && p.safety.title
    ? `<p><b>🛡 Safety envelope:</b> ${esc(p.safety.title)} — keeps ultrasound intensity, mechanical index, and viral dose within limits across the whole chain.</p>` : '';
  const risks = (s.open_risks && s.open_risks.length)
    ? `<h2>Open risks</h2><ul>${s.open_risks.map((r) => `<li>${esc(r)}</li>`).join('')}</ul>` : '';
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${name} — BCI v3 prototype</title>
<style>
  @page { margin: 18mm; }
  * { box-sizing: border-box; }
  body { font: 12px/1.5 -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #111; max-width: 760px; margin: 0 auto; padding: 1rem; }
  h1 { font-size: 22px; margin: 0 0 .2rem; }
  h2 { font-size: 15px; margin: 1.4rem 0 .4rem; border-bottom: 1px solid #ccc; padding-bottom: .2rem; }
  h3 { font-size: 12.5px; margin: .7rem 0 .3rem; }
  .meta { color: #666; font-family: ui-monospace, "JetBrains Mono", monospace; font-size: 11px; margin-bottom: .8rem; }
  .over { font-size: 13px; color: #333; }
  .phase { margin: .3rem 0; padding-left: .2rem; }
  .phase ul { margin: .2rem 0 .2rem 1.1rem; padding: 0; }
  li { margin: .12rem 0; }
  ol { margin: .3rem 0 .3rem 1.2rem; padding: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 11px; margin-top: .3rem; }
  td, th { border: 1px solid #ddd; padding: 3px 6px; text-align: left; vertical-align: top; }
  th { background: #f3f3f3; }
  .foot { margin-top: 1.6rem; color: #999; font-size: 10px; border-top: 1px solid #eee; padding-top: .5rem; }
  @media print { body { padding: 0; } }
</style></head><body>
  <h1>${name}</h1>
  <div class="meta">Brain-Computer-Interface v3 · prototype ${esc(String(p.id || '').slice(0, 12))} · ${when} · built via ${esc(s.engine || 'template')} · ${esc(String(p.total || ''))} blockers fused</div>
  <p class="over">${esc(s.overview || '')}</p>
  <h2>End-to-end pipeline</h2>${pipeline}
  ${s.integration_notes ? `<p><b>Integration:</b> ${esc(s.integration_notes)}</p>` : ''}${safety}
  <h2>How it works — end to end</h2><ol>${how}</ol>
  <h2>Bill of materials (${(p.bill_of_materials || []).length} parts)</h2>
  <table><thead><tr><th>Part</th><th>Role</th><th>Phase</th></tr></thead><tbody>${bom}</tbody></table>
  ${risks}
  <div class="foot">Generated from the BCI v3 cockpit · non-invasive brain-uploading system · every stage is a passing, law-simulated design.</div>
  <script>window.onload=function(){setTimeout(function(){window.print();},250);};<\/script>
</body></html>`;
  const w = window.open('', '_blank');
  if (!w) { alert('Pop-up blocked — allow pop-ups for this page to download the PDF.'); return; }
  w.document.open(); w.document.write(html); w.document.close();
}

// Open the server-rendered ~30-page research monograph for a prototype; it auto-triggers the
// browser print dialog (→ Save as PDF). Requires the API (bci serve) to be up.
function exportResearchPdf(id) {
  // live backend renders it on the fly; otherwise open the pre-rendered ~30-page PDF (GitHub Pages)
  const url = apiUp ? (API + '/api/research/' + encodeURIComponent(id))
                    : ('../data/research/' + encodeURIComponent(id) + '.pdf');
  const w = window.open(url, '_blank');
  if (!w) alert('Pop-up blocked — allow pop-ups for this page to open the research PDF.');
}

async function loadSynthHistory() {
  const box = $('synth-history');
  if (!box) return;
  let rows = [];
  if (apiUp) {
    try {
      const r = await fetch(API + '/api/syntheses?limit=20', { signal: AbortSignal.timeout(5000) });
      rows = (await r.json()).syntheses || [];
    } catch { apiUp = false; }
  }
  if (!apiUp) rows = (await loadStatic('syntheses')) || [];    // repo snapshot on GitHub Pages / offline
  try {
    Object.keys(protoById).forEach((k) => delete protoById[k]);
    rows.forEach((p) => { if (p.id) protoById[p.id] = p; });
    // the Research monograph is server-rendered live (bci serve) or a pre-rendered static file
    // committed to the repo (docs/data/research/<id>.html) — offer it either way.
    const researchBtn = (id) =>
      `<button class="pdf research" data-id="${esc(id)}" title="Open the full ~30-page research monograph (print → Save as PDF)">📕 Research</button>`;
    box.innerHTML = rows.length ? rows.map((p) => {
      const sysd = p.system || {};
      return `<div class="bench-run proto-row" data-id="${esc(p.id || '')}">` +
             `<span class="pname">${esc(String(p.ts || '').slice(0, 19).replace('T', ' '))} · ${esc(sysd.system_name || 'system')}</span>` +
             `<span class="pmeta">${(p.bill_of_materials || []).length} parts · ${esc(sysd.engine || '')} · view →</span>` +
             researchBtn(p.id) +
             `<button class="pdf" data-id="${esc(p.id || '')}" title="Download a one-page prototype summary as PDF">📄 PDF</button></div>`;
    }).join('') : '<div class="muted small">no prototypes yet — synthesize one above</div>';
    box.querySelectorAll('.proto-row').forEach((row) =>
      row.addEventListener('click', () => openPrototype(row.dataset.id)));
    box.querySelectorAll('.pdf:not(.research)').forEach((b) =>
      b.addEventListener('click', (e) => { e.stopPropagation(); exportPrototypePdf(b.dataset.id); }));
    box.querySelectorAll('.pdf.research').forEach((b) =>
      b.addEventListener('click', (e) => { e.stopPropagation(); exportResearchPdf(b.dataset.id); }));
  } catch { box.innerHTML = '<div class="muted small">—</div>'; }
}

async function runSynthesize() {
  const btn = $('run-synth'), box = $('synth-result');
  const selection = {};                        // {topic: chosen invention id}
  document.querySelectorAll('.psel').forEach((s) => { if (s.value) selection[s.dataset.topic] = s.value; });
  btn.disabled = true; box.innerHTML = '<div class="muted small" style="margin-top:1rem">🧬 fusing your chosen designs into one system…</div>';
  try {
    const r = await fetch(API + '/api/synthesize', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ selection }), signal: AbortSignal.timeout(600000),
    });
    box.innerHTML = renderSynthResult(await r.json());
    loadSynthHistory();                       // refresh the prototype library with the new one
  } catch (e) {
    box.innerHTML = `<div class="muted small" style="margin-top:1rem">failed (${esc(e.name || 'error')})</div>`;
  }
  btn.disabled = false;
}

$('open-synth').addEventListener('click', () => { $('synth').hidden = false; $('synth-result').innerHTML = ''; loadSynthStatus(); loadSynthHistory(); });
$('close-synth').addEventListener('click', () => { $('synth').hidden = true; });
$('synth').addEventListener('click', (e) => { if (e.target.id === 'synth') $('synth').hidden = true; });
$('run-synth').addEventListener('click', runSynthesize);

// ---- init ----
$('topic').value = selected;
if ($('model')) $('model').addEventListener('change', syncEngineLabel);
(async () => {
  await probeApi();
  await loadModels();
  showReady(selected); draw();          // neutral ready state — do NOT invent until the user clicks
})();
resize();
