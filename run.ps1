# Starts the API and the UI together. Ctrl+C in each window to stop.
#   .\run.ps1
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$root\backend'; python -m uvicorn app.main:app --reload --port 8000"
)
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "Set-Location '$root\frontend'; npm run dev"
)

Write-Host 'API  -> http://127.0.0.1:8000/api/health'
Write-Host 'UI   -> http://localhost:5173'
