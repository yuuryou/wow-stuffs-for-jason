@echo off
title WoW Douyin Hub - Feral Druid Edition
cd /d "%~dp0"

echo.
echo   🐾 WoW Douyin Hub - Feral Druid Edition
echo   ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    pause
    exit /b 1
)

:: Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt -q

:: Initialize & Run
echo [2/2] Starting server...
echo.
python app.py

pause
