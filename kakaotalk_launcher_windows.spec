# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for KCS Messenger - Windows Version

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Collect all PyQt5 data files and binaries
datas = []
binaries = []
hiddenimports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
]

# Windows-specific modules for proper display
hiddenimports += [
    'win32com',
    'win32api',
    'win32con',
    'pywintypes',
    'pythoncom',
]

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

# Add encoding support for Korean text (Windows)
hiddenimports += [
    'encodings',
    'encodings.utf_8',
    'encodings.cp949',
    'encodings.cp1252',
    'locale',
    'codecs',
]

# Essential Python standard library modules
hiddenimports += [
    'json',
    'threading',
    'socket',
    'subprocess',
    'datetime',
    'time',
    'sys',
    'os',
]

a = Analysis(
    ['kakaotalk_launcher.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'black',
        'flake8',
        'mypy',
        'pre-commit',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'notebook',
        'ipython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove unnecessary modules to reduce size
a.binaries = [x for x in a.binaries if not x[0].startswith("scipy")]
a.binaries = [x for x in a.binaries if not x[0].startswith("numpy")]
a.binaries = [x for x in a.binaries if not x[0].startswith("pandas")]

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
    console=False,  # False = GUI 앱 (콘솔 창 숨김)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,  # 관리자 권한 불필요
    uac_uiaccess=False,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,  # 아이콘 파일 (있을 경우)
    version='version_info.txt' if os.path.exists('version_info.txt') else None,  # 버전 정보 (있을 경우)
)