"""Tests for the curated prototype presets (bci synthesize --preset ...)."""

from __future__ import annotations

import pytest


def test_presets_are_well_formed():
    from bciv3 import presets
    from bciv3.innovations import all_ids
    topics = set(all_ids())
    assert set(presets.names()) == set(presets.PRESET_INFO)
    for name in presets.names():
        sel = presets.get(name)
        assert set(sel) == topics, f"{name} must cover all 10 topics"
        # every pick is a full 32-char record id
        assert all(isinstance(v, str) and len(v) == 32 for v in sel.values()), name


def test_get_is_case_insensitive_and_none_on_miss():
    from bciv3 import presets
    assert presets.get("ECHO") == presets.get("echo")
    assert presets.get("  Echo ") == presets.get("echo")
    assert presets.get("does-not-exist") is None
    assert presets.get(None) is None


def test_api_presets_endpoint():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from bciv3.api.app import app
    from bciv3 import presets
    c = TestClient(app)
    body = c.get("/api/presets").json()
    assert set(body["presets"]) == set(presets.names())
    assert body["info"]["echo"]
