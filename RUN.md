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
pip install -e ".[dev,plot]"

python -m pytest -q               # expect: 13 passed
python scripts\demo_invent.py --plot
```

### Linux / macOS (bash / zsh)

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,plot]"

python -m pytest -q               # expect: 13 passed
python scripts/demo_invent.py --plot
```

`demo_invent.py` invents a design for each of the 10 topics, grades every one against the law
simulator, prints a scorecard, and writes `docs/media/scorecard.png`.

---

## 3. Live LLM in the cockpit — the FastAPI backend

The browser cockpit runs the deterministic proposer on its own. Start the backend and it routes
**Invent + Simulate** through the Python engine — so the real LLM lenses + critique loop (and your
local Qwen) run, and the design flows back into the cockpit.

```bash
cd backend
pip install -e ".[api]"
uvicorn bciv3.api.app:app --port 8000        # add --reload while developing
```

Then serve the cockpit (separate terminal) and open it — it auto-detects the backend on
`http://localhost:8000` and shows the active provider (e.g. `qwen3.5:9b (backend)`):

```bash
cd docs && python -m http.server 8097        # → http://localhost:8097/app/
```

> Point the cockpit at a different backend URL from the browser console:
> `localStorage.setItem('bciv3_api','http://host:8000')`. If the backend is down, the cockpit
> silently falls back to the in-browser proposer.

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
cd backend && pip install -e ".[dev,plot]"
```
