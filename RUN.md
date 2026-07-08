# RUN — Brain-Computer-Interface v3

Everything you need to clone, install, run, and (optionally) wire your **local Qwen** LLM.
Only dependency for the core is **Python 3.10+**. `matplotlib` is optional (for the graph).

### Where to run each command

| Command | Where | Notes |
|---|---|---|
| `python -m venv` / `pip install -e …` | **`backend/`** | one-time setup |
| `.\serve.ps1` · `./serve.sh` | **repo root** | no venv activation needed |
| `bci serve` · `bci invent` · `bci bench` · `bci db` … | **any dir**, venv **active** | activate once: `source backend/.venv/bin/activate` (or `.\backend\.venv\Scripts\Activate.ps1`) |

> Once the venv is active (prompt shows `(.venv)`), every `bci …` command works from any folder.

---

## 0. Prerequisites

- **Python 3.10+** and **git** (required). Check: `python --version` (Windows) / `python3 --version`.
  - Windows: `winget install Python.Python.3.12 Git.Git`
  - macOS: `brew install python git`
  - Linux (Debian/Ubuntu): `sudo apt update && sudo apt install -y python3 python3-venv python3-pip git`
- Optional: **Ollama + Qwen** (real invention) and **MongoDB Community** (storage). Both are
  auto-detected; without them the engine uses a rule-based fallback + a JSONL file.

---

## 1. Get the code — clone (first time) **or** pull (update)

**First time — clone:**
```bash
git clone https://github.com/sanjaydoc/Brain-Computer-Interface-v3.git
cd Brain-Computer-Interface-v3
```
> Private repo — sign in with your GitHub username + a **Personal Access Token** (or SSH key).

**Already cloned — pull the latest:**
```bash
cd Brain-Computer-Interface-v3
git pull origin main
```
> After a pull, re-run the install step below only if dependencies changed (safe to run anytime).

---

## 2. Create the venv, activate it, install dependencies

Do this in the **`backend/`** folder. The virtual environment (`.venv`) keeps this project's
packages isolated from your system Python.

### Windows (PowerShell)

```powershell
cd backend

# (one-time only) allow the venv's activate script to run:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 1) create the venv
python -m venv .venv

# 2) ACTIVATE it — your prompt then shows (.venv)
.\.venv\Scripts\Activate.ps1

# 3) install dependencies (everything: tests, plot, API, database)
pip install -e ".[dev,plot,api,db]"

# 4) verify
python -m pytest -q               # expect: 29 passed
```

### macOS (bash / zsh)

```bash
cd backend

python3 -m venv .venv             # 1) create
source .venv/bin/activate         # 2) ACTIVATE — prompt shows (.venv)
pip install -e ".[dev,plot,api,db]"   # 3) install
python -m pytest -q               # 4) verify → 29 passed
```

### Linux (bash)

```bash
cd backend

python3 -m venv .venv             # 1) create
source .venv/bin/activate         # 2) ACTIVATE — prompt shows (.venv)
pip install -e ".[dev,plot,api,db]"   # 3) install
python -m pytest -q               # 4) verify → 29 passed
```

**Re-activating later** (each new terminal): from the repo root, run
`.\backend\.venv\Scripts\Activate.ps1` (Windows) or `source backend/.venv/bin/activate`
(macOS/Linux). To leave the venv: `deactivate`.

Optional sanity check — invents + grades all 10 topics and writes a scorecard graph:
```bash
python scripts/demo_invent.py --plot      # (Windows: python scripts\demo_invent.py --plot)
```

---

## 3. Run everything — one command

`bci serve` runs the API **and** the cockpit on a single port.

**From the repo root — no `cd`, no venv activation** (uses the root launcher scripts):

```powershell
.\serve.ps1                   # Windows  → http://localhost:8000/app/
.\serve.ps1 --port 9000       # flags pass through
```
```bash
./serve.sh                    # macOS / Linux → http://localhost:8000/app/
./serve.sh --port 9000
```

Or, with the venv **already active**, `bci serve` works from anywhere:

```bash
bci serve                     # → http://localhost:8000/app/
```

Open **http://localhost:8000/app/**. The cockpit is served from the same origin as the API, so
**Invent + Simulate** routes through the Python engine (real LLM lenses + critique loop, and your
local Qwen if wired) with zero extra config. The controls card shows the active provider
(e.g. `qwen2.5:7b (backend)`).

```bash
bci serve --port 9000         # pick a port
bci serve --reload            # auto-reload while developing
```

Other one-shot commands:

```bash
bci health                                            # LLM provider / database / search sources
bci ping                                              # one tiny timed LLM call — is the model working & fast?
bci topics                                            # list the 10 topics
bci invent multiplexed_reporters "acoustic, deep"     # invent + grade from the terminal
bci record in_vivo_readout "non-destructive"          # search → invent → simulate → save to DB
bci record snr_depth "deep, safe" --no-ground         # skip the literature search (faster)
bci search "gas vesicle acoustic reporter genes"      # preview retrieved literature (per-source)
bci bench --samples 5                                 # leaderboard across all 10 topics
bci db --stats                                        # counts + pass-rate per category
```

> If the backend isn't running, the cockpit silently falls back to the in-browser proposer, so
> the static page still works on its own (`cd docs && python -m http.server 8097`).

---

## 3b. Configure keys with a `.env` file (recommended)

Paste your settings once into `backend/.env` (copied from `backend/.env.example`) instead of
exporting every time. The engine auto-loads it; real exported vars still win. **`.env` is
git-ignored — never commit it.**

```bash
cd backend
cp .env.example .env
# then edit .env:
```

```ini
# backend/.env
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:7b
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxx
BCI_LLM_MODEL=qwen/qwen2.5-7b-instruct
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=bciv3
```

Provider order stays local (Qwen) → NVIDIA NIM → cloud → rule-based, so with both set, Qwen is
used first and NIM is the automatic fallback.

---

## 4. Wire your local LLM (Qwen) — details

The engine runs fully **without** an LLM (deterministic rule-based fallback). To use your local
**Qwen 7B** for real creative invention, point the adapter at any OpenAI-compatible server
(Ollama / vLLM / llama.cpp / LM Studio).

### Example: Ollama + Qwen

```bash
# install Ollama, then pull a model sized to your hardware (see the table below):
ollama pull qwen2.5:7b           # fast, direct, emits JSON — the recommended default
# smaller / faster on a modest machine:  ollama pull qwen2.5:3b
# (deeper but slow, needs a strong GPU:  ollama pull qwen3.5:9b)
ollama serve                     # serves an OpenAI-compatible API on :11434
```

**Pick a model that fits your machine** — the simulator grades the *design*, not the model size,
so a small model that actually runs beats a big one that times out:

| model | disk | needs | when to use |
|---|---|---|---|
| `qwen2.5:3b`  | ~1.9 GB | modest GPU / decent CPU | slower machines — **fast & reliable** |
| `qwen2.5:7b`  | ~4.7 GB | a real GPU (≥6 GB VRAM) | the recommended default |
| `qwen3.5:9b`  | ~6.6 GB | a strong GPU (≥10 GB VRAM) | deepest designs, but slow — a *thinking* model |

Set the config in `backend/.env` (the adapter is **local-first**); `LOCAL_LLM_MODEL` is just the
Ollama tag, so point it at the model you pulled:

```ini
# backend/.env
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:7b        # or qwen2.5:3b on a slower box
```

> You can also set it per-shell (`$env:LOCAL_LLM_MODEL="qwen2.5:7b"` on Windows,
> `export LOCAL_LLM_MODEL=…` on Linux/macOS) — but note a shell variable **overrides `.env`** and
> persists for the whole session, so if a `bci` run keeps using the wrong model, clear it (see
> Troubleshooting). Any OpenAI-compatible model works; confirm the exact tag with `ollama list`.

**Verify before you invent** — one tiny timed call confirms the model is wired and fast:

```bash
bci ping
```

Expect `model=<your tag>` with both modes **OK** in a couple of seconds and a `'{"ok": true}'`
reply. If it says `fallback`, times out, or errors, `bci ping` prints the exact cause and fix.
Then the real thing:

```bash
bci record snr_depth "focused ultrasound, deep cortex, low thermal dose, safe" --no-ground
```

The header should read **`engine: LLM (local)`** (not `fallback`), and you'll get a real
Qwen-generated design — full mechanism, materials, protocol, and scores — graded by the simulator.

### Tuning knobs (slow or fussy local models)

All optional, all settable in `backend/.env`. Run `bci ping` to see which you need.

```ini
# BCI_LLM_TIMEOUT=600      # seconds before giving up (default 300) — raise on a slow/CPU box
# BCI_LLM_MAX_TOKENS=900   # shorter designs = faster generation (default 2000)
# BCI_LLM_JSON_MODE=off    # drop response_format if the JSON-grammar mode hangs your Ollama
#                          #   (bci ping tells you: "plain works, JSON-mode hangs" → set this)
# BCI_LLM_NO_THINK=1       # thinking models only (qwen3.5) — skip the reasoning block for speed
```

### Choose the model in the cockpit GUI (auto-detected)

The cockpit has an **LLM model** dropdown that **auto-detects every model you've pulled** — it calls
`/api/models`, which queries your local server's `{LOCAL_LLM_URL}/models` (Ollama lists all tags).
Pick one and hit **Invent + Simulate**; the engine line shows the active model
(`local · qwen2.5:3b (backend)`), and each saved record stores which model produced it — so you can
A-B two models and let the simulator score decide.

**`.env` setup for a 7B ⇄ 3B choice.** Pull both models, then set the *default* in `backend/.env`;
the GUI dropdown overrides it per run (leave the dropdown on the default to use `.env`):

```bash
ollama pull qwen2.5:7b        # quality default
ollama pull qwen2.5:3b        # faster on a modest box
```
```ini
# backend/.env
LOCAL_LLM_URL=http://localhost:11434/v1
LOCAL_LLM_MODEL=qwen2.5:7b    # the default; the GUI dropdown can switch to qwen2.5:3b per run
```

Then `bci serve`, open the cockpit, and the dropdown shows **both** (plus any other tags you've
pulled). No code change to add a model — just `ollama pull <tag>` and reload the page.

> The dropdown is **backend-only**: it's live when the Python backend is running (`bci serve`);
> in the static browser-only cockpit it's greyed to "backend only". From the terminal, the same
> choice is `LOCAL_LLM_MODEL=… bci record …` (or `$env:LOCAL_LLM_MODEL="…"; bci record …`).

### Thinking models (Qwen3.5, DeepSeek-R1)

Qwen3.5 **reasons before answering** (the `Thinking…` block). The engine handles this: it strips
the reasoning, prefers the real JSON that follows, and uses a generous token budget so the answer
isn't cut off. Reasoning generally improves the designs — but it's slower and uses more tokens.
For faster, cleaner structured output, skip it:

```bash
export BCI_LLM_NO_THINK=1     # (Windows: $env:BCI_LLM_NO_THINK="1")  → appends /no_think
```

Then any `invent(...)` / `design(...)` call uses Qwen automatically.

### Fallback order

`LOCAL_LLM_URL` (Qwen) → `NVIDIA_API_KEY` (NIM) → `OPENAI_API_KEY` → `ANTHROPIC_API_KEY` →
`OPENROUTER_API_KEY` → rule-based fallback. Set only what you have.

**NVIDIA NIM instead of local:**
```bash
export NVIDIA_API_KEY="nvapi-…"           # (Windows: $env:NVIDIA_API_KEY = "nvapi-…")
export BCI_LLM_MODEL="qwen/qwen2.5-7b-instruct"
```

---

## 4b. Compare / A-B two models (which is better at invention?)

The model is just `LOCAL_LLM_MODEL` — swap it per run and let the **law simulator decide** which
produces more physically-admissible, higher-scoring designs. No code change.

**Linux / macOS**
```bash
# a faster, lighter baseline:
LOCAL_LLM_MODEL=qwen2.5:7b bci invent multiplexed_reporters "acoustic, deep, safe"
# a newer, larger model:
LOCAL_LLM_MODEL=qwen3.5:9b bci invent multiplexed_reporters "acoustic, deep, safe"
```

**Windows (PowerShell)** — set, run, repeat:
```powershell
$env:LOCAL_LLM_MODEL = "qwen2.5:7b"; bci invent multiplexed_reporters "acoustic, deep, safe"
$env:LOCAL_LLM_MODEL = "qwen3.5:9b"; bci invent multiplexed_reporters "acoustic, deep, safe"
```

Compare the `passed`, `score`, and `limiting` fields across the 10 topics. Whichever yields more
passes / higher scores is empirically better **for this task** — the answer that matters, and it's
model-agnostic.

> Confirm the exact model tag first with `ollama show <tag>` / `ollama list`, and read its model
> card. A larger, newer, reasoning-capable model usually invents better; a smaller one iterates
> faster. `bci serve` shows the active provider in the cockpit's controls card.

---

## 4c. Database — capture every invention (MongoDB)

Every invention **auto-saves** — the design, its multi-domain detail (biophysics / physics /
electronics / biology), its parts list, and its simulator score — grouped by the 10 innovation
categories. Target: **local MongoDB Community**.

1. Install MongoDB Community and start it (`mongod`), then set (already in `.env.example`):

```ini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=bciv3
```

2. Install the driver and run:

```bash
pip install -e ".[db]"          # pymongo
bci record multiplexed_reporters "acoustic, deep, safe"   # invent + detail + score → saved
bci db --stats                  # counts + pass-rate per category
bci db multiplexed_reporters    # list saved inventions in one category
```

Records land in `bciv3.inventions`. In the cockpit, **📚 Saved inventions** shows them grouped by
the 10 categories, each with a 🗑 delete button.

> **No Mongo yet? It still works.** If Mongo is down or `pymongo` isn't installed, saves fall back
> to a JSONL file (`inventions.jsonl`), and the browser cockpit saves to `localStorage`. Nothing
> is lost — switch to Mongo whenever it's up.

---

## 4d. Literature grounding (PubMed, arXiv, patents, …)

Every invention is **grounded in real prior art**: before Qwen invents, the engine searches
**PubMed · arXiv · USPTO · PubChem · GitHub · SearXNG · Wikipedia** and feeds the results in as
prior knowledge, then stores the citations with the record. Keyless for PubMed / arXiv / Wikipedia
/ PubChem / USPTO — nothing to configure.

```bash
bci search "gas vesicle acoustic reporter genes brain"   # preview what the sources return
bci record multiplexed_reporters "acoustic, deep, safe"  # grounded invention (search → invent → simulate → save)
```

In the cockpit, the **ground in literature** checkbox (on by default) controls it; retrieved
citations show in the candidate aside and are saved to the record's `citations` field.

**Optional config** (in `.env`):

```ini
# NCBI_API_KEY=...             # higher PubMed rate limits
# GITHUB_TOKEN=...             # higher GitHub search rate limits
# SEARXNG_URL=http://localhost:8080   # enables the SearXNG web-search source
# BCIV3_SEARCH_SOURCES=pubmed,arxiv,wikipedia   # narrow the sources (default: all)
```

> Sources that fail, time out, or aren't configured contribute nothing — grounding never breaks a
> run. Offline, inventions still work (ungrounded).

---

## 4e. Benchmark — which model invents better (`bci bench`)

Sweep the topics N times, grade every attempt with the simulator, and get a **pass-rate +
mean/best-score leaderboard** — saved compactly to a `benchmarks` collection.

```bash
bci bench --samples 5                 # all 10 topics × 5 samples, current model
bci bench --topic snr_depth --samples 8
bci bench --ground                    # ground each attempt in literature (slower)
bci bench --save-attempts             # also persist every invention to the DB
```

**A-B two models** — run it once per model and compare the leaderboards:

```bash
# .env: LOCAL_LLM_MODEL=qwen2.5:7b
bci bench --samples 5
# .env: LOCAL_LLM_MODEL=qwen3.5:9b   (or a per-session override)
bci bench --samples 5
```

Each run records the model, mean pass-rate, and mean score, so whichever produces more
physically-admissible, higher-scoring designs is the empirical winner. (With the rule-based
fallback every topic passes deterministically — the leaderboard gets interesting once an LLM is
driving, because temperature makes the samples vary.)

---

## 4f. Example commands (`bci invent` / `bci record`)

Format: `bci invent <topic_id> "<prompt>"` — prints the design + simulator verdict.
Use `bci record …` for the same **plus** literature grounding + save to MongoDB.
(Venv active; run from any directory. Add `aggressive` to a prompt to push parameters harder.)

```bash
# 2 · Massively-multiplexed reporters — the multiplexing wall
bci invent multiplexed_reporters "acoustic reporters with thousands of distinguishable channels, deep, safe"

# 1 · In-vivo, non-destructive barcode readout — door #1
bci invent in_vivo_readout "read barcodes 75 mm deep in a living brain, under all safety limits"

# 4 · ~100% neuron delivery
bci invent neuron_delivery "BBB-crossing vector that labels every neuron with a safe viral dose"

# 5 · Signal boost + noise cut at depth
bci invent snr_depth "brighter reporters and heavy averaging so it still reads at depth, aggressive"

# 6 · Whole-brain scan throughput
bci invent scan_throughput "read the whole brain in under 30 days with massively parallel channels"

# 3 · Trans-synaptic pairing at scale
bci invent transsynaptic_pairing "pair pre and post barcodes across every synapse with low false-pair rate"

# 10 · Human safety of the whole chain
bci invent human_safety "keep ultrasound intensity, mechanical index, and AAV dose well inside limits"
```

Flags:

```bash
bci invent multiplexed_reporters "acoustic, deep, safe" --lens inversion   # pick a creative lens
bci invent snr_depth "aggressive" --backend fallback                        # force the fast rule-based proposer
bci record in_vivo_readout "non-destructive"                                # grounded + saved to the DB
```

**The 10 topic IDs** (`bci topics` to list): `in_vivo_readout` · `multiplexed_reporters` ·
`transsynaptic_pairing` · `neuron_delivery` · `snr_depth` · `scan_throughput` · `exabyte_assembly`
· `twin_sim_scale` · `behavioral_verification` · `human_safety`.

**The 10 lenses:** `analogical · inversion · crossDomain · extreme · historical · biomimicry ·
combinatorial · reduction · scaling · future`. See also **`50 invention prompts to try.txt`**.

---

## 5. Use it from Python

```python
import bciv3

# pick a topic + a prompt → invent a design → grade it against the laws
cand = bciv3.invent("multiplexed_reporters", "acoustic reporters, deep, safe")
print(bciv3.report("multiplexed_reporters", cand))

# closed loop: invent → simulate → refine on failure
print(bciv3.design("scan_throughput", "parallelise the readout", rounds=3))

# tournament: one candidate per creative lens, ranked by simulated score
for r in bciv3.rank("neuron_delivery"):
    print(r["score"], r["lens"], r["limiting"])

print(bciv3.all_ids())            # the 10 topics
print(bciv3.LENSES)               # the 10 invention lenses
```

---

## 6. Updating later

```bash
git pull origin main
cd backend && pip install -e ".[dev,plot,api,db]"
```

---

## 7. Troubleshooting

**Start with `bci ping`** — it fires one tiny timed call (JSON-mode and plain), prints the active
`model=…`, the latency, and a specific diagnosis. Most issues below are identified by it.

| Symptom | Cause | Fix |
|---|---|---|
| `engine: fallback (no LLM used)` after a run | the LLM call failed → rule-based fallback | run `bci ping` to see why (below) |
| `bci ping` shows the **wrong** `model=…` | a shell variable is overriding `.env` | clear it (next row) |
| `note: llm failed (timed out after Ns)` | model too slow for the token budget | smaller model + raise `BCI_LLM_TIMEOUT` |
| `ping` JSON-mode hangs but plain is OK | Ollama's JSON-grammar mode stalls | `BCI_LLM_JSON_MODE=off` in `.env` |
| `HTTP 500 … 0xc0000005` from Ollama | Ollama's runner crashed (often after an out-of-memory) | restart Ollama (below) |
| `engine: … → jsonl` instead of MongoDB | `pymongo` missing or Mongo down | `pip install -e ".[db]"`, set `MONGODB_URI`, start `mongod` |

**A shell variable is overriding `.env`.** Environment variables set in the shell win over the
`.env` file *for the whole session*. If `bci ping` shows a model you thought you changed, clear the
stale one:
```powershell
# Windows (PowerShell)
Remove-Item Env:\LOCAL_LLM_MODEL          # then bci reads .env again
```
```bash
# Linux / macOS
unset LOCAL_LLM_MODEL
```
(Or just open a fresh terminal — session variables don't carry over.)

**The model is too slow / times out.** A large model on a weak GPU or CPU can take minutes per
design. Use a smaller model and give it headroom, in `backend/.env`:
```ini
LOCAL_LLM_MODEL=qwen2.5:3b
BCI_LLM_TIMEOUT=600
BCI_LLM_MAX_TOKENS=900      # optional — shorter, faster designs
```

**Ollama crashed (`0xc0000005` / HTTP 500).** The inference subprocess died — common right after a
model runs out of memory. Kill it and restart, then warm the model directly:
```powershell
# Windows
Get-Process *ollama* | Stop-Process -Force
# relaunch Ollama from the Start menu, then:
ollama run qwen2.5:3b "hi"        # should reply normally; /bye to exit (leaves it warm)
```
```bash
# Linux / macOS
pkill ollama; ollama serve &      # restart the server
ollama run qwen2.5:3b "hi"
```
If `ollama run` *itself* still crashes, reboot (clears a wedged GPU state), then update Ollama.

**PowerShell won't activate the venv** (`the module '.venv' could not be loaded`). Use the `.\`
prefix so PowerShell runs the script instead of treating it as a module name:
```powershell
.\.venv\Scripts\Activate.ps1      # not  .venv\Scripts\Activate.ps1
```
If it's blocked by execution policy: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
first. If `.venv` doesn't exist yet, create it: `python -m venv .venv`.
