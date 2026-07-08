#!/usr/bin/env bash
# Brain-Computer-Interface v3 — run the API + cockpit from the repo ROOT (macOS / Linux).
#
#   ./serve.sh                 # → http://localhost:8000/app/
#   ./serve.sh --port 9000     # any bci-serve flag is passed through
#
# No need to cd into backend or activate the venv — this finds the venv for you.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/backend/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "venv not found. First-time setup:"
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[dev,plot,api,db]'"
  exit 1
fi
exec "$PY" -m bciv3.cli serve "$@"
