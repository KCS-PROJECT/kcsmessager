# -*- coding: utf-8 -*-
"""
메인 창 - 왼쪽 세로 사이드바(친구/채팅/조직도/캘린더/더보기) + 탭 스택
채팅방 창 관리, 트레이 알림, 연결 끊김 배너, 토스트, 테마 즉시 적용, 자동 자리비움,
잠금모드(무입력 N분 / 수동 잠금, 앱 시작 시 잠금), 기능 둘러보기
"""

import time

from PyQt5.QtCore import Qt, QRectF, QTimer, QEvent, QObject, QPoint, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPalette, QKeySequence
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QStackedWidget, QAbstractButton, QSystemTrayIcon, QMenu,
                             QSizePolicy, QFrame, QShortcut, QDialog, QLineEdit, QListWidget,
                             QListWidgetItem)

from client.kakao import theme
from client.kakao.widgets import paint_icon, Badge
from client.kakao.login import talk_icon, talk_icon_pixmap
from client.kakao import brand
from client.kakao.chats_tab import presence_of, set_presence, user_pixmap, connect_avatar_changed

APP_TITLE = 'KCS Talk'
ORG_DOCK_WIDTH = 340          # 왼쪽 조직도 패널 폭
ORG_DOCK_MIN_WINDOW = 860     # 이 폭 이상이면 조직도 패널 자동 표시
SPLIT_MIN_WINDOW = 1180       # 이 폭 이상이면 목록 옆에 대화창을 붙여 연다 (분할 화면)
LIST_WIDTH = 380              # 분할 화면에서 목록 열의 폭
IDLE_SECONDS = 10 * 60
TAB_KEYS = ['friends', 'chats', 'org', 'calendar', 'more']
TAB_LABELS = {'friends': '친구', 'chats': '채팅', 'org': '조직도', 'calendar': '캘린더', 'more': '더보기'}
TAB_ICONS = {'friends': 'friends', 'chats': 'chat', 'org': 'building', 'calendar': 'calendar', 'more': 'more'}


# ================================================================ 테마 적용
def apply_app_theme(settings=None):
    """설정(다크 모드, 글자 크기)을 테마·팔레트·전역 스타일시트에 반영"""
    if settings is not None:
        theme.set_dark(bool(settings.get('dark_mode')))
        theme.set_brand('kcs')   # 회사 CI(KCS 블루) 고정 - 테마 색상 선택은 제공하지 않는다
        theme.set_font_scale(float(settings.get('font_scale') or 1.0))
        theme.set_reduce_motion(bool(settings.get('reduce_motion')))
    app = QApplication.instance()
    if app is None:
        return
    pal = QPalette()
    roles = {
        QPalette.Window: 'bg', QPalette.WindowText: 'text', QPalette.Base: 'input_bg',
        QPalette.AlternateBase: 'bg_alt', QPalette.Text: 'text', QPalette.Button: 'bg_alt',
        QPalette.ButtonText: 'text', QPalette.ToolTipBase: 'bg', QPalette.ToolTipText: 'text',
        QPalette.PlaceholderText: 'text_hint',
    }
    for role, key in roles.items():
        pal.setColor(role, QColor(theme.c(key)))
    pal.setColor(QPalette.Highlight, QColor(theme.c('yellow')))
    pal.setColor(QPalette.HighlightedText, QColor(theme.c('on_accent')))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor(theme.c('text_hint')))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(theme.c('text_hint')))
    app.setPalette(pal)
    app.setFont(theme.font())
    app.setStyleSheet(theme.base_qss())


# ================================================================ 사이드바
class SidebarButton(QAbstractButton):
    def __init__(self, key, parent=None):
        super().__init__(parent)
        self.key = key
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(TAB_LABELS[key])
        self.setFixedSize(64, 58)
        self._hover = False

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.isChecked():
            color = theme.c('sidebar_icon_active')
            # 선택된 탭 뒤 은은한 하이라이트(브랜드 사이드바에서 위치를 분명히)
            p.setPen(Qt.NoPen)
            p.setBrush(theme.qc('sidebar_active_bg'))
            p.drawRoundedRect(QRectF(6, 2, self.width() - 12, self.height() - 4), 12, 12)
        elif self._hover:
            color = theme.c('sidebar_icon_hover')
        else:
            color = theme.c('sidebar_icon')
        s = 24
        rect = QRectF((self.width() - s) / 2, 8, s, s)
        # 아이콘 아래 탭 이름 (왼쪽 메뉴에서 '조직도' 등을 바로 찾을 수 있게)
        f = theme.font('micro', bold=self.isChecked(), scaled=False)   # 고정 크기 사이드바 버튼 안
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(QRectF(0, 36, self.width(), 16), Qt.AlignHCenter | Qt.AlignVCenter, TAB_LABELS[self.key])
        if self.key == 'org':
            from client.kakao.org_tab import paint_building
            paint_building(p, rect, color, stroke=1.9 if self.isChecked() else 1.7)
        else:
            filled = self.isChecked() and self.key in ('friends', 'chat', 'chats')
            paint_icon(p, TAB_ICONS[self.key], rect, color, stroke=1.9 if self.isChecked() else 1.7,
                       filled=True if filled else None)


class Sidebar(QWidget):
    tab_selected = pyqtSignal(str)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setFixedWidth(64)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 16, 0, 14)
        col.setSpacing(4)
        # 회사 CI 마크
        self.logo = QLabel()
        self.logo.setObjectName('sidebarLogo')
        self.logo.setAlignment(Qt.AlignCenter)
        self.logo.setFixedHeight(36)
        self.logo.setToolTip(f'KCS Talk · {brand.COMPANY_NAME}')
        col.addWidget(self.logo)
        col.addSpacing(10)
        self._refresh_logo()
        self.buttons = {}
        for key in TAB_KEYS:
            btn = SidebarButton(key)
            btn.clicked.connect(lambda _c=False, k=key: self.tab_selected.emit(k))
            col.addWidget(btn)
            self.buttons[key] = btn
        col.addStretch(1)
        self.me_avatar = QLabel()
        self.me_avatar.setFixedSize(32, 32)
        self.me_avatar.setToolTip('내 프로필')
        col.addWidget(self.me_avatar, 0, Qt.AlignHCenter)
        self.chat_badge = Badge(0, self.buttons['chats'])
        self._place_badge()
        connect_avatar_changed(state, self.refresh_me)
        state.users_changed.connect(self.refresh_me)

    def refresh_me(self):
        if self.state.me:
            self.me_avatar.setPixmap(user_pixmap(self.state, self.state.me, 32, show_presence=True))
            self.me_avatar.setToolTip(f"{self.state.display_name(self.state.me)} · 내 프로필")

    def _place_badge(self):
        btn = self.buttons['chats']
        self.chat_badge.move(min(btn.width() - self.chat_badge.width() - 2, 36), 6)
        self.chat_badge.raise_()

    def set_unread(self, count):
        self.chat_badge.set_count(count)
        self._place_badge()
        # 스크린리더: 숫자만이 아니라 맥락 있는 문장으로 (ui-ux-pro-max: Contextual Live Badge Updates)
        self.buttons['chats'].setAccessibleName(f'채팅, 안 읽은 메시지 {count}개' if count else '채팅')

    def set_current(self, key):
        for k, btn in self.buttons.items():
            btn.setChecked(k == key)

    def _refresh_logo(self):
        # 브랜드(네이비) 사이드바: 흰 타일 + 네이비 마크 / 밝은 사이드바: 네이비 타일 + 흰 마크
        if theme.c('sidebar_logo') == '#FFFFFF':
            self.logo.setPixmap(brand.badge_pixmap(46, 34, '#FFFFFF', theme.BRAND_NAVY))
        else:
            self.logo.setPixmap(brand.badge_pixmap(46, 34, theme.BRAND_NAVY, '#FFFFFF'))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.c('sidebar')))

    def apply_theme(self):
        self._refresh_logo()
        self.chat_badge.set_count(self.chat_badge.count)
        self._place_badge()
        self.refresh_me()
        self.update()
        for btn in self.buttons.values():
            btn.update()


class QuickSwitcher(QDialog):
    """Ctrl+K - 채팅방·동료 이름(직함·부서)으로 찾아 Enter 로 바로 연다. ↑/↓ 로 고르고 Esc 로 닫는다"""

    chosen = pyqtSignal(str, str)   # 'room'|'person', room_id|username

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle('빠른 이동')
        self.setMinimumSize(420, 380)
        col = QVBoxLayout(self)
        col.setContentsMargins(theme.sp('l'), theme.sp('l'), theme.sp('l'), theme.sp('m'))
        col.setSpacing(theme.sp('s'))
        self.search = QLineEdit()
        self.search.setPlaceholderText('채팅방 또는 동료 이름 · 부서 · 직함')
        self.search.setAccessibleName('빠른 이동 검색')
        col.addWidget(self.search)
        self.list = QListWidget()
        self.list.setAccessibleName('검색 결과')
        self.list.setStyleSheet(
            f"QListWidget::item {{ padding: {theme.sp('s')}px {theme.sp('s')}px; border-radius: 8px; }}"
            f" QListWidget::item:selected {{ background: {theme.c('yellow')}; color: {theme.c('on_accent')}; }}"
            f" QListWidget::item:hover:!selected {{ background: {theme.c('bg_hover')}; color: {theme.c('text')}; }}")
        col.addWidget(self.list, 1)
        hint = QLabel('↑↓ 이동 · Enter 열기 · Esc 닫기')
        hint.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('meta')}px;")
        col.addWidget(hint)
        self.search.textChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.accept_current)
        self.list.itemActivated.connect(lambda _i: self.accept_current())
        self.search.installEventFilter(self)
        self.refresh()

    def entries(self, query=''):
        q = query.strip().lower()
        out = []
        for room in self.state.sorted_rooms():
            title = self.state.room_title(room['room_id'])
            if not q or q in title.lower():
                unread = self.state.room_unread(room['room_id'])
                out.append(('room', room['room_id'], title + (f"  ·  안 읽음 {unread}" if unread else '')))
        for u in self.state.friends(include_bots=True):
            name = self.state.display_name(u['username'])
            meta = ' · '.join(x for x in (u.get('title'), ' '.join(u.get('org_path') or []) or u.get('department'))
                              if x)
            hay = ' '.join([name, meta, u.get('account') or '']).lower()
            if not q or q in hay:
                out.append(('person', u['username'], name + (f"  ·  {meta}" if meta else '')))
        return out[:200]

    def refresh(self):
        self.list.clear()
        from client.kakao.widgets import make_icon
        icons = {'room': make_icon('chat', theme.c('text_sub'), 18), 'person': make_icon('friends', theme.c('text_sub'), 18)}
        for kind, value, label in self.entries(self.search.text()):
            item = QListWidgetItem(icons[kind], label)
            item.setData(Qt.UserRole, (kind, value))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def eventFilter(self, obj, event):
        if obj is self.search and event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Down, Qt.Key_Up):
            row = self.list.currentRow() + (1 if event.key() == Qt.Key_Down else -1)
            self.list.setCurrentRow(max(0, min(self.list.count() - 1, row)))
            return True
        return super().eventFilter(obj, event)

    def accept_current(self):
        item = self.list.currentItem()
        if item is None:
            return
        kind, value = item.data(Qt.UserRole)
        self.chosen.emit(kind, value)
        self.accept()


class RoomPlaceholder(QWidget):
    """분할 화면에서 대화를 고르기 전의 오른쪽 칸 - 회사 마크와 안내 한 줄"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), theme.qc('chat_bg'))
        mark = brand.logo_pixmap('mark', 44, theme.c('text_hint'))
        mw = mark.width() / mark.devicePixelRatio()
        mh = mark.height() / mark.devicePixelRatio()
        cx, cy = self.width() / 2, self.height() / 2
        p.setOpacity(0.55)
        p.drawPixmap(QRectF(cx - mw / 2, cy - mh - 14, mw, mh), mark, QRectF(mark.rect()))
        p.setOpacity(1.0)
        p.setPen(theme.qc('text_sub'))
        p.setFont(theme.font('emphasis', bold=True))
        p.drawText(QRectF(0, cy + 4, self.width(), 22), Qt.AlignCenter, '대화를 선택하세요')
        p.setPen(theme.qc('text_hint'))
        p.setFont(theme.font('meta'))
        p.drawText(QRectF(0, cy + 28, self.width(), 20), Qt.AlignCenter, '왼쪽 목록에서 채팅방이나 동료를 고르면 여기에 열립니다')


# ================================================================ 토스트 / 배너
class Toast(QLabel):
    """창 아래쪽에 잠깐 떴다 사라지는 안내"""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text, msec=2600):
        self.setStyleSheet(
            f"background: rgba(30,30,30,0.88); color: #FFFFFF; border-radius: 10px;"
            f" padding: 10px 16px; font-size: {theme.fs('body')}px;")
        self.setText(text)
        parent = self.parentWidget()
        from PyQt5.QtGui import QFontMetrics
        fm = QFontMetrics(theme.font('body'))
        max_w = max(160, parent.width() - 48)
        width = min(max_w, fm.horizontalAdvance(text) + 32 + 4)
        self.setFixedWidth(width)
        self.setFixedHeight(self.heightForWidth(width) if self.hasHeightForWidth() else self.sizeHint().height())
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 28)
        self.show()
        self.raise_()
        self._timer.start(msec)


class ConnectionBanner(QFrame):
    reconnect_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 8, 10, 8)
        row.setSpacing(8)
        self.label = QLabel('서버 연결이 끊어졌습니다')
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.button = QPushButton('재연결')
        self.button.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.label, 1)
        row.addWidget(self.button)
        self.button.clicked.connect(self.reconnect_clicked)
        self.apply_theme()
        self.hide()

    def apply_theme(self):
        self.setStyleSheet(
            f"ConnectionBanner {{ background: {'#4A2A28' if theme.is_dark() else '#FFF1F0'};"
            f" border-bottom: 1px solid {theme.c('border')}; }}"
            f" QLabel {{ color: {theme.c('badge')}; font-size: {theme.fs('body')}px; font-weight: bold; }}"
            f" QPushButton {{ background: {theme.c('bg')}; border: 1px solid {theme.c('border')};"
            f" border-radius: 12px; padding: 4px 12px; font-size: {theme.fs('meta')}px; }}")


# ================================================================ 자동 자리비움
class IdleWatcher(QObject):
    """앱 전체 키보드/마우스 입력을 감시해 10분 무입력 시 자동 자리비움, 입력 시 복원.
    lock_seconds(초를 돌려주는 함수, 0/None = 꺼짐)와 on_lock 을 주면 무입력 잠금도 담당한다."""

    INPUT_EVENTS = {QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.Wheel,
                    QEvent.TouchBegin}

    def __init__(self, state, idle_seconds=IDLE_SECONDS, parent=None, lock_seconds=None, on_lock=None):
        super().__init__(parent)
        self.state = state
        self.idle_seconds = idle_seconds
        self.lock_seconds = lock_seconds
        self.on_lock = on_lock
        self.last_input = time.monotonic()
        self.auto_away = False
        self.timer = QTimer(self)
        self.timer.setInterval(30 * 1000)
        self.timer.timeout.connect(self.check)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self.timer.start()

    def eventFilter(self, obj, event):
        if event.type() in self.INPUT_EVENTS:
            self.activity()
        return False

    def activity(self, now=None):
        self.last_input = time.monotonic() if now is None else now
        if self.auto_away:
            self.auto_away = False
            if presence_of(self.state, self.state.me) == 'away':
                set_presence(self.state, 'online')

    def check(self, now=None):
        now = time.monotonic() if now is None else now
        self.check_lock(now)
        if self.auto_away or not self.state.me:
            return
        if now - self.last_input >= self.idle_seconds and presence_of(self.state, self.state.me) == 'online':
            self.auto_away = True
            set_presence(self.state, 'away')

    def check_lock(self, now=None):
        """잠금 시간이 지났으면 on_lock 호출. 잠갔으면 True"""
        if self.on_lock is None or self.lock_seconds is None or getattr(self.state, 'locked', False):
            return False
        now = time.monotonic() if now is None else now
        seconds = self.lock_seconds()
        if seconds and now - self.last_input >= seconds:
            self.on_lock()
            return True
        return False

    def stop(self):
        self.timer.stop()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)


# ================================================================ 메인 창
class PlaceholderTab(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        col.addWidget(self.label)
        self.apply_theme()

    def apply_theme(self):
        self.label.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('body')}px;")


class MainWindow(QMainWindow):
    def __init__(self, state, settings, reconnect=None, server_address='', parent=None):
        super().__init__(parent)
        self.state = state
        self.settings = settings
        self.reconnect_cb = reconnect
        self.server_address = server_address
        self.room_windows = {}
        self._last_notify_room = ''
        self._quitting = False
        self._hidden_rooms = []        # 잠금 중 숨긴 채팅방 창
        self._pending_rooms = []       # 잠금 중 열라고 요청된 방
        self.feature_tour = None

        self.setWindowIcon(talk_icon())
        self.resize(400, 680)
        self.setMinimumSize(340, 520)

        central = QWidget()
        self.setCentralWidget(central)
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.sidebar = Sidebar(state)
        row.addWidget(self.sidebar)
        # 넓은 창에서는 조직도를 왼쪽에 항상 펼쳐 둔다(현재 탭이 조직도가 아닐 때)
        from client.kakao.org_tab import OrgTab
        self.org_dock = OrgTab(state, settings)
        self.org_dock.setObjectName('orgDock')
        self.org_dock.setFixedWidth(ORG_DOCK_WIDTH)
        self.org_dock.hide()
        row.addWidget(self.org_dock)
        self.dock_line = QWidget()
        self.dock_line.setFixedWidth(1)
        self.dock_line.hide()
        row.addWidget(self.dock_line)
        right = QWidget()
        right_col = QVBoxLayout(right)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)
        self.banner = ConnectionBanner()
        right_col.addWidget(self.banner)
        self.stack = QStackedWidget()
        right_col.addWidget(self.stack, 1)
        row.addWidget(right, 1)
        self.list_column = right
        # 분할 화면: 목록 | 대화창 (넓은 창에서 빈 공간 대신 대화를 바로 보여 준다)
        self.split_line = QWidget()
        self.split_line.setFixedWidth(1)
        self.split_line.hide()
        row.addWidget(self.split_line)
        self.room_pane = QStackedWidget()
        self.room_pane.hide()
        self.room_placeholder = RoomPlaceholder()
        self.room_pane.addWidget(self.room_placeholder)
        row.addWidget(self.room_pane, 1)
        self.toast = Toast(central)

        self.tabs = {}
        self._build_tabs()
        self.sidebar.tab_selected.connect(self.set_tab)
        self.set_tab('friends')

        # 상태 시그널
        state.room_opened.connect(self.open_room)
        state.rooms_changed.connect(self.refresh_unread)
        state.room_removed.connect(self._close_room_window)
        state.connection_lost.connect(self._on_connection_lost)
        state.welcomed.connect(self._on_welcomed)
        state.error.connect(self.show_toast)
        state.notify.connect(self.show_notification)
        settings.changed.connect(self._on_setting_changed)
        self.banner.reconnect_clicked.connect(self.reconnect)

        self._setup_shortcuts()
        from client.kakao.widgets import label_buttons_for_accessibility
        label_buttons_for_accessibility(self)
        self.tray = None
        self._setup_tray()
        self.idle_watcher = IdleWatcher(state, parent=self, lock_seconds=self._lock_seconds, on_lock=self.lock)
        from client.kakao.lock import LockScreen, has_pin
        self.lock_screen = LockScreen(settings, self)
        self.lock_screen.unlocked.connect(self.unlock)
        self.sidebar.refresh_me()
        self.refresh_unread()
        if has_pin(settings):    # 비밀번호가 있으면 잠긴 상태로 시작
            self.lock()

    # ---- 잠금모드 ----
    def _lock_seconds(self):
        from client.kakao.lock import has_pin, lock_minutes
        return lock_minutes(self.settings) * 60 if has_pin(self.settings) else 0

    def is_locked(self):
        return bool(getattr(self.state, 'locked', False))

    def lock(self):
        """잠금 화면을 덮고 채팅방 창을 숨긴다. 비밀번호가 없으면 False"""
        from client.kakao.lock import has_pin
        if not has_pin(self.settings):
            self.show_toast('잠금 비밀번호를 먼저 설정해 주세요')
            return False
        if self.is_locked():
            return True
        self.state.locked = True
        self._hidden_rooms = []
        for rid, win in list(self.room_windows.items()):
            try:
                if win.isVisible():
                    win.hide()
                    self._hidden_rooms.append(rid)
            except RuntimeError:
                self.room_windows.pop(rid, None)
        for dlg in (self.feature_tour,):
            try:
                if dlg is not None and dlg.isVisible():
                    dlg.hide()
            except RuntimeError:
                self.feature_tour = None
        self.toast.hide()
        self.lock_screen.show_over()
        return True

    def unlock(self):
        """잠금 해제 - 숨겼던 채팅방 창과 잠금 중 요청된 방을 다시 보여준다"""
        self.state.locked = False
        self.lock_screen.hide()
        self.idle_watcher.activity()
        hidden, self._hidden_rooms = self._hidden_rooms, []
        for rid in hidden:
            win = self.room_windows.get(rid)
            if win is not None:
                try:
                    win.show()
                except RuntimeError:
                    self.room_windows.pop(rid, None)
        pending, self._pending_rooms = self._pending_rooms, []
        for rid in pending:
            self.open_room(rid)
        return True

    # ---- 기능 둘러보기 ----
    def open_feature_tour(self):
        try:
            from client.kakao.feature_tour import FeatureTourDialog
        except Exception:   # 모듈이 없거나 깨져도 앱은 계속 동작
            self.show_toast('기능 둘러보기를 불러올 수 없습니다')
            return None
        try:
            if self.feature_tour is not None and self.feature_tour.isVisible():
                self.feature_tour.raise_()
                self.feature_tour.activateWindow()
                return self.feature_tour
        except RuntimeError:
            self.feature_tour = None
        try:
            dlg = FeatureTourDialog(self.state, self.settings, self, self)
        except Exception as e:
            self.show_toast(f'기능 둘러보기를 열 수 없습니다 ({e.__class__.__name__})')
            return None
        self.feature_tour = dlg
        dlg.show()
        dlg.raise_()
        return dlg

    # ---- 탭 ----
    def _build_tabs(self):
        from client.kakao.friends_tab import FriendsTab
        from client.kakao.chats_tab import ChatsTab
        from client.kakao.org_tab import OrgTab
        from client.kakao.more_tab import MoreTab
        self.tabs['friends'] = FriendsTab(self.state, self.settings)
        self.tabs['chats'] = ChatsTab(self.state, self.settings)
        self.tabs['org'] = OrgTab(self.state, self.settings)
        try:
            from client.kakao.calendar_tab import CalendarTab
            self.tabs['calendar'] = CalendarTab(self.state)
        except Exception as e:  # 캘린더 모듈이 없거나 오류여도 앱은 동작해야 한다
            self.tabs['calendar'] = PlaceholderTab(f'캘린더를 불러올 수 없습니다\n({e.__class__.__name__})')
        self.tabs['more'] = MoreTab(self.state, self.settings, server_address=self.server_address)
        for key in TAB_KEYS:
            self.stack.addWidget(self.tabs[key])

    def set_tab(self, key):
        if key not in self.tabs:
            return
        self.stack.setCurrentWidget(self.tabs[key])
        self.sidebar.set_current(key)
        self._update_dock()

    @staticmethod
    def _repolish_room(win):
        def apply():
            try:
                if hasattr(win, 'apply_theme'):
                    win.apply_theme()
                if hasattr(win, '_relayout_rows'):
                    win._relayout_rows()
            except RuntimeError:
                pass
        apply()
        QTimer.singleShot(0, apply)

    # ---- 키보드 ----
    SHORTCUT_HELP = [('Ctrl+1~5', '친구 · 채팅 · 조직도 · 캘린더 · 더보기'), ('Ctrl+K', '채팅방·동료 빠른 이동'),
                     ('Ctrl+N', '새 채팅'), ('Ctrl+Shift+A', '친구 추가')]

    def _setup_shortcuts(self):
        self.shortcuts = []

        def add(seq, fn):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(fn)
            self.shortcuts.append(sc)
        for i, key in enumerate(TAB_KEYS[:5], start=1):
            add(f'Ctrl+{i}', lambda k=key: self.set_tab(k))
        add('Ctrl+K', self.open_quick_switcher)
        add('Ctrl+N', lambda: self.tabs['chats'].show_create_dialog() if hasattr(self.tabs['chats'], 'show_create_dialog')
            else None)
        add('Ctrl+Shift+A', lambda: self.tabs['friends'].show_add_friend()
            if hasattr(self.tabs['friends'], 'show_add_friend') else None)
        for key, btn in self.sidebar.buttons.items():
            idx = TAB_KEYS.index(key) + 1
            btn.setToolTip(f'{TAB_LABELS[key]}  (Ctrl+{idx})')
            btn.setAccessibleName(TAB_LABELS[key])

    def open_quick_switcher(self, exec_=True):
        dlg = QuickSwitcher(self.state, self)
        dlg.chosen.connect(self._quick_open)
        if exec_:
            dlg.exec_()
        return dlg

    def _quick_open(self, kind, value):
        if kind == 'room':
            self.open_room(value)
        else:
            self.state.open_direct(value)

    def is_split(self):
        return hasattr(self, 'room_pane') and self.room_pane.isVisible()

    def _update_split(self):
        """넓은 창이면 목록 폭을 고정하고 오른쪽에 대화창 칸을 연다. 좁아지면 대화창을 별도 창으로 꺼낸다"""
        if not hasattr(self, 'room_pane'):
            return
        split = self.width() >= SPLIT_MIN_WINDOW
        if split == self.room_pane.isVisible():
            return
        if split:
            self.list_column.setFixedWidth(LIST_WIDTH)
            self.room_pane.show()
            self.split_line.show()
            self.split_line.setStyleSheet(f"background: {theme.c('border')};")
        else:
            for rid, win in list(self.room_windows.items()):
                try:
                    if win.parent() is self.room_pane:
                        self.room_pane.removeWidget(win)
                        win.setParent(None)
                        win.resize(420, 680)
                        win.show()
                        self._repolish_room(win)
                except RuntimeError:
                    self.room_windows.pop(rid, None)
            self.room_pane.hide()
            self.split_line.hide()
            self.list_column.setMinimumWidth(0)
            self.list_column.setMaximumWidth(16777215)

    def _update_dock(self):
        """창 폭이 충분하면 왼쪽에 조직도 패널 표시 (조직도 탭을 보고 있을 땐 중복이므로 숨김)"""
        if not hasattr(self, 'org_dock'):
            return
        self._update_split()
        show = self.width() >= ORG_DOCK_MIN_WINDOW and self.current_tab() != 'org'
        self.org_dock.setVisible(show)
        self.dock_line.setVisible(show)
        self.dock_line.setStyleSheet(f"background: {theme.c('border')};")

    def current_tab(self):
        widget = self.stack.currentWidget()
        for key, tab in self.tabs.items():
            if tab is widget:
                return key
        return ''

    # ---- 안 읽은 수 ----
    def refresh_unread(self):
        total = self.state.total_unread()
        self.sidebar.set_unread(total)
        self.setWindowTitle(f"{APP_TITLE} ({total})" if total else APP_TITLE)
        if self.tray is not None:
            self.tray.setToolTip(f"{APP_TITLE} - 안 읽은 메시지 {total}개" if total else APP_TITLE)

    # ---- 채팅방 창 ----
    def open_room(self, room_id):
        if not room_id or self.state.room(room_id) is None:
            return None
        if self.is_locked():     # 잠금 중에는 해제 후 연다
            if room_id not in self._pending_rooms:
                self._pending_rooms.append(room_id)
            return None
        win = self.room_windows.get(room_id)
        if win is not None:
            try:
                if self.is_split() and win.parent() is self.room_pane:
                    self.room_pane.setCurrentWidget(win)
                    win.setFocus()
                    return win
                win.showNormal()
                win.raise_()
                win.activateWindow()
                return win
            except RuntimeError:  # 이미 삭제된 C++ 객체
                self.room_windows.pop(room_id, None)
        try:
            from client.kakao.chat_room import ChatRoomWindow
        except Exception as e:
            self.show_toast(f'채팅방을 열 수 없습니다 ({e.__class__.__name__})')
            return None
        win = ChatRoomWindow(self.state, room_id)
        win.setAttribute(Qt.WA_DeleteOnClose, True)
        win.destroyed.connect(lambda _obj=None, rid=room_id: self.room_windows.pop(rid, None))
        if self.is_split():
            # 분할 화면: 오른쪽 칸에 끼워 연다
            self.room_windows[room_id] = win
            self.room_pane.addWidget(win)
            self.room_pane.setCurrentWidget(win)
            win.show()
            # 부모가 바뀌면 Qt가 채팅방 자체 스타일시트(말풍선 안쪽 여백 등)를 자식에 바로 다시 적용하지 않는다
            # → 테마를 다시 입혀 스타일을 새로 계산하고, 새 폭으로 말풍선 줄바꿈을 다시 한다
            self._repolish_room(win)
            return win
        n = len(self.room_windows) % 6
        geo = self.frameGeometry()
        screen = QApplication.desktop().availableGeometry(self)
        # 메인 창 오른쪽(공간이 없으면 왼쪽)에 열고, 여러 개면 계단식으로 비켜 놓는다
        x = geo.right() + 8
        if x + win.width() > screen.right():
            x = max(screen.left(), geo.left() - win.width() - 8)
        y = geo.top()
        x = min(x + 26 * n, max(screen.left(), screen.right() - win.width()) + 26 * n)
        y = min(y + 26 * n, max(screen.top(), screen.bottom() - win.height()) + 26 * n)
        pos = QPoint(x, y)
        win.move(pos)
        self.room_windows[room_id] = win
        win.show()
        win.raise_()
        win.activateWindow()
        return win

    def focus_message(self, room_id, msg_id):
        win = self.open_room(room_id)
        if win is not None and hasattr(win, 'focus_message'):
            win.focus_message(msg_id)

    def _close_room_window(self, room_id):
        win = self.room_windows.pop(room_id, None)
        if win is not None:
            try:
                win.close()
            except RuntimeError:
                pass

    # ---- 알림 ----
    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(talk_icon(), self)
        menu = QMenu()
        menu.addAction('KCS Talk 열기', self.bring_to_front)
        menu.addSeparator()
        menu.addAction('종료', self.quit_app)
        self.tray.setContextMenu(menu)
        self._tray_menu = menu
        self.tray.activated.connect(self._tray_activated)
        self.tray.messageClicked.connect(self._notification_clicked)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.bring_to_front()

    def bring_to_front(self):
        if self.is_locked():
            self.lock_screen.show_over()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _app_focused_on(self, room_id):
        active = QApplication.activeWindow()
        if active is None:
            return False
        win = self.room_windows.get(room_id)
        if win is not None and active is win:
            return True
        return active is self

    def should_notify(self, room_id):
        if not self.settings.get('notifications'):
            return False
        return not self._app_focused_on(room_id)

    def show_notification(self, title, body, room_id):
        if not self.should_notify(room_id):
            return False
        self._last_notify_room = room_id
        if self.tray is not None and self.tray.supportsMessages():
            self.tray.showMessage(title, body, talk_icon(), 4000)
        else:
            self.show_toast(f"{title}: {body}")
        return True

    def _notification_clicked(self):
        rid = self._last_notify_room
        self.bring_to_front()
        if rid:
            self.open_room(rid)

    def show_toast(self, text):
        self.toast.show_message(text)

    # ---- 연결 ----
    def _on_connection_lost(self, reason=''):
        self.banner.label.setText('서버 연결이 끊어졌습니다')
        self.banner.setToolTip(reason or '')
        self.banner.button.setEnabled(self.reconnect_cb is not None)
        self.banner.show()

    def _on_welcomed(self):
        self.banner.hide()
        self.sidebar.refresh_me()
        self.refresh_unread()

    def reconnect(self):
        if self.reconnect_cb is None:
            return
        self.banner.button.setEnabled(False)
        self.banner.label.setText('재연결 중…')
        QApplication.processEvents()
        try:
            result = self.reconnect_cb()
        except Exception as e:  # 재연결 콜백 오류도 배너로 보여준다
            result = (False, str(e))
        ok, message = result if isinstance(result, tuple) else (bool(result), '')
        self.banner.button.setEnabled(True)
        if ok:
            self.banner.hide()
            self.show_toast('서버에 다시 연결되었습니다')
        else:
            self.banner.label.setText('서버 연결이 끊어졌습니다')
            self.show_toast(message or '재연결에 실패했습니다')

    # ---- 테마 ----
    def _on_setting_changed(self, key):
        if key in ('dark_mode', 'font_scale', 'brand_theme'):
            self.apply_theme_all()
        elif key in ('muted_rooms',):
            self.refresh_unread()

    def apply_theme_all(self):
        apply_app_theme(self.settings)
        self.apply_theme()
        for win in list(self.room_windows.values()):
            try:
                if hasattr(win, 'apply_theme'):
                    win.apply_theme()
            except RuntimeError:
                pass

    def apply_theme(self):
        self.sidebar.apply_theme()
        self.banner.apply_theme()
        self.lock_screen.apply_theme()
        self.org_dock.apply_theme()
        self._update_dock()
        for tab in self.tabs.values():
            if hasattr(tab, 'apply_theme'):
                tab.apply_theme()
        self.refresh_unread()

    # ---- 종료 ----
    def quit_app(self):
        self._quitting = True
        self.close()

    def closeEvent(self, event):
        for win in list(self.room_windows.values()):
            try:
                win.close()
            except RuntimeError:
                pass
        self.idle_watcher.stop()
        self.state.locked = False
        if self.tray is not None:
            self.tray.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_dock()
        if self.toast.isVisible():
            self.toast.move((self.centralWidget().width() - self.toast.width()) // 2,
                            self.centralWidget().height() - self.toast.height() - 28)


__all__ = ['MainWindow', 'apply_app_theme', 'IdleWatcher', 'talk_icon_pixmap']
