@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Remote control - installer

echo.
echo ========================================
echo   Remote control - Windows installer
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 goto :try_python_command

py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 goto :use_python_312
py -3.11 -c "import sys" >nul 2>nul
if not errorlevel 1 goto :use_python_311
py -3.10 -c "import sys" >nul 2>nul
if not errorlevel 1 goto :use_python_310
py -3.9 -c "import sys" >nul 2>nul
if not errorlevel 1 goto :use_python_39
goto :try_python_command

:use_python_312
set "PYTHON_COMMAND=py -3.12"
goto :python_ready

:use_python_311
set "PYTHON_COMMAND=py -3.11"
goto :python_ready

:use_python_310
set "PYTHON_COMMAND=py -3.10"
goto :python_ready

:use_python_39
set "PYTHON_COMMAND=py -3.9"
goto :python_ready

:try_python_command
where python >nul 2>nul
if errorlevel 1 goto :python_missing
set "PYTHON_COMMAND=python"
goto :python_ready

:python_ready
%PYTHON_COMMAND% -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 9), (3, 10), (3, 11), (3, 12)) else 1)"
if errorlevel 1 goto :python_unsupported

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating the private Python environment...
    %PYTHON_COMMAND% -m venv ".venv"
    if errorlevel 1 goto :failed
) else (
    echo [1/4] Python environment already exists.
)

echo [2/4] Updating the installer tools...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto :failed

echo [3/4] Installing Remote control and its free dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -e .
if errorlevel 1 goto :failed

echo [4/4] Installing the offline voice and webcam models...
".venv\Scripts\python.exe" "scripts\download_model.py"
if errorlevel 1 goto :failed

echo.
echo ========================================
echo   Installation completed successfully.
echo ========================================
echo.
echo Double-click START.bat to use push-to-talk.
echo Double-click START_ALWAYS_LISTENING.bat for continuous listening.
echo.
pause
exit /b 0

:python_missing
echo Python was not found on this computer.
echo.
echo Install 64-bit Python 3.9 through 3.12 from:
echo https://www.python.org/downloads/windows/
echo.
echo IMPORTANT: select "Add Python to PATH" in the Python installer.
echo Then double-click INSTALL.bat again.
echo.
pause
exit /b 2

:python_unsupported
echo The installed Python version is not supported by this prototype.
echo.
echo Install 64-bit Python 3.9 through 3.12 from:
echo https://www.python.org/downloads/windows/
echo.
echo Python 3.12 is recommended. Then double-click INSTALL.bat again.
echo.
pause
exit /b 2

:failed
echo.
echo Installation stopped because a step failed.
echo Check the error above, confirm that the internet is available for the
echo first installation, and then double-click INSTALL.bat again.
echo.
pause
exit /b 1
