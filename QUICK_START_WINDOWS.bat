@echo off
chcp 65001 >nul
cls
echo ====================================================
echo    KCS Messenger - Windows 빠른 시작 가이드
echo ====================================================
echo.
echo 이 스크립트는 KCS Messenger를 자동으로 빌드하고
echo 실행합니다.
echo.
echo 필요사항: Python 3.8 이상이 설치되어 있어야 합니다.
echo.
pause

echo.
echo [1/2] 빌드 시작...
echo ====================================================
call build_windows.bat --clean

if errorlevel 1 (
    echo.
    echo ====================================================
    echo    빌드 실패 - Python이 설치되어 있는지 확인하세요
    echo ====================================================
    echo.
    echo Python 다운로드: https://www.python.org/downloads/
    echo (설치 시 "Add Python to PATH" 체크 필수!)
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] 프로그램 실행...
echo ====================================================
timeout /t 2 >nul
call run_messenger.bat

echo.
echo ====================================================
echo    완료!
echo ====================================================
echo.
echo KCS Messenger가 실행되었습니다.
echo 다음부터는 run_messenger.bat을 실행하거나
echo dist\KCS_Messenger.exe를 직접 실행하세요.
echo.
pause