@echo off
echo =====================================
echo   KakaoTalk Messenger - Standalone
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

REM Check PyQt5 installation
python -c "import PyQt5" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] PyQt5 is not installed. Installing now...
    pip install PyQt5 --user
    echo.
)

echo Starting KakaoTalk Messenger...
echo.
python kakaotalk_standalone.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start the application
    echo.
    echo Possible solutions:
    echo 1. Install PyQt5: pip install PyQt5
    echo 2. Check Python version: python --version
    echo 3. Try running directly: python kakaotalk_standalone.py
    echo.
    pause
)