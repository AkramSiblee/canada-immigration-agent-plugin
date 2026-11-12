@echo off
title Immigration Agent Dashboard - close this window to stop it
cd /d "%~dp0"
where python3 >nul 2>nul
if %errorlevel%==0 (python3 app\dashboard.py) else (py -3 app\dashboard.py)
if errorlevel 1 pause
