# -*- coding: utf-8 -*-
"""v5 - 업무용 메신저 필수 기능 (명세 §10): 방해금지 · 휴가 상태 · 방장 · 스레드"""

import os
import sys
import unittest
from datetime import datetime

from PyQt5.QtWidgets import QWidget as QWidget_

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_kakao_server import ServerTestBase  # noqa: E402


# ================================================================ §10.2 휴가 상태 (서버)
class VacationPresenceTest(ServerTestBase):
    def test_vacation_visible_while_offline(self):
        a, b = self.connect(), self.connect()
        a.send({'type': 'presence_set', 'presence': 'vacation'})
        b.wait_for('user_updated', lambda m: m['user']['username'] == a.username
                   and m['user']['presence'] == 'vacation')
        a.close()
        c = self.connect()
        users = {u['username']: u for u in c.welcome['users']}
        self.assertFalse(users[a.username]['online'])
        self.assertEqual(users[a.username]['presence'], 'vacation')

    def test_other_presence_offline_when_disconnected(self):
        a = self.connect()
        a.send({'type': 'presence_set', 'presence': 'meeting'})
        a.wait_for('user_updated', lambda m: m['user']['username'] == a.username)
        a.close()
        c = self.connect()
        users = {u['username']: u for u in c.welcome['users']}
        self.assertEqual(users[a.username]['presence'], 'offline')

    def test_invalid_presence(self):
        a = self.connect()
        err = a.expect_error({'type': 'presence_set', 'presence': 'sleeping'})
        self.assertIn('vacation', err['message'])


# ================================================================ §10.3 방장
class RoomOwnerTest(ServerTestBase):
    def test_creator_is_owner_and_direct_has_none(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        self.assertEqual(room['owner'], a.username)
        a.send({'type': 'room_open_direct', 'target': b.username})
        direct = a.wait_for('room_updated', lambda m: m['room']['type'] == 'direct')['room']
        self.assertIsNone(direct['owner'])

    def test_owner_kicks_member(self):
        a, b, c = self.connect(), self.connect(), self.connect()
        room = self.group(a, [b, c])
        a.send({'type': 'room_kick', 'room_id': room['room_id'], 'username': c.username})
        removed = c.wait_for('room_removed', lambda m: m['room_id'] == room['room_id'])
        self.assertTrue(removed.get('kicked'))
        upd = b.wait_for('room_updated', lambda m: m['room']['room_id'] == room['room_id']
                         and c.username not in m['room']['members'])
        self.assertEqual(sorted(upd['room']['members']), sorted([a.username, b.username]))
        sys_msg = b.wait_for('msg_new', lambda m: m['message']['kind'] == 'system'
                             and '내보냈습니다' in m['message']['content'])
        self.assertIn(c.username, sys_msg['message']['content'])

    def test_non_owner_cannot_kick_or_transfer(self):
        a, b, c = self.connect(), self.connect(), self.connect()
        room = self.group(a, [b, c])
        err = b.expect_error({'type': 'room_kick', 'room_id': room['room_id'], 'username': c.username})
        self.assertEqual(err['message'], '방장만 할 수 있습니다.')
        err = b.expect_error({'type': 'room_owner_set', 'room_id': room['room_id'], 'username': b.username})
        self.assertEqual(err['message'], '방장만 할 수 있습니다.')

    def test_owner_cannot_kick_self(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        err = a.expect_error({'type': 'room_kick', 'room_id': room['room_id'], 'username': a.username})
        self.assertIn('자기 자신', err['message'])

    def test_transfer_owner(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        a.send({'type': 'room_owner_set', 'room_id': room['room_id'], 'username': b.username})
        upd = a.wait_for('room_updated', lambda m: m['room']['room_id'] == room['room_id']
                         and m['room']['owner'] == b.username)
        self.assertEqual(upd['room']['owner'], b.username)
        b.wait_for('msg_new', lambda m: '방장이 되었습니다' in m['message']['content'])
        err = a.expect_error({'type': 'room_kick', 'room_id': room['room_id'], 'username': b.username})
        self.assertEqual(err['message'], '방장만 할 수 있습니다.')

    def test_owner_leaves_next_member_becomes_owner(self):
        a, b, c = self.connect(), self.connect(), self.connect()
        room = self.group(a, [b, c])
        a.send({'type': 'room_leave', 'room_id': room['room_id']})
        upd = b.wait_for('room_updated', lambda m: m['room']['room_id'] == room['room_id']
                         and a.username not in m['room']['members'])
        self.assertEqual(upd['room']['owner'], b.username)
        msg = c.wait_for('msg_new', lambda m: '방장이 되었습니다' in m['message']['content'])
        self.assertIn(b.username, msg['message']['content'])

    def test_kicked_user_cannot_rejoin_open_room(self):
        a, b = self.connect(), self.connect()
        a.send({'type': 'open_room_create', 'name': '오픈방', 'description': '', 'tags': []})
        room = a.wait_for('room_updated', lambda m: m['room']['type'] == 'open')['room']
        self.assertEqual(room['owner'], a.username)
        b.send({'type': 'open_room_join', 'room_id': room['room_id'], 'nickname': '손님'})
        b.wait_for('room_updated', lambda m: m['room']['room_id'] == room['room_id'])
        a.send({'type': 'room_kick', 'room_id': room['room_id'], 'username': b.username})
        b.wait_for('room_removed', lambda m: m['room_id'] == room['room_id'])
        err = b.expect_error({'type': 'open_room_join', 'room_id': room['room_id'], 'nickname': '손님2'})
        self.assertIn('다시 들어갈 수 없습니다', err['message'])

    def test_kick_in_direct_room_rejected(self):
        a, b = self.connect(), self.connect()
        a.send({'type': 'room_open_direct', 'target': b.username})
        direct = a.wait_for('room_updated', lambda m: m['room']['type'] == 'direct')['room']
        err = a.expect_error({'type': 'room_kick', 'room_id': direct['room_id'], 'username': b.username})
        self.assertIn('그룹 채팅방', err['message'])


# ================================================================ §10.4 스레드
class ThreadTest(ServerTestBase):
    def test_thread_reply_updates_root_and_thread_get(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        root = self.send_text(a, room['room_id'], '내일 회의 안건 정리해 주세요')
        self.assertIsNone(root['thread_root'])
        self.assertEqual(root['thread_count'], 0)
        reply = self.send_text(b, room['room_id'], '네 정리할게요', thread_root_id=root['msg_id'])
        self.assertEqual(reply['thread_root'], root['msg_id'])
        upd = a.wait_for('msg_updated', lambda m: m['message']['msg_id'] == root['msg_id'])
        self.assertEqual(upd['message']['thread_count'], 1)
        self.assertTrue(upd['message']['thread_last_at'])
        self.send_text(a, room['room_id'], '감사합니다', thread_root_id=root['msg_id'])
        th = a.request({'type': 'thread_get', 'root_id': root['msg_id']}, 'thread')
        self.assertEqual(th['root_id'], root['msg_id'])
        self.assertEqual(th['root']['thread_count'], 2)
        self.assertEqual([m['content'] for m in th['messages']], ['네 정리할게요', '감사합니다'])
        # 답글 id 로 요청해도 원글 스레드를 준다
        th2 = b.request({'type': 'thread_get', 'root_id': reply['msg_id']}, 'thread')
        self.assertEqual(th2['root_id'], root['msg_id'])

    def test_no_nested_thread(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        root = self.send_text(a, room['room_id'], '원글')
        reply = self.send_text(b, room['room_id'], '답글', thread_root_id=root['msg_id'])
        err = a.expect_error({'type': 'send', 'room_id': room['room_id'], 'kind': 'text', 'content': 'x',
                              'thread_root_id': reply['msg_id']})
        self.assertIn('다시 스레드', err['message'])

    def test_thread_root_must_be_in_same_room(self):
        a, b = self.connect(), self.connect()
        r1 = self.group(a, [b], name='방1')
        r2 = self.group(a, [b], name='방2')
        root = self.send_text(a, r1['room_id'], '원글')
        err = a.expect_error({'type': 'send', 'room_id': r2['room_id'], 'kind': 'text', 'content': 'x',
                              'thread_root_id': root['msg_id']})
        self.assertIn('원글을 찾을 수 없습니다', err['message'])

    def test_thread_reply_cannot_be_scheduled(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        root = self.send_text(a, room['room_id'], '원글')
        err = a.expect_error({'type': 'send', 'room_id': room['room_id'], 'kind': 'text', 'content': 'x',
                              'thread_root_id': root['msg_id'], 'send_at': '2099-01-01T09:00:00'})
        self.assertIn('예약', err['message'])

    def test_thread_get_requires_membership(self):
        a, b, c = self.connect(), self.connect(), self.connect()
        room = self.group(a, [b])
        root = self.send_text(a, room['room_id'], '원글')
        err = c.expect_error({'type': 'thread_get', 'root_id': root['msg_id']})
        self.assertIn('대화상대가 아닙니다', err['message'])

    def test_deleted_root_rejects_new_thread(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b])
        root = self.send_text(a, room['room_id'], '원글')
        a.send({'type': 'delete', 'msg_id': root['msg_id']})
        a.wait_for('msg_updated', lambda m: m['message']['msg_id'] == root['msg_id'] and m['message']['deleted'])
        err = b.expect_error({'type': 'send', 'room_id': room['room_id'], 'kind': 'text', 'content': 'x',
                              'thread_root_id': root['msg_id']})
        self.assertIn('스레드를 달 수 없습니다', err['message'])


# ================================================================ §10.1 방해금지 (클라이언트 로직)
class _Settings:
    def __init__(self, **values):
        self.values = dict(values)

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


class DndLogicTest(unittest.TestCase):
    def setUp(self):
        from client.kakao import dnd
        self.dnd = dnd
        self.monday_10 = datetime(2026, 10, 12, 10, 0)    # 월요일 10:00
        self.monday_20 = datetime(2026, 10, 12, 20, 0)
        self.saturday_10 = datetime(2026, 10, 17, 10, 0)

    def test_off_by_default(self):
        s = _Settings()
        self.assertEqual(self.dnd.dnd_reason(s, self.monday_20), '')
        self.assertFalse(self.dnd.suppresses(s, 'a', self.monday_20))
        self.assertEqual(self.dnd.status_text(s, self.monday_20), '사용 안 함')

    def test_pause_presets(self):
        s = _Settings()
        self.dnd.pause(s, 30, self.monday_10)
        self.assertEqual(s.get('dnd_until'), '2026-10-12T10:30:00')
        self.assertEqual(self.dnd.dnd_reason(s, datetime(2026, 10, 12, 10, 29)), 'pause')
        self.assertEqual(self.dnd.dnd_reason(s, datetime(2026, 10, 12, 10, 30)), '')
        self.assertIn('10:30까지', self.dnd.status_text(s, self.monday_10))
        self.dnd.pause(s, 'tomorrow', self.monday_20)
        self.assertEqual(s.get('dnd_until'), '2026-10-13T09:00:00')
        self.dnd.pause(s, 'forever', self.monday_10)
        self.assertEqual(self.dnd.dnd_reason(s, datetime(2030, 1, 1)), 'pause')
        self.assertIn('직접 끌 때까지', self.dnd.status_text(s, self.monday_10))
        self.dnd.resume(s)
        self.assertEqual(self.dnd.dnd_reason(s, self.monday_10), '')

    def test_work_hours(self):
        s = _Settings(work_hours={'enabled': True, 'days': [0, 1, 2, 3, 4], 'start': '09:00', 'end': '18:00'})
        self.assertEqual(self.dnd.dnd_reason(s, self.monday_10), '')
        self.assertEqual(self.dnd.dnd_reason(s, self.monday_20), 'off_hours')
        self.assertEqual(self.dnd.dnd_reason(s, self.saturday_10), 'off_hours')
        self.assertIn('근무 시간 밖', self.dnd.status_text(s, self.monday_20))

    def test_overnight_work_hours(self):
        s = _Settings(work_hours={'enabled': True, 'days': [0], 'start': '22:00', 'end': '06:00'})
        self.assertEqual(self.dnd.dnd_reason(s, datetime(2026, 10, 12, 23, 0)), '')   # 월 23시
        self.assertEqual(self.dnd.dnd_reason(s, datetime(2026, 10, 13, 5, 0)), '')    # 화 05시 = 월요일 근무
        self.assertEqual(self.dnd.dnd_reason(s, datetime(2026, 10, 13, 23, 0)), 'off_hours')

    def test_vip_passes(self):
        s = _Settings(vip_users=['boss'])
        self.dnd.pause(s, 60, self.monday_10)
        self.assertTrue(self.dnd.suppresses(s, 'peer', self.monday_10))
        self.assertFalse(self.dnd.suppresses(s, 'boss', self.monday_10))

    def test_state_should_alert_respects_dnd(self):
        from tests.kakao_fakes import make_demo_state
        state, _conn = make_demo_state()
        rid = 'r2'
        message = {'kind': 'text', 'content': 'hi', 'sender': '박민수', 'mentions': []}
        state.settings.set('dnd_until', '')
        state.settings.set('work_hours', {})
        state.settings.set('vip_users', [])
        baseline = state.should_alert(rid, message)
        self.dnd.pause(state.settings, 'forever')
        self.assertFalse(state.should_alert(rid, message))
        state.settings.set('vip_users', ['박민수'])
        self.assertTrue(baseline)
        self.assertTrue(state.should_alert(rid, message))
        self.dnd.resume(state.settings)



# ================================================================ 클라이언트 UI (FakeConnection)
class _UiBase(unittest.TestCase):
    room = 'r1'

    def setUp(self):
        from tests.kakao_fakes import make_demo_state, app
        from client.kakao import theme
        from client.kakao.chat_room import ChatRoomWindow
        app()
        theme.set_dark(False)
        self.state, self.conn = make_demo_state()
        self.win = ChatRoomWindow(self.state, self.room)
        self.win.confirm = lambda *a: True
        self.win.resize(420, 720)
        self.win.show()
        self.flush()

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()
        self.flush()

    @staticmethod
    def flush():
        from PyQt5.QtWidgets import QApplication
        for _ in range(3):
            QApplication.processEvents()

    def msg(self, msg_id, sender, content, **extra):
        m = dict(msg_id=msg_id, room_id=self.room, sender=sender, kind='text', content=content,
                 timestamp=datetime.now().replace(microsecond=0).isoformat(), reply_to=None, mentions=[],
                 reactions={}, deleted=False, attachment=None, event_id=None, poll=None)
        m.update(extra)
        return m


class ThreadUiTest(_UiBase):
    def test_thread_reply_hidden_from_timeline_and_root_shows_count(self):
        root = dict(self.state.find_message('r1', 2), thread_count=1,
                    thread_last_at=datetime.now().replace(microsecond=0).isoformat())
        self.conn.push('msg_new', message=self.msg(100, '이영희', '스레드 답글입니다', thread_root=2), client_tmp_id=None)
        self.conn.push('msg_updated', message=root)
        self.flush()
        self.assertNotIn(100, self.win.rows)
        row = self.win.rows[2]
        self.assertIsNotNone(row.thread_link)
        self.assertIn('답글 1개', row.thread_link.text())
        self.assertEqual(self.state.room('r1')['last_message']['msg_id'], 100)
        self.assertTrue(self.state.message_preview(self.state.find_message('r1', 100)).startswith('↳ '))

    def test_context_menu_and_thread_dialog_send(self):
        menu = self.win.build_context_menu(self.state.find_message('r1', 2))
        self.assertIn('스레드로 답장', [a.text() for a in menu.actions()])
        dlg = self.win.open_thread(self.state.find_message('r1', 2))
        self.flush()
        self.assertEqual(self.conn.last('thread_get'), {'root_id': 2})
        self.assertIs(self.win.open_thread(self.state.find_message('r1', 2)), dlg)   # 같은 원글은 같은 창
        dlg.edit.setText('제가 정리할게요')
        self.assertTrue(dlg.send())
        sent = self.conn.last('send')
        self.assertEqual((sent['thread_root_id'], sent['content']), (2, '제가 정리할게요'))
        self.assertNotIn('reply_to_id', sent)
        # 서버가 스레드를 돌려주면 답글이 보인다
        self.conn.push('thread', root_id=2, room_id='r1', root=dict(self.state.find_message('r1', 2), thread_count=1),
                       messages=[self.msg(101, '홍길동', '제가 정리할게요', thread_root=2)])
        self.flush()
        self.assertEqual(list(dlg.reply_labels), [101])
        self.assertIn('답글 1개', dlg.count_label.text())
        self.conn.push('msg_new', message=self.msg(102, '김철수', '감사합니다', thread_root=2), client_tmp_id=None)
        self.flush()
        self.assertEqual(list(dlg.reply_labels), [101, 102])
        dlg.close()

    def test_thread_reply_not_offered_for_thread_reply(self):
        self.conn.push('msg_new', message=self.msg(100, '이영희', '답글', thread_root=2), client_tmp_id=None)
        self.flush()
        menu = self.win.build_context_menu(self.state.find_message('r1', 100))
        self.assertNotIn('스레드로 답장', [a.text() for a in menu.actions()])

    def test_jump_to_unloaded_thread_reply_opens_thread(self):
        opened = []
        self.win.open_thread = lambda m: opened.append(m.get('thread_root') or m['msg_id'])
        # 검색 결과(hint)로 받은 답글은 히스토리를 넘기지 않고 바로 스레드를 연다
        hint = self.msg(200, '이영희', '검색된 답글', thread_root=2)
        self.win.focus_message(200, hint=hint)
        self.assertEqual(opened, [2])
        # 이전 대화를 넘기다 받은 답글도 스레드를 연다 (끝까지 넘기지 않음)
        self.state.has_more['r1'] = True
        self.win.focus_message(1)            # 가장 오래된 메시지보다 앞이 아니면 그 자리에서 처리
        self.win._pending_focus = 300
        self.conn.push('history', room_id='r1', messages=[self.msg(300, '김철수', '오래된 답글', thread_root=2)],
                       has_more=True)
        self.flush()
        self.assertEqual(opened, [2, 2])
        self.assertIsNone(self.win._pending_focus)

    def test_thread_send_failure_shows_error(self):
        dlg = self.win.open_thread(self.state.find_message('r1', 2))
        self.conn.send = lambda *a, **k: None
        dlg.edit.setText('안 가는 답글')
        self.assertFalse(dlg.send())
        self.assertFalse(dlg.error_label.isHidden())
        self.assertEqual(dlg.edit.text(), '안 가는 답글')
        dlg.close()


class RoomOwnerUiTest(_UiBase):
    def _set_owner(self, owner):
        room = dict(self.state.room('r1'), owner=owner)
        self.conn.push('room_updated', room=room)
        self.flush()

    def test_owner_sees_manage_buttons(self):
        self._set_owner('홍길동')
        popup = self.win.build_members_popup()
        self.assertEqual(popup.owner, '홍길동')
        self.assertEqual(sorted(popup.manage_buttons), ['김철수', '이영희'])
        popup.close()

    def test_member_sees_no_manage_buttons(self):
        self._set_owner('김철수')
        popup = self.win.build_members_popup()
        self.assertEqual(popup.manage_buttons, {})
        popup.close()

    def test_kick_and_transfer_send_requests(self):
        self._set_owner('홍길동')
        self.win.kick_member('이영희')
        self.assertEqual(self.conn.last('room_kick'), {'room_id': 'r1', 'username': '이영희'})
        self.win.transfer_owner('김철수')
        self.assertEqual(self.conn.last('room_owner_set'), {'room_id': 'r1', 'username': '김철수'})

    def test_kicked_notice(self):
        got = []
        self.state.notify.connect(lambda title, body, rid: got.append(body))
        self.conn.push('room_removed', room_id='r1', kicked=True)
        self.flush()
        self.assertTrue(any('내보내졌습니다' in b for b in got))
        self.assertNotIn('r1', self.state.rooms)


class VacationUiTest(unittest.TestCase):
    def test_vacation_shown_even_offline(self):
        from tests.kakao_fakes import make_demo_state
        from client.kakao.state import PRESENCE_LABELS
        state, conn = make_demo_state()
        conn.push('user_updated', user=dict(state.user('이영희'), online=False, presence='vacation'))
        self.assertEqual(state.presence_of('이영희'), 'vacation')
        self.assertEqual(PRESENCE_LABELS['vacation'], '휴가 중')
        state.set_presence('vacation')
        self.assertEqual(conn.last('presence_set'), {'presence': 'vacation'})


class TrayDndMenuTest(unittest.TestCase):
    def test_tray_presets_pause(self):
        from PyQt5.QtWidgets import QMenu
        from tests.kakao_fakes import make_demo_state
        from client.kakao import dnd
        from client.kakao.main_window import MainWindow
        state, _conn = make_demo_state()
        holder = type('W', (), {})()
        holder.settings = state.settings
        holder.tray_dnd_menu = QMenu()
        MainWindow._fill_tray_dnd_menu(holder)
        actions = {a.text(): a for a in holder.tray_dnd_menu.actions()}
        actions['1시간'].trigger()
        self.assertIsNotNone(dnd.paused_until(state.settings))
        MainWindow._fill_tray_dnd_menu(holder)
        actions = {a.text(): a for a in holder.tray_dnd_menu.actions()}
        actions['일시중지 끄기'].trigger()
        self.assertIsNone(dnd.paused_until(state.settings))
        actions['직접 끌 때까지'].trigger()
        self.assertEqual(state.settings.get('dnd_until'), dnd.DND_FOREVER)


class DndDialogTest(unittest.TestCase):
    def test_dialog_pause_work_hours_vip(self):
        from tests.kakao_fakes import make_demo_state
        from client.kakao.dnd import DndDialog, paused_until
        state, _conn = make_demo_state()
        dlg = DndDialog(state, state.settings)
        self.assertFalse(dlg.resume_button.isEnabled())
        dlg._pause(60)
        self.assertIsNotNone(paused_until(state.settings))
        self.assertIn('일시중지 중', dlg.status_label.text())
        dlg._resume()
        self.assertIsNone(paused_until(state.settings))
        dlg.work_check.setChecked(True)
        self.assertTrue(state.settings.get('work_hours')['enabled'])
        self.assertEqual(state.settings.get('work_hours')['days'], [0, 1, 2, 3, 4])
        self.assertTrue(dlg.add_vip('김철수'))
        self.assertFalse(dlg.add_vip('김철수'))     # 중복
        self.assertFalse(dlg.add_vip(state.me))     # 나 자신
        self.assertEqual(state.settings.get('vip_users'), ['김철수'])
        self.assertNotIn('김철수', [dlg.vip_combo.itemData(i) for i in range(dlg.vip_combo.count())])
        dlg.remove_vip('김철수')
        self.assertEqual(state.settings.get('vip_users'), [])
        dlg.close()


# ================================================================ §10.5 멘션 모아보기 (서버)
class MentionListTest(ServerTestBase):
    def test_mentions_across_rooms_newest_first(self):
        a, b, c = self.connect(), self.connect(), self.connect()
        r1 = self.group(a, [b], name='멘션1')
        r2 = self.group(a, [b, c], name='멘션2')
        self.send_text(b, r1['room_id'], f'@{a.username} 첫 번째', mentions=[a.username])
        self.send_text(b, r1['room_id'], '멘션 없음')
        self.send_text(c, r2['room_id'], f'@{a.username} 두 번째', mentions=[a.username])
        self.send_text(a, r2['room_id'], f'@{a.username} 내가 나를', mentions=[a.username])
        res = a.request({'type': 'mention_list'}, 'mention_list')
        self.assertEqual([m['content'] for m in res['messages']],
                         [f'@{a.username} 두 번째', f'@{a.username} 첫 번째'])

    def test_blocked_and_deleted_excluded(self):
        a, b = self.connect(), self.connect()
        room = self.group(a, [b], name='멘션3')
        m = self.send_text(b, room['room_id'], f'@{a.username} 지울 것', mentions=[a.username])
        b.send({'type': 'delete', 'msg_id': m['msg_id']})
        a.wait_for('msg_updated', lambda x: x['message']['msg_id'] == m['msg_id'])
        self.send_text(b, room['room_id'], f'@{a.username} 남는 것', mentions=[a.username])
        res = a.request({'type': 'mention_list'}, 'mention_list')
        self.assertEqual([x['content'] for x in res['messages']], [f'@{a.username} 남는 것'])
        a.request({'type': 'block_set', 'username': b.username, 'blocked': True}, 'block_list')
        res = a.request({'type': 'mention_list'}, 'mention_list')
        self.assertEqual(res['messages'], [])


# ================================================================ §10.6~10.8 클라이언트
class WorkUiTest(_UiBase):
    def test_unread_members_popup(self):
        m = self.state.find_message('r1', 11)
        names = self.state.unread_members('r1', m)
        self.assertEqual(names, ['홍길동', '이영희'] if self.state.display_name('홍길동') < self.state.display_name('이영희')
                         else ['이영희', '홍길동'])
        popup = self.win.show_unread_members(m)
        self.assertEqual(sorted(popup.member_names()), ['이영희', '홍길동'])
        popup.close()
        row = self.win.rows[11]
        self.assertEqual(row.unread_label.toolTip(), '안 읽은 사람 보기')
        self.assertIn('명 보기', row.unread_label.accessibleName())

    def test_draft_saved_on_close_and_restored(self):
        from client.kakao.chat_room import ChatRoomWindow
        self.win.edit.setPlainText('쓰다 만 보고서')
        self.win.close()
        self.flush()
        self.assertEqual(self.state.room_draft('r1'), '쓰다 만 보고서')
        again = ChatRoomWindow(self.state, 'r1')
        again.show()
        self.flush()
        self.assertEqual(again.edit.toPlainText(), '쓰다 만 보고서')
        again.edit.clear()
        again.close()
        self.flush()
        self.assertEqual(self.state.room_draft('r1'), '')

    def test_draft_not_revived_by_closed_window_timer(self):
        """닫힌 창의 자동 저장 타이머(0.8초)가 늦게 울려 다른 창에서 지운 임시저장을 되살리지 않는다"""
        from PyQt5.QtTest import QTest
        from client.kakao.chat_room import ChatRoomWindow
        self.win.edit.setPlainText('쓰다 만 글')                  # 자동 저장 타이머 시작
        self.win.close()                                          # 닫으며 저장 + 타이머 멈춤
        self.assertFalse(self.win._draft_timer.isActive())
        again = ChatRoomWindow(self.state, 'r1')
        again.show()
        self.flush()
        again.edit.clear()
        again.close()
        QTest.qWait(1000)                                         # 예전에는 여기서 옛 글이 다시 저장됐다
        self.assertEqual(self.state.room_draft('r1'), '')

    def test_draft_shown_in_chat_list_preview(self):
        from client.kakao.chats_tab import ChatsTab, ElidedLabel
        self.state.set_room_draft('r2', '내일 보낼 글')
        tab = ChatsTab(self.state, self.state.settings)
        tab.refresh()
        previews = [w.text() for w in tab.findChildren(ElidedLabel)]
        self.assertIn('[임시저장] 내일 보낼 글', previews)

    def test_bookmark_menu_and_dialog(self):
        from client.kakao.inbox import SavedDialog
        m = self.state.find_message('r1', 2)
        menu = self.win.build_context_menu(m)
        acts = {a.text(): a for a in menu.actions()}
        acts['책갈피'].trigger()
        self.assertTrue(self.state.is_saved('r1', 2))
        menu = self.win.build_context_menu(m)
        self.assertIn('책갈피 해제', [a.text() for a in menu.actions()])
        jumped = []

        class Host(QWidget_):
            def focus_message(self, rid, mid, hint=None):
                jumped.append((rid, mid))
        host = Host()
        dlg = SavedDialog(self.state, host)
        self.assertEqual(dlg.list.count(), 1)
        self.assertTrue(dlg.open_selected())
        self.assertEqual(jumped, [('r1', 2)])
        dlg.remove_selected()
        self.assertEqual(dlg.list.count(), 0)
        self.assertFalse(self.state.is_saved('r1', 2))
        dlg.close()

    def test_mentions_dialog_requests_and_lists(self):
        from client.kakao.inbox import MentionsDialog
        dlg = MentionsDialog(self.state)
        self.assertEqual(self.conn.last('mention_list'), {'limit': 100})
        self.conn.push('mention_list', messages=[self.msg(500, '김철수', '@홍길동 확인 부탁', mentions=['홍길동'])])
        self.flush()
        self.assertEqual(dlg.list.count(), 1)
        # 새로 받은 멘션은 목록 맨 앞에 붙는다
        self.conn.push('msg_new', message=self.msg(501, '이영희', '@홍길동 하나 더', mentions=['홍길동']), client_tmp_id=None)
        self.flush()
        self.assertEqual(self.state.mentions[0]['msg_id'], 501)
        self.assertEqual(dlg.list.count(), 2)
        dlg.close()


class MainWindowMinSizeTest(unittest.TestCase):
    def test_min_size_follows_layout_at_200_percent(self):
        from tests.kakao_fakes import make_demo_state
        from client.kakao import theme
        from client.kakao.main_window import MainWindow
        from PyQt5.QtWidgets import QApplication
        state, _conn = make_demo_state()
        try:
            theme.set_font_scale(2.0)
            mw = MainWindow(state, state.settings)
            mw.show()
            mw.set_tab('calendar')
            QApplication.processEvents()
            mw.resize(300, 600)
            QApplication.processEvents()
            month = mw.tabs['calendar'].month_label
            need = month.fontMetrics().horizontalAdvance(month.text())
            self.assertGreaterEqual(month.width() + 2, need)
            mw.close()
        finally:
            theme.set_font_scale(1.0)


class ContrastTest(unittest.TestCase):
    def test_theme_tokens_meet_wcag(self):
        from scripts.harness.design_probe import contrast_failures
        self.assertEqual(contrast_failures(), [])


if __name__ == '__main__':
    unittest.main()
