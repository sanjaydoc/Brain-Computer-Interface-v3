"""Prompt construction for the invention engine — ports the inventor-studio-v3 pattern: a
creative *lens* frames the reasoning, and the model must return a structured design whose
quantitative parameters the simulator can grade against the laws.
"""

from __future__ import annotations

from ..innovations.base import Innovation

# The ten creative lenses (from inventor-studio-v3's dream agents), each a short directive.
LENSES = {
    "analogical":    "Find how nature or another field already solves a similar problem, extract the mechanism, and apply it.",
    "inversion":     "Flip the assumptions everyone makes; design from the inverted premise.",
    "crossDomain":   "Import a solution structure from a distant field (software, physics, economics, immunology).",
    "extreme":       "Remove all constraints, design the ideal, then find the simplest real-technology approximation.",
    "historical":    "Study what was tried and failed; design specifically to avoid those failure modes.",
    "biomimicry":    "Find the organism or biological system that solves this best and replicate its exact mechanism.",
    "combinatorial": "Fuse two unrelated existing technologies into one novel mechanism.",
    "reduction":     "Strip to the absolute core; solve only that with minimum complexity.",
    "scaling":       "Change the scale 1000× (nano or macro); exploit the new physics that emerges.",
    "future":        "Assume it is solved 30 years out; work backward to what must exist first.",
}

DEFAULT_LENS = "biomimicry"


def build_invent_prompt(inv: Innovation, user_prompt: str, lens: str, context: str = "") -> str:
    directive = LENSES.get(lens, LENSES[DEFAULT_LENS])
    schema = ", ".join(f'"{k}": <number>' for k in inv.param_schema)
    laws = ", ".join(inv.laws)
    grounding = f"\n\n{context}\nGround your design in the prior knowledge above where relevant.\n" if context else ""
    return f"""You are the {lens} Invention Agent for a non-invasive brain-mapping program.
Invent ONE concrete design that solves the target below, then express it as parameters a physics
simulator can grade. Output ONLY raw JSON, no markdown.

TARGET (innovation): {inv.title}
DOMAIN: {inv.domain}   GOVERNING LAWS: {laws}
SPEC (must meet): {inv.spec}
USER PROMPT: {str(user_prompt or '').strip()[:300]}{grounding}

LENS — {directive}

The design's numeric parameters MUST use exactly these keys (pick values that clear the spec):
{{{schema}}}

JSON:
{{"title":"short catchy name","mechanism":"2-3 sentences on how it physically works","domain":"{inv.domain}","params":{{{schema}}},"assumptions":["a1","a2"],"risks":["r1"],"noveltyScore":0.8}}"""


def build_refine_prompt(inv: Innovation, prev: dict, score) -> str:
    """Second-round prompt: feed back the simulator's failure so the model repairs the design."""
    schema = ", ".join(f'"{k}": <number>' for k in inv.param_schema)
    return f"""Your previous design for "{inv.title}" FAILED the physics simulator.
LIMITING FACTOR: {score.limiting}
MEASURED: {score.metrics}
PREVIOUS PARAMS: {prev.get('params', {})}

Revise the parameters to clear the wall (respect real physical/biological plausibility — do not
just set impossible numbers). Output ONLY raw JSON with the same keys:
{{"title":"{prev.get('title','revised')}","mechanism":"what you changed and why","domain":"{inv.domain}","params":{{{schema}}},"assumptions":["a1"],"risks":["r1"],"noveltyScore":0.8}}"""
