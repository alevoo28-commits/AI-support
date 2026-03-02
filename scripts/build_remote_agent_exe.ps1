# Build a standalone Windows .exe for the Remote Agent (no Python required on client PCs).
# Run this on a build machine (dev PC/CI) where Python is available.

param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Building Remote Agent EXE..."
Write-Host "ProjectRoot: $ProjectRoot"

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  throw "No venv python found at $python. Create venv and install requirements first."
}

Push-Location $ProjectRoot
try {
  & $python -m pip install --upgrade pip
  # PyInstaller is build-time only
  & $python -m pip install --upgrade pyinstaller

  # Build
  & $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "AI-Support-RemoteAgent" `
    --hidden-import "fastapi" `
    --hidden-import "uvicorn" `
    --hidden-import "starlette" `
    "ai_support/remote_agent/run_agent.py"

  Write-Host "Done. EXE is under dist/AI-Support-RemoteAgent.exe"
}
finally {
  Pop-Location
}
