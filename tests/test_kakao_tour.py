# -*- coding: utf-8 -*-
"""
오픈채팅 다이얼로그 · 전체 톡서랍 · 기능 둘러보기 · 데모 시드 함수 테스트

    QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_kakao_tour -v
"""

import base64
import os
import shutil
import tempfile
import unittest
from unittest import mock

from tests.kakao_fakes import make_demo_state, app, iso

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget

from client.kakao import theme
from client.kakao.chats_tab import ChatsTab, OpenChatDialog, RoomRow, parse_tags
from client.kakao.drawer import TalkDrawerDialog, links_of
from client.kakao import feature_tour
from client.kakao.feature_tour import FeatureTourDialog, FEATURES, GROUPS

PNG_1PX = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==')


def pump(n=3):
    for _ in range(n):
        QApplication.processEvents()


def msg(msg_id, room_id, sender, kind, content='', **extra):
    m = dict(msg_id=msg_id, room_id=room_id, sender=sender, kind=kind, content=content,
             timestamp='2026-10-08T10:00:00', reply_to=None, mentions=[], reactions={}, deleted=False,
             attachment=None, event_id=None, poll=None, edited=False, edited_at=None, silent=False, link_preview=None)
    m.update(extra)
    return m


class TourTestBase(unittest.TestCase):
    def setUp(self):
        app()
        theme.set_dark(False)
        self.state, self.conn = make_demo_state()
        self.widgets = []

    def tearDown(self):
        for w in self.widgets:
            try:
                w.close()
                w.deleteLater()
            except RuntimeError:
                pass
        pump()

    def keep(self, w):
        self.widgets.append(w)
        return w


# ================================================================ 오픈채팅
class OpenChatTests(TourTestBase):
    ROOMS = [{'room_id': 'o1', 'name': '파이썬 개발자 모임', 'description': 'PyQt, 서버 이야기', 'tags': ['파이썬', '개발'],
              'member_count': 12},
             {'room_id': 'o2', 'name': '등산 동호회', 'description': '', 'tags': [], 'member_count': 3}]

    def test_initial_and_manual_search_requests(self):
        dlg = self.keep(OpenChatDialog(self.state))
        self.assertEqual(self.conn.last('open_room_search'), {'query': ''})
        dlg.search_edit.setText('파이썬')
        dlg.search_button.click()
        self.assertEqual(self.conn.last('open_room_search'), {'query': '파이썬'})

    def test_results_render_cards(self):
        dlg = self.keep(OpenChatDialog(self.state))
        self.conn.push('open_room_search', rooms=self.ROOMS)
        self.assertEqual(len(dlg.cards), 2)
        card = dlg.cards[0]
        self.assertEqual(card.name_label.text(), '파이썬 개발자 모임')
        self.assertEqual(card.count_label.text(), '12명')
        self.assertIn('#파이썬', card.tags_label.text())
        self.assertEqual(card.join_button.text(), '참여')
        self.assertTrue(dlg.empty_label.isHidden())
        self.conn.push('open_room_search', rooms=[])
        self.assertEqual(dlg.cards, [])
        self.assertFalse(dlg.empty_label.isHidden())

    def test_join_prompts_nickname_default_my_name(self):
        dlg = self.keep(OpenChatDialog(self.state))
        self.conn.push('open_room_search', rooms=self.ROOMS)
        with mock.patch('client.kakao.chats_tab.QInputDialog.getText', return_value=('길동이', True)) as ask:
            dlg.cards[0].join_button.click()
        self.assertEqual(ask.call_args[0][4], '홍길동')   # 기본값 = 내 이름
        self.assertEqual(self.conn.last('open_room_join'), {'room_id': 'o1', 'nickname': '길동이'})

    def test_join_cancel_sends_nothing(self):
        dlg = self.keep(OpenChatDialog(self.state))
        self.conn.push('open_room_search', rooms=self.ROOMS)
        with mock.patch('client.kakao.chats_tab.QInputDialog.getText', return_value=('', False)):
            self.assertFalse(dlg.join('o1'))
        self.assertIsNone(self.conn.last('open_room_join'))

    def test_joined_room_opens_instead(self):
        dlg = self.keep(OpenChatDialog(self.state))
        self.conn.push('open_room_search', rooms=[{'room_id': 'r1', 'name': '프로젝트 팀', 'member_count': 3}])
        self.assertEqual(dlg.cards[0].join_button.text(), '열기')
        opened = []
        self.state.room_opened.connect(opened.append)
        dlg.join('r1')
        self.assertEqual(opened, ['r1'])
        self.assertIsNone(self.conn.last('open_room_join'))

    def test_create_request(self):
        dlg = self.keep(OpenChatDialog(self.state))
        self.assertFalse(dlg.create_button.isEnabled())
        dlg.name_edit.setText(' 주말 러닝 ')
        dlg.desc_edit.setPlainText('한강에서 같이 뛰어요')
        dlg.tags_edit.setText('#러닝, 운동,러닝, 한강')
        self.assertTrue(dlg.create_button.isEnabled())
        dlg.create_button.click()
        self.assertEqual(self.conn.last('open_room_create'),
                         {'name': '주말 러닝', 'description': '한강에서 같이 뛰어요', 'tags': ['러닝', '운동', '한강']})
        self.assertEqual(parse_tags(''), [])

    def test_open_room_in_list_with_badge_and_header_buttons(self):
        tab = self.keep(ChatsTab(self.state, self.state.settings))
        self.conn.push('room_updated', room={'room_id': 'o9', 'type': 'open', 'name': '오픈방', 'members': ['홍길동', '김철수'],
                                             'created_at': iso(__import__('datetime').datetime.now()), 'notice': None,
                                             'last_message': None, 'read_pointers': {}, 'unread_count': 0,
                                             'description': '', 'tags': [], 'nicknames': {'홍길동': '길동'}})
        self.assertIn('o9', tab.room_ids())
        row = tab.list.itemWidget(tab.list.find_data('o9'))
        self.assertIsInstance(row, RoomRow)
        self.assertIsNotNone(row.open_badge)
        self.assertEqual(row.open_badge.text(), '오픈')
        self.assertIsNone(tab.list.itemWidget(tab.list.find_data('r1')).open_badge)
        self.assertEqual(self.state.member_name('o9', '홍길동'), '길동')
        dlg = self.keep(tab.show_open_chat_dialog(modal=False))
        self.assertIsInstance(dlg, OpenChatDialog)
        drawer = self.keep(tab.show_talk_drawer())
        self.assertIsInstance(drawer, TalkDrawerDialog)


# ================================================================ 톡서랍
class TalkDrawerTests(TourTestBase):
    def push_results(self):
        self.conn.push('drawer_result', kind='image', messages=[
            msg(101, 'r1', '김철수', 'image', 'a.png', attachment={'attachment_id': 50, 'name': 'a.png', 'mime': 'image/png', 'size': 70}),
            msg(102, 'r2', '박민수', 'image', 'b.png', attachment={'attachment_id': 51, 'name': 'b.png', 'mime': 'image/png', 'size': 70})])
        self.conn.push('drawer_result', kind='file', messages=[
            msg(103, 'r1', '김철수', 'file', '회의자료.pdf', attachment={'attachment_id': 52, 'name': '회의자료.pdf', 'mime': 'application/pdf', 'size': 248000}),
            msg(104, 'r2', '박민수', 'file', 'old.zip', attachment={'attachment_id': 53, 'name': 'old.zip', 'mime': 'application/zip', 'size': 10, 'expired': True})])
        self.conn.push('drawer_result', kind='link', messages=[
            msg(105, 'r1', '홍길동', 'text', '자료 https://example.com/docs 와 https://kcins.co.kr 참고',
                link_preview={'url': 'https://example.com/docs', 'title': '예제 문서', 'description': '', 'site': 'example'})])

    def test_requests_all_kinds(self):
        self.keep(TalkDrawerDialog(self.state))
        kinds = [p['kind'] for t, p in self.conn.sent if t == 'drawer_query']
        self.assertEqual(kinds, ['image', 'file', 'link'])

    def test_renders_results_and_thumbnails(self):
        dlg = self.keep(TalkDrawerDialog(self.state))
        self.assertEqual(dlg.stacks['image'].currentIndex(), 0)   # 불러오는 중
        self.conn.sent.clear()
        self.push_results()
        self.assertEqual(dlg.photos.count(), 2)
        self.assertEqual(dlg.files.count(), 2)
        self.assertEqual(dlg.links.count(), 2)
        self.assertEqual(dlg.tabs.tabText(0), '사진 2')
        self.assertEqual(sorted(p['attachment_id'] for t, p in self.conn.sent if t == 'attachment_get'), [50, 51])
        self.conn.push('attachment_data', attachment_id=50, name='a.png', mime='image/png',
                       data_b64=base64.b64encode(PNG_1PX).decode())
        self.assertTrue(dlg.thumbnail_loaded(50))
        self.assertFalse(dlg.thumbnail_loaded(51))
        row = dlg.files.itemWidget(dlg.files.item(0))
        self.assertEqual(row.name_label.text(), '회의자료.pdf')
        self.assertIn('프로젝트 팀', row.meta_label.text())
        expired = dlg.files.itemWidget(dlg.files.item(1))
        self.assertFalse(expired.save_button.isEnabled())
        link = dlg.links.itemWidget(dlg.links.item(0))
        self.assertEqual(link.title_label.text(), '예제 문서')
        self.assertEqual(dlg.links.item(1).data(Qt.UserRole + 1), 'https://kcins.co.kr')

    def test_empty_result(self):
        dlg = self.keep(TalkDrawerDialog(self.state))
        self.conn.push('drawer_result', kind='file', messages=[])
        self.assertEqual(dlg.stacks['file'].currentIndex(), 0)
        self.assertIn('없습니다', dlg.empty_labels['file'].text())

    def test_save_file_requests_then_writes(self):
        dlg = self.keep(TalkDrawerDialog(self.state))
        self.push_results()
        path = os.path.join(tempfile.mkdtemp(), 'out.pdf')
        self.conn.sent.clear()
        self.assertTrue(dlg.save_file(dlg.files.item(0).data(Qt.UserRole), path))
        self.assertEqual(self.conn.last('attachment_get'), {'attachment_id': 52})
        self.conn.push('attachment_data', attachment_id=52, name='회의자료.pdf', mime='application/pdf',
                       data_b64=base64.b64encode(b'%PDF-1').decode())
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), b'%PDF-1')
        self.assertFalse(dlg.save_file(dlg.files.item(1).data(Qt.UserRole), path))   # 만료

    def test_open_link_and_show_in_room(self):
        mw = FakeMainWindow()
        dlg = self.keep(TalkDrawerDialog(self.state, main_window=mw))
        self.push_results()
        with mock.patch('client.kakao.drawer.QDesktopServices.openUrl') as open_url:
            dlg.links.itemWidget(dlg.links.item(0)).open_button.click()
        self.assertEqual(open_url.call_args[0][0].toString(), 'https://example.com/docs')
        dlg.files.itemDoubleClicked.emit(dlg.files.item(0))
        self.assertEqual(mw.calls[-1], ('focus_message', 'r1', 103))
        menu = dlg.menu_for('link', dlg.links.item(0))
        self.assertEqual([a.text() for a in menu.actions()], ['채팅방에서 보기', '브라우저에서 열기'])
        self.assertEqual(links_of({'content': 'x http://a.b/c.', 'link_preview': None}), ['http://a.b/c'])


# ================================================================ 기능 둘러보기
class FakeRoomWindow:
    def __init__(self, rid, log):
        self.room_id, self.log = rid, log

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return lambda *args: self.log.append(('room.' + name, self.room_id) + args)


class FakeTab:
    def __init__(self, key, log):
        self.key, self.log = key, log

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError(name)
        return lambda *args: self.log.append(('tab.' + name, self.key) + args)


class FakeMainWindow:
    """MainWindow 흉내: set_tab / open_room / focus_message / lock / tabs"""

    def __init__(self):
        self.calls = []
        self.tabs = {k: FakeTab(k, self.calls) for k in ('friends', 'chats', 'org', 'calendar', 'more')}

    def set_tab(self, key):
        self.calls.append(('set_tab', key))

    def open_room(self, rid):
        self.calls.append(('open_room', rid))
        return FakeRoomWindow(rid, self.calls)

    def focus_message(self, rid, mid):
        self.calls.append(('focus_message', rid, mid))

    def lock(self):
        self.calls.append(('lock',))


class FeatureTourTests(TourTestBase):
    def setUp(self):
        super().setUp()
        self._vpath = tempfile.mkdtemp()
        patcher = mock.patch.object(feature_tour, 'VERIFICATION_PATH', os.path.join(self._vpath, 'none.md'))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self._vpath, True)
        self.mw = FakeMainWindow()

    def make(self):
        return self.keep(FeatureTourDialog(self.state, self.state.settings, self.mw))

    def test_lists_at_least_40_grouped_features(self):
        dlg = self.make()
        self.assertGreaterEqual(len(dlg.feature_keys()), 40)
        self.assertEqual(len(set(f[0] for f in FEATURES)), len(FEATURES))
        self.assertEqual(set(dlg.headers), {f[1] for f in FEATURES})
        self.assertTrue(set(dlg.headers) <= set(GROUPS))
        names = ' '.join(f[2] for f in FEATURES)
        for word in ('오픈채팅', '톡서랍', '비밀채팅', '보이스톡', '펑', '사다리', '게시판', '멀티프로필', '잠금',
                     '메시지 수정', '조용히', '폴더', '브리핑', '조직도', '투표', '할 일'):
            self.assertIn(word, names)
        self.assertNotIn('번역', names)   # 범위 제외 (사용자 요청)

    def test_search_filters_rows_and_groups(self):
        dlg = self.make()
        dlg.search_edit.setText('투표')
        self.assertEqual(dlg.visible_keys(), ['poll'])
        self.assertFalse(dlg.headers['채팅방 기능'].isHidden())
        self.assertTrue(dlg.headers['친구·프로필'].isHidden())
        dlg.search_edit.setText('없는기능xyz')
        self.assertEqual(dlg.visible_keys(), [])
        self.assertFalse(dlg.no_match.isHidden())
        dlg.search_edit.setText('')
        self.assertEqual(len(dlg.visible_keys()), len(FEATURES))

    def test_every_try_handler_runs_without_exceptions(self):
        dlg = self.make()
        settings = self.state.settings
        dark, social = settings.get('dark_mode'), settings.get('social_features')
        for key in dlg.feature_keys():
            with mock.patch.object(dlg, 'explain', wraps=dlg.explain):
                message = dlg.try_feature(key)
            self.assertTrue(message, key)
            self.assertNotIn('열지 못했습니다', message, key)
            pump()
            self.assertNotIn('실행 중 오류', dlg.last_message, key)
        # 실제 동작 확인
        self.assertIn(('set_tab', 'calendar'), self.mw.calls)
        self.assertIn(('tab.set_section', 'calendar', 1), self.mw.calls)
        self.assertIn(('room.open_poll_dialog', 'r1'), self.mw.calls)
        self.assertIn(('room.open_drawer', 'r1'), self.mw.calls)
        self.assertEqual(self.conn.last('room_open_secret'), {'target': '김철수'})
        self.assertIn(('room_open_direct', {'target': 'AI 비서'}), self.conn.sent)
        self.assertEqual(self.conn.last('open_room_search'), {'query': ''})
        self.assertIn('drawer_query', [t for t, _p in self.conn.sent])
        # 다크 모드 / 테마 토글은 한 번씩 바뀌었다
        self.assertNotEqual(settings.get('dark_mode'), dark)
        self.assertNotEqual(settings.get('social_features'), social)   # '소식 기능' 항목이 켜고 끈다
        settings.set('dark_mode', dark)
        settings.set('social_features', social)
        theme.set_dark(False)
        theme.set_brand('kcs')
        # 해본 기능은 체크되고 설정에 저장된다
        self.assertEqual(dlg.progress_label.text(), f'{len(FEATURES)} / {len(FEATURES)} 해봄')
        self.assertEqual(len(settings.get('tour_checked')), len(FEATURES))
        dlg.done(0)

    def test_room_message_actions_start_composer(self):
        dlg = self.make()
        dlg.try_feature('reply')
        dlg.try_feature('edit')
        from PyQt5.QtTest import QTest
        QTest.qWait(400)
        replies = [c for c in self.mw.calls if c[0] == 'room.start_reply']
        self.assertEqual(replies[0][2]['msg_id'], 11)        # 김철수의 마지막 텍스트
        edits = [c for c in self.mw.calls if c[0] == 'room.start_edit']
        self.assertEqual(edits[0][2]['msg_id'], 4)           # 24시간 안에 내가 보낸 마지막 텍스트

    def test_works_without_main_window(self):
        dlg = self.keep(FeatureTourDialog(self.state, self.state.settings, None))
        opened = []
        self.state.room_opened.connect(opened.append)
        self.assertIn('메인 창이 없어', dlg.try_feature('calendar'))
        dlg.try_feature('poll')
        self.assertEqual(opened, ['r1'])

    def test_verification_tab_reads_results(self):
        path = os.path.join(self._vpath, 'v.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('# 기능 검증 결과\n\n| 영역 | 기능 | 결과 | 테스트 |\n|---|---|---|---|\n'
                    '| 채팅방 기능 | 투표 | ✅ PASS | 3/3 |\n| 메시지 | 답장 | ❌ FAIL | 1/2 |\n')
        with mock.patch.object(feature_tour, 'VERIFICATION_PATH', path):
            dlg = self.make()
        self.assertEqual(dlg.rows['poll'].verdict_label.text(), '검증 ✓')
        self.assertEqual(dlg.rows['reply'].verdict_label.text(), '검증 ✗')
        self.assertTrue(dlg.rows['folders'].verdict_label.isHidden())
        self.assertIn('2개 중 1개 통과', dlg.verify_hint.text())
        self.assertIn('기능 검증 결과', dlg.verify_view.toPlainText())

    def test_missing_verification_shows_hint(self):
        dlg = self.make()
        self.assertIn('verify_features.py', dlg.verify_view.toPlainText())

    def test_dark_theme_renders(self):
        theme.set_dark(True)
        try:
            dlg = self.make()
            dlg.resize(600, 700)
            self.assertFalse(dlg.grab().isNull())
        finally:
            theme.set_dark(False)


# ================================================================ 데모 시드 (서버를 스레드로 실행, 프로세스 없음)
class DemoSeedTests(unittest.TestCase):
    def test_settings_and_db_preparation(self):
        from scripts import demo
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        org_dir = os.path.join(tmp, 'src')
        os.makedirs(org_dir)
        with open(os.path.join(org_dir, 'org.json'), 'w', encoding='utf-8') as f:
            f.write('{"version": 2, "users": [{"username": "갑"}, {"username": "을"}, {"username": "AI 비서"}]}')
        db_dir = demo.prepare_db_dir(os.path.join(tmp, 'db'), org_source=os.path.join(org_dir, 'org.json'))
        self.assertTrue(os.path.exists(os.path.join(db_dir, 'org.json')))
        self.assertEqual(demo.default_users(os.path.join(org_dir, 'org.json'), 3), ['갑', '을'])
        self.assertEqual(demo.default_users(os.path.join(tmp, 'none.json'), 2), ['홍길동', '김철수'])
        path = demo.write_client_settings(os.path.join(tmp, 'home'), '갑', [{'name': '업무', 'room_ids': ['x']}],
                                          pinned=['x'])
        import json
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['chat_folders'], [{'name': '업무', 'room_ids': ['x']}])
        self.assertEqual(data['pinned_rooms'], ['x'])

    def test_seed_against_threaded_server(self):
        os.environ['KCS_LINK_PREVIEW'] = 'off'
        from scripts import demo
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch.dict(os.environ, {'KCS_MESSENGER_HOME': os.path.join(tmp, 'home', '.kcs_messenger')}):
            server = demo.start_server(os.path.join(tmp, 'db', 'kakao.db'), port=0, rag_off=True)
            try:
                users = ['홍길동', '김철수', '이영희']
                report = demo.seed(server.port, users, home=os.path.join(tmp, 'home'), quiet=True)
                checks = demo.verify(server.port, users, report, home=os.path.join(tmp, 'home'))
            finally:
                server.stop()
        by_name = {c.name: c for c in checks}
        # v2까지(서버에 이미 있는 기능)는 반드시 통과해야 한다
        for name in ('그룹 채팅', '텍스트 메시지', '메시지 수정', '조용히 보내기', '답장', '공감', '투표', '일정 공유',
                     '사진', '파일', '링크', '공지', '할 일', '채팅방 폴더', '오늘의 브리핑'):
            self.assertTrue(by_name[name].ok, f'{name}: {by_name[name].detail}')
        # 모든 항목은 결과(ok/실패 사유)를 갖는다 - 예외로 중단되지 않음
        self.assertTrue(all(isinstance(c.detail, str) for c in checks))
        self.assertGreaterEqual(len(checks), 20)


if __name__ == '__main__':
    unittest.main()
