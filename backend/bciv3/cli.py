"""`bci` — one command to run everything. From the project root (with the venv active):

    bci serve                 # API + cockpit on one port → http://localhost:8000/app/
    bci serve --port 9000     # pick a port
    bci invent multiplexed_reporters "acoustic, deep, safe"   # one-shot from the terminal
    bci topics                # list the 10 innovation topics
"""

from __future__ import annotations

import argparse
import json
import sys


def _serve(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed — run:  pip install -e \".[api]\"", file=sys.stderr)
        return 1
    print(f"BCI v3 → cockpit: http://{args.host}:{args.port}/app/   ·   API: /api/health")
    uvicorn.run("bciv3.api.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def _invent(args) -> int:
    import bciv3
    cand = bciv3.invent(args.topic, args.prompt or "", lens=args.lens, backend=args.backend)
    print(json.dumps(bciv3.report(args.topic, cand), indent=2))
    return 0


def _topics(_args) -> int:
    from bciv3.innovations import CATALOG
    for tid, inv in CATALOG.items():
        print(f"{tid:<24} {inv.fidelity:<12} {inv.title}")
    return 0


def _record(args) -> int:
    import bciv3
    rec = bciv3.record(args.topic, args.prompt or "", lens=args.lens, backend=args.backend, save=True)
    print(f"saved id={rec['id']}  →  {bciv3.store.backend()}")
    print(json.dumps({k: rec[k] for k in ("topic", "title", "score", "detail", "parts")}, indent=2))
    return 0


def _db(args) -> int:
    import bciv3
    if args.stats:
        print(json.dumps(bciv3.store.stats(), indent=2)); return 0
    rows = bciv3.store.list_records(args.topic, limit=args.limit)
    print(f"store: {bciv3.store.backend()}   ({len(rows)} shown)")
    for r in rows:
        sc = r.get("score", {})
        print(f"  [{'PASS' if sc.get('passed') else 'fail'}] {sc.get('score'):<6} "
              f"{r.get('topic'):<22} {r.get('title','')[:40]}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bci", description="Brain-Computer-Interface v3 — invention engine")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("serve", help="run the API + cockpit on one port")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true", help="auto-reload on code changes (dev)")
    s.set_defaults(fn=_serve)

    iv = sub.add_parser("invent", help="invent + simulate one design from the terminal")
    iv.add_argument("topic")
    iv.add_argument("prompt", nargs="?", default="")
    iv.add_argument("--lens", default="biomimicry")
    iv.add_argument("--backend", default="auto", choices=["auto", "llm", "fallback"])
    iv.set_defaults(fn=_invent)

    t = sub.add_parser("topics", help="list the 10 innovation topics")
    t.set_defaults(fn=_topics)

    rc = sub.add_parser("record", help="invent + detail + score, then save to the database")
    rc.add_argument("topic")
    rc.add_argument("prompt", nargs="?", default="")
    rc.add_argument("--lens", default="biomimicry")
    rc.add_argument("--backend", default="auto", choices=["auto", "llm", "fallback"])
    rc.set_defaults(fn=_record)

    db = sub.add_parser("db", help="list saved inventions (or --stats)")
    db.add_argument("topic", nargs="?", default=None)
    db.add_argument("--limit", type=int, default=20)
    db.add_argument("--stats", action="store_true")
    db.set_defaults(fn=_db)

    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        p.print_help()
        return 0
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
