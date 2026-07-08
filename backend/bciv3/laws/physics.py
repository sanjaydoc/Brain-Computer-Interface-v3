"""Physics law-checkers — the wave/information side of the simulator.

Every invention that moves a signal through tissue or encodes identity is graded here:
wave attenuation → SNR at depth, the resolution wall, and the barcode capacity law
(carried over from BCI v2's readout model). These are the hard limits an LLM proposal
cannot argue its way past.
"""

from __future__ import annotations

import math

# deep, non-destructive reporter+sensor pairings (mirror of BCI v2)
MODALITIES = {
    "fus":  {"label": "focused ultrasound",       "penetration_um": 80_000.0, "wavelength_um": 300.0},
    "mri":  {"label": "MRI",                        "penetration_um": 1e9,      "wavelength_um": 1e5},
    "pet":  {"label": "PET",                        "penetration_um": 1e9,      "wavelength_um": 1e6},
    "nirs": {"label": "near-infrared (fNIRS)",      "penetration_um": 3_000.0,  "wavelength_um": 0.9},
    "xray": {"label": "X-ray / CT",                 "penetration_um": 1e9,      "wavelength_um": 1e-4},
}


def required_bits(syn_per_voxel: float, epsilon: float = 0.01) -> int:
    """Capacity law: barcode bits needed so the collision probability among k reporters in one
    voxel stays below epsilon (birthday bound). This is the information wall behind multiplexing."""
    k = max(float(syn_per_voxel), 1.0)
    c = k * k / (2.0 * max(epsilon, 1e-9))
    return int(math.ceil(math.log2(max(c, 2.0))))


def snr_at_depth(snr0: float, depth_um: float, penetration_um: float) -> float:
    """Signal-to-noise after attenuation over `depth` with a modality's penetration length."""
    return float(snr0) * math.exp(-float(depth_um) / max(float(penetration_um), 1e-9))


def p_detect(snr: float, threshold: float = 1.0) -> float:
    """Smooth detection probability from SNR — 1 when signal dominates, 0 when it drowns."""
    return snr / (snr + max(threshold, 1e-9))


def averaging_gain(n: int) -> float:
    """SNR improves as sqrt(N) with N independent averages — the noise-cutting lever."""
    return math.sqrt(max(int(n), 1))


def positional_resolution_ok(wavelength_um: float, target_nm: float) -> bool:
    """Can the wave resolve the target feature by POSITION? Diffraction limit ≈ wavelength/2.
    For a ~20 nm synapse this is essentially always False for any penetrating wave — which is
    exactly why identity (barcodes), not position, must carry the resolution."""
    diffraction_nm = (wavelength_um * 1000.0) / 2.0
    return diffraction_nm <= float(target_nm)


def channel_info_bits(channels: int) -> float:
    """Bits of identity a readout with `channels` distinguishable states can carry per voxel."""
    return math.log2(max(int(channels), 1))
