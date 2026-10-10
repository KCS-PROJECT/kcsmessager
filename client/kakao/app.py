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

# High DPI 설정은 QApplication 생성 전에 해야 한다 (자세한 OS 별 보정은 osenv.prepare_process)
os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

from PyQt5.QtCore import Qt, QTimer, QCoreApplication  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog  # noqa: E402

from client.kakao import theme, osenv  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='KCS Talk 클라이언트')
    parser.add_argument('--host', default='127.0.0.1', help='서버 주소 (기본 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5555, help='서버 포트 (기본 5555)')
    parser.add_argument('--user', default='', help='로그인 아이디 (생략 시 로그인 창)')
    parser.add_argument('--password', default='', help='비밀번호 (틀리거나 필요하면 로그인 창)')
    parser.add_argument('--no-auto-login', action='store_true',
                        help='저장된 자동 로그인을 쓰지 않고 항상 로그인 창 (런처에서 여러 사람으로 창을 열 때)')
    parser.add_argument('--self-check', action='store_true',
                        help='창을 띄우지 않고 OS · 글꼴 · 로고 · 데이터 폴더를 점검하고 끝낸다 (빌드한 앱 확인용)')
    return parser.parse_args(argv)


def self_check(out=print):
    """빌드한 앱(또는 소스 실행)이 이 OS 에서 필요한 것을 찾는지 점검. 문제가 없으면 0"""
    from client.kakao import brand
    families = theme.font_families()
    checks = [
        ('OS', True, f'{osenv.os_label()} ({osenv.current()})'),
        ('글꼴 폴더', os.path.isdir(theme.FONT_DIR), theme.FONT_DIR),
        ('Pretendard 등록', 'Pretendard' in families, ', '.join(families[:3])),
        ('회사 로고', brand.has_logo(), brand.BRAND_DIR),
        ('데이터 폴더', os.access(os.path.dirname(osenv.app_home()) or '.', os.W_OK), osenv.app_home()),
    ]
    for name, ok, detail in checks:
        out(f"{'✓' if ok else '✗'} {name}: {detail}")
    return 0 if all(ok for _n, ok, _d in checks) else 1


def setup_high_dpi():
    """QApplication 전 보정 - High DPI + OS 별 앱 이름 · 작업 표시줄 묶음 (osenv 한 곳에서)"""
    osenv.prepare_process()


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

    def __init__(self, host, port, username, password='', token='', remember=False, registration=None):
        from client.kakao.net import ChatConnection
        from client.kakao.settings import LocalSettings
        from client.kakao.state import AppState
        self.host, self.port, self.username = host, port, username
        self.password = password   # 자동 재연결용으로 메모리에만 둔다
        self.token = token         # 자동 로그인 토큰 (저장된 로그인)
        self.remember = remember
        self.registration = registration   # 처음 사용 등록 {company, name, employee_no, email, password} (명세 §4.1)
        if registration:                   # 다음부터의 로그인 아이디는 사번
            self.username = registration.get('employee_no') or registration['name']
            self.password = registration['password']
        self.settings = LocalSettings(self.username)   # welcome 때 실제 사용자 이름 파일로 바뀐다
        self.conn = ChatConnection()
        self.state = AppState(self.conn, self.settings)
        self.window = None
        self.on_relogin_needed = None   # 재연결이 거절되면(비밀번호 변경 등) 부를 함수(사유)
        # 자동 재연결: 예기치 않게 끊기면 1·2·4·8·10초… 간격으로 다시 붙는다 (직접 닫은 연결은 제외)
        from PyQt5.QtCore import QTimer
        self._closing = False
        self._retry = 0
        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._auto_reconnect)
        self.state.connection_lost.connect(self._schedule_reconnect)
        self.state.login_failed.connect(self._on_login_failed)
        self.state.account_disabled.connect(self._on_login_failed)   # 관리자가 사용 중지 → 재연결하지 않고 로그인 창

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

    def _credentials(self):
        """재연결은 받은 토큰 → 저장된 토큰 → 비밀번호 순으로 쓴다"""
        token = self.state.login_token or self.token
        return {'token': token} if token else {'password': self.password}

    def connect(self):
        if self.registration:      # 재연결은 등록된 비밀번호로 join 한다
            self.conn.connect_to(self.host, self.port, self.username, registration=self.registration,
                                 remember=self.remember)
        elif self.token:
            self.conn.connect_to(self.host, self.port, self.username, token=self.token)
        else:
            self.conn.connect_to(self.host, self.port, self.username, password=self.password,
                                 remember=self.remember)

    def reconnect(self):
        """같은 host/port/user로 새 연결을 만들어 상태에 붙인다 → (성공, 메시지)
        join 이 거절되면 login_failed → _on_login_failed 가 처리한다"""
        from client.kakao.net import ChatConnection
        conn = ChatConnection()
        try:
            conn.connect_to(self.host, self.port, self.state.me or self.username, **self._credentials())
        except OSError as e:
            return False, f'재연결 실패: {e}'
        old = self.conn
        try:
            old.event_received.disconnect(self.state.handle)
            old.disconnected.disconnect(self.state.connection_lost)
        except TypeError:
            pass
        try:
            old.close()           # 수동 재연결이면 예전 연결이 아직 살아 있을 수 있다
        except Exception:
            pass
        conn.event_received.connect(self.state.handle)
        conn.disconnected.connect(self.state.connection_lost)
        self.conn = conn
        self.state.conn = conn
        self.state.history_requested.clear()  # 열려 있는 방은 다시 히스토리를 받는다
        return True, ''

    def _on_login_failed(self, reason):
        if self.window is None:      # 첫 로그인은 wait_for_login 이 처리
            return
        self._closing = True         # 다시 붙어도 또 거절된다 → 재시도 멈춤
        self._retry_timer.stop()
        try:
            self.conn.close()
        except Exception:
            pass
        if self.on_relogin_needed is not None:
            self.on_relogin_needed(reason)

    def close(self):
        self._closing = True
        self._retry_timer.stop()
        try:
            self.conn.close()
        except Exception:
            pass

    def show_main_window(self, logout=None):
        if self.window is not None:
            return
        from client.kakao.main_window import MainWindow
        self.window = MainWindow(self.state, self.settings, reconnect=self.reconnect,
                                 server_address=f'{self.host}:{self.port}', logout=logout)
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()


def remember_login(session, login_id, auto_login):
    """로그인 성공 후: 최근 아이디 + (선택 시) 아이디·토큰 저장. 저장 안 함이면 저장 정보 삭제"""
    from client.kakao import login
    login.save_recent(login_id)
    token = session.state.login_token or session.token
    if session.remember and token:
        login.save_saved_login(login_id, token, auto_login, session.host, session.port)
    elif not session.remember:
        login.clear_saved_login()


def perform_logout(session, relaunch=None):
    """로그아웃: 서버의 자동 로그인 토큰 폐기 + 저장된 로그인 삭제 + 연결 종료 → 로그인 창부터 다시 시작"""
    from client.kakao import login
    saved_now = login.load_saved_login()
    session.state.revoke_login_token((saved_now or {}).get('token') or session.state.login_token)
    login.clear_saved_login()
    session.close()
    (relaunch or relaunch_to_login)()


def relaunch_to_login():
    """로그인 창부터 다시 시작 (로그아웃·재로그인 필요). --user/--password 인자는 빼고 다시 실행한다"""
    from PyQt5.QtCore import QProcess
    args, skip = [], False
    for a in sys.argv[1:]:
        if skip:
            skip = False
            continue
        if a in ('--user', '--password'):
            skip = True
            continue
        if a.startswith(('--user=', '--password=')):
            continue
        args.append(a)
    program, program_args = osenv.relaunch_command([sys.argv[0]] + args)
    QProcess.startDetached(program, program_args)
    QApplication.quit()


def wait_for_login(state, timeout_ms=10000):
    """join 결과를 기다린다 → ('ok'|'failed'|'lost'|'timeout', 사유)
    중첩 QEventLoop 대신 이벤트를 직접 돌린다(앞서 quit()가 불렸으면 QEventLoop.exec_는 바로 끝난다)"""
    import time
    from PyQt5.QtCore import QEventLoop
    result = []
    hooks = ((state.welcomed, lambda: result or result.append(('ok', ''))),
             (state.login_failed, lambda reason: result or result.append(('failed', reason))),
             (state.connection_lost, lambda reason: result or result.append(('lost', reason))))
    for signal, slot in hooks:
        signal.connect(slot)
    deadline = time.monotonic() + timeout_ms / 1000
    app = QCoreApplication.instance()
    while not result and time.monotonic() < deadline:
        app.processEvents(QEventLoop.AllEvents, 50)
        time.sleep(0.01)
    for signal, slot in hooks:
        signal.disconnect(slot)
    return result[0] if result else ('timeout', '')


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
    setup_high_dpi()                  # macOS 메뉴 막대 이름 · Windows 작업 표시줄 묶음 (QApplication 보다 먼저)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    osenv.configure_app(app)          # 이름 · Fusion 스타일 · macOS Dock 이름 · Linux .desktop 연결
    if args.self_check:
        return self_check()
    install_korean_qt_translation(app)

    from client.kakao.login import LoginDialog, talk_icon
    from client.kakao.main_window import apply_app_theme
    app.setWindowIcon(talk_icon())
    apply_app_theme(None)

    from client.kakao import login as login_mod
    host, port, username, password = args.host, args.port, args.user.strip(), args.password
    saved = login_mod.load_saved_login() if not username else None
    token, remember, auto_login = '', False, False
    if saved and saved['auto_login'] and not args.no_auto_login:   # 자동 로그인: 로그인 창 없이 저장된 토큰으로
        username, token, remember, auto_login = saved['login_id'], saved['token'], True, True
        host, port = saved['host'] or host, saved['port'] or port
    need_login = not username
    error = ''
    registration = None
    while True:
        if need_login:
            if saved and not args.user and not args.no_auto_login:
                host, port = saved['host'] or host, saved['port'] or port
            # 런처(--no-auto-login)로 연 창은 처음 로그인 상태: 아이디·비밀번호를 비우고 저장된 로그인을 쓰지 않는다
            dlg = LoginDialog(host, port, username, registration=registration,   # 등록 실패면 등록 화면 그대로
                              fresh=args.no_auto_login)
            dlg.show_error(error)
            if dlg.exec_() != QDialog.Accepted:
                return 0
            username, host, port = dlg.values()
            password, token = dlg.password(), dlg.saved_token()
            remember, auto_login = dlg.remember(), dlg.auto_login()
            registration = dlg.registration()
        session = Session(host, port, username, password, token=token, remember=remember,
                          registration=registration)
        try:
            session.connect()
        except OSError as e:
            choice = ask_connection_failure(host, port, e)
            if choice == 'quit':
                return 1
            need_login, error = choice == 'settings', ''
            continue
        outcome, detail = wait_for_login(session.state)
        if outcome == 'ok':
            break
        session.close()
        if outcome == 'failed':          # 아이디/비밀번호 오류·저장 정보 만료 → 로그인 창에 사유 표시
            if token:
                login_mod.clear_saved_login()
                saved, token = None, ''
            need_login, error = True, detail
            continue
        if outcome == 'timeout':
            QMessageBox.critical(None, '서버 응답 없음', '서버에 연결했지만 응답이 없습니다.\n잠시 후 다시 시도해 주세요.')
        else:
            QMessageBox.critical(None, '서버 연결 끊김', f'로그인 중 연결이 끊어졌습니다.\n{detail}')
        return 1

    remember_login(session, username, auto_login)

    def logout():
        perform_logout(session)

    def relogin_needed(reason):
        login_mod.clear_saved_login()
        QMessageBox.warning(session.window, '다시 로그인', f'다시 로그인해 주세요.\n{reason}')
        relaunch_to_login()
    session.on_relogin_needed = relogin_needed

    # 사용자별 설정(다크 모드, 글자 크기)을 적용
    apply_app_theme(session.settings)
    session.show_main_window(logout=logout)
    app.aboutToQuit.connect(session.close)
    app._kcs_session = session  # 가비지 컬렉션 방지
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
