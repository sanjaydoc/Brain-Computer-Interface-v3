"""Invention engine — pick a topic + a prompt, get a candidate design.

LLM path (ported from inventor-studio-v3's reasoning + retries + JSON-extract) frames the idea
through a creative lens and proposes design parameters. A deterministic rule-based fallback
always returns a valid, spec-aware design, so v3 runs with no LLM (CI / offline / no GPU).

The engine only *proposes*; grading is the simulator's job — invention and evaluation are kept
separate so a persuasive narrative can never fake a passing score.
"""

from __future__ import annotations

from .. import llm
from ..innovations import Innovation, get
from .prompt import LENSES, DEFAULT_LENS, build_invent_prompt


def _sanitize_params(inv: Innovation, raw: dict) -> dict:
    """Keep only schema keys; coerce to numbers; fall back to the default for anything missing."""
    out = dict(inv.param_schema)
    for k, default in inv.param_schema.items():
        v = (raw or {}).get(k, default)
        if isinstance(default, str):
            out[k] = str(v)
        else:
            try:
                out[k] = float(v)
            except Exception:
                out[k] = default
    return out


def _rule_based(inv: Innovation, prompt: str) -> dict:
    """Deterministic proposer: nudge each knob toward the spec so the design is a real attempt,
    not just the defaults. Physically bounded — it won't propose impossible numbers."""
    p = dict(inv.param_schema)
    t = str(prompt or "").lower()
    if inv.id == "multiplexed_reporters":
        p["barcode_bits"] = 48                      # enough for a human fUS voxel
        p["channels"] = 16                          # stay within acoustic ceiling
    elif inv.id == "transsynaptic_pairing":
        p["dropout"], p["false_pair_rate"] = 0.1, 0.02
        p["reads_per_synapse"], p["min_reads"] = 10, 2
    elif inv.id == "neuron_delivery":
        p["transduction_fraction"] = 0.995
        p["aav_dose_vg_per_kg"] = 8e13
    elif inv.id == "snr_depth":
        p["signal_gain"], p["averaging_n"], p["noise_floor"] = 4.0, 64, 0.7
    elif inv.id == "scan_throughput":
        p["parallel_channels"], p["dwell_s"] = 65536, 2e-4
    elif inv.id == "in_vivo_readout":
        p["snr0"], p["penetration_um"] = 24.0, 120_000.0
        p["ispta_mw_cm2"], p["mechanical_index"] = 400.0, 1.0
    elif inv.id == "exabyte_assembly":
        p["min_reads"], p["bytes_per_read"], p["storage_exabytes"] = 6, 2, 50.0
    elif inv.id == "twin_sim_scale":
        p["hardware_flops"] = 1e21                  # exascale+ toward zettascale
    elif inv.id == "behavioral_verification":
        p["edge_recall"], p["n_stimuli"] = 0.92, 12
    elif inv.id == "human_safety":
        p["ispta_mw_cm2"], p["mechanical_index"], p["aav_dose_vg_per_kg"] = 300.0, 0.8, 3e13
    if "aggressive" in t or "max" in t:
        for k, v in p.items():
            if isinstance(v, (int, float)) and k in ("signal_gain", "averaging_n", "parallel_channels"):
                p[k] = v * 2
    return {"title": f"{inv.title} — rule-based candidate", "mechanism": "Deterministic spec-aware proposal.",
            "domain": inv.domain, "params": p, "assumptions": ["rule-based fallback (no LLM)"],
            "risks": ["assumptions unverified"], "noveltyScore": 0.5, "lens": "reduction", "backend": "fallback"}


def invent(topic_id: str, prompt: str = "", *, lens: str = DEFAULT_LENS, backend: str = "auto",
           ground: bool = False, sources=None) -> dict:
    inv = get(topic_id)
    lens = lens if lens in LENSES else DEFAULT_LENS
    chosen = backend if backend != "auto" else ("llm" if llm.available() else "fallback")

    # ground the design in real literature / prior art (PubMed, arXiv, Wikipedia, …)
    citations, context = [], ""
    if ground:
        from ..search import retrieve
        res = retrieve(f"{inv.title} {prompt}".strip())
        citations, context = res["citations"], res["context"]

    def _grounded(out: dict) -> dict:
        out["citations"] = citations
        out["grounded"] = bool(ground and citations)
        return out

    if chosen == "llm":
        for _ in range(3):
            try:
                parsed = llm.extract_json(llm.invoke_json(build_invent_prompt(inv, prompt, lens, context), max_tokens=2000))
            except Exception as exc:
                return _grounded({**_rule_based(inv, prompt), "note": f"llm failed ({exc}); used fallback"})
            if parsed and parsed.get("params"):
                _list = lambda k: [str(x) for x in (parsed.get(k) or [])][:40]
                _num = lambda k, d: float(parsed.get(k) or d)
                return _grounded({"title": str(parsed.get("title") or inv.title)[:200],
                        "mechanism": str(parsed.get("mechanism") or ""),        # full, not trimmed
                        "domain": parsed.get("domain", inv.domain),
                        "params": _sanitize_params(inv, parsed.get("params")),
                        "materials": _list("materials"),
                        "protocol_steps": _list("protocol_steps"),
                        "assumptions": _list("assumptions"),
                        "risks": _list("risks"),
                        "references": _list("references"),
                        "noveltyScore": _num("noveltyScore", 0.7),
                        "feasibilityScore": _num("feasibilityScore", 0.6),
                        "impactScore": _num("impactScore", 0.7),
                        "lens": lens, "backend": "llm", "provider": llm.provider()})
        return _grounded({**_rule_based(inv, prompt), "note": "llm returned no usable design; used fallback"})
    return _grounded(_rule_based(inv, prompt))


def backends() -> dict:
    return {"llm": llm.available(), "provider": llm.provider(), "fallback": True, "lenses": list(LENSES)}
