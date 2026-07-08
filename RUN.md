# RUN — Brain-Computer-Interface v3

Everything you need to clone, install, run, and (optionally) wire your **local Qwen** LLM.
Only dependency for the core is **Python 3.10+**. `matplotlib` is optional (for the graph).

---

## 1. Clone

```bash
git clone https://github.com/sanjaydoc/Brain-Computer-Interface-v3.git
cd Brain-Computer-Interface-v3
```

> Private repo — sign in with your GitHub username + a **Personal Access Token** (or SSH key).

---

## 2. Install & verify

### Windows (PowerShell)

```powershell
cd backend

# one-time only: allow the venv activate script to run
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,plot,api]"

python -m pytest -q               # expect: 15 passed
python scripts\demo_invent.py --plot
```

### Linux / macOS (bash / zsh)

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,plot,api]"

python -m pytest -q               # expect: 15 passed
python scripts/demo_invent.py --plot
```

`demo_invent.py` invents a design for each of the 10 topics, grades every one against the law
simulator, prints a scorecard, and writes `docs/media/scorecard.png`.

---

## 3. Run everything — one command

`bci serve` runs the API **and** the cockpit on a single port. From the project root (venv active):

```bash
bci serve                     # → http://localhost:8000/app/
```

Open **http://localhost:8000/app/**. The cockpit is served from the same origin as the API, so
**Invent + Simulate** routes through the Python engine (real LLM lenses + critique loop, and your
local Qwen if wired) with zero extra config. The controls card shows the active provider
(e.g. `qwen3.5:9b (backend)`).

```bash
bci serve --port 9000         # pick a port
bci serve --reload            # auto-reload while developing
```

Other one-shot commands:

```bash
bci topics                                            # list the 10 topics
bci invent multiplexed_reporters "acoustic, deep"     # invent + grade from the terminal
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
LOCAL_LLM_MODEL=qwen3.5:9b
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxx
BCI_LLM_MODEL=qwen/qwen2.5-7b-instruct
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
# install Ollama, then pull the model you're using (e.g. Qwen 3.5 9B):
ollama pull qwen3.5:9b            # use whatever tag `ollama list` shows
ollama serve                     # serves an OpenAI-compatible API on :11434
```

Set the environment variables (the adapter is **local-first**); `LOCAL_LLM_MODEL` is just the
Ollama tag, so point it at your downloaded model:

**Windows (PowerShell)**
```powershell
$env:LOCAL_LLM_URL   = "http://localhost:11434/v1"
$env:LOCAL_LLM_MODEL = "qwen3.5:9b"
```

**Linux / macOS**
```bash
export LOCAL_LLM_URL="http://localhost:11434/v1"
export LOCAL_LLM_MODEL="qwen3.5:9b"
```

> Any OpenAI-compatible model works — the adapter doesn't hard-code Qwen. Confirm the exact tag
> with `ollama list` after the download finishes, and use that string for `LOCAL_LLM_MODEL`.

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
LOCAL_LLM_MODEL=qwen2.5:7b-instruct bci invent multiplexed_reporters "acoustic, deep, safe"
# a newer, larger model:
LOCAL_LLM_MODEL=qwen3.5:9b          bci invent multiplexed_reporters "acoustic, deep, safe"
```

**Windows (PowerShell)** — set, run, repeat:
```powershell
$env:LOCAL_LLM_MODEL = "qwen2.5:7b-instruct"; bci invent multiplexed_reporters "acoustic, deep, safe"
$env:LOCAL_LLM_MODEL = "qwen3.5:9b";          bci invent multiplexed_reporters "acoustic, deep, safe"
```

Compare the `passed`, `score`, and `limiting` fields across the 10 topics. Whichever yields more
passes / higher scores is empirically better **for this task** — the answer that matters, and it's
model-agnostic.

> Confirm the exact model tag first with `ollama show <tag>` / `ollama list`, and read its model
> card. A larger, newer, reasoning-capable model usually invents better; a smaller one iterates
> faster. `bci serve` shows the active provider in the cockpit's controls card.

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
cd backend && pip install -e ".[dev,plot,api]"
```
