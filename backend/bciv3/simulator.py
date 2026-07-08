"""The simulator — grade a proposed design against the laws that govern its topic.

Thin on purpose: each Innovation already carries its law-based ``evaluate``. The simulator's job
is to route a candidate (from the invention engine, or hand-written) to that evaluator and return
a Score. Invention proposes; the simulator disposes — a persuasive narrative can never move the
number, only the physics can.
"""

from __future__ import annotations

from .innovations import get, Score


def simulate(topic_id: str, candidate: dict) -> Score:
    """Grade an engine candidate ({'params': {...}}) against its topic's laws."""
    return get(topic_id).evaluate((candidate or {}).get("params", {}))


def simulate_params(topic_id: str, params: dict) -> Score:
    """Grade raw parameters directly (no engine needed)."""
    return get(topic_id).evaluate(params or {})


def report(topic_id: str, candidate: dict) -> dict:
    """A flat, presentable result: the design + its verdict + the limiting factor."""
    inv = get(topic_id)
    s = simulate(topic_id, candidate)
    return {
        "topic": topic_id, "title": candidate.get("title", inv.title),
        "layer": inv.layer, "domain": inv.domain, "laws": inv.laws,
        "backend": candidate.get("backend", "?"), "lens": candidate.get("lens", "?"),
        "params": candidate.get("params", {}),
        "passed": s.passed, "score": round(s.score, 3), "fidelity": s.fidelity,
        "limiting": s.limiting, "metrics": s.as_dict()["metrics"],
    }
