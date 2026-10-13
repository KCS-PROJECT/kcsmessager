# -*- coding: utf-8 -*-
"""채팅방 화면 공용 바탕: 대화상자 틀(_Dialog) · 라벨/버튼 줄 · 시간 표기 · 아이콘 그림
chat_room.py(채팅방 창)와 room_dialogs.py(채팅방에서 여는 대화상자들)가 함께 쓴다"""


from PyQt5.QtCore import (Qt, QRectF)
from PyQt5.QtGui import (QPainter, QColor, QPixmap)
from PyQt5.QtWidgets import (QLabel, QTextEdit, QLineEdit, QDialog, QDialogButtonBox, QApplication)

from client.kakao import theme

try:  # 일부 PyQt5 빌드(macOS 휠 등)에는 접근성 이벤트 API가 없다 → 이름만 바꾸고 알림 이벤트는 생략
    from PyQt5.QtGui import QAccessible, QAccessibleEvent
except ImportError:  # pragma: no cover
    QAccessible = QAccessibleEvent = None
from client.kakao.state import (parse_dt, WEEKDAYS,
                               fmt_ampm)
from client.kakao.widgets import (paint_icon)


APP_NAME = 'KCS Talk'


# ---------------------------------------------------------------- 상수
AV = theme.AVATAR_ROW   # 프로필 크기 - 친구 · 채팅 목록 · 조직도와 같은 사진 크기 (2026-10-10)


# ---------------------------------------------------------------- 포맷 도우미
def fmt_time(ts):
    dt = parse_dt(ts)
    return fmt_ampm(dt) if dt is not None else ''


def fmt_short_date(dt):
    return f'{dt.month}월 {dt.day}일 ({WEEKDAYS[dt.weekday()]})'


def event_when(ev):
    """일정 기간 문자열: '10월 9일 (금) 오후 2:00 ~ 오후 3:00'"""
    s, e = parse_dt(ev.get('start')), parse_dt(ev.get('end'))
    if s is None:
        return ''
    e = e or s
    if ev.get('all_day'):
        if e.date() > s.date():
            return f'{fmt_short_date(s)} ~ {fmt_short_date(e)} · 종일'
        return f'{fmt_short_date(s)} · 종일'
    if e.date() == s.date():
        return f'{fmt_short_date(s)} {fmt_time(s)} ~ {fmt_time(e)}'
    return f'{fmt_short_date(s)} {fmt_time(s)} ~ {fmt_short_date(e)} {fmt_time(e)}'


def to_qcolor(value):
    """'#RRGGBB' / 'rgba(r,g,b,a)' 문자열 → QColor"""
    value = (value or '').strip()
    if value.startswith('rgba'):
        r, g, b, a = [x.strip() for x in value[5:-1].split(',')]
        col = QColor(int(r), int(g), int(b))
        col.setAlphaF(float(a))
        return col
    return QColor(value)


def _label(text='', name='', parent=None, wrap=False, rich=False):
    lab = QLabel(parent)
    if name:
        lab.setObjectName(name)
    lab.setTextFormat(Qt.RichText if rich else Qt.PlainText)
    lab.setWordWrap(wrap)
    lab.setText(text)
    return lab


def icon_pixmap(name, color, size, bg=None):
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pad = 0
    if bg:
        p.setPen(Qt.NoPen)
        p.setBrush(to_qcolor(bg))
        p.drawEllipse(QRectF(0, 0, size, size))
        pad = size * 0.24
    paint_icon(p, name, QRectF(pad, pad, size - 2 * pad, size - 2 * pad), color)
    p.end()
    return pm


# ---------------------------------------------------------------- 대화상자
class _Dialog(QDialog):
    """채팅방 대화상자 공통 (ui-styling·Radix Dialog 원칙): 열리면 첫 입력칸에 포커스,
    닫히면 연 곳(이전 포커스)으로 포커스를 돌려준다. Esc 닫기·Tab 순환은 QDialog 기본"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet(dialog_qss())
        self._opener = QApplication.focusWidget()

    def showEvent(self, event):
        super().showEvent(event)
        first = next((w for w in self.findChildren((QLineEdit, QTextEdit)) if w.isEnabled() and w.isVisibleTo(self)), None)
        if first is not None:
            first.setFocus()

    def done(self, result):
        super().done(result)
        opener = self._opener
        try:
            if opener is not None and opener.isVisible():
                opener.window().activateWindow()
                opener.setFocus()
        except RuntimeError:   # 연 위젯이 이미 지워짐
            pass


def dialog_qss():
    c = theme.c
    return f"""
        QDialog {{ background: {c('bg')}; }}
        QLabel {{ color: {c('text')}; background: transparent; }}
        QLabel#dlgHint {{ color: {c('text_sub')}; font-size: {theme.fs('meta')}px; }}
        QListWidget {{ background: {c('bg')}; color: {c('text')}; border: 1px solid {c('border')};
                      border-radius: 6px; outline: 0; }}
        QListWidget::item {{ padding: 6px; }}
        QListWidget::item:selected {{ background: {c('bg_selected')}; color: {c('text')}; }}
        QLineEdit, QTextEdit, QDateTimeEdit {{ background: {c('input_bg')}; color: {c('text')};
            border: 1px solid {c('border')}; border-radius: 6px; padding: 6px 8px; }}
        QCheckBox {{ color: {c('text')}; }}
        QPushButton {{ background: {c('bg_alt')}; color: {c('text')}; border: 1px solid {c('border')};
            border-radius: 6px; padding: 7px 14px; }}
        QPushButton:hover {{ background: {c('bg_hover')}; }}
        QPushButton:disabled {{ color: {c('text_hint')}; }}
        QPushButton#primary {{ background: {c('yellow')}; color: {theme.c('on_accent')}; border: none; font-weight: bold; }}
        QPushButton#primary:disabled {{ background: {c('bg_alt')}; color: {c('text_hint')}; }}
        QTabWidget::pane {{ border: none; }}
        QTabBar::tab {{ background: transparent; color: {c('text_sub')}; padding: 8px 16px; border: none; }}
        QTabBar::tab:selected {{ color: {c('text')}; border-bottom: 2px solid {c('text')}; font-weight: bold; }}
    """


def _buttons(dlg, ok_text):
    box = QDialogButtonBox(dlg)
    ok = box.addButton(ok_text, QDialogButtonBox.AcceptRole)
    ok.setObjectName('primary')
    ok.style().unpolish(ok)     # 버튼 박스가 이미 polish했으므로 objectName 규칙을 다시 적용
    ok.style().polish(ok)
    cancel = box.addButton('취소', QDialogButtonBox.RejectRole)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    return box, ok, cancel
