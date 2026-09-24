@echo off
title Cineforge Local Server & Ngrok Tunnel

:: Kill any existing uvicorn/ngrok on port 8000 first
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1

echo Starting Cineforge FastAPI Backend on port 8000...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\backend"
start "Cineforge Backend" /min ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak >nul

echo Starting Ngrok Tunnel for https://oxidize-dandelion-outmost.ngrok-free.dev...
start "Ngrok Tunnel" /min ngrok http --url=oxidize-dandelion-outmost.ngrok-free.dev 8000

echo Cineforge is live at: https://oxidize-dandelion-outmost.ngrok-free.dev
