# -*- coding: utf-8 -*-
"""
KCS Talk(카카오톡 PC 스타일) 진입점

    python client/kakao/app.py [--host 127.0.0.1] [--port 5555] [--user 이름]

--user를 주지 않으면 로그인 창을 띄운다.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# High DPI 설정은 QApplication 생성 전에 해야 한다
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

from PyQt5.QtCore import Qt, QTimer, QCoreApplication  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog  # noqa: E402

from client.kakao import theme  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='KCS Talk 클라이언트')
    parser.add_argument('--host', default='127.0.0.1', help='서버 주소 (기본 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5555, help='서버 포트 (기본 5555)')
    parser.add_argument('--user', default='', help='로그인할 사용자 이름 (생략 시 로그인 창)')
    return parser.parse_args(argv)


def setup_high_dpi():
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)


def ask_connection_failure(host, port, error):
    """연결 실패 안내. 'retry' / 'settings' / 'quit'"""
    box = QMessageBox()
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle('서버 연결 실패')
    box.setText('서버에 연결할 수 없습니다.')
    box.setInformativeText(f'{host}:{port}\n서버가 실행 중인지, 주소와 포트가 맞는지 확인해 주세요.')
    box.setDetailedText(str(error))
    retry = box.addButton('다시 시도', QMessageBox.AcceptRole)
    settings = box.addButton('서버 설정', QMessageBox.ActionRole)
    box.addButton('종료', QMessageBox.RejectRole)
    box.setDefaultButton(retry)
    box.exec_()
    clicked = box.clickedButton()
    if clicked is retry:
        return 'retry'
    if clicked is settings:
        return 'settings'
    return 'quit'


class Session:
    """한 번의 로그인 세션: 연결 · 설정 · 상태 · 메인 창"""

    def __init__(self, host, port, username):
        from client.kakao.net import ChatConnection
        from client.kakao.settings import LocalSettings
        from client.kakao.state import AppState
        self.host, self.port, self.username = host, port, username
        self.settings = LocalSettings(username)
        self.conn = ChatConnection()
        self.state = AppState(self.conn, self.settings)
        self.window = None
        # 자동 재연결: 예기치 않게 끊기면 1·2·4·8·10초… 간격으로 다시 붙는다 (직접 닫은 연결은 제외)
        from PyQt5.QtCore import QTimer
        self._closing = False
        self._retry = 0
        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._auto_reconnect)
        self.state.connection_lost.connect(self._schedule_reconnect)

    RETRY_DELAYS = (1, 2, 4, 8, 10)

    def retry_delay(self):
        return self.RETRY_DELAYS[min(self._retry, len(self.RETRY_DELAYS) - 1)]

    def _schedule_reconnect(self, _reason=''):
        if self._closing or self._retry_timer.isActive():
            return
        delay = self.retry_delay()
        if self.window is not None:
            self.window.show_reconnecting(delay)
        self._retry_timer.start(delay * 1000)

    def _auto_reconnect(self):
        if self._closing:
            return
        ok, _msg = self.reconnect()
        if ok:
            self._retry = 0
        else:
            self._retry += 1
            self._schedule_reconnect()

    def connect(self):
        self.conn.connect_to(self.host, self.port, self.username)

    def reconnect(self):
        """같은 host/port/user로 새 연결을 만들어 상태에 붙인다 → (성공, 메시지)"""
        from client.kakao.net import ChatConnection
        conn = ChatConnection()
        try:
            conn.connect_to(self.host, self.port, self.state.me or self.username)
        except OSError as e:
            return False, f'재연결 실패: {e}'
        old = self.conn
        try:
            old.event_received.disconnect(self.state.handle)
            old.disconnected.disconnect(self.state.connection_lost)
        except TypeError:
            pass
        conn.event_received.connect(self.state.handle)
        conn.disconnected.connect(self.state.connection_lost)
        self.conn = conn
        self.state.conn = conn
        self.state.history_requested.clear()  # 열려 있는 방은 다시 히스토리를 받는다
        return True, ''

    def close(self):
        self._closing = True
        self._retry_timer.stop()
        try:
            self.conn.close()
        except Exception:
            pass

    def show_main_window(self):
        if self.window is not None:
            return
        from client.kakao.main_window import MainWindow
        self.window = MainWindow(self.state, self.settings, reconnect=self.reconnect,
                                 server_address=f'{self.host}:{self.port}')
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()


def install_korean_qt_translation(app):
    """Qt 기본 대화상자 버튼(Yes/No/Cancel, 파일 선택 창)을 한국어로 (예/아니요/취소).
    번역 파일이 없으면(일부 배포본) 조용히 영어로 둔다"""
    from PyQt5.QtCore import QLibraryInfo, QTranslator
    translator = QTranslator(app)
    for path in (QLibraryInfo.location(QLibraryInfo.TranslationsPath),
                 os.path.join(getattr(sys, '_MEIPASS', ''), 'PyQt5', 'Qt5', 'translations')):
        if path and translator.load('qtbase_ko', path):
            app.installTranslator(translator)
            app._kcs_translator = translator   # 가비지 컬렉션 방지
            return True
    return False


def main(argv=None):
    args = parse_args(argv)
    setup_high_dpi()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName('KCS Talk')
    app.setApplicationDisplayName('KCS Talk')
    app.setStyle('Fusion')
    install_korean_qt_translation(app)

    from client.kakao.login import LoginDialog, talk_icon
    from client.kakao.main_window import apply_app_theme
    app.setWindowIcon(talk_icon())
    apply_app_theme(None)

    host, port, username = args.host, args.port, args.user.strip()
    need_login = not username
    while True:
        if need_login:
            dlg = LoginDialog(host, port, username)
            if dlg.exec_() != QDialog.Accepted:
                return 0
            username, host, port = dlg.values()
        session = Session(host, port, username)
        try:
            session.connect()
            break
        except OSError as e:
            choice = ask_connection_failure(host, port, e)
            if choice == 'quit':
                return 1
            need_login = choice == 'settings'

    # 사용자별 설정(다크 모드, 글자 크기)을 적용
    apply_app_theme(session.settings)
    session.state.welcomed.connect(session.show_main_window)

    def welcome_timeout():
        if session.window is None:
            QMessageBox.critical(None, '서버 응답 없음',
                                 '서버에 연결했지만 응답이 없습니다.\n잠시 후 다시 시도해 주세요.')
            app.quit()
    QTimer.singleShot(10000, welcome_timeout)

    def lost_before_welcome(reason):
        if session.window is None:
            QMessageBox.critical(None, '서버 연결 끊김', f'로그인 중 연결이 끊어졌습니다.\n{reason}')
            app.quit()
    session.state.connection_lost.connect(lost_before_welcome)

    app.aboutToQuit.connect(session.close)
    app._kcs_session = session  # 가비지 컬렉션 방지
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
