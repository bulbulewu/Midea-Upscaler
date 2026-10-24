@echo off
if "%~1"=="run" goto main
cmd /k call "%~f0" run
exit /b

:main
title Stock Contributor Toolkit Pro
cd /d "%~dp0"
echo ============================================
echo  Stock Contributor Toolkit Pro - Launcher
echo  Folder: %cd%
echo ============================================
echo.
where python >nul 2>nul
if %errorlevel%==0 goto have_python
echo Python was NOT found on this PC.
echo Install it free from https://www.python.org/downloads/
echo IMPORTANT: during install tick "Add python.exe to PATH".
echo Also disable the Microsoft Store alias: Settings, search
echo "app execution aliases", turn OFF python.exe / python3.exe.
echo Then run this file again.
goto end

:have_python
python --version
if exist ".venv\Scripts\python.exe" goto venv_ok
echo Creating environment (first run only)...
python -m venv .venv
if exist ".venv\Scripts\python.exe" goto venv_ok
echo Failed to create the environment. Send a photo of this window to support.
goto end

:venv_ok
echo Installing / checking components (first run: a few minutes, needs internet)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %errorlevel%==0 goto deps_ok
echo Component install had a problem - check your internet and run again.
echo If it keeps failing, send a photo of this window.
goto end

:deps_ok
where ffmpeg >nul 2>nul
if %errorlevel%==0 goto start_app
echo.
echo NOTE: FFmpeg not found - video tools need it, other tools still work.
echo Install free later with:  winget install ffmpeg
echo.

:start_app
echo.
echo Starting... your browser should open at http://127.0.0.1:5000
echo If it does not, open that address manually.
echo KEEP THIS WINDOW OPEN while using the app. Ctrl+C stops it.
echo.
".venv\Scripts\python.exe" app.py
echo.
echo The app has stopped (message above explains why, if it was an error).

:end
echo.
pause
