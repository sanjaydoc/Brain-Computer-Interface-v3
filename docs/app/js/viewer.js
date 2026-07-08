// v3 invention cockpit — pick a topic + lens + prompt → invent (rule-based) → simulate → render.
// The stage shows a live scorecard bar chart of all 10 topics; cards show the verdict + design.

import { TOPICS, TOPIC_IDS, LENSES, invent, simulate } from './catalog.js';

const $ = (id) => document.getElementById(id);
const scores = {};                 // tid -> {score, passed, fidelity}
let selected = TOPIC_IDS[0];

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

// ---- run one invention ----
function runOne(tid) {
  const cand = invent(tid, $('prompt').value);
  const s = simulate(tid, cand);
  scores[tid] = { score: s.score, passed: s.passed, fidelity: TOPICS[tid].fidelity };
  return { cand, s };
}

function showVerdict(tid, cand, s) {
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
  $('c-assume').innerHTML = `<li>spec-aware rule-based proposal</li><li>assumptions unverified in vivo</li>`;
  $('c-risks').innerHTML = `<li>passes = physically admissible, not proven in a living brain</li>`;
}

function fmt(v) {
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (typeof v !== 'number') return String(v);
  if (v !== 0 && (Math.abs(v) >= 1e5 || Math.abs(v) < 1e-3)) return v.toExponential(2);
  return (Math.round(v * 1000) / 1000).toString();
}

// ---- events ----
$('topic').addEventListener('change', (e) => { selected = e.target.value; const { cand, s } = runOne(selected); showVerdict(selected, cand, s); draw(); });
$('invent').addEventListener('click', () => { selected = $('topic').value; const { cand, s } = runOne(selected); showVerdict(selected, cand, s); draw(); });
$('all').addEventListener('click', () => {
  for (const tid of TOPIC_IDS) runOne(tid);
  const { cand, s } = runOne(selected); showVerdict(selected, cand, s); draw();
});

// ---- init ----
$('topic').value = selected;
{ const { cand, s } = runOne(selected); showVerdict(selected, cand, s); }
resize();
