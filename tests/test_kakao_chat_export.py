# -*- coding: utf-8 -*-
"""대화 내용 저장 (명세 §9.5): 형식(텍스트 · 엑셀용 표 · 사진·파일 포함 zip) + 기간"""

import base64
import csv
import io
import os
import shutil
import tempfile
import unittest
import zipfile
from datetime import date, datetime
from unittest import mock

from tests.kakao_fakes import make_demo_state, app

from client.kakao import chat_export
from client.kakao.chat_export import ExportDialog, period_range


def pump(n=5):
    for _ in range(n):
        app().processEvents()


def msg(msg_id, kind='text', content='', sender='김철수', ts='2026-10-08T09:06:00', **kw):
    base = {'msg_id': msg_id, 'room_id': 'r1', 'sender': sender, 'kind': kind, 'content': content,
            'timestamp': ts, 'deleted': False, 'attachment': None}
    base.update(kw)
    return base


class PeriodAndFormatTests(unittest.TestCase):
    def test_period_range(self):
        today = date(2026, 10, 9)
        self.assertEqual(period_range('all', today), (None, None, ''))
        self.assertEqual(period_range('today', today), (today, today, '2026-10-09'))
        self.assertEqual(period_range('week', today)[:2], (date(2026, 10, 3), today))
        self.assertEqual(period_range('month', today)[0], date(2026, 9, 10))
        since, until, label = period_range('custom', today, date(2026, 10, 5), date(2026, 10, 1))
        self.assertEqual((since, until, label), (date(2026, 10, 1), date(2026, 10, 5), '2026-10-01 ~ 2026-10-05'))

    def test_file_names(self):
        now = datetime(2026, 10, 9, 15, 0, 0)
        self.assertEqual(chat_export.default_file_name('팀/방:1', 'csv', now), 'KCS Talk_팀_방_1_20261009_150000.csv')
        self.assertEqual(chat_export.ensure_extension('/tmp/a', 'zip'), '/tmp/a.zip')
        self.assertEqual(chat_export.ensure_extension('/tmp/a.ZIP', 'zip'), '/tmp/a.ZIP')
        self.assertEqual(chat_export.safe_name('..'), 'file')


class StateExportTests(unittest.TestCase):
    def setUp(self):
        self.state, self.conn = make_demo_state()

    def test_request_export_with_period(self):
        self.state.request_export('r1', since=date(2026, 10, 1), until=date(2026, 10, 9))
        self.assertEqual(self.conn.last('room_export'), {'room_id': 'r1', 'since': '2026-10-01', 'until': '2026-10-09'})
        self.state.request_export('r1')
        self.assertEqual(self.conn.last('room_export'), {'room_id': 'r1'})      # 전체 (예전 서버와 같은 요청)

    def test_export_csv_columns_bom_and_formula_guard(self):
        msgs = [msg(1, 'system', '김철수님이 들어왔습니다.', sender='', ts='2026-10-08T09:05:00'),
                msg(2, content='안녕하세요, "모두"'),
                msg(3, content='=HYPERLINK("http://x")'),
                msg(4, 'file', '보고서.pdf', sender='홍길동', ts='2026-10-09T14:30:00',
                    attachment={'attachment_id': 7, 'name': '보고서.pdf'}),
                msg(5, content='x', deleted=True)]
        text = self.state.export_csv('r1', msgs)
        self.assertTrue(text.startswith('﻿'))                             # 엑셀에서 한글이 바로 열린다
        rows = list(csv.reader(io.StringIO(text[1:])))
        self.assertEqual(rows[0], ['날짜', '시각', '보낸 사람', '종류', '내용', '첨부 파일'])
        self.assertEqual(rows[1], ['2026-10-08', '09:05:00', '', '알림', '김철수님이 들어왔습니다.', ''])
        self.assertEqual(rows[2][2:5], ['김철수', '텍스트', '안녕하세요, "모두"'])
        self.assertEqual(rows[3][4], '\'=HYPERLINK("http://x")')                # 수식으로 실행되지 않게
        self.assertEqual(rows[4][3:], ['파일', '파일: 보고서.pdf', '보고서.pdf'])
        self.assertEqual(rows[5][4:], ['삭제된 메시지입니다.', ''])

    def test_export_text_period_and_file_marks(self):
        msgs = [msg(1, 'image', '사진', attachment={'attachment_id': 3, 'name': 'a.png'})]
        text = self.state.export_text('r1', msgs, saved_at=datetime(2026, 10, 9, 15, 0, 0),
                                      files={1: 'files/1_a.png'}, period='2026-10-01 ~ 2026-10-09')
        self.assertIn('저장한 기간 : 2026-10-01 ~ 2026-10-09', text.splitlines())
        self.assertIn('[김철수] [오전 9:06] 사진 [files/1_a.png]', text.splitlines())

    def test_attachment_errors_have_their_own_signal(self):
        failed, errors = [], []
        self.state.attachment_failed.connect(failed.append)
        self.state.error.connect(errors.append)
        self.conn.push('error', req_type='attachment_get', message='보관 기간이 지난 파일입니다.')
        self.assertEqual((failed, errors), (['보관 기간이 지난 파일입니다.'], ['보관 기간이 지난 파일입니다.']))
        self.state.quiet_attachment_errors = True                             # 저장 중에는 알림 없이
        self.conn.push('error', req_type='attachment_get', message='만료')
        self.assertEqual((len(failed), len(errors)), (2, 1))


class ExportDialogTests(unittest.TestCase):
    def setUp(self):
        app()

    def test_defaults_and_choices(self):
        dlg = ExportDialog('프로젝트 팀', today=date(2026, 10, 9))
        self.assertEqual(dlg.options(), {'fmt': 'txt', 'since': None, 'until': None, 'period': ''})
        self.assertTrue(dlg.custom_box.isHidden())
        dlg.format_buttons['zip'].setChecked(True)
        dlg.period_combo.setCurrentIndex([k for k, _ in chat_export.PERIODS].index('week'))
        self.assertEqual(dlg.options()['fmt'], 'zip')
        self.assertEqual(dlg.options()['since'], date(2026, 10, 3))
        dlg.period_combo.setCurrentIndex([k for k, _ in chat_export.PERIODS].index('custom'))
        self.assertFalse(dlg.custom_box.isHidden())
        from PyQt5.QtCore import QDate
        dlg.start_edit.setDate(QDate(2026, 9, 1))
        dlg.end_edit.setDate(QDate(2026, 9, 30))
        self.assertEqual(dlg.options()['period'], '2026-09-01 ~ 2026-09-30')


class ChatRoomExportTests(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        from client.kakao.chat_room import ChatRoomWindow
        self.win = ChatRoomWindow(self.state, 'r1')
        self.win.show()
        pump()
        self.addCleanup(self.win.close)

    def test_csv_export_with_period(self):
        path = os.path.join(self.dir, 'chat.csv')
        self.win.export_chat(path, fmt='csv', since=date(2026, 10, 1), until=date(2026, 10, 9), period='x')
        self.assertEqual(self.conn.last('room_export'), {'room_id': 'r1', 'since': '2026-10-01', 'until': '2026-10-09'})
        self.conn.push('room_export', room_id='r1', messages=self.state.room_messages('r1'), truncated=False)
        with open(path, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0][0], '날짜')
        self.assertTrue(any(r[4] == '다들 내일 회의 시간 괜찮아요?' for r in rows[1:]))
        self.assertIn('저장했습니다', self.win.toast_label.text())

    def test_zip_export_includes_files_and_marks_missing_ones(self):
        path = os.path.join(self.dir, 'chat.zip')
        msgs = [msg(1, content='사진 보낼게요'),
                msg(2, 'image', '사진', attachment={'attachment_id': 11, 'name': 'photo.png'}),
                msg(3, 'file', 'old.pdf', attachment={'attachment_id': 12, 'name': 'old.pdf', 'expired': True}),
                msg(4, 'file', 'gone.txt', attachment={'attachment_id': 13, 'name': 'gone.txt'}),
                msg(5, 'file', 'x.pdf', deleted=True, attachment={'attachment_id': 14, 'name': 'x.pdf'})]
        self.win.export_chat(path, fmt='zip')
        self.conn.push('room_export', room_id='r1', messages=msgs, truncated=False)
        # 첨부는 하나씩 요청한다: 만료된 12 와 삭제된 14 는 요청하지 않는다
        self.assertEqual(self.conn.last('attachment_get'), {'attachment_id': 11})
        self.conn.push('attachment_data', attachment_id=11, name='photo.png', mime='image/png',
                       data_b64=base64.b64encode(b'PNGDATA').decode())
        self.assertEqual(self.conn.last('attachment_get'), {'attachment_id': 13})
        errors = []
        self.state.error.connect(errors.append)
        self.conn.push('error', req_type='attachment_get', message='첨부 파일을 찾을 수 없거나 접근 권한이 없습니다.')
        self.assertEqual(errors, [])                                          # 저장 중 첨부 오류는 알림 없이
        self.assertFalse(self.state.quiet_attachment_errors)                  # 끝나면 원래대로
        requested = [p['attachment_id'] for t, p in self.conn.sent if t == 'attachment_get']
        self.assertEqual(requested, [11, 13])
        with zipfile.ZipFile(path) as zf:
            self.assertEqual(sorted(zf.namelist()), ['files/2_photo.png', '대화.csv', '대화.txt'])
            self.assertEqual(zf.read('files/2_photo.png'), b'PNGDATA')
            text = zf.read('대화.txt').decode('utf-8')
        self.assertIn('사진 [files/2_photo.png]', text)
        self.assertIn('파일: old.pdf [포함되지 않음: 보관 기간 만료]', text)
        self.assertIn('파일: gone.txt [포함되지 않음: 첨부 파일을 찾을 수 없거나 접근 권한이 없습니다.]', text)
        self.assertIn('사진·파일 1개', self.win.toast_label.text())
        self.assertIn('빠진 첨부 2개', self.win.toast_label.text())

    def test_zip_attachment_timeout_skips(self):
        path = os.path.join(self.dir, 'slow.zip')
        with mock.patch.object(chat_export, 'ATTACHMENT_TIMEOUT_MS', 30):
            self.win.export_chat(path, fmt='zip')
            self.conn.push('room_export', room_id='r1', truncated=False,
                           messages=[msg(2, 'image', '사진', attachment={'attachment_id': 21, 'name': 'p.png'})])
            from PyQt5.QtTest import QTest
            for _ in range(40):
                if os.path.exists(path):
                    break
                QTest.qWait(20)
        with zipfile.ZipFile(path) as zf:
            self.assertIn('받지 못함', zf.read('대화.txt').decode('utf-8'))

    def test_guards_offline_busy_and_no_response(self):
        self.conn.is_connected = False
        self.win.export_chat(os.path.join(self.dir, 'a.txt'))
        self.assertIsNone(self.conn.last('room_export'))
        self.assertIn('연결', self.win.toast_label.text())
        self.conn.is_connected = True
        self.win.EXPORT_TIMEOUT_MS = 30
        self.win.export_chat(os.path.join(self.dir, 'a.txt'))
        self.win.export_chat(os.path.join(self.dir, 'b.txt'))                 # 저장 중에는 한 번만
        self.assertEqual(sum(1 for t, _ in self.conn.sent if t == 'room_export'), 1)
        from PyQt5.QtTest import QTest
        QTest.qWait(80)
        self.assertFalse(self.win._export_requested)                          # 응답이 없으면 풀린다
        self.assertIn('응답하지 않아', self.win.toast_label.text())

    def test_menu_opens_options_dialog(self):
        labels = [a.text() for a in self.win.build_room_menu().actions()]
        self.assertIn('대화 내용 저장… (텍스트 · 엑셀 · 사진 포함)', labels)
        dlg = self.win.show_export_dialog(exec_=False)
        self.assertIsInstance(dlg, ExportDialog)
        with mock.patch.object(ExportDialog, 'exec_', return_value=ExportDialog.Accepted), \
                mock.patch.object(ExportDialog, 'options', return_value={'fmt': 'csv', 'since': date(2026, 10, 9),
                                                                         'until': date(2026, 10, 9), 'period': '2026-10-09'}):
            self.win.show_export_dialog()
        self.assertEqual(self.conn.last('room_export'), {'room_id': 'r1', 'since': '2026-10-09', 'until': '2026-10-09'})


class ChatListExportTests(unittest.TestCase):
    def test_context_menu_and_export_room(self):
        from client.kakao.main_window import MainWindow
        state, _conn = make_demo_state()
        win = MainWindow(state, state.settings)
        self.addCleanup(win.close)
        chats = win.tabs['chats']
        self.assertIn('대화 내용 저장…', [a.text() for a in chats.context_menu_for('r1').actions()])
        dlg = chats.export_room('r1', exec_=False)
        self.assertIsInstance(dlg, ExportDialog)
        self.assertIn('r1', win.room_windows)
        for room in list(win.room_windows.values()):
            room.close()


if __name__ == '__main__':
    unittest.main()
