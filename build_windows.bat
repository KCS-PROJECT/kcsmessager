@echo off
chcp 65001 >nul
echo ================================================
echo    KCS Messenger Windows 빌드 도구
echo ================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되지 않았거나 PATH에 없습니다.
    echo.
    echo Python 3.8 이상을 설치해주세요:
    echo https://www.python.org/downloads/
    echo.
    echo 설치 시 "Add Python to PATH" 옵션을 체크하세요!
    pause
    exit /b 1
)

echo Python 설치 확인 완료!
echo.

REM Run the build script
echo KCS Messenger 실행파일 빌드를 시작합니다...
echo.
python build_windows.py --clean %*

if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패!
    echo 위의 오류 메시지를 확인하세요.
    pause
    exit /b 1
) else (
    echo.
    echo ================================================
    echo    빌드 완료!
    echo ================================================
    echo.
    echo 실행파일 위치: dist\KCS_Messenger.exe
    echo.
    echo 실행 방법:
    echo   1. dist 폴더에서 KCS_Messenger.exe 더블클릭
    echo   2. 또는 run_messenger.bat 실행
    echo.
    pause
)