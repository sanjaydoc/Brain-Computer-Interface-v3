<div align="center">

# 🧪 Brain-Computer-Interface v3

### Invent past the 10 blockers — then let the laws of physics grade the invention.

**A local-LLM invention engine paired with a law-based simulator. Pick one of the 10 mapping
innovations, add a prompt, and the engine proposes a concrete design — which the simulator then
grades against the laws of biophysics, physics, and electronics. Invention proposes; only the
physics can move the score.**

[![License: MIT](https://img.shields.io/badge/License-MIT-0d0d0f.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-2f6fed.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-15%20passing-0e9f6e.svg)](backend/tests)
[![Topics](https://img.shields.io/badge/innovation%20topics-10-635bff.svg)](#-the-10-innovation-topics)
[![Lenses](https://img.shields.io/badge/invention%20lenses-10-635bff.svg)](#-the-invention-engine)
[![LLM](https://img.shields.io/badge/LLM-local%20Qwen%20first%20·%20NIM%20fallback-d98218.svg)](RUN.md)

_Author: **Dr. Sanjay Anbu**_

</div>

---

> ⚠️ **Private & proprietary.** Confidential work in progress. All rights reserved — not licensed
> for public use, reproduction, or redistribution.

---

![The invention cockpit — v1's theme + cockpit view](docs/media/cockpit.png)

> **The cockpit** (`docs/app/`) — v1's theme and floating-card cockpit view. Pick a topic + a
> creative lens + a prompt, hit **Invent + Simulate**, and the law simulator grades the design
> live: the verdict card (pass/fail + limiting number + metrics), the candidate design aside
> (proposed parameters + assumptions + risks), and the scorecard for all 10 topics.

![Invented designs graded by the law simulator](docs/media/scorecard.png)

> The same run as a static graph. Green = the proposed design is **physically admissible
> in-model**; the right-hand tag is the **fidelity** of that verdict (`full-sim` = fully modelled;
> `physics-only` / `estimate` / `limits-only` = honestly partial).

---

## 🎯 Project goals

- ✅ **Port the inventor-studio-v3 invention pipeline** — 10 creative lenses + critic/MVP reasoning, converted Node → Python.
- ✅ **Local-LLM-first** — runs on your **Qwen 7B** via `LOCAL_LLM_URL`, NVIDIA NIM fallback, rule-based fallback with no LLM at all.
- ✅ **All 10 innovation topics** from the v2 map, each with a target spec + parameter schema.
- ✅ **Law-based simulator** — biophysics · physics · electronics engines grade every design.
- ✅ **Invent → simulate → refine loop** — failures feed the limiting number back to the engine.
- ✅ **Candidate ranking** — one design per lens, ordered by simulated score (an idea tournament).
- ✅ **Honest fidelity flags** — a pass means *physically admissible*, never *proven in a living brain*.
- ✅ **15 tests, deterministic** — the whole pipeline runs offline in CI.
- ✅ **Cockpit GUI** — v1's theme + cockpit view; pick a topic, invent, and watch the law simulator grade it live in the browser.
- ✅ **Thin FastAPI backend** — the cockpit calls the Python engine (and your local Qwen) live; auto-detected, graceful browser fallback.
- ✅ **`.env` config** — paste `LOCAL_LLM_URL` / `LOCAL_LLM_MODEL` / `NVIDIA_API_KEY` once (zero-dependency loader, git-ignored).
- ⬜ **Amber topics as full estimators** — richer models for assembly / twin-sim at scale (Phase 4).

---

## 🔭 What this is

v1 *interfaces* with a connectome. v2 *maps* it and measures the **10 blockers** that stand between
today and a non-invasive human brain map. **v3 tries to invent past those blockers** — and refuses
to take the invention's word for it:

```
 pick 1 of 10 topics  +  prompt
        │
        ▼
 INVENTION ENGINE  (local Qwen, ported from inventor-studio-v3)
   → candidate design: mechanism + parameters + assumptions + risks
        │
        ▼
 LAW SIMULATOR  — grades the parameters against:
   🧬 biophysics   (coverage, reporter kinetics, thermal/AAV safety limits)
   〰️ physics      (wave attenuation → SNR/depth, resolution wall, capacity law)
   🔌 electronics  (channels, bandwidth, scan-time, array feasibility)
        │
        ▼
 pass / fail  +  the limiting number  +  ranked candidates
```

The two halves are kept **separate on purpose**: a persuasive narrative can never fake a passing
score — only the physics moves the number.

---

## 🧩 The 10 innovation topics

| # | Topic | Layer | Domain | Laws | Fidelity |
|---|---|---|---|---|---|
| 1 | In-vivo, non-destructive barcode readout | 🧬 bio · 🔌 hw | life-science | physics, biophysics | physics-only |
| 2 | Massively-multiplexed reporters | 🧬 bio | life-science | physics, electronics | **full-sim** |
| 3 | Trans-synaptic pairing at scale | 🧬 bio | life-science | physics | **full-sim** |
| 4 | ~100% neuron delivery | 🧬 bio | cell-therapy | biophysics | **full-sim** |
| 5 | Signal boost + noise cut (SNR) | 🔌 hw · 🧬 bio | electronics | physics, biophysics | **full-sim** |
| 6 | Whole-brain scan throughput | 🔌 hw | hardware | electronics | **full-sim** |
| 7 | Exabyte assembly + error-correction | 💻 sw · 🧠 tpl | software | electronics | estimate |
| 8 | Whole-brain twin simulation | 💻 sw · 🌐 venv | software | electronics | estimate |
| 9 | Behavioural upload-verification | 🌐 venv | software | physics | **full-sim** |
| 10 | Human safety of the whole chain | 🧬 bio · 🔌 hw | cell-therapy | biophysics | limits-only |

**6 fully-modelled**, 4 honestly flagged. Domains map onto inventor-studio-v3's taxonomy
(software · hardware · electronics · life-science · cell-therapy · hybrid).

---

## 🧠 The invention engine

Ported from **inventor-studio-v3** — ten creative *lenses* frame the reasoning, then the model
must return a design whose **numeric parameters** the simulator can grade:

`analogical · inversion · crossDomain · extreme · historical · biomimicry · combinatorial ·
reduction · scaling · future`

`rank()` runs one candidate per lens and orders them by simulated score — a small idea tournament.

---

## ⚡ Quickstart

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate      # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev,plot,api]"
python -m pytest -q                    # 15 passed
python scripts/demo_invent.py --plot   # scorecard + docs/media/scorecard.png

bci serve                              # API + cockpit on one port → http://localhost:8000/app/
```

```python
import bciv3
cand = bciv3.invent("multiplexed_reporters", "acoustic reporters, deep, safe")
print(bciv3.report("multiplexed_reporters", cand))      # design + verdict + limiting number
```

**Choose / A-B a model** — the model is just `LOCAL_LLM_MODEL`; swap it per run and let the law
simulator decide which invents better (more passes / higher scores):

```bash
LOCAL_LLM_MODEL=qwen2.5:7b-instruct bci invent multiplexed_reporters "acoustic, deep, safe"
LOCAL_LLM_MODEL=qwen3.5:9b          bci invent multiplexed_reporters "acoustic, deep, safe"
# Windows: $env:LOCAL_LLM_MODEL="qwen3.5:9b"; bci invent multiplexed_reporters "acoustic, deep, safe"
```

**Full setup for Windows / Linux / macOS + wiring your local Qwen + A-B'ing models → [RUN.md](RUN.md).**

---

## 📁 Layout

```
backend/bciv3/
  llm.py               local-Qwen-first LLM adapter (→ NIM → cloud → rule-based fallback)
  laws/                the simulator: physics.py · biophysics.py · electronics.py
  innovations/         the 10 topics — base.py (abstraction) + catalog.py (specs + evaluators)
  engine/              invention pipeline: prompt.py (10 lenses) · inventor.py · loop.py
  simulator.py         route a candidate to its laws → Score
backend/tests/         13 deterministic tests
backend/scripts/       demo_invent.py
```

---

## ⚖️ Honesty by construction

"Passes the simulator" means **physically admissible under the model** — that the design doesn't
violate a known law of biophysics, physics, or circuit feasibility. It does **not** mean *proven in
a living brain*. The fidelity flags (`physics-only`, `estimate`, `limits-only`) and the safety
topic's deliberately tight margin keep v3 a **research-agenda engine**, not a discovery oracle: it
prunes the impossible, ranks the plausible, and prints the target numbers to build toward.

---

<div align="center"><sub>Brain-Computer-Interface v3 · MIT License · Author: <b>Dr. Sanjay Anbu</b></sub></div>
