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


def retrieve(query: str, *, sources=None, per: int = 3, timeout: float = 15.0) -> dict:
    """Search the enabled sources; return {context, citations, sources_used, per_source}."""
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

    used = sorted({c["source"] for c in citations})
    return {"context": build_context(citations), "citations": citations,
            "sources_used": used, "per_source": per_source}


def build_context(citations: list[dict], limit: int = 14) -> str:
    if not citations:
        return ""
    lines = []
    for c in citations[:limit]:
        snip = f" — {c['snippet']}" if c.get("snippet") else ""
        lines.append(f"- [{c['source']}] {c['title']}{snip} ({c['url']})")
    return "PRIOR KNOWLEDGE (retrieved literature / prior art):\n" + "\n".join(lines)
