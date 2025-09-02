@echo off
setlocal enabledelayedexpansion
echo =====================================
echo   KCS Messenger - KakaoTalk Clone
echo   [Organized Version]
echo =====================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

echo [1] Standalone Chat (No Server Required) [RECOMMENDED]
echo [2] Real-Time Chat (Start Server + Client)
echo [3] Chat Launcher GUI (Manage Multiple Windows)
echo [4] Start Chat Server Only
echo [5] Start Chat Client Only
echo [6] Test & Utilities
echo [7] Install Dependencies
echo [8] Exit
echo.

set /p choice="Select option (1-8): "

if "%choice%"=="1" (
    echo Starting Standalone KakaoTalk Chat...
    python client\standalone\standalone_chat.py
) else if "%choice%"=="2" (
    echo Starting Real-Time Chat System...
    echo.
    echo [1/2] Starting server...
    start "Chat Server" python server\chat\chat_server.py
    timeout /t 2 /nobreak >nul
    echo [2/2] Starting chat client...
    python client\realtime\chat_client.py
) else if "%choice%"=="3" (
    echo Starting Chat Launcher GUI...
    python client\launcher\chat_launcher.py
) else if "%choice%"=="4" (
    echo Starting Chat Server Only...
    python server\chat\chat_server.py
) else if "%choice%"=="5" (
    echo Starting Chat Client Only...
    echo Make sure the server is running first!
    timeout /t 2 /nobreak >nul
    python client\realtime\chat_client.py
) else if "%choice%"=="6" (
    echo.
    echo Test & Utilities:
    echo [A] Test Installation
    echo [B] Test All Versions
    echo [C] View Project Structure
    echo.
    set /p ver="Select (A-C): "
    if /i "!ver!"=="A" python tests\test_installation.py
    if /i "!ver!"=="B" python tests\test_all_versions.py
    if /i "!ver!"=="C" type PROJECT_STRUCTURE_NEW.md
    pause
) else if "%choice%"=="7" (
    echo Installing Dependencies...
    pip install PyQt5 python-socketio aiohttp --user
    echo.
    echo Installation complete!
    pause
) else if "%choice%"=="8" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid option!
    pause
)