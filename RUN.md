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

## 3. Wire your local LLM (Qwen) — optional

The engine runs fully **without** an LLM (deterministic rule-based fallback). To use your local
**Qwen 7B** for real creative invention, point the adapter at any OpenAI-compatible server
(Ollama / vLLM / llama.cpp / LM Studio).

### Example: Ollama + Qwen

```bash
# install Ollama, then:
ollama pull qwen2.5:7b-instruct
ollama serve                      # serves an OpenAI-compatible API on :11434
```

Set the environment variables (the adapter is **local-first**):

**Windows (PowerShell)**
```powershell
$env:LOCAL_LLM_URL   = "http://localhost:11434/v1"
$env:LOCAL_LLM_MODEL = "qwen2.5:7b-instruct"
```

**Linux / macOS**
```bash
export LOCAL_LLM_URL="http://localhost:11434/v1"
export LOCAL_LLM_MODEL="qwen2.5:7b-instruct"
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

## 4. Use it from Python

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

## 5. Updating later

```bash
git pull origin main
cd backend && pip install -e ".[dev,plot]"
```
