"""Unified chat-LLM adapter (stdlib only) — the reasoning backend for the invention engine
(ported from inventor-studio-v3, same pattern as BCI v1's bci.llm).

**Local-first**, per the v3 setup: providers are tried in this order for ``backend="auto"``:
  1. **local**   — any OpenAI-compatible server (Ollama / vLLM / llama.cpp / LM Studio) hosting
                   your Qwen 7B. Set ``LOCAL_LLM_URL`` (e.g. http://localhost:11434/v1) and
                   ``LOCAL_LLM_MODEL`` (e.g. qwen2.5:7b). This is the default path.
  2. **nvidia**  — NVIDIA NIM (OpenAI-compatible). Set ``NVIDIA_API_KEY`` (or ``NGC_API_KEY``).
  3. **openai** / **anthropic** / **openrouter** — cloud fallbacks via their keys.

Everything degrades gracefully: with no provider set, the invention engine falls back to its
deterministic rule-based proposer, so v3 always runs (CI / offline / no GPU).
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def _load_dotenv() -> None:
    """Zero-dependency .env loader: read KEY=VALUE lines from the first .env found walking up from
    here (backend/ or repo root). Existing environment variables always win, so real exported vars
    override the file. Paste LOCAL_LLM_URL / LOCAL_LLM_MODEL / NVIDIA_API_KEY etc. into .env."""
    here = Path(__file__).resolve()
    for base in [Path.cwd(), *here.parents]:
        env = base / ".env"
        if env.is_file():
            for line in env.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
            return


_load_dotenv()

NVIDIA_BASE = "https://integrate.api.nvidia.com/v1"
OPENAI_BASE = "https://api.openai.com/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def provider() -> str | None:
    if os.environ.get("LOCAL_LLM_URL"):
        return "local"
    if os.environ.get("NVIDIA_API_KEY") or os.environ.get("NGC_API_KEY"):
        return "nvidia"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    return None


def available() -> bool:
    return provider() is not None


def _post(url: str, headers: dict, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _chat(base: str, key: str | None, model: str, prompt: str, max_tokens: int, timeout: float,
          json_mode: bool = True) -> str:
    # Always send a bearer header (Ollama ignores it) — matches inventor-studio-v3's client.
    headers = {"content-type": "application/json", "Authorization": f"Bearer {key or 'local-no-auth'}"}
    payload = {"model": model, "max_tokens": max_tokens, "temperature": 0.6,
               "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        # Force valid-JSON output. Critical for thinking models (Qwen3.5): without it the reasoning
        # prose eats the token budget and the JSON never arrives → parse fails → fallback.
        payload["response_format"] = {"type": "json_object"}
    data = _post(f"{base.rstrip('/')}/chat/completions", headers, payload, timeout)
    return data["choices"][0]["message"]["content"]


def invoke_json(prompt: str, max_tokens: int = 2000, timeout: float = 120.0) -> str:
    """Return raw model text (expected JSON). Raises if no provider / on failure.

    For thinking models (Qwen3, etc.) the default token budget is generous so the JSON that
    follows the reasoning isn't truncated. Set ``BCI_LLM_NO_THINK=1`` to append ``/no_think`` —
    Qwen3 then skips the reasoning block entirely, for faster, cleaner structured output."""
    if os.environ.get("BCI_LLM_NO_THINK") in ("1", "true", "yes"):
        prompt = prompt + "\n/no_think"
    timeout = float(os.environ.get("BCI_LLM_TIMEOUT", timeout))    # local 9B cold-loads are slow
    p = provider()
    if p == "local":
        return _chat(os.environ["LOCAL_LLM_URL"], os.environ.get("LOCAL_LLM_KEY"),
                     os.environ.get("LOCAL_LLM_MODEL", "qwen2.5:7b"), prompt, max_tokens, timeout)
    if p == "nvidia":
        key = os.environ.get("NVIDIA_API_KEY") or os.environ["NGC_API_KEY"]
        return _chat(NVIDIA_BASE, key, os.environ.get("BCI_LLM_MODEL", "qwen/qwen2.5-7b-instruct"),
                     prompt, max_tokens, timeout)
    if p == "openai":
        return _chat(OPENAI_BASE, os.environ["OPENAI_API_KEY"],
                     os.environ.get("BCI_LLM_MODEL", "gpt-4o-mini"), prompt, max_tokens, timeout)
    if p == "openrouter":
        return _chat(OPENROUTER_BASE, os.environ["OPENROUTER_API_KEY"],
                     os.environ.get("BCI_LLM_MODEL", "qwen/qwen-2.5-7b-instruct"), prompt, max_tokens, timeout)
    if p == "anthropic":
        data = _post("https://api.anthropic.com/v1/messages",
                     {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                      "content-type": "application/json"},
                     {"model": os.environ.get("BCI_LLM_MODEL", "claude-sonnet-5"), "max_tokens": max_tokens,
                      "temperature": 0.6, "messages": [{"role": "user", "content": prompt}]}, timeout)
        return "".join(b.get("text", "") for b in data.get("content", []))
    raise RuntimeError("no LLM provider configured (set LOCAL_LLM_URL / NVIDIA_API_KEY / …)")


def _strip_thinking(s: str) -> str:
    """Remove reasoning blocks that thinking models (Qwen3, DeepSeek-R1, …) emit before the
    answer — otherwise draft JSON inside the reasoning confuses the extractor."""
    import re
    s = re.sub(r"<think>[\s\S]*?</think>", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"<think>[\s\S]*", " ", s, flags=re.IGNORECASE)                 # unclosed
    s = re.sub(r"Thinking\.\.\.[\s\S]*?\.\.\.\s*done thinking\.?", " ", s, flags=re.IGNORECASE)
    return s


def _balanced_objects(s: str) -> list[str]:
    """All top-level {...} spans, in order (depth-0 to depth-0)."""
    objs, depth, start = [], 0, None
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                objs.append(s[start:i + 1]); start = None
    return objs


def extract_json(text: str) -> dict | None:
    """Parse a JSON object from model output — tolerant of markdown fences, surrounding prose, and
    thinking-model reasoning blocks. Prefers the LAST valid top-level object (the real answer that
    follows any reasoning), so it survives Qwen3-style `Thinking… …done thinking.` output."""
    s = _strip_thinking(str(text))
    try:
        return json.loads(s)
    except Exception:
        pass
    for frag in reversed(_balanced_objects(s)):     # last well-formed object wins
        try:
            return json.loads(frag)
        except Exception:
            continue
    return None
