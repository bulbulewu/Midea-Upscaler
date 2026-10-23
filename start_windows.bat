@echo off
title Media Toolkit Pro V3 — Made By Munajat International
cd /d "%~dp0"

echo ========================================================
echo   Media Toolkit Pro V3 — Multi-Marketplace Studio
echo   Made By Munajat International
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [Setup] Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo [Setup] Installing dependencies...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo [Launch] Starting Media Toolkit Pro V3 server...
python app.py
pause
