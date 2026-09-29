@echo off
title Stopping Cineforge Services...
echo 1. Marking Cineforge server offline in Supabase...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\backend"
call "C:\Users\manuk\Downloads\projects\Cineforge\backend\.venv\Scripts\python.exe" -m app.services.publish_tunnel --offline >nul 2>&1

echo 2. Stopping Cineforge server, Streamer Bot, Cloudflare tunnel, and Tray App...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*tray_app.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1
taskkill /f /im cloudflared.exe >nul 2>&1
taskkill /f /im fsb.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8088" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo All Cineforge services stopped successfully.
