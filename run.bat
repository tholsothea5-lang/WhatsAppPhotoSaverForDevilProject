@echo off
cd /d "%~dp0"
if not exist venv (
  python -m venv venv || (echo Install Python 3.10+ from python.org first & pause & exit /b 1)
  call venv\Scripts\activate
  pip install -r requirements.txt
  playwright install chromium
) else (
  call venv\Scripts\activate
)
python app.py %*
pause
