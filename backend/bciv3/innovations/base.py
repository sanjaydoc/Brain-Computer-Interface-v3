"""The Innovation abstraction + the Score a law-simulation returns.

An Innovation is one of the 10 blockers from BCI v2's innovation map. Each declares:
  * the target **spec** it must meet,
  * a **param_schema** (the quantitative knobs the invention engine must propose),
  * which **laws** govern it, and
  * an **evaluate(params)** that scores a proposed design against those laws.

`fidelity` flags how literally to read a pass: a fully-modelled topic ("full-sim") vs. an
estimate or a limits-only safety check — so v3 never overstates what the simulator proved.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Callable


@dataclass
class Score:
    passed: bool
    score: float                       # 0..1 overall
    metrics: dict = field(default_factory=dict)
    limiting: str = ""                 # the factor that held it back / the wall it cleared
    fidelity: str = "full-sim"         # full-sim | physics-only | estimate | limits-only

    def as_dict(self) -> dict:
        d = asdict(self)
        d["score"] = round(self.score, 3)
        d["metrics"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.metrics.items()}
        return d


@dataclass
class Innovation:
    id: str
    title: str
    layer: list[str]                   # tag(s): biomolecules / hardware / software / brain-template / virtual-env
    domain: str                        # inventor-studio-v3 domain the engine invents in
    laws: list[str]                    # physics / biophysics / electronics
    spec: dict                         # target requirement
    param_schema: dict                 # {name: default} — what the engine proposes
    _evaluate: Callable[[dict], Score]
    fidelity: str = "full-sim"
    keywords: str = ""                 # concise domain search seed for literature grounding
    guidance: str = ""                 # how the simulator grades this — param meanings + pass thresholds

    def evaluate(self, params: dict) -> Score:
        merged = {**self.param_schema, **(params or {})}
        s = self._evaluate(merged)
        s.fidelity = self.fidelity
        return s

    def defaults(self) -> dict:
        return dict(self.param_schema)
