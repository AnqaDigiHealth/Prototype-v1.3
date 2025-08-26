#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

. .venv/bin/activate

export GPT_OSS_SERVER="${GPT_OSS_SERVER:-http://127.0.0.1:8000}"

python - << 'PY'
from gptoss_client import healthcheck
print("GPT-OSS: OK" if healthcheck() else "GPT-OSS: UNREACHABLE (start tunnel?)")
PY

python adhd_app_gui.py
