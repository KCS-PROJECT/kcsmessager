# -*- coding: utf-8 -*-
"""
대직자 (명세 §8.13) - 내가 자리에 없을 때 대신 업무를 맡는 사람.

프로필 편집 '대직자' 칸(DeputyEditor): 이름 · 부서 · 팀 · 직함으로 검색해
- 한 명이면 바로 추가
- 여럿이면 체크 목록 팝업(DeputyPickerDialog)에서 골라 추가 (검색어 없이 [찾기] = 전체에서 고르기)
- 칩의 ✕ 로 빼기
저장은 프로필 편집 [저장] 때 profile_update {deputies}.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QPushButton, QVBoxLayout, QWidget)

from client.kakao import theme
from client.kakao.widgets import FlowWidget, make_icon

MAX_DEPUTIES = 10


def deputy_title(state, username):
    """'강태영 책임' - 이름과 직함"""
    title = state.user(username).get('title') or ''
    return f"{state.display_name(username)} {title}".strip()


def deputy_unit(state, username):
    """팀(없으면 부서)"""
    user = state.user(username)
    path = user.get('org_path') or []
    return path[-1] if path else (user.get('department') or '')


def deputy_summary(state, names):
    """프로필 보기용: '김철수 책임' / '김철수 책임 외 2명'"""
    names = [n for n in names or [] if n]
    if not names:
        return ''
    first = deputy_title(state, names[0])
    return first if len(names) == 1 else f"{first} 외 {len(names) - 1}명"


def find_candidates(state, query=''):
    """대직자로 고를 수 있는 사람 (나 · 봇 제외). 검색어는 이름 · 아이디 · 부서 · 팀 · 직함 · 회사 일부 (대소문자 무시)"""
    q = (query or '').strip().lower()
    out = []
    for name, user in state.users.items():
        if name == state.me or user.get('is_bot') or user.get('removed'):
            continue
        fields = [name, user.get('display_name'), user.get('department'), user.get('title'), user.get('company'),
                  *(user.get('org_path') or [])]
        if not q or any(q in str(f).lower() for f in fields if f):
            out.append(name)
    return sorted(out, key=lambda n: (state.display_name(n), n))


class DeputyPickerDialog(QDialog):
    """여러 명 중 체크해서 대직자로 추가"""

    def __init__(self, state, candidates, already=(), query='', parent=None):
        super().__init__(parent)
        self.state = state
        self.setWindowTitle('대직자 선택')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        title = QLabel(f"'{query}' 검색 결과 {len(candidates)}명" if query else f"대직자로 고를 사람 {len(candidates)}명")
        title.setStyleSheet(f"font-size: {theme.fs('title')}px; font-weight: bold;")
        layout.addWidget(title)
        hint = QLabel('대직자로 추가할 사람을 체크하세요.')
        hint.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
        layout.addWidget(hint)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText('목록에서 이름 · 부서 · 팀 찾기')
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setAccessibleName('대직자 목록 찾기')
        layout.addWidget(self.filter_edit)
        self.list = QListWidget()
        self.list.setAccessibleName('대직자 후보')
        self.list.setMinimumHeight(theme.px(240))
        from client.kakao.calendar_tab import checkbox_qss
        self.list.setStyleSheet(checkbox_qss() + f" QListWidget::item {{ padding: 7px 4px; }}"
                                f" QListWidget::item:disabled {{ color: {theme.c('text_hint')}; }}")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setTextElideMode(Qt.ElideMiddle)
        self.setMinimumWidth(theme.px(380))
        already = set(already)
        for name in candidates:
            unit = deputy_unit(state, name)
            text = deputy_title(state, name) + (f"  ·  {unit}" if unit else '')
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, name)
            if name in already:
                item.setText('이미 대직자 · ' + text)
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsUserCheckable)
            else:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)
        layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        self.count_label = QLabel('')
        self.count_label.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
        buttons.addWidget(self.count_label)
        buttons.addStretch(1)
        cancel = QPushButton('취소')
        self.add_button = QPushButton('추가')
        self.add_button.setProperty('primary', True)
        self.add_button.setDefault(True)
        buttons.addWidget(cancel)
        buttons.addWidget(self.add_button)
        layout.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        self.add_button.clicked.connect(self.accept)
        self.list.itemChanged.connect(lambda _item: self._update_count())
        self.list.itemPressed.connect(self._remember)
        self.list.itemClicked.connect(self._toggle)
        self.filter_edit.textChanged.connect(self._filter)
        self._update_count()

    def _remember(self, item):
        self._pressed_state = (item, item.checkState())

    def _toggle(self, item):
        """줄 아무 데나 눌러도 체크 (작은 네모를 눌렀으면 Qt 가 이미 바꿨으므로 그대로)"""
        before = getattr(self, '_pressed_state', None)
        self._pressed_state = None
        if not item.flags() & Qt.ItemIsUserCheckable:
            return
        if before is not None and before[0] is item and before[1] != item.checkState():
            return
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def _filter(self, text):
        q = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(q) and q not in item.text().lower())

    def _update_count(self):
        n = len(self.selected())
        self.count_label.setText(f"{n}명 선택" if n else '')
        self.add_button.setEnabled(n > 0)

    def set_checked(self, username, checked=True):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == username and item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def selected(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())
                if self.list.item(i).flags() & Qt.ItemIsUserCheckable
                and self.list.item(i).checkState() == Qt.Checked]


class DeputyChip(QFrame):
    """'김철수 책임 ✕'"""

    def __init__(self, state, username, on_remove, parent=None):
        super().__init__(parent)
        self.username = username
        self.setObjectName('deputyChip')
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 3, 4, 3)
        row.setSpacing(2)
        self.label = QLabel(deputy_title(state, username))
        self.label.setToolTip(deputy_unit(state, username))
        self.label.setStyleSheet(f"font-size: {theme.fs('meta')}px; background: transparent;")
        row.addWidget(self.label)
        self.remove_button = QPushButton()
        self.remove_button.setIcon(make_icon('close', theme.c('text_sub'), 12))
        self.remove_button.setAccessibleName(f"대직자 {state.display_name(username)} 빼기")
        self.remove_button.setToolTip('대직자에서 빼기')
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setStyleSheet("QPushButton { border: none; background: transparent; padding: 0; }"
                                         f" QPushButton:hover {{ background: {theme.c('bg_hover')}; border-radius: 12px; }}")
        self.remove_button.clicked.connect(lambda: on_remove(username))
        row.addWidget(self.remove_button)
        self.setStyleSheet(f"QFrame#deputyChip {{ background: {theme.c('bg_alt')};"
                           f" border: 1px solid {theme.c('border')}; border-radius: 13px; }}")


class DeputyEditor(QWidget):
    """프로필 편집의 '대직자' 칸 - 검색 칸 + [찾기] + 지정한 사람 칩"""

    changed = pyqtSignal()

    def __init__(self, state, deputies=(), parent=None):
        super().__init__(parent)
        self.state = state
        self._deputies = [d for d in deputies or [] if d != state.me]
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('이름 · 부서 · 팀으로 검색')
        self.search_edit.setAccessibleName('대직자 검색')
        self.search_edit.setClearButtonEnabled(True)
        row.addWidget(self.search_edit, 1)
        self.search_button = QPushButton('찾기')
        self.search_button.setAutoDefault(False)
        self.search_button.setToolTip('검색어 없이 누르면 전체 목록에서 고릅니다')
        row.addWidget(self.search_button)
        col.addLayout(row)
        self.flow = FlowWidget(spacing=6)
        col.addWidget(self.flow)
        self.message = QLabel('')
        self.message.setWordWrap(True)
        self.message.hide()
        col.addWidget(self.message)
        self.search_edit.returnPressed.connect(self.search)
        self.search_button.clicked.connect(lambda: self.search())
        self._refresh()

    def deputies(self):
        return list(self._deputies)

    def add(self, names):
        added, full = [], False
        for name in names:
            if name and name != self.state.me and name not in self._deputies:
                if len(self._deputies) >= MAX_DEPUTIES:
                    full = True
                    break
                self._deputies.append(name)
                added.append(name)
        limit = f'대직자는 {MAX_DEPUTIES}명까지 지정할 수 있습니다.'
        if added:
            self.search_edit.clear()
            done = ', '.join(deputy_title(self.state, n) for n in added) + ' 님을 대직자로 추가했어요.'
            self._say(f'{done} {limit}' if full else done, error=full)
            self._refresh()
            self.changed.emit()
        elif full:
            self._say(limit, error=True)
        return added

    def remove(self, username):
        if username in self._deputies:
            self._deputies.remove(username)
            self._say('')
            self._refresh()
            self.changed.emit()

    def search(self, query=None, exec_=True):
        """검색 → 한 명이면 바로 추가, 여럿이면 체크 팝업. exec_=False 면 팝업을 띄우지 않고 돌려준다(테스트)"""
        query = self.search_edit.text() if query is None or isinstance(query, bool) else query
        query = query.strip()
        found = find_candidates(self.state, query)
        fresh = [n for n in found if n not in self._deputies]
        if not found:
            self._say(f"'{query}'(으)로 찾은 사람이 없어요.", error=True)
            return None
        if query and len(fresh) == 1 and len(found) == 1:
            return self.add(fresh)
        if query and not fresh:
            self._say('이미 대직자로 지정한 사람이에요.', error=True)
            return None
        dlg = DeputyPickerDialog(self.state, found, already=self._deputies, query=query, parent=self.window())
        if not exec_:
            return dlg
        if dlg.exec_() == QDialog.Accepted:
            return self.add(dlg.selected())
        return None

    def _say(self, text, error=False):
        self.message.setText(text)
        self.message.setVisible(bool(text))
        self.message.setStyleSheet(f"color: {theme.c('danger_text') if error else theme.c('text_sub')};"
                                   f" font-size: {theme.fs('caption')}px;")

    def _refresh(self):
        chips = [DeputyChip(self.state, n, self.remove) for n in self._deputies]
        if not chips:
            empty = QLabel('지정한 대직자가 없어요')
            empty.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('meta')}px; padding: 2px 0;")
            chips = [empty]
        self.flow.set_widgets(chips)
