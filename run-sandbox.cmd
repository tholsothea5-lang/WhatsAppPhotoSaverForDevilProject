@echo off
rem Run WhatsApp Photo Saver in this DSH workspace sandbox (demo backend, no WhatsApp login).
rem Usage: double-click, or:  run-sandbox.cmd [port]
setlocal
cd /d "%~dp0"

rem Optional: set WPS_PYTHON to a specific python.exe before running.
rem Otherwise "python" from PATH is used.
set "PY=%WPS_PYTHON%"
if not "%PY%"=="" goto checkpy
set "PY=python"
:checkpy
"%PY%" -c "import sys" >nul 2>nul
if errorlevel 1 goto nopython

if exist ".pydeps\flask" goto run
echo Installing demo dependencies into .pydeps ...
set "PYTHONPATH=%CD%\.dshshim"
"%PY%" -m pip install --target "%CD%\.pydeps" --no-cache-dir --disable-pip-version-check --no-warn-script-location flask "qrcode[pil]" requests pillow
if errorlevel 1 goto pipfail

:run
set "PYTHONPATH=%CD%\.pydeps"
set "WPS_DATA=%CD%\.sandbox\data"
set "WPS_FOLDER=%CD%\.sandbox\downloads"
if not exist "%WPS_DATA%" mkdir "%WPS_DATA%"
if not exist "%WPS_FOLDER%" mkdir "%WPS_FOLDER%"

set "PORT=%~1"
if "%PORT%"=="" set "PORT=5000"
echo Starting demo server on http://127.0.0.1:%PORT%   (Ctrl+C to stop)
"%PY%" -u app.py --demo --no-browser --port %PORT%
pause
exit /b 0

:nopython
echo Python was not found.
echo   Set WPS_PYTHON to your python.exe, or add python to PATH.
pause
exit /b 1

:pipfail
echo pip install failed.
pause
exit /b 1
