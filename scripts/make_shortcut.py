# -*- coding: utf-8 -*-
"""
KCS Talk 바로가기 만들기 - OS 마다 사용자가 앱을 찾는 자리에 둔다.

    python kcs.py shortcut            Windows: 바탕화면 + 시작 메뉴 .lnk
                                      macOS:   바탕화면 'KCS Talk.command' (빌드한 .app 은 응용 프로그램 폴더로 끌어 놓기)
                                      Linux:   ~/.local/share/applications/kr.co.kcs.talk.desktop (앱 목록)
    python kcs.py shortcut --dry-run  만들 파일과 내용만 출력

빌드한 실행 파일(dist/)이 있으면 그것을, 없으면 소스 실행(python kcs.py client)을 가리킨다.
"""

import argparse
import os
import stat
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from client.kakao import osenv  # noqa: E402

KCS = os.path.join(ROOT, 'kcs.py')
ICON_PNG = os.path.join(ROOT, 'assets', 'icon', 'app_icon_256.png')


def built_executable(os_name=None):
    """dist/ 에 빌드한 메신저가 있으면 그 경로"""
    os_name = os_name or osenv.current()
    name = osenv.APP_NAME
    path = {'mac': os.path.join(ROOT, 'dist', f'{name}.app'),
            'windows': os.path.join(ROOT, 'dist', name, f'{name}.exe'),
            'linux': os.path.join(ROOT, 'dist', name, name)}[os_name]
    return path if os.path.exists(path) else None


def python_for_gui():
    """콘솔 창 없이 띄울 파이썬 (Windows 는 pythonw.exe)"""
    exe = sys.executable
    if osenv.is_windows():
        candidate = os.path.join(os.path.dirname(exe), 'pythonw.exe')
        if os.path.exists(candidate):
            return candidate
    return exe


def plan(os_name=None, home=None):
    """[(경로, 내용 또는 None, 설명)] - 만들 바로가기 목록 (Windows .lnk 는 PowerShell 로 만들므로 내용 None)"""
    os_name = os_name or osenv.current()
    home = home or os.path.expanduser('~')
    exe = built_executable(os_name)
    if os_name == 'linux':
        exec_line = f'"{exe}"' if exe else f'"{python_for_gui()}" "{KCS}" client'
        content = '\n'.join(['[Desktop Entry]', 'Type=Application', f'Name={osenv.APP_NAME}',
                             'Comment=케이씨에스 사내 메신저', f'Exec={exec_line}', f'Icon={ICON_PNG}',
                             f'Path={ROOT}', 'Terminal=false', 'Categories=Network;InstantMessaging;Chat;',
                             f'StartupWMClass={osenv.APP_NAME}', 'StartupNotify=true', '']) + '\n'
        path = os.path.join(home, '.local', 'share', 'applications', f'{osenv.DESKTOP_FILE}.desktop')
        return [(path, content, '앱 목록')]
    if os_name == 'mac':
        target = f'open "{exe}"' if exe else f'cd "{ROOT}" && exec "{sys.executable}" "{KCS}" client'
        content = f'#!/bin/bash\n# KCS Talk 실행 (python kcs.py shortcut 이 만듦)\n{target}\n'
        return [(os.path.join(home, 'Desktop', f'{osenv.APP_NAME}.command'), content, '바탕화면')]
    start_menu = os.path.join(os.environ.get('APPDATA') or os.path.join(home, 'AppData', 'Roaming'),
                              'Microsoft', 'Windows', 'Start Menu', 'Programs')
    return [(os.path.join(home, 'Desktop', f'{osenv.APP_NAME}.lnk'), None, '바탕화면'),
            (os.path.join(start_menu, f'{osenv.APP_NAME}.lnk'), None, '시작 메뉴')]


def windows_lnk_script(path):
    """.lnk 를 만드는 PowerShell 스크립트"""
    exe = built_executable('windows')
    target, arguments = (exe, '') if exe else (python_for_gui(), f'"{KCS}" client')
    icon = os.path.join(ROOT, 'assets', 'icon.ico')

    def q(text):
        return text.replace("'", "''")
    return (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(path)}');"
            f"$s.TargetPath='{q(target)}';$s.Arguments='{q(arguments)}';$s.WorkingDirectory='{q(ROOT)}';"
            f"$s.IconLocation='{q(icon)}';$s.Description='KCS Talk';$s.Save()")


def main(argv=None):
    parser = argparse.ArgumentParser(prog='kcs.py shortcut', description='KCS Talk 바로가기 만들기')
    parser.add_argument('--dry-run', action='store_true', help='만들 파일만 출력')
    args = parser.parse_args(argv)
    for path, content, where in plan():
        print(f'[{osenv.os_label()} · {where}] {path}')
        if args.dry_run:
            if content:
                print(content)
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if content is None:
            subprocess.check_call(['powershell', '-NoProfile', '-Command', windows_lnk_script(path)])
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return 0


if __name__ == '__main__':
    sys.exit(main())
