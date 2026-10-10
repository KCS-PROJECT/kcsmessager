# -*- coding: utf-8 -*-
"""
채팅방 배경화면 - 단색/그라데이션/이미지, 전체 기본값 + 방별 덮어쓰기
설정 형식은 claudedocs/KAKAO_FEATURE_SPEC.md 7.5 참고
"""

import os

from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QLinearGradient, QPixmap, QPainterPath, QPen
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QGridLayout, QFileDialog, QWidget, QSizePolicy)

from client.kakao import theme, osenv

COLOR_PRESETS = ['#BACEE0', '#9BBBD4', '#C4D7B2', '#F5E1A4', '#F7C8C8',
                 '#D9CFF0', '#E8E8E8', '#3A4A5C', '#2B2F33', '#1E1E1E']
GRADIENT_PRESETS = [['#A1C4FD', '#C2E9FB'], ['#FBC2EB', '#A6C1EE'], ['#FDDB92', '#D1FDFF'],
                    ['#84FAB0', '#8FD3F4'], ['#30CFD0', '#330867'], ['#232526', '#414345']]

_image_cache = {}


def resolve_wallpaper(settings, room_id=None):
    """방별 설정 → 전체 설정 → None(테마 기본) 순서로 결정"""
    if settings is None:
        return None
    if room_id:
        per_room = settings.get('room_wallpapers') or {}
        if per_room.get(room_id):
            return per_room[room_id]
    return settings.get('chat_wallpaper') or None


def is_dark_wallpaper(spec):
    """배경이 어두운지 (말풍선 밖 글자색 결정용)"""
    if not spec:
        return theme.is_dark()
    if spec.get('type') == 'color':
        return QColor(spec['value']).lightness() < 128
    if spec.get('type') == 'brand':
        return spec.get('value') == 'dark'
    if spec.get('type') == 'gradient':
        colors = [QColor(v) for v in spec['value']]
        return sum(c.lightness() for c in colors) / len(colors) < 128
    return True  # 사진은 어둡다고 가정 → 반투명 칩 + 흰 글자


def _load_image(path):
    pm = _image_cache.get(path)
    if pm is None:
        pm = QPixmap(path)
        if pm.isNull():
            return None
        _image_cache[path] = pm
    return pm


def paint_wallpaper(painter, rect, spec):
    """rect 영역에 배경을 그린다. spec이 None/잘못되면 테마 기본 배경"""
    rect = QRectF(rect)
    kind = (spec or {}).get('type')
    if kind == 'color':
        painter.fillRect(rect, QColor(spec['value']))
        return
    if kind == 'gradient' and len(spec.get('value') or []) >= 2:
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        values = spec['value']
        for i, value in enumerate(values):
            grad.setColorAt(i / (len(values) - 1), QColor(value))
        painter.fillRect(rect, grad)
        return
    if kind == 'brand':
        _paint_brand(painter, rect, spec.get('value') == 'dark')
        return
    if kind == 'image':
        pm = _load_image(spec.get('value', ''))
        if pm is not None:
            # 꽉 차게(cover) 가운데 정렬
            scaled = pm.size().scaled(rect.size().toSize(), Qt.KeepAspectRatioByExpanding)
            x = rect.x() + (rect.width() - scaled.width()) / 2
            y = rect.y() + (rect.height() - scaled.height()) / 2
            painter.save()
            painter.setClipRect(rect)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawPixmap(QRectF(x, y, scaled.width(), scaled.height()), pm, QRectF(pm.rect()))
            painter.fillRect(rect, QColor(0, 0, 0, 40))  # 말풍선 가독성용 살짝 어둡게
            painter.restore()
            return
    painter.fillRect(rect, theme.qc('chat_bg'))


def _paint_brand(painter, rect, dark):
    """회사 CI 배경: 은은한 그라데이션 + 가운데 큰 KCS 마크 워터마크"""
    from client.kakao import brand
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    if dark:
        grad.setColorAt(0, QColor('#2F3F7E'))
        grad.setColorAt(1, QColor('#1B2448'))
    else:
        grad.setColorAt(0, QColor('#EEF1F8'))
        grad.setColorAt(1, QColor('#D9E0EE'))
    painter.fillRect(rect, grad)
    size = max(10, int(min(rect.width() * 0.55, rect.height() * 0.32)))
    mark = brand.logo_pixmap('mark', max(8, size // 2), '#FFFFFF' if dark else theme.BRAND_NAVY)
    mw = mark.width() / mark.devicePixelRatio()
    mh = mark.height() / mark.devicePixelRatio()
    painter.save()
    painter.setOpacity(0.10 if dark else 0.07)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawPixmap(QRectF(rect.center().x() - mw / 2, rect.center().y() - mh / 2, mw, mh), mark,
                       QRectF(mark.rect()))
    painter.restore()


class _Swatch(QWidget):
    """배경 미리보기 칸 (클릭 가능)"""

    clicked = pyqtSignal(object)

    def __init__(self, spec, label='', parent=None):
        super().__init__(parent)
        self.spec = spec
        self.label = label
        self.selected = False
        self.setFixedSize(64, 88)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(label or '')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(3, 3, self.width() - 6, self.height() - 6)
        path = QPainterPath()
        path.addRoundedRect(r, 8, 8)
        p.save()
        p.setClipPath(path)
        paint_wallpaper(p, r, self.spec)
        # 말풍선 미리보기
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#FFFFFF'))
        p.drawRoundedRect(QRectF(r.x() + 6, r.y() + 14, 30, 11), 5, 5)
        p.setBrush(QColor(theme.c('bubble_mine')))
        p.drawRoundedRect(QRectF(r.right() - 34, r.y() + 32, 28, 11), 5, 5)
        p.restore()
        if self.label:
            p.setPen(QColor('#FFFFFF') if is_dark_wallpaper(self.spec) else QColor('#333333'))
            p.setFont(theme.font('micro', bold=True))
            p.drawText(r.adjusted(0, 0, 0, -6), Qt.AlignHCenter | Qt.AlignBottom, self.label)
        pen = QPen(QColor(theme.c('yellow_dark')) if self.selected else QColor(theme.c('border')),
                   3 if self.selected else 1)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def mousePressEvent(self, event):
        self.clicked.emit(self.spec)


class WallpaperDialog(QDialog):
    """배경화면 선택. room_id가 있으면 해당 방에만, 없으면 전체 기본값으로 저장"""

    def __init__(self, settings, room_id=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.room_id = room_id
        self.setWindowTitle('채팅방 배경화면' if room_id else '배경화면 (전체)')
        self.current = self._stored()
        self.swatches = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        title = QLabel('이 채팅방의 배경화면' if room_id else '모든 채팅방의 기본 배경화면')
        title.setFont(theme.font('title', bold=True))
        layout.addWidget(title)

        self.preview = _Preview(self)
        layout.addWidget(self.preview)

        layout.addWidget(self._section_label('색상'))
        grid = QGridLayout()
        grid.setSpacing(6)
        specs = [None] + [{'type': 'color', 'value': c} for c in COLOR_PRESETS]
        for i, spec in enumerate(specs):
            sw = _Swatch(spec, '기본' if spec is None else '')
            sw.clicked.connect(self._choose)
            self.swatches.append(sw)
            grid.addWidget(sw, i // 6, i % 6)
        layout.addLayout(grid)

        layout.addWidget(self._section_label('KCS 브랜드'))
        brand_row = QHBoxLayout()
        brand_row.setSpacing(6)
        for value, label in (('light', 'KCS 라이트'), ('dark', 'KCS 네이비')):
            sw = _Swatch({'type': 'brand', 'value': value}, label)
            sw.clicked.connect(self._choose)
            self.swatches.append(sw)
            brand_row.addWidget(sw)
        brand_row.addStretch()
        layout.addLayout(brand_row)

        layout.addWidget(self._section_label('그라데이션'))
        grad_row = QHBoxLayout()
        grad_row.setSpacing(6)
        for values in GRADIENT_PRESETS:
            sw = _Swatch({'type': 'gradient', 'value': values})
            sw.clicked.connect(self._choose)
            self.swatches.append(sw)
            grad_row.addWidget(sw)
        grad_row.addStretch()
        layout.addLayout(grad_row)

        image_row = QHBoxLayout()
        self.image_btn = QPushButton('사진 선택…')
        self.image_btn.clicked.connect(self._pick_image)
        image_row.addWidget(self.image_btn)
        self.image_label = QLabel('')
        self.image_label.setStyleSheet(f"color: {theme.c('text_sub')};")
        image_row.addWidget(self.image_label, 1)
        layout.addLayout(image_row)

        buttons = QHBoxLayout()
        if room_id:
            reset = QPushButton('전체 기본값 사용')
            reset.clicked.connect(self._use_global)
            buttons.addWidget(reset)
        buttons.addStretch()
        cancel = QPushButton('취소')
        cancel.clicked.connect(self.reject)
        ok = QPushButton('적용')
        ok.setProperty('primary', True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)
        self._refresh()

    def _section_label(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"color: {theme.c('text_sub')}; font-weight: bold;")
        return label

    def _stored(self):
        if self.room_id:
            return (self.settings.get('room_wallpapers') or {}).get(self.room_id)
        return self.settings.get('chat_wallpaper')

    def _choose(self, spec):
        self.current = spec
        self._refresh()

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(self, '배경 사진 선택', osenv.user_dir('pictures'),
                                              '이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)')
        if path:
            self.choose_image(path)

    def choose_image(self, path):
        if QPixmap(path).isNull():
            self.image_label.setText('이미지를 열 수 없습니다')
            return False
        self.current = {'type': 'image', 'value': os.path.abspath(path)}
        self._refresh()
        return True

    def _use_global(self):
        self.current = None
        self.accept()

    def _refresh(self):
        for sw in self.swatches:
            sw.selected = sw.spec == self.current
            sw.update()
        is_image = (self.current or {}).get('type') == 'image'
        self.image_label.setText(os.path.basename(self.current['value']) if is_image else '')
        self.preview.spec = self.current if self.current is not None else (
            resolve_wallpaper(self.settings) if self.room_id else None)
        self.preview.update()

    def accept(self):
        if self.room_id:
            per_room = self.settings.get('room_wallpapers') or {}
            if self.current is None:
                per_room.pop(self.room_id, None)
            else:
                per_room[self.room_id] = self.current
            self.settings.set('room_wallpapers', per_room)
        else:
            self.settings.set('chat_wallpaper', self.current)
        super().accept()


class _Preview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(r, 10, 10)
        p.setClipPath(path)
        paint_wallpaper(p, r, self.spec)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.c('bubble_other')))
        p.drawRoundedRect(QRectF(16, 20, 150, 30), 12, 12)
        p.setBrush(QColor(theme.c('bubble_mine')))
        p.drawRoundedRect(QRectF(r.right() - 140, 64, 124, 30), 12, 12)
        p.setFont(theme.font('meta'))
        p.setPen(QColor(theme.c('bubble_text')))
        p.drawText(QRectF(28, 20, 140, 30), Qt.AlignVCenter, '배경화면 미리보기')
        p.setPen(QColor(theme.c('bubble_mine_text')))
        p.drawText(QRectF(r.right() - 128, 64, 112, 30), Qt.AlignVCenter, '좋아요 👍')
