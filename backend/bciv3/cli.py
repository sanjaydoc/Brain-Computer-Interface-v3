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
    cand = bciv3.invent(args.topic, args.prompt or "", lens=args.lens, backend=args.backend,
                        model=args.model, constraint=args.constraint)
    print(json.dumps(bciv3.report(args.topic, cand), indent=2))
    return 0


def _topics(_args) -> int:
    from bciv3.innovations import CATALOG
    for tid, inv in CATALOG.items():
        print(f"{tid:<24} {inv.fidelity:<12} {inv.title}")
    return 0


def _record(args) -> int:
    import bciv3
    rec = bciv3.record(args.topic, args.prompt or "", lens=args.lens, backend=args.backend,
                       ground=args.ground, save=True, model=args.model, constraint=args.constraint)
    via = rec.get("backend")
    tag = f"LLM ({rec.get('provider')})" if via == "llm" else f"{via} (no LLM used)" if via == "fallback" else via
    ground = f"grounded: {', '.join(rec.get('sources_used') or []) or 'none'}"
    print(f"saved id={rec['id']}  →  {bciv3.store.backend()}   |   engine: {tag}   |   {ground}")
    print(json.dumps(rec, indent=2, ensure_ascii=False, default=str))    # full record, nothing trimmed
    return 0


def _health(_args) -> int:
    import bciv3
    b = bciv3.backends()
    print("LLM provider :", b["provider"] or "NONE — falling back to the rule-based proposer")
    print("LLM available:", b["llm"])
    print("database     :", bciv3.store.backend())
    from bciv3.search.retrieve import _enabled
    print("search       :", ", ".join(_enabled(None)) or "none")
    import os
    print("LOCAL_LLM_URL:", os.environ.get("LOCAL_LLM_URL") or "(unset) — required to use a local model")
    print("LOCAL_LLM_MODEL:", os.environ.get("LOCAL_LLM_MODEL") or "(unset)")
    if not b["llm"]:
        print("\n→ To use Qwen: set LOCAL_LLM_URL=http://localhost:11434/v1 (+ LOCAL_LLM_MODEL) and run `ollama serve`.")
    return 0


def _ping(args) -> int:
    import bciv3
    r = bciv3.llm.ping(max_tokens=args.max_tokens, timeout=args.timeout)
    if r.get("provider") is None:
        print("✗ No LLM configured. Set LOCAL_LLM_URL=http://localhost:11434/v1 in backend/.env")
        return 1
    j, pl = r["json"], r["plain"]
    fmt = lambda x: (f"OK  {x['elapsed']}s  → {x.get('content','')!r}" if x["ok"]
                     else f"FAIL {x['elapsed']}s  → {x.get('error','')}")
    print(f"provider={r['provider']}  model={r['model']}\n")
    print(f"  JSON-mode (response_format) : {fmt(j)}")
    print(f"  plain-mode (no constraint)  : {fmt(pl)}\n")
    if pl["ok"] and not j["ok"]:
        print("→ DIAGNOSIS: the JSON grammar constraint is the bottleneck — plain works, JSON-mode hangs.")
        print("  FIX (no code change, effective now):  set  BCI_LLM_JSON_MODE=off  in backend/.env")
        print("  qwen2.5:7b emits clean JSON from the prompt alone, so it doesn't need the constraint.")
    elif j["ok"] and pl["ok"]:
        print("→ Both modes work. The model is healthy; a slow full invention is just generation length")
        print("  — raise BCI_LLM_TIMEOUT in backend/.env if a 2000-token run still times out.")
    elif not j["ok"] and not pl["ok"]:
        err = str(j.get("error", "")).lower()
        if "timed out" in err:
            print("→ Both modes time out — the model itself is slow/cold. Warm it (`ollama run qwen2.5:7b`),")
            print("  check `ollama ps` shows GPU (not 100% CPU), or raise:  bci ping --timeout 180")
        else:
            print("→ Both modes error before generating. Check `ollama serve` is up, the model is pulled")
            print("  (`ollama list`), and LOCAL_LLM_URL is correct (default http://localhost:11434/v1).")
    else:
        print("→ JSON-mode works but plain failed (unusual). Keep JSON-mode on; re-run to confirm.")
    return 0 if r.get("ok") else 1


def _search(args) -> int:
    import bciv3
    res = bciv3.retrieve(args.query)
    print("per-source status:")
    for name, status in sorted(res.get("per_source", {}).items()):
        print(f"  {name:<10} {status}")
    print(f"\n{len(res['citations'])} citation(s):")
    for c in res["citations"]:
        print(f"  [{c['source']:<9}] {c['title'][:70]}\n              {c['url']}")
    return 0


def _bench(args) -> int:
    import bciv3
    res = bciv3.bench.run(samples=args.samples, prompt=args.prompt or "",
                          topics=[args.topic] if args.topic else None,
                          backend=args.backend, ground=args.ground,
                          save_attempts=args.save_attempts, model=args.model,
                          constraint=args.constraint)
    m = res["model"] or res["provider"] or "rule-based"
    print(f"model: {m}  |  samples/topic: {res['samples_per_topic']}  |  grounded: {res['grounded']}")
    print(f"MEAN pass-rate: {res['mean_pass_rate']}   MEAN score: {res['mean_score']}\n")
    print(f"{'topic':<24}{'pass-rate':>10}{'mean':>9}{'best':>7}{'n':>4}")
    for tid, t in res["per_topic"].items():
        print(f"{tid:<24}{t['pass_rate']:>10}{t['mean_score']:>9}{t['best_score']:>7}{t['samples']:>4}")
    print(f"\nsaved leaderboard → {bciv3.store.backend()} (benchmarks)")
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
    iv.add_argument("--model", default=None, help="override the LLM model (e.g. qwen2.5:3b) for this run")
    iv.add_argument("--constraint", default=None, choices=["noninvasive", "invasive"],
                    help="restrict the design: noninvasive (biomolecules) or invasive (electrodes)")
    iv.set_defaults(fn=_invent)

    t = sub.add_parser("topics", help="list the 10 innovation topics")
    t.set_defaults(fn=_topics)

    hp = sub.add_parser("health", help="show the active LLM provider, database, and search sources")
    hp.set_defaults(fn=_health)

    rc = sub.add_parser("record", help="invent + detail + score, then save to the database")
    rc.add_argument("topic")
    rc.add_argument("prompt", nargs="?", default="")
    rc.add_argument("--lens", default="biomimicry")
    rc.add_argument("--backend", default="auto", choices=["auto", "llm", "fallback"])
    rc.add_argument("--no-ground", dest="ground", action="store_false", help="skip the literature search (faster)")
    rc.add_argument("--model", default=None, help="override the LLM model (e.g. qwen2.5:3b) for this run")
    rc.add_argument("--constraint", default=None, choices=["noninvasive", "invasive"],
                    help="restrict the design: noninvasive (biomolecules) or invasive (electrodes)")
    rc.set_defaults(ground=True)
    rc.set_defaults(fn=_record)

    pg = sub.add_parser("ping", help="one tiny timed LLM call — is the model actually working & how fast?")
    pg.add_argument("--max-tokens", type=int, default=50, dest="max_tokens")
    pg.add_argument("--timeout", type=float, default=60.0, help="seconds to wait before giving up")
    pg.set_defaults(fn=_ping)

    sr = sub.add_parser("search", help="preview retrieved literature / prior art for a query")
    sr.add_argument("query")
    sr.set_defaults(fn=_search)

    bn = sub.add_parser("bench", help="sweep topics N times → pass-rate + mean-score leaderboard")
    bn.add_argument("--samples", type=int, default=3)
    bn.add_argument("--topic", default=None, help="one topic (default: all 10)")
    bn.add_argument("--prompt", default="")
    bn.add_argument("--backend", default="auto", choices=["auto", "llm", "fallback"])
    bn.add_argument("--ground", action="store_true", help="ground each attempt in literature (slower)")
    bn.add_argument("--save-attempts", action="store_true", help="also save every invention to the DB")
    bn.add_argument("--model", default=None, help="override the LLM model (e.g. qwen2.5:3b) for the whole sweep")
    bn.add_argument("--constraint", default=None, choices=["noninvasive", "invasive"],
                    help="restrict all designs: noninvasive (biomolecules) or invasive (electrodes)")
    bn.set_defaults(fn=_bench)

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
