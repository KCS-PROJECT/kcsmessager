# -*- coding: utf-8 -*-
"""
친구 탭 - 펑(24시간 스토리) 줄, 내 프로필, AI 비서, 생일인 친구, 즐겨찾기, 온라인/오프라인 친구(접기 가능)
프로필 보기/편집 다이얼로그와 상태(presence) 선택 메뉴, 친구 숨김/차단도 이 모듈에 둔다.
"""

import base64

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QRectF, pyqtSignal
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QFontMetrics
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMenu, QDialog,
                             QLineEdit, QPushButton, QFileDialog, QFormLayout, QSizePolicy,
                             QMessageBox, QFrame, QGridLayout, QAbstractButton, QScrollArea)

from client.kakao import theme
from client.kakao.widgets import Avatar, make_icon
from client.kakao.chats_tab import (ElidedLabel, StatusPill, RowList, TabHeader, CreateGroupDialog,
                                    make_search_edit, search_box_qss, user_pixmap, InviteToRoomDialog, presence_of,
                                    set_presence, foreign_company, CompanyChip, connect_avatar_changed,
                                    presence_dot_pixmap, PRESENCE_CHOICES, PRESENCE_LABELS,
                                    PRESENCE_COLORS)

AVATAR_MAX_BYTES = 512 * 1024
SECTION_TITLES = {
    'bot': 'AI 비서',
    'birthday': '생일인 친구',
    'team': '내 부서',
    'favorites': '즐겨찾기',
    'registered': '내가 추가한 친구',
    'online': '온라인',
    'offline': '오프라인',
}
BOT_HINT = '문서를 보내면 학습하고, 질문에 답해요'


# ================================================================ 상태(presence) 메뉴
def presence_menu(state, parent=None, on_selected=None):
    """온라인/자리비움/다른 용무 중/회의 중/휴가 중 선택 메뉴"""
    menu = QMenu(parent)
    current = presence_of(state, state.me)
    for key, label, _color in PRESENCE_CHOICES:
        action = menu.addAction(make_icon_from_pixmap(presence_dot_pixmap(key, 12)), label)
        action.setCheckable(True)
        action.setChecked(key == current)
        action.setData(key)

        def choose(_checked=False, k=key):
            set_presence(state, k)
            if on_selected:
                on_selected(k)
        action.triggered.connect(choose)
    return menu


def make_icon_from_pixmap(pm):
    from PyQt5.QtGui import QIcon
    return QIcon(pm)


class PresenceButton(QPushButton):
    """현재 상태를 색 점 + 글자로 보여주고 누르면 상태 메뉴를 띄운다"""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.clicked.connect(self._open_menu)
        self.refresh()

    def refresh(self):
        presence = presence_of(self.state, self.state.me)
        if presence == 'offline':
            presence = 'online'
        self.setIcon(make_icon_from_pixmap(presence_dot_pixmap(presence, 10)))
        self.setText(PRESENCE_LABELS.get(presence, '온라인'))
        self.setStyleSheet(
            f"QPushButton {{ background: {theme.c('bg_alt')}; border: 1px solid {theme.c('border')};"
            f" border-radius: {theme.px(10)}px; padding: 3px 10px; font-size: {theme.fs('caption')}px;"
            f" color: {theme.c('text_sub')}; }}"
            f" QPushButton:hover {{ background: {theme.c('bg_hover')}; }}")

    def _open_menu(self):
        menu = presence_menu(self.state, self, lambda _k: None)
        menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))



# ================================================================ 숨김 / 차단
def hide_friend(state, username, hidden=True):
    state.set_hidden(username, hidden)


def confirm_block(state, username, parent=None):
    """차단 확인 후 block_set 전송. 차단했으면 True"""
    name = state.display_name(username)
    answer = QMessageBox.question(
        parent, '친구 차단',
        f"{name}님을 차단할까요?\n차단하면 {name}님이 보내는 메시지를 받지 않으며, 상대방은 차단 사실을 알 수 없습니다.",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if answer != QMessageBox.Yes:
        return False
    state.block_user(username, True)
    return True


# ================================================================ 펑 줄
class StoryBubble(QAbstractButton):
    """펑 아바타 - 안 본 펑이 있으면 강조색 고리, 다 봤으면 회색 고리. kind='add' 는 '+' 올리기 버튼"""

    def __init__(self, state, username, kind='story', parent=None):
        super().__init__(parent)
        self.state = state
        self.username = username
        self.kind = kind
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(theme.px(64), theme.px(80))
        if kind == 'add':
            self.setToolTip('펑 올리기')
        else:
            self.setToolTip(f'{state.display_name(username)}님의 펑')

    def unseen(self):
        return self.kind == 'story' and self.state.has_unseen_story(self.username)

    def ring_color(self):
        return theme.c('yellow') if self.unseen() else theme.c('border' if not theme.is_dark() else 'text_hint')

    def label(self):
        if self.kind == 'add':
            return '펑 올리기'
        if self.username == self.state.me:
            return '내 펑'
        return self.state.display_name(self.username)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        d = theme.px(52)
        x = (self.width() - d) / 2
        ring = QRectF(x, 3, d, d)
        if self.kind == 'add':
            pen = QPen(QColor(theme.c('text_hint')), 1.4, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(theme.qc('bg_alt'))
            p.drawEllipse(ring.adjusted(1, 1, -1, -1))
            # 내 사진 위 '+' 대신 단순한 + 기호(카카오 펑 첫 칸)
            p.setPen(QPen(theme.qc('text_sub'), 2.0, Qt.SolidLine, Qt.RoundCap))
            c = ring.center()
            s = d * 0.18
            p.drawLine(int(c.x() - s), int(c.y()), int(c.x() + s), int(c.y()))
            p.drawLine(int(c.x()), int(c.y() - s), int(c.x()), int(c.y() + s))
        else:
            p.setPen(QPen(QColor(self.ring_color()), 2.4 if self.unseen() else 1.6))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(ring.adjusted(1.2, 1.2, -1.2, -1.2))
            inner = int(d - 10)
            pm = user_pixmap(self.state, self.username, inner)
            p.drawPixmap(int(x + 5), 8, inner, inner, pm)
        f = theme.font('caption', bold=self.unseen())
        p.setFont(f)
        p.setPen(theme.qc('text' if self.kind != 'add' else 'text_sub'))
        fm = QFontMetrics(f)
        text = fm.elidedText(self.label(), Qt.ElideRight, self.width() - 2)
        p.drawText(QRectF(0, d + 8, self.width(), fm.height() + 2), Qt.AlignHCenter | Qt.AlignTop, text)


class StoryBar(QWidget):
    """친구 탭 위쪽 '펑' 가로 줄 - [+ 펑 올리기] [내 펑] [친구들 …]"""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.bubbles = []
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 2, 0, 4)
        col.setSpacing(2)
        head = QHBoxLayout()
        head.setContentsMargins(16, 0, 16, 0)
        self.title = QLabel('펑')
        head.addWidget(self.title)
        self.count_label = QLabel('')
        head.addWidget(self.count_label, 1)
        self.compose_link = QPushButton('＋ 펑 올리기')
        self.compose_link.setProperty('flat', True)
        self.compose_link.setCursor(Qt.PointingHandCursor)
        self.compose_link.setToolTip('24시간 뒤 사라지는 소식을 올려요')
        self.compose_link.clicked.connect(lambda: self.compose())
        head.addWidget(self.compose_link)
        col.addLayout(head)
        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.inner = QWidget()
        self.inner.setObjectName('storyInner')
        self.row = QHBoxLayout(self.inner)
        self.row.setContentsMargins(10, 0, 10, 0)
        self.row.setSpacing(2)
        self.scroll.setWidget(self.inner)
        col.addWidget(self.scroll)
        state.stories_changed.connect(self.refresh)
        state.users_changed.connect(self.refresh)
        state.blocked_changed.connect(self.refresh)
        connect_avatar_changed(state, self.refresh)
        self.apply_theme()

    def owners(self):
        return list(self.state.story_owners())

    def bubble_menu(self, username):
        """펑 동그라미 우클릭: 소식 숨기기"""
        menu = QMenu(self)
        menu.addAction('펑 보기', lambda: self.open_story(username))
        menu.addAction(f"{self.state.display_name(username)}님 소식 숨기기",
                       lambda: self.state.set_story_hidden(username, True))
        return menu

    def bubble_for(self, username):
        for b in self.bubbles:
            if b.kind == 'story' and b.username == username:
                return b
        return None

    def refresh(self):
        for b in self.bubbles:
            b.hide()
            b.deleteLater()   # 클릭 처리 중 삭제될 수 있으므로 지연 삭제
        self.bubbles = []
        while self.row.count():
            self.row.takeAt(0)
        add = StoryBubble(self.state, self.state.me, 'add')
        add.clicked.connect(self.compose)
        self.bubbles.append(add)
        self.row.addWidget(add)
        owners = self.owners()
        for name in owners:
            b = StoryBubble(self.state, name, 'story')
            b.clicked.connect(lambda _c=False, n=name: self.open_story(n))
            if name != self.state.me:
                b.setContextMenuPolicy(Qt.CustomContextMenu)
                b.customContextMenuRequested.connect(
                    lambda pos, n=name, w=b: self.bubble_menu(n).exec_(w.mapToGlobal(pos)))
            self.bubbles.append(b)
            self.row.addWidget(b)
        self.row.addStretch(1)
        unseen = sum(1 for n in owners if self.state.has_unseen_story(n))
        self.count_label.setText(f'새 펑 {unseen}' if unseen else '')
        self.scroll.setFixedHeight(theme.px(80) + 12)
        # 올라온 펑이 없으면 가로 줄 대신 한 줄 링크만 (첫 화면 공간을 대화·친구에 양보)
        self.scroll.setVisible(bool(owners))
        self.compose_link.setVisible(not owners)
        self.compose_link.setStyleSheet(f"color: {theme.c('yellow')}; font-size: {theme.fs('meta')}px;"
                                        f" font-weight: bold; padding: 2px 6px;")

    def open_story(self, username):
        from client.kakao.story import StoryViewer
        viewer = StoryViewer(self.state, username, self.window())
        viewer.exec_()
        return viewer

    def compose(self):
        from client.kakao.story import StoryComposeDialog
        dlg = StoryComposeDialog(self.state, self.window())
        dlg.exec_()
        return dlg

    def apply_theme(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"StoryBar, QScrollArea, QWidget#storyInner {{ background: {theme.c('bg')}; }}")
        self.title.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px; font-weight: bold;")
        self.count_label.setStyleSheet(f"color: {theme.c('yellow') if not theme.is_dark() else theme.c('brand')};"
                                       f" font-size: {theme.fs('caption')}px; font-weight: bold; padding-left: 4px;")
        self.refresh()


# ================================================================ 프로필 사진
def avatar_png_from_path(path, size=256):
    """이미지 → 정사각형 가운데 자르기 → size px PNG bytes. (bytes, 오류문자열)"""
    image = QImage(path)
    if image.isNull():
        return None, '이미지 파일을 열 수 없습니다.'
    side = min(image.width(), image.height())
    image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
    image = image.scaled(size, size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    image.save(buf, 'PNG')
    buf.close()
    raw = bytes(data)
    if len(raw) > AVATAR_MAX_BYTES:
        return None, '프로필 사진은 512KB 이하만 사용할 수 있습니다.'
    return raw, None


# ================================================================ 프로필 편집
class ProfileEditDialog(QDialog):
    """내 프로필 편집 - 사진, 이름, 상태메시지, 생일(MM-DD)"""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        me = state.user(state.me)
        self.setWindowTitle('프로필 편집')
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        self.avatar = Avatar(size=96)
        layout.addWidget(self.avatar, 0, Qt.AlignHCenter)
        photo_row = QHBoxLayout()
        photo_row.addStretch(1)
        self.photo_button = QPushButton('사진 변경')
        self.clear_photo_button = QPushButton('기본 이미지')
        self.clear_photo_button.setToolTip('회사 조직도 사진으로 되돌립니다 (조직도 사진이 없으면 사진 없음)')
        photo_row.addWidget(self.photo_button)
        photo_row.addWidget(self.clear_photo_button)
        photo_row.addStretch(1)
        layout.addLayout(photo_row)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        self.name_edit = QLineEdit(me.get('display_name') or state.me)
        self.name_edit.setMaxLength(20)
        self.status_edit = QLineEdit(me.get('status_message') or '')
        self.status_edit.setMaxLength(60)
        self.status_edit.setPlaceholderText('상태메시지를 입력해 주세요')
        self.birthday_edit = QLineEdit(me.get('birthday') or '')
        self.birthday_edit.setPlaceholderText('MM-DD (예: 03-15)')
        self.birthday_edit.setInputMask('')
        form.addRow('이름', self.name_edit)
        form.addRow('상태메시지', self.status_edit)
        form.addRow('생일', self.birthday_edit)
        self.mobile_edit = QLineEdit(me.get('mobile') or '')
        self.mobile_edit.setPlaceholderText('010-1234-5678')
        self.mobile_edit.setMaxLength(20)
        self.email_edit = QLineEdit(me.get('email') or '')
        self.email_edit.setPlaceholderText('name@company.com')
        self.email_edit.setMaxLength(120)
        form.addRow('전화번호', self.mobile_edit)
        form.addRow('이메일', self.email_edit)
        layout.addLayout(form)
        hint = QLabel('다른 사람이 전화번호나 이메일로 나를 친구로 추가할 수 있어요.')
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('caption')}px;")
        layout.addWidget(hint)

        self.error_label = QLabel('')
        self.error_label.setStyleSheet(f"color: {theme.c('danger_text')}; font-size: {theme.fs('meta')}px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton('취소')
        self.ok_button = QPushButton('저장')
        self.ok_button.setProperty('primary', True)
        self.ok_button.setDefault(True)
        buttons.addWidget(cancel)
        buttons.addWidget(self.ok_button)
        layout.addLayout(buttons)

        cancel.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)
        self.photo_button.clicked.connect(self.choose_photo)
        self.clear_photo_button.clicked.connect(self.clear_photo)
        connect_avatar_changed(state, self._refresh_avatar)
        self._refresh_avatar()

    def _refresh_avatar(self):
        self.avatar.setPixmap(user_pixmap(self.state, self.state.me, 96))

    def _show_error(self, text, field=None):
        """오류를 보여 주고 그 입력칸에 연결한다 (ui-styling: 오류는 입력칸과 연결해 스크린리더가 읽게,
        포커스를 그 칸으로)"""
        self.error_label.setText(text or '')
        self.error_label.setVisible(bool(text))
        for edit in (self.birthday_edit, self.mobile_edit, self.email_edit):
            edit.setAccessibleDescription(text if edit is field else '')
        if field is not None:
            field.setFocus()

    def choose_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, '프로필 사진 선택', '',
                                              '이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)')
        if path:
            self.set_photo_from_path(path)

    def set_photo_from_path(self, path):
        """사진을 정사각형 256px PNG로 변환해 바로 전송. 오류 문자열 또는 None"""
        data, err = avatar_png_from_path(path)
        if err:
            self._show_error(err)
            return err
        self._show_error('')
        self.state.update_profile(avatar_b64=base64.b64encode(data).decode('ascii'))
        return None

    def clear_photo(self):
        self.state.update_profile(avatar_clear=True)

    def values(self):
        return {'display_name': self.name_edit.text().strip() or self.state.me,
                'status_message': self.status_edit.text().strip(),
                'birthday': self.birthday_edit.text().strip() or None,
                **self._contact_changes()}

    def _contact_changes(self):
        """전화번호·이메일은 바뀐 것만 보낸다"""
        me = self.state.user(self.state.me)
        out = {}
        for key, edit in (('mobile', self.mobile_edit), ('email', self.email_edit)):
            value = edit.text().strip()
            if value != (me.get(key) or ''):
                out[key] = value
        return out

    def accept(self):
        values = self.values()
        birthday = values['birthday']
        if birthday:
            ok = len(birthday) == 5 and birthday[2] == '-' and birthday.replace('-', '').isdigit()
            if ok:
                month, day = int(birthday[:2]), int(birthday[3:])
                ok = 1 <= month <= 12 and 1 <= day <= 31
            if not ok:
                self._show_error('생일은 MM-DD 형식으로 입력해 주세요. (예: 03-15)', self.birthday_edit)
                return
        if values.get('mobile') and self.state.contact_kind(values['mobile']) != 'phone':
            self._show_error('전화번호 형식이 올바르지 않습니다. (예: 010-1234-5678)', self.mobile_edit)
            return
        if values.get('email') and self.state.contact_kind(values['email']) != 'email':
            self._show_error('이메일 형식이 올바르지 않습니다. (예: name@company.com)', self.email_edit)
            return
        self.state.update_profile(**values)
        super().accept()


# ================================================================ 친구 추가 (전화번호 · 이메일)
def _set_add_friend_icon(button, size=22):
    """사람 + 플러스 아이콘"""
    from PyQt5.QtGui import QPixmap, QIcon
    from PyQt5.QtCore import QSize, QPointF
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(theme.c('text_sub')), 1.7)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    k = size / 24.0
    p.drawEllipse(QRectF(5 * k, 4 * k, 7.5 * k, 7.5 * k))
    p.drawArc(QRectF(2 * k, 13.5 * k, 13.5 * k, 12 * k), 0, 180 * 16)
    p.drawLine(QPointF(18.5 * k, 6 * k), QPointF(18.5 * k, 13 * k))
    p.drawLine(QPointF(15 * k, 9.5 * k), QPointF(22 * k, 9.5 * k))
    p.end()
    button.setIcon(QIcon(pm))
    button.setIconSize(QSize(size, size))


class AddFriendDialog(QDialog):
    """친구 추가 - [전화번호] / [이메일] 탭, 정확히 일치하는 사용자만 찾는다 (카카오톡 연락처·ID 추가와 같은 방식)"""

    MODES = {'phone': ('전화번호', '010-1234-5678', '상대방이 프로필에 등록한 휴대폰 번호를 입력하세요.'),
             'email': ('이메일', 'name@company.com', '상대방이 프로필에 등록한 이메일 주소를 입력하세요.')}

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.mode = 'phone'
        self.found = None
        self.setWindowTitle('친구 추가')
        self.setMinimumWidth(360)
        col = QVBoxLayout(self)
        col.setContentsMargins(24, 20, 24, 18)
        col.setSpacing(10)
        title = QLabel('친구 추가')
        title.setStyleSheet(f"font-size: {theme.fs('headline')}px; font-weight: bold;")
        col.addWidget(title)
        tabs = QHBoxLayout()
        tabs.setSpacing(6)
        self.mode_buttons = {}
        for key, (label, _ph, _hint) in self.MODES.items():
            b = QPushButton(label)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _c=False, k=key: self.set_mode(k))
            tabs.addWidget(b)
            self.mode_buttons[key] = b
        tabs.addStretch(1)
        col.addLayout(tabs)
        self.input = QLineEdit()
        self.input.setMinimumHeight(theme.px(38))
        self.input.returnPressed.connect(self.submit)
        col.addWidget(self.input)
        self.hint = QLabel('')
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('meta')}px;")
        col.addWidget(self.hint)
        self.message = QLabel('')
        self.message.setWordWrap(True)
        self.message.hide()
        col.addWidget(self.message)
        # 찾은 사람 카드
        self.card = QWidget()
        card_row = QHBoxLayout(self.card)
        card_row.setContentsMargins(0, 6, 0, 6)
        card_row.setSpacing(12)
        self.card_avatar = Avatar(size=theme.px(48))
        card_row.addWidget(self.card_avatar)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.card_name = QLabel('')
        self.card_name.setStyleSheet(f"font-size: {theme.fs('title')}px; font-weight: bold;")
        self.card_sub = QLabel('')
        self.card_sub.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
        info.addWidget(self.card_name)
        info.addWidget(self.card_sub)
        card_row.addLayout(info, 1)
        self.chat_button = QPushButton('1:1 채팅')
        self.chat_button.clicked.connect(self._chat)
        card_row.addWidget(self.chat_button)
        self.card.hide()
        col.addWidget(self.card)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        close = QPushButton('닫기')
        close.clicked.connect(self.reject)
        self.add_button = QPushButton('친구 추가')
        self.add_button.setProperty('primary', True)
        self.add_button.setDefault(True)
        self.add_button.clicked.connect(self.submit)
        buttons.addWidget(close)
        buttons.addWidget(self.add_button)
        col.addLayout(buttons)
        state.friend_added.connect(self._on_added)
        state.error.connect(self._on_error)
        self.input.textChanged.connect(lambda _t: self._update_button())
        self.set_mode('phone')

    def set_mode(self, mode):
        self.mode = mode
        label, placeholder, hint = self.MODES[mode]
        for key, b in self.mode_buttons.items():
            b.setChecked(key == mode)
            b.setProperty('primary', key == mode)
            b.style().unpolish(b)
            b.style().polish(b)
        self.input.clear()
        self.input.setPlaceholderText(placeholder)
        self.hint.setText(hint)
        self._show_message('')
        self.card.hide()
        self._update_button()
        self.input.setFocus()

    def set_query(self, text):
        self.input.setText(text)

    def _update_button(self):
        self.add_button.setEnabled(self.state.contact_kind(self.input.text()) == self.mode)

    def _show_message(self, text, error=False):
        self.message.setText(text)
        self.message.setVisible(bool(text))
        self.input.setAccessibleDescription(text if error else '')   # 오류를 입력칸에 연결
        color = theme.c('danger_text') if error else theme.c('text_sub')
        self.message.setStyleSheet(f"color: {color}; font-size: {theme.fs('meta')}px;")

    def submit(self):
        query = self.input.text().strip()
        kind = self.state.contact_kind(query)
        if kind != self.mode:
            self._show_message('전화번호 형식이 올바르지 않습니다. (예: 010-1234-5678)' if self.mode == 'phone'
                               else '이메일 형식이 올바르지 않습니다. (예: name@company.com)', error=True)
            return False
        self.card.hide()
        self._show_message('찾는 중…')
        err = self.state.add_friend(query)
        if err:
            self._show_message(err, error=True)
            return False
        return True

    def _on_added(self, user, already):
        self.found = user['username']
        self.card_avatar.setPixmap(user_pixmap(self.state, user['username'], theme.px(48)))
        self.card_name.setText(self.state.display_name(user['username']))
        org = self.state.org_text(user['username'])
        self.card_sub.setText(org or user.get('status_message') or '')
        self.card.show()
        self._show_message('이미 친구로 등록되어 있어요.' if already else '친구로 추가했어요! 🎉')

    def _on_error(self, text):
        if self.isVisible() or self.message.text() == '찾는 중…':
            self._show_message(text, error=True)

    def _chat(self):
        if self.found:
            self.state.open_direct(self.found)
            self.accept()


# ================================================================ 프로필 보기
class ProfileDialog(QDialog):
    """친구 프로필 카드 - 큰 사진, 이름, 소속, 상태메시지, 생일, 1:1 채팅"""

    def __init__(self, state, username, parent=None):
        super().__init__(parent)
        self.state = state
        self.username = username
        user = state.user(username)
        self.setWindowTitle(f"{state.display_name(username)} 프로필")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 20)
        layout.setSpacing(8)
        avatar = Avatar(size=104)
        avatar.setPixmap(user_pixmap(state, username, 104, show_presence=True))
        layout.addWidget(avatar, 0, Qt.AlignHCenter)
        layout.addSpacing(6)

        name = QLabel(state.display_name(username))
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"font-size: {theme.fs('headline')}px; font-weight: bold;")
        layout.addWidget(name)

        path = user.get('org_path') or ([user['department']] if user.get('department') else [])
        org = ' · '.join(x for x in (user.get('company'), ' › '.join(path), user.get('title')) if x)
        sub = []
        if org:
            sub.append(org)
        presence = presence_of(state, username)
        sub.append(PRESENCE_LABELS.get(presence, ''))
        info = QLabel('\n'.join(sub))
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
        layout.addWidget(info)

        status = QLabel(user.get('status_message') or '상태메시지가 없습니다')
        status.setAlignment(Qt.AlignCenter)
        status.setWordWrap(True)
        status.setStyleSheet(f"color: {theme.c('text') if user.get('status_message') else theme.c('text_hint')};"
                             f" font-size: {theme.fs('body')}px; padding: 6px 0;")
        layout.addWidget(status)

        if user.get('birthday'):
            month, _, day = user['birthday'].partition('-')
            bday = QLabel(f"🎂 생일 {int(month)}월 {int(day)}일" if month.isdigit() and day.isdigit()
                          else f"🎂 {user['birthday']}")
            bday.setAlignment(Qt.AlignCenter)
            bday.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
            layout.addWidget(bday)

        # 연락처 카드 (조직도에서 가져온 내선·휴대폰·계정, 겸직)
        contacts = [('내선', user.get('extension')), ('휴대폰', user.get('mobile')), ('계정', user.get('account'))]
        concurrent = [' › '.join(c.get('org_path') or []) + (f" ({c['title']})" if c.get('title') else '')
                      for c in (user.get('concurrent') or []) if c.get('org_path')]
        rows = [(k, v) for k, v in contacts if v] + [('겸직', v) for v in concurrent]
        if rows:
            card = QFrame()
            card.setObjectName('contactCard')
            card.setStyleSheet(f"QFrame#contactCard {{ background: {theme.c('bg_alt')}; border-radius: 10px; }}")
            grid = QGridLayout(card)
            grid.setContentsMargins(14, 10, 14, 10)
            grid.setHorizontalSpacing(12)
            grid.setVerticalSpacing(5)
            self.contact_labels = {}
            for i, (key, value) in enumerate(rows):
                k = QLabel(key)
                k.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('meta')}px; background: transparent;")
                v = QLabel(value)
                v.setWordWrap(True)
                v.setTextInteractionFlags(Qt.TextSelectableByMouse)
                v.setStyleSheet(f"color: {theme.c('text')}; font-size: {theme.fs('meta')}px; background: transparent;")
                grid.addWidget(k, i, 0, Qt.AlignTop)
                grid.addWidget(v, i, 1)
                self.contact_labels.setdefault(key, v)
            grid.setColumnStretch(1, 1)
            layout.addSpacing(4)
            layout.addWidget(card)

        layout.addSpacing(10)
        self.chat_button = QPushButton('나와의 채팅' if username == state.me else '1:1 채팅')
        self.chat_button.setProperty('primary', True)
        self.chat_button.setIcon(make_icon('chat', theme.c('on_accent'), 18))
        self.chat_button.setMinimumHeight(theme.px(38))
        layout.addWidget(self.chat_button)
        self.chat_button.clicked.connect(self._chat)

        # 숨김 / 차단 (내 프로필·AI 비서 제외)
        self.hide_button = self.block_button = None
        if username != state.me and not user.get('is_bot'):
            actions = QHBoxLayout()
            actions.setSpacing(6)
            registered = getattr(state, 'is_registered_friend', lambda _n: False)(username)
            self.friend_button = QPushButton('친구 삭제' if registered else '친구 추가')
            self.friend_button.setProperty('flat', True)
            self.friend_button.setCursor(Qt.PointingHandCursor)
            self.friend_button.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
            actions.addWidget(self.friend_button, 1)
            self.friend_button.clicked.connect(self.toggle_friend)
            self.hide_button = QPushButton('숨김 해제' if state.is_hidden(username) else '숨기기')
            self.block_button = QPushButton('차단 해제' if state.is_blocked(username) else '차단')
            for btn in (self.hide_button, self.block_button):
                btn.setProperty('flat', True)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet(f"color: {theme.c('text_sub')}; font-size: {theme.fs('meta')}px;")
                actions.addWidget(btn, 1)
            layout.addLayout(actions)
            self.hide_button.clicked.connect(self.toggle_hidden)
            self.block_button.clicked.connect(self.toggle_blocked)

    def _chat(self):
        self.state.open_direct(self.username)
        self.accept()

    def toggle_hidden(self):
        hide_friend(self.state, self.username, not self.state.is_hidden(self.username))
        self.accept()

    def toggle_friend(self):
        """프로필에서 친구 추가/삭제 - 상대의 전화번호·이메일을 알 필요 없이 바로 등록"""
        if self.state.is_registered_friend(self.username):
            self.state.remove_friend(self.username)
        else:
            user = self.state.user(self.username)
            contact = user.get('mobile') or user.get('email')
            if contact:
                self.state.add_friend(contact)
        self.accept()

    def toggle_blocked(self):
        if self.state.is_blocked(self.username):
            self.state.block_user(self.username, False)
            self.accept()
        elif confirm_block(self.state, self.username, self):
            self.accept()


# ================================================================ 행 위젯
ROW_AVATAR = theme.AVATAR_ROW      # 친구 탭 모든 행(내 프로필 · AI 비서 · 친구)의 아바타 크기 - 테마 한 곳에서 정한다


class MyProfileRow(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        me = state.user(state.me)
        row = QHBoxLayout(self)
        # 내 프로필도 아래 친구 · AI 비서 행과 같은 아바타 크기 · 간격 (예전 58px 은 혼자 커 보였다, 2026-10-10)
        row.setContentsMargins(16, 8, 16, 8)
        row.setSpacing(12)
        size = theme.px(ROW_AVATAR)
        self.avatar = Avatar(size=size)
        self.avatar.setPixmap(user_pixmap(state, state.me, size))
        row.addWidget(self.avatar, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addStretch(1)
        self.name = ElidedLabel(state.display_name(state.me), 'emphasis', 'text', bold=True)
        col.addWidget(self.name)
        self.status = ElidedLabel(me.get('status_message') or '상태메시지를 입력해 주세요', 'meta',
                                  'text_sub' if me.get('status_message') else 'text_hint')
        col.addWidget(self.status)
        col.addStretch(1)
        row.addLayout(col, 1)
        self.presence_button = PresenceButton(state)
        row.addWidget(self.presence_button, 0, Qt.AlignVCenter)


class FriendRow(QWidget):
    def __init__(self, state, username, kind='friend', on_gift=None, parent=None):
        super().__init__(parent)
        self.username = username
        user = state.user(username)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 7, 16, 7)
        row.setSpacing(12)
        size = theme.px(ROW_AVATAR)
        self.avatar = Avatar(size=size)
        self.avatar.setPixmap(user_pixmap(state, username, size, show_presence=(kind != 'bot')))
        row.addWidget(self.avatar, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addStretch(1)
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        self.name = ElidedLabel(state.display_name(username), 'emphasis', 'text', bold=True)
        self.name.setMinimumWidth(min(self.name.sizeHint().width(), theme.px(70)))
        name_row.addWidget(self.name)
        self.company = foreign_company(state, username)
        if self.company:
            name_row.addWidget(CompanyChip(self.company))
        name_row.addStretch(1)
        col.addLayout(name_row)
        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)
        presence = presence_of(state, username)
        self.presence_label = None
        if kind != 'bot' and presence in ('away', 'busy', 'meeting', 'vacation'):
            self.presence_label = QLabel(PRESENCE_LABELS[presence])
            self.presence_label.setStyleSheet(
                f"color: {PRESENCE_COLORS[presence]}; font-size: {theme.fs('caption')}px; font-weight: bold;")
            sub_row.addWidget(self.presence_label)
        self.sub = None
        if kind == 'bot':
            self.sub = ElidedLabel(BOT_HINT, 'meta', 'text_sub')
        elif kind == 'team':
            # 업무 정보: 직함 · 팀 · 지금 진행 중인 일정
            path = user.get('org_path') or []
            parts = [user.get('title') or '', path[1] if len(path) > 1 else '']
            ev = state.current_event_of(username) if hasattr(state, 'current_event_of') else None
            if ev:
                end = (ev.get('end') or '')[11:16]
                parts.append(f"일정 중 ~{end}" if end else '일정 중')
            text = ' · '.join(p for p in parts if p)
            if text:
                self.sub = ElidedLabel(text, 'meta', 'text_sub')
        elif kind == 'birthday':
            self.sub = ElidedLabel('🎂 오늘 생일이에요', 'meta', 'text_sub')
        if self.sub is not None:
            sub_row.addWidget(self.sub, 1)
        else:
            sub_row.addStretch(1)
        if self.sub is not None or self.presence_label is not None:
            col.addLayout(sub_row)
        col.addStretch(1)
        row.addLayout(col, 1)

        self.status = None
        self.gift_button = None
        if kind == 'birthday':
            self.gift_button = QPushButton('선물하기')
            self.gift_button.setCursor(Qt.PointingHandCursor)
            self.gift_button.setStyleSheet(
                f"QPushButton {{ background: {theme.c('bg')}; border: 1px solid {theme.c('border')};"
                f" border-radius: {theme.px(10)}px; padding: 4px 10px; font-size: {theme.fs('meta')}px; }}"
                f" QPushButton:hover {{ background: {theme.c('bg_hover')}; }}")
            if on_gift:
                self.gift_button.clicked.connect(lambda: on_gift(username))
            row.addWidget(self.gift_button, 0, Qt.AlignVCenter)
        elif kind != 'bot' and user.get('status_message'):
            self.status = StatusPill(user['status_message'])
            row.addWidget(self.status, 0, Qt.AlignVCenter)


class SectionHeader(QWidget):
    """'즐겨찾기 3 ▾' 형태의 접기 가능한 구역 머리글"""

    def __init__(self, title, count, collapsed, parent=None):
        super().__init__(parent)
        self.collapsed = collapsed
        row = QHBoxLayout(self)
        # 위아래 여백을 같게: 줄 전체가 눌림·마우스 강조 영역이므로 글자가 그 가운데에 와야 한다
        row.setContentsMargins(theme.GUTTER, theme.sp('m'), theme.GUTTER, theme.sp('m'))
        row.setSpacing(theme.sp('xs') + 1)
        self.title = ElidedLabel(title, 'meta', 'text_sub', bold=True)
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setFixedWidth(self.title.sizeHint().width())
        self.count = ElidedLabel(str(count), 'meta', 'text_hint')
        row.addWidget(self.title)
        row.addWidget(self.count, 1)
        self.chevron = QLabel()
        self.chevron.setPixmap(self._chevron_pixmap())
        row.addWidget(self.chevron)

    def _chevron_pixmap(self):
        from PyQt5.QtGui import QPixmap, QPen
        size = 12
        pm = QPixmap(size * 2, size * 2)
        pm.setDevicePixelRatio(2.0)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(theme.qc('text_hint'), 1.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        if self.collapsed:
            p.drawPolyline(*_pts([(4, 2.5), (8, 6), (4, 9.5)]))
        else:
            p.drawPolyline(*_pts([(2.5, 4), (6, 8), (9.5, 4)]))
        p.end()
        return pm

def _pts(points):
    from PyQt5.QtCore import QPointF
    return [QPointF(x, y) for x, y in points]


# ================================================================ 친구 탭
class FriendsTab(QWidget):
    def __init__(self, state, settings, parent=None):
        super().__init__(parent)
        self.state = state
        self.settings = settings
        self.collapsed = {'offline'}
        self.sections = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = TabHeader('친구')
        self.search_button = self.header.add_button('search', '이름, 상태메시지 검색')
        self.add_friend_button = self.header.add_button('friends', '친구 추가 (전화번호 · 이메일)')
        self.add_friend_button.refresh_icon = lambda color=None, b=None: _set_add_friend_icon(self.add_friend_button)
        _set_add_friend_icon(self.add_friend_button)
        self.group_button = self.header.add_button('add_chat', '그룹채팅 만들기')
        layout.addWidget(self.header)

        self.search_edit = make_search_edit('이름, 상태메시지 검색')
        wrap = QHBoxLayout()
        wrap.setContentsMargins(16, 0, 16, 8)
        wrap.addWidget(self.search_edit)
        layout.addLayout(wrap)

        self.story_bar = StoryBar(state)
        layout.addWidget(self.story_bar)
        self.story_bar.setVisible(bool(settings and settings.get('social_features')))
        self.story_line = QFrame()
        self.story_line.setFixedHeight(1)
        layout.addWidget(self.story_line)

        self.list = RowList()
        layout.addWidget(self.list, 1)

        self.search_button.clicked.connect(self.toggle_search)
        self.group_button.clicked.connect(self.show_create_dialog)
        # clicked 는 checked(False)를 넘기므로 감싸서 부른다 (그대로 연결하면 exec_=False 가 되어 창이 안 뜬다)
        self.add_friend_button.clicked.connect(lambda _checked=False: self.show_add_friend())
        if hasattr(state, 'my_friends_changed'):
            state.my_friends_changed.connect(self.refresh)
        self.search_edit.textChanged.connect(lambda _t: self.refresh())
        self.list.row_activated.connect(self._activate)
        self.list.itemClicked.connect(self._clicked)
        self.list.customContextMenuRequested.connect(self._show_context_menu)

        state.users_changed.connect(self.refresh)
        state.user_changed.connect(lambda _u: self.refresh())
        settings.changed.connect(self._on_setting)
        connect_avatar_changed(state, self.refresh)
        self.apply_theme()

    # ---- 데이터 ----
    def _matches(self, user, query):
        if not query:
            return True
        query = query.lower()
        name = self.state.display_name(user['username']).lower()
        return (query in name or query in user['username'].lower()
                or query in (user.get('status_message') or '').lower())

    def build_sections(self, query=''):
        """구역 키 → 사용자명 목록 (검색어 적용)"""
        state = self.state
        friends = [u for u in state.friends() if self._matches(u, query)]
        bots = [u['username'] for u in state.friends(include_bots=True)
                if u.get('is_bot') and self._matches(u, query)] if _supports_bots(state) else []
        favorites = [u['username'] for u in friends if state.is_favorite(u['username'])]
        mine = set(getattr(state, 'my_friends', []) or [])
        registered = [u['username'] for u in friends if u['username'] in mine and u['username'] not in favorites]
        # 업무 우선: 내 부서 동료를 맨 위에 (회사·부서가 같은 사람)
        my_team = state.team_of(state.me) if hasattr(state, 'team_of') else ('', '')
        team = [u['username'] for u in friends if my_team[1] and hasattr(state, 'team_of')
                and state.team_of(u['username']) == my_team
                and u['username'] not in favorites and u['username'] not in registered]
        others = [u for u in friends if u['username'] not in favorites and u['username'] not in registered
                  and u['username'] not in team]
        social = bool(self.settings and self.settings.get('social_features'))
        birthdays = [u['username'] for u in state.birthday_friends() if self._matches(u, query)] if social else []
        return {
            'bot': bots,
            'team': team,
            'birthday': birthdays,
            'favorites': favorites,
            'registered': registered,
            'online': [u['username'] for u in others if presence_of(state, u['username']) != 'offline'],
            'offline': [u['username'] for u in others if presence_of(state, u['username']) == 'offline'],
        }

    def section_members(self, key):
        return list(self.sections.get(key, []))

    def toggle_search(self):
        visible = self.search_edit.isHidden()
        self.search_edit.setVisible(visible)
        if visible:
            self.search_edit.setFocus()
        else:
            self.search_edit.clear()

    def toggle_section(self, key):
        if key in self.collapsed:
            self.collapsed.discard(key)
        else:
            self.collapsed.add(key)
        self.refresh()

    def refresh(self):
        if not self.state.me:
            return
        friends = self.state.friends()
        online = sum(1 for f in friends if self.state.is_online(f['username']))
        self.header.set_subtitle(f'친구 {len(friends)}명 · 온라인 {online}명')
        scroll = self.list.verticalScrollBar().value()
        self.list.clear()
        query = self.search_edit.text().strip()
        self.sections = self.build_sections(query)
        if not query:
            self.list.add_row(MyProfileRow(self.state), ('me', self.state.me))
        for key in ('bot', 'team', 'favorites', 'registered', 'birthday', 'online', 'offline'):
            members = self.sections[key]
            if not members and (query or key in ('bot', 'team', 'birthday', 'favorites', 'registered')):
                continue
            collapsed = key in self.collapsed and not query
            self.list.add_row(SectionHeader(SECTION_TITLES[key], len(members), collapsed),
                              ('section', key), selectable=False)
            if collapsed:
                continue
            kind = {'bot': 'bot', 'birthday': 'birthday', 'team': 'team'}.get(key, 'friend')
            for name in members:
                self.list.add_row(FriendRow(self.state, name, kind, on_gift=self.send_gift),
                                  ('friend', name, key))
        self.list.verticalScrollBar().setValue(scroll)

    # ---- 동작 ----
    def _on_setting(self, key):
        if key == 'favorites':
            self.refresh()
        elif key == 'social_features':
            self.story_bar.setVisible(bool(self.settings.get('social_features')))
            self.refresh()

    def _clicked(self, item):
        data = item.data(Qt.UserRole)
        if data[0] == 'section':
            self.toggle_section(data[1])
        elif data[0] == 'me':
            self.edit_profile()

    def _activate(self, item):
        data = item.data(Qt.UserRole)
        if data and data[0] == 'friend':
            self.state.open_direct(data[1])

    def send_gift(self, username):
        # 선물하기 결제는 범위 밖 - 1:1 채팅방만 연다
        self.state.open_direct(username)

    def edit_profile(self):
        ProfileEditDialog(self.state, self.window()).exec_()

    def show_profile(self, username):
        ProfileDialog(self.state, username, self.window()).exec_()

    def show_create_dialog(self):
        CreateGroupDialog(self.state, self.window()).exec_()

    def show_add_friend(self, exec_=True):
        dlg = AddFriendDialog(self.state, self.window())
        if exec_:
            dlg.exec_()
        return dlg

    def context_menu_for(self, data):
        menu = QMenu(self)
        if data[0] == 'me':
            menu.addAction('프로필 편집', self.edit_profile)
            menu.addAction('나와의 채팅', lambda: self.state.open_direct(self.state.me))
            return menu
        if data[0] != 'friend':
            return None
        name = data[1]
        menu.addAction('1:1 채팅', lambda: self.state.open_direct(name))
        if not self.state.user(name).get('is_bot'):
            fav = self.state.is_favorite(name)
            menu.addAction('즐겨찾기 해제' if fav else '즐겨찾기 추가',
                           lambda: self.settings.toggle_in('favorites', name))
        menu.addAction('채팅방에 초대…', lambda: InviteToRoomDialog(self.state, name, self.window()).exec_())
        menu.addAction('프로필 보기', lambda: self.show_profile(name))
        if self.state.stories_of(name) and not self.state.is_story_hidden(name):
            menu.addAction('펑 보기', lambda: self.story_bar.open_story(name))
        if self.settings.get('social_features') and not self.state.user(name).get('is_bot'):
            # 친구 소식 숨기기 (카카오톡 2026 2차 업데이트): 친구 관계는 그대로, 내 화면에서만 감춤
            hidden = self.state.is_story_hidden(name)
            menu.addAction('소식 다시 보기' if hidden else '소식 숨기기',
                           lambda: self.state.set_story_hidden(name, not hidden))
        if not self.state.user(name).get('is_bot'):
            menu.addSeparator()
            if getattr(self.state, 'is_registered_friend', lambda _n: False)(name):
                menu.addAction('친구 삭제', lambda: self.state.remove_friend(name))
            menu.addAction('숨기기', lambda: hide_friend(self.state, name, True))
            menu.addAction('차단', lambda: confirm_block(self.state, name, self.window()))
        return menu

    def _show_context_menu(self, pos):
        item = self.list.itemAt(pos)
        if item is None:
            return
        menu = self.context_menu_for(item.data(Qt.UserRole))
        if menu is not None:
            menu.exec_(self.list.viewport().mapToGlobal(pos))

    def apply_theme(self):
        self.header.apply_theme()
        self.search_edit.setStyleSheet(search_box_qss())
        self.story_bar.apply_theme()
        self.story_line.setStyleSheet(f"background: {theme.c('border')}; margin: 0 16px;")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"FriendsTab {{ background: {theme.c('bg')}; }}")
        self.refresh()


def _supports_bots(state):
    try:
        state.friends(include_bots=True)
        return True
    except TypeError:
        return False


__all__ = ['FriendsTab', 'ProfileEditDialog', 'ProfileDialog', 'PresenceButton', 'presence_menu',
           'avatar_png_from_path', 'QMessageBox', 'StoryBar', 'StoryBubble', 'hide_friend', 'confirm_block']
