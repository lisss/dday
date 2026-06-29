#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "API  → http://127.0.0.1:8000  (hot reload)"
uvicorn api.index:app \
  --reload \
  --reload-dir api \
  --reload-dir data \
  --host 127.0.0.1 \
  --port 8000 &
API_PID=$!

cd frontend
npm install --silent

echo "App  → http://localhost:5173  (hot reload)"
exec npm run dev
