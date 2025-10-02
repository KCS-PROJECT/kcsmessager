@echo off
chcp 65001 >nul
echo ====================================================
echo    KCS Messenger 배포 패키지 생성기
echo ====================================================
echo.

REM 버전 설정
set VERSION=1.0
set DIST_NAME=KCS_Messenger_v%VERSION%
set DIST_DIR=%DIST_NAME%_Windows

REM 기존 배포 폴더 삭제
if exist %DIST_DIR% (
    echo 기존 배포 폴더 삭제 중...
    rmdir /s /q %DIST_DIR%
)

REM 배포 폴더 생성
echo 배포 폴더 생성: %DIST_DIR%
mkdir %DIST_DIR%

REM exe 파일 확인 및 복사
if not exist "dist\KCS_Messenger.exe" (
    echo.
    echo [오류] exe 파일을 찾을 수 없습니다!
    echo 먼저 build_windows.bat을 실행하여 빌드하세요.
    echo.
    pause
    exit /b 1
)

echo.
echo [1/4] exe 파일 복사 중...
copy "dist\KCS_Messenger.exe" "%DIST_DIR%\" >nul
echo   ✓ KCS_Messenger.exe 복사 완료

REM 실행 스크립트 생성
echo.
echo [2/4] 실행 스크립트 생성 중...
(
echo @echo off
echo chcp 65001 ^>nul
echo title KCS Messenger
echo start "" "KCS_Messenger.exe"
) > "%DIST_DIR%\실행하기.bat"
echo   ✓ 실행하기.bat 생성 완료

REM README 파일 생성
echo.
echo [3/4] 사용자 가이드 생성 중...
(
echo ====================================================
echo    KCS Messenger v%VERSION% - 카카오톡 스타일 메신저
echo ====================================================
echo.
echo [빠른 시작]
echo   1. KCS_Messenger.exe 더블클릭
echo   2. 또는 "실행하기.bat" 더블클릭
echo.
echo [기능]
echo   ✓ 실시간 채팅
echo   ✓ 독립 실행 모드
echo   ✓ 카카오톡 스타일 UI
echo   ✓ 한글 완벽 지원
echo.
echo [시스템 요구사항]
echo   - Windows 10 이상
echo   - 메모리: 최소 2GB RAM
echo   - 저장공간: 100MB
echo   - Python 설치 불필요!
echo.
echo [실행 방법]
echo   방법 1: KCS_Messenger.exe 더블클릭
echo   방법 2: "실행하기.bat" 더블클릭
echo.
echo [첫 실행 시 Windows Defender 경고]
echo   1. "Windows의 PC 보호" 창이 나타나면
echo   2. "추가 정보" 클릭
echo   3. "실행" 버튼 클릭
echo.
echo   이 경고는 서명되지 않은 앱에 대한 일반적인 경고입니다.
echo   프로그램은 안전하며 악성코드가 없습니다.
echo.
echo [문제 해결]
echo   Q: 프로그램이 실행되지 않아요
echo   A: Visual C++ 재배포 가능 패키지를 설치하세요
echo      다운로드: https://aka.ms/vs/17/release/vc_redist.x64.exe
echo.
echo   Q: 한글이 깨져 보여요
echo   A: Windows 지역 설정을 확인하세요
echo      설정 ^> 시간 및 언어 ^> 언어 ^> 한국어
echo.
echo [기능 설명]
echo   • 실시간 채팅: 서버를 시작하여 여러 클라이언트 연결
echo   • 독립 모드: 서버 없이 단독으로 채팅 테스트
echo   • 카카오톡 UI: 친숙한 카카오톡 스타일 인터페이스
echo.
echo [지원 및 문의]
echo   GitHub: https://github.com/your-repo/kcsmessager
echo   이메일: support@example.com
echo.
echo [라이선스]
echo   이 소프트웨어는 교육 및 개인 사용 목적으로 제공됩니다.
echo.
echo [버전 정보]
echo   버전: v%VERSION%
echo   빌드 날짜: %date% %time%
echo   플랫폼: Windows 10/11
echo ====================================================
) > "%DIST_DIR%\README.txt"
echo   ✓ README.txt 생성 완료

REM ZIP 압축 (PowerShell 사용)
echo.
echo [4/4] ZIP 파일 생성 중...

REM PowerShell로 압축
powershell -command "Compress-Archive -Path '%DIST_DIR%' -DestinationPath '%DIST_NAME%.zip' -Force"

if exist "%DIST_NAME%.zip" (
    echo   ✓ %DIST_NAME%.zip 생성 완료
) else (
    echo   ⚠️  ZIP 생성 실패 - PowerShell을 사용할 수 없습니다
)

echo.
echo ====================================================
echo    배포 패키지 생성 완료!
echo ====================================================
echo.
echo 생성된 파일:
echo   📁 폴더: %DIST_DIR%\
echo      ├── KCS_Messenger.exe
echo      ├── 실행하기.bat
echo      └── README.txt
echo.

if exist "%DIST_NAME%.zip" (
    echo   📦 압축: %DIST_NAME%.zip
    for %%A in ("%DIST_NAME%.zip") do echo      크기: %%~zA bytes
    echo.
)

echo.
echo 다음 단계:
echo   1. %DIST_DIR% 폴더를 사용자에게 배포
echo   2. 또는 %DIST_NAME%.zip 파일을 배포
echo   3. GitHub Releases 또는 클라우드에 업로드
echo.
echo 사용자는 다운로드 후:
echo   - 압축 해제
echo   - KCS_Messenger.exe 또는 "실행하기.bat" 실행
echo.
pause