#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for creating KCS Messenger executable
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def clean_build():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build artifacts...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  ✓ Removed {dir_name}/")

    # Clean .spec file if requested
    spec_file = 'kakaotalk_launcher.spec'
    if '--fresh' in sys.argv and os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"  ✓ Removed {spec_file}")

def install_dependencies():
    """Install PyInstaller if not present"""
    print("\n📦 Checking dependencies...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller is installed")
    except ImportError:
        print("  ! PyInstaller not found, installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("  ✓ PyInstaller installed")

def create_spec_file():
    """Create or update the spec file"""
    spec_file = 'kakaotalk_launcher.spec'

    if not os.path.exists(spec_file):
        print("\n📝 Creating spec file...")
        spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Collect all data files and submodules from PyQt5
datas = []
binaries = []
hiddenimports = ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets']

# Add all Python modules in the project
hiddenimports += [
    'client.launcher.chat_launcher',
    'client.realtime.chat_client',
    'client.standalone.standalone_chat',
    'client.desktop.kakaotalk_ui',
    'client.desktop.kakaotalk_integrated',
    'server.chat.chat_server',
    'server.core.async_server',
]

# Add encoding support for Korean text
hiddenimports += ['encodings.utf_8', 'encodings.cp949', 'locale', 'codecs']

a = Analysis(
    ['kakaotalk_launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'black', 'flake8', 'mypy', 'pre-commit'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KCS_Messenger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False for GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an icon file here later
)

# For Windows, just create the exe
if sys.platform == 'win32':
    pass
# For macOS, create an app bundle
elif sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='KCS Messenger.app',
        icon=None,
        bundle_identifier='com.kcs.messenger',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
        },
    )
'''
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        print(f"  ✓ Created {spec_file}")
    else:
        print(f"\n📝 Using existing {spec_file}")

def build_executable():
    """Build the executable using PyInstaller"""
    print("\n🔨 Building executable...")
    spec_file = 'kakaotalk_launcher.spec'

    cmd = ['pyinstaller', spec_file, '--clean']
    if '--debug' in sys.argv:
        cmd.append('--debug=all')

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print("\n✅ Build successful!")
        return True
    else:
        print("\n❌ Build failed!")
        return False

def show_results():
    """Show the build results"""
    print("\n📁 Build Results:")
    print("-" * 40)

    dist_path = Path('dist')
    if not dist_path.exists():
        print("  ❌ No dist folder found")
        return

    # Show all files in dist
    for item in dist_path.iterdir():
        size = 0
        if item.is_file():
            size = item.stat().st_size / (1024 * 1024)  # MB
            print(f"  📄 {item.name} ({size:.1f} MB)")
        elif item.is_dir():
            print(f"  📁 {item.name}/")

    print("\n💡 How to run:")
    print("-" * 40)

    if sys.platform == 'win32':
        exe_path = dist_path / 'KCS_Messenger.exe'
        if exe_path.exists():
            print(f"  Windows: Double-click dist\\KCS_Messenger.exe")
            print(f"  Or run: .\\dist\\KCS_Messenger.exe")
    elif sys.platform == 'darwin':
        app_path = dist_path / 'KCS Messenger.app'
        exe_path = dist_path / 'KCS_Messenger'
        if app_path.exists():
            print(f"  macOS App: open 'dist/KCS Messenger.app'")
        if exe_path.exists():
            print(f"  macOS Terminal: ./dist/KCS_Messenger")
    else:
        exe_path = dist_path / 'KCS_Messenger'
        if exe_path.exists():
            print(f"  Linux: ./dist/KCS_Messenger")

def main():
    """Main build process"""
    print("=" * 50)
    print("🚀 KCS Messenger Executable Builder")
    print("=" * 50)

    # Parse arguments
    if '--help' in sys.argv:
        print("\nUsage: python build_exe.py [options]")
        print("\nOptions:")
        print("  --clean     Clean build artifacts before building")
        print("  --fresh     Remove spec file and create new one")
        print("  --debug     Build with debug information")
        print("  --help      Show this help message")
        return

    # Clean if requested
    if '--clean' in sys.argv or '--fresh' in sys.argv:
        clean_build()

    # Install dependencies
    install_dependencies()

    # Create spec file
    create_spec_file()

    # Build
    if build_executable():
        show_results()
    else:
        print("\n❌ Build process failed. Check the error messages above.")
        sys.exit(1)

if __name__ == '__main__':
    main()