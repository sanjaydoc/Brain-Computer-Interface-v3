"""Detailer — expand a candidate design into a full, multi-domain summary + a parts list.

Every invention gets a structured breakdown across biophysics, physics, electronics, and biology,
plus a parts/BOM list, composed deterministically from the topic, the proposed parameters, and the
simulator's metrics. LLM narrative (mechanism/assumptions) augments it when present, but the
domain sections are always populated — so a stored record is complete even with no LLM.
"""

from __future__ import annotations

from .innovations import get, Score

DEEP_UM = 75_000


def _g(m: dict, k: str, d="—"):
    v = m.get(k, d)
    if isinstance(v, float):
        return f"{v:.3g}"
    return v


# Per-topic parts (name + role). Domains: bio-molecular, delivery, hardware, electronics, compute.
PARTS = {
    "in_vivo_readout": [
        ("BBB-crossing AAV vector", "delivers the reporter gene to neurons"),
        ("Genetically-encoded acoustic reporter (gas vesicles)", "the molecular signal source"),
        ("Focused-ultrasound transducer array", "focuses and receives at depth"),
        ("Skull-aberration phase corrector", "restores focus through bone"),
        ("Low-noise receive amplifier + DAQ", "captures the returning signal"),
    ],
    "multiplexed_reporters": [
        ("Barcode reporter library", "one distinguishable variant per neuron"),
        ("Expression cassette + promoter", "drives reporter expression in vivo"),
        ("Channel-resolving readout front-end", "separates reporter signatures in a voxel"),
        ("Demultiplexing compute", "assigns reads to barcode identities"),
    ],
    "transsynaptic_pairing": [
        ("Trans-synaptic barcode-transfer system", "pairs pre and post identities at the synapse"),
        ("Molecular consensus tags", "many reads per true synapse"),
        ("Sequencing / readout chemistry", "recovers the paired barcodes"),
        ("Consensus assembler", "rejects one-off false pairs"),
    ],
    "neuron_delivery": [
        ("Engineered BBB-crossing capsid", "reaches every neuron class"),
        ("Ubiquitous neuronal promoter", "expresses in all neuron types"),
        ("Focused-ultrasound BBB-opening rig", "boosts local delivery at lower dose"),
        ("Dose-titration protocol", "keeps viral load under the safety ceiling"),
    ],
    "snr_depth": [
        ("Signal-amplifying reporter", "brighter source raises SNR"),
        ("Background-subtraction / ratiometric readout", "cuts tissue background"),
        ("Coherent averaging pipeline", "sqrt(N) noise reduction"),
        ("Skull-aberration correction electronics", "recovers depth focus"),
    ],
    "scan_throughput": [
        ("Massively-parallel transducer/detector array", "reads many voxels at once"),
        ("Multi-channel DAQ + FPGA front-end", "streams parallel reads"),
        ("Fast beam/scan controller", "short per-voxel dwell"),
        ("High-throughput data bus + storage", "sinks the read stream"),
    ],
    "exabyte_assembly": [
        ("Distributed graph-assembly cluster", "reconstructs the connectome at scale"),
        ("Consensus + confidence pipeline", "error-corrects noisy reads"),
        ("GNN gap-fill model", "infers missed edges"),
        ("Exabyte object store", "holds reads + graph"),
    ],
    "twin_sim_scale": [
        ("Sparse per-synapse compute kernel", "O(edges) neuron/synapse update"),
        ("Accelerator fleet (GPU/TPU)", "runs 1e14 synapses"),
        ("Partition-native graph loader", "shards the connectome"),
        ("Real-time scheduler", "keeps the twin at real time"),
    ],
    "behavioral_verification": [
        ("Stimulus battery generator", "drives the twin and the original"),
        ("Behavioural divergence metric", "quantifies match"),
        ("Paired twin runner", "runs truth vs recovered identically"),
        ("Pass/fail certifier", "decides upload fidelity"),
    ],
    "human_safety": [
        ("Reversible / switchable reporter", "expression can be turned off"),
        ("Dose + intensity monitor", "enforces ISPTA / MI / AAV limits"),
        ("Immunology screen", "guards against vector response"),
        ("Safety interlock + logging", "hard-stops on limit breach"),
    ],
}


def _sections(topic: str, params: dict, m: dict) -> dict:
    """The four domain paragraphs, filled from params + simulator metrics."""
    if topic == "in_vivo_readout":
        return {
            "biology": "Neurons are made readable by a genetically-encoded acoustic reporter delivered by a BBB-crossing AAV; the reporter must be non-toxic at its expression level.",
            "biophysics": f"Reading must be non-destructive — acoustic dose held under limits (ISPTA {_g(params,'ispta_mw_cm2')} mW/cm², MI {_g(params,'mechanical_index')}); safe: {_g(m,'safe')}.",
            "physics": f"Signal attenuates over ~{DEEP_UM} µm depth: with SNR0 {_g(params,'snr0')} and penetration {_g(params,'penetration_um')} µm the SNR-at-depth is {_g(m,'snr_at_depth')} → p_detect {_g(m,'p_detect')}.",
            "electronics": "A focused-ultrasound transducer array with skull-aberration phase correction focuses and receives the reporter signal deep in tissue.",
        }
    if topic == "multiplexed_reporters":
        return {
            "biology": "A library of distinguishable reporter variants assigns each neuron a unique molecular barcode.",
            "biophysics": "Reporters must express and fold without perturbing neuronal function or firing.",
            "physics": f"Capacity law: {_g(m,'required_bits')} barcode bits are needed to demultiplex ~{_g(params,'syn_per_voxel')} synapses per voxel by identity; the design provides {_g(m,'have_bits')} bits ({_g(m,'channel_info_bits')} channel-info bits).",
            "electronics": f"The {_g(params,'readout_tech')} front-end must resolve {_g(params,'channels')} channels in one voxel — within the technology ceiling: {_g(m,'channels_feasible')}.",
        }
    if topic == "transsynaptic_pairing":
        return {
            "biology": "Barcodes label neurons; a trans-synaptic transfer system links each pre-barcode to its post-partner across the synapse.",
            "biophysics": "Transfer efficiency and reporter stability set how reliably a true synapse is captured.",
            "physics": f"Predicted edge fidelity from the noise model: recall {_g(m,'predicted_recall')}, precision {_g(m,'predicted_precision')}, F1 {_g(m,'predicted_f1')} (dropout {_g(params,'dropout')}, false-pair {_g(params,'false_pair_rate')}).",
            "electronics": f"Readout with consensus depth {_g(params,'reads_per_synapse')} reads/synapse and a ≥{_g(params,'min_reads')}-read acceptance threshold suppresses one-off false pairs.",
        }
    if topic == "neuron_delivery":
        return {
            "biology": "An engineered BBB-crossing capsid with a ubiquitous neuronal promoter aims to transduce every neuron class.",
            "biophysics": f"Coverage {_g(params,'transduction_fraction')} leaves a blind fraction of {_g(m,'blind_fraction')}; focused-ultrasound BBB opening can raise coverage at lower dose.",
            "physics": "Delivery reach is set by capsid tropism and BBB permeability, not by any wave.",
            "electronics": f"A focused-ultrasound BBB-opening rig localises delivery; AAV dose {_g(params,'aav_dose_vg_per_kg')} vg/kg within ceiling: {_g(m,'dose_ok')}.",
        }
    if topic == "snr_depth":
        return {
            "biology": "A signal-amplifying reporter (e.g. enzymatic or bioluminescent cascade) raises the source brightness.",
            "biophysics": "Brighter, more specific reporters cut tissue background and raise SNR without more acoustic dose.",
            "physics": f"With signal gain {_g(params,'signal_gain')}, {_g(params,'averaging_n')} averages (gain {_g(m,'averaging_gain')}) and noise floor {_g(params,'noise_floor')}, effective SNR is {_g(m,'effective_snr')} → p_detect {_g(m,'p_detect')} at depth.",
            "electronics": "Ratiometric / background-subtraction readout plus coherent averaging electronics deliver the noise reduction.",
        }
    if topic == "scan_throughput":
        return {
            "biology": "—",
            "biophysics": "Per-voxel dwell must stay short enough to avoid tissue heating over a whole-brain scan.",
            "physics": f"Total read time follows #voxels × dwell ÷ parallelism; at voxel {_g(params,'voxel_um')} µm, dwell {_g(params,'dwell_s')} s, {_g(params,'parallel_channels')} channels → {_g(m,'scan_days')} days.",
            "electronics": "A massively-parallel transducer/detector array with multi-channel FPGA DAQ reads thousands of voxels at once.",
        }
    if topic == "exabyte_assembly":
        return {
            "biology": "—",
            "biophysics": "—",
            "physics": f"Data volume ≈ synapses × reads × bytes → {_g(m,'data_exabytes')} EB; consensus depth sets residual error {_g(m,'residual_error')}.",
            "electronics": "A distributed graph-assembly cluster with an exabyte object store runs consensus + GNN gap-fill + confidence.",
        }
    if topic == "twin_sim_scale":
        return {
            "biology": "—",
            "biophysics": "Neuron/synapse dynamics reduced to the cheapest faithful update per step.",
            "physics": f"Compute needed ≈ synapses × flops/step × steps → {_g(m,'flops_needed_per_s')} FLOP/s; hardware gives real-time factor {_g(m,'real_time_factor')}.",
            "electronics": "An accelerator fleet with a partition-native graph loader and O(edges) sparse kernels runs the twin.",
        }
    if topic == "behavioral_verification":
        return {
            "biology": "—",
            "biophysics": "—",
            "physics": f"Behavioural fidelity from map quality: {_g(m,'predicted_fidelity')} (edge recall {_g(params,'edge_recall')}); discriminative protocol: {_g(m,'discriminative_protocol')}.",
            "electronics": "A paired twin runner drives truth and recovered connectomes identically; a divergence metric certifies the upload.",
        }
    if topic == "human_safety":
        return {
            "biology": "A reversible / switchable reporter and an immunology screen guard the biological arm.",
            "biophysics": f"All exposure kept inside limits — safety margin {_g(m,'safety_margin')}; within limits: {_g(m,'within_limits')}.",
            "physics": "Acoustic intensity and mechanical index are the physical safety knobs.",
            "electronics": "A dose/intensity monitor with a hard-stop interlock enforces the limits in real time.",
        }
    return {"biology": "—", "biophysics": "—", "physics": "—", "electronics": "—"}


def detail(topic: str, candidate: dict, score: Score | None = None) -> dict:
    """Return {detail: {biology, biophysics, physics, electronics, summary}, parts: [...]}. """
    inv = get(topic)
    params = (candidate or {}).get("params", {})
    s = score if score is not None else inv.evaluate(params)
    m = s.metrics
    sections = _sections(topic, {**inv.param_schema, **params}, m)
    verdict = "physically admissible" if s.passed else "not admissible"
    sections["summary"] = (
        f"{candidate.get('title', inv.title)} — {inv.title.lower()} ({inv.domain}). "
        f"Simulator: {verdict}, score {round(s.score, 3)}, fidelity {s.fidelity}; "
        f"limiting factor: {s.limiting}."
    )
    parts = [{"name": n, "role": r, "domain": inv.domain} for n, r in PARTS.get(topic, [])]
    return {"detail": sections, "parts": parts}
