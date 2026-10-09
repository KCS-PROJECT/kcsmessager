# -*- coding: utf-8 -*-
"""
로그인 다이얼로그 - 회사 CI 네이비 배경 + ㈜케이씨에스 로고, 사용자 이름, 빠른 선택, 서버 설정(접기)
창 크기는 고정값이 아니라 레이아웃 sizeHint로 정해진다(잘림 방지).
"""

import json
import os

from PyQt5.QtCore import Qt, QRectF, QPointF, QSize
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QPixmap, QIcon, QIntValidator
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QWidget, QLayout, QSizePolicy)

from client.kakao import theme, brand

PRESET_USERS = ['홍길동', '김철수', '이영희', '박민수', '최지우']   # 최근 로그인 기록이 없을 때의 예시
RECENT_PATH = os.path.join(os.environ.get('KCS_MESSENGER_HOME') or os.path.join(os.path.expanduser('~'), '.kcs_messenger'),
                           'recent_logins.json')
MAX_RECENT = 6


def load_recent(path=None):
    """최근 로그인한 이름(최신순)"""
    try:
        with open(path or RECENT_PATH, encoding='utf-8') as f:
            names = json.load(f)
        return [n for n in names if isinstance(n, str) and n.strip()][:MAX_RECENT]
    except (OSError, ValueError):
        return []


def save_recent(name, path=None):
    path = path or RECENT_PATH
    names = [name] + [n for n in load_recent(path) if n != name]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(names[:MAX_RECENT], f, ensure_ascii=False)
    except OSError:
        pass
KAKAO_BROWN = '#3C1E1E'
LOGIN_BUTTON = '#423630'


def paint_talk_logo(p, rect, bubble_color=KAKAO_BROWN, text_color='#FEE500', text='TALK', brand='KCS'):
    """둥근 말풍선 + 꼬리 + 'TALK' 글자"""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    w, h = rect.width(), rect.height()
    body = QRectF(rect.x(), rect.y(), w, h * 0.82)
    path = QPainterPath()
    path.addEllipse(body)
    tail = QPainterPath()
    tail.moveTo(QPointF(rect.x() + w * 0.24, rect.y() + h * 0.66))
    tail.lineTo(QPointF(rect.x() + w * 0.17, rect.y() + h * 0.98))
    tail.lineTo(QPointF(rect.x() + w * 0.44, rect.y() + h * 0.77))
    tail.closeSubpath()
    path = path.united(tail)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(bubble_color))
    p.drawPath(path)
    if text:
        f = theme.font('micro', bold=True)
        f.setPixelSize(max(6, int(h * 0.26)))
        f.setLetterSpacing(f.AbsoluteSpacing, max(0.5, h * 0.01))
        main_rect = QRectF(body)
        if brand and h >= 40:
            # 'KCS'를 작게 위에, 'TALK'을 크게 아래에
            small = theme.font('micro', bold=True)
            small.setPixelSize(max(6, int(h * 0.13)))
            small.setLetterSpacing(small.AbsoluteSpacing, max(0.5, h * 0.02))
            p.setFont(small)
            p.setPen(QColor(text_color))
            p.drawText(QRectF(body.x(), body.y() + body.height() * 0.17, body.width(), body.height() * 0.2),
                       Qt.AlignCenter, brand)
            main_rect = QRectF(body.x(), body.y() + body.height() * 0.1, body.width(), body.height())
        p.setFont(f)
        p.setPen(QColor(text_color))
        p.drawText(main_rect, Qt.AlignCenter, text)
    p.restore()


def talk_icon_pixmap(size=64, with_background=True):
    """앱/트레이 아이콘: 회사 CI 아이콘(네이비 + 흰색 KCS 마크). 로고가 없으면 TALK 말풍선"""
    if with_background and brand.has_logo():
        return brand.app_icon_pixmap(size)
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    if with_background:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#FEE500'))
        p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
        m = size * 0.18
        paint_talk_logo(p, QRectF(m, m * 1.1, size - 2 * m, size - 2 * m), text='TALK' if size >= 48 else '')
    else:
        paint_talk_logo(p, QRectF(0, 0, size, size), bubble_color='#FEE500', text='')
    p.end()
    return pm


def talk_icon(size=64):
    if brand.has_logo():
        return brand.app_icon()
    return QIcon(talk_icon_pixmap(size))


class TalkLogo(QWidget):
    def __init__(self, size=96, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, int(size * 0.9))

    def paintEvent(self, event):
        p = QPainter(self)
        paint_talk_logo(p, QRectF(0, 0, self.width(), self.height()))


class LoginDialog(QDialog):
    def __init__(self, host='127.0.0.1', port=5555, username='', parent=None):
        super().__init__(parent)
        self.setWindowTitle('KCS Talk 로그인')
        self.setWindowIcon(talk_icon())
        self.setObjectName('loginDialog')

        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SetFixedSize)  # 내용에 맞춰 자동 크기(서버 설정 펼침 포함)
        root.setContentsMargins(36, 40, 36, 26)
        root.setSpacing(0)

        if brand.has_logo():
            self.logo = QLabel()
            self.logo.setPixmap(brand.logo_pixmap('vertical', 92, '#FFFFFF'))
            self.logo.setAlignment(Qt.AlignCenter)
        else:
            self.logo = TalkLogo(92)
        root.addWidget(self.logo, 0, Qt.AlignHCenter)
        root.addSpacing(18)
        title = QLabel('KCS Talk')
        title.setObjectName('loginTitle')
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)
        root.addSpacing(30)

        self.name_edit = QLineEdit(username)
        self.name_edit.setPlaceholderText('사용자 이름')
        self.name_edit.setMaxLength(20)
        self.name_edit.setMinimumWidth(280)
        root.addWidget(self.name_edit)
        root.addSpacing(10)

        recent = load_recent(getattr(self, 'recent_path', None))
        if not username and recent:
            self.name_edit.setText(recent[0])
        quick_label = QLabel('최근 로그인' if recent else '빠른 선택')
        quick_label.setObjectName('loginHint')
        root.addWidget(quick_label)
        root.addSpacing(6)
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        self.preset_buttons = []
        for i, name in enumerate(recent or PRESET_USERS):
            btn = QPushButton(name)
            btn.setObjectName('presetButton')
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAutoDefault(False)
            btn.clicked.connect(lambda _c=False, n=name: self._pick(n))
            grid.addWidget(btn, i // 3, i % 3)
            self.preset_buttons.append(btn)
        root.addLayout(grid)
        root.addSpacing(12)

        self.server_toggle = QPushButton('서버 설정  ▸')
        self.server_toggle.setObjectName('serverToggle')
        self.server_toggle.setCursor(Qt.PointingHandCursor)
        self.server_toggle.setAutoDefault(False)
        self.server_toggle.setCheckable(True)
        root.addWidget(self.server_toggle, 0, Qt.AlignLeft)

        self.server_box = QWidget()
        box = QHBoxLayout(self.server_box)
        box.setContentsMargins(0, 6, 0, 0)
        box.setSpacing(6)
        self.host_edit = QLineEdit(str(host))
        self.host_edit.setPlaceholderText('서버 주소')
        self.port_edit = QLineEdit(str(port))
        self.port_edit.setPlaceholderText('포트')
        self.port_edit.setValidator(QIntValidator(1, 65535, self))
        self.port_edit.setFixedWidth(82)
        box.addWidget(self.host_edit, 1)
        box.addWidget(self.port_edit)
        self.server_box.hide()
        root.addWidget(self.server_box)
        root.addSpacing(18)

        self.error_label = QLabel('')
        self.error_label.setObjectName('loginError')
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        root.addWidget(self.error_label)

        self.login_button = QPushButton('로그인')
        self.login_button.setObjectName('loginButton')
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setDefault(True)
        self.login_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        root.addWidget(self.login_button)
        root.addSpacing(22)
        footer = QLabel(f'KCS Talk v2.0 · {brand.COMPANY_NAME}')
        footer.setObjectName('loginFooter')
        footer.setAlignment(Qt.AlignCenter)
        root.addWidget(footer)

        self.server_toggle.toggled.connect(self._toggle_server)
        self.login_button.clicked.connect(self.accept)
        self.name_edit.textChanged.connect(self._update_state)
        self.name_edit.returnPressed.connect(self.accept)
        self._apply_style()
        self._update_state()

    def _apply_style(self):
        # 다크 모드와 무관하게 회사 CI 색(네이비)으로 고정한다
        self.setStyleSheet(f"""
            QDialog#loginDialog {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                   stop:0 #34478F, stop:1 {theme.BRAND_NAVY}); }}
            QLabel {{ color: #FFFFFF; background: transparent; }}
            QLabel#loginTitle {{ font-size: 22px; font-weight: bold; letter-spacing: 1px; }}
            QLabel#loginHint {{ font-size: 12px; color: rgba(255,255,255,0.7); }}
            QLabel#loginFooter {{ font-size: 11px; color: rgba(255,255,255,0.55); }}
            QLabel#loginError {{ font-size: 12px; color: #FFB4A8; padding-bottom: 8px; }}
            QLineEdit {{ background: #FFFFFF; color: #191919; border: 1px solid transparent; border-radius: 6px;
                         padding: 11px 12px; font-size: 14px; selection-background-color: {theme.BRAND_NAVY};
                         selection-color: #FFFFFF; }}
            QLineEdit:focus {{ border: 2px solid #8FA3E8; }}
            QPushButton#presetButton {{ background: rgba(255,255,255,0.14); color: #FFFFFF;
                         border: 1px solid rgba(255,255,255,0.22); border-radius: 14px; padding: 6px 4px; font-size: 13px; }}
            QPushButton#presetButton:hover {{ background: rgba(255,255,255,0.28); }}
            QPushButton#serverToggle {{ background: transparent; color: rgba(255,255,255,0.75); border: none;
                         padding: 2px 0; font-size: 12px; }}
            QPushButton#serverToggle:hover {{ color: #FFFFFF; }}
            QPushButton#loginButton {{ background: #FFFFFF; color: {theme.BRAND_NAVY}; border: none; border-radius: 6px;
                         padding: 12px; font-size: 15px; font-weight: bold; }}
            QPushButton#loginButton:hover {{ background: #E6EBFA; }}
            QPushButton#loginButton:disabled {{ background: rgba(255,255,255,0.25); color: rgba(255,255,255,0.7); }}
        """)

    def _pick(self, name):
        self.name_edit.setText(name)
        self.name_edit.setFocus()

    def _toggle_server(self, on):
        self.server_box.setVisible(on)
        self.server_toggle.setText('서버 설정  ▾' if on else '서버 설정  ▸')

    def _update_state(self):
        self.login_button.setEnabled(bool(self.name_edit.text().strip()))

    def show_error(self, text):
        self.error_label.setText(text or '')
        self.error_label.setVisible(bool(text))

    def values(self):
        """(username, host, port)"""
        try:
            port = int(self.port_edit.text())
        except ValueError:
            port = 5555
        return self.name_edit.text().strip(), self.host_edit.text().strip() or '127.0.0.1', port

    def accept(self):
        name, host, port = self.values()
        if not name:
            self.show_error('사용자 이름을 입력해 주세요.')
            return
        if not (1 <= port <= 65535):
            self.show_error('포트 번호가 올바르지 않습니다.')
            return
        save_recent(name, getattr(self, 'recent_path', None))
        super().accept()

    def sizeHint(self):
        return super().sizeHint().expandedTo(QSize(352, 0))
