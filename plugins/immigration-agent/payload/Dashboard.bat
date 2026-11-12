@echo off
rem Immigration Agent Dashboard: opens in its own window and stops by itself after you close it.
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (start "" pythonw app\dashboard.py & exit /b 0)
where python3 >nul 2>nul
if %errorlevel%==0 (python3 app\dashboard.py) else (py -3 app\dashboard.py)
if errorlevel 1 pause
