@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Remote control - always listening

if not exist ".venv\Scripts\remote-control.exe" (
    echo Remote control is not installed yet. Starting the installer...
    call "INSTALL.bat"
    if errorlevel 1 exit /b 1
)

echo.
echo Always-listening mode is active. Press Ctrl+C to stop.
echo.
".venv\Scripts\remote-control.exe" --mode always

if errorlevel 1 (
    echo.
    echo Remote control stopped with an error. See the message above.
    pause
)
