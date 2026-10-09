# -*- coding: utf-8 -*-
"""레이아웃 개선 회귀 테스트 - 헤더 2행, 선택지 줄이기(⋯/＋ 메뉴), 친구 탭 리듬, 더보기 묶음, 분할 화면, 대비 토큰"""

import unittest

from tests.kakao_fakes import make_demo_state, app
from PyQt5.QtGui import QColor

from client.kakao import theme


def pump(n=8):
    for _ in range(n):
        app().processEvents()


def contrast(a, b):
    def lum(c):
        c = QColor(c)
        ch = []
        for v in (c.redF(), c.greenF(), c.blueF()):
            ch.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TokenContrastTest(unittest.TestCase):
    def tearDown(self):
        theme.set_dark(False)

    def test_hint_badge_sidebar_meet_aa(self):
        theme.set_dark(False)
        self.assertGreaterEqual(contrast(theme.c('text_hint'), theme.c('bg')), 4.5)
        self.assertGreaterEqual(contrast('#FFFFFF', theme.c('badge')), 4.5)
        self.assertGreaterEqual(contrast(theme.c('sidebar_icon'), theme.c('sidebar')), 4.5)
        theme.set_dark(True)
        self.assertGreaterEqual(contrast(theme.c('text_hint'), theme.c('bg')), 4.5)

    def test_spacing_scale(self):
        self.assertEqual([theme.sp(k) for k in ('xs', 's', 'm', 'l', 'xl')], [4, 8, 12, 16, 24])

    def test_avatar_palette_readable(self):
        from client.kakao.widgets import AVATAR_COLORS
        for color in AVATAR_COLORS:
            self.assertGreaterEqual(contrast('#FFFFFF', color), 3.0, color)   # 굵은 큰 글자 기준


class LayoutTest(unittest.TestCase):
    def setUp(self):
        app()
        theme.set_dark(False)
        self.state, self.conn = make_demo_state()

    def test_header_subtitle_on_own_row(self):
        from client.kakao.chats_tab import ChatsTab
        tab = ChatsTab(self.state, self.state.settings)
        tab.resize(336, 600)
        tab.show()
        pump()
        sub = tab.header.subtitle
        self.assertGreater(sub.y(), tab.header.title.y())               # 제목 아래 줄
        self.assertGreaterEqual(sub.width(), 250)                         # 버튼에 밀리지 않고 폭 전체
        tab.close()

    def test_chats_header_has_four_actions_and_overflow(self):
        from client.kakao.chats_tab import ChatsTab
        tab = ChatsTab(self.state, self.state.settings)
        visible = [b for b in tab.header.buttons if not b.isHidden()]
        self.assertLessEqual(len(visible), 4)
        self.assertEqual([a.text() for a in tab.more_menu().actions()],
                         ['오픈채팅 찾기 · 만들기', '톡서랍 (모든 채팅방의 사진·파일·링크)'])

    def test_chat_input_shows_three_tools_and_labelled_menu(self):
        from client.kakao.chat_room import ChatRoomWindow
        win = ChatRoomWindow(self.state, 'r1')
        win.show()
        pump()
        shown = [b for b in win.tool_buttons if b.isVisible()]
        self.assertEqual(shown, [win.emoji_btn, win.file_btn, win.plus_btn])
        self.assertEqual([a.text() for a in win.tools_menu().actions() if not a.isSeparator()],
                         ['투표', '일정 공유', '예약 메시지', '사다리 게임', '톡게시판', '음성메시지', '연락처 보내기'])
        from unittest import mock
        from PyQt5.QtWidgets import QDialog
        with mock.patch.object(QDialog, 'exec_', return_value=0) as ex:
            win.tools_menu().actions()[0].trigger()   # 숨긴 버튼의 기능(투표 창)이 그대로 동작
        ex.assert_called()
        win.close()

    def test_friends_compact_story_and_no_duplicates(self):
        from client.kakao.friends_tab import FriendsTab
        self.conn.push('friend_list', friends=['박민수'])
        tab = FriendsTab(self.state, self.state.settings)
        tab.show()
        pump()
        self.assertTrue(tab.story_bar.scroll.isHidden())                 # 펑 없음 → 한 줄 링크
        self.assertFalse(tab.story_bar.compose_link.isHidden())
        sections = tab.sections
        self.assertIn('박민수', sections['registered'])
        self.assertNotIn('박민수', sections['online'] + sections['offline'])
        tab.close()

    def test_more_tab_grouped(self):
        from client.kakao.more_tab import MoreTab
        tab = MoreTab(self.state, self.state.settings)
        self.assertGreaterEqual(len(tab.groups), 5)
        titles = [l.text() for l in tab.section_labels]
        self.assertEqual(titles[:2], ['상태 · 화면', '알림 · 채팅'])
        for frame in tab.groups:
            rows = [frame.layout().itemAt(i).widget() for i in range(frame.layout().count())]
            rows = [r for r in rows if r is not None and r.objectName() != 'settingsDivider']
            self.assertLessEqual(len(rows), 4)                               # 한 묶음 4개 이하

    def test_wide_window_split_embeds_and_pops_out(self):
        from client.kakao.main_window import MainWindow
        win = MainWindow(self.state, self.state.settings)
        win.resize(1320, 760)
        win.show()
        pump()
        self.assertTrue(win.is_split())
        self.assertEqual(win.room_pane.currentWidget(), win.room_placeholder)
        room = win.open_room('r1')
        pump()
        self.assertIs(room.parent(), win.room_pane)
        self.assertIs(win.open_room('r1'), room)                          # 다시 열어도 같은 칸
        win.resize(500, 700)
        pump()
        self.assertFalse(win.is_split())
        self.assertIsNone(room.parent())                                  # 좁아지면 별도 창으로
        room.close()
        win.close()


class WorkFirstAndKeyboardTest(unittest.TestCase):
    """사용자 결정 반영: 업무 우선 친구 탭 · 키보드/접근성 · KCS 블루 고정"""

    def setUp(self):
        app()
        theme.set_dark(False)
        self.state, self.conn = make_demo_state()
        for name, path, title in (('홍길동', ['기술연구소1실', '2팀(SI)'], '수석'),
                                  ('김철수', ['기술연구소1실', '1팀(Tandem)'], '팀장'),
                                  ('박민수', ['영업1부'], '부장')):
            self.conn.push('user_updated', user=dict(self.state.user(name), company='케이씨에스', org_path=path,
                                                    department=path[0], title=title))

    def test_social_features_default_off(self):
        from client.kakao.settings import LocalSettings
        import tempfile
        fresh = LocalSettings('누군가', base_dir=tempfile.mkdtemp())
        self.assertFalse(fresh.get('social_features'))

    def test_team_section_first_with_work_info(self):
        from client.kakao.friends_tab import FriendsTab
        from datetime import datetime, timedelta
        now = datetime.now()
        ev = {'event_id': 50, 'room_id': None, 'creator': '김철수', 'title': '고객 미팅', 'description': '',
              'location': '', 'start': (now - timedelta(minutes=30)).isoformat(timespec='seconds'),
              'end': (now + timedelta(minutes=30)).isoformat(timespec='seconds'), 'all_day': False,
              'remind_minutes': None, 'color': '#2A386C', 'attendees': {'김철수': 'yes'}, 'created_at': ''}
        self.conn.push('event_updated', event=ev)
        self.state.settings.set('social_features', False)
        tab = FriendsTab(self.state, self.state.settings)
        self.assertTrue(tab.story_bar.isHidden())
        self.assertEqual(tab.sections['team'], ['김철수'])               # 같은 부서(기술연구소1실)
        self.assertEqual(tab.sections['birthday'], [])                 # 소식 기능 꺼짐
        self.assertNotIn('김철수', tab.sections['online'] + tab.sections['offline'])
        data = [tab.list.item(i).data(0x0100) for i in range(tab.list.count())]
        sections = [d[1] for d in data if d[0] == 'section']
        self.assertEqual(sections[0], 'team')
        row = tab.list.itemWidget(tab.list.find_data(('friend', '김철수', 'team')))
        self.assertIn('팀장', row.sub.text())
        self.assertIn('1팀(Tandem)', row.sub.text())
        self.assertIn('일정 중 ~', row.sub.text())
        self.state.settings.set('social_features', True)
        self.assertFalse(tab.story_bar.isHidden())

    def test_shortcuts_and_quick_switcher(self):
        from client.kakao.main_window import MainWindow, QuickSwitcher
        win = MainWindow(self.state, self.state.settings)
        win.show()
        keys = {sc.key().toString() for sc in win.shortcuts}
        for k in ('Ctrl+1', 'Ctrl+2', 'Ctrl+3', 'Ctrl+4', 'Ctrl+5', 'Ctrl+K', 'Ctrl+N', 'Ctrl+Shift+A'):
            self.assertIn(k, keys)
        [sc for sc in win.shortcuts if sc.key().toString() == 'Ctrl+3'][0].activated.emit()
        self.assertEqual(win.current_tab(), 'org')
        dlg = win.open_quick_switcher(exec_=False)
        self.assertIsInstance(dlg, QuickSwitcher)
        dlg.search.setText('프로젝트')
        self.assertEqual(dlg.list.currentItem().data(0x0100), ('room', 'r1'))
        dlg.search.setText('Tandem')
        self.assertEqual(dlg.list.currentItem().data(0x0100), ('person', '김철수'))
        dlg.accept_current()
        self.assertEqual(self.conn.last('room_open_direct'), {'target': '김철수'})   # 1:1 방이 없으면 만들기 요청
        win.close()

    def test_icon_buttons_have_accessible_names(self):
        from client.kakao.main_window import MainWindow
        from PyQt5.QtWidgets import QAbstractButton
        win = MainWindow(self.state, self.state.settings)
        unnamed = [b for b in win.findChildren(QAbstractButton)
                   if b.isVisibleTo(win) and not b.accessibleName() and not b.text()]
        self.assertEqual(unnamed, [])
        self.assertEqual(win.sidebar.buttons['org'].accessibleName(), '조직도')
        win.close()


if __name__ == '__main__':
    unittest.main()
