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
