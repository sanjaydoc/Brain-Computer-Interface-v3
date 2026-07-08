"""Tests for the benchmark sweep + its storage (JSONL fallback in CI)."""

from __future__ import annotations

import importlib


def test_bench_sweeps_all_topics(tmp_path, monkeypatch):
    monkeypatch.setenv("BCIV3_BENCH_JSONL", str(tmp_path / "bench.jsonl"))
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:1")     # force JSONL fallback
    import bciv3.store as store_mod
    importlib.reload(store_mod)
    import bciv3.bench as bench_mod
    importlib.reload(bench_mod)

    res = bench_mod.run(samples=2, backend="fallback", save_attempts=False)
    assert len(res["per_topic"]) == 10
    for t in res["per_topic"].values():
        assert t["samples"] == 2 and 0 <= t["pass_rate"] <= 1 and 0 <= t["mean_score"] <= 1
    assert 0 <= res["mean_pass_rate"] <= 1 and 0 <= res["mean_score"] <= 1
    assert res["id"]                                              # summary saved

    saved = store_mod.list_benchmarks()
    assert len(saved) == 1 and saved[0]["samples_per_topic"] == 2


def test_bench_single_topic(monkeypatch, tmp_path):
    monkeypatch.setenv("BCIV3_BENCH_JSONL", str(tmp_path / "b2.jsonl"))
    import bciv3.bench as bench_mod
    res = bench_mod.run(samples=1, topics=["multiplexed_reporters"], backend="fallback", save_summary=False)
    assert list(res["per_topic"]) == ["multiplexed_reporters"]
    assert res["per_topic"]["multiplexed_reporters"]["passes"] == 1     # rule-based passes
