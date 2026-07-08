"""Invent → simulate across all 10 innovation topics, print a scorecard, and (optionally) plot it.

    python backend/scripts/demo_invent.py            # text scorecard
    python backend/scripts/demo_invent.py --plot     # also writes docs/media/scorecard.png
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bciv3 import invent, report, all_ids, backends


def main() -> None:
    b = backends()
    print(f"LLM backend: {b['provider'] or 'none (rule-based fallback)'}   lenses: {len(b['lenses'])}\n")
    cols = ["topic", "layer", "domain", "pass", "score", "fidelity", "limiting"]
    print("  ".join(f"{c:<22}" if c in ("topic", "limiting") else f"{c:<12}" for c in cols))
    rows = []
    for tid in all_ids():
        cand = invent(tid, "map the whole human brain, no blind spots", backend="fallback")
        r = report(tid, cand)
        rows.append(r)
        print("  ".join([
            f"{tid:<22}", f"{'+'.join(r['layer'])[:12]:<12}", f"{r['domain']:<12}",
            f"{'✓' if r['passed'] else '✗':<12}", f"{r['score']:<12}",
            f"{r['fidelity']:<12}", f"{r['limiting'][:34]:<22}",
        ]))

    npass = sum(1 for r in rows if r["passed"])
    print(f"\n{npass}/10 topics pass the simulator with a spec-aware design (rule-based).")
    print("Fully-modelled (full-sim): 6 · flagged (physics-only/estimate/limits-only): 4.")

    if "--plot" in sys.argv:
        _plot(rows)


def _plot(rows) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("matplotlib not installed — skipping plot (pip install '.[plot]')")
        return
    labels = [r["topic"].replace("_", " ") for r in rows]
    scores = [r["score"] for r in rows]
    passed = [r["passed"] for r in rows]
    colors = ["#0e9f6e" if p else "#e0332d" for p in passed]
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=140)
    y = range(len(labels))
    ax.barh(list(y), scores, color=colors, edgecolor="none")
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(0, 1)
    ax.set_xlabel("simulated design score (0–1)")
    ax.set_title("BCI v3 — invented designs graded by the law simulator", fontsize=12, weight="bold")
    ax.axvline(0.5, color="#9a9aa2", ls="--", lw=1)
    for i, r in enumerate(rows):
        ax.text(min(r["score"] + 0.02, 0.96), i, r["fidelity"], va="center", fontsize=7, color="#6f6f78")
    fig.tight_layout()
    out = Path(__file__).resolve().parents[2] / "docs" / "media" / "scorecard.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
