# Ensure we're at repo root if run from scripts\
Set-Location (Split-Path -Parent $PSScriptRoot)

# Activate venv
$venv = ".\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) {
  Write-Host "Virtual env not found. Run scripts\install.ps1 first." -ForegroundColor Yellow
  exit 1
}
. $venv

# Point to the GPU server via SSH tunnel on localhost:8000 by default
if (-not $env:GPT_OSS_SERVER) {
  $env:GPT_OSS_SERVER = "http://127.0.0.1:8000"
}

# Optional quick connectivity probe
python - << 'PY'
from gptoss_client import healthcheck
print("GPT-OSS: OK" if healthcheck() else "GPT-OSS: UNREACHABLE (start tunnel?)")
PY

# Run the GUI
python .\adhd_app_gui.py
