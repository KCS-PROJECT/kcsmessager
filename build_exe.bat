@echo off
echo ========================================
echo KCS Messenger Executable Builder
echo ========================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Run the build script
echo.
echo Building KCS Messenger executable...
python build_exe.py %*

if errorlevel 1 (
    echo.
    echo Build failed!
    pause
    exit /b 1
) else (
    echo.
    echo Build complete!
    echo.
    echo The executable can be found in:
    echo   dist\KCS_Messenger.exe
    echo.
    echo You can run it by double-clicking the exe file
    echo or from command line: dist\KCS_Messenger.exe
    echo.
    pause
)