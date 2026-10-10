# -*- coding: utf-8 -*-
"""
방해금지 (명세 §10.1, 클라이언트 전용) - 알림 일시중지 · 근무 시간 알림 · VIP 예외

- 설정 `dnd_until`: ISO 시각까지 알림 일시중지 ('' = 사용 안 함, DND_FOREVER = 직접 끌 때까지)
- 설정 `work_hours`: {enabled, days:[0=월..6=일], start:'HH:MM', end:'HH:MM'} - 근무 시간 밖에는 알림 없음
- 설정 `vip_users`: 방해금지 중에도 알림을 받는 사람
방해금지 중에도 안 읽은 수·아이콘 깜박임은 그대로이고, 데스크톱 알림만 막는다.
"""

from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
                             QTimeEdit, QComboBox, QListWidget, QListWidgetItem)

from client.kakao import theme

DND_FOREVER = '9999-12-31T23:59:59'
DEFAULT_WORK_HOURS = {'enabled': False, 'days': [0, 1, 2, 3, 4], 'start': '09:00', 'end': '18:00'}
DAY_LABELS = '월화수목금토일'
VIP_MAX = 30
PAUSE_PRESETS = [('30분', 30), ('1시간', 60), ('2시간', 120), ('내일 오전 9시까지', 'tomorrow'),
                 ('직접 끌 때까지', 'forever')]


def _parse_hhmm(text, default):
    try:
        h, m = str(text).split(':')
        h, m = int(h), int(m)
        if 0 <= h < 24 and 0 <= m < 60:
            return h * 60 + m
    except (ValueError, TypeError):
        pass
    return default


def work_hours(settings):
    value = (settings.get('work_hours') if settings else None) or {}
    out = dict(DEFAULT_WORK_HOURS)
    if isinstance(value, dict):
        out.update({k: value[k] for k in DEFAULT_WORK_HOURS if k in value})
    out['days'] = sorted({int(d) for d in out.get('days') or [] if str(d).isdigit() and 0 <= int(d) <= 6})
    return out


def in_work_hours(settings, now=None):
    """근무 시간 알림을 켰을 때 지금이 근무 시간인지. 꺼져 있으면 항상 True"""
    wh = work_hours(settings)
    if not wh.get('enabled'):
        return True
    now = now or datetime.now()
    start = _parse_hhmm(wh['start'], 9 * 60)
    end = _parse_hhmm(wh['end'], 18 * 60)
    minute = now.hour * 60 + now.minute
    if start == end:
        return now.weekday() in wh['days']   # 시작=끝이면 그 요일 하루 종일
    if start < end:
        return now.weekday() in wh['days'] and start <= minute < end
    # 밤샘 근무 (예: 22:00~06:00): 자정 넘은 부분은 전날 요일로 본다
    if minute >= start:
        return now.weekday() in wh['days']
    if minute < end:
        return (now.weekday() - 1) % 7 in wh['days']
    return False


def paused_until(settings, now=None):
    """알림 일시중지가 끝나는 시각 (일시중지 중이 아니면 None)"""
    value = settings.get('dnd_until') if settings else ''
    if not value:
        return None
    try:
        until = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return until if until > (now or datetime.now()) else None


def dnd_reason(settings, now=None):
    """'pause' (일시중지) | 'off_hours' (근무 시간 밖) | '' (알림 받음)"""
    now = now or datetime.now()
    if paused_until(settings, now) is not None:
        return 'pause'
    if not in_work_hours(settings, now):
        return 'off_hours'
    return ''


def is_vip(settings, username):
    return bool(settings) and username in (settings.get('vip_users') or [])


def suppresses(settings, sender, now=None):
    """이 보낸 사람의 메시지 알림을 방해금지가 막는지 (VIP 는 통과)"""
    return bool(dnd_reason(settings, now)) and not is_vip(settings, sender)


def pause_until_for(preset, now=None):
    """일시중지 프리셋(분 | 'tomorrow' | 'forever') → dnd_until 값"""
    now = now or datetime.now()
    if preset == 'forever':
        return DND_FOREVER
    if preset == 'tomorrow':
        target = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        target = now + timedelta(minutes=int(preset))
    return target.replace(microsecond=0).isoformat()


def pause(settings, preset, now=None):
    settings.set('dnd_until', pause_until_for(preset, now))


def resume(settings):
    settings.set('dnd_until', '')


def status_text(settings, now=None):
    """설정 행·트레이에 보이는 한 줄 요약"""
    now = now or datetime.now()
    until = paused_until(settings, now)
    if until is not None:
        if str(settings.get('dnd_until')) == DND_FOREVER:
            return '알림 일시중지 중 · 직접 끌 때까지'
        when = until.strftime('%H:%M') if until.date() == now.date() else f"{until.month}/{until.day} {until.strftime('%H:%M')}"
        return f'알림 일시중지 중 · {when}까지'
    wh = work_hours(settings)
    if wh.get('enabled'):
        days = ''.join(DAY_LABELS[d] for d in wh['days']) or '요일 없음'
        prefix = '근무 시간 밖 · 알림 꺼짐' if not in_work_hours(settings, now) else '근무 시간 알림'
        return f"{prefix} ({days} {wh['start']}~{wh['end']})"
    return '사용 안 함'


class DndDialog(QDialog):
    """방해금지 설정 창: 일시중지 · 근무 시간 · VIP"""

    def __init__(self, state, settings, parent=None):
        super().__init__(parent)
        self.state = state
        self.settings = settings
        self.setWindowTitle('방해금지')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        title = QLabel('방해금지')
        title.setStyleSheet(f"font-size: {theme.fs('lead')}px; font-weight: bold;")
        layout.addWidget(title)
        self.status_label = QLabel('')
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
        layout.addWidget(self.status_label)

        # ---- 알림 일시중지 ----
        layout.addWidget(self._section('알림 일시중지'))
        pause_row = QHBoxLayout()
        pause_row.setSpacing(6)
        self.pause_buttons = []
        for label, preset in PAUSE_PRESETS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, p=preset: self._pause(p))
            pause_row.addWidget(btn)
            self.pause_buttons.append(btn)
        pause_row.addStretch(1)
        layout.addLayout(pause_row)
        self.resume_button = QPushButton('일시중지 끄기')
        self.resume_button.clicked.connect(self._resume)
        layout.addWidget(self.resume_button, 0, Qt.AlignLeft)

        # ---- 근무 시간 ----
        layout.addWidget(self._section('근무 시간에만 알림 받기'))
        wh = work_hours(settings)
        self.work_check = QCheckBox('근무 시간 밖에는 알림 끄기')
        self.work_check.setChecked(bool(wh['enabled']))
        layout.addWidget(self.work_check)
        day_row = QHBoxLayout()
        day_row.setSpacing(4)
        self.day_checks = []
        for i, ch in enumerate(DAY_LABELS):
            box = QCheckBox(ch)
            box.setChecked(i in wh['days'])
            box.toggled.connect(self._save_work_hours)
            day_row.addWidget(box)
            self.day_checks.append(box)
        day_row.addStretch(1)
        layout.addLayout(day_row)
        time_row = QHBoxLayout()
        self.start_edit = QTimeEdit(QTime.fromString(wh['start'], 'HH:mm'))
        self.end_edit = QTimeEdit(QTime.fromString(wh['end'], 'HH:mm'))
        for edit in (self.start_edit, self.end_edit):
            edit.setDisplayFormat('HH:mm')
            edit.timeChanged.connect(self._save_work_hours)
        time_row.addWidget(self.start_edit)
        time_row.addWidget(QLabel('~'))
        time_row.addWidget(self.end_edit)
        time_row.addStretch(1)
        layout.addLayout(time_row)
        self.work_check.toggled.connect(self._save_work_hours)

        # ---- VIP ----
        layout.addWidget(self._section('VIP - 방해금지 중에도 알림 받기'))
        vip_row = QHBoxLayout()
        self.vip_combo = QComboBox()
        self.vip_combo.setEditable(False)
        self.vip_add_button = QPushButton('추가')
        self.vip_add_button.setProperty('primary', True)
        self.vip_add_button.clicked.connect(self._add_vip_from_combo)
        vip_row.addWidget(self.vip_combo, 1)
        vip_row.addWidget(self.vip_add_button)
        layout.addLayout(vip_row)
        self.vip_list = QListWidget()
        self.vip_list.setMaximumHeight(theme.px(140))
        layout.addWidget(self.vip_list)
        self.vip_remove_button = QPushButton('선택한 VIP 빼기')
        self.vip_remove_button.clicked.connect(self._remove_selected_vip)
        layout.addWidget(self.vip_remove_button, 0, Qt.AlignLeft)

        hint = QLabel('방해금지 중에도 안 읽은 메시지 수와 아이콘 깜박임은 그대로 표시됩니다.')
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('meta')}px;")
        layout.addWidget(hint)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close = QPushButton('닫기')
        close.clicked.connect(self.accept)
        close_row.addWidget(close)
        layout.addLayout(close_row)
        self.refresh()

    def _section(self, text):
        label = QLabel(text)
        label.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px; font-weight: bold;"
                            f" padding-top: 6px;")
        return label

    # ---- 동작 ----
    def _pause(self, preset):
        pause(self.settings, preset)
        self.refresh()

    def _resume(self):
        resume(self.settings)
        self.refresh()

    def _save_work_hours(self, *_args):
        self.settings.set('work_hours', {
            'enabled': self.work_check.isChecked(),
            'days': [i for i, box in enumerate(self.day_checks) if box.isChecked()],
            'start': self.start_edit.time().toString('HH:mm'),
            'end': self.end_edit.time().toString('HH:mm'),
        })
        self.refresh()

    def vips(self):
        return list(self.settings.get('vip_users') or [])

    def add_vip(self, username):
        vips = self.vips()
        if not username or username in vips or username == getattr(self.state, 'me', None) or len(vips) >= VIP_MAX:
            return False
        self.settings.set('vip_users', vips + [username])
        self.refresh()
        return True

    def remove_vip(self, username):
        self.settings.set('vip_users', [u for u in self.vips() if u != username])
        self.refresh()

    def _add_vip_from_combo(self):
        self.add_vip(self.vip_combo.currentData())

    def _remove_selected_vip(self):
        item = self.vip_list.currentItem()
        if item is not None:
            self.remove_vip(item.data(Qt.UserRole))

    def _candidates(self):
        users = getattr(self.state, 'users', {}) or {}
        vips = set(self.vips())
        out = []
        for name, user in users.items():
            if name == self.state.me or name in vips or user.get('is_bot'):
                continue
            out.append((user.get('display_name') or name, name))
        return sorted(out)

    def refresh(self):
        self.status_label.setText(f'현재: {status_text(self.settings)}')
        self.resume_button.setEnabled(paused_until(self.settings) is not None)
        enabled = self.work_check.isChecked()
        for w in self.day_checks + [self.start_edit, self.end_edit]:
            w.setEnabled(enabled)
        self.vip_combo.clear()
        for label, name in self._candidates():
            self.vip_combo.addItem(label, name)
        self.vip_add_button.setEnabled(self.vip_combo.count() > 0 and len(self.vips()) < VIP_MAX)
        self.vip_list.clear()
        users = getattr(self.state, 'users', {}) or {}
        for name in self.vips():
            item = QListWidgetItem((users.get(name) or {}).get('display_name') or name)
            item.setData(Qt.UserRole, name)
            self.vip_list.addItem(item)
        self.vip_remove_button.setEnabled(self.vip_list.count() > 0)
