# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for KCS Messenger

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
    pathex=['/Users/joogik/develop/kcsmessager'],
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

# For macOS, create an app bundle
if sys.platform == 'darwin':
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