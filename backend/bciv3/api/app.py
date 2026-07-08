"""Thin FastAPI backend — lets the cockpit call the Python invention engine (and your local
Qwen) live. The browser cockpit runs the deterministic proposer on its own; when this server is
up, the cockpit routes 'Invent + Simulate' here so the real LLM lenses + critique loop run.

Run:  uvicorn bciv3.api.app:app --reload --port 8000
CORS is wide-open (localhost dev tool); tighten `allow_origins` if you expose it.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import bciv3
from bciv3 import backends, invent, design, rank, report, all_ids, record, store
from bciv3.engine import LENSES
from bciv3.innovations import CATALOG

app = FastAPI(title="BCI v3 — invention engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Serve the cockpit from the same origin, so one command + one port runs API + GUI (`bci serve`).
DOCS = Path(__file__).resolve().parents[3] / "docs"


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
    n_lenses: int = 10             # run the first N of the 10 lenses (3 / 5 / 10)


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
    n = max(1, min(int(req.n_lenses), len(LENSES)))
    return {"ranked": rank(req.topic, req.prompt, lenses=list(LENSES)[:n], backend=req.backend),
            "n_lenses": n}


@app.post("/api/record")
def do_record(req: DesignReq) -> dict:
    """Invent → simulate → detail → save. Returns the full stored record."""
    if req.topic not in CATALOG:
        return {"error": f"unknown topic {req.topic!r}", "topics": all_ids()}
    return {"record": record(req.topic, req.prompt, lens=req.lens, backend=req.backend, save=True),
            "store": store.backend()}


@app.get("/api/inventions")
def do_inventions(topic: str | None = None, limit: int = 50) -> dict:
    return {"inventions": store.list_records(topic, limit=limit), "store": store.backend()}


@app.get("/api/inventions/grouped")
def do_grouped() -> dict:
    """All saved inventions grouped by the 10 innovation categories (topics)."""
    groups = store.list_grouped()
    return {"groups": {tid: groups.get(tid, []) for tid in CATALOG}, "store": store.backend()}


@app.delete("/api/inventions/{rec_id}")
def do_delete(rec_id: str) -> dict:
    return {"deleted": store.delete(rec_id)}


@app.get("/api/stats")
def do_stats() -> dict:
    return store.stats()


# --- static cockpit (mounted last so /api/* always wins) ---------------------
if DOCS.is_dir():
    @app.get("/")
    def _root() -> RedirectResponse:
        return RedirectResponse(url="/app/")

    if (DOCS / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DOCS / "assets"), name="assets")
    app.mount("/app", StaticFiles(directory=DOCS / "app", html=True), name="cockpit")
