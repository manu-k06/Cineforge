@echo off
echo Stopping Cineforge server and Ngrok tunnel...
taskkill /f /im ngrok.exe >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
echo Cineforge services stopped successfully.
