@echo off
chcp 65001 >nul
echo ====================================================
echo    KCS Messenger 설치 프로그램 생성기
echo ====================================================
echo.

REM NSIS 확인
where makensis >nul 2>&1
if %errorlevel% neq 0 (
    echo [알림] NSIS가 설치되지 않았습니다.
    echo.
    echo NSIS는 Windows 설치 프로그램을 만드는 도구입니다.
    echo.
    echo 다운로드: https://nsis.sourceforge.io/Download
    echo.
    echo NSIS를 설치하지 않으려면:
    echo   - prepare_distribution.bat을 사용하여 ZIP 배포
    echo   - 또는 exe 파일을 직접 배포
    echo.
    pause
    exit /b 1
)

REM exe 파일 확인
if not exist "dist\KCS_Messenger.exe" (
    echo [오류] dist\KCS_Messenger.exe 파일이 없습니다.
    echo 먼저 build_windows.bat을 실행하세요.
    echo.
    pause
    exit /b 1
)

REM NSI 스크립트 생성
echo NSI 스크립트 생성 중...

(
echo ; KCS Messenger NSIS Installer Script
echo ; Auto-generated installer configuration
echo.
echo !define APPNAME "KCS Messenger"
echo !define COMPANYNAME "KCS"
echo !define DESCRIPTION "카카오톡 스타일 메신저"
echo !define VERSIONMAJOR 1
echo !define VERSIONMINOR 0
echo !define VERSIONBUILD 0
echo !define HELPURL "https://github.com/your-repo/kcsmessager"
echo !define ABOUTURL "https://github.com/your-repo/kcsmessager"
echo.
echo RequestExecutionLevel admin
echo InstallDir "$PROGRAMFILES\${APPNAME}"
echo.
echo Name "${APPNAME}"
echo OutFile "KCS_Messenger_Setup.exe"
echo.
echo ; UI Settings
echo !include "MUI2.nsh"
echo !define MUI_ABORTWARNING
echo !define MUI_WELCOMEPAGE_TITLE "${APPNAME} 설치"
echo !define MUI_WELCOMEPAGE_TEXT "이 마법사는 ${APPNAME}를 설치합니다.$\r$\n$\r$\n계속하려면 다음을 클릭하세요."
echo.
echo ; Pages
echo !insertmacro MUI_PAGE_WELCOME
echo !insertmacro MUI_PAGE_DIRECTORY
echo !insertmacro MUI_PAGE_INSTFILES
echo !insertmacro MUI_PAGE_FINISH
echo.
echo !insertmacro MUI_UNPAGE_WELCOME
echo !insertmacro MUI_UNPAGE_CONFIRM
echo !insertmacro MUI_UNPAGE_INSTFILES
echo !insertmacro MUI_UNPAGE_FINISH
echo.
echo ; Languages
echo !insertmacro MUI_LANGUAGE "Korean"
echo !insertmacro MUI_LANGUAGE "English"
echo.
echo ; Installation Section
echo Section "install"
echo     SetOutPath $INSTDIR
echo.
echo     ; Copy main executable
echo     File "dist\KCS_Messenger.exe"
echo.
echo     ; Create uninstaller
echo     WriteUninstaller "$INSTDIR\uninstall.exe"
echo.
echo     ; Start Menu shortcuts
echo     CreateDirectory "$SMPROGRAMS\${APPNAME}"
echo     CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\KCS_Messenger.exe"
echo     CreateShortCut "$SMPROGRAMS\${APPNAME}\제거.lnk" "$INSTDIR\uninstall.exe"
echo.
echo     ; Desktop shortcut
echo     CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\KCS_Messenger.exe"
echo.
echo     ; Registry for Add/Remove Programs
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\uninstall.exe"
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "HelpLink" "${HELPURL}"
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLInfoAbout" "${ABOUTURL}"
echo     WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
echo     WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
echo     WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
echo     WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoModify" 1
echo     WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "NoRepair" 1
echo     WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "EstimatedSize" 50000
echo SectionEnd
echo.
echo ; Uninstallation Section
echo Section "uninstall"
echo     ; Remove shortcuts
echo     Delete "$SMPROGRAMS\${APPNAME}\*.*"
echo     RmDir "$SMPROGRAMS\${APPNAME}"
echo     Delete "$DESKTOP\${APPNAME}.lnk"
echo.
echo     ; Remove files
echo     Delete "$INSTDIR\KCS_Messenger.exe"
echo     Delete "$INSTDIR\uninstall.exe"
echo     RmDir "$INSTDIR"
echo.
echo     ; Remove registry keys
echo     DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
echo SectionEnd
) > installer.nsi

echo   ✓ installer.nsi 생성 완료
echo.

REM NSIS로 설치 프로그램 빌드
echo 설치 프로그램 빌드 중...
makensis installer.nsi

if exist "KCS_Messenger_Setup.exe" (
    echo.
    echo ====================================================
    echo    설치 프로그램 생성 완료!
    echo ====================================================
    echo.
    echo 생성된 파일: KCS_Messenger_Setup.exe
    for %%A in ("KCS_Messenger_Setup.exe") do echo 파일 크기: %%~zA bytes
    echo.
    echo 이 설치 프로그램은:
    echo   ✓ Program Files에 자동 설치
    echo   ✓ 시작 메뉴 바로가기 생성
    echo   ✓ 바탕화면 바로가기 생성
    echo   ✓ 프로그램 추가/제거에 등록
    echo.
    echo 사용자에게 KCS_Messenger_Setup.exe를 배포하세요.
    echo.
) else (
    echo.
    echo [오류] 설치 프로그램 생성 실패
    echo installer.nsi 파일을 확인하세요.
    echo.
)

pause