@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Remote control is not installed yet. Starting the installer...
    call "INSTALL.bat"
    if errorlevel 1 exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m remote_control
