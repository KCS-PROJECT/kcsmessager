# -*- coding: utf-8 -*-
"""
잠금모드 (명세 §8.11) - 4자리 PIN 저장/검증과 메인 창을 덮는 잠금 화면

    set_pin(settings, '1234')          # lock_salt + lock_pin_hash 저장 (sha256(salt + pin))
    verify_pin(settings, '1234')       # True
    screen = LockScreen(settings, main_window)
    screen.unlocked.connect(...)
"""

import hashlib
import hmac
import secrets

from PyQt5.QtCore import (Qt, QRectF, QEvent, QTimer, pyqtSignal, pyqtProperty, QPropertyAnimation,
                          QEasingCurve)
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QPen
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QAbstractButton

from client.kakao import theme

PIN_LENGTH = 4
LOCK_MINUTE_CHOICES = [1, 5, 10, 30]


# ================================================================ PIN 저장/검증
def hash_pin(pin, salt):
    """sha256(salt + pin) 16진 문자열"""
    return hashlib.sha256((str(salt) + str(pin)).encode('utf-8')).hexdigest()


def is_valid_pin(pin):
    pin = str(pin or '')
    return len(pin) == PIN_LENGTH and pin.isdigit() and pin.isascii()


def has_pin(settings):
    return bool(settings is not None and settings.get('lock_pin_hash') and settings.get('lock_salt'))


def set_pin(settings, pin):
    """새 PIN 저장. 4자리 숫자가 아니면 ValueError. 디스크에 저장하지 못하면 False"""
    if not is_valid_pin(pin):
        raise ValueError('비밀번호는 숫자 4자리로 입력해 주세요.')
    salt = secrets.token_hex(8)
    ok = settings.set('lock_salt', salt) is not False
    return settings.set('lock_pin_hash', hash_pin(pin, salt)) is not False and ok


def clear_pin(settings):
    settings.set('lock_pin_hash', '')
    settings.set('lock_salt', '')


def verify_pin(settings, pin):
    if not has_pin(settings) or not is_valid_pin(pin):
        return False
    return hmac.compare_digest(hash_pin(pin, settings.get('lock_salt')), settings.get('lock_pin_hash'))


def lock_minutes(settings):
    try:
        minutes = int(settings.get('lock_minutes') or 5)
    except (TypeError, ValueError):
        minutes = 5
    return max(1, minutes)


# ================================================================ 잠금 화면
class PinDots(QWidget):
    """입력한 자리 수만큼 채워지는 동그라미 4개. shift 속성으로 좌우 흔들림"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.count = 0
        self.error = False
        self._shift = 0.0
        self.setFixedSize(4 * 18 + 3 * 18, 24)

    def _get_shift(self):
        return self._shift

    def _set_shift(self, value):
        self._shift = value
        self.update()

    shift = pyqtProperty(float, _get_shift, _set_shift)

    def set_count(self, count, error=False):
        self.count = count
        self.error = error
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        d = 14
        gap = (self.width() - PIN_LENGTH * d) / (PIN_LENGTH - 1)
        color = QColor('#FF8A80') if self.error else QColor('#FFFFFF')
        for i in range(PIN_LENGTH):
            r = QRectF(i * (d + gap) + self._shift, (self.height() - d) / 2, d, d)
            if i < self.count:
                p.setPen(Qt.NoPen)
                p.setBrush(color)
            else:
                p.setPen(QPen(color, 1.6))
                p.setBrush(Qt.NoBrush)
                r = r.adjusted(0.8, 0.8, -0.8, -0.8)
            p.drawEllipse(r)


class PinKey(QAbstractButton):
    """둥근 숫자 키"""

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedSize(68, 68)
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
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        alpha = 0.30 if self.isDown() else (0.20 if self._hover else 0.11)
        if self.text() not in ('', '⌫'):
            bg = QColor(255, 255, 255)
            bg.setAlphaF(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawEllipse(r)
        elif self.isDown() or self._hover:
            bg = QColor(255, 255, 255)
            bg.setAlphaF(alpha * 0.6)
            p.setPen(Qt.NoPen)
            p.setBrush(bg)
            p.drawEllipse(r)
        f = theme.font('numeral' if self.text() != '⌫' else 'display', scaled=False)   # 고정 크기 원 안
        p.setFont(f)
        p.setPen(QColor('#FFFFFF'))
        p.drawText(r, Qt.AlignCenter, self.text())


class LockScreen(QWidget):
    """부모(메인 창) 전체를 덮는 잠금 화면 - 회사 로고, PIN 4자리 키패드, 틀리면 흔들림"""

    unlocked = pyqtSignal()
    failed = pyqtSignal()

    def __init__(self, settings, parent):
        super().__init__(parent)
        self.settings = settings
        self.entered = ''
        self.attempts = 0
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setObjectName('lockScreen')

        col = QVBoxLayout(self)
        col.setContentsMargins(24, 40, 24, 32)
        col.setSpacing(0)
        col.addStretch(2)
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignCenter)
        col.addWidget(self.logo)
        col.addSpacing(22)
        self.title = QLabel('KCS Talk이 잠겨 있습니다')
        self.title.setAlignment(Qt.AlignCenter)
        col.addWidget(self.title)
        col.addSpacing(6)
        self.hint = QLabel('비밀번호 4자리를 입력해 주세요')
        self.hint.setAlignment(Qt.AlignCenter)
        col.addWidget(self.hint)
        col.addSpacing(20)
        dots_row = QHBoxLayout()
        dots_row.addStretch(1)
        self.dots = PinDots()
        dots_row.addWidget(self.dots)
        dots_row.addStretch(1)
        col.addLayout(dots_row)
        col.addSpacing(28)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)
        self.keys = {}
        labels = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '', '0', '⌫']
        for i, label in enumerate(labels):
            key = PinKey(label)
            if label == '':
                key.setEnabled(False)
            elif label == '⌫':
                key.setToolTip('지우기')
                key.clicked.connect(self.backspace)
            else:
                key.clicked.connect(lambda _c=False, d=label: self.press_digit(d))
            self.keys[label] = key
            grid.addWidget(key, i // 3, i % 3)
        grid_row = QHBoxLayout()
        grid_row.addStretch(1)
        grid_row.addLayout(grid)
        grid_row.addStretch(1)
        col.addLayout(grid_row)
        col.addStretch(3)

        self._shake = QPropertyAnimation(self.dots, b'shift', self)
        self._shake.setDuration(420)
        self._shake.setEasingCurve(QEasingCurve.Linear)
        for t, v in ((0, 0), (0.12, -14), (0.3, 12), (0.48, -9), (0.66, 6), (0.84, -3), (1.0, 0)):
            self._shake.setKeyValueAt(t, float(v))
        self._clear_timer = QTimer(self)
        self._clear_timer.setSingleShot(True)
        self._clear_timer.timeout.connect(self._reset_after_error)

        parent.installEventFilter(self)
        self.apply_theme()
        self.hide()

    # ---- 표시 ----
    def apply_theme(self):
        from client.kakao import brand
        self.logo.setPixmap(brand.logo_pixmap('horizontal', 34, '#FFFFFF'))
        self.logo.setToolTip(getattr(brand, 'COMPANY_NAME', ''))
        self.title.setStyleSheet(f"color: #FFFFFF; font-size: {theme.fs('heading')}px; font-weight: bold;"
                                 f" background: transparent;")
        self._set_hint(self.hint.text(), error=False)
        self.update()

    def _set_hint(self, text, error=False):
        self.hint.setText(text)
        self.hint.setStyleSheet(f"color: {'#FFB3AD' if error else 'rgba(255,255,255,0.72)'};"
                                f" font-size: {theme.fs('body')}px; background: transparent;")

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        if theme.is_dark():
            grad.setColorAt(0, QColor('#1A2142'))
            grad.setColorAt(1, QColor('#0E1224'))
        else:
            grad.setColorAt(0, QColor('#33478F'))
            grad.setColorAt(1, QColor(theme.BRAND_NAVY).darker(135))
        p.fillRect(self.rect(), grad)

    def show_over(self):
        """부모 전체를 덮고 앞으로 가져와 키 입력을 받는다"""
        self.entered = ''
        self.dots.set_count(0)
        self._set_hint('비밀번호 4자리를 입력해 주세요')
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.show()
        self.raise_()
        self.setFocus(Qt.OtherFocusReason)

    def hideEvent(self, event):
        """가려지면(창을 숨기거나 최소화) 흔들림 · 지우기 타이머를 멈춘다 - 보이지 않는 위젯을 계속 다시 그리지 않게.
        (macOS CI 에서 흔들림 도중 창을 숨기고 앱 스타일을 다시 입히면 Qt 안에서 Bus error 가 났다)"""
        self._shake.stop()
        self.dots.shift = 0.0
        if self._clear_timer.isActive():
            self._clear_timer.stop()
            self._reset_after_error()
        super().hideEvent(event)

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() == QEvent.Resize and self.isVisible():
            self.setGeometry(obj.rect())
            self.raise_()
        return False

    # ---- 입력 ----
    def press_digit(self, digit):
        if self._clear_timer.isActive():
            self._reset_after_error()
        if len(self.entered) >= PIN_LENGTH or not str(digit).isdigit():
            return
        self.entered += str(digit)
        self.dots.set_count(len(self.entered))
        if len(self.entered) == PIN_LENGTH:
            self._submit()

    def backspace(self):
        if self._clear_timer.isActive():
            self._reset_after_error()
            return
        self.entered = self.entered[:-1]
        self.dots.set_count(len(self.entered))

    def _submit(self):
        if verify_pin(self.settings, self.entered):
            self.entered = ''
            self.attempts = 0
            self.dots.set_count(0)
            self.hide()
            self.unlocked.emit()
            return
        self.attempts += 1
        self.dots.set_count(PIN_LENGTH, error=True)
        self._set_hint('비밀번호가 일치하지 않습니다', error=True)
        self.shake()
        self.failed.emit()
        self._clear_timer.start(650)

    def _reset_after_error(self):
        self._clear_timer.stop()
        self.entered = ''
        self.dots.set_count(0)

    def shake(self):
        self._shake.stop()
        self._shake.start()

    def is_shaking(self):
        return self._shake.state() == QPropertyAnimation.Running

    def keyPressEvent(self, event):
        text = event.text()
        if text and text.isdigit() and text.isascii():
            self.press_digit(text)
        elif event.key() == Qt.Key_Backspace:
            self.backspace()
        else:
            event.accept()   # 잠금 중에는 다른 단축키를 삼킨다

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        event.accept()


__all__ = ['hash_pin', 'set_pin', 'clear_pin', 'verify_pin', 'has_pin', 'is_valid_pin', 'lock_minutes',
           'LockScreen', 'LOCK_MINUTE_CHOICES', 'PIN_LENGTH']
