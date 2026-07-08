"""Tests for the law engines — the deterministic physics/biophysics/electronics core."""

from __future__ import annotations

from bciv3.laws import physics as P, biophysics as B, electronics as E


def test_capacity_law_grows_with_density():
    assert P.required_bits(1e6) > P.required_bits(1e3) > P.required_bits(10)
    assert 30 <= P.required_bits(1e6) <= 60


def test_snr_falls_with_depth():
    shallow = P.snr_at_depth(12, 1_000, 80_000)
    deep = P.snr_at_depth(12, 75_000, 80_000)
    assert shallow > deep
    assert 0 < P.p_detect(deep) < P.p_detect(shallow) < 1


def test_positional_resolution_wall():
    # no penetrating wave resolves a 20 nm synapse by position
    assert not P.positional_resolution_ok(300.0, 20.0)     # ultrasound
    assert not P.positional_resolution_ok(0.9, 20.0)       # NIR light


def test_safety_limits():
    assert B.thermal_dose_ok(500) and not B.thermal_dose_ok(1000)
    assert B.mechanical_index_ok(1.2) and not B.mechanical_index_ok(2.5)
    assert B.aav_dose_ok(5e13) and not B.aav_dose_ok(5e14)
    assert 0 <= B.safety_margin(500, 1.2, 5e13) <= 1


def test_channels_and_scan_time():
    assert E.channels_feasible(8, "acoustic_collapse")
    assert not E.channels_feasible(1000, "acoustic_collapse")
    fast = E.scan_time_s(1.4e6, 100, 1e-3, 65536)
    slow = E.scan_time_s(1.4e6, 100, 1e-3, 8)
    assert slow > fast > 0
