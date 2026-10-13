# -*- coding: utf-8 -*-
"""조직도 개편 (명세 §7.7 · §4.4): 그룹사 아래 지주사 · 계열사 같은 단계, KCS AI 지식봇 맨 위,
게스트는 그대로 맨 아래, 그룹 관리자의 조직도 그룹 만들기 · 수정 · 삭제"""

import os
import sys
import unittest

from PyQt5.QtCore import Qt, QPoint, QEvent
from PyQt5.QtGui import QMouseEvent, QColor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest

from tests.kakao_fakes import app, make_demo_state, expand_org
from tests.test_kakao_server import ServerTestBase, Client, uname

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import import_org_xlsx as imp  # noqa: E402

from client.kakao.org_tab import OrgTab, CompanyHeader, GroupDialog, CARD_INSET  # noqa: E402

GROUP_NAMES = [imp.HOLDING['name']] + [a['name'] for a in imp.AFFILIATES]


def rows(lst):
    return [lst.item(i).data(Qt.UserRole) for i in range(lst.count())]


class OrgLayoutTests(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.state.org = {'holding': dict(imp.HOLDING), 'companies': [dict(a) for a in imp.AFFILIATES]}
        self.conn.push('user_updated', user=dict(self.state.user('김철수'), company='한네트', department='영업팀'))
        self.conn.push('user_updated', user=dict(self.state.user('이영희'), company='게스트'))
        self.conn.push('user_updated', user={'username': 'AI 비서', 'display_name': 'AI 비서', 'company': 'KCS AI',
                                             'department': '지식봇', 'title': '봇', 'is_bot': True,
                                             'online': True, 'presence': 'online', 'status_message': ''})
        self.state.my_friends = list(self.state.users)
        self.tab = OrgTab(self.state, self.state.settings)
        expand_org(self.tab)

    def header(self, key):
        return self.tab.list.itemWidget(self.tab.list.find_data(key))

    def test_holding_and_affiliates_on_same_level(self):
        data = rows(self.tab.list)
        companies = [d[1] for d in data if d[0] == 'company']
        section = data.index(('section', '그룹사'))
        self.assertEqual(len(GROUP_NAMES), 14)                                  # 한국지주 + 계열사 13곳
        self.assertEqual([c for c in companies if c in GROUP_NAMES], GROUP_NAMES)
        self.assertEqual(data[section + 1], ('company', '한국지주'))
        self.assertNotIn('holding', [d[0] for d in data])                       # 지주사 따로 단계 없음
        lefts = {self.header(('company', n)).layout().contentsMargins().left() for n in GROUP_NAMES}
        self.assertEqual(len(lefts), 1)                                        # 모두 같은 들여쓰기
        section_left = self.header(('section', '그룹사')).layout().contentsMargins().left()
        self.assertGreater(lefts.pop(), section_left)                          # 그룹사 머리글 밑으로 들여쓰기
        self.assertEqual(self.header(('section', '그룹사')).count.text(), '14곳')
        bot_left = self.header(('company', 'KCS AI')).layout().contentsMargins().left()
        guest_left = self.header(('company', '게스트')).layout().contentsMargins().left()
        self.assertEqual((bot_left, guest_left), (section_left, section_left))  # 지식봇 · 게스트는 그룹사 밖
        self.tab._clicked(self.tab.list.find_data(('section', '그룹사')))       # 접으면 계열사 모두 숨김
        data = rows(self.tab.list)
        self.assertIn(('section', '그룹사'), data)
        self.assertFalse(any(d == ('company', n) for d in data for n in GROUP_NAMES))
        self.tab._clicked(self.tab.list.find_data(('section', '그룹사')))
        self.assertIn(('company', '한국지주'), rows(self.tab.list))
        self.assertIsInstance(self.header(('company', '한국지주')), CompanyHeader)
        self.assertIn('그룹사 14곳', self.tab.header.subtitle.text())

    def test_bot_on_top_and_guest_untouched_at_bottom(self):
        data = rows(self.tab.list)
        self.assertEqual(data[0], ('company', 'KCS AI'))                       # 지식봇이 맨 위
        self.assertLess(data.index(('member', 'AI 비서')), data.index(('section', '그룹사')))
        companies = [d[1] for d in data if d[0] == 'company']
        self.assertEqual(companies[-1], '게스트')                               # 게스트는 그대로 맨 아래
        self.assertIn(('member', '이영희'), data[data.index(('company', '게스트')):])

    def test_bot_right_under_kcs_ai_and_dividers_between_blocks(self):
        self.state.org['groups'] = [{'group_id': 1, 'name': '한국자산관리공사(감사시스템 개발 구축)',
                                     'description': '', 'members': []},
                                    {'group_id': 2, 'name': '경영위원회', 'description': '', 'members': ['김철수']}]
        expand_org(self.tab)
        data = rows(self.tab.list)
        self.assertEqual(data[:2], [('company', 'KCS AI'), ('member', 'AI 비서')])   # 지식봇 단계 없이 바로 아래
        self.assertNotIn(('unit', 'KCS AI', ('지식봇',)), data)
        self.assertNotIn(('section', '그룹'), data)
        # 지식봇 | 그룹사 | 그룹 하나하나 | 게스트 - 덩어리마다 앞에 구분선 (맨 위 제외)
        starts = [('section', '그룹사'), ('org_group', 1), ('org_group', 2), ('company', '게스트')]
        for key in starts:
            self.assertEqual(data[data.index(key) - 1][0], 'divider', key)
        self.assertEqual(sum(1 for d in data if d[0] == 'divider'), len(starts))
        self.assertNotEqual(data[0][0], 'divider')

    def test_search_keeps_bot_first(self):
        self.tab.search_edit.setText('비서')
        self.assertEqual(self.tab.companies(), ['KCS AI'])
        self.tab.search_edit.setText('영업')
        self.assertEqual(self.tab.companies(), ['한네트'])


class OrgGroupClientTests(unittest.TestCase):
    GROUPS = [{'group_id': 1, 'name': '경영위원회', 'description': '그룹 경영 협의', 'members': ['김철수', '박민수']},
              {'group_id': 2, 'name': '빈 그룹', 'description': '', 'members': []}]

    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.state.org = {'holding': {'name': '한국지주'}, 'companies': [{'name': '케이씨에스'}]}
        self.tab = OrgTab(self.state, self.state.settings)

    def make_admin(self, company=''):
        self.conn.push('user_updated', user=dict(self.state.user('홍길동'), is_admin=True, admin_company=company))
        self.tab.refresh()

    def test_button_only_for_group_admin(self):
        self.assertFalse(self.tab.group_button.isVisibleTo(self.tab))
        self.assertIsNone(self.tab.create_group(exec_=False))
        self.make_admin('케이씨에스')                                            # 회사 관리자는 안 됨
        self.assertFalse(self.tab.group_button.isVisibleTo(self.tab))
        self.make_admin()
        self.assertTrue(self.tab.group_button.isVisibleTo(self.tab))
        self.assertEqual(self.tab.group_button.accessibleName(), '그룹 만들기')

    def test_groups_render_after_companies(self):
        self.conn.push('org_groups', groups=self.GROUPS)
        expand_org(self.tab)
        data = rows(self.tab.list)
        self.assertNotIn(('section', '그룹'), data)                              # '그룹' 문구 없음
        self.assertGreater(data.index(('org_group', 1)), data.index(('company', '케이씨에스')))
        idx = data.index(('org_group', 1))
        self.assertEqual(data[idx + 1:idx + 3], [('member', '김철수'), ('member', '박민수')])
        self.assertIn(('empty', ('org_group', 2)), data)
        header = self.tab.list.itemWidget(self.tab.list.find_data(('org_group', 1)))
        self.assertEqual(header.title.text(), '경영위원회')
        self.tab._clicked(self.tab.list.find_data(('org_group', 1)))         # 접기
        data = rows(self.tab.list)
        self.assertNotEqual(data[data.index(('org_group', 1)) + 1], ('member', '김철수'))
        self.tab.search_edit.setText('경영')                                   # 그룹 이름 검색 → 구성원 모두
        self.assertIn(('member', '박민수'), rows(self.tab.list))
        self.tab.search_edit.setText('없는사람')
        self.assertNotIn(('org_group', 1), rows(self.tab.list))

    def test_group_menu_only_for_admin(self):
        self.conn.push('org_groups', groups=self.GROUPS)
        self.assertIsNone(self.tab.context_menu_for(('org_group', 1)))
        self.make_admin()
        menu = self.tab.context_menu_for(('org_group', 1))
        self.assertEqual([a.text() for a in menu.actions()], ['그룹 수정…', '위로 이동', '아래로 이동', '그룹 삭제'])
        self.assertEqual([a.isEnabled() for a in menu.actions()], [True, False, True, True])   # 첫 그룹은 위로 못 감

    def test_create_edit_delete_send_requests(self):
        self.make_admin()
        dlg = self.tab.create_group(exec_=False)
        self.assertIsInstance(dlg, GroupDialog)
        self.assertFalse(dlg.ok_button.isEnabled())                            # 이름이 있어야
        dlg.name_edit.setText(' 양자암호 TF ')
        dlg.desc_edit.setText('계열사 합동')
        dlg.set_checked(['김철수', '이영희'])
        self.assertTrue(dlg.ok_button.isEnabled())
        self.assertEqual(dlg.count_label.text(), '선택한 구성원 2명')
        dlg.search.setText('철수')
        self.assertEqual([dlg.list.item(i).data(Qt.UserRole) for i in range(dlg.list.count())
                          if not dlg.list.item(i).isHidden()], ['김철수'])
        self.state.admin_group_create(dlg.name(), dlg.description(), dlg.members())
        self.assertEqual(self.conn.last('admin_group_create'),
                         {'name': '양자암호 TF', 'description': '계열사 합동', 'members': ['김철수', '이영희']})
        self.conn.push('org_groups', groups=self.GROUPS)
        edit = self.tab.edit_group(1, exec_=False)
        self.assertEqual((edit.name(), sorted(edit.members())), ('경영위원회', ['김철수', '박민수']))
        self.assertEqual(edit.ok_button.text(), '저장')
        self.assertTrue(self.tab.delete_group(1, confirm=False))
        self.assertEqual(self.conn.last('admin_group_delete'), {'group_id': 1})
        self.assertFalse(self.tab.delete_group(99, confirm=False))


class OrgGroupReorderClientTests(unittest.TestCase):
    """그룹 관리자는 그룹 머리글을 끌어서 순서를 바꾼다 (명세 §4.4)"""
    GROUPS = [{'group_id': 1, 'name': 'A 위원회', 'description': '', 'members': ['김철수']},
              {'group_id': 2, 'name': 'B 협의회', 'description': '', 'members': ['박민수', '이영희']},
              {'group_id': 3, 'name': 'C TF', 'description': '', 'members': []}]

    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.state.org = {'holding': {'name': '한국지주'}, 'companies': [{'name': '케이씨에스'}]}
        self.tab = OrgTab(self.state, self.state.settings)
        self.tab.resize(400, 1400)
        self.tab.show()
        self.conn.push('org_groups', groups=[dict(g) for g in self.GROUPS])
        expand_org(self.tab)

    def make_admin(self):
        self.conn.push('user_updated', user=dict(self.state.user('홍길동'), is_admin=True, admin_company=''))
        self.tab.refresh()
        QApplication.processEvents()

    def order(self):
        return [d[1] for d in rows(self.tab.list) if d[0] == 'org_group']

    def header(self, gid):
        return self.tab.list.itemWidget(self.tab.list.find_data(('org_group', gid)))

    def rect(self, key):
        return self.tab.list.visualItemRect(self.tab.list.find_data(key))

    def last_row_bottom(self):
        return self.tab.list.visualItemRect(self.tab.list.item(self.tab.list.count() - 1)).bottom()

    def drag(self, key, target):
        """머리글(key 또는 그룹 id)을 눌러 target(y 또는 '지금 배치에서의 y'를 돌려주는 함수)까지 8px 씩 끌어 놓는다.
        끄는 동안 배치가 바뀌므로 목표는 매 걸음 다시 계산한다. → 끄는 중 본 것 {'ghost', 'slot'}"""
        key = ('org_group', key) if isinstance(key, int) else key
        goal = target if callable(target) else (lambda: target)
        vp = self.tab.list.viewport()
        start = self.rect(key).center()
        x, y = start.x(), start.y()
        send = QApplication.sendEvent
        send(vp, QMouseEvent(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
        seen = {'ghost': False, 'slot': False}
        for _ in range(400):
            to = goal()
            if abs(to - y) <= 1:
                break
            y += max(-8, min(8, to - y))
            send(vp, QMouseEvent(QEvent.MouseMove, QPoint(x, y), Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
            seen['ghost'] |= bool(self.tab.ghost is not None and self.tab.ghost.isVisible())
            seen['slot'] |= any(d[0] == 'slot' for d in rows(self.tab.list))
        send(vp, QMouseEvent(QEvent.MouseButtonRelease, QPoint(x, y), Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
        QApplication.processEvents()
        return seen

    def test_grip_only_for_group_admin(self):
        self.assertFalse(self.header(1).movable)
        self.make_admin()
        self.assertTrue(self.header(1).movable)
        self.assertIsNone(self.header(1).grip)                                 # 점 모양 손잡이는 보이지 않는다
        self.assertIn('끌어서 순서', self.header(1).toolTip())
        self.tab.search_edit.setText('위원회')                                 # 검색 중에는 끌 수 없음
        self.assertFalse(self.header(1).movable)

    def test_drag_last_group_to_top(self):
        self.make_admin()
        seen = self.drag(3, lambda: self.rect(('org_group', 1)).top() + 2)
        self.assertEqual(seen, {'ghost': True, 'slot': True})                 # 떠오른 카드 + 점선 빈칸
        self.assertEqual(self.conn.last('admin_org_order'),
                         {'order': ['group:3', 'group:1', 'group:2', 'company:게스트']})
        self.assertEqual(self.order(), [3, 1, 2])                              # 화면은 바로 바뀐다
        self.assertIsNone(self.tab.ghost)
        self.assertFalse(any(d[0] == 'slot' for d in rows(self.tab.list)))
        self.assertNotIn(3, self.tab.collapsed_groups)                         # 놓기를 접기로 치지 않음
        self.assertFalse(self.tab._skip_click)                                 # 다음 클릭은 그대로 동작
        self.drag(3, self.rect(('org_group', 3)).top() + 3)                    # 제자리에 놓기 → 요청 없음
        self.assertEqual(len([t for t, _p in self.conn.sent if t == 'admin_org_order']), 1)
        self.assertNotIn(3, self.tab.collapsed_groups)

    def test_drag_first_group_below_last(self):
        self.make_admin()
        self.drag(1, lambda: self.last_row_bottom() - 2)                        # 목록 맨 아래까지
        self.assertEqual(self.tab.lower_tokens(), ['group:2', 'group:3', 'company:게스트', 'group:1'])

    def test_drop_onto_header_above_moves_there(self):
        """사용자처럼 위 덩어리 머리글 '위에' 놓아도(머리글 아래쪽 절반) 그 자리로 간다"""
        self.make_admin()
        self.tab.collapsed_groups.update({1, 2, 3})
        self.tab.collapsed.add('게스트')
        self.tab.refresh()
        self.drag(('company', '게스트'), self.rect(('org_group', 3)).center().y() + 6)   # 처음 본 그 자리에
        self.assertEqual(self.tab.lower_tokens(), ['group:1', 'group:2', 'company:게스트', 'group:3'])

    def test_live_preview_and_escape_cancels(self):
        self.make_admin()
        vp = self.tab.list.viewport()
        start = self.rect(('company', '게스트')).center()
        QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton,
                                               Qt.NoModifier))
        y = start.y()
        while y > self.rect(('org_group', 1)).top() + 2:                       # 놓기 전에 순서가 미리 바뀐다
            y -= 8
            QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseMove, QPoint(start.x(), y), Qt.NoButton,
                                                   Qt.LeftButton, Qt.NoModifier))
        lower = [d for d in rows(self.tab.list) if d[0] in ('slot', 'org_group')]
        self.assertEqual(lower[0], ('slot', 'company:게스트'))
        self.assertNotIn(('company', '게스트'), rows(self.tab.list))           # 원래 자리는 비고 카드가 따라온다
        self.assertTrue(self.tab.ghost.isVisible())
        QTest.keyClick(self.tab.list, Qt.Key_Escape)                            # Esc → 취소
        self.assertIsNone(self.tab.ghost)
        self.assertEqual(self.tab.lower_tokens(), ['group:1', 'group:2', 'group:3', 'company:게스트'])
        self.assertIn(('company', '게스트'), rows(self.tab.list))
        QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseButtonRelease, QPoint(start.x(), y), Qt.LeftButton,
                                               Qt.NoButton, Qt.NoModifier))
        self.assertIsNone(self.conn.last('admin_org_order'))

    def test_hover_highlights_draggable_header(self):
        self.make_admin()
        vp = self.tab.list.viewport()
        center = self.rect(('company', '게스트')).center()
        QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseMove, center, Qt.NoButton, Qt.NoButton, Qt.NoModifier))
        guest = self.tab.list.itemWidget(self.tab.list.find_data(('company', '게스트')))
        self.assertTrue(guest.hovered)
        self.assertEqual(vp.cursor().shape(), Qt.OpenHandCursor)
        QApplication.sendEvent(vp, QEvent(QEvent.Leave))
        self.assertFalse(guest.hovered)

    def test_small_move_is_a_click_and_non_admin_cannot_drag(self):
        self.drag(1, self.rect(('org_group', 1)).center().y() + 200)          # 관리자 아님 → 끌기 없음
        self.assertIsNone(self.conn.last('admin_org_order'))
        self.make_admin()
        self.tab.collapsed_groups.clear()
        self.tab.refresh()
        self.drag(2, self.rect(('org_group', 2)).center().y() + 1)
        self.assertIsNone(self.conn.last('admin_org_order'))                   # 조금 움직임 = 클릭(접기)
        self.assertIn(2, self.tab.collapsed_groups)

    def test_menu_move_up_down(self):
        self.make_admin()
        self.assertTrue(self.tab.move_group_by(2, -1))
        self.assertEqual(self.order(), [2, 1, 3])
        self.assertTrue(self.tab.move_group_by(2, 1))
        self.assertEqual(self.order(), [1, 2, 3])
        self.assertTrue(self.tab.move_group_by(3, 1))                          # 게스트 아래로도 갈 수 있다
        self.assertEqual(self.tab.lower_tokens(), ['group:1', 'group:2', 'company:게스트', 'group:3'])
        self.assertFalse(self.tab.move_group_by(3, 1))                         # 이미 맨 아래
        self.conn.push('org_groups', groups=[dict(g) for g in self.GROUPS],   # 서버 확정 순서가 이긴다
                       order=['company:게스트', 'group:3', 'group:2', 'group:1'])
        self.assertEqual(self.tab.lower_tokens(), ['company:게스트', 'group:3', 'group:2', 'group:1'])

    def test_kcs_ai_and_group_companies_are_fixed(self):
        self.conn.push('user_updated', user={'username': 'AI 비서', 'display_name': 'AI 비서', 'company': 'KCS AI',
                                             'department': '지식봇', 'title': '봇', 'is_bot': True,
                                             'online': True, 'presence': 'online', 'status_message': ''})
        self.state.my_friends = list(self.state.users)
        self.make_admin()
        data = rows(self.tab.list)
        self.assertEqual(data[0], ('company', 'KCS AI'))
        for key in (('company', 'KCS AI'), ('section', '그룹사'), ('company', '한국지주')):
            self.assertFalse(self.tab.can_move(self.tab.token_of(key)), key)
            widget = self.tab.list.itemWidget(self.tab.list.find_data(key))
            self.assertFalse(getattr(widget, 'movable', False), key)              # 끌 수 없음
        self.assertIsNone(self.tab.context_menu_for(('company', '한국지주')))
        self.assertFalse(self.tab.move_block('company:KCS AI', 0))
        # 게스트를 맨 위로 끌어도 KCS AI · 그룹사 아래(아래쪽 첫 자리)까지만
        guest = self.tab.list.itemWidget(self.tab.list.find_data(('company', '게스트')))
        self.assertTrue(guest.movable)
        self.drag(('company', '게스트'), 2)
        self.assertEqual(self.tab.lower_tokens()[0], 'company:게스트')
        data = rows(self.tab.list)
        self.assertEqual(data[0], ('company', 'KCS AI'))
        self.assertLess(data.index(('section', '그룹사')), data.index(('company', '게스트')))
        menu = self.tab.context_menu_for(('company', '게스트'))
        self.assertEqual([a.text() for a in menu.actions()], ['위로 이동', '아래로 이동'])

    def test_non_admin_never_reorders(self):
        for admin_company in (None, '케이씨에스'):                                # 일반 사용자 · 회사 관리자
            if admin_company:
                self.conn.push('user_updated', user=dict(self.state.user('홍길동'), is_admin=True,
                                                         admin_company=admin_company))
                self.tab.refresh()
            for token in self.tab.lower_tokens():
                self.assertFalse(self.tab.can_move(token))
                self.assertFalse(self.tab.move_block(token, 0))
            self.assertIsNone(self.tab.context_menu_for(('company', '게스트')))
            self.assertIsNone(self.tab.context_menu_for(('org_group', 1)))
            self.assertFalse(self.header(1).movable)
            self.drag(3, 0)
        self.assertIsNone(self.conn.last('admin_org_order'))


class OrgCardDesignTests(unittest.TestCase):
    """카드 디자인: 덩어리마다 카드, 머리글 글자 줄 = 구성원 사진 줄, 손잡이가 있어도 아이콘 줄 그대로"""

    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.state.org = {'holding': {'name': '한국지주'}, 'companies': [{'name': '케이씨에스'}]}
        self.conn.push('user_updated', user=dict(self.state.user('홍길동'), is_admin=True, admin_company=''))
        self.tab = OrgTab(self.state, self.state.settings)
        self.tab.resize(400, 1200)
        self.tab.show()
        self.conn.push('org_groups', groups=[{'group_id': 1, 'name': '경영위원회', 'description': '',
                                              'members': ['김철수']}])
        QApplication.processEvents()

    def widget(self, key):
        return self.tab.list.itemWidget(self.tab.list.find_data(key))

    def x_in_list(self, w):
        return w.mapTo(self.tab.list.viewport(), QPoint(0, 0)).x()

    def test_member_photo_starts_at_header_title(self):
        guest = self.widget(('company', '게스트'))
        title_x = self.x_in_list(guest.title)
        for name in ('박민수', '최지우'):                                       # 게스트 구성원
            row = self.widget(('member', name))
            self.assertEqual(self.x_in_list(row.avatar), title_x, name)
        group = self.widget(('org_group', 1))
        self.assertEqual(self.x_in_list(self.widget(('member', '김철수')).avatar), self.x_in_list(group.title))

    def test_icon_column_same_with_or_without_grip(self):
        guest, group, section = (self.widget(('company', '게스트')), self.widget(('org_group', 1)),
                                 self.widget(('section', '그룹사')))
        self.assertTrue(guest.movable)
        self.assertEqual(self.x_in_list(guest.title), self.x_in_list(group.title))
        self.assertEqual(guest.layout().contentsMargins().left(), section.layout().contentsMargins().left())
        # 점 모양 손잡이 없음: 머리글 왼쪽 여백(카드 안)에 그려진 것이 없다
        img = guest.grab().toImage()
        left = guest.layout().contentsMargins().left()
        ys = range(4, img.height() - 4)
        self.assertTrue(all(QColor(img.pixel(x, y)).alpha() == 0 or QColor(img.pixel(x, y)).lightness() > 235
                            for x in range(CARD_INSET + 1, left - 1) for y in ys))

    def test_cards_and_gaps(self):
        blocks = [[it.data(Qt.UserRole) for it in b] for b in self.tab.list.blocks()]
        self.assertEqual([b[0] for b in blocks], [('section', '그룹사'), ('org_group', 1), ('company', '게스트')])
        gap = self.tab.list.find_data(next(d for d in rows(self.tab.list) if d[0] == 'divider'))
        self.assertEqual(self.tab.list.visualItemRect(gap).height(), 10)          # 카드 사이 간격

    def test_ghost_card_is_light_not_black(self):
        vp = self.tab.list.viewport()
        start = self.tab.list.visualItemRect(self.tab.list.find_data(('company', '게스트'))).center()
        QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton,
                                               Qt.NoModifier))
        QApplication.sendEvent(vp, QMouseEvent(QEvent.MouseMove, QPoint(start.x(), start.y() - 30), Qt.NoButton,
                                               Qt.LeftButton, Qt.NoModifier))
        ghost = self.tab.ghost
        self.assertIsNotNone(ghost)
        img = ghost.pixmap().toImage()
        center = QColor(img.pixel(img.width() // 2, img.height() // 2))
        self.assertGreater(center.lightness(), 200)                               # 흰 카드 (검게 채워지지 않음)
        slot = self.tab.list.find_data(('slot', 'company:게스트'))
        self.assertEqual(self.tab.list.visualItemRect(slot).height(), self.tab.list.itemWidget(slot).height())
        QTest.keyClick(self.tab.list, Qt.Key_Escape)


class OrgGroupServerTests(ServerTestBase):
    def member(self, admin=False, company=''):
        name = uname('grp')
        store = self.server.store
        store.register_user(name, 'KCS 홀딩스', f'{name}@kcs.test', 'pw-1234', employee_no=f'E{name}'[:20])
        if admin:
            store.set_admin(name, True, company)
        c = Client(self.port, name, join=False)
        self.clients.append(c)
        c.request({'type': 'join', 'username': name, 'password': 'pw-1234'}, 'welcome')
        return c, name

    def test_group_admin_crud_and_broadcast(self):
        admin, admin_name = self.member(admin=True)
        other, other_name = self.member()
        done = admin.request({'type': 'admin_group_create', 'name': ' 경영위원회 ', 'description': '협의',
                              'members': [other_name, admin_name, other_name]}, 'admin_done')
        self.assertEqual((done['action'], done['name']), ('group_create', '경영위원회'))
        pushed = other.wait_for('org_groups')['groups']
        self.assertEqual([(g['name'], g['members']) for g in pushed], [('경영위원회', [other_name, admin_name])])
        gid = pushed[0]['group_id']
        late = Client(self.port, uname('late'))
        self.clients.append(late)
        self.assertEqual([g['name'] for g in late.welcome['org']['groups']], ['경영위원회'])   # welcome 에도
        admin.request({'type': 'admin_group_update', 'group_id': gid, 'name': '경영협의회', 'members': [other_name]},
                      'admin_done')
        self.assertEqual(self.server.store.org_group(gid)['members'], [other_name])
        self.assertEqual(self.server.store.org_group(gid)['description'], '')
        self.server.store.member_set_removed(other_name, True)                  # 삭제된 구성원은 빠진다
        self.assertEqual(self.server.store.org_group(gid)['members'], [])
        admin.request({'type': 'admin_group_delete', 'group_id': gid}, 'admin_done')
        self.assertEqual(self.server.store.org_groups(), [])

    def test_refused_and_validated(self):
        admin, _ = self.member(admin=True)
        plain, _ = self.member()
        company_admin, _ = self.member(admin=True, company='KCS 홀딩스')
        payload = {'type': 'admin_group_create', 'name': 'TF'}
        self.assertEqual(plain.expect_error(payload)['message'], '관리자만 사용할 수 있습니다.')
        self.assertEqual(company_admin.expect_error(payload)['message'], '그룹 관리자만 할 수 있습니다.')
        admin.request(payload, 'admin_done')
        self.assertEqual(admin.expect_error(payload)['message'], '이미 있는 그룹 이름입니다.')
        self.assertIn('구성원을 찾을 수 없습니다',
                      admin.expect_error({**payload, 'name': 'TF2', 'members': ['없는사람']})['message'])
        admin.expect_error({**payload, 'name': '   '})
        admin.expect_error({**payload, 'name': 'TF3', 'members': 'x'})
        self.assertEqual(admin.expect_error({'type': 'admin_group_delete', 'group_id': 999})['message'],
                         '그룹을 찾을 수 없습니다.')


    def test_reorder_saved_and_broadcast(self):
        admin, _ = self.member(admin=True)
        other, _ = self.member()
        before = [g['group_id'] for g in self.server.store.org_groups()]    # 같은 서버를 쓰는 다른 테스트의 그룹
        ids = [admin.request({'type': 'admin_group_create', 'name': n}, 'admin_done')['group_id']
               for n in ('가', '나', '다')]
        self.assertEqual([g['group_id'] for g in self.server.store.org_groups()], before + ids)   # 만든 순서, 맨 뒤
        want = [ids[2]] + before + [ids[0], ids[1]]
        done = admin.request({'type': 'admin_group_reorder', 'group_ids': want}, 'admin_done')
        self.assertEqual(done['action'], 'group_reorder')
        for _ in range(4):                                       # 앞서 만든 그룹들의 org_groups 푸시를 건너뛴다
            got = [g['group_id'] for g in other.wait_for('org_groups')['groups']]
            if got == want:
                break
        self.assertEqual(got, want)
        self.assertEqual([g['group_id'] for g in self.server.store.org_groups()], want)
        new = admin.request({'type': 'admin_group_create', 'name': '라'}, 'admin_done')['group_id']
        self.assertEqual(self.server.store.org_groups()[-1]['group_id'], new)   # 새 그룹은 맨 뒤

    def test_reorder_refused_and_validated(self):
        admin, _ = self.member(admin=True)
        plain, _ = self.member()
        company_admin, _ = self.member(admin=True, company='KCS 홀딩스')
        for n in 'XY':
            admin.request({'type': 'admin_group_create', 'name': n}, 'admin_done')
        ids = [g['group_id'] for g in self.server.store.org_groups()]
        payload = {'type': 'admin_group_reorder', 'group_ids': ids[::-1]}
        self.assertEqual(plain.expect_error(payload)['message'], '관리자만 사용할 수 있습니다.')
        self.assertEqual(company_admin.expect_error(payload)['message'], '그룹 관리자만 할 수 있습니다.')
        stale = '그룹 목록이 바뀌었습니다. 조직도를 새로 보고 다시 시도해 주세요.'
        for bad in (ids[:-1], ids + [999], ids[:-1] + [ids[0]]):
            self.assertEqual(admin.expect_error({**payload, 'group_ids': bad})['message'], stale)
        admin.expect_error({**payload, 'group_ids': 'x'})
        admin.expect_error({**payload, 'group_ids': [True, False]})
        self.assertEqual([g['group_id'] for g in self.server.store.org_groups()], ids)   # 그대로

    def test_org_order_only_group_admin_and_saved(self):
        admin, _ = self.member(admin=True)
        plain, _ = self.member()
        company_admin, _ = self.member(admin=True, company='KCS 홀딩스')
        gid = admin.request({'type': 'admin_group_create', 'name': '순서TF'}, 'admin_done')['group_id']
        order = ['company:게스트', f'group:{gid}']
        payload = {'type': 'admin_org_order', 'order': order}
        self.assertEqual(plain.expect_error(payload)['message'], '관리자만 사용할 수 있습니다.')
        self.assertEqual(company_admin.expect_error(payload)['message'], '그룹 관리자만 할 수 있습니다.')
        before = self.server.store.org_order()
        for bad in ('x', ['group:abc'], ['company: '], ['bad'], [1], ['company:게스트', 'company:게스트']):
            admin.expect_error({**payload, 'order': bad})
        self.assertIn('그룹 목록이 바뀌었습니다',
                      admin.expect_error({**payload, 'order': ['group:99999']})['message'])
        self.assertEqual(self.server.store.org_order(), before)                    # 거부되면 그대로
        done = admin.request(payload, 'admin_done')
        self.assertEqual(done['action'], 'org_order')
        for _ in range(6):
            pushed = plain.wait_for('org_groups')
            if pushed.get('order') == order:
                break
        self.assertEqual(pushed['order'], order)                                    # 모두에게
        self.assertEqual(self.server.store.org_order(), order)
        late = Client(self.port, uname('late'))
        self.clients.append(late)
        self.assertEqual(late.welcome['org']['order'], order)                      # 새로 접속해도 같은 순서


class OrgGroupMigrationTests(unittest.TestCase):
    def test_old_db_gets_sort_order_in_creation_order(self):
        import shutil
        import sqlite3
        import tempfile
        from server.kakao.store import Store
        folder = tempfile.mkdtemp(prefix='kcs_grp_')
        self.addCleanup(shutil.rmtree, folder, True)
        db = os.path.join(folder, 'kakao.db')
        con = sqlite3.connect(db)                                 # 순서 칸이 없던 예전 표
        con.execute("CREATE TABLE org_groups (group_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,"
                    " description TEXT NOT NULL DEFAULT '', members TEXT NOT NULL DEFAULT '[]',"
                    " created_by TEXT NOT NULL, created_at TEXT NOT NULL)")
        for n in ('첫째', '둘째'):
            con.execute("INSERT INTO org_groups(name, created_by, created_at) VALUES (?, 'x', 'now')", (n,))
        con.commit()
        con.close()
        store = Store(db)
        try:
            self.assertEqual([g['name'] for g in store.org_groups()], ['첫째', '둘째'])
            store.org_group_reorder([2, 1])
            self.assertEqual([g['name'] for g in store.org_groups()], ['둘째', '첫째'])
        finally:
            store.close()


if __name__ == '__main__':
    unittest.main()
