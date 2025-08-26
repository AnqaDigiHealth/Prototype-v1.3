param(
  [string]$Python = "python",
  [string]$VenvPath = ".\.venv"
)

Write-Host "==> Creating virtual environment at $VenvPath"
& $Python -m venv $VenvPath

$pip = Join-Path $VenvPath "Scripts\pip.exe"
$pythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "==> Upgrading pip"
& $pythonExe -m pip install --upgrade pip

Write-Host "==> Installing requirements (this may take a few minutes)"
& $pip install -r ".\requirements.txt"

# PyAudio fallback (Windows)
try {
  Write-Host "==> Verifying PyAudio import..."
  & $pythonExe - << 'PY'
import importlib, sys
try:
    importlib.import_module("pyaudio")
    print("PyAudio OK")
except Exception as e:
    sys.exit(1)
PY
} catch {
  Write-Host "PyAudio import failed. Trying pipwin fallback..."
  & $pip install pipwin
  & $pythonExe -m pipwin install pyaudio
}

Write-Host "`n✅ All dependencies installed in $VenvPath"
Write-Host "To run: scripts\run.ps1"
