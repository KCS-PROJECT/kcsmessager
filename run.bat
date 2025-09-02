@echo off
setlocal enabledelayedexpansion
echo =====================================
echo   KCS Messenger - KakaoTalk Clone
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

echo [1] KakaoTalk 통합 런처 [RECOMMENDED - 모든 기능 포함]
echo [2] 스마트 진입점 (자동 최적 런처 선택)
echo [3] Test & Utilities
echo [4] Install Dependencies
echo [5] Exit
echo.

set /p choice="Select option (1-5): "

if "%choice%"=="1" (
    echo Starting KakaoTalk 통합 런처...
    python kakaotalk_launcher_unified.py
) else if "%choice%"=="2" (
    echo Starting 스마트 진입점...
    python launch_real_chat.py
) else if "%choice%"=="3" (
    echo.
    echo Test & Utilities:
    echo [A] Test Installation
    echo [B] Test All Versions
    echo [C] Test Real Chat Fixes
    echo [D] View Project Structure
    echo.
    set /p ver="Select (A-D): "
    if /i "!ver!"=="A" python test_installation.py
    if /i "!ver!"=="B" python test_all_versions.py
    if /i "!ver!"=="C" python test_real_chat_fixes.py
    if /i "!ver!"=="D" type PROJECT_STRUCTURE_NEW.md
    pause
) else if "%choice%"=="4" (
    echo Installing Dependencies...
    pip install PyQt5 python-socketio aiohttp --user
    echo.
    echo Installation complete!
    pause
) else if "%choice%"=="5" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid option!
    pause
)