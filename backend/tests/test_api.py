"""Tests for the thin FastAPI backend + the zero-dependency .env loader."""

from __future__ import annotations

import os

import pytest


def test_dotenv_loader_sets_missing_and_respects_existing(tmp_path, monkeypatch):
    from bciv3 import llm
    (tmp_path / ".env").write_text('FOO_BAR_V3=from_file\nLOCAL_LLM_MODEL="qwen3.5:9b"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FOO_BAR_V3", raising=False)
    monkeypatch.setenv("LOCAL_LLM_MODEL", "already-set")   # existing must win
    llm._load_dotenv()
    assert os.environ["FOO_BAR_V3"] == "from_file"
    assert os.environ["LOCAL_LLM_MODEL"] == "already-set"


def test_extract_json_survives_thinking_models():
    from bciv3 import llm
    # Qwen3-style: reasoning block (with DRAFT json) then the real answer last
    out = (
        "<think>\nLet me draft options. Maybe {\"title\": \"draft\", \"params\": {}}\n</think>\n"
        '{"title": "Real Wave", "params": {"barcode_bits": 48, "channels": 16}}'
    )
    d = llm.extract_json(out)
    assert d["title"] == "Real Wave" and d["params"]["barcode_bits"] == 48

    # plaintext "Thinking... ...done thinking." form
    out2 = "Thinking...\nblah {\"x\": 1} blah\n...done thinking.\n\n{\"title\": \"Y\", \"params\": {\"a\": 2}}"
    d2 = llm.extract_json(out2)
    assert d2["title"] == "Y" and d2["params"]["a"] == 2

    assert llm.extract_json("no json here") is None


def test_api_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from bciv3.api.app import app
    c = TestClient(app)

    assert c.get("/api/health").json()["backends"]["fallback"] is True
    t = c.get("/api/topics").json()
    assert len(t["topics"]) == 10 and len(t["lenses"]) == 10

    r = c.post("/api/invent", json={"topic": "multiplexed_reporters", "backend": "fallback"}).json()
    assert r["result"]["passed"] and set(r["candidate"]["params"])

    assert c.post("/api/invent", json={"topic": "nope", "backend": "fallback"}).json().get("error")

    rk = c.post("/api/rank", json={"topic": "neuron_delivery", "backend": "fallback"}).json()
    assert len(rk["ranked"]) == 10


def test_api_record_save_group_delete(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setenv("BCIV3_JSONL", str(tmp_path / "api.jsonl"))
    monkeypatch.setenv("MONGODB_URI", "mongodb://127.0.0.1:1")     # force JSONL fallback
    import importlib
    import bciv3.store as store_mod
    importlib.reload(store_mod)                                     # picks up the tmp JSONL path
    from fastapi.testclient import TestClient
    from bciv3.api.app import app                                   # holds a live ref to store_mod
    c = TestClient(app)

    rec = c.post("/api/record", json={"topic": "multiplexed_reporters", "backend": "fallback"}).json()["record"]
    assert rec["id"] and rec["detail"]["physics"] and rec["parts"] and rec["score"]["passed"]

    grouped = c.get("/api/inventions/grouped").json()["groups"]
    assert len(grouped) == 10 and len(grouped["multiplexed_reporters"]) == 1

    assert c.delete(f"/api/inventions/{rec['id']}").json()["deleted"] is True
    assert len(c.get("/api/inventions/grouped").json()["groups"]["multiplexed_reporters"]) == 0
