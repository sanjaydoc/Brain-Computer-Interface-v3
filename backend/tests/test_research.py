"""Tests for the research-monograph generator (bciv3.research.build_html)."""

from __future__ import annotations


def _fake_synth():
    """A minimal saved-synthesis record with an embedded pipeline (no store lookup needed)."""
    return {
        "id": "test1234abcd", "ts": "2026-07-09T00:00:00",
        "system": {"system_name": "TestSystem", "engine": "template"},
        "sources": {},  # force pipeline-stage fallback
        "safety": {"title": "Safety module", "params": {"ispta_mw_cm2": 360.0, "mechanical_index": 1.5, "aav_dose_vg_per_kg": 5e13}},
        "pipeline": [
            {"phase": "Label", "stages": [
                {"topic": "neuron_delivery", "title": "TestDelivery", "mechanism": "m",
                 "params": {"transduction_fraction": 0.99, "aav_dose_vg_per_kg": 5e13, "target_coverage": 0.99}, "parts": []},
                {"topic": "multiplexed_reporters", "title": "TestBarcode", "mechanism": "m",
                 "params": {"barcode_bits": 48, "channels": 16, "syn_per_voxel": 1e6, "readout_tech": "acoustic_collapse"}, "parts": []},
            ]},
        ],
    }


def test_build_html_produces_full_monograph():
    from bciv3 import research
    html = research.build_html(_fake_synth(), autoprint=False)
    # core sections present
    for marker in ["Research Monograph", "Abstract", "2. Methods", "Translational roadmap",
                   "Wet-lab and validation experiment program", "References", "TestSystem"]:
        assert marker in html, marker
    # all ten modules appear as numbered subsections
    assert html.count('class="ss modstart"') == 10
    # a wet-lab experiment row per module
    assert html.count(">E1<") == 1 and ">E10<" in html
    assert len(html) > 40000


def test_build_html_autoprint_toggle():
    from bciv3 import research
    assert "window.print()" in research.build_html(_fake_synth(), autoprint=True)
    assert "window.print()" not in research.build_html(_fake_synth(), autoprint=False)
