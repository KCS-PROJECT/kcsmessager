# -*- coding: utf-8 -*-
"""v3 클라이언트 상태 테스트 - 비밀채팅 암호화, 알림 규칙, 통화·펑·게시판·오픈채팅·차단 상태 처리"""

import os
import sys
import tempfile
import unittest

from tests.kakao_fakes import make_demo_state, app

from client.kakao.secret import SecretKeyring


def msg(**kw):
    base = dict(msg_id=100, room_id='r1', sender='김철수', kind='text', content='', timestamp='2026-10-08T10:00:00',
                reply_to=None, mentions=[], reactions={}, deleted=False, attachment=None, event_id=None,
                poll=None, edited=False, edited_at=None, silent=False, link_preview=None)
    base.update(kw)
    return base


class SecretCryptoTest(unittest.TestCase):
    def test_round_trip_and_tamper(self):
        d = tempfile.mkdtemp()
        alice, bob = SecretKeyring('alice', d), SecretKeyring('bob', d)
        blob = alice.encrypt('s1', bob.public_key_b64, '비밀 이야기 🤫')
        self.assertNotIn('비밀', blob)
        self.assertEqual(bob.decrypt('s1', alice.public_key_b64, blob), '비밀 이야기 🤫')
        self.assertIsNone(bob.decrypt('s2', alice.public_key_b64, blob))          # 다른 방(salt/AAD)
        eve = SecretKeyring('eve', d)
        self.assertIsNone(eve.decrypt('s1', alice.public_key_b64, blob))          # 제3자
        tampered = blob[:-4] + ('AAAA' if not blob.endswith('AAAA') else 'BBBB')
        self.assertIsNone(bob.decrypt('s1', alice.public_key_b64, tampered))

    def test_key_persists_with_private_permissions(self):
        d = tempfile.mkdtemp()
        k1 = SecretKeyring('carol', d)
        k2 = SecretKeyring('carol', d)
        self.assertEqual(k1.public_key_b64, k2.public_key_b64)
        if not sys.platform.startswith('win'):              # POSIX 권한 (Windows 는 프로필 폴더 권한)
            self.assertEqual(os.stat(k1.path).st_mode & 0o777, 0o600)


class V3StateTest(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()

    def collect(self, signal):
        got = []
        signal.connect(lambda *a: got.append(a))
        return got

    def test_welcome_publishes_key(self):
        self.conn.sent.clear()
        s = self.state
        self.conn.push('welcome', me=s.user('홍길동'), users=list(s.users.values()), rooms=list(s.rooms.values()))
        self.assertIsNotNone(self.conn.last('key_publish'))
        self.assertIsNotNone(self.conn.last('story_list'))

    def test_secret_room_encrypt_and_decrypt(self):
        s = self.state
        peer = SecretKeyring('박민수', tempfile.mkdtemp())
        self.conn.push('user_updated', user=dict(s.user('박민수'), public_key=peer.public_key_b64))
        self.conn.push('user_updated', user=dict(s.user('홍길동'), public_key=s.keyring.public_key_b64))
        room = {'room_id': 's9', 'type': 'secret', 'name': '', 'members': ['홍길동', '박민수'], 'created_at': '',
                'notice': None, 'last_message': None, 'read_pointers': {}, 'unread_count': 0}
        self.conn.push('room_updated', room=room)
        self.assertEqual(s.room_title('s9'), '🔒 박민수')
        self.assertIsNone(s.send_secret('s9', '안녕 비밀'))
        sent = self.conn.last('send')
        self.assertEqual(sent['kind'], 'secret')
        self.assertEqual(peer.decrypt('s9', s.keyring.public_key_b64, sent['content']), '안녕 비밀')
        incoming = peer.encrypt('s9', s.keyring.public_key_b64, '답장이야')
        self.conn.push('msg_new', message=msg(msg_id=300, room_id='s9', sender='박민수', kind='secret', content=incoming))
        m = s.find_message('s9', 300)
        self.assertEqual((m['secret_text'], m['secret_ok']), ('답장이야', True))
        self.assertEqual(s.message_preview(m), '🔒 비밀채팅 메시지')
        self.conn.push('msg_new', message=msg(msg_id=301, room_id='s9', sender='박민수', kind='secret', content='garbage'))
        self.assertFalse(s.find_message('s9', 301)['secret_ok'])

    def test_secret_requires_peer_key(self):
        s = self.state
        room = {'room_id': 's8', 'type': 'secret', 'name': '', 'members': ['홍길동', '최지우'], 'created_at': '',
                'notice': None, 'last_message': None, 'read_pointers': {}, 'unread_count': 0}
        self.conn.push('room_updated', room=room)
        self.assertIn('비밀채팅', s.send_secret('s8', 'hi'))

    def test_alert_rules_keyword_mention_lock(self):
        s = self.state
        notes = self.collect(s.notify)
        s.set_room_alert_mode('r2', 'mention')
        self.conn.push('msg_new', message=msg(msg_id=401, room_id='r2', sender='박민수', content='그냥 메시지'))
        self.assertEqual(notes, [])
        self.conn.push('msg_new', message=msg(msg_id=402, room_id='r2', sender='박민수', content='@홍길동 확인',
                                              mentions=['홍길동']))
        self.assertEqual(len(notes), 1)
        s.set_room_alert_mode('r2', 'off')
        self.assertTrue(s.is_muted('r2'))
        s.settings.set('alert_keywords', ['서버 장애'])
        self.conn.push('msg_new', message=msg(msg_id=403, room_id='r2', sender='박민수', content='지금 서버 장애 발생!'))
        self.assertEqual(len(notes), 2)                       # 알림 끈 방이어도 키워드는 울림
        self.assertEqual(s.keyword_hit(s.find_message('r2', 403)), '서버 장애')
        s.locked = True
        self.conn.push('msg_new', message=msg(msg_id=404, room_id='r1', sender='김철수', content='비밀 내용'))
        self.assertEqual(notes[-1][:2], ('KCS Talk', '새 메시지가 있습니다'))
        s.set_room_alert_mode('r2', 'all')
        self.assertFalse(s.is_muted('r2'))

    def test_calls_state_and_media_signal(self):
        s = self.state
        call = {'call_id': 7, 'room_id': 'r1', 'mode': 'video', 'host': '김철수', 'started_at': '',
                'participants': {'김철수': {'role': 'host', 'muted': False, 'video': True, 'screen': False,
                                         'hand': False}}}
        self.conn.push('call_updated', call=call)
        self.assertEqual(s.call_for_room('r1')['call_id'], 7)
        self.assertIsNone(s.my_call())
        media = self.collect(s.call_media)
        self.conn.push('call_media', call_id=7, **{'from': '김철수'}, kind='audio', seq=3, data_b64='AA==', codec='zpcm')
        self.assertEqual(media[0][:5], (7, '김철수', 'audio', 3, 'AA=='))
        self.assertEqual(media[0][5], {'codec': 'zpcm'})
        ended = self.collect(s.call_ended)
        self.conn.push('call_ended', call_id=7, room_id='r1', duration_seconds=65)
        self.assertIsNone(s.call_for_room('r1'))
        self.assertEqual(ended[0][0]['duration_seconds'], 65)
        s.start_call('r1', 'voiceroom')
        self.assertEqual(self.conn.last('call_start'), {'room_id': 'r1', 'mode': 'voiceroom'})
        s.set_call_state(7, muted=1)
        self.assertEqual(self.conn.last('call_state'), {'call_id': 7, 'muted': True})

    def test_stories(self):
        s = self.state
        st = {'story_id': 1, 'owner': '김철수', 'kind': 'text', 'content': '오늘 날씨 최고', 'bg_color': '#2A386C',
              'created_at': '2026-10-08T09:00:00', 'expires_at': '2026-10-09T09:00:00', 'viewers': []}
        self.conn.push('story_new', story=st)
        self.assertEqual(s.story_owners(), ['김철수'])
        self.assertTrue(s.has_unseen_story('김철수'))
        s.view_story(1)
        self.assertEqual(self.conn.last('story_view'), {'story_id': 1})
        self.assertFalse(s.has_unseen_story('김철수'))
        self.conn.push('story_deleted', story_id=1)
        self.assertEqual(s.story_owners(), [])

    def test_block_and_hide_filter_friends(self):
        s = self.state
        s.set_hidden('최지우', True)
        self.assertNotIn('최지우', [u['username'] for u in s.friends()])
        self.assertIn('최지우', [u['username'] for u in s.friends(include_hidden=True)])
        self.conn.push('block_list', blocked=['이영희'])
        self.assertTrue(s.is_blocked('이영희'))
        self.assertNotIn('이영희', [u['username'] for u in s.friends()])
        s.block_user('이영희', False)
        self.assertEqual(self.conn.last('block_set'), {'username': '이영희', 'blocked': False})

    def test_board_open_chat_drawer(self):
        s = self.state
        post = {'post_id': 5, 'room_id': 'r1', 'author': '김철수', 'title': '회의록', 'content': '내용',
                'created_at': '2026-10-08T10:00:00', 'comments': []}
        self.conn.push('board_updated', post=post)
        self.assertEqual([p['title'] for p in s.board_posts('r1')], ['회의록'])
        self.conn.push('board_deleted', post_id=5, room_id='r1')
        self.assertEqual(s.board_posts('r1'), [])
        found = self.collect(s.open_rooms_found)
        self.conn.push('open_room_search', rooms=[{'room_id': 'o1', 'name': '파이썬 모임'}])
        self.assertEqual(found[0][0][0]['name'], '파이썬 모임')
        drawer = self.collect(s.drawer_loaded)
        self.conn.push('drawer_result', kind='file', messages=[msg(kind='file')])
        self.assertEqual(drawer[0][0], 'file')
        room = dict(s.room('r1'), nicknames={'김철수': '철수닉'})
        self.conn.push('room_updated', room=room)
        self.assertEqual(s.member_name('r1', '김철수'), '철수닉')
        self.assertEqual(s.member_name('r2', '박민수'), '박민수')


if __name__ == '__main__':
    unittest.main()
