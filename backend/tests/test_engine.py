"""Tests for the invention engine + simulator — the invent→grade→refine loop."""

from __future__ import annotations

import pytest

import bciv3
from bciv3 import invent, simulate, design, rank, all_ids
from bciv3.innovations import CATALOG


def test_all_ten_topics_present():
    ids = all_ids()
    assert len(ids) == 10
    for i in ids:
        assert CATALOG[i].param_schema and CATALOG[i].laws


def test_fallback_invents_valid_params_for_every_topic():
    """With no LLM, every topic still yields a design whose params match its schema."""
    for tid in all_ids():
        cand = invent(tid, "map the whole brain", backend="fallback")
        assert cand["backend"] == "fallback"
        assert set(cand["params"]) == set(CATALOG[tid].param_schema)


def test_simulator_grades_and_is_deterministic():
    c = invent("multiplexed_reporters", backend="fallback")
    s1 = simulate("multiplexed_reporters", c)
    s2 = simulate("multiplexed_reporters", c)
    assert s1.as_dict() == s2.as_dict()
    assert isinstance(s1.passed, bool) and 0 <= s1.score <= 1


def test_a_good_design_passes_and_a_bad_one_fails():
    # rule-based proposer is spec-aware → should pass the capacity wall
    good = simulate("multiplexed_reporters", invent("multiplexed_reporters", backend="fallback"))
    assert good.passed
    # too few barcode bits → must fail
    bad = bciv3.simulate_params("multiplexed_reporters",
                                {"barcode_bits": 8, "channels": 4, "syn_per_voxel": 1e6, "readout_tech": "acoustic_collapse"})
    assert not bad.passed and "bits" in bad.limiting


def test_fidelity_flags_are_honest():
    assert CATALOG["multiplexed_reporters"].fidelity == "full-sim"
    assert CATALOG["human_safety"].fidelity == "limits-only"
    assert CATALOG["in_vivo_readout"].fidelity == "physics-only"
    assert CATALOG["twin_sim_scale"].fidelity == "estimate"


def test_design_loop_refines_on_failure():
    # start from a failing topic and let the loop refine
    out = design("scan_throughput", "parallelise hard", rounds=2, backend="fallback")
    assert "best" in out and "history" in out
    assert out["score"]["score"] >= out["history"][0]["score"]["score"]


def test_rank_orders_candidates():
    ranked = rank("neuron_delivery", backend="fallback", lenses=["biomimicry", "inversion", "reduction"])
    assert len(ranked) == 3
    assert ranked[0]["score"] >= ranked[-1]["score"]


def test_backends_reports_fallback():
    b = bciv3.backends()
    assert b["fallback"] is True and len(b["lenses"]) == 10
