"""The 10 innovation topics from BCI v2's map, each wired to a law-based evaluator.

Human-scale defaults are the targets the invention must clear. 6 topics are fully modelled
(full-sim); 4 are honestly flagged (physics-only / estimate / limits-only).
"""

from __future__ import annotations

from ..laws import physics as P, biophysics as B, electronics as E
from .base import Innovation, Score

# human-scale reference targets
HUMAN_SYN_PER_FUS_VOXEL = 1e6
HUMAN_BRAIN_MM3 = 1.4e6            # ~1.4 L
HUMAN_SYNAPSES = 1e14
DEEP_TARGET_UM = 75_000.0         # deepest brain structures from the surface


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


# 1 — in-vivo, non-destructive barcode readout (physics-only: models the signal-escape half)
def _eval_readout(p) -> Score:
    snr = P.snr_at_depth(p["snr0"], DEEP_TARGET_UM, p["penetration_um"])
    pdet = P.p_detect(snr)
    safe = B.thermal_dose_ok(p["ispta_mw_cm2"]) and B.mechanical_index_ok(p["mechanical_index"])
    score = pdet * (1.0 if safe else 0.2)
    return Score(passed=(pdet >= 0.5 and safe), score=_clip01(score),
                 metrics={"snr_at_depth": snr, "p_detect": pdet, "safe": safe},
                 limiting=("dose over limit" if not safe else "signal escapes" if pdet >= 0.5 else "signal drowns at depth"))


# 2 — massively-multiplexed reporters (full-sim: the capacity wall)
def _eval_multiplex(p) -> Score:
    need = P.required_bits(p["syn_per_voxel"])
    bits_ok = p["barcode_bits"] >= need
    chan_ok = E.channels_feasible(p["channels"], p["readout_tech"])
    info = P.channel_info_bits(p["channels"])
    score = _clip01(min(p["barcode_bits"] / need, 1.0)) * (1.0 if chan_ok else 0.4)
    return Score(passed=(bits_ok and chan_ok), score=score,
                 metrics={"required_bits": need, "have_bits": p["barcode_bits"],
                          "channel_info_bits": info, "channels_feasible": chan_ok},
                 limiting=("too few barcode bits" if not bits_ok else "channels exceed readout ceiling" if not chan_ok else "demultiplexable"))


# 3 — trans-synaptic pairing at scale + fidelity (full-sim: predicted edge F1)
def _eval_pairing(p) -> Score:
    # analytic edge F1: recall from copies surviving consensus; precision from false-pair suppression
    survive = 1.0 - (1.0 - (1.0 - p["dropout"])) ** 1  # expressed fraction
    recall = (1.0 - p["dropout"]) * (1.0 - 0.5 ** max(p["reads_per_synapse"] - p["min_reads"] + 1, 0))
    false_surviving = p["false_pair_rate"] * (0.5 ** max(p["min_reads"] - 1, 0))
    precision = 1.0 / (1.0 + false_surviving / max(recall, 1e-6))
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return Score(passed=(f1 >= p["target_f1"]), score=_clip01(f1),
                 metrics={"predicted_recall": recall, "predicted_precision": precision, "predicted_f1": f1},
                 limiting=("low recall (dropout/consensus)" if recall < 0.9 else "false pairs" if precision < 0.9 else "meets F1"))


# 4 — ~100% neuron delivery (full-sim: coverage + dose)
def _eval_delivery(p) -> Score:
    blind = B.blind_fraction(p["transduction_fraction"])
    dose_ok = B.aav_dose_ok(p["aav_dose_vg_per_kg"])
    score = (1.0 - blind) * (1.0 if dose_ok else 0.4)
    return Score(passed=(p["transduction_fraction"] >= p["target_coverage"] and dose_ok), score=_clip01(score),
                 metrics={"blind_fraction": blind, "coverage": p["transduction_fraction"], "dose_ok": dose_ok},
                 limiting=("coverage gaps → blind spots" if blind > (1 - p["target_coverage"]) else "AAV dose over ceiling" if not dose_ok else "full coverage"))


# 5 — signal boost + noise cut at depth (full-sim: SNR with averaging)
def _eval_snr(p) -> Score:
    base = P.snr_at_depth(p["snr0"] * p["signal_gain"], DEEP_TARGET_UM, p["penetration_um"])
    eff = base * P.averaging_gain(p["averaging_n"]) / max(p["noise_floor"], 1e-6)
    pdet = P.p_detect(eff)
    return Score(passed=(pdet >= 0.5), score=_clip01(pdet),
                 metrics={"effective_snr": eff, "p_detect": pdet, "averaging_gain": P.averaging_gain(p["averaging_n"])},
                 limiting=("still drowns — need more gain/averaging" if pdet < 0.5 else "reads at depth"))


# 6 — whole-brain scan throughput (full-sim: arithmetic wall)
def _eval_throughput(p) -> Score:
    t = E.scan_time_s(HUMAN_BRAIN_MM3, p["voxel_um"], p["dwell_s"], p["parallel_channels"])
    days = t / 86400.0
    ok = days <= p["target_days"]
    return Score(passed=ok, score=_clip01(p["target_days"] / max(days, 1e-9)),
                 metrics={"scan_days": days, "target_days": p["target_days"]},
                 limiting=("scan too slow" if not ok else "scan fits the time budget"))


# 7 — exabyte-scale assembly + error-correction (estimate)
def _eval_assembly(p) -> Score:
    data_bytes = HUMAN_SYNAPSES * p["reads_per_synapse"] * p["bytes_per_read"]
    exabytes = data_bytes / 1e18
    residual_err = 0.5 ** max(p["min_reads"] - 1, 0)
    ok = exabytes <= p["storage_exabytes"] and residual_err <= p["target_error"]
    score = _clip01((1.0 - residual_err) * min(p["storage_exabytes"] / max(exabytes, 1e-9), 1.0))
    return Score(passed=ok, score=score,
                 metrics={"data_exabytes": exabytes, "residual_error": residual_err},
                 limiting=("data volume exceeds storage" if exabytes > p["storage_exabytes"] else "assembly error too high" if residual_err > p["target_error"] else "assemblable"))


# 8 — whole-brain twin simulation (estimate)
def _eval_twinsim(p) -> Score:
    flops_needed = HUMAN_SYNAPSES * p["flops_per_syn_step"] * p["steps_per_biological_s"]
    rtf = p["hardware_flops"] / max(flops_needed, 1e-9)   # real-time factor
    ok = rtf >= p["target_real_time_factor"]
    return Score(passed=ok, score=_clip01(rtf / max(p["target_real_time_factor"], 1e-9)),
                 metrics={"flops_needed_per_s": flops_needed, "real_time_factor": rtf},
                 limiting=("too slow to run the twin in real time" if not ok else "runs the twin"))


# 9 — behavioural upload-verification (full-sim: proxy behavioural fidelity from map quality)
def _eval_verify(p) -> Score:
    # behaviour saturates with edge recall (a few command neurons dominate) — monotone proxy
    fidelity = 1.0 - (1.0 - p["edge_recall"]) ** (1.0 + p["protocol_sensitivity"])
    discriminative = p["n_stimuli"] >= p["min_stimuli"]
    ok = fidelity >= p["target_fidelity"] and discriminative
    return Score(passed=ok, score=_clip01(fidelity) * (1.0 if discriminative else 0.5),
                 metrics={"predicted_fidelity": fidelity, "discriminative_protocol": discriminative},
                 limiting=("protocol too weak to discriminate" if not discriminative else "fidelity below bar" if fidelity < p["target_fidelity"] else "twin behaves like the original"))


# 10 — human safety of the whole chain (limits-only)
def _eval_safety(p) -> Score:
    margin = B.safety_margin(p["ispta_mw_cm2"], p["mechanical_index"], p["aav_dose_vg_per_kg"])
    ok = B.thermal_dose_ok(p["ispta_mw_cm2"]) and B.mechanical_index_ok(p["mechanical_index"]) and B.aav_dose_ok(p["aav_dose_vg_per_kg"])
    return Score(passed=ok, score=_clip01(margin),
                 metrics={"safety_margin": margin, "within_limits": ok},
                 limiting=("over a safety limit" if not ok else "within all known limits"))


def _make() -> dict:
    L = lambda *t: list(t)
    items = [
        Innovation("in_vivo_readout", "In-vivo, non-destructive barcode readout",
                   L("biomolecules", "hardware"), "life-science", L("physics", "biophysics"),
                   {"read_depth_um": DEEP_TARGET_UM, "non_destructive": True},
                   {"snr0": 12.0, "penetration_um": 80_000.0, "ispta_mw_cm2": 500.0, "mechanical_index": 1.2},
                   _eval_readout, fidelity="physics-only"),
        Innovation("multiplexed_reporters", "Massively-multiplexed reporters",
                   L("biomolecules"), "life-science", L("physics", "electronics"),
                   {"demultiplex_syn_per_voxel": HUMAN_SYN_PER_FUS_VOXEL},
                   {"barcode_bits": 30, "channels": 16, "syn_per_voxel": HUMAN_SYN_PER_FUS_VOXEL, "readout_tech": "acoustic_collapse"},
                   _eval_multiplex),
        Innovation("transsynaptic_pairing", "Trans-synaptic pairing at scale + fidelity",
                   L("biomolecules"), "life-science", L("physics"),
                   {"target_edge_f1": 0.9},
                   {"dropout": 0.2, "false_pair_rate": 0.05, "reads_per_synapse": 6, "min_reads": 2, "target_f1": 0.9},
                   _eval_pairing),
        Innovation("neuron_delivery", "~100% neuron delivery (BBB-crossing)",
                   L("biomolecules"), "cell-therapy", L("biophysics"),
                   {"target_coverage": 0.99},
                   {"transduction_fraction": 0.9, "aav_dose_vg_per_kg": 5e13, "target_coverage": 0.99},
                   _eval_delivery),
        Innovation("snr_depth", "Signal boost + noise cut at depth (SNR)",
                   L("hardware", "biomolecules"), "electronics", L("physics", "biophysics"),
                   {"read_depth_um": DEEP_TARGET_UM},
                   {"snr0": 12.0, "signal_gain": 2.0, "noise_floor": 1.0, "averaging_n": 16, "penetration_um": 80_000.0},
                   _eval_snr),
        Innovation("scan_throughput", "Whole-brain scan throughput",
                   L("hardware"), "hardware", L("electronics"),
                   {"target_scan_days": 30},
                   {"voxel_um": 100.0, "dwell_s": 1e-3, "parallel_channels": 1024, "target_days": 30},
                   _eval_throughput),
        Innovation("exabyte_assembly", "Exabyte-scale assembly + error-correction",
                   L("software", "brain-template"), "software", L("electronics"),
                   {"target_assembly_error": 0.05},
                   {"reads_per_synapse": 6, "bytes_per_read": 4, "min_reads": 3, "storage_exabytes": 10.0, "target_error": 0.05},
                   _eval_assembly, fidelity="estimate"),
        Innovation("twin_sim_scale", "Whole-brain twin simulation",
                   L("software", "virtual-env"), "software", L("electronics"),
                   {"target_real_time_factor": 1.0},
                   {"hardware_flops": 1e18, "flops_per_syn_step": 10.0, "steps_per_biological_s": 1000.0, "target_real_time_factor": 1.0},
                   _eval_twinsim, fidelity="estimate"),
        Innovation("behavioral_verification", "Behavioural upload-verification",
                   L("virtual-env"), "software", L("physics"),
                   {"target_fidelity": 0.9},
                   {"edge_recall": 0.85, "protocol_sensitivity": 1.0, "n_stimuli": 8, "min_stimuli": 5, "target_fidelity": 0.9},
                   _eval_verify),
        Innovation("human_safety", "Human safety of the whole chain",
                   L("biomolecules", "hardware"), "cell-therapy", L("biophysics"),
                   {"within_all_limits": True},
                   {"ispta_mw_cm2": 500.0, "mechanical_index": 1.2, "aav_dose_vg_per_kg": 5e13},
                   _eval_safety, fidelity="limits-only"),
    ]
    return {it.id: it for it in items}


CATALOG: dict[str, Innovation] = _make()


def get(topic_id: str) -> Innovation:
    if topic_id not in CATALOG:
        raise KeyError(f"unknown innovation {topic_id!r}; choose from {list(CATALOG)}")
    return CATALOG[topic_id]


def all_ids() -> list[str]:
    return list(CATALOG)
