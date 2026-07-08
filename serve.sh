#!/usr/bin/env bash
# Brain-Computer-Interface v3 — run the API + cockpit from the repo ROOT (macOS / Linux).
#
#   ./serve.sh                 # → http://localhost:8000/app/
#   ./serve.sh --port 9000     # any bci-serve flag is passed through
#
# No need to cd into backend or activate the venv — this finds the venv for you.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Look for the venv at the repo root (.venv) first, then backend/.venv — either layout works.
PY=""
for cand in "$DIR/.venv/bin/python" "$DIR/backend/.venv/bin/python"; do
  if [ -x "$cand" ]; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "venv not found. First-time setup (from the repo root):"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e 'backend[api,db]'"
  exit 1
fi
exec "$PY" -m bciv3.cli serve "$@"
