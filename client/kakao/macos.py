# -*- coding: utf-8 -*-
"""
macOS 전용 보정 - python3 로 실행하면 Dock·메뉴 막대에 'Python' 으로 나오는 것을 앱 이름으로 바꾼다.
pyobjc 없이 ctypes 만 쓴다.
- set_app_name: main bundle 의 CFBundleName 을 덮어쓴다 (메뉴 막대). QApplication 을 만들기 전에 부른다.
- set_dock_name: LaunchServices 표시 이름을 바꾼다 (Dock 툴팁 · 앱 전환기). QApplication 을 만든 뒤에 부른다.
- unify_title_bar: 창의 제목 표시줄을 투명하게 해 본문 배경이 창 맨 위(신호등 버튼 뒤)까지 이어지게 한다.
  Dock 은 실행 파일 묶음(Python.app)의 이름을 LaunchServices 에서 읽으므로 CFBundleName 만으로는 'Python' 이 남는다.
macOS 가 아니거나 실패하면 아무것도 하지 않는다.
"""

import ctypes
import ctypes.util
import sys


def set_app_name(name):
    """Dock 툴팁 · 메뉴 막대 앱 이름을 name 으로. 바꿨으면 True"""
    if sys.platform != 'darwin' or getattr(sys, 'frozen', False):   # 빌드한 .app 은 Info.plist 이름을 쓴다
        return False
    objc_path, foundation_path = ctypes.util.find_library('objc'), ctypes.util.find_library('Foundation')
    if not objc_path or not foundation_path:
        return False
    try:
        objc = ctypes.cdll.LoadLibrary(objc_path)
        ctypes.cdll.LoadLibrary(foundation_path)
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.sel_registerName.restype = ctypes.c_void_p
        send = objc.objc_msgSend

        def call(obj, selector, *args, argtypes=()):
            send.restype = ctypes.c_void_p
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, *argtypes]
            return send(obj, objc.sel_registerName(selector.encode()), *args)

        def nsstring(text):
            return call(objc.objc_getClass(b'NSString'), 'stringWithUTF8String:', text.encode('utf-8'),
                        argtypes=(ctypes.c_char_p,))

        bundle = call(objc.objc_getClass(b'NSBundle'), 'mainBundle')
        info = call(bundle, 'infoDictionary') if bundle else None
        if not info:
            return False
        for key in ('CFBundleName', 'CFBundleDisplayName'):
            call(info, 'setObject:forKey:', nsstring(name), nsstring(key), argtypes=(ctypes.c_void_p, ctypes.c_void_p))
        return True
    except (OSError, AttributeError, TypeError):
        return False


DOCK_NAME = '케이씨에스'   # Dock 아이콘에 마우스를 올리면 보이는 이름
_LAUNCH_SERVICES = '/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/LaunchServices'
_CORE_FOUNDATION = '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
_UTF8 = 0x08000100              # kCFStringEncodingUTF8
_DEFAULT_SESSION = -2           # kLSDefaultSessionID


def set_dock_name(name=DOCK_NAME):
    """Dock 툴팁 · Cmd+Tab 앱 전환기 이름을 name 으로 (QApplication 생성 뒤). 바꿨으면 True"""
    if sys.platform != 'darwin' or getattr(sys, 'frozen', False):
        return False
    try:
        ls = ctypes.cdll.LoadLibrary(_LAUNCH_SERVICES)
        cf = ctypes.cdll.LoadLibrary(_CORE_FOUNDATION)
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        ls._LSGetCurrentApplicationASN.restype = ctypes.c_void_p
        ls._LSSetApplicationInformationItem.restype = ctypes.c_int32
        ls._LSSetApplicationInformationItem.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                                        ctypes.c_void_p, ctypes.c_void_p]
        key = ctypes.c_void_p.in_dll(ls, '_kLSDisplayNameKey').value
        asn = ls._LSGetCurrentApplicationASN()
        if not key or not asn:
            return False
        value = cf.CFStringCreateWithCString(None, name.encode('utf-8'), _UTF8)
        return bool(value) and ls._LSSetApplicationInformationItem(_DEFAULT_SESSION, asn, key, value, None) == 0
    except (OSError, AttributeError, ValueError):
        return False


NS_FULL_SIZE_CONTENT_VIEW = 1 << 15   # NSWindowStyleMaskFullSizeContentView
NS_TITLE_HIDDEN = 1                   # NSWindowTitleHidden
TITLE_BAR_HEIGHT = 28                 # 신호등 버튼이 차지하는 높이 - 이 아래부터 내용을 둔다


def unify_title_bar(widget):
    """macOS: 제목 표시줄을 투명하게 + 제목 글자 숨김 + 내용을 창 맨 위까지 (카카오톡 로그인 창처럼
    헤더와 본문이 한 배경). 창이 만들어진 뒤(show 이후) 부른다. 바꿨으면 True, macOS 가 아니면 False"""
    if sys.platform != 'darwin' or _qt_platform() != 'cocoa':
        return False
    objc_path = ctypes.util.find_library('objc')
    if not objc_path:
        return False
    try:
        objc = ctypes.cdll.LoadLibrary(objc_path)
        objc.sel_registerName.restype = ctypes.c_void_p
        send = objc.objc_msgSend

        def call(obj, selector, *args, argtypes=(), restype=ctypes.c_void_p):
            send.restype = restype
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, *argtypes]
            return send(obj, objc.sel_registerName(selector.encode()), *args)

        window = call(int(widget.winId()), 'window')
        if not window:
            return False
        mask = call(window, 'styleMask', restype=ctypes.c_ulong)
        call(window, 'setStyleMask:', mask | NS_FULL_SIZE_CONTENT_VIEW, argtypes=(ctypes.c_ulong,))
        call(window, 'setTitlebarAppearsTransparent:', True, argtypes=(ctypes.c_bool,))
        call(window, 'setTitleVisibility:', NS_TITLE_HIDDEN, argtypes=(ctypes.c_long,))
        # setMovableByWindowBackground 는 켜지 않는다: 누른 채로 있으면 창 끌기로 잡혀 콤보 목록 등 팝업이 바로 닫힌다.
        # 창은 투명해진 제목 표시줄 줄(위 28px)을 끌어 옮길 수 있다
        return True
    except (OSError, AttributeError, TypeError, ValueError):
        return False


def _qt_platform():
    """Qt 플랫폼 이름 ('cocoa', 'offscreen' …) - QApplication 이 없으면 ''"""
    from PyQt5.QtGui import QGuiApplication
    return QGuiApplication.platformName() if QGuiApplication.instance() else ''
