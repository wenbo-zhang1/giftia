@echo off
title Giftia - AI Companion

echo ============================================
echo    Giftia - One-Click Start
echo ============================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo [ERROR] .env not found. Run: copy .env.example .env
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node.js 18+
    pause
    exit /b 1
)

echo [1/4] Checking Python dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing Python dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Python dependencies
        pause
        exit /b 1
    )
) else (
    echo       Python dependencies OK
)

echo [2/4] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo       Installing frontend dependencies...
    cd /d "%~dp0frontend" && npm install && cd /d "%~dp0"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend dependencies
        pause
        exit /b 1
    )
) else (
    echo       Frontend dependencies OK
)

echo [3/4] Starting backend on port 8000...
start "Giftia Backend" /d "%~dp0backend" cmd /k python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

echo [4/4] Starting frontend on port 3000...
start "Giftia Frontend" /d "%~dp0frontend" cmd /k npm run dev

echo.
echo ============================================
echo    Started!
echo    Backend:  http://127.0.0.1:8000
echo    Frontend: http://localhost:3000
echo ============================================
echo.
echo Closing this window won't stop services.
echo Close the Backend/Frontend windows to stop.
pause
