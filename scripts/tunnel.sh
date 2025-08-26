#!/usr/bin/env bash
set -euo pipefail
SERVER="${1:-chat.anqa.cloud}"
USER="${2:-anqa}"
PORT="${3:-8000}"

echo "Opening SSH tunnel $PORT -> $SERVER:127.0.0.1:$PORT"
echo "Enter password when prompted. KEEP THIS WINDOW OPEN."
ssh -N -L "${PORT}:127.0.0.1:${PORT}" "${USER}@${SERVER}"
