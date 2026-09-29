@echo off
title Cineforge Tray Launcher
echo.
echo ======================================================================
echo   Starting Cineforge System Tray App...
echo ======================================================================
echo.
echo   Launching backend, streamer bot, and Cloudflare tunnel in the background...
start "" "C:\Users\manuk\Downloads\projects\Cineforge\backend\.venv\Scripts\pythonw.exe" "C:\Users\manuk\Downloads\projects\Cineforge\tray_app.py"
echo.
echo   [OK] Cineforge is now active in your Windows System Tray (by the clock)!
echo        - Zero console windows (impossible to close accidentally).
echo        - Right-click the Cineforge tray icon to copy URL, open player, view logs, or stop.
echo.
echo   Closing this launcher window in 4 seconds...
timeout /t 4 >nul
