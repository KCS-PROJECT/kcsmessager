# -*- coding: utf-8 -*-
"""
공용 그래픽 위젯 - 외부 이미지 없이 QPainter로 그리는 아이콘/아바타/배지
아이콘은 24x24 좌표계의 선(stroke) 아이콘이며 어떤 크기·색상으로도 렌더링된다.
"""

import hashlib
import math

from PyQt5.QtCore import Qt, QRectF, QPointF, QSize, pyqtSignal
from PyQt5.QtGui import (QPainter, QPainterPath, QPen, QColor, QIcon, QPixmap, QBrush, QLinearGradient)
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QSizePolicy

from client.kakao import theme

# KCS Ink 아바타: 채도를 눌러 네이비 CI 와 어울리는 잉크 톤 (흰 굵은 이니셜 4.5:1 이상)
AVATAR_COLORS = ['#3E5BA9', '#2F767D', '#5B4FA0', '#A2533C', '#3B7353',
                 '#8A4A78', '#5F6680', '#8C6420', '#2D6A99']


# ---------------------------------------------------------------- 아이콘
def _icon_path(name):
    """name → (QPainterPath, filled:bool). 24x24 기준 좌표"""
    p = QPainterPath()
    filled = False
    if name == 'friends':
        p.addEllipse(QRectF(8, 3.5, 8, 8))
        p.moveTo(4, 20.5)
        p.cubicTo(4, 15.5, 8, 13.5, 12, 13.5)
        p.cubicTo(16, 13.5, 20, 15.5, 20, 20.5)
        p.closeSubpath()
    elif name == 'chat':
        p.addEllipse(QRectF(3, 4, 18, 14))
        p.moveTo(7, 16.5)
        p.lineTo(5.5, 20.5)
        p.lineTo(10.5, 17.6)
    elif name == 'calendar':
        p.addRoundedRect(QRectF(3.5, 5, 17, 15.5), 2.5, 2.5)
        p.moveTo(3.5, 10)
        p.lineTo(20.5, 10)
        p.moveTo(8, 3)
        p.lineTo(8, 7)
        p.moveTo(16, 3)
        p.lineTo(16, 7)
    elif name == 'more':
        for x in (5, 12, 19):
            p.addEllipse(QPointF(x, 12), 1.6, 1.6)
        filled = True
    elif name == 'search':
        p.addEllipse(QRectF(4, 4, 12, 12))
        p.moveTo(14.5, 14.5)
        p.lineTo(20, 20)
    elif name == 'plus':
        p.moveTo(12, 5)
        p.lineTo(12, 19)
        p.moveTo(5, 12)
        p.lineTo(19, 12)
    elif name == 'add_chat':
        p.addEllipse(QRectF(3, 4, 16, 13))
        p.moveTo(6.5, 15.5)
        p.lineTo(5, 19.5)
        p.lineTo(9.5, 16.6)
        p.moveTo(18.5, 2.5)
        p.lineTo(18.5, 8.5)
        p.moveTo(15.5, 5.5)
        p.lineTo(21.5, 5.5)
    elif name == 'bell':
        p.moveTo(6, 17)
        p.lineTo(6, 11)
        p.cubicTo(6, 7, 8.5, 4.5, 12, 4.5)
        p.cubicTo(15.5, 4.5, 18, 7, 18, 11)
        p.lineTo(18, 17)
        p.lineTo(20, 18.5)
        p.lineTo(4, 18.5)
        p.closeSubpath()
        p.moveTo(10, 21)
        p.lineTo(14, 21)
    elif name == 'bell_off':
        p.addPath(_icon_path('bell')[0])
        p.moveTo(4, 4)
        p.lineTo(20, 20)
    elif name == 'pin':
        p.moveTo(9, 3.5)
        p.lineTo(15, 3.5)
        p.lineTo(14, 9.5)
        p.lineTo(17.5, 13.5)
        p.lineTo(6.5, 13.5)
        p.lineTo(10, 9.5)
        p.closeSubpath()
        p.moveTo(12, 13.5)
        p.lineTo(12, 20.5)
    elif name == 'clip':
        p.moveTo(16.5, 7)
        p.lineTo(8.5, 15)
        p.cubicTo(7.5, 16, 7.5, 17.5, 8.5, 18.3)
        p.cubicTo(9.5, 19.2, 11, 19.2, 12, 18.2)
        p.lineTo(19, 11)
        p.cubicTo(21, 9, 21, 6, 19, 4.3)
        p.cubicTo(17, 2.5, 14, 2.8, 12.3, 4.7)
        p.lineTo(5, 12)
        p.cubicTo(2.5, 14.5, 2.7, 18.5, 5, 20.5)
    elif name == 'smile':
        p.addEllipse(QRectF(3.5, 3.5, 17, 17))
        p.moveTo(8, 14)
        p.cubicTo(9.5, 16.5, 14.5, 16.5, 16, 14)
        p.addEllipse(QPointF(9, 9.8), 0.6, 0.6)
        p.addEllipse(QPointF(15, 9.8), 0.6, 0.6)
    elif name == 'image':
        p.addRoundedRect(QRectF(3.5, 4.5, 17, 15), 2, 2)
        p.addEllipse(QPointF(9, 9.5), 1.6, 1.6)
        p.moveTo(3.5, 17)
        p.lineTo(9, 12.5)
        p.lineTo(13, 16)
        p.lineTo(16, 13.5)
        p.lineTo(20.5, 17.5)
    elif name == 'file':
        p.moveTo(6, 3.5)
        p.lineTo(14, 3.5)
        p.lineTo(18.5, 8)
        p.lineTo(18.5, 20.5)
        p.lineTo(6, 20.5)
        p.closeSubpath()
        p.moveTo(14, 3.5)
        p.lineTo(14, 8)
        p.lineTo(18.5, 8)
    elif name == 'close':
        p.moveTo(6, 6)
        p.lineTo(18, 18)
        p.moveTo(18, 6)
        p.lineTo(6, 18)
    elif name == 'menu':
        for y in (6.5, 12, 17.5):
            p.moveTo(4.5, y)
            p.lineTo(19.5, y)
    elif name == 'drawer':
        p.addRoundedRect(QRectF(3.5, 8, 17, 12), 2, 2)
        p.moveTo(5.5, 8)
        p.lineTo(7.5, 4)
        p.lineTo(16.5, 4)
        p.lineTo(18.5, 8)
        p.moveTo(9.5, 12.5)
        p.lineTo(14.5, 12.5)
    elif name == 'poll':
        p.addRoundedRect(QRectF(3.5, 3.5, 17, 17), 3, 3)
        p.moveTo(8, 16.5)
        p.lineTo(8, 12)
        p.moveTo(12, 16.5)
        p.lineTo(12, 7.5)
        p.moveTo(16, 16.5)
        p.lineTo(16, 10)
    elif name == 'check':
        p.moveTo(5, 12.5)
        p.lineTo(10, 17.5)
        p.lineTo(19, 7)
    elif name == 'send':
        p.moveTo(4, 11.5)
        p.lineTo(20, 4)
        p.lineTo(13.5, 20)
        p.lineTo(11, 13.5)
        p.closeSubpath()
        p.moveTo(11, 13.5)
        p.lineTo(20, 4)
    elif name == 'clock':
        p.addEllipse(QRectF(3.5, 3.5, 17, 17))
        p.moveTo(12, 7.5)
        p.lineTo(12, 12)
        p.lineTo(15.5, 14)
    elif name == 'notice':
        p.moveTo(4, 10)
        p.lineTo(4, 14)
        p.lineTo(8, 14)
        p.lineTo(16, 18.5)
        p.lineTo(16, 5.5)
        p.lineTo(8, 10)
        p.closeSubpath()
        p.moveTo(19, 9.5)
        p.cubicTo(20.5, 11, 20.5, 13, 19, 14.5)
    elif name == 'gear':
        p.addEllipse(QRectF(9, 9, 6, 6))
        for i in range(8):
            a = i * math.pi / 4
            p.moveTo(12 + 6 * math.cos(a), 12 + 6 * math.sin(a))
            p.lineTo(12 + 8.5 * math.cos(a), 12 + 8.5 * math.sin(a))
        p.addEllipse(QRectF(6, 6, 12, 12))
    elif name == 'moon':
        p.moveTo(17.5, 15.5)
        p.cubicTo(12, 17, 7, 12, 8.5, 6)
        p.cubicTo(5, 7.5, 3.5, 11.5, 5, 15)
        p.cubicTo(7, 19.5, 13.5, 20.5, 17.5, 15.5)
    elif name == 'reply':
        p.moveTo(9.5, 5.5)
        p.lineTo(4, 11)
        p.lineTo(9.5, 16.5)
        p.moveTo(4, 11)
        p.lineTo(14, 11)
        p.cubicTo(18, 11, 20, 13.5, 20, 18.5)
    elif name == 'trash':
        p.moveTo(4.5, 6.5)
        p.lineTo(19.5, 6.5)
        p.moveTo(9.5, 6.5)
        p.lineTo(10, 3.5)
        p.lineTo(14, 3.5)
        p.lineTo(14.5, 6.5)
        p.moveTo(6.5, 6.5)
        p.lineTo(7.5, 20.5)
        p.lineTo(16.5, 20.5)
        p.lineTo(17.5, 6.5)
    elif name == 'gift':
        p.addRect(QRectF(4, 9, 16, 4))
        p.addRect(QRectF(5.5, 13, 13, 7.5))
        p.moveTo(12, 9)
        p.lineTo(12, 20.5)
        p.moveTo(12, 9)
        p.cubicTo(9, 3, 5, 6, 8.5, 9)
        p.moveTo(12, 9)
        p.cubicTo(15, 3, 19, 6, 15.5, 9)
    elif name == 'star':
        for i in range(10):
            r = 9 if i % 2 == 0 else 4
            a = -math.pi / 2 + i * math.pi / 5
            pt = QPointF(12 + r * math.cos(a), 12.5 + r * math.sin(a))
            if i == 0:
                p.moveTo(pt)
            else:
                p.lineTo(pt)
        p.closeSubpath()
    elif name == 'back':
        p.moveTo(14.5, 5)
        p.lineTo(7.5, 12)
        p.lineTo(14.5, 19)
    elif name in ('eye', 'eye_off'):
        p.moveTo(2.5, 12)
        p.cubicTo(5, 7, 8.5, 5, 12, 5)
        p.cubicTo(15.5, 5, 19, 7, 21.5, 12)
        p.cubicTo(19, 17, 15.5, 19, 12, 19)
        p.cubicTo(8.5, 19, 5, 17, 2.5, 12)
        p.closeSubpath()
        p.addEllipse(QRectF(9, 9, 6, 6))
        if name == 'eye_off':
            p.moveTo(4, 4)
            p.lineTo(20, 20)
    else:
        p.addRect(QRectF(5, 5, 14, 14))
    return p, filled


def paint_icon(painter, name, rect, color, stroke=1.7, filled=None):
    path, default_filled = _icon_path(name)
    filled = default_filled if filled is None else filled
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 24.0, rect.height() / 24.0)
    color = QColor(color)
    if filled:
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
    else:
        pen = QPen(color, stroke)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)
    painter.restore()


def make_icon(name, color=None, size=24, filled=None):
    """QIcon 생성 (HiDPI 대응: 2배 해상도로 렌더링)"""
    color = color or theme.c('text')
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    paint_icon(painter, name, QRectF(0, 0, size, size), color, filled=filled)
    painter.end()
    return QIcon(pm)


class IconButton(QPushButton):
    """아이콘만 있는 납작한 버튼"""

    def __init__(self, icon_name, tooltip='', size=22, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self._icon_size = size
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip.split('(')[0].strip() or icon_name)   # 화면낭독기용 이름
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty('flat', True)
        self.setFixedSize(size + 12, size + 12)
        self.refresh_icon()

    def refresh_icon(self, color=None):
        self.setIcon(make_icon(self.icon_name, color or theme.c('text_sub'), self._icon_size))
        self.setIconSize(QSize(self._icon_size, self._icon_size))


# ---------------------------------------------------------------- 아바타
def label_buttons_for_accessibility(root):
    """이름이 없는 버튼에 툴팁/글자를 화면낭독기 이름으로 붙인다 (아이콘만 있는 버튼 대비)"""
    from PyQt5.QtWidgets import QAbstractButton
    for btn in root.findChildren(QAbstractButton):
        if not btn.accessibleName():
            name = (btn.text() or btn.toolTip() or '').replace('&', '').strip()
            if name:
                btn.setAccessibleName(name.split('\n')[0])


def avatar_color(username):
    digest = hashlib.md5(username.encode('utf-8')).digest()
    return AVATAR_COLORS[digest[0] % len(AVATAR_COLORS)]


def avatar_pixmap(username, display_name, size, online=None):
    """카카오톡 스타일 둥근 사각형(squircle) 프로필 이미지"""
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(0, 0, size, size)
    radius = size * 0.38
    base = QColor(avatar_color(username or '?'))
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    grad = QLinearGradient(0, 0, 0, size)              # 위가 아주 조금 밝은 잉크 (광택 아닌 종이 위 농담)
    grad.setColorAt(0, base.lighter(112))
    grad.setColorAt(1, base)
    p.fillPath(path, QBrush(grad))
    # 이름 첫 글자
    initial = (display_name or username or '?')[0]
    f = theme.font(max(9, int(size * 0.36)), bold=True)
    f.setPixelSize(max(9, int(size * 0.36)))
    p.setFont(f)
    p.setPen(QColor('#FFFFFF'))
    p.drawText(rect, Qt.AlignCenter, initial)
    if online is not None:
        d = max(8, size * 0.26)
        dot = QRectF(size - d, size - d, d, d)
        p.setBrush(QColor('#3DD16B') if online else QColor('#BDBDBD'))
        p.setPen(QPen(QColor(theme.c('bg')), max(1.5, size * 0.05)))
        p.drawEllipse(dot)
    p.end()
    return pm


_photo_cache = {}


def _dot(p, size, color):
    d = max(8, size * 0.26)
    p.setBrush(QColor(color))
    p.setPen(QPen(QColor(theme.c('bg')), max(1.5, size * 0.05)))
    p.drawEllipse(QRectF(size - d, size - d, d, d))


def photo_avatar_pixmap(data, size):
    """사진 바이트 → 가운데 정사각형으로 잘라 squircle 마스크 적용. 실패 시 None"""
    from PyQt5.QtGui import QImage
    image = QImage()
    if not image.loadFromData(data):
        return None
    side = min(image.width(), image.height())
    image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), size * 0.38, size * 0.38)
    p.setClipPath(path)
    p.drawImage(QRectF(0, 0, size, size), image)
    # 증명사진은 대부분 흰 배경이라 흰 목록 위에서 테두리가 사라져 이니셜 아바타보다 작아 보인다
    # → 같은 모양의 가는 안쪽 선으로 사진 칸 크기를 드러낸다 (사진 · 빈 사진 같은 크기로 보이게, 2026-10-10)
    p.setClipping(False)
    edge = max(1.0, size / 44.0)
    p.setPen(QPen(theme.qc('avatar_ring'), edge))
    p.setBrush(Qt.NoBrush)
    inset = edge / 2
    r = size * 0.38 - inset
    p.drawRoundedRect(QRectF(inset, inset, size - edge, size - edge), r, r)
    p.end()
    return pm


def user_avatar_pixmap(state, username, size, show_presence=False):
    """프로필 사진(있으면) 또는 이니셜 아바타 + 선택적으로 상태(presence) 점"""
    from client.kakao.state import PRESENCE_COLORS
    data = state.avatar_bytes(username) if state is not None else None
    presence = state.presence_of(username) if (state is not None and show_presence) else None
    key = (username, hash(data) if data else None, size, presence, theme.is_dark(),
           state.display_name(username) if state is not None else username)
    cached = _photo_cache.get(key)
    if cached is not None:
        return cached
    base = photo_avatar_pixmap(data, size) if data else None
    if base is None:
        name = state.display_name(username) if state is not None else username
        base = avatar_pixmap(username, name, size)
    if presence:
        p = QPainter(base)
        p.setRenderHint(QPainter.Antialiasing)
        _dot(p, size, PRESENCE_COLORS.get(presence, '#BDBDBD'))
        p.end()
    if len(_photo_cache) > 500:
        _photo_cache.clear()
    _photo_cache[key] = base
    return base


def group_avatar_pixmap(members, names, size):
    """그룹 채팅방 아바타 - 최대 4명 프로필을 격자로 배치"""
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    members = list(members)[:4]
    if len(members) <= 1:
        p = QPainter(pm)
        name = members[0] if members else '?'
        p.drawPixmap(0, 0, avatar_pixmap(name, names.get(name, name), size))
        p.end()
        return pm
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    half = size // 2 - 1
    if len(members) == 2:
        spots = [(0, 0), (size - half, size - half)]
    elif len(members) == 3:
        spots = [((size - half) // 2, 0), (0, size - half), (size - half, size - half)]
    else:
        spots = [(0, 0), (size - half, 0), (0, size - half), (size - half, size - half)]
    for (x, y), member in zip(spots, members):
        p.drawPixmap(x, y, avatar_pixmap(member, names.get(member, member), half))
    p.end()
    return pm


class Avatar(QLabel):
    clicked = pyqtSignal()

    def __init__(self, username='', display_name='', size=44, online=None, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.set_user(username, display_name, online)

    def set_user(self, username, display_name='', online=None):
        self.setPixmap(avatar_pixmap(username, display_name, self._size, online))

    def set_state_user(self, state, username, show_presence=False):
        self.setPixmap(user_avatar_pixmap(state, username, self._size, show_presence))

    def set_group(self, members, names):
        self.setPixmap(group_avatar_pixmap(members, names, self._size))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class Badge(QWidget):
    """빨간 안 읽은 수 배지 (0이면 숨김, 999+ 표기)"""

    def __init__(self, count=0, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.set_count(count)

    def set_count(self, count):
        self.count = int(count or 0)
        self.text = '999+' if self.count > 999 else str(self.count)
        h = theme.px(18)
        w = max(h, theme.px(8) * len(self.text) + theme.px(10))
        self.setFixedSize(w, h)
        self.setVisible(self.count > 0)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(theme.c('badge'))))
        r = QRectF(self.rect())
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setPen(QColor('#FFFFFF'))
        p.setFont(theme.font('caption', bold=True))
        p.drawText(r, Qt.AlignCenter, self.text)
