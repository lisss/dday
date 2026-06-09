#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

source venv/bin/activate
python - <<'PY'
import asyncio
from api.data_fetcher import refresh_all_countries

result = asyncio.run(refresh_all_countries())
print(result)
PY
