@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Remote control - F8 push-to-talk

if not exist ".venv\Scripts\remote-control.exe" (
    echo Remote control is not installed yet. Starting the installer...
    call "INSTALL.bat"
    if errorlevel 1 exit /b 1
)

echo.
echo Hold F8 while speaking, then release F8.
echo Close this window or say "quit remote control" to stop.
echo.
".venv\Scripts\remote-control.exe" --mode f8

if errorlevel 1 (
    echo.
    echo Remote control stopped with an error. See the message above.
    pause
)
