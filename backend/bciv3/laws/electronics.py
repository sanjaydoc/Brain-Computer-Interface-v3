"""Electronics law-checkers — the circuit/readout side of the simulator (ported in spirit from
inventor-studio-v3's hardware/electronics domain).

Grades whether a proposed readout is buildable: how many distinguishable channels a technology
can actually resolve, whether the sampling bandwidth covers the signal, the power budget, and
whether a transducer array of the required size is physically sensible.
"""

from __future__ import annotations

# Distinguishable channels a readout technology can resolve today (order-of-magnitude).
CHANNEL_CEILING = {
    "acoustic_collapse": 16,   # gas-vesicle collapse-pressure bands
    "mri_relaxation": 8,       # relaxation / CEST bins
    "pet_tracer": 6,           # co-injected radiotracers
    "spectral_optical": 32,    # fluorescent colours (surface only)
    "sequencing": 1_000_000,   # DNA barcodes — but destructive / ex-vivo
}


def channels_feasible(channels: int, tech: str) -> bool:
    """Is the requested channel count within what this readout technology can resolve?"""
    return int(channels) <= CHANNEL_CEILING.get(tech, 8)


def channel_headroom(channels: int, tech: str) -> float:
    """0..1 — how far the requested channels are inside the technology ceiling (1 = trivial)."""
    ceil = CHANNEL_CEILING.get(tech, 8)
    return max(0.0, min(1.0, 1.0 - int(channels) / max(ceil, 1)))


def bandwidth_ok(sample_rate_hz: float, signal_bw_hz: float) -> bool:
    """Nyquist: the sampler must run at ≥2× the signal bandwidth."""
    return float(sample_rate_hz) >= 2.0 * float(signal_bw_hz)


def power_budget_ok(power_mw: float, budget_mw: float) -> bool:
    return float(power_mw) <= float(budget_mw)


def array_elements_feasible(n_elements: int, ceiling: int = 100_000) -> bool:
    """A transducer/detector array is buildable only up to a practical element count."""
    return 1 <= int(n_elements) <= ceiling


def scan_time_s(brain_volume_mm3: float, voxel_um: float, dwell_s: float, parallel_channels: int) -> float:
    """Total read time = (#voxels × per-voxel dwell) ÷ parallel channels. Turns 'average longer to
    cut noise' into a wall: more voxels or longer dwell blows up the whole-brain scan time."""
    voxel_mm3 = (float(voxel_um) / 1000.0) ** 3
    n_voxels = float(brain_volume_mm3) / max(voxel_mm3, 1e-12)
    return n_voxels * float(dwell_s) / max(int(parallel_channels), 1)
