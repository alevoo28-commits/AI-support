# Build a standalone Windows .exe for the Remote Poller client (no Python required on client PCs).
# This poller connects OUT to the server Remote Control API and executes jobs locally.
# Run this on a build machine (dev PC/CI) where Python is available.

param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Building Remote Poller EXE..."
Write-Host "ProjectRoot: $ProjectRoot"

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  throw "No venv python found at $python. Create venv and install requirement.txt first."
}

Push-Location $ProjectRoot
try {
  & $python -m pip install --upgrade pip
  # PyInstaller is build-time only
  & $python -m pip install --upgrade pyinstaller

  & $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "AI-Support-RemotePoller" `
    --hidden-import "requests" `
    "ai_support/remote_agent/run_poller.py"

  Write-Host "Done. EXE is under dist/AI-Support-RemotePoller.exe"
}
finally {
  Pop-Location
}
