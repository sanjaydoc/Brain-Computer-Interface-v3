"""Recorder — build a complete, persistable invention record and (optionally) save it.

One call turns a topic + prompt into the full row that lands in the database: the design, its
multi-domain detail (biophysics / physics / electronics / biology), its parts list, and its
simulator score. Timestamped, ready for MongoDB (or the JSONL fallback).
"""

from __future__ import annotations

from datetime import datetime, timezone

from .engine import invent as _invent
from .simulator import simulate
from .detailer import detail
from .innovations import get
from . import store


def build_record(topic: str, candidate: dict, prompt: str = "") -> dict:
    inv = get(topic)
    s = simulate(topic, candidate)
    d = detail(topic, candidate, s)
    cites = candidate.get("citations", [])
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "topic": topic, "title": candidate.get("title", inv.title),
        "layer": inv.layer, "domain": inv.domain, "laws": inv.laws,
        "lens": candidate.get("lens", "—"),
        "backend": candidate.get("backend", "—"), "provider": candidate.get("provider"),
        "grounded": bool(candidate.get("grounded")),
        "prompt": prompt,
        "params": candidate.get("params", {}),
        "mechanism": candidate.get("mechanism", ""),
        "assumptions": candidate.get("assumptions", []),
        "risks": candidate.get("risks", []),
        "detail": d["detail"], "parts": d["parts"],
        "citations": cites, "sources_used": sorted({c["source"] for c in cites}),
        "score": {"passed": s.passed, "score": round(s.score, 4), "fidelity": s.fidelity,
                  "limiting": s.limiting, "metrics": s.as_dict()["metrics"]},
    }


def record(topic: str, prompt: str = "", *, lens: str = "biomimicry", backend: str = "auto",
           ground: bool = True, save: bool = True) -> dict:
    """Search → invent (grounded) → simulate → detail → save. Returns the record with its id.
    Grounding is ON by default: the design is invented from retrieved literature / prior art."""
    cand = _invent(topic, prompt, lens=lens, backend=backend, ground=ground)
    rec = build_record(topic, cand, prompt)
    if save:
        rec["id"] = store.save(rec)
    return rec
