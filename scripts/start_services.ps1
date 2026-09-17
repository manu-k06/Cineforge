# Cineforge Multi-Service Launcher (Go Streamer + FastAPI Backend)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Starting Cineforge Full Stack (Streamer + Backend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Start Go Streamer
Write-Host "[1/2] Starting Go Streamer on http://127.0.0.1:8088..." -ForegroundColor Yellow
$StreamerDir = Join-Path $Root "streamer"
$StreamerProc = Start-Process -FilePath (Join-Path $StreamerDir "streamer.exe") -WorkingDirectory $StreamerDir -PassThru

# Wait briefly for streamer to bind
Start-Sleep -Seconds 2

# 2. Start FastAPI Backend
Write-Host "[2/2] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Yellow
$BackendDir = Join-Path $Root "backend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"

& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
