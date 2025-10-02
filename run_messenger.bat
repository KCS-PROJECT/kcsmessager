@echo off
chcp 65001 >nul
title KCS Messenger

echo ================================================
echo    KCS Messenger 실행
echo ================================================
echo.

if exist "dist\KCS_Messenger.exe" (
    echo KCS Messenger를 시작합니다...
    echo.
    start "" "dist\KCS_Messenger.exe"
    echo 메신저가 실행되었습니다!
    timeout /t 3 >nul
) else (
    echo [오류] 실행파일을 찾을 수 없습니다!
    echo.
    echo dist\KCS_Messenger.exe 파일이 없습니다.
    echo.
    echo 해결 방법:
    echo   1. build_windows.bat을 먼저 실행하여 빌드하세요
    echo   2. 또는 build_windows.py를 실행하세요
    echo.
    pause
)