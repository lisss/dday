#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
exec uvicorn api.index:app \
  --reload \
  --reload-dir api \
  --reload-dir data \
  --host 127.0.0.1 \
  --port 8000
