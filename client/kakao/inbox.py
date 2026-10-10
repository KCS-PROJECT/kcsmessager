# -*- coding: utf-8 -*-
"""
모아보기 창 (명세 §10.5 · §10.7)
- MentionsDialog: 모든 채팅방에서 나를 멘션한 메시지 (서버 mention_list)
- SavedDialog: 책갈피 - 내가 저장한 메시지 (클라이언트 설정 saved_messages)
줄을 두 번 누르거나 [이동]을 누르면 그 채팅방의 그 메시지로 간다.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
                             QListWidgetItem)

from client.kakao import theme
from client.kakao.state import parse_dt, fmt_ampm


def _when(ts):
    dt = parse_dt(ts)
    if dt is None:
        return ''
    return f'{dt.month}/{dt.day} {fmt_ampm(dt)}'


class _InboxDialog(QDialog):
    TITLE = ''
    EMPTY = ''

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle(self.TITLE)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.resize(theme.px(400), theme.px(480))
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(8)
        title = QLabel(self.TITLE)
        title.setStyleSheet(f"font-size: {theme.fs('lead')}px; font-weight: bold;")
        v.addWidget(title)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
        v.addWidget(self.status)
        self.list = QListWidget(self)
        self.list.setWordWrap(True)
        self.list.setAccessibleName(self.TITLE)
        self.list.itemDoubleClicked.connect(lambda _item: self.open_selected())
        self.list.itemActivated.connect(lambda _item: self.open_selected())
        v.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.extra_button = None
        self._add_extra_button(row)
        row.addStretch(1)
        self.open_button = QPushButton('이동')
        self.open_button.setProperty('primary', True)
        self.open_button.clicked.connect(self.open_selected)
        close = QPushButton('닫기')
        close.clicked.connect(self.close)
        row.addWidget(self.open_button)
        row.addWidget(close)
        v.addLayout(row)
        self.list.currentRowChanged.connect(lambda _r: self._sync_buttons())

    def _add_extra_button(self, row):
        pass

    def entries(self):
        return []

    def _line(self, e):
        room = self.state.room_title(e['room_id']) if e.get('room_id') in self.state.rooms else '나간 채팅방'
        sender = self.state.display_name(e['sender']) if e.get('sender') else ''
        head = ' · '.join(x for x in (room, sender, _when(e.get('timestamp'))) if x)
        return f"{head}\n{(e.get('preview') or '').strip() or ' '}"

    def refresh(self):
        current = self.list.currentRow()
        self.list.clear()
        for e in self.entries():
            item = QListWidgetItem(self._line(e))
            item.setData(Qt.UserRole, e)
            self.list.addItem(item)
        n = self.list.count()
        self.status.setText(f'{n}개' if n else self.EMPTY)
        if n:
            self.list.setCurrentRow(min(max(current, 0), n - 1))
        self._sync_buttons()

    def _sync_buttons(self):
        has = self.list.currentItem() is not None
        self.open_button.setEnabled(has)
        if self.extra_button is not None:
            self.extra_button.setEnabled(has)

    def selected(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def open_selected(self):
        """그 채팅방을 열고 메시지로 이동"""
        e = self.selected()
        if not e or e.get('room_id') not in self.state.rooms:
            if e:
                self.status.setText('이 채팅방에서 나가서 열 수 없습니다.')
            return False
        target = self.parent()
        while target is not None and not hasattr(target, 'focus_message'):
            target = target.parent()
        if target is None:
            return False
        if e.get('thread_root') is not None:
            target.focus_message(e['room_id'], e['msg_id'], hint=e)
        else:
            target.focus_message(e['room_id'], e['msg_id'])
        return True


class MentionsDialog(_InboxDialog):
    """나를 멘션한 메시지 모아보기 (§10.5)"""
    TITLE = '나를 멘션한 메시지'
    EMPTY = '나를 멘션한 메시지가 없습니다.'

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        state.mentions_changed.connect(self.refresh)
        self.refresh()
        if state.request_mentions():
            self.status.setText('불러오는 중…' if not state.mentions else self.status.text())
        else:
            self.status.setText('서버에 연결되어 있지 않아 최근에 받은 멘션만 보여 줍니다.')

    def entries(self):
        out = []
        for m in self.state.mentions:
            out.append({'room_id': m.get('room_id'), 'msg_id': m['msg_id'], 'sender': m.get('sender', ''),
                        'timestamp': m.get('timestamp', ''), 'preview': self.state.message_preview(m),
                        'thread_root': m.get('thread_root')})
        return out

    def done(self, result):
        try:
            self.state.mentions_changed.disconnect(self.refresh)
        except (TypeError, RuntimeError):
            pass
        super().done(result)

    def closeEvent(self, event):
        try:
            self.state.mentions_changed.disconnect(self.refresh)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)


class SavedDialog(_InboxDialog):
    """책갈피 - 저장한 메시지 (§10.7)"""
    TITLE = '책갈피'
    EMPTY = '저장한 메시지가 없습니다. 말풍선 우클릭 → 책갈피로 저장하세요.'

    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        state.saved_changed.connect(self.refresh)
        self.refresh()

    def _add_extra_button(self, row):
        self.extra_button = QPushButton('책갈피 해제')
        self.extra_button.clicked.connect(self.remove_selected)
        row.addWidget(self.extra_button)

    def entries(self):
        return self.state.saved_messages()

    def remove_selected(self):
        e = self.selected()
        if e:
            self.state.unsave_message(e['room_id'], e['msg_id'])

    def closeEvent(self, event):
        try:
            self.state.saved_changed.disconnect(self.refresh)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)
