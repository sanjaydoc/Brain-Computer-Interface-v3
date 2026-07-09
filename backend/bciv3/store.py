"""Persistence — save each invention (design + multi-domain detail + score) to MongoDB.

Local MongoDB Community is the target: set ``MONGODB_URI`` (default mongodb://localhost:27017)
and ``MONGODB_DB`` (default ``bciv3``); records land in the ``inventions`` collection. If pymongo
isn't installed or Mongo is unreachable, it transparently falls back to a JSONL file
(``inventions.jsonl``), so the pipeline still records everything before the DB is up.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

_JSONL = Path(os.environ.get("BCIV3_JSONL", "inventions.jsonl"))


_CLIENT = None          # cached MongoClient (created once)
_MONGO_OK = None        # None = unchecked, False = unavailable (cached so we don't re-ping every call)
_INDEXED = False


def _client():
    """One cached Mongo client. The connect-and-ping happens once, not on every store read — a
    synthesis touches the store ~30 times, and reconnecting each time (an 800ms timeout when Mongo is
    down) is what used to make it hang. Set BCIV3_NO_MONGO=1 to force the JSONL fallback."""
    global _CLIENT, _MONGO_OK
    if os.environ.get("BCIV3_NO_MONGO", "").lower() in ("1", "true", "yes"):
        return None
    if _MONGO_OK is False:
        return None
    if _CLIENT is not None:
        return _CLIENT
    try:
        import pymongo
    except Exception:
        _MONGO_OK = False; return None
    try:
        c = pymongo.MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
                                serverSelectionTimeoutMS=800)
        c.admin.command("ping")                            # fail fast if Mongo is down
        _CLIENT = c; _MONGO_OK = True; return c
    except Exception:
        _MONGO_OK = False; return None


def _col(name: str = "inventions"):
    """Return a live Mongo collection, or None to signal JSONL fallback."""
    global _INDEXED
    c = _client()
    if c is None:
        return None
    col = c[os.environ.get("MONGODB_DB", "bciv3")][name]
    if name == "inventions" and not _INDEXED:
        try:
            col.create_index([("topic", 1)]); col.create_index([("score.score", -1)]); _INDEXED = True
        except Exception:
            pass
    return col


def _mongo():
    return _col("inventions")


def backend() -> str:
    return "mongodb" if _col() is not None else f"jsonl ({_JSONL})"


def save(record: dict) -> str:
    """Persist one invention record; returns its id. Adds an id if missing."""
    rec = dict(record)
    rec.setdefault("id", uuid.uuid4().hex)
    col = _mongo()
    if col is not None:
        rec["_id"] = rec["id"]
        col.replace_one({"_id": rec["_id"]}, rec, upsert=True)
    else:
        with open(_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    return rec["id"]


def list_records(topic: str | None = None, limit: int = 50) -> list[dict]:
    """Most-relevant records first (highest score), optionally filtered by topic."""
    col = _mongo()
    if col is not None:
        q = {"topic": topic} if topic else {}
        cur = col.find(q, {"_id": 0}).sort("score.score", -1).limit(int(limit))
        return list(cur)
    if not _JSONL.exists():
        return []
    rows = [json.loads(l) for l in _JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    if topic:
        rows = [r for r in rows if r.get("topic") == topic]
    rows.sort(key=lambda r: r.get("score", {}).get("score", 0), reverse=True)
    return rows[:int(limit)]


def delete(rec_id: str) -> bool:
    """Remove one record by id. Returns True if something was deleted."""
    col = _mongo()
    if col is not None:
        return col.delete_one({"_id": rec_id}).deleted_count > 0
    if not _JSONL.exists():
        return False
    rows = [json.loads(l) for l in _JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    keep = [r for r in rows if r.get("id") != rec_id]
    if len(keep) == len(rows):
        return False
    _JSONL.write_text("".join(json.dumps(r, default=str) + "\n" for r in keep), encoding="utf-8")
    return True


def list_grouped(limit_per: int = 100) -> dict:
    """All records grouped by topic (the 10 categories) — best-first within each."""
    out: dict[str, list] = {}
    for r in list_records(limit=100000):
        out.setdefault(r.get("topic", "?"), []).append(r)
    return {t: rows[:limit_per] for t, rows in out.items()}


_BENCH_JSONL = Path(os.environ.get("BCIV3_BENCH_JSONL", "benchmarks.jsonl"))


def save_bench(summary: dict) -> str:
    """Persist a compact benchmark summary (leaderboard) to the `benchmarks` collection."""
    rec = dict(summary)
    rec.setdefault("id", uuid.uuid4().hex)
    col = _col("benchmarks")
    if col is not None:
        rec["_id"] = rec["id"]
        col.insert_one(rec)
    else:
        with open(_BENCH_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    return rec["id"]


def list_benchmarks(limit: int = 20) -> list[dict]:
    col = _col("benchmarks")
    if col is not None:
        return list(col.find({}, {"_id": 0}).sort("ts", -1).limit(int(limit)))
    if not _BENCH_JSONL.exists():
        return []
    rows = [json.loads(l) for l in _BENCH_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    return list(reversed(rows))[:int(limit)]


_SYNTH_JSONL = Path(os.environ.get("BCIV3_SYNTH_JSONL", "syntheses.jsonl"))


def save_synthesis(record: dict) -> str:
    """Persist one synthesized end-to-end system (a 'prototype') to the `syntheses` collection.
    Every `synthesize` run is kept, so you accumulate a library of prototypes over time."""
    rec = dict(record)
    rec.setdefault("id", uuid.uuid4().hex)
    col = _col("syntheses")
    if col is not None:
        rec["_id"] = rec["id"]
        col.insert_one(rec)
    else:
        with open(_SYNTH_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
    return rec["id"]


def list_syntheses(limit: int = 20) -> list[dict]:
    """Saved prototypes, newest first."""
    col = _col("syntheses")
    if col is not None:
        return list(col.find({}, {"_id": 0}).sort("ts", -1).limit(int(limit)))
    if not _SYNTH_JSONL.exists():
        return []
    rows = [json.loads(l) for l in _SYNTH_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    return list(reversed(rows))[:int(limit)]


def delete_synthesis(rec_id: str) -> bool:
    """Remove one saved prototype by id."""
    col = _col("syntheses")
    if col is not None:
        return col.delete_one({"_id": rec_id}).deleted_count > 0
    if not _SYNTH_JSONL.exists():
        return False
    rows = [json.loads(l) for l in _SYNTH_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    keep = [r for r in rows if r.get("id") != rec_id]
    if len(keep) == len(rows):
        return False
    _SYNTH_JSONL.write_text("".join(json.dumps(r, default=str) + "\n" for r in keep), encoding="utf-8")
    return True


def stats() -> dict:
    rows = list_records(limit=100000)
    per_topic: dict[str, dict] = {}
    for r in rows:
        t = r.get("topic", "?")
        d = per_topic.setdefault(t, {"count": 0, "passes": 0, "best": 0.0})
        d["count"] += 1
        sc = r.get("score", {})
        d["passes"] += 1 if sc.get("passed") else 0
        d["best"] = max(d["best"], sc.get("score", 0.0))
    return {"backend": backend(), "total": len(rows), "per_topic": per_topic}
