"""Synthesis — once ALL 10 blockers have a PASSING design, fuse them into one end-to-end
brain-uploading system: an ordered pipeline (Label → Read → Map → Emulate, inside a Safety
envelope), a consolidated parts list, and a "how it works" narrative for the schematic.

The gate is strict: `status()["complete"]` is True only when every one of the 10 topics has at least
one saved record with ``score.passed`` — that's what unlocks the GUI's Synthesize button.
"""

from __future__ import annotations

from . import llm, store
from .innovations import CATALOG, all_ids

# The 10 blockers arranged as the actual brain-uploading pipeline. Each stage names the solved topic,
# its role in the whole system, and what it hands to the next stage (inputs → outputs).
PHASES = [
    ("Label", "Get a unique molecular identity into every neuron, non-invasively.", [
        ("neuron_delivery", "Deliver reporter genes into ~100% of neurons across the blood-brain barrier",
         "a systemic dose", "every neuron carries the reporter cassette"),
        ("multiplexed_reporters", "Give each neuron/synapse a unique, demultiplexable molecular barcode",
         "reporter-expressing neurons", "a voxel full of distinguishable barcodes"),
    ]),
    ("Read", "Read those barcodes out of the living brain, at depth, fast enough.", [
        ("in_vivo_readout", "Read the barcodes non-destructively inside the living brain",
         "barcoded neurons", "raw per-voxel reporter signals"),
        ("snr_depth", "Boost signal and cut noise so it still reads in deep structures",
         "raw reporter signals", "clean signals at whole-brain depth"),
        ("scan_throughput", "Read the whole brain within a practical time budget",
         "clean per-voxel signals", "a whole-brain stream of reads"),
    ]),
    ("Map", "Turn noisy reads into an error-corrected wiring diagram.", [
        ("transsynaptic_pairing", "Pair pre- and post-synaptic barcodes to recover the edges (connections)",
         "whole-brain reads", "candidate synaptic edges"),
        ("exabyte_assembly", "Assemble and error-correct the exabyte-scale connectome",
         "candidate edges", "a clean whole-brain connectome"),
    ]),
    ("Emulate", "Run the twin and prove it behaves like the original.", [
        ("twin_sim_scale", "Run the whole-brain digital twin in real time",
         "the connectome", "a running digital twin"),
        ("behavioral_verification", "Verify the twin behaves like the original brain",
         "the running twin", "a verified upload"),
    ]),
]
SAFETY_TOPIC = "human_safety"   # the cross-cutting envelope around the whole chain


def _best_passing(topic: str) -> dict | None:
    """The highest-scoring PASSING saved record for a topic, or None if none passes yet."""
    for r in store.list_records(topic, limit=200):          # already sorted best-first
        if (r.get("score") or {}).get("passed"):
            return r
    return None


def status() -> dict:
    """Per-topic solved state + the gate. `complete` is True only when all 10 pass."""
    solved, missing = {}, []
    for tid in all_ids():
        best = _best_passing(tid)
        if best:
            solved[tid] = {"title": best.get("title"), "score": (best.get("score") or {}).get("score"),
                           "id": best.get("id")}
        else:
            missing.append(tid)
    return {"solved": solved, "missing": missing,
            "solved_count": len(solved), "total": len(all_ids()),
            "complete": len(missing) == 0}


def _stage(topic: str, role: str, feeds_in: str, feeds_out: str, rec: dict) -> dict:
    inv = CATALOG[topic]
    sc = rec.get("score") or {}
    return {"topic": topic, "title": rec.get("title") or inv.title, "role": role,
            "domain": inv.domain, "layer": inv.layer,
            "inputs": feeds_in, "outputs": feeds_out,
            "score": sc.get("score"), "fidelity": sc.get("fidelity"),
            "mechanism": rec.get("mechanism", ""),
            "parts": rec.get("parts", []), "params": rec.get("params", {}),
            "constraint": rec.get("constraint")}


def _pipeline(solved_records: dict) -> list[dict]:
    out = []
    for phase, why, stages in PHASES:
        pstages = [_stage(t, role, fin, fout, solved_records[t])
                   for (t, role, fin, fout) in stages if solved_records.get(t)]
        out.append({"phase": phase, "why": why, "stages": pstages})
    return out


def _llm_overview(records: dict) -> dict | None:
    """Ask the LLM to weave the 10 solved designs into one integrated system description."""
    if not llm.available():
        return None
    lines = []
    for tid in all_ids():
        r = records.get(tid) or {}
        parts = ", ".join(p.get("name", "") for p in (r.get("parts") or [])[:4])
        lines.append(f"- {CATALOG[tid].title}: {r.get('title','')} — {str(r.get('mechanism',''))[:220]} "
                     f"[key parts: {parts}]")
    prompt = ("Ten brain-mapping blockers have each been solved with a concrete, physically-admissible "
              "design (listed below). Fuse them into ONE end-to-end non-invasive brain-UPLOADING system: "
              "how the solved pieces connect (each stage's output feeds the next), stage by stage, from "
              "molecular labeling to a verified digital twin. Output ONLY JSON:\n"
              '{"system_name":"catchy name","overview":"2-3 sentence what-it-is","how_it_works":'
              '["end-to-end step 1","step 2","..."],"integration_notes":"how the interfaces line up",'
              '"open_risks":["r1","r2"]}\n\nSOLVED DESIGNS:\n' + "\n".join(lines))
    try:
        parsed = llm.extract_json(llm.invoke_json(prompt, max_tokens=1200))
        if parsed and parsed.get("how_it_works"):
            return parsed
    except Exception:
        pass
    return None


def _deterministic_overview(pipeline: list[dict]) -> dict:
    steps = []
    for ph in pipeline:
        for s in ph["stages"]:
            steps.append(f"[{ph['phase']}] {s['title']}: {s['role']} (takes {s['inputs']} → yields {s['outputs']}).")
    return {"system_name": "End-to-End Non-Invasive Brain-Uploading System",
            "overview": "A single pipeline that labels every neuron with a molecular barcode, reads the "
                        "barcodes out of the living brain at depth and speed, reconstructs the whole-brain "
                        "connectome, and runs a verified real-time digital twin — all within safety limits.",
            "how_it_works": steps,
            "integration_notes": "Each stage's output is the next stage's input; the human-safety envelope "
                                 "bounds intensity, mechanical index, and viral dose across the whole chain.",
            "open_risks": ["Each stage is physically admissible in-model, not yet proven in a living human brain."]}


def synthesize() -> dict:
    """Fuse the 10 passing designs into one system. Raises if the gate isn't met (all 10 must pass)."""
    st = status()
    if not st["complete"]:
        return {"complete": False, "missing": st["missing"], "solved_count": st["solved_count"],
                "total": st["total"], "error": "Solve all 10 blockers first — "
                f"{st['solved_count']}/{st['total']} passing."}

    records = {tid: _best_passing(tid) for tid in all_ids()}
    pipeline = _pipeline(records)
    system = _llm_overview(records) or _deterministic_overview(pipeline)
    system["engine"] = "llm" if llm.available() else "template"

    # consolidated bill of materials (dedup by name), tagged with the stage it comes from
    bom, seen = [], set()
    for ph in pipeline:
        for s in ph["stages"]:
            for p in s.get("parts", []):
                key = (p.get("name", "") or "").lower()
                if key and key not in seen:
                    seen.add(key)
                    bom.append({"name": p.get("name"), "role": p.get("role"), "stage": s["title"], "phase": ph["phase"]})

    safety = _best_passing(SAFETY_TOPIC)
    return {"complete": True, "system": system, "pipeline": pipeline,
            "bill_of_materials": bom,
            "safety": {"title": (safety or {}).get("title"), "params": (safety or {}).get("params", {}),
                       "score": ((safety or {}).get("score") or {}).get("score")},
            "solved_count": st["solved_count"], "total": st["total"], "store": store.backend()}
