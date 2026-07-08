"""Biophysics law-checkers — the living-tissue side of the simulator.

Grades inventions that touch cells: delivery coverage, reporter expression/readability, and the
safety envelope (thermal dose, mechanical index, viral dose). These are the limits that decide
whether a design is compatible with a *living* brain rather than a slice.
"""

from __future__ import annotations

import math

# Regulatory / safety reference limits (diagnostic-ultrasound + gene-therapy literature).
FDA_ISPTA_MW_CM2 = 720.0      # spatial-peak temporal-average intensity ceiling (diagnostic US)
FDA_MECHANICAL_INDEX = 1.9    # mechanical index ceiling
AAV_DOSE_CEILING_VG_KG = 1e14  # systemic AAV dose above which toxicity risk rises sharply


def blind_fraction(transduction_fraction: float) -> float:
    """Un-labeled neurons are coverage blind spots. frac=1.0 → no blind spots."""
    return 1.0 - min(max(float(transduction_fraction), 0.0), 1.0)


def reporter_readable(expression_level: float, snr: float, express_ref: float = 1.0) -> float:
    """Probability a reporter is bright enough to read: scales with expression and SNR."""
    e = min(max(expression_level / max(express_ref, 1e-9), 0.0), 4.0)
    return (e * snr) / (e * snr + 1.0)


def thermal_dose_ok(ispta_mw_cm2: float) -> bool:
    return float(ispta_mw_cm2) <= FDA_ISPTA_MW_CM2


def mechanical_index_ok(mi: float) -> bool:
    return float(mi) <= FDA_MECHANICAL_INDEX


def aav_dose_ok(vg_per_kg: float) -> bool:
    return float(vg_per_kg) <= AAV_DOSE_CEILING_VG_KG


def safety_margin(ispta_mw_cm2: float, mi: float, vg_per_kg: float) -> float:
    """0..1 headroom under the tightest safety limit (1 = far inside all limits, 0 = at/over)."""
    margins = [
        1.0 - float(ispta_mw_cm2) / FDA_ISPTA_MW_CM2,
        1.0 - float(mi) / FDA_MECHANICAL_INDEX,
        1.0 - float(vg_per_kg) / AAV_DOSE_CEILING_VG_KG,
    ]
    return max(0.0, min(1.0, min(margins)))


def membrane_tau_ms(permeability: float) -> float:
    """Membrane time constant from a normalized permeability knob (v1 biophysics heuristic):
    higher permeability → faster (leakier) membrane. Bounds keep neurons in a sane regime."""
    return max(2.0, 25.0 - float(permeability) * 18.0)
