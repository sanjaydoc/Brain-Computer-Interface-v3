"""Retrieval orchestrator — run the sources in parallel, report per-source status, and build a
prior-art context block that grounds the invention engine. Everything degrades gracefully:
sources that fail, time out, aren't configured, or simply have no results contribute nothing and
are reported as such (so "why only arxiv?" is always answerable).
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from .sources import SOURCES, DEFAULT_SOURCES


def _clean(query: str) -> str:
    """Punctuation-free keyword query — PubMed/Wikipedia match far better without commas etc."""
    q = re.sub(r"[^\w\s-]", " ", str(query or ""))
    return re.sub(r"\s+", " ", q).strip()


def _enabled(sources) -> list[str]:
    if sources:
        return [s for s in sources if s in SOURCES]
    env = os.environ.get("BCIV3_SEARCH_SOURCES")
    if env:
        return [s.strip() for s in env.split(",") if s.strip() in SOURCES]
    return list(DEFAULT_SOURCES)


def _run(name: str, q: str, per: int):
    """Return (citations, status) for one source — never raises."""
    try:
        cs = SOURCES[name](q, per) or []
        return cs, (f"{len(cs)} result(s)" if cs else "no results")
    except Exception as exc:
        return [], f"error: {type(exc).__name__}"


def _fulltext_enabled(flag) -> bool:
    if flag is not None:
        return bool(flag)
    return os.environ.get("BCIV3_FULLTEXT", "").lower() in ("1", "true", "yes")


def _summarize_fulltext(citations: list[dict], focus: str) -> list[dict]:
    """For the top-K citations: fetch the FULL publication, then have the LLM distill it into a dense,
    detail-preserving brief that replaces the abstract. This is how we feed 'the whole paper' without
    blowing the context window — the model reads a faithful summary, not 15k raw tokens per paper.

    Needs an LLM (to summarize) and is slow (a fetch + a summary call per doc), so it's opt-in
    (BCIV3_FULLTEXT=1). Falls back to the abstract for any doc that can't be fetched/summarized."""
    from .sources import read_page
    from .. import llm
    if not citations or not llm.available():
        return citations
    top_k = int(os.environ.get("BCIV3_FULLTEXT_TOPK", "5"))
    per_doc = int(os.environ.get("BCIV3_SNIPPET_CHARS", "1600"))
    targets = citations[:top_k]

    texts: dict[int, str] = {}                 # fetch full text in parallel (network-bound)
    try:
        with ThreadPoolExecutor(max_workers=min(4, len(targets))) as ex:
            futs = {ex.submit(read_page, c["url"]): i for i, c in enumerate(targets)}
            for fut in as_completed(futs, timeout=90):
                try:
                    texts[futs[fut]] = fut.result()
                except Exception:
                    pass
    except Exception:
        pass

    for i, c in enumerate(targets):            # summarize sequentially (one local GPU serves one call)
        raw = " ".join((texts.get(i) or "").split())
        if len(raw) < 600:                     # too short to beat the abstract we already have
            continue
        prompt = ("You are distilling a source for an engineer inventing a solution to:\n"
                  f"  {focus}\n\nWrite a DENSE technical brief of the source below. Preserve every "
                  "concrete useful detail — mechanisms, materials, quantitative values/parameters, "
                  "methods, results, and limitations. No preamble, 150-220 words.\n\n"
                  f"SOURCE TITLE: {c['title']}\n\nSOURCE TEXT:\n{raw[:12000]}")
        try:
            s = " ".join((llm.invoke_text(prompt, max_tokens=400) or "").split())
            if len(s) > 80:
                c["snippet"] = s[:per_doc]
                c["fulltext"] = True
        except Exception:
            pass
    return citations


def retrieve(query: str, *, sources=None, per: int = 3, timeout: float = 15.0, fulltext=None) -> dict:
    """Search the enabled sources; return {context, citations, sources_used, per_source}.

    With ``fulltext`` (or BCIV3_FULLTEXT=1): fetch the full publication for the top hits and distill
    each with the LLM before grounding — richer, but slower and requires an LLM."""
    q = _clean(query)
    names = _enabled(sources)
    if not q or not names:
        return {"context": "", "citations": [], "sources_used": [], "per_source": {}}

    citations: list[dict] = []
    per_source: dict[str, str] = {}
    try:
        with ThreadPoolExecutor(max_workers=min(8, len(names))) as ex:
            futs = {ex.submit(_run, n, q, per): n for n in names}
            for fut in as_completed(futs, timeout=timeout):
                name = futs[fut]
                try:
                    cs, status = fut.result()
                except Exception:
                    cs, status = [], "error"
                per_source[name] = status
                citations.extend(cs)
    except Exception:
        pass                                   # overall timeout — keep whatever completed
    for n in names:
        per_source.setdefault(n, "timeout")

    if _fulltext_enabled(fulltext):
        citations = _summarize_fulltext(citations, query)

    used = sorted({c["source"] for c in citations})
    return {"context": build_context(citations), "citations": citations,
            "sources_used": used, "per_source": per_source}


def build_context(citations: list[dict], limit: int = 14) -> str:
    """Assemble the grounding block, BUDGETED to a total character cap so it fits the model's context
    window. Full papers are never fed (a single paper is ~10k tokens; 14 would blow past even a 32k
    window) — we feed titles + abstracts, capped. Raise BCIV3_CONTEXT_CHARS only if you've also raised
    your local model's context length (e.g. Ollama OLLAMA_CONTEXT_LENGTH); otherwise the prompt gets
    truncated and the JSON instructions at the end can be lost."""
    if not citations:
        return ""
    max_chars = int(os.environ.get("BCIV3_CONTEXT_CHARS", "6000"))
    lines, used = [], 0
    for c in citations[:limit]:
        snip = f" — {c['snippet']}" if c.get("snippet") else ""
        line = f"- [{c['source']}] {c['title']}{snip} ({c['url']})"
        if lines and used + len(line) > max_chars:
            break
        lines.append(line); used += len(line)
    return "PRIOR KNOWLEDGE (retrieved literature / prior art):\n" + "\n".join(lines)
