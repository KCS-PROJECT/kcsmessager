# -*- coding: utf-8 -*-
"""
운영체제 공통 계층 - Windows · macOS · Linux 차이를 이 파일 한 곳에 모은다.

다른 모듈은 sys.platform 을 직접 보지 말고 여기 함수를 쓴다.
- 어떤 OS 인가: current() / is_mac() / is_windows() / is_linux()
- 폴더: app_home() (사용자 데이터) · user_dir('downloads'|'documents'|'pictures'|'home') · resource_path() (앱에 든 파일)
- 열기: open_path() · open_url()
- 글자: ui_font_families() · emoji_families() - OS 마다 기본 한글 · 이모지 글꼴 순서
- 단축키 표기: shortcut_text('Ctrl+Shift+Enter') → macOS '⇧⌘Enter' (Apple 순서 ⌃⌥⇧⌘), 그 밖 'Ctrl+Shift+Enter'
  (Qt 는 QKeySequence 의 Ctrl 을 macOS 에서 ⌘ 로 자동으로 바꾸므로 키 연결은 어디서나 'Ctrl+…' 로 쓴다)
- 시작 보정: prepare_process() (QApplication 전) · configure_app(app) (QApplication 직후)
- 다시 실행: relaunch_command(argv)

함수는 부를 때마다 sys.platform 을 읽는다 (테스트에서 OS 를 바꿔 끼울 수 있게).
"""

import os
import subprocess
import sys

APP_NAME = 'KCS Talk'
APP_ID = 'kr.co.kcs.talk'                 # macOS 번들 ID · Windows AppUserModelID · Linux 데스크톱 파일 이름
ORGANIZATION = '케이씨에스'
DESKTOP_FILE = 'kr.co.kcs.talk'           # Linux: ~/.local/share/applications/kr.co.kcs.talk.desktop
DATA_DIR_NAME = '.kcs_messenger'          # 모든 OS 공통 (예전 설치와 같은 폴더를 그대로 쓴다)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------- 어떤 OS 인가
def current():
    """'mac' / 'windows' / 'linux' (그 밖의 유닉스도 'linux' 로 다룬다)"""
    if sys.platform == 'darwin':
        return 'mac'
    if sys.platform.startswith(('win', 'cygwin', 'msys')):
        return 'windows'
    return 'linux'


def is_mac():
    return current() == 'mac'


def is_windows():
    return current() == 'windows'


def is_linux():
    return current() == 'linux'


def os_label():
    return {'mac': 'macOS', 'windows': 'Windows', 'linux': 'Linux'}[current()]


# ---------------------------------------------------------------- 폴더
def app_home():
    """사용자 데이터 폴더 (설정 · 저장된 로그인 · 비밀채팅 키 · 녹음). KCS_MESSENGER_HOME 이 있으면 그 폴더"""
    return os.environ.get('KCS_MESSENGER_HOME') or os.path.join(os.path.expanduser('~'), DATA_DIR_NAME)


def app_path(*parts):
    """app_home() 아래 경로"""
    return os.path.join(app_home(), *parts)


_STANDARD = {'downloads': ('DownloadLocation', 'Downloads'), 'documents': ('DocumentsLocation', 'Documents'),
             'pictures': ('PicturesLocation', 'Pictures'), 'home': ('HomeLocation', '')}


def user_dir(kind):
    """사용자 폴더 (다운로드 · 문서 · 사진 · 홈). OS 가 알려 주는 위치(한글 이름 폴더 포함)를 쓰고,
    없으면 홈 아래 영문 이름, 그것도 없으면 홈"""
    location, fallback = _STANDARD[kind]
    home = os.path.expanduser('~')
    path = ''
    try:
        from PyQt5.QtCore import QStandardPaths
        path = QStandardPaths.writableLocation(getattr(QStandardPaths, location))
    except ImportError:
        pass
    if not path:
        path = os.path.join(home, fallback) if fallback else home
    return path if os.path.isdir(path) else home


def resource_path(*parts):
    """앱에 든 파일(assets/…) 경로 - 소스 실행이면 저장소, PyInstaller 로 빌드한 앱이면 풀린 임시 폴더"""
    base = getattr(sys, '_MEIPASS', None) or ROOT
    return os.path.join(base, *parts)


def secure_file(path):
    """다른 사용자가 못 읽게 (POSIX 600). Windows 는 사용자 프로필 폴더 권한을 따르므로 하지 않는다"""
    if is_windows():
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


_WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def safe_filename(name, fallback='file'):
    """어느 OS 에서도 저장되는 파일 이름 - 받은 첨부 이름은 다른 OS 에서 왔을 수 있다.
    Windows 금지 글자(\\ / : * ? " < > |, 제어 문자) → '_', 끝의 점 · 공백 제거, CON · NUL 같은 예약 이름 피하기, 길이 제한"""
    import re
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', os.path.basename(str(name or '').replace('\\', '/'))).strip(' .')
    if not name:
        return fallback
    stem, dot, ext = name.partition('.')
    if stem.upper() in _WINDOWS_RESERVED:
        name = '_' + name
    if len(name) > 180:                                   # 경로 길이 한도(Windows 260자) 여유
        root, ext = os.path.splitext(name)
        name = root[:180 - len(ext)] + ext
    return name


# ---------------------------------------------------------------- 열기
def open_command(path_or_url):
    """Qt 없이 열 때 쓰는 명령 (Windows 는 None - os.startfile 사용)"""
    if is_mac():
        return ['open', path_or_url]
    if is_windows():
        return None
    return ['xdg-open', path_or_url]


def _open_fallback(target):
    try:
        if is_windows():
            os.startfile(target)          # noqa: S606 - 사용자가 고른 파일/주소를 기본 앱으로
        else:
            subprocess.Popen(open_command(target) or [], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, AttributeError):
        return False


def open_path(path):
    """파일 · 폴더를 OS 기본 앱으로 연다. 열었으면 True"""
    try:
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        if QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path))):
            return True
    except ImportError:
        pass
    return _open_fallback(os.path.abspath(path))


def open_url(url):
    """웹 주소를 기본 브라우저로. 열었으면 True"""
    try:
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices
        if QDesktopServices.openUrl(QUrl(url)):
            return True
    except ImportError:
        pass
    return _open_fallback(url)


# ---------------------------------------------------------------- 글자
_UI_FONTS = {
    'mac': ['Apple SD Gothic Neo', 'AppleGothic', 'Noto Sans KR', 'Arial'],
    'windows': ['맑은 고딕', 'Malgun Gothic', 'Noto Sans KR', 'Segoe UI', 'Arial'],
    'linux': ['Noto Sans CJK KR', 'Noto Sans KR', 'NanumGothic', 'Nanum Gothic', 'UnDotum', 'DejaVu Sans'],
}
_EMOJI_FONTS = {'mac': ['Apple Color Emoji'], 'windows': ['Segoe UI Emoji'], 'linux': ['Noto Color Emoji']}


def ui_font_families():
    """한글 UI 글꼴 순서: 앱에 든 Pretendard → 이 OS 기본 한글 글꼴 → 다른 OS 글꼴(원격 데스크톱 등 대비)"""
    own = _UI_FONTS[current()]
    others = [f for key, names in _UI_FONTS.items() if key != current() for f in names]
    return list(dict.fromkeys(['Pretendard'] + own + others))


def emoji_families():
    own = _EMOJI_FONTS[current()]
    others = [f for key, names in _EMOJI_FONTS.items() if key != current() for f in names]
    return own + others


# ---------------------------------------------------------------- 단축키 표기
_MAC_KEYS = {'Ctrl': '⌘', 'Shift': '⇧', 'Alt': '⌥', 'Meta': '⌃'}


def mod_label():
    """주 수정 키 이름: macOS '⌘', 그 밖 'Ctrl'"""
    return '⌘' if is_mac() else 'Ctrl'


def shortcut_text(sequence):
    """'Ctrl+Shift+Enter' → macOS '⇧⌘Enter' (Qt 가 macOS 에서 Ctrl 을 ⌘ 로 연결하는 것과 같게), 그 밖은 그대로"""
    if not is_mac():
        return sequence
    parts = sequence.split('+')
    keys = [p for p in parts if p not in _MAC_KEYS]
    mods = ''.join(_MAC_KEYS[p] for p in ('Meta', 'Alt', 'Shift', 'Ctrl') if p in parts)
    return mods + '+'.join(keys)


# ---------------------------------------------------------------- 시작 보정
def prepare_process():
    """QApplication 을 만들기 전에 부른다: High DPI · OS 별 앱 이름/작업 표시줄 묶음"""
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
    from PyQt5.QtCore import Qt, QCoreApplication
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        from PyQt5.QtGui import QGuiApplication
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    if is_mac():
        from client.kakao.macos import set_app_name
        set_app_name(APP_NAME)                 # 메뉴 막대에 'Python' 대신
    elif is_windows():
        set_windows_app_id()                   # 작업 표시줄에 python.exe 아이콘 대신 앱 아이콘 · 한 묶음


def set_windows_app_id(app_id=APP_ID):
    """Windows: 작업 표시줄이 이 프로세스를 python.exe 가 아닌 KCS Talk 로 묶게 한다. 바꿨으면 True"""
    if not is_windows():
        return False
    try:
        import ctypes
        return ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id) == 0
    except (OSError, AttributeError):
        return False


def configure_app(app):
    """QApplication 을 만든 직후 부른다: 이름 · 스타일 · OS 별 연동"""
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORGANIZATION)
    app.setOrganizationDomain('kcs.co.kr')
    app.setStyle('Fusion')                     # 세 OS 에서 같은 모양 (기본 스타일은 OS 마다 다르다)
    if is_mac():
        from client.kakao.macos import set_dock_name
        set_dock_name()
    elif is_linux() and hasattr(app, 'setDesktopFileName'):
        app.setDesktopFileName(DESKTOP_FILE)   # Wayland/GNOME 이 작업 표시줄 아이콘을 .desktop 과 잇는다


# ---------------------------------------------------------------- 다시 실행
def relaunch_command(argv=None):
    """(프로그램, 인자) - 지금 앱을 같은 방식으로 다시 띄우는 명령. 빌드한 앱이면 실행 파일 그대로"""
    argv = list(sys.argv if argv is None else argv)
    if getattr(sys, 'frozen', False):
        return sys.executable, argv[1:]
    return sys.executable, [os.path.abspath(argv[0])] + argv[1:]
