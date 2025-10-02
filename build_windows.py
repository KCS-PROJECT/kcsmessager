#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows-specific build script for KCS Messenger
Creates a standalone .exe file that runs on Windows without Python installation
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path
import platform

def check_windows():
    """Check if running on Windows"""
    if platform.system() != 'Windows':
        print("⚠️  Warning: This script is designed for Windows.")
        print("   You are running on:", platform.system())
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)

def clean_build():
    """Clean previous build artifacts"""
    print("🧹 정리 중: 이전 빌드 파일 제거...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"  ✓ {dir_name}/ 폴더 삭제됨")
            except Exception as e:
                print(f"  ⚠️  {dir_name}/ 삭제 실패: {e}")

    # Clean spec files if requested
    if '--fresh' in sys.argv:
        for spec_file in ['kakaotalk_launcher_windows.spec', 'kakaotalk_launcher.spec']:
            if os.path.exists(spec_file):
                os.remove(spec_file)
                print(f"  ✓ {spec_file} 삭제됨")

def check_python_version():
    """Check Python version compatibility"""
    print("\n🐍 Python 버전 확인...")
    version = sys.version_info
    print(f"  현재 버전: Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("  ❌ Python 3.8 이상이 필요합니다!")
        print("  다운로드: https://www.python.org/downloads/")
        sys.exit(1)
    else:
        print("  ✓ Python 버전 호환됨")

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 필수 패키지 설치 중...")

    # Check and install PyQt5
    try:
        import PyQt5
        print("  ✓ PyQt5 이미 설치됨")
    except ImportError:
        print("  ! PyQt5 설치 중...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'PyQt5'], check=True)
        print("  ✓ PyQt5 설치 완료")

    # Check and install PyInstaller
    try:
        import PyInstaller
        print("  ✓ PyInstaller 이미 설치됨")
    except ImportError:
        print("  ! PyInstaller 설치 중...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("  ✓ PyInstaller 설치 완료")

def create_version_info():
    """Create version information file for Windows exe"""
    version_file = 'version_info.txt'
    if not os.path.exists(version_file):
        print("\n📝 버전 정보 파일 생성 중...")
        version_content = """
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'KCS'),
        StringStruct(u'FileDescription', u'KCS Messenger - 카카오톡 클론'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'KCS_Messenger'),
        StringStruct(u'LegalCopyright', u'© 2024 KCS. All rights reserved.'),
        StringStruct(u'OriginalFilename', u'KCS_Messenger.exe'),
        StringStruct(u'ProductName', u'KCS Messenger'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(version_content)
        print(f"  ✓ {version_file} 생성됨")

def build_executable():
    """Build the Windows executable"""
    print("\n🔨 Windows 실행파일 빌드 중...")
    print("  이 작업은 몇 분 정도 걸릴 수 있습니다...")

    spec_file = 'kakaotalk_launcher_windows.spec'

    # Check if spec file exists, if not use the default one
    if not os.path.exists(spec_file):
        spec_file = 'kakaotalk_launcher.spec'
        if not os.path.exists(spec_file):
            print("  ❌ Spec 파일을 찾을 수 없습니다!")
            print("  먼저 build_exe.py를 실행하세요")
            return False

    # Build command
    cmd = [sys.executable, '-m', 'PyInstaller', spec_file, '--clean', '--noconfirm']

    if '--debug' in sys.argv:
        cmd.append('--debug=all')

    if '--onedir' not in sys.argv:
        cmd.append('--onefile')  # Single exe file by default

    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print("\n✅ 빌드 성공!")
        return True
    else:
        print("\n❌ 빌드 실패!")
        return False

def create_run_script():
    """Create a simple run script for the exe"""
    run_bat = 'run_messenger.bat'
    print(f"\n📝 실행 스크립트 생성 중: {run_bat}")

    content = r"""@echo off
chcp 65001 >nul
echo ========================================
echo    KCS Messenger 실행
echo ========================================
echo.

if exist "dist\KCS_Messenger.exe" (
    echo KCS Messenger를 시작합니다...
    start "" "dist\KCS_Messenger.exe"
) else (
    echo 오류: 실행파일을 찾을 수 없습니다!
    echo dist\KCS_Messenger.exe 파일이 없습니다.
    echo.
    echo 먼저 build_windows.py를 실행하여 빌드하세요.
    pause
)
"""

    with open(run_bat, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ {run_bat} 생성됨")

def show_results():
    """Show build results and instructions"""
    print("\n" + "=" * 50)
    print("📊 빌드 결과")
    print("=" * 50)

    dist_path = Path('dist')
    if not dist_path.exists():
        print("  ❌ dist 폴더를 찾을 수 없습니다")
        return

    exe_path = dist_path / 'KCS_Messenger.exe'
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ 실행파일 생성 완료!")
        print(f"  📍 위치: {exe_path.absolute()}")
        print(f"  📊 크기: {size_mb:.1f} MB")

        print("\n" + "=" * 50)
        print("💡 실행 방법")
        print("=" * 50)
        print("\n방법 1: 파일 탐색기에서 직접 실행")
        print(f"  1. dist 폴더 열기")
        print(f"  2. KCS_Messenger.exe 더블클릭")

        print("\n방법 2: 배치 파일로 실행")
        print(f"  run_messenger.bat 더블클릭")

        print("\n방법 3: 명령 프롬프트에서 실행")
        print(f"  dist\\KCS_Messenger.exe")

        print("\n📌 참고사항:")
        print("  • Windows Defender가 처음 실행 시 검사할 수 있습니다")
        print("  • '추가 정보' → '실행'을 클릭하여 실행하세요")
        print("  • Python이 설치되지 않은 PC에서도 실행 가능합니다")

    else:
        print("  ❌ 실행파일이 생성되지 않았습니다")
        print("  오류 메시지를 확인하세요")

def create_installer_script():
    """Create NSIS installer script (optional)"""
    nsi_file = 'installer.nsi'
    print(f"\n📝 설치 프로그램 스크립트 생성 중: {nsi_file}")

    content = """; KCS Messenger NSIS Installer Script
; Requires NSIS (https://nsis.sourceforge.io/)

!define APPNAME "KCS Messenger"
!define COMPANYNAME "KCS"
!define DESCRIPTION "카카오톡 스타일 메신저"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0

RequestExecutionLevel admin
InstallDir "$PROGRAMFILES\\${APPNAME}"

Name "${APPNAME}"
Icon "assets\\icon.ico"
OutFile "KCS_Messenger_Setup.exe"

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "assets\\icon.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "English"

Section "install"
    SetOutPath $INSTDIR

    File "dist\\KCS_Messenger.exe"

    WriteUninstaller "$INSTDIR\\uninstall.exe"

    # Start Menu
    CreateDirectory "$SMPROGRAMS\\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\\${APPNAME}\\${APPNAME}.lnk" "$INSTDIR\\KCS_Messenger.exe"
    CreateShortCut "$SMPROGRAMS\\${APPNAME}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"

    # Desktop shortcut
    CreateShortCut "$DESKTOP\\${APPNAME}.lnk" "$INSTDIR\\KCS_Messenger.exe"

    # Registry
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}" "EstimatedSize" 50000
SectionEnd

Section "uninstall"
    Delete "$SMPROGRAMS\\${APPNAME}\\*.*"
    RmDir "$SMPROGRAMS\\${APPNAME}"
    Delete "$DESKTOP\\${APPNAME}.lnk"
    Delete "$INSTDIR\\*.*"
    RmDir "$INSTDIR"

    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APPNAME}"
SectionEnd
"""

    with open(nsi_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ {nsi_file} 생성됨")
    print(f"  📌 NSIS를 설치한 후 이 스크립트로 설치 프로그램을 만들 수 있습니다")
    print(f"     다운로드: https://nsis.sourceforge.io/")

def main():
    """Main build process"""
    print("=" * 50)
    print("🚀 KCS Messenger Windows 빌드")
    print("=" * 50)

    # Help
    if '--help' in sys.argv:
        print("\n사용법: python build_windows.py [옵션]")
        print("\n옵션:")
        print("  --clean     빌드 전 기존 파일 정리")
        print("  --fresh     모든 설정 파일 재생성")
        print("  --debug     디버그 정보 포함")
        print("  --onedir    단일 파일 대신 폴더로 생성")
        print("  --installer 설치 프로그램 스크립트 생성")
        print("  --help      도움말 표시")
        return

    # Check Windows
    check_windows()

    # Check Python version
    check_python_version()

    # Clean if requested
    if '--clean' in sys.argv or '--fresh' in sys.argv:
        clean_build()

    # Install dependencies
    install_dependencies()

    # Create version info
    create_version_info()

    # Build
    if build_executable():
        create_run_script()

        if '--installer' in sys.argv:
            create_installer_script()

        show_results()
    else:
        print("\n❌ 빌드 실패. 오류 메시지를 확인하세요.")
        sys.exit(1)

if __name__ == '__main__':
    main()