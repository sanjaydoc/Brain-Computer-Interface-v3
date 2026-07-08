"""Benchmark — sweep the topics N times, grade every attempt, and report a leaderboard.

Turns the invention engine into a measurable thing: for each of the 10 topics, run `samples`
inventions, and aggregate pass-rate + mean/best simulated score. Because the model is just
`LOCAL_LLM_MODEL`, running this twice with different models gives you a head-to-head — the honest
answer to "which model invents better", decided by the physics simulator.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from . import llm, store
from .innovations import all_ids
from .recorder import record


def run(*, topics=None, samples: int = 3, prompt: str = "", backend: str = "auto",
        ground: bool = False, lens: str = "biomimicry", save_attempts: bool = False,
        save_summary: bool = True, model: str | None = None, constraint: str | None = None) -> dict:
    """Run the sweep. `save_attempts` persists every invention to the DB (off by default to avoid
    flooding it); `save_summary` stores the compact leaderboard in the `benchmarks` collection.
    `model` overrides the LLM model for this whole sweep (A-B two models head-to-head)."""
    topics = topics or all_ids()
    per_topic: dict[str, dict] = {}
    for tid in topics:
        scores, passes = [], 0
        for _ in range(max(1, samples)):
            rec = record(tid, prompt, lens=lens, backend=backend, ground=ground,
                         save=save_attempts, model=model, constraint=constraint)
            sc = rec["score"]
            scores.append(sc["score"]); passes += 1 if sc["passed"] else 0
        n = len(scores)
        per_topic[tid] = {"samples": n, "passes": passes,
                          "pass_rate": round(passes / n, 3),
                          "mean_score": round(sum(scores) / n, 4),
                          "best_score": round(max(scores), 4)}

    k = len(per_topic) or 1
    summary = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model or os.environ.get("LOCAL_LLM_MODEL") or os.environ.get("BCI_LLM_MODEL"),
        "provider": llm.provider(),
        "backend": backend, "grounded": ground, "samples_per_topic": samples, "prompt": prompt,
        "mean_pass_rate": round(sum(t["pass_rate"] for t in per_topic.values()) / k, 3),
        "mean_score": round(sum(t["mean_score"] for t in per_topic.values()) / k, 4),
        "per_topic": per_topic,
    }
    if save_summary:
        summary["id"] = store.save_bench(summary)
    return summary
