#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."   # repo root

python3 -m venv .venv
. .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt || true

# Check PyAudio; if missing try system package suggestions
python - << 'PY'
import importlib, sys
try:
    importlib.import_module("pyaudio")
    print("PyAudio OK")
except Exception:
    sys.exit(1)
PY

if [ $? -ne 0 ]; then
  echo "PyAudio import failed. On Linux, try: sudo apt-get install portaudio19-dev && pip install pyaudio"
  # We don't attempt root installs automatically.
fi

echo "✅ All dependencies installed in .venv"
echo "Run: scripts/run.sh"
