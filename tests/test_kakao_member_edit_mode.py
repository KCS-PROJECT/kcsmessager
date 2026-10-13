# -*- coding: utf-8 -*-
"""관리자 편집 모드 (명세 §4.3): KCS관리자(kcs_administrator) 같은 관리자가 조직도 · 친구 · 프로필에서
우클릭 또는 조직도 편집 모드로 구성원 정보를 바로 고친다. 부서 · 팀은 org_path [부서, 팀]"""

import unittest
from unittest import mock

from PyQt5.QtWidgets import QApplication, QMessageBox

from tests.kakao_fakes import app, make_demo_state, expand_org
from tests.test_kakao_server import ServerTestBase, Client, uname

from client.kakao.admin import (MemberDialog, EDIT_ACTION_TEXT, can_edit_member, edit_member_info,
                                submit_member_edit)
from client.kakao.org_tab import OrgTab
from client.kakao.friends_tab import ProfileDialog


def actions(menu):
    return [a.text() for a in menu.actions() if a.text()] if menu else []


ADMIN_USERS = [
    {'username': '김철수', 'company': '케이씨에스', 'department': '기술연구소1실', 'team': '2팀(SI)', 'title': '대리',
     'account': 'kim', 'employee_no': 'E2', 'email': 'kim@kcs.test', 'extension': '5100', 'mobile': '',
     'registered': True, 'disabled': False, 'is_admin': False, 'admin_company': '', 'removed': False,
     'online': False}]


class EditModeClientTests(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()              # 나 = 홍길동
        self.state.org = {'holding': {'name': '한국지주'}, 'companies': [{'name': '케이씨에스'}, {'name': '한네트'}]}
        for name, company, path in (('홍길동', '케이씨에스', []), ('김철수', '케이씨에스', ['기술연구소1실', '2팀(SI)']),
                                    ('이영희', '한네트', ['영업팀'])):
            self.conn.push('user_updated', user=dict(self.state.user(name), company=company, org_path=path,
                                                    department=path[0] if path else ''))
        self.tab = OrgTab(self.state, self.state.settings)

    def make_admin(self, company=''):
        """KCS관리자(사내 계정 kcs_administrator)처럼 관리자로 로그인한 상태"""
        self.conn.push('user_updated', user=dict(self.state.user('홍길동'), is_admin=True, admin_company=company,
                                                 account='kcs_administrator'))

    def test_edit_button_and_menu_only_for_admin(self):
        self.assertFalse(self.tab.edit_button.isVisibleTo(self.tab))
        self.assertNotIn(EDIT_ACTION_TEXT, actions(self.tab.context_menu_for(('member', '김철수'))))
        self.assertIsNone(self.tab.edit_member('김철수', exec_=False))
        self.tab.set_edit_mode(True)                                         # 관리자가 아니면 켜지지 않는다
        self.assertFalse(self.tab.edit_mode)
        self.make_admin()
        self.assertTrue(self.tab.edit_button.isVisibleTo(self.tab))
        self.assertEqual(self.tab.edit_button.accessibleName(), '편집 모드')
        self.assertIn(EDIT_ACTION_TEXT, actions(self.tab.context_menu_for(('member', '김철수'))))

    def test_toggle_edit_mode_and_click_opens_member_form(self):
        self.make_admin()
        expand_org(self.tab)
        self.tab.edit_button.click()
        self.assertTrue(self.tab.edit_mode)
        self.assertTrue(self.tab.edit_bar.isVisibleTo(self.tab))
        self.assertIsNotNone(self.conn.last('admin_users'))                  # 사번 · 이메일 · 팀을 받으러
        self.assertIn('편집 모드 끝내기', actions(self.tab.context_menu_for(('member', '김철수'))))
        item = self.tab.list.find_data(('member', '김철수'))
        with mock.patch.object(self.tab, 'edit_member') as edit, \
                mock.patch.object(self.state, 'open_direct') as chat:
            self.tab.list.itemClicked.emit(item)
            self.tab.list.itemDoubleClicked.emit(item)
        self.assertEqual(edit.call_count, 2)                                 # 누르거나 두 번 눌러도 수정 창
        chat.assert_not_called()                                             # 편집 모드에서는 채팅을 열지 않는다
        self.tab.edit_done_button.click()
        self.assertFalse(self.tab.edit_mode)
        self.assertFalse(self.tab.edit_bar.isVisibleTo(self.tab))
        with mock.patch.object(self.state, 'open_direct') as chat:
            self.tab.list.itemDoubleClicked.emit(self.tab.list.find_data(('member', '김철수')))
        chat.assert_called_once_with('김철수')

    def test_right_click_starts_edit_mode_and_sends_only_changes(self):
        self.make_admin()
        menu = self.tab.context_menu_for(('member', '김철수'))
        action = next(a for a in menu.actions() if a.text() == EDIT_ACTION_TEXT)
        with mock.patch.object(MemberDialog, 'exec_', return_value=MemberDialog.Rejected) as shown:
            action.trigger()
        self.assertTrue(self.tab.edit_mode)                                  # 우클릭 → 편집 모드
        shown.assert_called_once()
        self.assertIsNone(self.conn.last('admin_member_update'))             # 취소하면 보내지 않음
        dlg = self.tab.edit_member('김철수', exec_=False)
        self.assertEqual(dlg.windowTitle(), '편집 모드 · 김철수')
        self.assertTrue(dlg.name_edit.isReadOnly())
        self.assertEqual((dlg.edits['department'].text(), dlg.edits['team'].text()), ('기술연구소1실', '2팀(SI)'))
        self.conn.push('admin_users', users=ADMIN_USERS, scope='')           # 늦게 온 사번 · 이메일을 채운다
        self.assertEqual((dlg.edits['employee_no'].text(), dlg.edits['email'].text()), ('E2', 'kim@kcs.test'))
        dlg.edits['title'].setText('과장')
        self.assertTrue(submit_member_edit(self.state, '김철수', dlg, self.tab))
        self.assertEqual(self.conn.last('admin_member_update'), {'username': '김철수', 'title': '과장'})
        dlg.edits['team'].setText('1팀(보안)')                                 # 팀만 바꿔도 부서와 함께
        self.assertEqual(dlg.changes(), {'title': '과장', 'department': '기술연구소1실', 'team': '1팀(보안)'})

    def test_fill_keeps_what_admin_already_typed(self):
        self.make_admin()
        dlg = self.tab.edit_member('김철수', exec_=False)
        dlg.edits['email'].setText('typed@kcs.test')
        self.conn.push('admin_users', users=ADMIN_USERS, scope='')
        self.assertEqual(dlg.edits['email'].text(), 'typed@kcs.test')
        self.assertEqual(dlg.changes(), {'email': 'typed@kcs.test'})

    def test_company_admin_edits_only_own_company(self):
        self.make_admin('케이씨에스')
        self.assertTrue(can_edit_member(self.state, '김철수'))
        self.assertFalse(can_edit_member(self.state, '이영희'))              # 한네트 - 관리 범위 밖
        self.assertNotIn(EDIT_ACTION_TEXT, actions(self.tab.context_menu_for(('member', '이영희'))))
        self.assertIsNone(edit_member_info(self.state, '이영희', exec_=False))
        self.assertFalse(can_edit_member(self.state, 'AI 비서'))             # 봇은 고치지 않는다

    def test_server_error_is_shown(self):
        self.make_admin()
        dlg = self.tab.edit_member('김철수', exec_=False)
        dlg.edits['employee_no'].setText('E9')
        submit_member_edit(self.state, '김철수', dlg, self.tab)
        self.conn.push('error', message='이미 다른 구성원이 쓰는 사번입니다.', req_type='admin_member_update')
        boxes = [w for w in QApplication.topLevelWidgets() if isinstance(w, QMessageBox) and w.isVisible()]
        self.assertTrue(any(b.text() == '이미 다른 구성원이 쓰는 사번입니다.' for b in boxes))
        for b in boxes:
            b.close()

    def test_profile_right_click_opens_edit_mode(self):
        profile = ProfileDialog(self.state, '김철수')
        self.addCleanup(profile.close)
        self.assertIsNone(profile.context_menu())                            # 관리자가 아니면 메뉴 없음
        self.make_admin()
        profile = ProfileDialog(self.state, '김철수')
        self.addCleanup(profile.close)
        self.assertEqual(actions(profile.context_menu()), [EDIT_ACTION_TEXT])
        dlg = profile.start_edit(exec_=False)
        self.assertIsInstance(dlg, MemberDialog)
        with mock.patch.object(MemberDialog, 'exec_', return_value=MemberDialog.Accepted), \
                mock.patch.object(MemberDialog, 'changes', return_value={'mobile': '010-1234-5678'}), \
                mock.patch.object(profile, 'accept') as closed:
            profile.start_edit()
        self.assertEqual(self.conn.last('admin_member_update'), {'username': '김철수', 'mobile': '010-1234-5678'})
        closed.assert_called_once()                                          # 저장하면 프로필을 닫는다

    def test_friends_tab_right_click_has_edit(self):
        from client.kakao.friends_tab import FriendsTab
        tab = FriendsTab(self.state, self.state.settings)
        self.assertNotIn(EDIT_ACTION_TEXT, actions(tab.context_menu_for(('friend', '김철수'))))
        self.make_admin()
        self.assertIn(EDIT_ACTION_TEXT, actions(tab.context_menu_for(('friend', '김철수'))))
        self.assertIn(EDIT_ACTION_TEXT, actions(tab.context_menu_for(('me', '홍길동'))))


class EditModeServerTests(ServerTestBase):
    def test_team_sets_org_path_and_is_listed(self):
        store = self.server.store
        admin = uname('adm')
        store.register_user(admin, 'KCS 홀딩스', f'{admin}@kcs.test', 'pw-1234', employee_no=f'A{admin}'[:20])
        store.set_admin(admin, True, '')
        target = uname('tgt')
        store.register_user(target, 'KCS 홀딩스', f'{target}@kcs.test', 'pw-1234', employee_no=f'T{target}'[:20])
        c = Client(self.port, admin, join=False)
        self.clients.append(c)
        c.request({'type': 'join', 'username': admin, 'password': 'pw-1234'}, 'welcome')
        c.request({'type': 'admin_member_update', 'username': target, 'department': '기술연구소1실',
                   'team': '2팀(SI)'}, 'admin_done')
        self.assertEqual(store.get_user(target)['org_path'], ['기술연구소1실', '2팀(SI)'])
        listed = {u['username']: u for u in c.request({'type': 'admin_users'}, 'admin_users')['users']}
        self.assertEqual(listed[target]['team'], '2팀(SI)')
        c.request({'type': 'admin_member_update', 'username': target, 'team': '1팀(보안)'}, 'admin_done')
        self.assertEqual(store.get_user(target)['org_path'], ['기술연구소1실', '1팀(보안)'])   # 부서는 그대로
        c.request({'type': 'admin_member_update', 'username': target, 'title': '수석'}, 'admin_done')
        self.assertEqual(store.get_user(target)['org_path'], ['기술연구소1실', '1팀(보안)'])   # 다른 필드는 경로 유지
        c.request({'type': 'admin_member_update', 'username': target, 'department': '관리팀'}, 'admin_done')
        self.assertEqual(store.get_user(target)['org_path'], ['관리팀'])                      # team 없이 = 예전대로
        err = c.expect_error({'type': 'admin_member_update', 'username': target, 'team': 'x' * 61})
        self.assertIn('team', err['message'])


if __name__ == '__main__':
    unittest.main()
