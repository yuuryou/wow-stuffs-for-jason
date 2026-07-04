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

:: Detect and display local IP for network access
for /f %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*Wi-Fi*' -PrefixOrigin Dhcp | Select-Object -First 1).IPAddress" 2^>nul') do set LOCAL_IP=%%i

:: For devs who prefer ipconfig, also try: for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4" ^| findstr /v "192.168.56"') do ...

echo.
if not "%LOCAL_IP%"=="" (
    echo   ✅ Local network access: http://%LOCAL_IP%:5050
) else (
    echo   ⚠️  Could not detect local IP — run "ipconfig" to find it.
)
echo   🌐 Local access: http://localhost:5050
echo   📱 Other devices on same WiFi: use the "Local network access" URL above
echo   🔥 If other devices can't connect, check Windows Firewall:
echo      "Python" or "python.exe" needs to be allowed on Private networks.
echo.

:: Install dependencies
echo [1/2] Installing dependencies...
pip install -r requirements.txt -q

:: Initialize & Run
echo [2/2] Starting server...
echo.
python app.py

pause
