@echo off
title Cineforge Local Server & Ngrok Tunnel

:: Kill any existing uvicorn/ngrok on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1

echo Starting Cineforge FastAPI Backend on port 8000...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\backend"
start "Cineforge Backend" /min ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

:: Reliable 3-second delay without input redirection errors
ping -n 4 127.0.0.1 >nul

echo Starting Ngrok Tunnel for https://oxidize-dandelion-outmost.ngrok-free.dev...
start "Ngrok Tunnel" /min ngrok http 8000 --url=oxidize-dandelion-outmost.ngrok-free.dev

echo Cineforge is live at: https://oxidize-dandelion-outmost.ngrok-free.dev
