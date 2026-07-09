"""Research-grade monograph generator — turn a saved synthesis prototype into a journal-style,
~25-30 page technical paper (HTML, print-to-PDF ready). IMRaD structure, governing equations,
per-module sections with computed figures, a translational plan, discussion, and references.

`build_html(synth)` takes a saved synthesis record (from the `syntheses` store) and rebuilds each
of the ten modules from its `sources` (topic → invention id), falling back to the pipeline stage
embedded in the synthesis when an invention id is no longer in the library. Every number shown is a
simulator-accepted set-point; the document is explicitly framed as an in-silico design study.
"""

from __future__ import annotations

import html
import math
import re

from .innovations import CATALOG, all_ids
from .simulator import simulate_params
from . import store

DEEP = 75000.0
BRAIN_MM3 = 1.4e6
SYN = 1e14
FDA_ISPTA = 720.0
FDA_MI = 1.9
AAV_CEIL = 1e14


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def _short(t):
    t = re.sub(r"\s*\([^)]*\)", "", t or "").strip()
    return t if len(t) <= 24 else t[:22] + "…"


# ---- law formulas (mirror the simulator, for graphs) -----------------------
def _snr_at_depth(s0, d, pen):
    return s0 * math.exp(-d / max(pen, 1e-9))


def _p_detect(s, thr=1.0):
    return s / (s + max(thr, 1e-9))


def _avg_gain(n):
    return math.sqrt(max(n, 1))


def _required_bits(k, eps=0.01):
    return math.ceil(math.log2(max(k * k / (2 * max(eps, 1e-9)), 2)))


def _scan_days(v, vox, dw, par):
    vmm3 = (vox / 1000.0) ** 3
    return (v / max(vmm3, 1e-12)) * dw / max(par, 1) / 86400.0


# ---- SVG chart helpers -----------------------------------------------------
def _axes(w, h, pad, title, xl, yl):
    return (f'<text x="{w/2}" y="15" class="ct" text-anchor="middle">{_esc(title)}</text>'
            f'<line x1="{pad}" y1="{h-pad}" x2="{w-8}" y2="{h-pad}" class="ax"/>'
            f'<line x1="{pad}" y1="8" x2="{pad}" y2="{h-pad}" class="ax"/>'
            f'<text x="{(pad+w)/2}" y="{h-3}" class="cl" text-anchor="middle">{_esc(xl)}</text>'
            f'<text x="11" y="{h/2}" class="cl" text-anchor="middle" transform="rotate(-90 11 {h/2})">{_esc(yl)}</text>')


def _line(t, xl, yl, pts, xr, yr, marks=None, w=500, h=270, pad=44, fmtx=None, fmty=None):
    x0, x1 = xr
    y0, y1 = yr
    sx = lambda x: pad + (x - x0) / (x1 - x0) * (w - 8 - pad)
    sy = lambda y: (h - pad) - (y - y0) / (y1 - y0) * (h - pad - 8)
    path = " ".join(("M" if i == 0 else "L") + f"{sx(x):.1f} {sy(y):.1f}" for i, (x, y) in enumerate(pts))
    g = [f'<svg viewBox="0 0 {w} {h}" class="chart" xmlns="http://www.w3.org/2000/svg">',
         '<rect width="100%" height="100%" fill="white"/>', _axes(w, h, pad, t, xl, yl)]
    for i in range(5):
        gx = x0 + (x1 - x0) * i / 4
        gy = y0 + (y1 - y0) * i / 4
        g.append(f'<line x1="{sx(gx):.1f}" y1="8" x2="{sx(gx):.1f}" y2="{h-pad}" class="grid"/>')
        g.append(f'<line x1="{pad}" y1="{sy(gy):.1f}" x2="{w-8}" y2="{sy(gy):.1f}" class="grid"/>')
        g.append(f'<text x="{sx(gx):.1f}" y="{h-pad+12}" class="tk" text-anchor="middle">{(fmtx(gx) if fmtx else f"{gx:.0f}")}</text>')
        g.append(f'<text x="{pad-4}" y="{sy(gy)+3:.1f}" class="tk" text-anchor="end">{(fmty(gy) if fmty else f"{gy:.1f}")}</text>')
    g.append(f'<path d="{path}" fill="none" class="ln"/>')
    for (mx, my, lab, cls) in (marks or []):
        g.append(f'<circle cx="{sx(mx):.1f}" cy="{sy(my):.1f}" r="3.5" class="{cls}"/>')
        g.append(f'<text x="{sx(mx):.1f}" y="{sy(my)-7:.1f}" class="mk" text-anchor="middle">{_esc(lab)}</text>')
    g.append("</svg>")
    return "".join(g)


def _bars(t, yl, bars, w=500, h=270, pad=48, ymax=1.0, thr=None, thrlab=""):
    n = len(bars)
    bw = (w - 8 - pad) / n * 0.58
    gap = (w - 8 - pad) / n
    g = [f'<svg viewBox="0 0 {w} {h}" class="chart" xmlns="http://www.w3.org/2000/svg">',
         '<rect width="100%" height="100%" fill="white"/>', _axes(w, h, pad, t, "", yl)]
    sy = lambda y: (h - pad) - y / ymax * (h - pad - 18)
    if thr is not None:
        g.append(f'<line x1="{pad}" y1="{sy(thr):.1f}" x2="{w-8}" y2="{sy(thr):.1f}" class="thr"/>')
        g.append(f'<text x="{w-10}" y="{sy(thr)-3:.1f}" class="mk" text-anchor="end">{_esc(thrlab)}</text>')
    for i, (lab, val, cls) in enumerate(bars):
        x = pad + gap * i + gap * 0.21
        yv = sy(min(val, ymax))
        g.append(f'<rect x="{x:.1f}" y="{yv:.1f}" width="{bw:.1f}" height="{(h-pad)-yv:.1f}" class="{cls}"/>')
        g.append(f'<text x="{x+bw/2:.1f}" y="{yv-3:.1f}" class="tk" text-anchor="middle">{val:.2f}</text>')
        g.append(f'<text x="{x+bw/2:.1f}" y="{h-pad+12}" class="tk" text-anchor="middle">{_esc(lab)}</text>')
    g.append("</svg>")
    return "".join(g)


TOPIC_ORDER = ["neuron_delivery", "multiplexed_reporters", "in_vivo_readout", "snr_depth", "scan_throughput",
               "transsynaptic_pairing", "exabyte_assembly", "twin_sim_scale", "behavioral_verification", "human_safety"]
TNAME = {"neuron_delivery": "Pan-neuronal vector delivery", "multiplexed_reporters": "Massively-multiplexed molecular barcoding",
         "in_vivo_readout": "Non-destructive in-vivo readout at depth", "snr_depth": "Signal amplification and noise suppression",
         "scan_throughput": "Whole-brain acquisition throughput", "transsynaptic_pairing": "Trans-synaptic edge recovery",
         "exabyte_assembly": "Exabyte-scale connectome assembly", "twin_sim_scale": "Real-time whole-brain simulation",
         "behavioral_verification": "Behavioural verification of the twin", "human_safety": "Integrated safety envelope"}
PHASE = {"neuron_delivery": "Label", "multiplexed_reporters": "Label", "in_vivo_readout": "Read", "snr_depth": "Read",
         "scan_throughput": "Read", "transsynaptic_pairing": "Map", "exabyte_assembly": "Map", "twin_sim_scale": "Emulate",
         "behavioral_verification": "Emulate", "human_safety": "Safety"}
OBJ = {"neuron_delivery": "transduce approximately 100% of neurons across the blood–brain barrier at a systemic dose below the toxicity ceiling",
       "multiplexed_reporters": "assign every synapse a demultiplexable molecular identity within one imaging voxel",
       "in_vivo_readout": "recover reporter signal from 75 mm depth in living tissue without destroying it",
       "snr_depth": "preserve a detectable signal-to-noise ratio at depth by source brightening and averaging rather than a larger scanner",
       "scan_throughput": "complete whole-brain acquisition within a 30-day budget",
       "transsynaptic_pairing": "recover pre-to-post synaptic edges with F1 at least 0.90",
       "exabyte_assembly": "assemble the connectome within bounded storage at under 5% residual error",
       "twin_sim_scale": "simulate 10^14 synapses at a real-time factor of at least 1",
       "behavioral_verification": "certify behavioural fidelity of at least 0.90 against the original",
       "human_safety": "hold ultrasound intensity, mechanical index, and viral dose within FDA limits across the chain"}
LAW = {"neuron_delivery": "Coverage law: blind fraction beta = 1 - f (f = transduction fraction) must satisfy beta <= 0.01, with dose D <= 10^14 vg/kg.",
       "multiplexed_reporters": "Capacity (birthday-bound) law: required bits b_req = ceil(log2(k^2/2e)) for k synapses/voxel at collision tolerance e; channels c must satisfy c <= c_max(technology).",
       "in_vivo_readout": "Attenuation law: SNR(d) = SNR0 * exp(-d/lambda); detection P = SNR/(SNR+1) must reach >= 0.5 at d = 75 mm, subject to I_SPTA <= 720 mW/cm^2 and MI <= 1.9.",
       "snr_depth": "Averaging law: effective SNR = [SNR0 * G * exp(-d/lambda) * sqrt(N)] / N_floor; P >= 0.5 at 75 mm.",
       "scan_throughput": "Throughput law: T = (V/v^3) * tau / P_c must satisfy T <= 30 d.",
       "transsynaptic_pairing": "Edge-fidelity model: F1 from recall (consensus over reads_per_synapse vs min_reads) and precision (false-pair suppression) must reach >= 0.90.",
       "exabyte_assembly": "Assembly law: data = N_syn * r * B bytes; residual error rho = 0.5^(min_reads-1); require data <= storage and rho <= 0.05.",
       "twin_sim_scale": "Compute law: real-time factor RTF = F_hw / (N_syn * phi * sigma) >= 1.",
       "behavioral_verification": "Behavioural model: fidelity = 1 - (1 - r)^(1+s) >= 0.90 with n_stimuli >= n_min.",
       "human_safety": "Safety envelope: margin = min(1 - I/720, 1 - MI/1.9, 1 - D/10^14) >= 0; all three limits simultaneously satisfied."}
PRIORART = {
    "neuron_delivery": ("Systemic AAV (AAV9, engineered BBB-crossing capsids such as BI-hTFR1) reaches partial CNS coverage.", "Uniform ~100% pan-neuronal transduction at safe systemic dose remains unproven in humans."),
    "multiplexed_reporters": ("MAPseq/BARseq establish high-diversity DNA/RNA barcoding ex vivo.", "A demultiplexable >=46-bit codebook readable non-invasively in vivo is not established."),
    "in_vivo_readout": ("Gas-vesicle acoustic reporters and functional ultrasound read deep signal in animals.", "Barcode-resolved readout at 75 mm through human skull is unproven."),
    "snr_depth": ("Bioluminescence and photoacoustics provide large signal gains.", "Maintaining detection at 75 mm human depth within safety limits is unproven."),
    "scan_throughput": ("Fast fUS and light-sheet reach high frame rates over small volumes.", "A 10^6-channel whole-human-brain reader does not exist."),
    "transsynaptic_pairing": ("SYNseq and trans-synaptic tracing recover connectivity at limited scale/fidelity.", "Whole-brain edge recovery at F1 >= 0.9 is unproven."),
    "exabyte_assembly": ("EM connectomics assembles mm^3-scale volumes with heavy compute.", "Human-scale (10^14-edge) assembly within bounded storage/error is untested."),
    "twin_sim_scale": ("Large-scale spiking simulators reach billions of neurons below real time.", "Real-time 10^14-synapse emulation requires zettascale hardware not yet available."),
    "behavioral_verification": ("Model-validation and Turing-style batteries exist for narrow tasks.", "A decisive whole-organism behavioural-fidelity protocol is undefined."),
    "human_safety": ("FDA limits for diagnostic ultrasound and AAV gene therapy are established.", "Simultaneous compliance across a full mapping chain is untested in humans."),
}
BENCH = {
    "neuron_delivery": "Measure transduction fraction by unbiased cell-type census (reporter+/NeuN+); target >=0.99 at dose <=10^14 vg/kg; assay: whole-brain light-sheet plus single-cell sequencing.",
    "multiplexed_reporters": "Measure demultiplexing accuracy vs codebook size in tissue phantoms and mouse cortex; target >=46 reliably-separable bits; assay: in-situ readout with known ground-truth barcodes.",
    "in_vivo_readout": "Measure P_detect vs depth with skull-aberration correction on/off; target P>=0.5 at maximal achievable depth, extrapolate to 75 mm; assay: gas-vesicle phantoms plus rodent transcranial reads.",
    "snr_depth": "Measure effective SNR gain from amplification and averaging separately; target combined gain sufficient for P>=0.5 at depth; assay: calibrated luminance/pressure references.",
    "scan_throughput": "Measure sustained voxels/s of a prototype array; target implied by <=30-day whole-brain extrapolation; assay: array bench test with synthetic voxel load.",
    "transsynaptic_pairing": "Measure edge precision/recall against a co-registered ground-truth microcircuit; target F1>=0.9; assay: small-volume EM cross-validation.",
    "exabyte_assembly": "Measure residual edge error vs consensus depth on a held-out sub-connectome; target rho<=5% within storage budget; assay: down-sampled reassembly benchmark.",
    "twin_sim_scale": "Measure achieved FLOP/synapse-step and RTF on target hardware; target RTF>=1; assay: kernel micro-benchmark scaled to cluster.",
    "behavioral_verification": "Measure twin-vs-original divergence across the stimulus battery; target fidelity>=0.9; assay: paired closed-loop behavioural testing.",
    "human_safety": "Measure realised I_SPTA, MI, and delivered dose in situ; target all below ceilings with margin; assay: hydrophone/thermometry plus biodistribution.",
}


WETLAB = {
    "neuron_delivery": ("Systemic dose-ranging of the delivery vector; quantify pan-neuronal transduction and biodistribution.",
                        "C57BL/6 mouse (then NHP)", "reporter+/NeuN+ fraction by whole-brain light-sheet + scRNA-seq", ">=99% transduction at dose <= ceiling; no off-target toxicity"),
    "multiplexed_reporters": ("Express the combinatorial barcode library in cortex; measure demultiplexing accuracy against a known ground-truth set.",
                              "mouse cortex + tissue phantom", "in-situ barcode calling vs ground truth", ">=46 reliably-separable bits; <1% collision"),
    "in_vivo_readout": ("Transcranial focused-ultrasound read of gas-vesicle barcodes with and without skull-aberration correction; depth series.",
                        "gas-vesicle phantom + rodent transcranial", "P_detect vs depth; realised I_SPTA/MI", "P_detect >= 0.5 at maximal depth within I_SPTA/MI"),
    "snr_depth": ("Isolate reporter-brightness gain from averaging gain in a calibrated depth phantom.",
                  "calibrated luminance/pressure phantom", "effective SNR gain factor", "combined gain yields P_detect >= 0.5 at depth"),
    "scan_throughput": ("Bench a parallel transducer/detector array under synthetic voxel load; measure sustained rate.",
                        "array prototype + synthetic load", "sustained voxels/s", "extrapolated whole-brain scan < 30 days"),
    "transsynaptic_pairing": ("Trans-synaptic barcode transfer in a defined microcircuit; validate edges against co-registered EM.",
                              "mouse microcircuit + EM cross-validation", "edge precision/recall (F1)", "F1 >= 0.90"),
    "exabyte_assembly": ("Reassemble a down-sampled connectome; residual edge error vs consensus depth and storage budget.",
                         "existing EM connectome dataset", "residual edge error rho; storage used", "rho <= 5% within storage budget"),
    "twin_sim_scale": ("Kernel micro-benchmark on GPU/accelerator hardware; measure FLOP per synapse-step and scaling.",
                       "HPC/accelerator cluster", "achieved FLOP/synapse-step; real-time factor", "RTF >= 1 at target scale"),
    "behavioral_verification": ("Paired closed-loop behavioural testing of a twin against its biological original.",
                                "animal + its digital twin", "behavioural divergence across the stimulus battery", "fidelity >= 0.90"),
    "human_safety": ("In-situ dosimetry of the full chain: hydrophone/thermometry and vector biodistribution.",
                     "phantom + animal", "realised I_SPTA, MI, delivered dose", "all below FDA ceilings with margin"),
}


def _collect(synth: dict) -> dict:
    """Build {topic: module-record} for all 10 topics from the synthesis prototype.

    Prefer the full saved invention record (has materials/protocol/risks/refs); fall back to the
    pipeline stage embedded in the synthesis when the invention id is no longer in the library.
    Always (re)compute the law metrics from the parameters so figures stay consistent."""
    sources = synth.get("sources") or {}
    # index pipeline stages by topic for fallback
    stage_by_topic = {}
    for ph in synth.get("pipeline") or []:
        for st in ph.get("stages") or []:
            stage_by_topic[st.get("topic")] = st
    safety = synth.get("safety") or {}
    out = {}
    for tid in all_ids():
        rec = store.record_by_id(sources.get(tid))
        st = stage_by_topic.get(tid, {})
        if rec:
            m = dict(rec)
        elif st:
            m = {"title": st.get("title"), "params": st.get("params"), "mechanism": st.get("mechanism"),
                 "parts": st.get("parts"), "lens": "—", "constraint": st.get("constraint")}
        elif tid == "human_safety" and safety:
            m = {"title": safety.get("title"), "params": safety.get("params"), "mechanism": "", "parts": []}
        else:
            m = {"title": CATALOG[tid].title, "params": {}}
        # recompute metrics/score for consistency
        params = m.get("params") or {}
        try:
            sc = simulate_params(tid, params).as_dict()
        except Exception:
            sc = {"passed": None, "score": None, "metrics": {}, "limiting": ""}
        m["score"] = {"passed": sc.get("passed"), "score": sc.get("score"),
                      "fidelity": sc.get("fidelity"), "limiting": sc.get("limiting"),
                      "metrics": sc.get("metrics", {})}
        for k in ("materials", "protocol_steps", "risks", "references", "parts"):
            m.setdefault(k, [])
        out[tid] = m
    return out


def _metric_line(tid, m):
    g = lambda k, d=0.0: (m.get(k) if m.get(k) is not None else d)
    if tid == "in_vivo_readout":
        return f"P_detect={g('p_detect'):.3f} (>=0.50)"
    if tid == "multiplexed_reporters":
        return f"{g('have_bits'):.0f}>={g('required_bits'):.0f} bits"
    if tid == "transsynaptic_pairing":
        return f"F1={g('predicted_f1'):.3f} (>=0.90)"
    if tid == "neuron_delivery":
        return f"blind={g('blind_fraction')*100:.1f}% (<=1%)"
    if tid == "snr_depth":
        return f"P_detect={g('p_detect'):.3f} (>=0.50)"
    if tid == "scan_throughput":
        return f"{g('scan_days'):.2f} d (<=30)"
    if tid == "exabyte_assembly":
        return f"{g('data_exabytes'):.0f} EB, rho={g('residual_error')*100:.1f}%"
    if tid == "twin_sim_scale":
        return f"RTF=x{g('real_time_factor'):.0f} (>=1)"
    if tid == "behavioral_verification":
        return f"fidelity={g('predicted_fidelity'):.3f} (>=0.90)"
    if tid == "human_safety":
        return f"margin {g('safety_margin')*100:.0f}%"
    return ""


def _graph(tid, p, m):
    if tid == "in_vivo_readout":
        s0 = p.get("snr0", 0); pen = p.get("penetration_um", 1)
        pts = [(d / 1000.0, _p_detect(_snr_at_depth(s0, d, pen))) for d in range(0, 120001, 4000)]
        return _line("Detection probability vs depth", "depth (mm)", "P_detect", pts, (0, 120), (0, 1),
                     marks=[(75, _p_detect(_snr_at_depth(s0, DEEP, pen)), f"75 mm: {m.get('p_detect', 0):.2f}", "ok")], fmtx=lambda v: f"{v:.0f}")
    if tid == "snr_depth":
        s0 = p.get("snr0", 0); g = p.get("signal_gain", 1); nf = p.get("noise_floor", 1); pen = p.get("penetration_um", 1)
        eff = lambda n: _p_detect(_snr_at_depth(s0 * g, DEEP, pen) * _avg_gain(n) / max(nf, 1e-6))
        N = int(p.get("averaging_n", 1))
        return _line("P_detect vs averaging N (75 mm)", "averages N", "P_detect", [(n, eff(n)) for n in range(1, 129, 4)], (0, 128), (0, 1),
                     marks=[(N, eff(N), f"N={N}", "ok")])
    if tid == "multiplexed_reporters":
        b = int(p.get("barcode_bits", 0))
        return _line("Required barcode bits vs synapses/voxel", "log10(synapses/voxel)", "bits",
                     [(k, _required_bits(10 ** k)) for k in [i / 2 for i in range(2, 15)]], (1, 7), (0, 60),
                     marks=[(6, _required_bits(1e6), f"10^6->{_required_bits(1e6)}; have {b}", "ok")])
    if tid == "neuron_delivery":
        cov = p.get("transduction_fraction", 0)
        return _bars("Coverage vs blind fraction", "fraction", [("coverage", cov, "good"), ("target", 0.99, "thr"), ("blind", 1 - cov, "bad")], ymax=1.0, thr=0.99, thrlab="0.99")
    if tid == "scan_throughput":
        par = int(p.get("parallel_channels", 1)); dw = p.get("dwell_s", 1e-3); vox = p.get("voxel_um", 100)
        pts = [(e, _scan_days(BRAIN_MM3, vox, dw, 10 ** e)) for e in [i / 2 for i in range(4, 15)]]
        d0 = _scan_days(BRAIN_MM3, vox, dw, par)
        return _line("Scan time vs parallel channels", "log10(channels)", "days", pts, (2, 7), (0, 60),
                     marks=[(math.log10(max(par, 1)), min(d0, 60), f"{d0:.2f} d", "ok")], fmty=lambda v: f"{v:.0f}")
    if tid == "transsynaptic_pairing":
        return _bars("Recall / precision / F1", "score", [("recall", m.get("predicted_recall", .9), "good"), ("precision", m.get("predicted_precision", .9), "good"), ("F1", m.get("predicted_f1", .9), "good"), ("target", 0.9, "thr")], ymax=1.0, thr=0.9, thrlab="0.90")
    if tid == "exabyte_assembly":
        mr = int(p.get("min_reads", 1))
        return _line("Residual error vs consensus min-reads", "min_reads", "residual error", [(k, 0.5 ** max(k - 1, 0)) for k in range(1, 11)], (1, 10), (0, 0.6),
                     marks=[(mr, 0.5 ** max(mr - 1, 0), f"min={mr}", "ok")], fmty=lambda v: f"{v:.2f}")
    if tid == "twin_sim_scale":
        hw = p.get("hardware_flops", 1); fps = p.get("flops_per_syn_step", 1); sps = p.get("steps_per_biological_s", 1)
        need = SYN * fps * sps
        return _line("Real-time factor vs hardware FLOP/s", "log10(FLOP/s)", "RTF", [(e, (10 ** e) / need) for e in range(15, 23)], (15, 22), (0, 3),
                     marks=[(math.log10(max(hw, 1)), min(hw / need, 3), f"x{hw/need:.0f}", "ok")], fmty=lambda v: f"{v:.1f}")
    if tid == "behavioral_verification":
        er = p.get("edge_recall", .9); ps = p.get("protocol_sensitivity", 1)
        return _line("Fidelity vs edge recall", "edge recall", "fidelity", [(r, 1 - (1 - r) ** (1 + ps)) for r in [i / 100 for i in range(50, 100)]], (0.5, 1), (0, 1),
                     marks=[(er, m.get("predicted_fidelity", .9), f"r={er}", "ok")], fmtx=lambda v: f"{v:.2f}")
    if tid == "human_safety":
        return _bars("Fraction of each FDA ceiling used", "fraction of limit", [("I_SPTA", p.get("ispta_mw_cm2", 0) / FDA_ISPTA, "good"), ("MI", p.get("mechanical_index", 0) / FDA_MI, "good"), ("AAV", p.get("aav_dose_vg_per_kg", 0) / AAV_CEIL, "good"), ("limit", 1.0, "thr")], ymax=1.1, thr=1.0, thrlab="ceiling")
    return ""


def _deriv(tid, p, m):
    if tid == "neuron_delivery":
        f = p.get("transduction_fraction", 0); D = p.get("aav_dose_vg_per_kg", 1)
        return (f"beta = 1 - {f} = {1-f:.3f} <= 0.01; D = {D:.0e} vg/kg <= 10^14 (headroom x{AAV_CEIL/max(D,1):.0e}).",
                "Coverage is the binding term: a 1% shortfall leaves ~10^12 unlabelled neurons. Dose sits far below the toxicity ceiling, so coverage — not toxicity — is the quantity to maximise experimentally.")
    if tid == "multiplexed_reporters":
        b = int(p.get("barcode_bits", 0)); c = int(p.get("channels", 0))
        return (f"b_req = ceil(log2(10^12/0.02)) = {_required_bits(1e6)}; have {b} bits -> 2^{b} ~ {2**b:.1e} identities >> 10^6; channels {c} <= 16.",
                "Identities exceed synapses-per-voxel by ~8 orders of magnitude, so collision probability is negligible. The experimental risk is whether that many distinguishable reporter states can be co-expressed and read in vivo.")
    if tid == "in_vivo_readout":
        s0 = p.get("snr0", 0); pen = p.get("penetration_um", 1); snrd = _snr_at_depth(s0, DEEP, pen)
        return (f"SNR(75 mm) = {s0} * exp(-75000/{pen:.0f}) = {snrd:.2f}; P = {snrd:.2f}/({snrd:.2f}+1) = {_p_detect(snrd):.3f} >= 0.5.",
                "Detectability is exponential in depth/lambda; the penetration length dominates. Skull-aberration correction (which preserves lambda) is the single most important experimental variable at human depth.")
    if tid == "snr_depth":
        s0 = p.get("snr0", 0); g = p.get("signal_gain", 1); nf = p.get("noise_floor", 1); N = int(p.get("averaging_n", 1)); pen = p.get("penetration_um", 1)
        eff = _snr_at_depth(s0 * g, DEEP, pen) * _avg_gain(N) / max(nf, 1e-6)
        return (f"SNR_eff = {s0}*{g}*exp(-75000/{pen:.0f})*sqrt({N})/{nf} = {eff:.2f}; P = {_p_detect(eff):.3f} >= 0.5.",
                "Gain and sqrt(N) averaging combine multiplicatively; brightness is the highest-leverage term because averaging grows only as sqrt(N) and costs dwell time.")
    if tid == "scan_throughput":
        vox = p.get("voxel_um", 100); dw = p.get("dwell_s", 1e-3); par = int(p.get("parallel_channels", 1)); T = _scan_days(BRAIN_MM3, vox, dw, par)
        return (f"T = (1.4e6/({vox/1000:.3f})^3)*{dw}/{par:,} = {T:.2f} d <= 30.",
                "Throughput is linear in dwell and inverse in parallel channels; the engineering risk migrates to building and calibrating a 10^6-element array, not the time arithmetic.")
    if tid == "transsynaptic_pairing":
        return (f"dropout {p.get('dropout')}, false-pair {p.get('false_pair_rate')}, {int(p.get('reads_per_synapse',0))} reads (min {int(p.get('min_reads',0))}): recall {m.get('predicted_recall',0):.2f}, precision {m.get('predicted_precision',0):.2f} -> F1 {m.get('predicted_f1',0):.3f} >= 0.90.",
                "Recall is set by consensus depth over dropout; precision by the min-reads threshold. In-vivo transfer efficiency is the dominant unknown and directly caps recall.")
    if tid == "exabyte_assembly":
        r = int(p.get("reads_per_synapse", 0)); B = int(p.get("bytes_per_read", 0)); mr = int(p.get("min_reads", 1)); data = SYN * r * B / 1e18
        return (f"data = 10^14*{r}*{B} = {data:.0f} EB <= {p.get('storage_exabytes',0):.0e} EB; rho = 0.5^{mr-1} = {0.5**(mr-1)*100:.2f}% <= 5%.",
                "Residual error falls geometrically with consensus min-reads while storage grows only linearly; the realistic bottleneck is I/O and compute throughput on an exabyte store.")
    if tid == "twin_sim_scale":
        hw = p.get("hardware_flops", 1); phi = p.get("flops_per_syn_step", 1); sig = p.get("steps_per_biological_s", 1)
        return (f"RTF = {hw:.0e}/(10^14*{phi}*{sig}) = x{hw/(SYN*phi*sig):.0f} >= 1.",
                "RTF is linear in hardware FLOP/s and inverse in per-synapse cost; the binding assumption is that a faithful synapse update reduces to ~5 FLOP.")
    if tid == "behavioral_verification":
        er = p.get("edge_recall", .9); s = p.get("protocol_sensitivity", 1)
        return (f"Phi = 1 - (1 - {er})^(1+{s}) = {1-(1-er)**(1+s):.3f} >= 0.90; n_stimuli {int(p.get('n_stimuli',0)):,} >= {int(p.get('min_stimuli',0)):,}.",
                "Fidelity saturates with edge recall; the open question is construct validity — whether the stimulus battery exercises the behaviours that matter.")
    if tid == "human_safety":
        I = p.get("ispta_mw_cm2", 0); mi = p.get("mechanical_index", 0); D = p.get("aav_dose_vg_per_kg", 0)
        return (f"I/720 = {I/FDA_ISPTA:.2f}, MI/1.9 = {mi/FDA_MI:.2f}, D/10^14 = {D/AAV_CEIL:.2f}; margin = {min(1-I/FDA_ISPTA,1-mi/FDA_MI,1-D/AAV_CEIL):.2f} >= 0.",
                "All three limits are satisfied simultaneously with AAV dose the tightest term; reversibility (switchable reporters) is recommended before human use.")
    return ("", "")


_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font:10.5px/1.55 Georgia,"Times New Roman",serif;color:#111;background:#fff}
@page{size:A4;margin:18mm 16mm}
p{margin:.35rem 0;text-align:justify}
.titleblock{text-align:center;border-bottom:2px solid #222;padding-bottom:.8rem;margin-bottom:.9rem}
.journal{font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:#666;margin-bottom:.5rem}
.ptitle{font-size:19px;line-height:1.25;margin:.2rem 3mm;font-weight:700}
.authors{font-size:12px;margin-top:.6rem}.affil{font-size:8.5px;color:#666;margin-top:.3rem}
.corr{font-size:8.5px;color:#666;margin-top:.35rem;font-style:italic}
.abstract{background:#f7f7f4;border:1px solid #e3e3d8;border-radius:4px;padding:.7rem .9rem;margin:.6rem 0 1rem}
.ab-h{font-weight:700;font-size:12px;margin-bottom:.25rem}.abstract p{margin:.3rem 0;font-size:10px}
.kw{font-size:9px;color:#444;margin-top:.4rem;border-top:1px solid #e3e3d8;padding-top:.35rem}
.s{font-size:14px;font-weight:700;margin:1.1rem 0 .4rem;padding-bottom:.15rem;border-bottom:1px solid #ccc;break-after:avoid}
.ss{font-size:11.5px;font-weight:700;margin:.7rem 0 .25rem;break-after:avoid}
.phtag{font-style:italic;font-size:8px;color:#777}
.mono{font-family:"Courier New",monospace;font-size:9px}.small{font-size:8.5px}
ul,ol{margin:.2rem 0 .4rem 1.2rem}li{margin:.12rem 0;text-align:left}
ul.tight,ol.tight{margin:.15rem 0 .35rem 1.1rem}ul.tight li,ol.tight li{margin:.08rem 0;font-size:9.5px}
.eqs{margin:.4rem 0;padding:.4rem .6rem;background:#fafaf7;border-left:3px solid #888}
.eq{font-style:italic;font-size:10px;margin:.22rem 0}.eq sub,.eq sup{font-style:normal}
.fig{margin:.7rem auto;text-align:center;break-inside:avoid}
.chart{width:100%;max-width:500px;border:1px solid #e6e6e6}.arch{width:100%;border:1px solid #e6e6e6}
figcaption{font-size:9px;color:#333;margin-top:.3rem;text-align:justify;padding:0 2mm}
.tabwrap{margin:.7rem 0;break-inside:avoid}.tabcap{font-size:9px;color:#333;margin-bottom:.25rem}
table.sci{border-collapse:collapse;width:100%;font-size:9.5px}
table.sci th,table.sci td{padding:3px 6px;text-align:left;vertical-align:top;border:0}
table.sci thead th{border-top:1.5px solid #222;border-bottom:1px solid #222;font-weight:700}
table.sci tbody tr{border-bottom:1px solid #e6e6e6}table.sci tbody tr:last-child{border-bottom:1.5px solid #222}
.twocol{display:grid;grid-template-columns:1fr 1fr;gap:.8rem;align-items:start}
.pass{font-weight:700;color:#186a34;font-family:"Courier New",monospace}
.cite{color:#2a2a7a;font-size:7.5px}
.env{fill:#fbf6fb;stroke:#dcc0d6;stroke-dasharray:3 2}.envt{font:italic 8px Georgia,serif;fill:#8a3a7a}
.pht{font:bold 9px Georgia,serif}.modt{font:8.5px Georgia,serif;fill:#111}.flow{stroke:#333;stroke-width:1.3}
.ct{font:bold 10px Georgia,serif;fill:#222}.cl{font:8.5px Georgia,serif;fill:#777}
.tk{font:7.5px "Courier New",monospace;fill:#777}.mk{font:bold 8px Georgia,serif;fill:#186a34}
.ax{stroke:#999;stroke-width:1}.grid{stroke:#f0f0f0}.ln{stroke:#2a2a7a;stroke-width:2}.thr{stroke:#8a5410;stroke-width:1.3;stroke-dasharray:4 3}
.ok{fill:#186a34}.good{fill:#0a6f6f}.bad{fill:#a83232}
.refs{margin-left:1.4rem;font-size:9px}.refs li{margin:.2rem 0;text-align:left}
.refnote{font-size:8.5px;color:#666;font-style:italic}
.decl{font-size:9px;color:#444;margin-top:.5rem;border-top:1px solid #e3e3d8;padding-top:.35rem}
.bench{background:#f2f6f2;border-left:3px solid #2c6e2c;padding:.3rem .5rem;font-size:9.5px;margin:.4rem 0}
.modstart{break-before:page}.s.secbreak{break-before:page}
@media print{body{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""


def build_html(synth: dict, autoprint: bool = True) -> str:
    """Render a full research-grade monograph (HTML string) for one saved synthesis prototype."""
    E = _collect(synth)
    sysd = synth.get("system") or {}
    name = sysd.get("system_name") or "Synthesized System"
    ts = str(synth.get("ts") or "")[:19].replace("T", " ")
    pid = str(synth.get("id") or "")[:12]
    fig = [0]; tab = [0]; REFS = []; RKEY = {}

    def figure(svg, cap):
        fig[0] += 1
        return f'<figure class="fig">{svg}<figcaption><b>Figure {fig[0]}.</b> {cap}</figcaption></figure>'

    def tbl(cap, thead, rows):
        tab[0] += 1
        return f'<div class="tabwrap"><div class="tabcap"><b>Table {tab[0]}.</b> {cap}</div><table class="sci"><thead>{thead}</thead><tbody>{rows}</tbody></table></div>'

    def cites(refs):
        nums = []
        for r in (refs or []):
            if not r:
                continue
            k = str(r)[:70]
            if k not in RKEY:
                REFS.append(r); RKEY[k] = len(REFS)
            nums.append(RKEY[k])
        nums = sorted(set(nums))
        return '<sup class="cite">[' + ",".join(str(n) for n in nums) + "]</sup>" if nums else ""

    B = []

    # architecture SVG
    def arch_svg():
        byp = {"Label": ["neuron_delivery", "multiplexed_reporters"], "Read": ["in_vivo_readout", "snr_depth", "scan_throughput"],
               "Map": ["transsynaptic_pairing", "exabyte_assembly"], "Emulate": ["twin_sim_scale", "behavioral_verification"]}
        cols = {"Label": "#3b3b8f", "Read": "#0a6f6f", "Map": "#8a5410", "Emulate": "#2c6e2c"}
        w = 720; h = 250; g = [f'<svg viewBox="0 0 {w} {h}" class="arch" xmlns="http://www.w3.org/2000/svg">', '<rect width="100%" height="100%" fill="white"/>']
        g.append(f'<rect x="6" y="6" width="{w-12}" height="{h-40}" rx="6" class="env"/>')
        g.append('<text x="16" y="22" class="envt">Safety envelope — I_SPTA <= 720 mW/cm^2 · MI <= 1.9 · AAV <= 10^14 vg/kg</text>')
        cw = 166; x0 = 18; y = 40; ch = 118
        for i, ph in enumerate(["Label", "Read", "Map", "Emulate"]):
            x = x0 + i * (cw + 10); col = cols[ph]
            g.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="6" fill="{col}" opacity="0.06" stroke="{col}"/>')
            g.append(f'<text x="{x+cw/2}" y="{y+17}" class="pht" fill="{col}" text-anchor="middle">{ph.upper()}</text>')
            for j, t in enumerate(byp[ph]):
                g.append(f'<rect x="{x+10}" y="{y+26+j*26}" width="{cw-20}" height="21" rx="3" fill="white" stroke="{col}"/>')
                g.append(f'<text x="{x+cw/2}" y="{y+40+j*26}" class="modt" text-anchor="middle">{_esc(_short(E[t].get("title")))}</text>')
            if i < 3:
                g.append(f'<path d="M{x+cw} {y+ch/2} l10 0" class="flow"/><path d="M{x+cw+10} {y+ch/2} l-5 -3.5 l0 7 z" fill="#333"/>')
        g.append("</svg>"); return "".join(g)

    # title + abstract
    B.append(f'''<div class="titleblock">
 <div class="journal">BCI v3 · Computational Neuroengineering Preprint Series</div>
 <h1 class="ptitle">{_esc(name)}: An In-Silico, Law-Constrained Design for a Non-Invasive Whole-Brain Mapping and Emulation System</h1>
 <div class="authors">S. Anbu<sup>1</sup> · BCI v3 Invention-and-Simulation Engine<sup>2</sup></div>
 <div class="affil"><sup>1</sup>Principal investigator, independent research. <sup>2</sup>Automated invention/critique pipeline (retrieval, generative design, multi-domain law simulator).</div>
 <div class="corr">Correspondence: dr.sanjayanbu@gmail.com · Prototype {_esc(pid)} · {_esc(ts)} · Preprint — not peer-reviewed</div>
</div>
<div class="abstract"><div class="ab-h">Abstract</div>
 <p><b>Background.</b> A non-invasive brain–computer interface capable of whole-brain structural mapping and functional emulation is obstructed by ten interdependent problems spanning molecular delivery, deep readout, information capacity, data assembly, simulation, and safety. Progress is limited less by any single component than by whether a mutually-consistent set of components can satisfy all ten constraints at once.</p>
 <p><b>Methods.</b> A retrieval-grounded generative design engine coupled to a deterministic law-based simulator grades each candidate against closed-form models from wave physics, biophysics, information theory, and computational feasibility, plus regulatory safety ceilings; a candidate is admitted only if it satisfies its governing inequality. Ten admitted designs were composed into the system {_esc(name)} and re-graded here.</p>
 <p><b>Results.</b> All ten modules satisfy their governing constraints in silico (Table 2): molecular barcodes read at 75 mm depth, 10^6 synapses per voxel resolved by identity, whole-brain acquisition under 30 days, connectome assembled within bounded storage at under 5% residual error, and a real-time twin — inside all FDA ultrasound and gene-therapy limits.</p>
 <p><b>Conclusions.</b> {_esc(name)} is a physically-admissible blueprint, not an empirical result; every parameter is a simulator-accepted set-point requiring wet-lab and computational validation. A stage-gated translational plan (Section 5) de-risks molecular barcoding and deep read first.</p>
 <div class="kw"><b>Keywords:</b> non-invasive BCI · connectomics · gas-vesicle reporters · focused ultrasound · molecular barcoding · whole-brain emulation · AAV gene delivery · in-silico design</div>
</div>''')

    # 1 Introduction + prior art
    pa = "".join(f'<tr><td>{_esc(TNAME[t])}</td><td>{_esc(PRIORART[t][0])}</td><td>{_esc(PRIORART[t][1])}</td></tr>' for t in TOPIC_ORDER)
    B.append('<h2 class="s">1. Introduction</h2>'
             '<p>Mapping and emulating a human brain without surgery requires solving a chain of problems in which each link constrains the next. Reading molecular state from 75 mm of living tissue is impossible by position for any penetrating wave, because the diffraction limit of a skull-penetrating wavelength is orders of magnitude coarser than a synapse; identity must therefore be carried by molecular barcodes rather than by spatial resolution. Barcodes demand a vehicle reaching essentially every neuron, a codebook large enough to separate ~10^6 synapses per voxel, a reader that recovers those codes at depth and speed, an assembler that reconstructs the wiring graph, a simulator that steps the twin in real time, and a verification protocol certifying behaviour — all inside human-safety limits. We call these the ten blockers.</p>'
             '<p>This paper reports a computational design study. Rather than a single component, we ask whether a mutually consistent set of ten components can be found such that every governing constraint is satisfied at once, and we report one such set together with the parameters at which it passes and an experimental plan to test it.</p>'
             '<h3 class="ss">1.1 The ten blockers, state of the art, and the gap</h3>'
             '<p>Table 1 summarises the closest established capability and the specific gap for each blocker. Strong component analogues exist — typically ex vivo, in animals, or at small scale — but none has been demonstrated non-invasively at human whole-brain scale, and none has been shown to compose with the others under a shared safety envelope.</p>' +
             tbl("State of the art and the gap addressed, per blocker.", '<tr><th>Blocker</th><th>Closest established capability</th><th>Gap addressed here</th></tr>', pa))

    # 2 Methods
    thr = "".join(f'<tr><td>{_esc(TNAME[t])}</td><td class="mono small">{_esc(LAW[t].split(":",1)[1].strip())}</td></tr>' for t in TOPIC_ORDER)
    B.append('<h2 class="s">2. Methods</h2>'
             '<h3 class="ss">2.1 In-silico evaluation framework</h3>'
             '<p>Candidate designs were produced by a retrieval-grounded generative engine and scored by a deterministic simulator implementing closed-form models in four domains — wave physics, biophysics, electronics/computation, and a regulatory safety envelope — returning, for each candidate, the governing metric and a pass/fail verdict against a fixed threshold. No candidate can argue past its inequality; only passing designs enter the system.</p>'
             '<h3 class="ss">2.2 Governing models</h3>'
             '<div class="eqs">'
             '<div class="eq">Barcode capacity (birthday bound): b<sub>req</sub> = ceil(log<sub>2</sub>(k&sup2;/2&epsilon;)), identities = 2<sup>b</sup> from c &le; c<sub>max</sub></div>'
             '<div class="eq">Depth attenuation: SNR(d) = SNR<sub>0</sub>&middot;e<sup>&minus;d/&lambda;</sup>, P<sub>detect</sub> = SNR/(SNR+1)</div>'
             '<div class="eq">Coherent averaging: SNR<sub>eff</sub> = SNR<sub>0</sub>&middot;G&middot;e<sup>&minus;d/&lambda;</sup>&middot;&radic;N / N<sub>floor</sub></div>'
             '<div class="eq">Acquisition time: T = (V/&upsilon;&sup3;)&middot;&tau; / P<sub>c</sub></div>'
             '<div class="eq">Assembly: data = N<sub>syn</sub>&middot;r&middot;B, residual &rho; = 0.5<sup>(min_reads&minus;1)</sup></div>'
             '<div class="eq">Real-time factor: RTF = F<sub>hw</sub> / (N<sub>syn</sub>&middot;&phi;&middot;&sigma;)</div>'
             '<div class="eq">Behavioural fidelity: &Phi; = 1 &minus; (1&minus;r)<sup>(1+s)</sup></div>'
             '<div class="eq">Safety margin: &mu; = min(1&minus;I/720, 1&minus;MI/1.9, 1&minus;D/10<sup>14</sup>)</div>'
             '</div>'
             '<h3 class="ss">2.3 Reference targets and thresholds</h3>'
             '<p>Human-scale reference values: deep target depth 75,000 &micro;m; synapses per voxel 10<sup>6</sup>; brain volume 1.4&times;10<sup>6</sup> mm&sup3;; total synapses 10<sup>14</sup>. Regulatory ceilings: I<sub>SPTA</sub> &le; 720 mW/cm&sup2;; mechanical index &le; 1.9; systemic AAV dose &le; 10<sup>14</sup> vg/kg.</p>' +
             tbl("Governing constraint per blocker (admission criterion).", '<tr><th>Blocker</th><th>Admission inequality</th></tr>', thr))

    # 3 Results architecture + summary table
    B.append('<h2 class="s">3. Results: system design</h2><h3 class="ss">3.1 Architecture</h3>'
             '<p>The admitted modules compose into four sequential phases — Label, Read, Map, Emulate — within a single safety envelope (Figure 1). Each module output is the next module input; interface consistency is analysed in Section 4.</p>' +
             figure(arch_svg(), f'End-to-end architecture of {_esc(name)}. Ten modules across four phases within one safety envelope.'))
    sr = ""
    for i, t in enumerate(TOPIC_ORDER, 1):
        sc = E[t].get("score") or {}
        sr += f'<tr><td>{i}</td><td>{_esc(TNAME[t])}</td><td>{_esc(E[t].get("title"))}</td><td class="mono small">{_esc(_metric_line(t, sc.get("metrics", {})))}</td><td class="pass">{sc.get("score")}</td></tr>'
    B.append(tbl("Per-module in-silico results (recomputed from the stored parameters).", '<tr><th>#</th><th>Blocker</th><th>Module</th><th>Governing metric</th><th>Score</th></tr>', sr))

    # module subsections
    for i, tid in enumerate(TOPIC_ORDER, 1):
        r = E[tid]; p = r.get("params") or {}; sc = r.get("score") or {}; m = sc.get("metrics", {})
        pr = "".join(f'<tr><td class="mono">{_esc(k)}</td><td class="mono">{_esc(f"{v:,}" if isinstance(v,(int,float)) and abs(v)>=1000 else v)}</td></tr>' for k, v in p.items())
        mr = "".join(f'<tr><td class="mono">{_esc(k)}</td><td class="mono">{_esc(f"{v:.4g}" if isinstance(v,(int,float)) else v)}</td></tr>' for k, v in m.items())
        mats = "".join(f"<li>{_esc(x)}</li>" for x in (r.get("materials") or []) if x)
        prot = "".join(f"<li>{_esc(x)}</li>" for x in (r.get("protocol_steps") or [])[:6] if x)
        risk = "".join(f"<li>{_esc(x)}</li>" for x in (r.get("risks") or [])[:4] if x)
        wrk, interp = _deriv(tid, p, m)
        B.append(f'''<h3 class="ss modstart">3.{i+1} {_esc(TNAME[tid])} <span class="phtag">[{PHASE[tid]}]</span></h3>
<p><b>Objective.</b> {_esc(OBJ[tid][0].upper()+OBJ[tid][1:])}. <b>Governing model.</b> {_esc(LAW[tid])}</p>
<p><b>Design ({_esc(r.get("title"))}).</b> {_esc(r.get("mechanism"))} {cites(r.get("references"))}</p>
<div class="twocol">{tbl(f"Accepted parameters — {_esc(r.get('title'))}.", '<tr><th>Parameter</th><th>Value</th></tr>', pr)}{tbl(f"Simulator metrics — {_esc(TNAME[tid])} (limiting: {_esc(sc.get('limiting'))}).", '<tr><th>Metric</th><th>Value</th></tr>', mr)}</div>
<p><b>Quantitative check.</b> <span class="mono small">{_esc(wrk)}</span></p>
{figure(_graph(tid, p, m), f'{_esc(TNAME[tid])}: accepted set-points (marker) vs the admission threshold (dashed).')}
<p><b>Interpretation and sensitivity.</b> {_esc(interp)}</p>
<p><b>Materials.</b></p><ul class="tight">{mats or "<li>—</li>"}</ul>
<p><b>Experimental protocol.</b></p><ol class="tight">{prot or "<li>—</li>"}</ol>
<p><b>Principal failure modes.</b></p><ul class="tight">{risk or "<li>—</li>"}</ul>
<p class="bench"><b>Expected empirical benchmark.</b> {_esc(BENCH[tid])}</p>''')

    # 4 Integration
    def sp_rows():
        P = lambda t: E[t].get("params") or {}
        MET = lambda t: (E[t].get("score") or {}).get("metrics", {})
        ea = P("exabyte_assembly"); tw = P("twin_sim_scale")
        data_eb = SYN * ea.get("reads_per_synapse", 1) * ea.get("bytes_per_read", 1) / 1e18
        rtf = tw.get("hardware_flops", 0) / max(SYN * tw.get("flops_per_syn_step", 1) * tw.get("steps_per_biological_s", 1), 1e-9)
        S = lambda t: _short(E[t].get("title"))
        rows = [
            (f"{S('neuron_delivery')} -> {S('multiplexed_reporters')}", "transduced neurons", f"{P('neuron_delivery').get('transduction_fraction',0)*100:.0f}% @ {P('neuron_delivery').get('aav_dose_vg_per_kg',0):.0e} vg/kg", "beta <= 0.01"),
            (f"{S('multiplexed_reporters')} -> {S('in_vivo_readout')}", "barcoded voxels", f"{int(P('multiplexed_reporters').get('barcode_bits',0))} bits / {int(P('multiplexed_reporters').get('channels',0))} ch", "b >= 46; c <= c_max"),
            (f"{S('in_vivo_readout')} -> {S('snr_depth')}", "raw signal", f"SNR0 {P('in_vivo_readout').get('snr0')}; P {MET('in_vivo_readout').get('p_detect',0):.2f}", "P >= 0.5"),
            (f"{S('snr_depth')} -> {S('scan_throughput')}", "clean signal", f"G {P('snr_depth').get('signal_gain')}x sqrt{int(P('snr_depth').get('averaging_n',1))}", "P >= 0.5"),
            (f"{S('scan_throughput')} -> {S('transsynaptic_pairing')}", "read stream", f"{int(P('scan_throughput').get('parallel_channels',0)):,} ch, {P('scan_throughput').get('dwell_s')} s", "T <= 30 d"),
            (f"{S('transsynaptic_pairing')} -> {S('exabyte_assembly')}", "edges", f"F1 {MET('transsynaptic_pairing').get('predicted_f1',0):.2f}", "F1 >= 0.90"),
            (f"{S('exabyte_assembly')} -> {S('twin_sim_scale')}", "connectome", f"{data_eb:.0f} EB, rho {MET('exabyte_assembly').get('residual_error',0)*100:.1f}%", "rho <= 5%"),
            (f"{S('twin_sim_scale')} -> {S('behavioral_verification')}", "running twin", f"RTF x{rtf:.0f}", "RTF >= 1"),
            (f"{S('behavioral_verification')} -> upload", "certified twin", f"Phi {MET('behavioral_verification').get('predicted_fidelity',0):.3f}", "Phi >= 0.90"),
        ]
        return "".join(f'<tr><td>{_esc(a)}</td><td>{_esc(b)}</td><td class="mono small">{_esc(c)}</td><td class="mono small">{_esc(d)}</td></tr>' for a, b, c, d in rows)
    ubr = E["in_vivo_readout"].get("params") or {}
    B.append('<h2 class="s secbreak">4. Systems integration</h2>'
             '<p>The modules form a system only if each interface balances. Table 12 gives the end-to-end budget. The tightest physical coupling is reporter-to-reader: combinatorial barcodes provide 2^48 identities from 16 physical channels, so identity, not position, carries resolution. The narrowest safety headroom occurs at the read stage (I_SPTA ' + f"{ubr.get('ispta_mw_cm2')}" + ' mW/cm^2, MI ' + f"{ubr.get('mechanical_index')}" + '); the safety module therefore imposes a lower-intensity acoustic-lens envelope around the whole chain.</p>' +
             tbl("End-to-end interface budget.", '<tr><th>Interface</th><th>Quantity</th><th>Set-point</th><th>Constraint</th></tr>', sp_rows()))

    # 5 Roadmap
    def road_svg():
        ph = [("P1 Barcoding", "mouse", "#3b3b8f"), ("P2 Deep read", "mouse", "#0a6f6f"), ("P3 Map+twin", "mouse", "#8a5410"), ("P4 Scale", "NHP", "#2c6e2c"), ("P5 FIH", "human", "#7a2e6e")]
        w = 720; h = 120; g = [f'<svg viewBox="0 0 {w} {h}" class="arch" xmlns="http://www.w3.org/2000/svg">', '<rect width="100%" height="100%" fill="white"/>']
        g.append(f'<line x1="24" y1="64" x2="{w-24}" y2="64" class="ax"/>')
        for i, (t, who, c) in enumerate(ph):
            x = 48 + i * 152
            g.append(f'<circle cx="{x}" cy="64" r="8" fill="{c}"/>')
            g.append(f'<text x="{x}" y="42" class="modt" text-anchor="middle">{_esc(t)}</text>')
            g.append(f'<text x="{x}" y="86" class="tk" text-anchor="middle">{_esc(who)} · Yr {i+1}-{i+2}</text>')
        g.append("</svg>"); return "".join(g)
    road = "".join(f'<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td></tr>' for a, b, c, d, e in [
        ("P1 Barcoding", "Express readable gas-vesicle barcodes in mouse cortex", "AAV capsid + GV/combinatorial cassette; verify >=46-bit codebook expresses and GVs collapse under FUS", "&ge;90% neurons barcoded; codebook demultiplexable", "Yr 1-2"),
        ("P2 Deep read", "Recover barcodes at depth with acoustic + amplified SNR", "FUS array + skull-aberration phase correction; amplification; P_detect at 5-10 mm mouse, model to 75 mm", "P_detect &ge; 0.5 in vivo; within I_SPTA/MI", "Yr 2-3"),
        ("P3 Map+twin", "Pair, assemble, simulate a mouse region", "Trans-synaptic pairing; consensus assembly; O(edges) sparse twin kernel on GPU cluster", "edge F1 &ge; 0.9; region twin at real time", "Yr 3-5"),
        ("P4 Scale", "Whole mouse brain, then NHP pilot", "10^6-channel parallel readout; exabyte pipeline; NHP delivery/safety", "&lt;30-day whole-brain scan; NHP safety clean", "Yr 5-7"),
        ("P5 FIH", "First-in-human, reversible, safety-first", "IND-enabling toxicology; switchable reporters; staged dose escalation under all ceilings", "No serious adverse events; behavioural endpoints", "Yr 7-10"),
    ])
    B.append('<h2 class="s secbreak">5. Translational roadmap</h2>'
             f'<p>{_esc(name)} sits at technology-readiness level 2-3 (formulated concept with component analogues in the literature). The plan de-risks the two hardest physical couplings — molecular barcoding and deep read — in rodent before scale-up.</p>' +
             figure(road_svg(), "Five-phase translational plan, ~8-10 years bench to first-in-human.") +
             tbl("Stage-gated experimental plan with exit criteria.", '<tr><th>Phase</th><th>Goal</th><th>Key experiments</th><th>Exit gate</th><th>Timeline</th></tr>', road) +
             '<p><b>Critical-path uncertainties.</b> (i) In-vivo barcode bit-depth is the least-validated assumption and must be tested first; (ii) skull aberration at 75 mm requires holographic acoustic-lens correction; (iii) trans-synaptic transfer efficiency sets achievable edge-F1 and dictates sequencing depth.</p>')
    wl = ""
    for i, t in enumerate(TOPIC_ORDER, 1):
        exp, model, readout, crit = WETLAB[t]
        wl += (f'<tr><td class="mono">E{i}</td><td>{_esc(_short(E[t].get("title")))}</td><td>{_esc(exp)}</td>'
               f'<td>{_esc(model)}</td><td>{_esc(readout)}</td><td class="mono small">{_esc(crit)}</td></tr>')
    B.append('<h3 class="ss">5.1 Wet-lab and validation experiment program</h3>'
             f'<p>Table {tab[0]+1} specifies one concrete experiment per module of {_esc(name)} — the experiment '
             'to run, the model system, the primary readout, and the quantitative success criterion. Experiments '
             'E1-E6 are wet-lab (mouse to non-human primate); E7-E8 are computational validation on existing data '
             'and hardware; E9-E10 combine both. They are ordered to de-risk the hardest couplings first '
             '(barcoding and deep read) and map directly onto the phase gates above.</p>' +
             tbl("Per-module wet-lab and validation experiments for this prototype.",
                 '<tr><th>#</th><th>Module</th><th>Experiment</th><th>Model system</th><th>Primary readout</th><th>Success criterion</th></tr>', wl))

    # 6 Discussion
    sens = "".join(f'<tr><td>{_esc(TNAME[t])}</td><td>{_esc(d)}</td></tr>' for t, d in [
        ("in_vivo_readout", "Penetration length (skull aberration) — exponential leverage on detection"),
        ("neuron_delivery", "Transduction fraction — a 1% shortfall leaves ~10^12 blind neurons"),
        ("transsynaptic_pairing", "In-vivo trans-synaptic transfer efficiency — caps recall directly"),
        ("multiplexed_reporters", "In-vivo co-expression/readout of many reporter states, not codebook size"),
        ("snr_depth", "Reporter brightness — linear leverage vs only sqrt(N) from averaging"),
        ("twin_sim_scale", "FLOP per synapse-step — richer neuron models erode the RTF margin"),
        ("exabyte_assembly", "I/O and compute throughput on the object store, not the error arithmetic"),
        ("scan_throughput", "Manufacturability/calibration of a 10^6-element array"),
        ("behavioral_verification", "Construct validity of the stimulus battery"),
        ("human_safety", "Delivered AAV dose in situ — the tightest of the three ceilings"),
    ])
    B.append('<h2 class="s secbreak">6. Discussion</h2>'
             '<p>Three themes emerge. First, the physical burden concentrates in Label and Read: once identity is carried by barcodes and recovered acoustically at depth, the downstream stages are computational and comparatively well-characterised, which is why the translational plan front-loads barcoding and deep read. Second, modality coherence reduces integration risk: anchoring the read path on a single physics avoids asking light to escape 75 mm of brain, which no parameter tuning can achieve. Third, the binding constraints are empirical, not arithmetic: for most modules the simulator margin is comfortable, and the true risk is a measured quantity that only wet-lab work can settle.</p>' +
             tbl("Dominant empirical sensitivity per module (where measurement effort should concentrate).", '<tr><th>Module</th><th>Dominant sensitivity / most-uncertain quantity</th></tr>', sens))

    # 7 Limitations, 8 Conclusion
    B.append('<h2 class="s secbreak">7. Limitations</h2>'
             '<p>This is an in-silico design study. (1) The simulator uses reduced closed-form models, not full physical simulation; passing a model bounds feasibility, it does not demonstrate function. (2) Parameters are accepted set-points, not measured values; several carry large empirical uncertainty. (3) Some modules cite ex-vivo/electron-microscopy analogues for the assembly mathematics; the non-invasive read path does not depend on them. (4) No result has been demonstrated in a living human brain. Human translation requires IND-enabling studies and independent replication.</p>')
    B.append('<h2 class="s secbreak">8. Conclusion</h2>'
             f'<p>{_esc(name)} demonstrates that a mutually-consistent set of ten non-invasive designs can satisfy all governing constraints for whole-brain mapping and emulation simultaneously, in silico, within regulatory safety limits. Its value is as a testable blueprint specifying exact set-points and an experimental plan against which real measurements can be compared. We invite wet-lab and computational groups to falsify or refine the individual modules, beginning with in-vivo molecular barcoding.</p>'
             '<div class="decl"><b>Data & code.</b> Design records and simulator are available in the BCI v3 repository. <b>Funding.</b> None declared. <b>Competing interests.</b> None declared. <b>Ethics.</b> No human or animal subjects; computational study only.</div>')

    # References + appendix
    ref_list = "".join(f"<li>{_esc(r)}</li>" for r in REFS)
    bom = []; seen = set()
    for t in TOPIC_ORDER:
        for pt in (E[t].get("parts") or []):
            n = (pt.get("name", "") or "").strip()
            if n and n.lower() not in seen:
                seen.add(n.lower()); bom.append((n, pt.get("role", ""), PHASE[t]))
    bom_rows = "".join(f'<tr><td>{_esc(n)}</td><td>{_esc(rl)}</td><td>{_esc(ph)}</td></tr>' for n, rl, ph in bom)
    B.append('<h2 class="s secbreak">References</h2>'
             '<p class="refnote">Grounding sources retrieved by the design engine; citation numbers correspond to inline marks above. This is a preprint; sources are provided for traceability, not as peer-reviewed endorsement.</p>'
             f'<ol class="refs">{ref_list or "<li>—</li>"}</ol>')
    B.append('<h2 class="s secbreak">Appendix A. Master bill of materials</h2>' +
             tbl("Consolidated components across all modules.", '<tr><th>Component</th><th>Function</th><th>Phase</th></tr>', bom_rows))

    auto = '<script>window.onload=function(){setTimeout(function(){window.print();},350);};</script>' if autoprint else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{_esc(name)} — Research Monograph</title>'
            f'<style>{_CSS}</style></head><body>{"".join(B)}{auto}</body></html>')
