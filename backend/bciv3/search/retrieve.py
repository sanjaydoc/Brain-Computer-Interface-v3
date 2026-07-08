"""Retrieval orchestrator — run the sources in parallel and build a prior-art context block
that grounds the invention engine. Everything degrades gracefully: sources that fail or aren't
configured contribute nothing, so grounding never breaks a run (offline / CI still work).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from .sources import SOURCES, DEFAULT_SOURCES


def _enabled(sources) -> list[str]:
    if sources:
        return [s for s in sources if s in SOURCES]
    env = os.environ.get("BCIV3_SEARCH_SOURCES")
    if env:
        return [s.strip() for s in env.split(",") if s.strip() in SOURCES]
    return list(DEFAULT_SOURCES)


def retrieve(query: str, *, sources=None, per: int = 3, timeout: float = 10.0) -> dict:
    """Search the enabled sources for `query`; return {context, citations, sources_used}."""
    q = (query or "").strip()
    names = _enabled(sources)
    if not q or not names:
        return {"context": "", "citations": [], "sources_used": []}

    citations: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(8, len(names))) as ex:
        futs = {ex.submit(SOURCES[n], q, per): n for n in names}
        for fut in as_completed(futs, timeout=timeout + 5):
            try:
                citations.extend(fut.result() or [])
            except Exception:
                pass

    used = sorted({c["source"] for c in citations})
    return {"context": build_context(citations), "citations": citations, "sources_used": used}


def build_context(citations: list[dict], limit: int = 12) -> str:
    """Compact prior-knowledge block for the LLM prompt."""
    if not citations:
        return ""
    lines = []
    for c in citations[:limit]:
        snip = f" — {c['snippet']}" if c.get("snippet") else ""
        lines.append(f"- [{c['source']}] {c['title']}{snip} ({c['url']})")
    return "PRIOR KNOWLEDGE (retrieved literature / prior art):\n" + "\n".join(lines)
