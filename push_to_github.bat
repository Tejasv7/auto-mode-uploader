@echo off
title Push to GitHub (Tejasv7/auto-mode-uploader)
echo ========================================================
echo   Pushing code to GitHub for 24/7 Cloud Autopilot...
echo ========================================================
cd /d "%~dp0"
git push -u origin main
echo ========================================================
echo   Done! Press any key to exit.
echo ========================================================
pause
