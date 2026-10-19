@echo off
setlocal
cd /d "%~dp0"
title triageIQ launcher

if not exist ".venv\Scripts\uvicorn.exe" (
    echo [!] Python venv not found. Create it first:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r backend\requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [!] Frontend dependencies not found. Install them first:
    echo     cd frontend ^&^& npm install
    pause
    exit /b 1
)

echo Cleaning up any previous instances...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,8001,5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo Starting simulated service (port 8001)...
start "triageIQ simulator :8001" cmd /k ".venv\Scripts\uvicorn.exe simulator.service:app --port 8001 --app-dir backend"

echo Starting API + AI agent (port 8000)...
start "triageIQ api :8000" cmd /k ".venv\Scripts\uvicorn.exe main:app --port 8000 --app-dir backend"

echo Starting dashboard (port 5173)...
start "triageIQ frontend :5173" cmd /k "cd frontend && npm run dev"

echo Waiting for services to come up...
timeout /t 8 /nobreak >nul
start "" http://localhost:5173

echo.
echo  triageIQ is running:
echo    dashboard   http://localhost:5173
echo    api         http://localhost:8000/api/status
echo    simulator   http://localhost:8001/health
echo.
echo  Close the three service windows to stop, or just run this script again to restart everything.
echo.
pause
