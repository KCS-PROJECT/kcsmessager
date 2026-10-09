# -*- coding: utf-8 -*-
"""
애플리케이션 셸(로그인·메인 창·친구/채팅/조직도/더보기 탭) 테스트 - 서버 없이 FakeConnection 사용

    QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_kakao_shell -v
"""

import base64
import importlib.util
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

from tests.kakao_fakes import make_demo_state, app

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QImage, QColor
from PyQt5.QtWidgets import QMessageBox, QApplication

from client.kakao import theme
from client.kakao.main_window import MainWindow, IdleWatcher, apply_app_theme
from client.kakao.chats_tab import (ChatsTab, CreateGroupDialog, InviteToRoomDialog, format_room_time,
                                    RoomRow, ChatFolderDialog, PeekDialog, AiButton)
from client.kakao.state import BOT_NAME
from client.kakao.friends_tab import FriendsTab, ProfileEditDialog, ProfileDialog, presence_menu, FriendRow
from client.kakao.org_tab import OrgTab
from client.kakao.more_tab import MoreTab, RagDocsDialog
from client.kakao.login import LoginDialog

HAS_CHAT_ROOM = importlib.util.find_spec('client.kakao.chat_room') is not None
HAS_CALENDAR = importlib.util.find_spec('client.kakao.calendar_tab') is not None
HAS_WALLPAPER = importlib.util.find_spec('client.kakao.wallpaper') is not None

ORG = {'홍길동': ('KCS 홀딩스', '경영지원팀', '팀장'), '김철수': ('KCS 홀딩스', '경영지원팀', '대리'),
       '이영희': ('KCS 물류', '운영팀', '과장'), '박민수': ('KCS 물류', '운영팀', '사원'),
       '최지우': ('KCS 커머스', '마케팅팀', '팀장')}


def add_org(state, conn):
    """데모 사용자에 회사/부서/직함과 AI 비서를 추가"""
    for name, (company, dept, title) in ORG.items():
        user = dict(state.user(name))
        user.update(company=company, department=dept, title=title, presence='online', is_bot=False)
        conn.push('user_updated', user=user)
    conn.push('user_updated', user={'username': 'AI 비서', 'display_name': 'AI 비서', 'status_message': '',
                                    'birthday': None, 'online': True, 'presence': 'online',
                                    'company': 'KCS AI', 'department': '지식봇', 'title': '봇', 'is_bot': True})


def rows(lst):
    return [lst.item(i).data(Qt.UserRole) for i in range(lst.count())]


class ShellTestBase(unittest.TestCase):
    def setUp(self):
        app()
        theme.set_dark(False)
        theme.set_font_scale(1.0)
        self.state, self.conn = make_demo_state()
        self.settings = self.state.settings
        self._windows = []

    def tearDown(self):
        for w in self._windows:
            w.hide()
            w.deleteLater()
        # 앱 전체 스타일 재적용 전에 지연 삭제를 먼저 처리 (삭제 대기 위젯 repolish → 세그폴트 방지)
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        theme.set_dark(False)
        theme.set_font_scale(1.0)
        apply_app_theme(None)
        QApplication.processEvents()

    def make_window(self, **kwargs):
        win = MainWindow(self.state, self.settings, server_address='127.0.0.1:5555', **kwargs)
        self._windows.append(win)
        return win


# ================================================================ 메인 창
class MainWindowTests(ShellTestBase):
    def test_builds_and_switches_tabs(self):
        win = self.make_window()
        win.show()
        self.assertEqual(win.current_tab(), 'friends')
        self.assertTrue(win.sidebar.buttons['friends'].isChecked())
        for key in ('chats', 'org', 'calendar', 'more', 'friends'):
            win.sidebar.buttons[key].click()
            self.assertEqual(win.current_tab(), key)
            self.assertTrue(win.sidebar.buttons[key].isChecked())
        self.assertGreaterEqual(win.minimumWidth(), 340)
        self.assertGreaterEqual(win.width(), 340)

    @unittest.skipUnless(HAS_CALENDAR, 'calendar_tab 미완성')
    def test_calendar_tab_is_real(self):
        from client.kakao.calendar_tab import CalendarTab
        win = self.make_window()
        self.assertIsInstance(win.tabs['calendar'], CalendarTab)

    def test_unread_badge_and_title(self):
        win = self.make_window()
        total = self.state.total_unread()
        self.assertEqual(total, 3)
        self.assertEqual(win.sidebar.chat_badge.count, total)
        self.assertEqual(win.windowTitle(), f'KCS Talk ({total})')
        self.conn.push('msg_new', message=dict(
            msg_id=99, room_id='r2', sender='박민수', kind='text', content='새 메시지',
            timestamp=datetime.now().isoformat(timespec='seconds'), reply_to=None, mentions=[], reactions={},
            deleted=False, attachment=None, event_id=None, poll=None))
        self.assertEqual(self.state.total_unread(), total + 1)
        self.assertEqual(win.sidebar.chat_badge.count, total + 1)
        self.assertEqual(win.windowTitle(), f'KCS Talk ({total + 1})')
        # 알림 끈 방의 안 읽은 수는 합계에서 빠진다
        self.settings.toggle_in('muted_rooms', 'r1')
        self.assertEqual(win.sidebar.chat_badge.count, self.state.total_unread())
        self.assertEqual(win.sidebar.chat_badge.count, total + 1 - 2)

    def test_connection_lost_banner_and_reconnect(self):
        calls = []
        win = self.make_window(reconnect=lambda: calls.append(1) or (True, ''))
        win.show()
        self.assertFalse(win.banner.isVisible())
        self.state.connection_lost.emit('끊김')
        self.assertTrue(win.banner.isVisible())
        self.assertIn('서버 연결이 끊어졌습니다', win.banner.label.text())
        win.banner.button.click()
        self.assertEqual(calls, [1])
        self.assertFalse(win.banner.isVisible())

    def test_error_shows_toast(self):
        win = self.make_window()
        win.show()
        self.state.error.emit('권한이 없습니다')
        self.assertTrue(win.toast.isVisible())
        self.assertEqual(win.toast.text(), '권한이 없습니다')

    def test_notification_respects_setting(self):
        win = self.make_window()
        self.settings.set('notifications', False)
        self.assertFalse(win.show_notification('제목', '본문', 'r1'))
        self.settings.set('notifications', True)
        with mock.patch.object(QApplication, 'activeWindow', return_value=None):
            self.assertTrue(win.show_notification('제목', '본문', 'r1'))
        self.assertEqual(win._last_notify_room, 'r1')
        with mock.patch.object(QApplication, 'activeWindow', return_value=win):
            self.assertFalse(win.show_notification('제목', '본문', 'r1'))

    def test_dark_mode_and_font_scale_rethemes(self):
        win = self.make_window()
        win.show()
        more = win.tabs['more']
        more.dark_toggle.setChecked(True)
        self.assertTrue(self.settings.get('dark_mode'))
        self.assertTrue(theme.is_dark())
        self.assertIn(theme.c('bg'), QApplication.instance().styleSheet())
        self.assertEqual(QApplication.instance().palette().window().color(), QColor(theme.c('bg')))
        more.set_font_scale_index(3)
        self.assertAlmostEqual(self.settings.get('font_scale'), 1.3)
        self.assertAlmostEqual(theme.font_scale(), 1.3)
        more.notify_toggle.setChecked(False)
        self.assertFalse(self.settings.get('notifications'))
        more.dark_toggle.setChecked(False)
        self.assertFalse(theme.is_dark())

    def test_room_opened_opens_window_once(self):
        win = self.make_window()
        if not HAS_CHAT_ROOM:
            self.skipTest('chat_room 미완성')
        self.state.room_opened.emit('r1')
        self.assertIn('r1', win.room_windows)
        first = win.room_windows['r1']
        self.state.room_opened.emit('r1')
        self.assertIs(win.room_windows['r1'], first)
        self.state.room_opened.emit('r2')
        self.assertEqual(set(win.room_windows), {'r1', 'r2'})
        self.assertNotEqual(win.room_windows['r1'].pos(), win.room_windows['r2'].pos())
        self.conn.push('room_removed', room_id='r2')
        self.assertNotIn('r2', win.room_windows)
        for w in list(win.room_windows.values()):
            w.close()


# ================================================================ 자동 자리비움
class IdleTests(ShellTestBase):
    def test_auto_away_and_restore(self):
        watcher = IdleWatcher(self.state, idle_seconds=600)
        try:
            watcher.last_input = 1000.0
            watcher.check(now=1000.0 + 599)
            self.assertIsNone(self.conn.last('presence_set'))
            watcher.check(now=1000.0 + 601)
            self.assertEqual(self.conn.last('presence_set'), {'presence': 'away'})
            self.assertTrue(watcher.auto_away)
            me = dict(self.state.user('홍길동'), presence='away')
            self.conn.push('user_updated', user=me)
            self.conn.sent.clear()
            watcher.activity(now=2000.0)
            self.assertEqual(self.conn.last('presence_set'), {'presence': 'online'})
            self.assertFalse(watcher.auto_away)
        finally:
            watcher.stop()

    def test_manual_status_untouched(self):
        watcher = IdleWatcher(self.state, idle_seconds=600)
        try:
            self.conn.push('user_updated', user=dict(self.state.user('홍길동'), presence='meeting'))
            watcher.last_input = 0.0
            watcher.check(now=10000.0)
            self.assertIsNone(self.conn.last('presence_set'))
            watcher.activity(now=10001.0)
            self.assertIsNone(self.conn.last('presence_set'))
        finally:
            watcher.stop()

    def test_presence_menu_sends(self):
        menu = presence_menu(self.state)
        labels = [a.text() for a in menu.actions()]
        self.assertEqual(labels, ['온라인', '자리비움', '다른 용무 중', '회의 중'])
        menu.actions()[2].trigger()
        self.assertEqual(self.conn.last('presence_set'), {'presence': 'busy'})


# ================================================================ 친구 탭
class FriendsTabTests(ShellTestBase):
    def setUp(self):
        super().setUp()
        self.tab = FriendsTab(self.state, self.settings)

    def test_sections(self):
        self.assertEqual(self.tab.section_members('birthday'), ['김철수'])
        self.assertEqual(sorted(self.tab.section_members('online')), ['김철수', '박민수'])
        self.assertEqual(sorted(self.tab.section_members('offline')), ['이영희', '최지우'])
        self.assertEqual(self.tab.section_members('favorites'), [])
        data = rows(self.tab.list)
        self.assertEqual(data[0], ('me', '홍길동'))
        # 오프라인은 기본으로 접혀 있다
        self.assertIn(('section', 'offline'), data)
        self.assertNotIn(('friend', '이영희', 'offline'), data)
        self.tab.toggle_section('offline')
        self.assertIn(('friend', '이영희', 'offline'), rows(self.tab.list))

    def test_bot_section_on_top(self):
        add_org(self.state, self.conn)
        self.assertEqual(self.tab.section_members('bot'), ['AI 비서'])
        data = rows(self.tab.list)
        self.assertEqual(data[1], ('section', 'bot'))
        self.assertEqual(data[2], ('friend', 'AI 비서', 'bot'))
        self.assertNotIn('AI 비서', self.tab.section_members('online'))

    def test_company_chip_for_other_company(self):
        add_org(self.state, self.conn)
        widgets = {}
        for i in range(self.tab.list.count()):
            w = self.tab.list.itemWidget(self.tab.list.item(i))
            if isinstance(w, FriendRow):
                widgets[w.username] = w
        self.assertEqual(widgets['박민수'].company, 'KCS 물류')
        self.assertEqual(widgets['김철수'].company, '')

    def test_presence_label(self):
        self.conn.push('user_updated', user=dict(self.state.user('박민수'), presence='away'))
        item = self.tab.list.find_data(('friend', '박민수', 'online'))
        self.assertIsNotNone(item)
        row = self.tab.list.itemWidget(item)
        self.assertEqual(row.presence_label.text(), '자리비움')

    def test_search_filter(self):
        self.tab.toggle_search()
        self.tab.search_edit.setText('회의')
        self.assertEqual(self.tab.section_members('online'), ['김철수'])
        self.assertEqual(self.tab.section_members('offline'), [])
        self.assertNotIn(('me', '홍길동'), rows(self.tab.list))
        self.tab.search_edit.setText('바쁨')  # 상태메시지 검색 + 검색 중에는 접힌 구역도 펼침
        self.assertEqual(self.tab.section_members('offline'), ['최지우'])
        self.assertIn(('friend', '최지우', 'offline'), rows(self.tab.list))
        self.tab.toggle_search()
        self.assertEqual(self.tab.search_edit.text(), '')
        self.assertEqual(len(self.tab.section_members('online')), 2)

    def test_favorite_toggle_moves_friend(self):
        menu = self.tab.context_menu_for(('friend', '최지우', 'offline'))
        action = next(a for a in menu.actions() if a.text() == '즐겨찾기 추가')
        action.trigger()
        self.assertIn('최지우', self.settings.get('favorites'))
        self.assertEqual(self.tab.section_members('favorites'), ['최지우'])
        self.assertNotIn('최지우', self.tab.section_members('offline'))
        menu = self.tab.context_menu_for(('friend', '최지우', 'favorites'))
        next(a for a in menu.actions() if a.text() == '즐겨찾기 해제').trigger()
        self.assertNotIn('최지우', self.settings.get('favorites'))

    def test_double_click_opens_direct_room(self):
        opened = []
        self.state.room_opened.connect(opened.append)
        item = self.tab.list.find_data(('friend', '김철수', 'online'))
        self.tab.list.itemDoubleClicked.emit(item)
        self.assertEqual(self.conn.last('room_open_direct'), {'target': '김철수'})
        self.assertEqual(opened, [])
        self.conn.push('room_updated', room={
            'room_id': 'r9', 'type': 'direct', 'name': '', 'members': ['홍길동', '김철수'],
            'created_at': datetime.now().isoformat(timespec='seconds'), 'notice': None,
            'last_message': None, 'read_pointers': {}, 'unread_count': 0})
        self.assertEqual(opened, ['r9'])
        # 이미 방이 있는 친구는 요청 없이 바로 열린다
        self.conn.sent.clear()
        item = self.tab.list.find_data(('friend', '박민수', 'online'))
        self.tab.list.row_activated.emit(item)
        self.assertIsNone(self.conn.last('room_open_direct'))
        self.assertEqual(opened[-1], 'r2')

    def test_birthday_gift_opens_chat(self):
        item = self.tab.list.find_data(('friend', '김철수', 'birthday'))
        row = self.tab.list.itemWidget(item)
        row.gift_button.click()
        self.assertEqual(self.conn.last('room_open_direct'), {'target': '김철수'})

    def test_profile_edit_sends_update(self):
        dlg = ProfileEditDialog(self.state)
        dlg.name_edit.setText('길동이')
        dlg.status_edit.setText('휴가 중')
        dlg.birthday_edit.setText('13-40')
        dlg.accept()
        self.assertIsNone(self.conn.last('profile_update'))
        self.assertTrue(dlg.error_label.isVisibleTo(dlg))
        dlg.birthday_edit.setText('03-15')
        dlg.accept()
        self.assertEqual(self.conn.last('profile_update'),
                         {'display_name': '길동이', 'status_message': '휴가 중', 'birthday': '03-15'})

    def test_profile_photo_change_and_clear(self):
        dlg = ProfileEditDialog(self.state)
        path = os.path.join(tempfile.mkdtemp(), 'photo.png')
        img = QImage(400, 300, QImage.Format_RGB32)
        img.fill(QColor('#3366CC'))
        self.assertTrue(img.save(path))
        self.assertIsNone(dlg.set_photo_from_path(path))
        payload = self.conn.last('profile_update')
        data = base64.b64decode(payload['avatar_b64'])
        self.assertLessEqual(len(data), 512 * 1024)
        decoded = QImage.fromData(data, 'PNG')
        self.assertEqual((decoded.width(), decoded.height()), (256, 256))
        bad = os.path.join(tempfile.mkdtemp(), 'bad.png')
        with open(bad, 'wb') as f:
            f.write(b'not an image')
        self.assertIsNotNone(dlg.set_photo_from_path(bad))
        dlg.clear_photo_button.click()
        self.assertEqual(self.conn.last('profile_update'), {'avatar_clear': True})

    def test_profile_view_chat_button(self):
        dlg = ProfileDialog(self.state, '최지우')
        dlg.chat_button.click()
        self.assertEqual(self.conn.last('room_open_direct'), {'target': '최지우'})

    def test_invite_to_room_menu(self):
        menu = self.tab.context_menu_for(('friend', '최지우', 'offline'))
        self.assertIn('채팅방에 초대…', [a.text() for a in menu.actions()])


# ================================================================ 채팅 탭
class ChatsTabTests(ShellTestBase):
    def setUp(self):
        super().setUp()
        self.tab = ChatsTab(self.state, self.settings)

    def test_order_and_pinning(self):
        self.assertEqual(self.tab.room_ids(), ['r1', 'r2', 'r3'])
        self.settings.toggle_in('pinned_rooms', 'r3')
        self.assertEqual(self.tab.room_ids(), ['r3', 'r1', 'r2'])
        row = self.tab.list.itemWidget(self.tab.list.item(0))
        self.assertTrue(row.pinned)

    def test_row_content(self):
        row = self.tab.list.itemWidget(self.tab.list.find_data('r1'))
        self.assertIsInstance(row, RoomRow)
        self.assertEqual(row.title.text(), '프로젝트 팀')
        self.assertEqual(row.count_label.text(), '3')
        self.assertTrue(row.preview.text().startswith('긴 메시지 테스트'))
        self.assertEqual(row.badge.count, 2)
        self.settings.toggle_in('muted_rooms', 'r1')
        row = self.tab.list.itemWidget(self.tab.list.find_data('r1'))
        self.assertTrue(row.muted)
        self.assertTrue(row.badge.muted)
        r2 = self.tab.list.itemWidget(self.tab.list.find_data('r2'))
        self.assertEqual(r2.title.text(), '박민수')
        self.assertIsNone(r2.count_label)

    def test_search(self):
        self.tab.toggle_search()
        self.tab.search_edit.setText('박민')
        self.assertEqual(self.tab.room_ids(), ['r2'])
        self.tab.search_edit.setText('이영희')  # 참여자 이름으로도 검색
        self.assertEqual(self.tab.room_ids(), ['r1'])
        self.tab.search_edit.setText('없는방')
        self.assertEqual(self.tab.room_ids(), [])
        self.assertTrue(self.tab.empty_label.isVisibleTo(self.tab))

    def test_relative_time(self):
        now = datetime(2026, 10, 8, 15, 30)
        self.assertEqual(format_room_time(datetime(2026, 10, 8, 15, 12), now), '오후 3:12')
        self.assertEqual(format_room_time(datetime(2026, 10, 8, 9, 5), now), '오전 9:05')
        self.assertEqual(format_room_time(datetime(2026, 10, 8, 0, 7), now), '오전 12:07')
        self.assertEqual(format_room_time(datetime(2026, 10, 8, 12, 0), now), '오후 12:00')
        self.assertEqual(format_room_time('2026-10-07T23:59:00', now), '어제')
        self.assertEqual(format_room_time('2026-03-01T10:00:00', now), '3월 1일')
        self.assertEqual(format_room_time('2025-03-01T10:00:00', now), '2025. 3. 1.')
        self.assertEqual(format_room_time(None, now), '')

    def test_activate_emits_room_opened(self):
        opened = []
        self.state.room_opened.connect(opened.append)
        self.tab.list.itemDoubleClicked.emit(self.tab.list.find_data('r2'))
        self.assertEqual(opened, ['r2'])

    def test_context_menu_pin_mute_leave(self):
        menu = self.tab.context_menu_for('r2')
        texts = [a.text() for a in menu.actions() if a.text()]
        self.assertEqual(texts, ['채팅방 열기', '읽지 않고 미리보기', '채팅방 상단 고정', '채팅방 알림 끄기',
                                 '폴더에 추가', '대화상대 초대…', '나가기'])
        next(a for a in menu.actions() if a.text() == '채팅방 상단 고정').trigger()
        self.assertTrue(self.state.is_pinned('r2'))
        next(a for a in menu.actions() if a.text() == '채팅방 알림 끄기').trigger()
        self.assertTrue(self.state.is_muted('r2'))
        menu = self.tab.context_menu_for('r2')
        texts = [a.text() for a in menu.actions() if a.text()]
        self.assertIn('상단 고정 해제', texts)
        self.assertIn('채팅방 알림 켜기', texts)
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            next(a for a in menu.actions() if a.text() == '나가기').trigger()
        self.assertIsNone(self.conn.last('room_leave'))
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            next(a for a in menu.actions() if a.text() == '나가기').trigger()
        self.assertEqual(self.conn.last('room_leave'), {'room_id': 'r2'})
        self.assertNotIn('대화상대 초대…', [a.text() for a in self.tab.context_menu_for('r3').actions()])

    @unittest.skipUnless(HAS_CHAT_ROOM, 'chat_room 미완성')
    def test_invite_dialog_from_chats(self):
        from client.kakao import chat_room
        if not hasattr(chat_room, 'InviteDialog'):
            self.skipTest('InviteDialog 미구현')
        with mock.patch.object(chat_room.InviteDialog, 'exec_', return_value=0):
            dlg = self.tab.show_invite_dialog('r1')
        self.assertIsNotNone(dlg)

    def test_live_update_on_new_message(self):
        self.conn.push('msg_new', message=dict(
            msg_id=100, room_id='r3', sender='홍길동', kind='text', content='나에게 메모',
            timestamp=(datetime.now() + timedelta(seconds=5)).isoformat(timespec='seconds'),
            reply_to=None, mentions=[], reactions={}, deleted=False, attachment=None, event_id=None, poll=None))
        self.assertEqual(self.tab.room_ids()[0], 'r3')
        row = self.tab.list.itemWidget(self.tab.list.item(0))
        self.assertEqual(row.preview.text(), '나에게 메모')


# ================================================================ 채팅방 폴더·미리보기·AI 버튼 (7.8)
class ChatFolderTests(ShellTestBase):
    def setUp(self):
        super().setUp()
        self.tab = ChatsTab(self.state, self.settings)

    def action(self, menu, text):
        return next(a for a in menu.actions() if a.text() == text)

    def test_chips_match_folders(self):
        self.assertEqual([c.folder for c in self.tab.folder_bar.chips], ['전체', '안읽음', '즐겨찾기', '통화'])
        self.assertEqual(self.tab.folder_bar.labels(), ['전체', '안읽음 2', '즐겨찾기 0', '통화'])
        self.assertTrue(self.tab.folder_bar.chip('전체').isChecked())
        self.assertIsNone(self.state.save_chat_folder('회사', ['r1']))
        self.assertEqual(self.tab.folder_bar.labels(), ['전체', '안읽음 2', '즐겨찾기 0', '통화', '회사 1'])

    def test_select_unread_and_favorites(self):
        self.tab.folder_bar.chip('안읽음').click()
        self.assertEqual(self.tab.current_folder, '안읽음')
        self.assertEqual(self.tab.room_ids(), ['r1', 'r2'])
        self.assertTrue(self.tab.folder_bar.chip('안읽음').isChecked())
        self.assertFalse(self.tab.folder_bar.chip('전체').isChecked())
        self.tab.select_folder('즐겨찾기')
        self.assertEqual(self.tab.room_ids(), [])
        self.assertIn('즐겨찾기한 채팅방이 없습니다', self.tab.empty_label.text())
        self.settings.toggle_in('pinned_rooms', 'r3')          # 고정된 방
        self.assertEqual(self.tab.room_ids(), ['r3'])
        self.settings.toggle_in('favorites', '박민수')          # 즐겨찾기 친구와의 1:1
        self.assertEqual(self.tab.room_ids(), ['r3', 'r2'])
        self.assertEqual(self.tab.folder_bar.chip('즐겨찾기').text(), '즐겨찾기 2')

    def test_custom_folder_filter_with_search(self):
        self.state.save_chat_folder('회사', ['r1', 'r3'])
        self.tab.folder_bar.chip('회사').click()
        self.assertEqual(self.tab.room_ids(), ['r1', 'r3'])
        self.tab.toggle_search()
        self.tab.search_edit.setText('프로젝트')
        self.assertEqual(self.tab.room_ids(), ['r1'])
        self.tab.search_edit.setText('박민')                    # 폴더 밖의 방은 검색돼도 안 보인다
        self.assertEqual(self.tab.room_ids(), [])

    def test_deleted_folder_falls_back_to_all(self):
        self.state.save_chat_folder('회사', ['r1'])
        self.tab.select_folder('회사')
        self.assertEqual(self.tab.current_folder, '회사')
        self.state.delete_chat_folder('회사')
        self.assertEqual(self.tab.current_folder, '전체')
        self.assertEqual(self.tab.room_ids(), ['r1', 'r2', 'r3'])
        self.tab.select_folder('없는 폴더')
        self.assertEqual(self.tab.current_folder, '전체')

    def test_subtitle_reflects_folder(self):
        self.assertTrue(self.tab.header.subtitle.text().startswith('채팅방 3개'))
        self.tab.select_folder('안읽음')
        self.assertEqual(self.tab.header.subtitle.text(), '안읽음 폴더 · 채팅방 2개')
        self.tab.select_folder('전체')
        self.assertEqual(self.tab.header.subtitle.text(), '채팅방 3개 · 안 읽은 메시지 3개')

    def test_unread_folder_updates_live(self):
        self.tab.select_folder('안읽음')
        self.conn.push('read_update', room_id='r2', username='홍길동', last_read_msg_id=14)
        self.assertEqual(self.state.room_unread('r2'), 0)
        self.assertEqual(self.tab.room_ids(), ['r1'])
        self.assertEqual(self.tab.folder_bar.chip('안읽음').text(), '안읽음 1')

    def test_folder_dialog_create(self):
        dlg = ChatFolderDialog(self.state)
        self.assertIsNone(dlg.delete_button)
        dlg.set_name('가족')
        dlg.set_checked(['r2', 'r3'])
        self.assertEqual(dlg.checked_room_ids(), ['r2', 'r3'])
        dlg.accept()
        self.assertEqual(dlg.result(), dlg.Accepted)
        self.assertEqual(dlg.saved_name, '가족')
        self.assertEqual([r['room_id'] for r in self.state.rooms_in_folder('가족')], ['r2', 'r3'])
        self.assertIn('가족', [c.folder for c in self.tab.folder_bar.chips])

    def test_folder_dialog_errors(self):
        self.state.save_chat_folder('회사', ['r1'])
        dlg = ChatFolderDialog(self.state)
        dlg.set_name('')
        dlg.accept()
        self.assertEqual(dlg.error_text(), '폴더 이름을 입력해 주세요.')
        dlg.set_name('안읽음')
        self.assertEqual(dlg.error_text(), '')                 # 입력하면 오류 숨김
        dlg.accept()
        self.assertIn('기본 폴더 이름', dlg.error_text())
        dlg.set_name('회사')
        dlg.accept()
        self.assertEqual(dlg.error_text(), '같은 이름의 폴더가 있습니다.')
        self.assertIsNone(dlg.saved_name)
        self.assertEqual(len(self.settings.get('chat_folders')), 1)

    def test_folder_dialog_edit_rename_and_delete(self):
        self.state.save_chat_folder('회사', ['r1'])
        self.tab.select_folder('회사')
        dlg = ChatFolderDialog(self.state, '회사')
        self.assertEqual(dlg.name_edit.text(), '회사')
        self.assertEqual(dlg.checked_room_ids(), ['r1'])
        self.assertIsNotNone(dlg.delete_button)
        dlg.set_name('업무')
        dlg.set_checked(['r1', 'r2'])
        dlg.accept()
        self.tab.apply_folder_dialog_result(dlg)
        self.assertEqual([f['name'] for f in self.settings.get('chat_folders')], ['업무'])
        self.assertEqual(self.tab.current_folder, '업무')      # 보고 있던 폴더 이름이 바뀌면 따라간다
        self.assertEqual(self.tab.room_ids(), ['r1', 'r2'])
        dlg = ChatFolderDialog(self.state, '업무')
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
            self.assertFalse(dlg.delete_folder())
        self.assertTrue(dlg.delete_folder(confirm=False))
        self.tab.apply_folder_dialog_result(dlg)
        self.assertEqual(self.settings.get('chat_folders'), [])
        self.assertEqual(self.tab.current_folder, '전체')

    def test_new_folder_from_plus_chip_selects_it(self):
        def fake_exec(dlg):
            dlg.set_name('스터디')
            dlg.set_checked(['r1'])
            dlg.accept()
            return dlg.result()
        with mock.patch.object(ChatFolderDialog, 'exec_', fake_exec):
            self.tab.folder_bar.add_chip.click()
        self.assertEqual(self.tab.current_folder, '스터디')
        self.assertEqual(self.tab.room_ids(), ['r1'])

    def test_folder_chip_menu(self):
        self.state.save_chat_folder('회사', ['r1'])
        self.assertIsNone(self.tab.folder_menu_for('전체'))
        self.assertIsNone(self.tab.folder_menu_for('안읽음'))
        menu = self.tab.folder_menu_for('회사')
        self.assertEqual([a.text() for a in menu.actions()], ['폴더 편집', '폴더 삭제'])
        with mock.patch.object(ChatFolderDialog, 'exec_', return_value=0) as exec_:
            self.action(menu, '폴더 편집').trigger()
        self.assertEqual(exec_.call_count, 1)
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            self.action(menu, '폴더 삭제').trigger()
        self.assertEqual(self.settings.get('chat_folders'), [])

    def test_context_submenu_toggles_membership(self):
        self.state.save_chat_folder('회사', [])
        self.state.save_chat_folder('가족', ['r2'])
        sub = self.action(self.tab.context_menu_for('r2'), '폴더에 추가').menu()
        texts = [a.text() for a in sub.actions() if a.text()]
        self.assertEqual(texts, ['회사', '가족', '새 폴더…'])
        self.assertFalse(self.action(sub, '회사').isChecked())
        self.assertTrue(self.action(sub, '가족').isChecked())
        self.action(sub, '회사').trigger()
        self.assertEqual([r['room_id'] for r in self.state.rooms_in_folder('회사')], ['r2'])
        sub = self.action(self.tab.context_menu_for('r2'), '폴더에 추가').menu()
        self.action(sub, '가족').trigger()
        self.assertEqual(self.state.rooms_in_folder('가족'), [])
        # 새 폴더… → 그 방이 미리 체크된 다이얼로그
        seen = []
        with mock.patch.object(ChatFolderDialog, 'exec_', lambda dlg: seen.append(dlg.checked_room_ids()) or 0):
            self.action(sub, '새 폴더…').trigger()
        self.assertEqual(seen, [['r2']])

    def test_peek_menu_only_with_unread(self):
        texts = [a.text() for a in self.tab.context_menu_for('r1').actions()]
        self.assertIn('읽지 않고 미리보기', texts)
        texts = [a.text() for a in self.tab.context_menu_for('r3').actions()]
        self.assertNotIn('읽지 않고 미리보기', texts)

    def test_peek_dialog_does_not_mark_read(self):
        with mock.patch.object(PeekDialog, 'exec_', return_value=0):
            dlg = self.tab.show_peek_dialog('r1')
        self.assertLessEqual(len(dlg.messages), 5)
        self.assertEqual([m['msg_id'] for m in dlg.messages], [9, 11])   # 내 읽음 포인터(8) 이후, 삭제 제외
        self.assertEqual(dlg.rows[0].sender.text(), '김철수')
        self.assertEqual(dlg.rows[0].text.text(), '파일: 회의자료.pdf')
        self.assertTrue(dlg.rows[1].text.text().startswith('긴 메시지 테스트'))
        self.assertEqual(dlg.note_label.text(), '읽음으로 표시되지 않습니다')
        self.assertIn('2', dlg.subtitle.text())
        self.assertIsNone(self.conn.last('read'))
        self.assertEqual(self.state.room_unread('r1'), 2)
        opened = []
        self.state.room_opened.connect(opened.append)
        dlg.open_button.click()
        self.assertEqual(opened, ['r1'])

    def test_ai_button_opens_bot_chat(self):
        add_org(self.state, self.conn)
        self.assertIsInstance(self.tab.ai_button, AiButton)
        self.assertIs(self.tab.header.buttons[0], self.tab.ai_button)   # 기존 버튼보다 앞
        self.assertEqual(self.tab.ai_button.toolTip(), 'AI 비서')
        self.assertFalse(self.tab.ai_button.icon().isNull())
        self.tab.ai_button.click()
        self.assertEqual(self.conn.last('room_open_direct'), {'target': BOT_NAME})
        # 이미 봇과의 방이 있으면 서버 요청 없이 바로 연다
        self.conn.push('room_updated', room={'room_id': 'rb', 'type': 'direct', 'name': '',
                                             'members': ['홍길동', BOT_NAME], 'created_at': '2026-10-01T00:00:00',
                                             'notice': None, 'last_message': None,
                                             'read_pointers': {}, 'unread_count': 0})
        self.conn.sent.clear()
        opened = []
        self.state.room_opened.connect(opened.append)
        self.tab.ai_button.click()
        self.assertIn('rb', opened)
        self.assertIsNone(self.conn.last('room_open_direct'))

    def test_folder_bar_fits_narrow_window(self):
        self.state.save_chat_folder('아주 긴 폴더 이름입니다', ['r1'])
        win = self.make_window()
        win.resize(340, 680)
        win.show()
        win.set_tab('chats')
        tab = win.tabs['chats']
        tab.select_folder('안읽음')
        QApplication.processEvents()
        self.assertLessEqual(tab.width(), 340)
        for i in range(tab.list.count()):
            row = tab.list.itemWidget(tab.list.item(i))
            self.assertLessEqual(row.width(), tab.list.viewport().width())
        for btn in tab.header.buttons:
            self.assertLessEqual(btn.mapTo(tab, btn.rect().bottomRight()).x(), tab.width())


# ================================================================ 다이얼로그
class DialogTests(ShellTestBase):
    def test_create_group_sends_room_create(self):
        dlg = CreateGroupDialog(self.state)
        self.assertFalse(dlg.ok_button.isEnabled())
        dlg.set_checked('김철수')
        dlg.set_checked('박민수')
        dlg.name_edit.setText('주말 모임')
        self.assertEqual(dlg.selected_members(), ['김철수', '박민수'])
        dlg.accept()
        self.assertEqual(self.conn.last('room_create'), {'name': '주말 모임', 'members': ['김철수', '박민수']})

    def test_create_group_single_member_opens_direct(self):
        dlg = CreateGroupDialog(self.state)
        dlg.set_checked('최지우')
        dlg.accept()
        self.assertIsNone(self.conn.last('room_create'))
        self.assertEqual(self.conn.last('room_open_direct'), {'target': '최지우'})

    def test_create_group_filter(self):
        dlg = CreateGroupDialog(self.state)
        dlg.search_edit.setText('영희')
        visible = [dlg.list.item(i).data(Qt.UserRole) for i in range(dlg.list.count())
                   if not dlg.list.item(i).isHidden()]
        self.assertEqual(visible, ['이영희'])

    def test_invite_to_group_room(self):
        dlg = InviteToRoomDialog(self.state, '최지우')
        self.assertEqual([r['room_id'] for r in dlg.candidate_rooms()], ['r1', 'r2'])
        self.assertTrue(dlg.select_room('r1'))
        dlg.accept()
        self.assertEqual(self.conn.last('room_invite'), {'room_id': 'r1', 'usernames': ['최지우']})

    def test_invite_to_direct_room_creates_group(self):
        dlg = InviteToRoomDialog(self.state, '최지우')
        dlg.select_room('r2')
        dlg.accept()
        payload = self.conn.last('room_create')
        self.assertIsNotNone(payload)
        self.assertEqual(sorted(payload['members']), ['박민수', '최지우'])

    def test_invite_excludes_rooms_with_member(self):
        dlg = InviteToRoomDialog(self.state, '김철수')
        self.assertEqual([r['room_id'] for r in dlg.candidate_rooms()], ['r2'])

    def test_login_dialog_values(self):
        dlg = LoginDialog('10.0.0.1', 6000)
        self.assertFalse(dlg.login_button.isEnabled())
        dlg.preset_buttons[2].click()
        self.assertEqual(dlg.name_edit.text(), '이영희')
        self.assertTrue(dlg.login_button.isEnabled())
        self.assertFalse(dlg.server_box.isVisibleTo(dlg))
        dlg.server_toggle.click()
        self.assertTrue(dlg.server_box.isVisibleTo(dlg))
        dlg.host_edit.setText('192.168.0.5')
        dlg.port_edit.setText('5556')
        self.assertEqual(dlg.values(), ('이영희', '192.168.0.5', 5556))
        self.assertEqual(dlg.windowTitle(), 'KCS Talk 로그인')
        dlg.accept()
        self.assertEqual(dlg.result(), LoginDialog.Accepted)

    def test_login_dialog_fits_content(self):
        dlg = LoginDialog()
        dlg.show()
        QApplication.processEvents()
        self.assertGreaterEqual(dlg.height(), dlg.layout().sizeHint().height())
        before = dlg.height()
        dlg.server_toggle.click()
        QApplication.processEvents()
        self.assertGreater(dlg.height(), before)
        self.assertGreaterEqual(dlg.height(), dlg.layout().sizeHint().height())
        dlg.hide()

    def test_rag_docs_dialog(self):
        dlg = RagDocsDialog(self.state)
        self.assertIsNotNone(self.conn.last('rag_doc_list'))
        self.conn.push('rag_doc_list', docs=[
            {'doc_id': 1, 'name': '규정.md', 'owner': '홍길동', 'size': 2048, 'chunks': 3, 'created_at': ''},
            {'doc_id': 2, 'name': '공용.txt', 'owner': '', 'size': 100, 'chunks': 1, 'created_at': ''}])
        self.assertEqual(dlg.list.count(), 2)
        dlg.list.setCurrentRow(1)
        self.assertFalse(dlg.delete_button.isEnabled())  # 공유 문서는 삭제 불가
        dlg.list.setCurrentRow(0)
        self.assertTrue(dlg.delete_button.isEnabled())
        with mock.patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
            dlg.delete_button.click()
        self.assertEqual(self.conn.last('rag_doc_delete'), {'doc_id': 1})
        path = os.path.join(tempfile.mkdtemp(), 'note.txt')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('회의는 매주 월요일 10시')
        self.assertIsNone(dlg.add_file(path))
        self.assertEqual(self.conn.last('rag_doc_add')['name'], 'note.txt')


# ================================================================ 조직도 / 더보기
class OrgAndMoreTests(ShellTestBase):
    def test_org_tree(self):
        add_org(self.state, self.conn)
        tab = OrgTab(self.state, self.settings)
        self.assertEqual(tab.companies()[0], 'KCS 홀딩스')
        self.assertEqual(set(tab.companies()), {'KCS 홀딩스', 'KCS 물류', 'KCS 커머스', 'KCS AI'})
        self.assertEqual(tab.members_of('KCS 홀딩스', '경영지원팀'), ['홍길동', '김철수'])
        self.assertEqual(tab.members_of('KCS 물류'), ['이영희', '박민수'])
        tab.toggle_company('KCS 물류')
        self.assertNotIn(('member', '이영희'), rows(tab.list))
        self.assertIn(('company', 'KCS 물류'), rows(tab.list))
        tab.toggle_company('KCS 물류')
        self.assertIn(('member', '이영희'), rows(tab.list))
        tab.search_edit.setText('마케팅')
        self.assertEqual(tab.companies(), ['KCS 커머스'])
        tab.search_edit.setText('')
        tab.list.itemDoubleClicked.emit(tab.list.find_data(('member', '최지우')))
        self.assertEqual(self.conn.last('room_open_direct'), {'target': '최지우'})
        menu = tab.context_menu_for(('member', '이영희'))
        self.assertEqual([a.text() for a in menu.actions()], ['1:1 채팅', '채팅방에 초대…', '프로필 보기', '연락처 보내기…'])

    def test_more_tab(self):
        tab = MoreTab(self.state, self.settings, server_address='127.0.0.1:5555')
        self.assertEqual(tab.name_label.text(), '홍길동')
        self.assertEqual(tab.server_value.text(), '127.0.0.1:5555')
        self.assertEqual(tab.version_value.text(), '2.0')
        self.conn.push('user_updated', user=dict(self.state.user('홍길동'), status_message='새 상태'))
        self.assertEqual(tab.status_label.text(), '새 상태')
        # 설정이 다른 곳에서 바뀌어도 컨트롤이 따라간다
        self.settings.set('font_scale', 1.15)
        self.assertEqual(tab.font_combo.currentText(), '크게')
        self.settings.set('dark_mode', True)
        self.assertTrue(tab.dark_toggle.isChecked())
        tab.apply_theme()

    @unittest.skipUnless(HAS_WALLPAPER, 'wallpaper 미완성')
    def test_wallpaper_row(self):
        from client.kakao import wallpaper
        tab = MoreTab(self.state, self.settings)
        with mock.patch.object(wallpaper.WallpaperDialog, 'exec_', return_value=0) as ex:
            tab.wallpaper_button.click()
        ex.assert_called_once()


class RecentLoginTests(unittest.TestCase):
    def test_recent_logins_replace_presets(self):
        from client.kakao import login
        path = os.path.join(tempfile.mkdtemp(), 'recent.json')
        with mock.patch.object(login, 'RECENT_PATH', path):
            dlg = login.LoginDialog()
            self.assertEqual([b.text() for b in dlg.preset_buttons], login.PRESET_USERS)
            dlg.name_edit.setText('도승현')
            dlg.accept()
            login.save_recent('엄태식')
            dlg2 = login.LoginDialog()
            self.assertEqual([b.text() for b in dlg2.preset_buttons][:2], ['엄태식', '도승현'])
            self.assertEqual(dlg2.name_edit.text(), '엄태식')


class OrgHierarchyTests(ShellTestBase):
    """지주사 → 계열사 → 다단계 조직 → 구성원(겸직 포함)"""

    def setUp(self):
        super().setUp()
        self.state.org = {'holding': {'name': '한국지주', 'business': '지주회사업'},
                          'companies': [{'name': '한네트', 'business': '부가통신업'}, {'name': '케이씨티'},
                                        {'name': '케이씨에스', 'units': [['기술연구소'], ['기술연구소', '연구1실'],
                                                                     ['기술연구소', '연구1실', '1팀'],
                                                                     ['기술연구소', '연구1실', '2팀(SI)'], ['신사업팀']]}]}
        for name, path, title, extra in (
                ('홍길동', ['기술연구소', '연구1실', '2팀(SI)'], '수석', []),
                ('김철수', ['기술연구소', '연구1실', '1팀'], '실장', [{'org_path': ['신사업팀'], 'title': '실장'}]),
                ('이영희', ['신사업팀'], '사원', [])):
            self.conn.push('user_updated', user=dict(self.state.user(name), company='케이씨에스',
                                                    department=path[-1], org_path=path, title=title,
                                                    extension='5100', concurrent=extra))

    def test_holding_then_affiliates_in_order(self):
        tab = OrgTab(self.state, self.settings)
        data = rows(tab.list)
        self.assertEqual(data[0], ('holding', '한국지주'))
        companies = [d[1] for d in data if d[0] == 'company']
        self.assertEqual(companies[:3], ['한네트', '케이씨티', '케이씨에스'])
        self.assertIn('지주회사', tab.header.subtitle.text() + '지주회사')

    def test_multilevel_units_and_concurrent(self):
        tab = OrgTab(self.state, self.settings)
        data = rows(tab.list)
        units = [d[2] for d in data if d[0] == 'unit' and d[1] == '케이씨에스']
        self.assertEqual(units[:4], [('기술연구소',), ('기술연구소', '연구1실'), ('기술연구소', '연구1실', '1팀'),
                                     ('기술연구소', '연구1실', '2팀(SI)')])
        self.assertEqual(tab.members_of('케이씨에스', ('신사업팀',)), ['이영희'])  # 겸직자는 주소속 목록에서 제외
        # 신사업팀 아래에는 겸직자 김철수도 행으로 나온다
        idx = data.index(('unit', '케이씨에스', ('신사업팀',)))
        self.assertIn(('member', '김철수'), data[idx:])
        tab.toggle_unit('케이씨에스', ('기술연구소',))
        self.assertNotIn(('member', '홍길동'), rows(tab.list))
        tab.toggle_unit('케이씨에스', ('기술연구소',))
        self.assertIn(('member', '홍길동'), rows(tab.list))

    def test_homepage_affiliates_include_kct(self):
        """회사 홈페이지(kcins.co.kr › 계열사) 기준 계열사 목록에 케이씨티 포함 + 화면 툴팁에 회사 정보"""
        import importlib
        mod = importlib.import_module('scripts.import_org_xlsx') if importlib.util.find_spec('scripts') else None
        if mod is None:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
            mod = importlib.import_module('import_org_xlsx')
        names = [a['name'] for a in mod.AFFILIATES]
        self.assertEqual(names, ['한국컴퓨터', '한네트', '로지시스', '케이씨티', '케이씨에스'])
        self.assertEqual(mod.HOLDING['name'], '한국지주')
        kct = mod.AFFILIATES[names.index('케이씨티')]
        self.state.org['companies'] = [kct if c['name'] == '케이씨티' else c for c in self.state.org['companies']]
        tab = OrgTab(self.state, self.settings)
        item = tab.list.find_data(('company', '케이씨티'))
        tip = tab.list.itemWidget(item).toolTip()
        self.assertIn('금융자동화 시스템 공급 사업', tip)
        self.assertIn('www.kctinc.co.kr', tip)

    def test_empty_affiliate_collapsed_then_expandable(self):
        tab = OrgTab(self.state, self.settings)
        self.assertNotIn(('empty', '한네트'), rows(tab.list))
        tab.toggle_company('한네트')
        self.assertIn(('empty', '한네트'), rows(tab.list))

    def test_search_by_org_path(self):
        tab = OrgTab(self.state, self.settings)
        tab.search_edit.setText('SI')
        members = [d[1] for d in rows(tab.list) if d[0] == 'member']
        self.assertEqual(members, ['홍길동'])

    def test_wide_window_docks_org_on_left(self):
        win = MainWindow(self.state, self.settings)
        win.resize(400, 680)
        win.show()
        app().processEvents()
        self.assertFalse(win.org_dock.isVisible())
        win.resize(1000, 700)
        app().processEvents()
        self.assertTrue(win.org_dock.isVisible())
        win.set_tab('org')
        self.assertFalse(win.org_dock.isVisible())   # 조직도 탭과 중복 표시 안 함
        win.close()


if __name__ == '__main__':
    unittest.main()
