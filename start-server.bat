@echo off
title Cineforge Local Server, Streamer Bot and Ngrok Tunnel

:: Kill any existing uvicorn, fsb, or ngrok
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8088" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
taskkill /f /im fsb.exe >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1

echo 1. Starting Go TG-FileStreamBot on port 8088...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\TG-FileStreamBot"
start "TG-FileStreamBot" /min "C:\Users\manuk\Downloads\projects\Cineforge\TG-FileStreamBot\fsb.exe" run

ping -n 3 127.0.0.1 >nul

echo 2. Starting Cineforge FastAPI Backend on port 8000...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\backend"
start "Cineforge Backend" /min "C:\Users\manuk\Downloads\projects\Cineforge\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

ping -n 4 127.0.0.1 >nul

echo 3. Starting Ngrok Tunnel for https://oxidize-dandelion-outmost.ngrok-free.dev...
start "Ngrok Tunnel" /min ngrok http 8000 --url=oxidize-dandelion-outmost.ngrok-free.dev

echo Cineforge and Streamer Bot are live at: https://oxidize-dandelion-outmost.ngrok-free.dev
