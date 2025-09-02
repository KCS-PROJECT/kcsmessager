@echo off
echo =====================================
echo   KakaoTalk Real Chat System
echo   실시간 채팅 시스템
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

echo 실행 옵션을 선택하세요:
echo.
echo [1] 런처 실행 (권장) - GUI로 서버와 클라이언트 관리
echo [2] 서버만 실행
echo [3] 클라이언트만 실행
echo [4] 서버 + 2개 클라이언트 동시 실행
echo.

set /p choice="선택 (1-4): "

if "%choice%"=="1" (
    echo.
    echo 런처를 시작합니다...
    echo.
    start python launch_real_chat.py
) else if "%choice%"=="2" (
    echo.
    echo 서버를 시작합니다...
    echo.
    start python simple_chat_server.py
    echo.
    echo 서버가 시작되었습니다. 별도로 클라이언트를 실행하세요.
    pause
) else if "%choice%"=="3" (
    echo.
    echo 클라이언트를 시작합니다...
    echo.
    start python kakaotalk_real_chat.py
) else if "%choice%"=="4" (
    echo.
    echo 서버를 시작합니다...
    start python simple_chat_server.py
    
    echo 2초 대기 중...
    timeout /t 2 /nobreak >nul
    
    echo 첫 번째 클라이언트를 시작합니다...
    start python kakaotalk_real_chat.py
    
    echo 1초 대기 중...
    timeout /t 1 /nobreak >nul
    
    echo 두 번째 클라이언트를 시작합니다...
    start python kakaotalk_real_chat.py
    
    echo.
    echo 서버와 2개의 클라이언트가 시작되었습니다!
    echo 각 창에서 다른 이름으로 로그인하여 대화를 시작하세요.
    echo.
    pause
) else (
    echo 잘못된 선택입니다.
    pause
)