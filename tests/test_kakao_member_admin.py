# -*- coding: utf-8 -*-
"""그룹사 관리자 · 구성원 관리 (명세 §4.3): 그룹/회사 관리자 범위 + 구성원 등록 · 조회 · 수정 · 삭제 · 복원"""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tests.kakao_fakes import app, make_demo_state
from tests.test_kakao_server import ServerTestBase, Client, uname


class MemberAdminServerTests(ServerTestBase):
    def member(self, company='KCS 홀딩스', admin=None, password='pw-1234'):
        """비밀번호를 등록하고 로그인한 사람 → (client, username). admin='' 그룹 관리자, '회사' 회사 관리자"""
        name = uname('mem')
        store = self.server.store
        store.register_user(name, company, f'{name}@kcs.test', password, employee_no=f'E{name}'[:20])
        if admin is not None:
            store.set_admin(name, True, admin)
        c = Client(self.port, name, join=False)
        self.clients.append(c)
        c.request({'type': 'join', 'username': name, 'password': password}, 'welcome')
        return c, name

    def create(self, admin, company='KCS 물류', **fields):
        name = fields.pop('username', None) or uname('new')
        payload = {'type': 'admin_member_create', 'username': name, 'company': company, **fields}
        return name, payload

    def test_group_admin_creates_member_who_then_registers(self):
        admin, _ = self.member(admin='')
        watcher, _w = self.member()
        name, payload = self.create(admin, department='물류팀', title='대리', employee_no='L2026001',
                                    account='newbie', extension='5300', mobile='010-1111-2222', email='newbie@kcs.test')
        done = admin.request(payload, 'admin_done')
        self.assertEqual((done['action'], done['username']), ('member_create', name))
        got = watcher.wait_for('user_updated', lambda m: m['user']['username'] == name)['user']
        self.assertEqual((got['company'], got['department'], got['title'], got['org_path'], got['employee_no']),
                         ('KCS 물류', '물류팀', '대리', ['물류팀'], 'L2026001'))
        listed = {u['username']: u for u in admin.request({'type': 'admin_users'}, 'admin_users')['users']}
        self.assertFalse(listed[name]['registered'])                             # 비밀번호는 아직 없다
        self.assertEqual(admin.expect_error(payload)['message'], '이미 있는 이름입니다.')
        # 등록된 사람은 [처음 사용 등록]으로 비밀번호를 정하고 사번으로 로그인한다
        c = Client(self.port, name, join=False)
        self.clients.append(c)
        c.request({'type': 'register', 'company': 'KCS 물류', 'name': name, 'employee_no': 'L2026001',
                   'email': 'newbie@kcs.test', 'password': 'first-pw'}, 'welcome')
        again = Client(self.port, 'L2026001', join=False)
        self.clients.append(again)
        me = again.request({'type': 'join', 'username': 'l2026001', 'password': 'first-pw'}, 'welcome')['me']
        self.assertEqual((me['username'], me['department']), (name, '물류팀'))

    def test_create_validation_and_conflicts(self):
        admin, other = self.member(admin='')
        base_name = uname('dup')
        admin.request(self.create(admin, username=base_name, employee_no='DUP001', account='dupacct',
                                  email='dup@kcs.test')[1], 'admin_done')
        for change, message in (({'company': '없는회사'}, '소속 회사를 선택해 주세요.'),
                                ({'employee_no': 'dup001'}, '이미 다른 구성원이 쓰는 사번입니다.'),
                                ({'employee_no': other}, '이미 다른 구성원이 쓰는 사번입니다.'),   # 남의 이름과 같은 사번
                                ({'account': 'DUPACCT'}, '이미 다른 구성원이 쓰는 사내 계정입니다.'),
                                ({'email': 'DUP@kcs.test'}, '이미 다른 구성원이 쓰는 이메일입니다.'),
                                ({'email': 'not-mail'}, '이메일 주소 형식이 올바르지 않습니다.'),
                                ({'employee_no': '12 34'}, '사번은 영문·숫자'),
                                ({'department': 'x' * 61}, 'department'),
                                ({'username': 'a@b'}, '사용할 수 없는 문자'),
                                ({'username': 'x' * 21}, '20자')):
            name, payload = self.create(admin, **change)
            err = admin.expect_error(payload)
            self.assertIn(message, err['message'])
            self.assertFalse(self.server.store.user_exists(name))

    def test_update_member_keeps_name_and_checks_conflicts(self):
        admin, _ = self.member(admin='')
        target_conn, target = self.member()
        done = admin.request({'type': 'admin_member_update', 'username': target, 'department': '경영지원팀',
                              'title': '과장', 'mobile': '010-9999-0000'}, 'admin_done')
        self.assertEqual(done['action'], 'member_update')
        me = target_conn.wait_for('user_updated', lambda m: m['user']['username'] == target
                                  and m['user']['department'] == '경영지원팀')['user']
        self.assertEqual((me['title'], me['org_path'], me['mobile']), ('과장', ['경영지원팀'], '010-9999-0000'))
        self.assertEqual(me['email'], f'{target}@kcs.test')                       # 보내지 않은 필드는 그대로
        _o, other = self.member()
        err = admin.expect_error({'type': 'admin_member_update', 'username': target,
                                  'employee_no': f'E{other}'[:20]})
        self.assertEqual(err['message'], '이미 다른 구성원이 쓰는 사번입니다.')
        admin.request({'type': 'admin_member_update', 'username': target, 'department': ''}, 'admin_done')
        self.assertEqual(self.server.store.get_user(target)['org_path'], [])       # 부서를 비우면 회사 바로 아래

    def test_delete_and_restore(self):
        admin, admin_name = self.member(admin='')
        target_conn, target = self.member(password='tgt-pass')
        watcher, _w = self.member()
        done = admin.request({'type': 'admin_member_delete', 'username': target}, 'admin_done')
        self.assertEqual(done['action'], 'member_delete')
        target_conn.wait_for('account_disabled')
        self.assertEqual(watcher.wait_for('user_removed')['username'], target)
        store = self.server.store
        self.assertNotIn(target, [u['username'] for u in store.list_users()])     # 조직도·친구 목록에서 빠짐
        self.assertIn(target, [u['username'] for u in store.admin_user_list()])        # 관리자 목록에는 남는다
        late = Client(self.port, uname('late'))
        self.clients.append(late)
        self.assertNotIn(target, [u['username'] for u in late.welcome['users']])
        again = Client(self.port, target, join=False)
        self.clients.append(again)
        self.assertIn('중지', again.expect_error({'type': 'join', 'username': target, 'password': 'tgt-pass'})['message'])
        self.assertEqual(admin.expect_error({'type': 'admin_member_delete', 'username': admin_name})['message'],
                         '자기 계정은 삭제할 수 없습니다.')
        removed = {u['username']: u for u in admin.request({'type': 'admin_users'}, 'admin_users')['users']}[target]
        self.assertTrue(removed['removed'])
        admin.request({'type': 'admin_member_restore', 'username': target}, 'admin_done')
        watcher.wait_for('user_updated', lambda m: m['user']['username'] == target)
        again.request({'type': 'join', 'username': target, 'password': 'tgt-pass'}, 'welcome')

    def test_company_admin_scope(self):
        company_admin, ca_name = self.member(company='KCS 물류', admin='KCS 물류')
        _m, mine = self.member(company='KCS 물류')
        _o, outsider = self.member(company='KCS 커머스')
        users = company_admin.request({'type': 'admin_users'}, 'admin_users')
        self.assertEqual(users['scope'], 'KCS 물류')
        self.assertEqual({u['company'] for u in users['users']}, {'KCS 물류'})        # 자기 회사만 조회
        self.assertIn(mine, [u['username'] for u in users['users']])
        company_admin.request({'type': 'admin_member_update', 'username': mine, 'title': '주임'}, 'admin_done')
        scope_error = '관리 범위(KCS 물류) 밖의 구성원입니다.'
        for payload in ({'type': 'admin_member_update', 'username': outsider, 'title': 'x'},
                        {'type': 'admin_member_delete', 'username': outsider},
                        {'type': 'admin_reset_password', 'username': outsider, 'new_password': 'abcd'},
                        {'type': 'admin_set_disabled', 'username': outsider, 'disabled': True},
                        {'type': 'admin_member_update', 'username': mine, 'company': 'KCS 커머스'},
                        {'type': 'admin_member_create', 'username': uname('x'), 'company': 'KCS 커머스'}):
            self.assertEqual(company_admin.expect_error(payload)['message'], scope_error)
        for payload in ({'type': 'admin_notice', 'content': '공지'},
                        {'type': 'admin_set_admin', 'username': mine, 'is_admin': True}):
            self.assertEqual(company_admin.expect_error(payload)['message'], '그룹 관리자만 할 수 있습니다.')
        name = uname('logi')
        company_admin.request({'type': 'admin_member_create', 'username': name, 'company': 'KCS 물류'}, 'admin_done')
        self.assertEqual(self.server.store.user_company(name), 'KCS 물류')
        self.assertEqual(self.server.store.get_user(ca_name)['admin_company'], 'KCS 물류')

    def test_group_admin_assigns_company_admin_and_last_group_admin_guard(self):
        store = self.server.store
        with store._lock:
            store._db.execute('UPDATE users SET is_admin=0, admin_company=\'\'')
            store._db.commit()
        group, group_name = self.member(admin='')
        _t, target = self.member(company='KCS 커머스')
        done = group.request({'type': 'admin_set_admin', 'username': target, 'is_admin': True,
                              'company': 'KCS 커머스'}, 'admin_done')
        self.assertEqual(done['company'], 'KCS 커머스')
        self.assertEqual(store.admin_scope(target), 'KCS 커머스')
        self.assertIn('소속 회사', group.expect_error({'type': 'admin_set_admin', 'username': target, 'is_admin': True,
                                                       'company': '없는회사'})['message'])
        # 회사 관리자가 있어도 그룹 관리자는 한 명 남아야 한다 (자기를 회사 관리자로 내리는 것도 막는다)
        for payload in ({'is_admin': False}, {'is_admin': True, 'company': 'KCS 홀딩스'}):
            err = group.expect_error({'type': 'admin_set_admin', 'username': group_name, **payload})
            self.assertEqual(err['message'], '관리자가 한 명은 있어야 합니다.')


class MemberPersistenceTests(unittest.TestCase):
    """서버를 다시 켜도 관리자가 고친 · 삭제한 구성원은 org.json 시드가 되돌리지 않는다"""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='kcs_member_')
        self.addCleanup(shutil.rmtree, self.dir, True)
        with open(os.path.join(self.dir, 'org.json'), 'w', encoding='utf-8') as f:
            json.dump({'version': 2, 'holding': {'name': '한국지주'}, 'companies': [{'name': '케이씨에스'}],
                       'include_demo_users': False, 'admins': ['KCS관리자'],
                       'users': [{'username': 'KCS관리자', 'company': '케이씨에스'},
                                 {'username': '류병두', 'company': '케이씨에스', 'department': 'MICE사업팀',
                                  'org_path': ['MICE사업팀'], 'title': '매니져', 'account': 'rbd'},
                                 {'username': '퇴사자', 'company': '케이씨에스', 'department': '관리팀'},
                                 {'username': '그대로', 'company': '케이씨에스', 'department': '영업1부'}]},
                      f, ensure_ascii=False)
        self.db = os.path.join(self.dir, 'kakao.db')

    def open(self):
        from server.kakao.store import Store
        store = Store(self.db)
        self.addCleanup(store.close)
        return store

    def test_edits_and_deletes_survive_restart(self):
        store = self.open()
        store.member_update('류병두', {'department': '관리팀'})
        store.member_set_removed('퇴사자', True)
        store.member_create('신입', {'company': '케이씨에스', 'department': '신사업팀'})
        store.close()
        store = self.open()                                          # 다시 시작 = 시드 다시 적용
        self.assertEqual(store.get_user('류병두')['org_path'], ['관리팀'])
        self.assertEqual(store.get_user('류병두')['account'], 'rbd')            # 고치지 않은 필드도 그대로
        self.assertNotIn('퇴사자', [u['username'] for u in store.list_users()])
        self.assertEqual(store.get_user('신입')['org_path'], ['신사업팀'])
        self.assertEqual(store.get_user('그대로')['org_path'], ['영업1부'])     # 손대지 않은 사람은 시드대로
        self.assertEqual(store.admin_scope('KCS관리자'), '')


class MemberAdminClientTests(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.state.org = {'holding': {'name': '한국지주'}, 'companies': [{'name': '케이씨에스'}, {'name': '한네트'}]}
        self.users = [
            {'username': '홍길동', 'company': '케이씨에스', 'department': '개발팀', 'title': '', 'account': 'hong',
             'employee_no': 'E1', 'email': 'hong@kcs.test', 'extension': '', 'mobile': '', 'registered': True,
             'disabled': False, 'is_admin': True, 'admin_company': '', 'removed': False, 'online': True},
            {'username': '김철수', 'company': '케이씨에스', 'department': '영업팀', 'title': '대리', 'account': 'kim',
             'employee_no': 'E2', 'email': 'kim@kcs.test', 'extension': '5100', 'mobile': '', 'registered': True,
             'disabled': False, 'is_admin': False, 'admin_company': '', 'removed': False, 'online': False},
            {'username': '퇴사자', 'company': '케이씨에스', 'department': '', 'title': '', 'account': '',
             'employee_no': '', 'email': '', 'extension': '', 'mobile': '', 'registered': True,
             'disabled': True, 'is_admin': False, 'admin_company': '', 'removed': True, 'online': False}]

    def set_me(self, company=''):
        self.conn.push('user_updated', user={**self.state.user(self.state.me), 'is_admin': True,
                                             'admin_company': company})

    def dialog(self):
        from client.kakao.admin import AdminDialog
        dlg = AdminDialog(self.state)
        self.addCleanup(dlg.close)
        self.conn.push('admin_users', users=self.users, scope=self.state.admin_company())
        return dlg

    def test_group_admin_dialog_create_edit_delete_restore(self):
        from client.kakao.admin import MemberDialog
        self.set_me('')
        dlg = self.dialog()
        self.assertEqual(dlg.windowTitle(), '관리자 · 계정 관리 (그룹 전체)')
        self.assertEqual([u['username'] for u in dlg.visible_users()], ['홍길동', '김철수'])   # 삭제된 사람은 숨김
        self.assertIn('삭제 1명', dlg.count_label.text())
        dlg.show_removed.setChecked(True)
        self.assertEqual(len(dlg.visible_users()), 3)
        # 등록
        form = dlg.create_member(exec_=False)
        self.assertEqual([form.company_combo.itemText(i) for i in range(form.company_combo.count())],
                         ['한국지주', '케이씨에스', '한네트'])
        form.accept()
        self.assertIn('이름', form.error.text())
        form.name_edit.setText('신입')
        form.company_combo.setCurrentText('한네트')
        form.edits['employee_no'].setText('H 1')
        form.accept()
        self.assertIn('사번', form.error.text())
        form.edits['employee_no'].setText('H001')
        form.edits['email'].setText('new@hannet.test')
        with mock.patch.object(MemberDialog, 'exec_', return_value=MemberDialog.Accepted), \
                mock.patch.object(MemberDialog, 'username', return_value='신입'), \
                mock.patch.object(MemberDialog, 'fields', return_value=form.fields()):
            dlg.create_member()
        sent = self.conn.last('admin_member_create')
        self.assertEqual((sent['username'], sent['company'], sent['employee_no'], sent['email']),
                         ('신입', '한네트', 'H001', 'new@hannet.test'))
        # 조회 · 수정: 이름은 못 바꾸고 바뀐 필드만 보낸다
        dlg.select('김철수')
        edit = dlg.edit_member(exec_=False)
        self.assertTrue(edit.name_edit.isReadOnly())
        self.assertEqual(edit.edits['extension'].text(), '5100')
        edit.edits['title'].setText('과장')
        self.assertEqual(edit.changes(), {'title': '과장'})
        with mock.patch.object(MemberDialog, 'exec_', return_value=MemberDialog.Accepted), \
                mock.patch.object(MemberDialog, 'changes', return_value={'title': '과장'}):
            dlg.edit_member()
        self.assertEqual(self.conn.last('admin_member_update'), {'username': '김철수', 'title': '과장'})
        # 삭제 / 복원
        self.assertEqual(dlg.delete_button.text(), '삭제')
        with mock.patch.object(dlg, 'confirm', return_value=True):
            dlg.toggle_removed()
            self.assertEqual(self.conn.last('admin_member_delete'), {'username': '김철수'})
            dlg.select('퇴사자')
            self.assertEqual(dlg.delete_button.text(), '복원')
            self.assertFalse(dlg.reset_button.isEnabled())                     # 삭제된 사람은 복원·조회만
            dlg.toggle_removed()
        self.assertEqual(self.conn.last('admin_member_restore'), {'username': '퇴사자'})
        dlg.select('홍길동')
        self.assertFalse(dlg.delete_button.isEnabled())                        # 나 자신
        self.conn.push('admin_done', action='member_create', username='신입')
        self.assertIn('신입 님을 등록했습니다', dlg.status.text())

    def test_company_admin_dialog(self):
        self.set_me('케이씨에스')
        dlg = self.dialog()
        self.assertEqual(dlg.windowTitle(), '관리자 · 계정 관리 (케이씨에스)')
        dlg.select('김철수')
        self.assertTrue(dlg.notice_button.isHidden() and dlg.admin_button.isHidden())   # 그룹 관리자만
        form = dlg.create_member(exec_=False)
        self.assertEqual(form.company_combo.currentText(), '케이씨에스')
        self.assertFalse(form.company_combo.isEnabled())                        # 자기 회사로 고정

    def test_group_admin_assigns_company_scope(self):
        self.set_me('')
        dlg = self.dialog()
        dlg.select('김철수')
        with mock.patch('client.kakao.admin.QInputDialog.getItem', return_value=('케이씨에스', True)):
            dlg.toggle_admin()
        self.assertEqual(self.conn.last('admin_set_admin'), {'username': '김철수', 'is_admin': True,
                                                             'company': '케이씨에스'})
        with mock.patch('client.kakao.admin.QInputDialog.getItem', return_value=('그룹 전체', True)):
            dlg.toggle_admin()
        self.assertEqual(self.conn.last('admin_set_admin'), {'username': '김철수', 'is_admin': True})
        self.conn.push('admin_done', action='set_admin', username='김철수', is_admin=True, company='케이씨에스')
        self.assertIn('회사 관리자(케이씨에스)', dlg.status.text())

    def test_user_removed_leaves_lists(self):
        changed = []
        self.state.users_changed.connect(lambda: changed.append(1))
        self.assertIn('김철수', self.state.users)
        self.conn.push('user_removed', username='김철수')
        self.assertNotIn('김철수', self.state.users)
        self.assertTrue(changed)


if __name__ == '__main__':
    unittest.main()
