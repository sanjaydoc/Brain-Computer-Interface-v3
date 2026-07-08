"""The closed invent → simulate → refine loop, plus candidate ranking.

`design` runs one candidate and, on a simulator failure, feeds the limiting factor back to the
engine to repair it (ported from inventor-studio-v3's critique loop). `rank` generates several
candidates through different lenses and orders them by simulated score — a small idea tournament.
"""

from __future__ import annotations

from .. import llm
from ..innovations import get
from ..simulator import simulate
from .inventor import invent, _rule_based, _sanitize_params
from .prompt import LENSES, build_refine_prompt


def design(topic_id: str, prompt: str = "", *, rounds: int = 2, lens: str = "biomimicry",
           backend: str = "auto") -> dict:
    """Invent → simulate → (on fail) refine, up to `rounds`. Returns the best candidate + history."""
    inv = get(topic_id)
    cand = invent(topic_id, prompt, lens=lens, backend=backend)
    score = simulate(topic_id, cand)
    history = [{"candidate": cand, "score": score.as_dict()}]

    r = 1
    while not score.passed and r < rounds:
        r += 1
        nxt = _refine(inv, cand, score, backend)
        nscore = simulate(topic_id, nxt)
        history.append({"candidate": nxt, "score": nscore.as_dict()})
        if nscore.score >= score.score:
            cand, score = nxt, nscore
        if score.passed:
            break
    return {"topic": topic_id, "best": cand, "score": score.as_dict(),
            "passed": score.passed, "rounds": r, "history": history}


def _refine(inv, prev, score, backend):
    chosen = backend if backend != "auto" else ("llm" if llm.available() else "fallback")
    if chosen == "llm":
        try:
            parsed = llm.extract_json(llm.invoke_json(build_refine_prompt(inv, prev, score), max_tokens=1600))
            if parsed and parsed.get("params"):
                return {**prev, "title": str(parsed.get("title") or prev["title"])[:80],
                        "mechanism": str(parsed.get("mechanism") or prev.get("mechanism", ""))[:400],
                        "params": _sanitize_params(inv, parsed.get("params")), "backend": "llm-refine"}
        except Exception:
            pass
    return _rule_based(inv, "aggressive")            # fallback nudges knobs harder


def rank(topic_id: str, prompt: str = "", *, lenses: list[str] | None = None,
         backend: str = "auto") -> list[dict]:
    """Generate one candidate per lens, grade them, and return them best-first."""
    lenses = lenses or list(LENSES)
    out = []
    for ln in lenses:
        c = invent(topic_id, prompt, lens=ln, backend=backend)
        s = simulate(topic_id, c)
        out.append({"lens": ln, "passed": s.passed, "score": round(s.score, 3),
                    "limiting": s.limiting, "title": c.get("title", ""), "params": c.get("params", {})})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out
