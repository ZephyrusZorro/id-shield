@echo off
rem ============================================================
rem  ID-SHIELD - one-click local/offline launcher
rem  Starts the server and opens the app in your browser.
rem ============================================================
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [ID-SHIELD] Python environment not found.
    echo             Run the setup first:
    echo             powershell -ExecutionPolicy Bypass -File "%ROOT%scripts\setup_offline.ps1"
    pause
    exit /b 1
)

echo [ID-SHIELD] Starting server on http://localhost:8000 ...
echo             Close this window to stop the app.
start "" http://localhost:8000

cd /d "%ROOT%backend"
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
