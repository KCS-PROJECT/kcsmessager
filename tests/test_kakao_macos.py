# -*- coding: utf-8 -*-
"""macOS 보정 (client/kakao/macos.py): Dock 이름 '케이씨에스' · 로그인 창 제목 표시줄을 본문과 한 배경으로"""

import os
import subprocess
import sys
import unittest
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from client.kakao import macos


class DockNameTests(unittest.TestCase):
    def test_default_dock_name_is_company(self):
        self.assertEqual(macos.DOCK_NAME, '케이씨에스')

    def test_noop_off_macos_and_in_frozen_app(self):
        with mock.patch.object(sys, 'platform', 'linux'):
            self.assertFalse(macos.set_dock_name())
        with mock.patch.object(sys, 'frozen', True, create=True):
            self.assertFalse(macos.set_dock_name())          # 빌드한 .app 은 Info.plist 이름

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS 전용')
    def test_launch_services_name_changes(self):
        # offscreen 플랫폼은 LaunchServices 에 앱으로 등록되지 않으므로 cocoa 로 자식 프로세스를 띄워 확인한다
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code = ("import os, subprocess, sys\n"
                "from PyQt5.QtWidgets import QApplication\n"
                "from client.kakao.macos import set_dock_name\n"
                "app = QApplication([])\n"
                "print('ok' if set_dock_name() else 'fail')\n"
                "print(subprocess.run(['lsappinfo', 'info', '-only', 'name', str(os.getpid())],"
                " capture_output=True, text=True).stdout)\n")
        env = dict(os.environ, QT_QPA_PLATFORM='cocoa')
        out = subprocess.run([sys.executable, '-c', code], cwd=root, env=env, capture_output=True,
                             text=True, timeout=30).stdout
        if not out.startswith('ok'):
            self.skipTest(f'GUI 세션이 없어 LaunchServices 를 쓸 수 없음: {out.strip()[:80]}')
        self.assertIn('"케이씨에스"', out)


class UnifiedTitleBarTests(unittest.TestCase):
    def test_offscreen_login_dialog_keeps_layout(self):
        from PyQt5.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])   # 참조를 잡아 둬야 지워지지 않는다
        from client.kakao.login import LoginDialog
        dlg = LoginDialog(fresh=True)
        dlg.show()
        self.assertFalse(macos.unify_title_bar(dlg))                  # macOS 창(cocoa)이 아니면 그대로
        self.assertEqual(dlg.layout().contentsMargins().top(), 48)
        dlg.close()

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS 전용')
    def test_cocoa_login_dialog_title_bar_is_transparent(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code = ("import ctypes, sys\n"
                "from PyQt5.QtWidgets import QApplication\n"
                "app = QApplication([])\n"
                "from client.kakao.login import LoginDialog\n"
                "from client.kakao import macos\n"
                "d = LoginDialog(fresh=True); d.show(); app.processEvents()\n"
                "objc = ctypes.cdll.LoadLibrary('/usr/lib/libobjc.dylib')\n"
                "objc.sel_registerName.restype = ctypes.c_void_p\n"
                "send = objc.objc_msgSend\n"
                "send.restype = ctypes.c_void_p; send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]\n"
                "w = send(int(d.winId()), objc.sel_registerName(b'window'))\n"
                "send.restype = ctypes.c_ulong\n"
                "mask = send(w, objc.sel_registerName(b'styleMask'))\n"
                "send.restype = ctypes.c_bool\n"
                "clear = send(w, objc.sel_registerName(b'titlebarAppearsTransparent'))\n"
                "send.restype = ctypes.c_long\n"
                "hidden = send(w, objc.sel_registerName(b'titleVisibility'))\n"
                "send.restype = ctypes.c_bool\n"
                "movable = send(w, objc.sel_registerName(b'isMovableByWindowBackground'))\n"
                "print(bool(mask & macos.NS_FULL_SIZE_CONTENT_VIEW), clear, hidden, movable,"
                " d.layout().contentsMargins().top())\n")
        env = dict(os.environ, QT_QPA_PLATFORM='cocoa', KCS_MESSENGER_HOME=os.path.join(root, '.no-such-home'))
        result = subprocess.run([sys.executable, '-c', code], cwd=root, env=env, capture_output=True,
                                text=True, timeout=30)
        if result.returncode != 0 or not result.stdout.strip():
            self.skipTest(f'GUI 세션이 없어 cocoa 창을 띄울 수 없음: {result.stderr.strip()[-80:]}')
        # 본문이 창 맨 위까지 · 제목 표시줄 투명 · 제목 글자 숨김 · 신호등 높이만큼 내용을 내림
        # 배경 끌기는 꺼 둔다: 켜면 누른 채로 있을 때 창 끌기로 잡혀 소속 회사 목록이 바로 닫혔다
        self.assertEqual(result.stdout.split(),
                         ['True', 'True', '1', 'False', str(48 + macos.TITLE_BAR_HEIGHT)])



class MainWindowTitleBarTests(unittest.TestCase):
    def test_offscreen_main_window_has_no_band(self):
        from tests.kakao_fakes import make_demo_state
        from client.kakao.main_window import MainWindow
        state, _conn = make_demo_state()
        win = MainWindow(state, state.settings)
        win.show()
        self.assertEqual(win.body.band, 0)                                   # macOS 창이 아니면 그대로
        self.assertEqual(win.sidebar.layout().contentsMargins().top(), 16)
        win.close()

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS 전용')
    def test_cocoa_main_window_header_reaches_top(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code = ("import os\n"
                "os.environ['QT_QPA_PLATFORM'] = 'cocoa'\n"
                "from tests.kakao_fakes import make_demo_state, app\n"
                "state, _c = make_demo_state()\n"
                "from client.kakao.main_window import MainWindow, apply_app_theme\n"
                "from client.kakao import macos\n"
                "apply_app_theme(state.settings)\n"
                "w = MainWindow(state, state.settings); w.resize(1300, 680); w.show(); app().processEvents()\n"
                "state.room_opened.emit(sorted(state.rooms)[0]); app().processEvents()\n"
                "img = w.body.grab().toImage()\n"
                "x = w.room_pane.x() + w.room_pane.width() // 2\n"
                "band = img.pixelColor(x * img.width() // w.body.width(), 4)\n"
                "print(w.body.band, w.sidebar.layout().contentsMargins().top(), w.is_split(), band.name(), flush=True)\n"
                "os._exit(0)\n")
        env = dict(os.environ, QT_QPA_PLATFORM='cocoa')
        result = subprocess.run([sys.executable, '-c', code], cwd=root, env=env, capture_output=True,
                                text=True, timeout=60)
        if result.returncode != 0 or not result.stdout.strip():
            self.skipTest(f'GUI 세션이 없어 cocoa 창을 띄울 수 없음: {result.stderr.strip()[-80:]}')
        band, inset, split, color = result.stdout.split()
        self.assertEqual((int(band), int(inset), split), (macos.TITLE_BAR_HEIGHT, 16 + macos.TITLE_BAR_HEIGHT, 'True'))
        self.assertNotEqual(color, '#000000')     # 반투명 헤더색(rgba)을 QColor 로 바로 쓰면 검게 칠해졌다



class ChatRoomWindowTitleBarTests(unittest.TestCase):
    def test_offscreen_room_window_keeps_header_margin(self):
        from tests.kakao_fakes import make_demo_state
        from client.kakao.chat_room import ChatRoomWindow
        state, _conn = make_demo_state()
        win = ChatRoomWindow(state, sorted(state.rooms)[0])
        win.show()
        self.assertEqual(win.header.layout().contentsMargins().top(), ChatRoomWindow.HEADER_TOP)
        win.close()

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS 전용')
    def test_cocoa_room_window_header_reaches_top_and_split_pane_does_not(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code = ("import os\n"
                "os.environ['QT_QPA_PLATFORM'] = 'cocoa'\n"
                "from tests.kakao_fakes import make_demo_state, app\n"
                "state, _c = make_demo_state()\n"
                "from client.kakao.main_window import MainWindow, apply_app_theme\n"
                "apply_app_theme(state.settings)\n"
                "w = MainWindow(state, state.settings); w.resize(1300, 680); w.show(); app().processEvents()\n"
                "r = w.open_room(sorted(state.rooms)[0]); app().processEvents()\n"
                "top = lambda: r.header.layout().contentsMargins().top()\n"
                "embedded = (r.isWindow(), top())\n"
                "w.resize(400, 680); app().processEvents(); app().processEvents()\n"
                "print(embedded[0], embedded[1], r.isWindow(), top(), flush=True)\n"
                "os._exit(0)\n")
        env = dict(os.environ, QT_QPA_PLATFORM='cocoa')
        result = subprocess.run([sys.executable, '-c', code], cwd=root, env=env, capture_output=True,
                                text=True, timeout=60)
        if result.returncode != 0 or not result.stdout.strip():
            self.skipTest(f'GUI 세션이 없어 cocoa 창을 띄울 수 없음: {result.stderr.strip()[-80:]}')
        # 분할 화면 안에서는 원래 여백, 별도 창으로 꺼내면 신호등 높이만큼 헤더를 내린다(헤더가 창 맨 위까지)
        self.assertEqual(result.stdout.split(), ['False', '10', 'True', str(10 + macos.TITLE_BAR_HEIGHT)])


if __name__ == '__main__':
    unittest.main()
