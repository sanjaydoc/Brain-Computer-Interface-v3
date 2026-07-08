"""Tests for the detailer + store + recorder — the DB-capture path (JSONL fallback in CI)."""

from __future__ import annotations

import bciv3
from bciv3 import invent, detail, all_ids
from bciv3.innovations import CATALOG


def test_every_topic_gets_full_multidomain_detail():
    for tid in all_ids():
        d = detail(tid, invent(tid, backend="fallback"))
        for key in ("biology", "biophysics", "physics", "electronics", "summary"):
            assert key in d["detail"] and d["detail"][key]
        assert d["parts"] and all("name" in p and "role" in p for p in d["parts"])


def test_record_is_complete_and_scored():
    rec = bciv3.build_record("multiplexed_reporters", invent("multiplexed_reporters", backend="fallback"), "acoustic")
    for key in ("ts", "topic", "layer", "domain", "laws", "params", "detail", "parts", "score"):
        assert key in rec
    assert rec["score"]["passed"] is True and 0 <= rec["score"]["score"] <= 1
    assert rec["detail"]["physics"] and rec["parts"]


def test_save_and_list_roundtrip_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("BCIV3_JSONL", str(tmp_path / "inv.jsonl"))
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:1")   # force fallback (unreachable)
    import importlib
    from bciv3 import store as store_mod
    importlib.reload(store_mod)
    assert store_mod.backend().startswith("jsonl")

    rid = store_mod.save({"topic": "neuron_delivery", "title": "X", "score": {"passed": True, "score": 0.9}})
    assert rid
    rows = store_mod.list_records("neuron_delivery")
    assert len(rows) == 1 and rows[0]["title"] == "X"
    st = store_mod.stats()
    assert st["total"] == 1 and st["per_topic"]["neuron_delivery"]["passes"] == 1
