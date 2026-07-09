"""Brain-Computer-Interface v3 — the invention engine + law-based simulator.

v1 interfaces with a connectome; v2 maps it and measures the 10 blockers; v3 tries to *invent
past* those blockers. Pick one of the 10 innovation topics, add a prompt, and the engine (a
local-LLM-first invention pipeline ported from inventor-studio-v3) proposes a design — which the
simulator then grades against the laws of biophysics, physics, and electronics.

    invent(topic, prompt) → candidate design → simulate() → pass/fail + the limiting number

Honesty by construction: the engine only proposes; only the physics can move the score. A
passing score means *physically admissible*, not *proven in a living brain*.
"""

from . import llm, laws, innovations, engine, simulator, detailer, store, recorder, search, bench, synthesis, presets, research
from .engine import invent, design, rank, backends, LENSES
from .simulator import simulate, simulate_params, report
from .detailer import detail
from .recorder import record, build_record
from .search import retrieve
from .innovations import CATALOG, all_ids

__all__ = ["llm", "laws", "innovations", "engine", "simulator", "detailer", "store", "recorder", "search", "bench", "synthesis", "presets", "research",
           "invent", "design", "rank", "backends", "LENSES",
           "simulate", "simulate_params", "report", "detail", "record", "build_record", "retrieve",
           "CATALOG", "all_ids"]
