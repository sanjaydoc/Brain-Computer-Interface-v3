"""Thin FastAPI backend — lets the cockpit call the Python invention engine (and your local
Qwen) live. The browser cockpit runs the deterministic proposer on its own; when this server is
up, the cockpit routes 'Invent + Simulate' here so the real LLM lenses + critique loop run.

Run:  uvicorn bciv3.api.app:app --reload --port 8000
CORS is wide-open (localhost dev tool); tighten `allow_origins` if you expose it.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import bciv3
from bciv3 import backends, invent, design, rank, report, all_ids
from bciv3.engine import LENSES
from bciv3.innovations import CATALOG

app = FastAPI(title="BCI v3 — invention engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


class InventReq(BaseModel):
    topic: str
    prompt: str = ""
    lens: str = "biomimicry"
    backend: str = "auto"          # auto | llm | fallback


class DesignReq(InventReq):
    rounds: int = 3


class RankReq(BaseModel):
    topic: str
    prompt: str = ""
    backend: str = "auto"


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "backends": backends()}


@app.get("/api/topics")
def topics() -> dict:
    return {"topics": [
        {"id": tid, "title": inv.title, "layer": inv.layer, "domain": inv.domain,
         "laws": inv.laws, "fidelity": inv.fidelity, "params": inv.param_schema}
        for tid, inv in CATALOG.items()
    ], "lenses": list(LENSES)}


@app.post("/api/invent")
def do_invent(req: InventReq) -> dict:
    if req.topic not in CATALOG:
        return {"error": f"unknown topic {req.topic!r}", "topics": all_ids()}
    cand = invent(req.topic, req.prompt, lens=req.lens, backend=req.backend)
    return {"candidate": cand, "result": report(req.topic, cand)}


@app.post("/api/design")
def do_design(req: DesignReq) -> dict:
    if req.topic not in CATALOG:
        return {"error": f"unknown topic {req.topic!r}", "topics": all_ids()}
    return design(req.topic, req.prompt, rounds=req.rounds, lens=req.lens, backend=req.backend)


@app.post("/api/rank")
def do_rank(req: RankReq) -> dict:
    if req.topic not in CATALOG:
        return {"error": f"unknown topic {req.topic!r}", "topics": all_ids()}
    return {"ranked": rank(req.topic, req.prompt, backend=req.backend)}
