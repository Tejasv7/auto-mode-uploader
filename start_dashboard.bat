@echo off
title Auto-Mode Uploader Studio Dashboard
echo ========================================================
echo   Starting Auto-Mode Uploader AI Studio Web UI...
echo ========================================================
cd /d "%~dp0"
call venv\Scripts\activate.bat
start http://localhost:5000
python web_server.py
pause
