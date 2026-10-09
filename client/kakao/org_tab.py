# -*- coding: utf-8 -*-
"""
조직도 탭 - 지주사 → 계열사 → 조직(부·본부·실·팀, 여러 단계) → 구성원
- 서버 welcome 의 org(지주사·계열사 순서·조직 순서)가 있으면 그 구조를, 없으면 회사 → 부서 2단계로 보여준다.
- 모든 머리글은 접을 수 있다. 겸직자는 겸직 조직에도 '겸직' 표시와 함께 나온다.
- 구성원 더블클릭 → 1:1 채팅, 우클릭 → 1:1 채팅 / 채팅방에 초대 / 프로필 보기
"""

from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QPainterPath, QPen, QPixmap, QIcon, QColor, QFontMetrics
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMenu, QSizePolicy, QDialog, QLineEdit

from client.kakao import theme
from client.kakao.widgets import Avatar
from client.kakao.chats_tab import (ElidedLabel, RowList, TabHeader, make_search_edit, search_box_qss, InviteToRoomDialog,
                                    user_pixmap, presence_of, connect_avatar_changed, PRESENCE_LABELS,
                                    PRESENCE_COLORS)

GUEST_COMPANY = '게스트'
INDENT = 14          # 조직 단계별 들여쓰기(px)
TITLE_RANK = ['회장', '대표이사', '사장', '부사장', '전무', '상무이사', '상무', '이사', '실장', '본부장', '팀장',
              '부장', '차장', '과장', '수석', '책임', '대리', '선임', '주임', '매니져', '매니저', '연구', '사원', '봇']


# ================================================================ 건물 아이콘
def building_path():
    p = QPainterPath()
    p.addRoundedRect(QRectF(4.5, 3.5, 10, 17), 1.2, 1.2)
    p.moveTo(14.5, 9.5)
    p.lineTo(19.5, 9.5)
    p.lineTo(19.5, 20.5)
    p.lineTo(14.5, 20.5)
    for y in (7.5, 11.5, 15.5):
        p.moveTo(7.5, y)
        p.lineTo(8.5, y)
        p.moveTo(10.5, y)
        p.lineTo(11.5, y)
    p.moveTo(3, 20.5)
    p.lineTo(21, 20.5)
    return p


def paint_building(painter, rect, color, stroke=1.7):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate(rect.x(), rect.y())
    painter.scale(rect.width() / 24.0, rect.height() / 24.0)
    pen = QPen(QColor(color), stroke)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(building_path())
    painter.restore()


def building_icon(color, size=24):
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    paint_building(p, QRectF(0, 0, size, size), color)
    p.end()
    return QIcon(pm)


# ================================================================ 행 위젯
class _Chevron(QWidget):
    def __init__(self, collapsed, parent=None, color=None):
        super().__init__(parent)
        self.collapsed = collapsed
        self.color = color
        self.setFixedSize(12, 12)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(self.color) if self.color else theme.qc('text_hint'), 1.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        pts = [(4, 2.5), (8, 6), (4, 9.5)] if self.collapsed else [(2.5, 4), (6, 8), (9.5, 4)]
        p.drawPolyline(*[QPointF(x, y) for x, y in pts])


class HoldingHeader(QWidget):
    """지주사 머리글 - 브랜드 색 띠"""

    def __init__(self, holding, count, collapsed, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(building_icon(theme.c('on_accent'), 20).pixmap(20, 20))
        row.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title = QLabel(holding.get('name', ''))
        self.title.setStyleSheet(f"color: {theme.c('on_accent')}; font-size: {theme.fs('title')}px; font-weight: bold;")
        col.addWidget(self.title)
        sub = ' · '.join(x for x in ('지주회사', f'계열사 {count}곳') if x)
        self.sub = QLabel(sub)
        self.sub.setStyleSheet(f"color: {theme.c('on_accent')}; font-size: {theme.fs('caption')}px;")
        col.addWidget(self.sub)
        row.addLayout(col, 1)
        row.addWidget(_Chevron(collapsed, color=theme.c('on_accent')))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), theme.qc('yellow'))


class CompanyHeader(QWidget):
    def __init__(self, company, count, collapsed, mine=False, parent=None, depth=0, business=''):
        super().__init__(parent)
        self.company = company
        row = QHBoxLayout(self)
        row.setContentsMargins(16 + depth * INDENT, 9, 16, 9)
        row.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(building_icon(theme.c('yellow') if mine else theme.c('text_sub'), 18).pixmap(18, 18))
        row.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(1)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.title = ElidedLabel(company, 'emphasis', 'text', bold=True)
        self.title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        top.addWidget(self.title)
        if mine:
            tag = QLabel('내 회사')
            tag.setStyleSheet(f"color: {theme.c('on_accent')}; background: {theme.c('yellow')}; border-radius: 4px;"
                              f" padding: 0px 5px; font-size: {theme.fs('micro')}px; font-weight: bold;")
            top.addWidget(tag)
        self.count = ElidedLabel(f'{count}명' if count else '', 'meta', 'text_hint')
        self.count.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.count.setFixedWidth(self.count.sizeHint().width())
        top.addWidget(self.count)
        top.addStretch(1)
        col.addLayout(top)
        if business:
            col.addWidget(ElidedLabel(business, 'caption', 'text_hint'))
        row.addLayout(col, 1)
        row.addWidget(_Chevron(collapsed))

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), theme.qc('bg_alt'))


class UnitHeader(QWidget):
    """조직(부·본부·실·팀) 머리글 - 단계만큼 들여쓰기, 접기 가능"""

    def __init__(self, name, count, collapsed, depth=0, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(22 + depth * INDENT, 8, 16, 4)
        row.setSpacing(6)
        row.addWidget(_Chevron(collapsed))
        self.title = ElidedLabel(name or '소속 없음', 13 if depth == 0 else 12, 'text' if depth == 0 else 'text_sub',
                                 bold=True)
        self.title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row.addWidget(self.title)
        self.count = ElidedLabel(str(count), 'meta', 'text_hint')
        self.count.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.count.setFixedWidth(self.count.sizeHint().width())
        row.addWidget(self.count)
        row.addStretch(1)


DepartmentHeader = UnitHeader  # 이전 이름 호환


# ================================================================ 그룹웨어 스타일 (사내 조직도 화면과 동일한 구성)
class CountChip(QWidget):
    """'👤 52 ›' 인원 칩 - 누르면 구성원 목록"""

    clicked = pyqtSignal()

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self.count = count
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip('구성원 보기')
        f = theme.font('meta', bold=True)
        w = QFontMetrics(f).horizontalAdvance(str(count))
        self.setFixedSize(w + 44, 22)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.NoPen)
        p.setBrush(theme.qc('bg_selected'))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        sub = theme.qc('text_sub')
        # 사람 아이콘
        p.setBrush(sub)
        p.drawEllipse(QRectF(9, 5.5, 5.5, 5.5))
        path = QPainterPath()
        path.addRoundedRect(QRectF(7, 11.5, 9.5, 5.5), 2.5, 2.5)
        p.drawPath(path)
        p.setPen(theme.qc('text_sub'))
        p.setFont(theme.font('meta', bold=True))
        p.drawText(QRectF(20, 0, self.width() - 32, self.height()), Qt.AlignVCenter | Qt.AlignLeft, str(self.count))
        pen = QPen(theme.qc('text_hint'), 1.3)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        x = self.width() - 10
        p.drawPolyline(QPointF(x - 2.5, 8), QPointF(x, 11), QPointF(x - 2.5, 14))

    def mousePressEvent(self, event):
        self.clicked.emit()


class TreeNodeRow(QWidget):
    """⌄/› + 이름 (+ 숫자 또는 인원 칩) 한 줄 - 들여쓰기 단계별"""

    def __init__(self, name, count, collapsed, depth=0, chip=False, bold=True, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(20 + depth * 22, 9, 16, 9)
        row.setSpacing(8)
        row.addWidget(_Chevron(collapsed))
        self.title = ElidedLabel(name, 'emphasis', 'text', bold=bold)
        self.title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        row.addWidget(self.title)
        self.chip = None
        if chip:
            self.chip = CountChip(count)
            row.addWidget(self.chip, 0, Qt.AlignVCenter)
        else:
            self.count = ElidedLabel(str(count), 'body', 'text_sub', bold=True)
            self.count.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.count.setFixedWidth(self.count.sizeHint().width())
            row.addWidget(self.count)
        row.addStretch(1)


class CompactMemberRow(QWidget):
    """아바타 + '이름 직위' 한 줄 (그룹웨어 조직도 구성원 행)"""

    def __init__(self, state, username, depth=0, concurrent_title=None, parent=None):
        super().__init__(parent)
        self.username = username
        user = state.user(username)
        row = QHBoxLayout(self)
        row.setContentsMargins(26 + depth * 22, 5, 16, 5)
        row.setSpacing(10)
        size = theme.px(32)
        self.avatar = Avatar(size=size)
        self.avatar.setPixmap(user_pixmap(state, username, size, show_presence=not user.get('is_bot')))
        row.addWidget(self.avatar)
        title = concurrent_title if concurrent_title is not None else (user.get('title') or '')
        name = state.display_name(username) + (' (나)' if username == state.me else '')
        self.name = ElidedLabel(f'{name} {title}'.strip(), 'emphasis', 'text')
        row.addWidget(self.name, 1)
        if concurrent_title is not None:
            tag = QLabel('겸직')
            tag.setStyleSheet(f"color: {theme.c('yellow')}; border: 1px solid {theme.c('yellow')};"
                              f" border-radius: 4px; padding: 0px 4px; font-size: {theme.fs('micro')}px;")
            row.addWidget(tag)
        tips = [x for x in (' › '.join(user.get('org_path') or []),
                            f"내선 {user['extension']}" if user.get('extension') else '',
                            user.get('mobile') or '', user.get('account') or '') if x]
        self.setToolTip('\n'.join(tips))


class MembersDialog(QDialog):
    """인원 칩을 누르면 뜨는 구성원 목록 (검색 · 더블클릭 1:1 채팅)"""

    def __init__(self, state, title, usernames, parent=None):
        super().__init__(parent)
        self.state = state
        self.usernames = list(usernames)
        self.setWindowTitle(f'{title} 구성원')
        self.setMinimumSize(340, 460)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 14, 0, 10)
        head = QLabel(f'{title}  {len(self.usernames)}명')
        head.setStyleSheet(f"font-size: {theme.fs('lead')}px; font-weight: bold; padding: 0 20px;")
        col.addWidget(head)
        self.search = QLineEdit()
        self.search.setPlaceholderText('이름, 직위, 부서, 전화, 아이디')
        self.search.setStyleSheet(search_box_qss())
        wrap = QHBoxLayout()
        wrap.setContentsMargins(16, 8, 16, 8)
        wrap.addWidget(self.search)
        col.addLayout(wrap)
        self.list = RowList()
        col.addWidget(self.list, 1)
        self.search.textChanged.connect(self.refresh)
        self.list.row_activated.connect(self._open)
        self.refresh()

    def refresh(self):
        q = self.search.text().strip().lower()
        self.list.clear()
        for name in self.usernames:
            u = self.state.user(name)
            fields = [self.state.display_name(name), u.get('title'), ' '.join(u.get('org_path') or []),
                      u.get('extension'), u.get('mobile'), u.get('account')]
            if q and not any(q in (f or '').lower() for f in fields):
                continue
            self.list.add_row(CompactMemberRow(self.state, name), ('member', name))

    def rows(self):
        return [self.list.item(i).data(Qt.UserRole)[1] for i in range(self.list.count())]

    def _open(self, item):
        self.state.open_direct(item.data(Qt.UserRole)[1])
        self.accept()


class HintRow(QWidget):
    def __init__(self, text, depth=0, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(26 + depth * INDENT, 6, 16, 8)
        row.addWidget(ElidedLabel(text, 'meta', 'text_hint'))


class MemberRow(QWidget):
    def __init__(self, state, username, parent=None, depth=0, concurrent_title=None):
        super().__init__(parent)
        self.username = username
        user = state.user(username)
        row = QHBoxLayout(self)
        row.setContentsMargins(26 + depth * INDENT, 6, 16, 6)
        row.setSpacing(12)
        size = theme.px(40)
        self.avatar = Avatar(size=size)
        self.avatar.setPixmap(user_pixmap(state, username, size, show_presence=not user.get('is_bot')))
        row.addWidget(self.avatar, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addStretch(1)
        top = QHBoxLayout()
        top.setSpacing(6)
        name = state.display_name(username) + (' (나)' if username == state.me else '')
        self.name = ElidedLabel(name, 'emphasis', 'text', bold=True)
        top.addWidget(self.name)
        self.title = None
        title = concurrent_title if concurrent_title is not None else user.get('title')
        if title:
            self.title = ElidedLabel(title, 'meta', 'text_sub')
            self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.title.setFixedWidth(self.title.sizeHint().width())
            top.addWidget(self.title)
        if concurrent_title is not None:
            tag = QLabel('겸직')
            tag.setStyleSheet(f"color: {theme.c('yellow')}; border: 1px solid {theme.c('yellow')};"
                              f" border-radius: 4px; padding: 0px 4px; font-size: {theme.fs('micro')}px;")
            top.addWidget(tag)
        presence = presence_of(state, username)
        if not user.get('is_bot') and presence in ('away', 'busy', 'meeting'):
            label = QLabel(PRESENCE_LABELS[presence])
            label.setStyleSheet(f"color: {PRESENCE_COLORS[presence]}; font-size: {theme.fs('caption')}px; font-weight: bold;")
            top.addWidget(label)
        top.addStretch(1)
        col.addLayout(top)
        self.status = None
        sub = ' · '.join(x for x in (user.get('status_message'),
                                     f"내선 {user['extension']}" if user.get('extension') else '') if x)
        if sub:
            self.status = ElidedLabel(sub, 'meta', 'text_hint')
            col.addWidget(self.status)
        col.addStretch(1)
        row.addLayout(col, 1)


# ================================================================ 조직도 탭
class OrgTab(QWidget):
    def __init__(self, state, settings, parent=None):
        super().__init__(parent)
        self.state = state
        self.settings = settings
        self.collapsed = set()          # 접힌 회사 이름
        self.collapsed_nodes = set()    # ('holding',) / ('unit', company, path_tuple)
        self.expanded_empty = set()     # 사용자가 펼친 빈 계열사
        self.expanded_depts = set()     # 그룹웨어 화면에서 펼친 부서 (기본: 모두 접힘)
        self._holding_default_set = False
        self.tree = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = TabHeader('조직도')
        self.search_button = self.header.add_button('search', '이름, 부서, 직함 검색')
        layout.addWidget(self.header)
        self.search_edit = make_search_edit('이름, 직위, 직책, 직급, 부서, 전화, 아이디')
        self.search_edit.setAccessibleName('조직도 검색')
        self.search_edit.show()
        wrap = QHBoxLayout()
        wrap.setContentsMargins(16, 0, 16, 8)
        wrap.addWidget(self.search_edit)
        layout.addLayout(wrap)
        self.list = RowList()
        layout.addWidget(self.list, 1)
        self.empty_label = QLabel('검색 결과가 없습니다')
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label, 1)

        self.search_button.clicked.connect(lambda: self.search_edit.setFocus())
        self.search_edit.textChanged.connect(lambda _t: self.refresh())
        self.list.row_activated.connect(self._activate)
        self.list.itemClicked.connect(self._clicked)
        self.list.customContextMenuRequested.connect(self._show_context_menu)
        state.users_changed.connect(self.refresh)
        state.user_changed.connect(lambda _u: self.refresh())
        connect_avatar_changed(state, self.refresh)
        self.apply_theme()

    # ---- 데이터 ----
    def _all_users(self):
        try:
            users = list(self.state.friends(include_bots=True))
        except TypeError:
            users = list(self.state.friends())
        if self.state.me:
            users.append(self.state.user(self.state.me))
        return users

    def _matches(self, user, query):
        if not query:
            return True
        query = query.lower()
        fields = [self.state.display_name(user['username']), user['username'], user.get('title'),
                  user.get('department'), user.get('company'), user.get('status_message'), user.get('extension'),
                  user.get('mobile'), (user.get('mobile') or '').replace('-', ''), user.get('account')]
        fields += list(user.get('org_path') or [])
        return any(query in (f or '').lower() for f in fields)

    def org(self):
        return getattr(self.state, 'org', None) or {}

    def org_meta(self, company):
        return next((c for c in self.org().get('companies', []) if c.get('name') == company), {})

    @staticmethod
    def _member_key(user):
        title = user.get('title') or ''
        rank = TITLE_RANK.index(title) if title in TITLE_RANK else len(TITLE_RANK)
        return (rank, user.get('display_name') or user['username'])

    def _company_order(self, names):
        """서버 org 의 계열사 순서 → 그 밖의 회사(내 회사 우선) → 게스트"""
        listed = [c['name'] for c in self.org().get('companies', []) if c.get('name')]
        mine = (self.state.user(self.state.me).get('company') or '').strip()
        extra = sorted((n for n in names if n not in listed),
                       key=lambda n: (n != mine, n == GUEST_COMPANY, n))
        if not listed:
            return extra
        return listed + extra

    def build_tree(self, query=''):
        """{company: {'units': {path_tuple: [(username, concurrent_title|None)]}}} (순서 보장)"""
        raw = {}
        for user in self._all_users():
            if not self._matches(user, query):
                continue
            company = (user.get('company') or GUEST_COMPANY).strip() or GUEST_COMPANY
            path = tuple(user.get('org_path') or ([user['department']] if user.get('department') else []))
            units = raw.setdefault(company, {})
            units.setdefault(path, []).append((user, None))
            for extra in user.get('concurrent') or []:
                extra_path = tuple(extra.get('org_path') or [])
                if extra_path and extra_path != path:
                    units.setdefault(extra_path, []).append((user, extra.get('title') or user.get('title') or ''))
        meta = {c['name']: c for c in self.org().get('companies', []) if c.get('name')}
        ordered = {}
        for company in self._company_order(set(raw)):
            units = raw.get(company, {})
            if query and not units:
                continue
            order = [tuple(u) for u in (meta.get(company, {}).get('units') or [])]

            def unit_key(path, order=order):
                # 조직 순서 목록에 있으면 그 순서, 없으면 뒤에 이름순. 소속 없음('')은 맨 뒤
                prefix_rank = []
                for depth in range(1, len(path) + 1):
                    node = path[:depth]
                    prefix_rank.append(order.index(node) if node in order else len(order) + 1)
                return (not path, prefix_rank, path)
            ordered[company] = {path: [(u['username'], ct) for u, ct in
                                       sorted(units[path], key=lambda x: (x[1] is not None, self._member_key(x[0])))]
                                for path in sorted(units, key=unit_key)}
        return ordered

    def companies(self):
        return list(self.tree)

    def members_of(self, company, department=None):
        """회사(또는 그 안의 조직: 마지막 단계 이름 또는 경로 튜플)의 주소속 구성원"""
        units = self.tree.get(company, {})
        names = []
        for path, members in units.items():
            if department is not None:
                target = tuple(department) if isinstance(department, (tuple, list)) else None
                if not (path == target or (target is None and path and path[-1] == department)
                        or (target is None and department == '' and not path)):
                    continue
            names += [u for u, ct in members if ct is None and u not in names]
        return names

    def _subtree_count(self, units, prefix):
        people = set()
        for path, members in units.items():
            if path[:len(prefix)] == prefix:
                people.update(u for u, _ct in members)
        return len(people)

    def refresh(self):
        if not self.state.me:
            return
        query = self.search_edit.text().strip()
        self.tree = self.build_tree(query)
        org = self.org()
        holding = org.get('holding')
        people = {u for units in self.tree.values() for ms in units.values() for u, _ in ms}
        if holding:
            self.header.set_subtitle(f"{holding.get('name', '')} · 계열사 {len(org.get('companies', []))}곳"
                                     f" · 구성원 {len(people)}명")
        else:
            self.header.set_subtitle(f'그룹사 {len(self.tree)}곳 · 구성원 {len(people)}명')
        scroll = self.list.verticalScrollBar().value()
        self.list.clear()
        mine = (self.state.user(self.state.me).get('company') or '').strip()
        meta = {c['name']: c for c in org.get('companies', []) if c.get('name')}
        base = 0
        # 그룹웨어 체계(depth=1)인 회사는 사내 조직도 화면과 같은 모양으로 맨 위에
        groupware = [c for c in self.tree if meta.get(c, {}).get('depth') == 1]
        for company in groupware:
            self._render_groupware(company, self.tree[company], meta[company], query)
        if groupware and holding:
            self.list.add_row(HintRow('그룹사', 0), ('section', '그룹사'), selectable=False)
            if ('holding',) not in self.collapsed_nodes and not self._holding_default_set:
                self.collapsed_nodes.add(('holding',))   # 계열사 묶음은 처음엔 접어 둔다
            self._holding_default_set = True
        if holding:
            collapsed = ('holding',) in self.collapsed_nodes and not query
            self.list.add_row(HoldingHeader(holding, len(org.get('companies', [])), collapsed),
                              ('holding', holding.get('name', '')), selectable=False)
            if collapsed:
                self._finish(scroll)
                return
            base = 1
        for company, units in self.tree.items():
            if company in groupware:
                continue
            count = self._subtree_count(units, ())
            # 구성원이 없는 계열사는 처음엔 접어 둔다(펼치면 안내 문구)
            if company not in self.expanded_empty and not units and company not in self.collapsed:
                self.collapsed.add(company)
            collapsed = (company in self.collapsed) and not query
            depth = base if company in meta else 0
            info = meta.get(company, {})
            header = CompanyHeader(company, count, collapsed, mine=(company == mine), depth=depth,
                                   business=info.get('business', ''))
            # 회사 홈페이지(kcins.co.kr › 계열사)에서 가져온 정보
            header.setToolTip('\n'.join(x for x in (company, info.get('business'), info.get('homepage'),
                                                     f"대표전화 {info['phone']}" if info.get('phone') else '') if x))
            self.list.add_row(header, ('company', company), selectable=False)
            if collapsed:
                continue
            if not units:
                self.list.add_row(HintRow('등록된 구성원이 없습니다', depth + 1), ('empty', company),
                                  selectable=False)
                continue
            shown = set()
            for path, members in units.items():
                # 이 경로의 상위 조직 머리글(아직 안 나온 것)부터
                hidden = False
                for d in range(1, len(path) + 1):
                    node = path[:d]
                    key = ('unit', company, node)
                    if any(key[2][:k] in self._collapsed_units(company) for k in range(1, d)):
                        hidden = True
                        break
                    if node not in shown:
                        shown.add(node)
                        unit_collapsed = node in self._collapsed_units(company) and not query
                        self.list.add_row(UnitHeader(node[-1], self._subtree_count(units, node), unit_collapsed,
                                                     depth=depth + d - 1), key, selectable=False)
                    if node in self._collapsed_units(company) and not query:
                        hidden = True
                        break
                if hidden:
                    continue
                if not path and len(units) > 1:
                    self.list.add_row(UnitHeader('', len(members), False, depth=depth), ('unit', company, ()),
                                      selectable=False)
                for name, concurrent_title in members:
                    self.list.add_row(MemberRow(self.state, name, depth=depth + len(path),
                                                concurrent_title=concurrent_title), ('member', name))
        self._finish(scroll)

    def _render_groupware(self, company, units, info, query):
        """케이씨에스 52 › 주식회사케이씨에스 [👤52 ›] › 직속 구성원 + 부서(접힘, 인원 칩)"""
        group = info.get('group_name') or company
        legal = info.get('legal_name') or company
        members = {}   # 부서 → [(username, 겸직직위|None)]
        for path, ms in units.items():
            dept = path[0] if path else ''
            for name, ct in ms:
                if all(name != n for n, _ in members.setdefault(dept, [])):
                    members[dept].append((name, ct))
        everyone = list(dict.fromkeys(n for ms in members.values() for n, ct in ms if ct is None))
        if info.get('count_excludes_root'):
            # 그룹웨어처럼 회사 인원은 부서에 속한 사람 수 (대표이사·관리자 계정 같은 직속 계정 제외)
            in_depts = {n for d, ms in members.items() if d for n, _ in ms}
            everyone = [n for n in everyone if n in in_depts]
        group_collapsed = ('group', company) in self.collapsed_nodes and not query
        self.list.add_row(TreeNodeRow(group, len(everyone), group_collapsed, depth=0),
                          ('group', company), selectable=False)
        if group_collapsed:
            return
        company_collapsed = company in self.collapsed and not query
        row = TreeNodeRow(legal, len(everyone), company_collapsed, depth=1, chip=True)
        row.chip.clicked.connect(lambda: self.show_members(legal, everyone))
        self.list.add_row(row, ('company', company), selectable=False)
        if company_collapsed:
            return
        root_order = info.get('root_members') or []
        root = sorted(members.get('', []), key=lambda x: (root_order.index(x[0]) if x[0] in root_order
                                                          else len(root_order), x[0]))
        for name, ct in root:
            self.list.add_row(CompactMemberRow(self.state, name, depth=1, concurrent_title=ct), ('member', name))
        order = [u[0] for u in (info.get('units') or []) if u]
        depts = [d for d in order if d in members] + sorted(d for d in members if d and d not in order)
        if not query:
            depts = [d for d in order if d] + [d for d in depts if d not in order]
        for dept in depts:
            ms = sorted(members.get(dept, []), key=lambda x: (x[1] is not None, self._member_key(self.state.user(x[0]))))
            open_ = dept in self.expanded_depts or bool(query)
            node = TreeNodeRow(dept, len(ms), not open_, depth=2, chip=True, bold=False)
            node.chip.clicked.connect(lambda d=dept, names=[n for n, _ in ms]: self.show_members(d, names))
            self.list.add_row(node, ('unit', company, (dept,)), selectable=False)
            if open_:
                if not ms:
                    self.list.add_row(HintRow('구성원이 없습니다', 3), ('empty', dept), selectable=False)
                for name, ct in ms:
                    self.list.add_row(CompactMemberRow(self.state, name, depth=2, concurrent_title=ct),
                                      ('member', name))

    def show_members(self, title, usernames, exec_=True):
        dlg = MembersDialog(self.state, title, usernames, self.window())
        if exec_:
            dlg.exec_()
        return dlg

    def _collapsed_units(self, company):
        return {node[2] for node in self.collapsed_nodes if node[0] == 'unit' and node[1] == company}

    def _finish(self, scroll):
        self.list.verticalScrollBar().setValue(scroll)
        has_rows = self.list.count() > 0
        self.list.setVisible(has_rows)
        self.empty_label.setVisible(not has_rows)

    # ---- 동작 ----
    def toggle_company(self, company):
        if company in self.collapsed:
            self.collapsed.discard(company)
            self.expanded_empty.add(company)
        else:
            self.collapsed.add(company)
        self.refresh()

    def toggle_node(self, node):
        if node in self.collapsed_nodes:
            self.collapsed_nodes.discard(node)
        else:
            self.collapsed_nodes.add(node)
        self.refresh()

    def toggle_unit(self, company, path):
        self.toggle_node(('unit', company, tuple(path)))

    def _clicked(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        if data[0] == 'company':
            self.toggle_company(data[1])
        elif data[0] == 'holding':
            self.toggle_node(('holding',))
        elif data[0] == 'group':
            self.toggle_node(('group', data[1]))
        elif data[0] == 'unit' and data[2] and self.org_meta(data[1]).get('depth') == 1:
            dept = data[2][0]
            if dept in self.expanded_depts:
                self.expanded_depts.discard(dept)
            else:
                self.expanded_depts.add(dept)
            self.refresh()
        elif data[0] == 'unit' and data[2]:
            self.toggle_unit(data[1], data[2])

    def _activate(self, item):
        data = item.data(Qt.UserRole)
        if data and data[0] == 'member':
            self.state.open_direct(data[1])

    def context_menu_for(self, data):
        if not data or data[0] != 'member':
            return None
        name = data[1]
        menu = QMenu(self)
        menu.addAction('나와의 채팅' if name == self.state.me else '1:1 채팅',
                       lambda: self.state.open_direct(name))
        if name != self.state.me:
            menu.addAction('채팅방에 초대…', lambda: InviteToRoomDialog(self.state, name, self.window()).exec_())
        menu.addAction('프로필 보기', lambda: self.show_profile(name))
        menu.addAction('연락처 보내기…', lambda: self.send_contact_to_room(name))
        return menu

    def send_contact_to_room(self, username, room_id=None):
        """조직도에서 찾은 사람의 연락처를 채팅방에 보낸다 ('누구에게 물어볼지' 찾은 뒤 바로 공유)"""
        if room_id is None:
            from client.kakao.chat_room import ForwardDialog
            dlg = ForwardDialog(self.state, self.window())
            dlg.setWindowTitle(f'{self.state.display_name(username)}님 연락처를 보낼 채팅방')
            if dlg.exec_() != dlg.Accepted or not dlg.room_id():
                return None
            room_id = dlg.room_id()
        self.state.send_contact(room_id, username)
        return room_id

    def show_profile(self, username):
        from client.kakao.friends_tab import ProfileDialog
        ProfileDialog(self.state, username, self.window()).exec_()

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
        self.empty_label.setStyleSheet(f"color: {theme.c('text_hint')}; font-size: {theme.fs('body')}px;")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"OrgTab {{ background: {theme.c('bg')}; }}")
        self.refresh()
