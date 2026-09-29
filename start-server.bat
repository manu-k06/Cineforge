@echo off
title Cineforge Local Server, Streamer Bot and Cloudflare Tunnel

:: Kill any existing uvicorn, fsb, ngrok, or cloudflared
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8088" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
taskkill /f /im fsb.exe >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1
taskkill /f /im cloudflared.exe >nul 2>&1

echo 1. Starting Go TG-FileStreamBot on port 8088...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\TG-FileStreamBot"
start "TG-FileStreamBot" /min "C:\Users\manuk\Downloads\projects\Cineforge\TG-FileStreamBot\fsb.exe" run

ping -n 3 127.0.0.1 >nul

echo 2. Starting Cineforge FastAPI Backend on port 8000...
cd /d "C:\Users\manuk\Downloads\projects\Cineforge\backend"
start "Cineforge Backend" /min "C:\Users\manuk\Downloads\projects\Cineforge\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

ping -n 4 127.0.0.1 >nul

echo 3. Starting Cloudflare Tunnel (Unlimited streaming bandwidth, zero warning interstitials)...
del /f /q "%TEMP%\cloudflared_cineforge.log" >nul 2>&1
start "Cloudflare Tunnel" /min "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000 --logfile "%TEMP%\cloudflared_cineforge.log"

:: Wait up to 15 seconds for Cloudflare tunnel URL to establish
set "TUNNEL_URL="
for /l %%i in (1,1,14) do (
    if not defined TUNNEL_URL (
        ping -n 2 127.0.0.1 >nul
        for /f "usebackq tokens=*" %%u in (`powershell -NoProfile -Command "(Get-Content -Path $env:TEMP\cloudflared_cineforge.log -ErrorAction SilentlyContinue | Select-String -Pattern 'https://[a-zA-Z0-9\.-]+\.trycloudflare\.com' | ForEach-Object { $_.Matches[0].Value } | Select-Object -First 1)"`) do (
            set "TUNNEL_URL=%%u"
        )
    )
)

if defined TUNNEL_URL (
    powershell -NoProfile -Command "(Get-Content 'C:\Users\manuk\Downloads\projects\Cineforge\TG-FileStreamBot\fsb.env') -replace '^HOST=.*', 'HOST=%TUNNEL_URL%' | Set-Content 'C:\Users\manuk\Downloads\projects\Cineforge\TG-FileStreamBot\fsb.env'"
    echo.
    echo 4. Publishing live tunnel URL to Supabase server_status...
    cd /d "C:\Users\manuk\Downloads\projects\Cineforge\backend"
    call "C:\Users\manuk\Downloads\projects\Cineforge\backend\.venv\Scripts\python.exe" -m app.services.publish_tunnel --url %TUNNEL_URL%
) else (
    echo.
    echo [Notice] Tunnel URL is still warming up in background (check %%TEMP%%\cloudflared_cineforge.log).
)

echo.
echo ======================================================================
echo   Cineforge Local Server, Streamer Bot, and Tunnel are now LIVE!
echo ======================================================================
if defined TUNNEL_URL (
    echo   * Cloudflare Tunnel : %TUNNEL_URL%
    echo   * Frontend Sync     : Auto-discovered via Supabase (Zero Vercel config!)
) else (
    echo   * Cloudflare Tunnel : Starting in background... check %%TEMP%%\cloudflared_cineforge.log
)
echo   * Web Player        : https://cineforge-v1.vercel.app
echo   * Local API         : http://127.0.0.1:8000/health
echo   * Streamer Bot      : http://127.0.0.1:8088/
echo ======================================================================
ping -n 6 127.0.0.1 >nul
