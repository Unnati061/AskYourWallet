@echo off
setlocal

rem Always run from the backend directory so .env and the SQLite file resolve correctly.
cd /d "%~dp0"
set "SEED_DEMO="

if not exist ".venv\Scripts\python.exe" (
    echo Backend virtual environment is missing. See README.md for the one-time setup.
    exit /b 1
)

if not exist ".env" (
    echo backend\.env is missing. Copy backend\.env.example to backend\.env and set a development JWT secret.
    exit /b 1
)

if not exist "askyourwallet.db" set "SEED_DEMO=1"

".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 exit /b 1

if defined SEED_DEMO (
    ".venv\Scripts\python.exe" seed.py
    if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
exit /b %errorlevel%
