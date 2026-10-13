# -*- coding: utf-8 -*-
"""파일 전송 보안 (명세 §10.10): 형태 · 확장자 · 파일 이름으로 막기, 그룹 관리자 정책, 승인 요청 → 승인 시 전송, 예외"""

import base64
import io
import os
import tempfile
import unittest
import zipfile


from tests.kakao_fakes import app, make_demo_state
from tests.test_kakao_server import ServerTestBase, Client, uname

from server.kakao import file_policy
from server.kakao.file_policy import DEFAULT_POLICY, check, normalize_policy, PolicyError
from client.kakao.file_guard import (FILE_BLOCKED, FileBlockedDialog, precheck)

EXE = b'MZ\x90\x00' + b'\0' * 60
PNG = b'\x89PNG\r\n\x1a\n' + b'\0' * 32


def b64(data):
    return base64.b64encode(data).decode()


def zip_with(*names):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name in names:
            zf.writestr(name, b'x')
    return buf.getvalue()


class PolicyCheckTests(unittest.TestCase):
    def test_default_blocks_executables_by_extension_and_content(self):
        self.assertEqual(check(None, 'setup.exe', b'hello')['rule'], 'type')
        disguised = check(None, '보고서.txt', EXE)                         # 이름만 바꾼 실행 파일
        self.assertEqual((disguised['rule'], disguised['value']), ('type', 'executable'))
        self.assertIn('내용은 실행 파일', disguised['detail'])
        self.assertEqual(check(None, 'run.txt', b'#!/bin/sh\nrm -rf /')['value'], 'executable')
        self.assertEqual(check(None, 'customers.txt', b'SQLite format 3\x00...')['value'], 'database')
        self.assertEqual(check(None, 'id_rsa', b'-----BEGIN OPENSSH PRIVATE KEY-----')['value'], 'credential')

    def test_default_allows_everyday_files(self):
        for name, data in (('회의록.txt', '안건'.encode()), ('사진.png', PNG), ('보고서.docx', zip_with('word/x.xml')),
                           ('보고서.bin', b'\0' * 10), ('BMW 견적.txt', b'BMW 520d')):
            self.assertIsNone(check(None, name, data), name)

    def test_names_extensions_and_zip_contents(self):
        policy = normalize_policy({'enabled': True, 'blocked_types': ['archive'], 'blocked_extensions': ['.HWP', 'dwg'],
                                   'blocked_names': ['*대외비*', '고객명단']})
        self.assertEqual(policy['blocked_extensions'], ['hwp', 'dwg'])
        self.assertEqual(check(policy, '2026 사업계획(대외비).pdf', b'%PDF')['rule'], 'name')
        self.assertEqual(check(policy, '영업_고객명단_v2.xlsx', b'')['rule'], 'name')      # * 없으면 '들어 있으면'
        self.assertEqual(check(policy, '도면.DWG', b'AC1032')['rule'], 'extension')
        self.assertEqual(check(policy, 'a.7z', b'7z\xbc\xaf\x27\x1c')['value'], 'archive')
        self.assertEqual(check(policy, '자료.pdf', b'PK\x03\x04')['value'], 'archive')       # 확장자 위장한 압축
        self.assertIsNone(check(policy, '계약서.hwpx', zip_with('mimetype', 'Contents/a.xml')))   # 한글 문서는 압축이 아니다
        self.assertIsNone(check(policy, '보고서.docx', zip_with('[Content_Types].xml', 'word/document.xml')))
        renamed = check(policy, '보고서.docx', zip_with('대외비_원가.xlsx'))              # 압축 파일을 .docx 로 바꿈
        self.assertEqual((renamed['value'], renamed['disguised']), ('archive', True))
        policy = normalize_policy(dict(DEFAULT_POLICY))
        inner = check(policy, 'photos.zip', zip_with('a.png', 'tools/setup.exe'))          # 압축 안 실행 파일
        self.assertIn("압축 파일 안 'setup.exe'", inner['detail'])
        self.assertIn('대외비', check(policy, 'x.zip', zip_with('대외비_원가.xlsx'))['detail'])

    def test_disabled_and_validation(self):
        self.assertIsNone(check({**DEFAULT_POLICY, 'enabled': False}, 'setup.exe', EXE))
        for bad in ({'blocked_types': ['nope']}, {'blocked_extensions': ['*.zip']}, {'enabled': 'yes'},
                    {'blocked_names': 'x'}, {'blocked_names': ['a' * 61]}, 'x'):
            with self.assertRaises(PolicyError):
                normalize_policy(bad)
        public = file_policy.public_policy(None)
        self.assertEqual(public['blocked_types'], DEFAULT_POLICY['blocked_types'])
        self.assertIn('exe', next(c for c in public['categories'] if c['key'] == 'executable')['extensions'])


class FileSecurityServerTests(ServerTestBase):
    def setUp(self):
        super().setUp()
        self.server.store.set_file_policy(dict(DEFAULT_POLICY))

    def member(self, admin=False, company=''):
        name = uname('fs')
        store = self.server.store
        store.register_user(name, 'KCS 홀딩스', f'{name}@kcs.test', 'pw-1234', employee_no=f'F{name}'[:20])
        if admin:
            store.set_admin(name, True, company)
        c = Client(self.port, name, join=False)
        self.clients.append(c)
        c.welcome = c.request({'type': 'join', 'username': name, 'password': 'pw-1234'}, 'welcome')
        return c

    def send_file(self, client, room_id, name, data, kind='file', tmp='f1'):
        client.send({'type': 'send', 'room_id': room_id, 'kind': kind, 'content': name, 'client_tmp_id': tmp,
                     'attachment': {'name': name, 'mime': 'application/octet-stream', 'data_b64': b64(data)}})

    def test_blocked_send_and_policy_admin_only(self):
        a, b = self.member(), self.member()
        welcome_policy = a.welcome['file_policy']
        self.assertEqual(welcome_policy['blocked_types'], DEFAULT_POLICY['blocked_types'])
        room = self.group(a, [b])
        self.send_file(a, room['room_id'], '정산.txt', EXE, tmp='x1')
        blocked = a.wait_for('file_blocked')
        self.assertEqual((blocked['client_tmp_id'], blocked['rule'], blocked['name']), ('x1', 'type', '정산.txt'))
        b.assert_no('msg_new', lambda m: m['message']['kind'] == 'file')
        policy = {'enabled': True, 'blocked_types': [], 'blocked_extensions': ['hwp'], 'blocked_names': []}
        self.assertIn('관리자만', a.expect_error({'type': 'admin_file_policy_set', 'policy': policy})['message'])
        company_admin = self.member(admin=True, company='KCS 홀딩스')
        self.assertIn('그룹 관리자만',
                      company_admin.expect_error({'type': 'admin_file_policy_set', 'policy': policy})['message'])
        admin = self.member(admin=True)
        done = admin.request({'type': 'admin_file_policy_set', 'policy': policy}, 'admin_done')
        self.assertEqual(done['action'], 'file_policy')
        pushed = b.wait_for('file_policy')['policy']                         # 모두에게 바로 적용
        self.assertEqual(pushed['blocked_extensions'], ['hwp'])
        self.send_file(a, room['room_id'], '정산.txt', EXE, tmp='x2')        # 실행 파일은 이제 풀림
        b.wait_for('msg_new', lambda m: m['message']['kind'] == 'file')
        self.send_file(a, room['room_id'], '계획.hwp', b'HWP', tmp='x3')
        self.assertEqual(a.wait_for('file_blocked', lambda m: m['client_tmp_id'] == 'x3')['rule'], 'extension')
        err = admin.expect_error({'type': 'admin_file_policy_set', 'policy': {'blocked_types': ['bogus']}})
        self.assertIn('알 수 없는 파일 형태', err['message'])

    def test_request_approve_delivers_and_allows_same_file(self):
        a, b = self.member(), self.member()
        admin = self.member(admin=True)
        room = self.group(a, [b])
        rid = room['room_id']
        err = a.expect_error({'type': 'file_send_request', 'room_id': rid, 'kind': 'file', 'reason': '  ',
                              'attachment': {'name': 'tool.exe', 'data_b64': b64(EXE)}})
        self.assertIn('사유', err['message'])
        request = a.request({'type': 'file_send_request', 'room_id': rid, 'kind': 'file', 'reason': '협력사 설치용',
                             'attachment': {'name': 'tool.exe', 'data_b64': b64(EXE)}}, 'file_request_ok')['request']
        self.assertEqual((request['status'], request['username'], request['rule']), ('pending', a.username, 'type'))
        self.assertEqual(request['room_label'], '테스트방')
        new = admin.wait_for('file_request_new')['request']                   # 그룹 관리자에게 알림
        self.assertEqual(new['request_id'], request['request_id'])
        b.assert_no('msg_new', lambda m: m['message']['kind'] == 'file')      # 승인 전에는 안 간다
        listed = admin.request({'type': 'admin_file_requests', 'status': 'pending'}, 'admin_file_requests')
        self.assertIn(request['request_id'], [r['request_id'] for r in listed['requests']])
        data = admin.request({'type': 'attachment_get', 'attachment_id': request['attachment_id']}, 'attachment_data')
        self.assertEqual(base64.b64decode(data['data_b64']), EXE)            # 관리자가 받아 확인
        self.assertIn('권한', b.expect_error({'type': 'attachment_get',
                                             'attachment_id': request['attachment_id']})['message'])
        a.clear()
        done = admin.request({'type': 'admin_file_request_decide', 'request_id': request['request_id'],
                              'approve': True, 'note': '확인함', 'allow_days': 3}, 'admin_done')
        self.assertTrue(done['approved'])
        msg = b.wait_for('msg_new', lambda m: m['message']['kind'] == 'file')['message']
        self.assertEqual((msg['sender'], msg['attachment']['name']), (a.username, 'tool.exe'))   # 요청한 사람 이름으로
        updated = a.wait_for('file_request_updated')['request']
        self.assertEqual((updated['status'], updated['note'], updated['msg_id']), ('approved', '확인함', msg['msg_id']))
        err = admin.expect_error({'type': 'admin_file_request_decide', 'request_id': request['request_id'],
                                  'approve': False})
        self.assertIn('이미 처리된', err['message'])
        self.send_file(a, rid, 'tool-copy.exe', EXE, tmp='same')              # 같은 파일(지문)은 3일간 허용
        b.wait_for('msg_new', lambda m: m['message']['attachment'] and m['message']['attachment']['name'] == 'tool-copy.exe')
        self.send_file(a, rid, 'other.exe', EXE + b'1', tmp='other')          # 다른 파일은 여전히 막힘
        a.wait_for('file_blocked', lambda m: m['client_tmp_id'] == 'other')
        self.send_file(b, rid, 'tool.exe', EXE, tmp='b1')                     # 예외는 그 사람에게만
        b.wait_for('file_blocked', lambda m: m['client_tmp_id'] == 'b1')
        mine = a.request({'type': 'file_request_list'}, 'file_requests')['requests']
        self.assertEqual(mine[0]['status'], 'approved')

    def test_reject_and_left_room(self):
        a, b = self.member(), self.member()
        admin = self.member(admin=True)
        room = self.group(a, [b])
        req = lambda name: a.request({'type': 'file_send_request', 'room_id': room['room_id'], 'reason': '필요',
                                      'attachment': {'name': name, 'data_b64': b64(EXE + name.encode())}},
                                     'file_request_ok')['request']
        first, second = req('a.exe'), req('b.exe')
        admin.request({'type': 'admin_file_request_decide', 'request_id': first['request_id'], 'approve': False,
                       'note': '외부 반출 불가'}, 'admin_done')
        rejected = a.wait_for('file_request_updated')['request']
        self.assertEqual((rejected['status'], rejected['note']), ('rejected', '외부 반출 불가'))
        self.assertEqual(self.server.store.get_attachment(first['attachment_id'])['data'], b'')   # 보관 파일 삭제
        a.request({'type': 'room_leave', 'room_id': room['room_id']}, 'room_removed')
        err = admin.expect_error({'type': 'admin_file_request_decide', 'request_id': second['request_id'],
                                  'approve': True})
        self.assertIn('채팅방에 없어', err['message'])
        self.assertIn('그룹 관리자만', self.member(admin=True, company='KCS 홀딩스').expect_error(
            {'type': 'admin_file_requests'})['message'])

    def test_not_blocked_request_is_sent_right_away(self):
        a, b = self.member(), self.member()
        room = self.group(a, [b])
        a.send({'type': 'file_send_request', 'room_id': room['room_id'], 'reason': '혹시 몰라서',
                'attachment': {'name': '메모.txt', 'data_b64': b64('안녕'.encode())}})
        b.wait_for('msg_new', lambda m: m['message']['kind'] == 'file')

    def test_person_pattern_exception(self):
        a, b = self.member(), self.member()
        admin = self.member(admin=True)
        room = self.group(a, [b])
        admin.request({'type': 'admin_file_policy_set', 'policy': {'enabled': True, 'blocked_types': ['archive']}},
                      'admin_done')
        err = admin.expect_error({'type': 'admin_file_exception_add', 'username': a.username, 'days': 1})
        self.assertIn('파일 이름', err['message'])
        err = admin.expect_error({'type': 'admin_file_exception_add', 'username': a.username, 'days': 0,
                                  'pattern': '*.zip'})
        self.assertIn('허용 기간', err['message'])
        done = admin.request({'type': 'admin_file_exception_add', 'username': a.username, 'days': 2,
                              'pattern': '*.zip', 'note': '고객사 납품'}, 'admin_done')
        exception = done['exception']
        self.assertEqual((exception['username'], exception['pattern']), (a.username, '*.zip'))
        listed = admin.request({'type': 'admin_file_exceptions'}, 'admin_file_exceptions')['exceptions']
        self.assertIn(exception['exception_id'], [e['exception_id'] for e in listed])
        self.send_file(a, room['room_id'], '납품.zip', zip_with('a.txt'), tmp='z1')
        b.wait_for('msg_new', lambda m: m['message']['kind'] == 'file')
        self.send_file(b, room['room_id'], '납품.zip', zip_with('a.txt'), tmp='z2')
        b.wait_for('file_blocked', lambda m: m['client_tmp_id'] == 'z2')
        admin.request({'type': 'admin_file_exception_delete', 'exception_id': exception['exception_id']}, 'admin_done')
        self.send_file(a, room['room_id'], '납품.zip', zip_with('a.txt'), tmp='z3')
        a.wait_for('file_blocked', lambda m: m['client_tmp_id'] == 'z3')


class FileSecurityClientTests(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.conn.push('file_policy', policy=file_policy.public_policy({**DEFAULT_POLICY, 'blocked_extensions': ['hwp']}))
        self.tmp = tempfile.mkdtemp()
        self.rid = next(iter(self.state.rooms))

    def path(self, name, data=b'data'):
        path = os.path.join(self.tmp, name)
        with open(path, 'wb') as f:
            f.write(data)
        return path

    def test_precheck(self):
        policy = self.state.file_policy
        self.assertEqual(precheck(policy, 'setup.EXE')['rule'], 'type')
        self.assertEqual(precheck(policy, '계획.hwp')['rule'], 'extension')
        self.assertEqual(precheck(policy, '(대외비) 원가.xlsx')['rule'], 'name')
        self.assertIsNone(precheck(policy, '회의록.docx'))
        self.assertIsNone(precheck({**policy, 'enabled': False}, 'setup.exe'))
        self.assertIsNone(precheck({}, 'setup.exe'))                           # 정책을 못 받았으면 서버에 맡긴다

    def test_blocked_file_is_not_uploaded_and_can_be_requested(self):
        got = []
        self.state.file_blocked.connect(got.append)
        self.assertEqual(self.state.send_file(self.rid, self.path('계획.hwp', b'HWPDATA')), FILE_BLOCKED)
        self.assertIsNone(self.conn.last('send'))                              # 올리지 않는다
        self.assertEqual((got[0]['name'], got[0]['rule']), ('계획.hwp', 'extension'))
        dlg = FileBlockedDialog(self.state, got[0])
        self.addCleanup(dlg.close)
        self.assertFalse(dlg.request_button.isEnabled())                       # 사유를 적어야
        dlg.reason_edit.setPlainText('협력사 계약 검토')
        self.assertTrue(dlg.request_button.isEnabled())
        dlg.submit()
        sent = self.conn.last('file_send_request')
        self.assertEqual((sent['room_id'], sent['reason'], sent['attachment']['name']),
                         (self.rid, '협력사 계약 검토', '계획.hwp'))
        self.assertEqual(base64.b64decode(sent['attachment']['data_b64']), b'HWPDATA')
        self.assertEqual(dlg.result(), FileBlockedDialog.Accepted)

    def test_server_side_block_uses_kept_file(self):
        got = []
        self.state.file_blocked.connect(got.append)
        self.assertIsNone(self.state.send_file(self.rid, self.path('정산.txt', EXE)))
        tmp = self.conn.last('send')['client_tmp_id']
        self.conn.push('file_blocked', room_id=self.rid, name='정산.txt', size=len(EXE), client_tmp_id=tmp,
                       rule='type', value='executable', detail='확장자는 .txt 이지만 내용은 실행 파일이에요')
        self.assertTrue(self.state.can_request_file(got[0]['client_tmp_id']))
        self.assertIsNone(self.state.request_file_send(tmp, '필요'))
        self.assertEqual(self.conn.last('file_send_request')['attachment']['name'], '정산.txt')
        unknown = FileBlockedDialog(self.state, {'name': 'x.exe', 'client_tmp_id': 'gone'})   # 전달 등 원본 없음
        self.addCleanup(unknown.close)
        self.assertFalse(unknown.request_button.isVisible() or unknown.reason_edit.isVisibleTo(unknown))

    def test_request_results_notify_and_main_window_dialog(self):
        from client.kakao.main_window import MainWindow
        notes = []
        self.state.notify.connect(lambda title, body, rid: notes.append((title, body)))
        self.conn.push('file_request_updated', request={'request_id': 1, 'username': self.state.me, 'name': 'a.exe',
                                                        'status': 'rejected', 'note': '반출 불가', 'room_id': self.rid})
        self.assertEqual(notes[-1], ('파일 전송 반려', "'a.exe' 요청이 반려됐어요 · 반출 불가"))
        win = MainWindow(self.state, self.state.settings)
        self.addCleanup(win.close)
        self.state.send_file(self.rid, self.path('계획.hwp'))
        self.assertIsInstance(win.file_blocked_dialog, FileBlockedDialog)
        self.assertEqual(win.file_blocked_dialog.name_label.text(), '계획.hwp')
        win.file_blocked_dialog.close()

    def test_admin_dialog(self):
        from client.kakao.admin import AdminDialog
        self.conn.push('user_updated', user=dict(self.state.user(self.state.me), is_admin=True, admin_company=''))
        admin = AdminDialog(self.state)
        self.addCleanup(admin.close)
        self.assertFalse(admin.file_security_button.isHidden())
        dlg = admin.open_file_security(exec_=False)
        self.addCleanup(dlg.close)
        self.assertIsNotNone(self.conn.last('admin_file_requests'))
        self.assertIsNotNone(self.conn.last('admin_file_exceptions'))
        # 정책 탭: 받은 정책이 채워지고 그대로 저장된다
        tab = dlg.policy_tab
        self.assertTrue(tab.type_checks['executable'].isChecked() and not tab.type_checks['archive'].isChecked())
        tab.type_checks['archive'].setChecked(True)
        tab.ext_edit.setText('hwp, .DWG ,')
        tab.names_edit.setPlainText('*대외비*\n\n고객명단')
        tab.save()
        self.assertEqual(self.conn.last('admin_file_policy_set')['policy'],
                         {'enabled': True, 'blocked_types': ['executable', 'archive', 'database', 'credential'],
                          'blocked_extensions': ['hwp', 'dwg'], 'blocked_names': ['*대외비*', '고객명단']})
        tab.enabled_check.setChecked(False)
        self.assertFalse(tab.ext_edit.isEnabled())
        # 승인 요청 탭
        request = {'request_id': 7, 'username': '김철수', 'name': 'tool.exe', 'size': 2048, 'rule': 'type',
                   'detail': '실행 파일 · 스크립트은(는) 보낼 수 없어요', 'room_label': '1:1 · 홍길동',
                   'reason': '장비 설치', 'status': 'pending', 'attachment_id': 99, 'created_at': '2026-10-11T09:00:00'}
        self.conn.push('admin_file_requests', requests=[request, dict(request, request_id=8, status='approved')])
        tab = dlg.requests_tab
        self.assertEqual(tab.table.rowCount(), 1)                              # 대기 중만
        self.assertEqual(dlg.tabs.tabText(1), '승인 요청 1')
        self.assertFalse(tab.approve_button.isEnabled())
        self.assertTrue(tab.select(7))
        self.assertIn('장비 설치', tab.reason_label.text())
        tab.allow_days.setValue(3)
        tab.note_edit.setText('확인함')
        tab.decide(True)
        self.assertEqual(self.conn.last('admin_file_request_decide'),
                         {'request_id': 7, 'approve': True, 'note': '확인함', 'allow_days': 3})
        out = os.path.join(self.tmp, 'saved.exe')
        tab.download(out)
        self.assertEqual(self.conn.last('attachment_get'), {'attachment_id': 99})
        self.conn.push('attachment_data', attachment_id=99, name='tool.exe', mime='application/octet-stream',
                       data_b64=b64(EXE))
        with open(out, 'rb') as f:
            self.assertEqual(f.read(), EXE)
        self.conn.push('admin_done', action='file_request_decide', username='김철수', request_id=7, approved=True)
        self.assertIn('승인했어요', dlg.status.text())
        tab.pending_only.setChecked(False)
        self.assertEqual(tab.table.rowCount(), 2)
        # 예외 탭
        ex = dlg.exceptions_tab
        add = ex.add(exec_=False)
        self.addCleanup(add.close)
        self.assertFalse(add.add_button.isEnabled())
        add.user_combo.setCurrentText('김철수')
        add.pattern_edit.setText('*.zip')
        self.assertTrue(add.add_button.isEnabled())
        self.assertEqual(add.values()['days'], 7)
        self.conn.push('admin_file_exceptions', exceptions=[
            {'exception_id': 3, 'username': '김철수', 'sha256': 'a' * 64, 'file_name': 'tool.exe', 'pattern': '',
             'expires_at': '2026-10-14T09:00:00', 'note': '', 'created_by': '홍길동'}])
        self.assertEqual(ex.table.item(0, 1).text(), 'tool.exe (이 파일만)')
        ex.table.selectRow(0)
        ex.delete()
        self.assertEqual(self.conn.last('admin_file_exception_delete'), {'exception_id': 3})

    def test_company_admin_has_no_file_security(self):
        from client.kakao.admin import AdminDialog
        self.conn.push('user_updated', user=dict(self.state.user(self.state.me), is_admin=True,
                                                 admin_company='케이씨에스'))
        admin = AdminDialog(self.state)
        self.addCleanup(admin.close)
        self.assertTrue(admin.file_security_button.isHidden())


if __name__ == '__main__':
    unittest.main()
