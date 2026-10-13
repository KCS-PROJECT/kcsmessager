# -*- coding: utf-8 -*-
"""입력 컨트롤 디자인: 콤보박스 화살표 칸 · 시간/날짜 칸의 위아래 단추가 기본 모양(네모 칸 · 끊긴 선)으로
그려지지 않도록 앱 전역 스타일을 주고, 콤보 목록은 칸 바로 아래 같은 너비로 QSS 줄 높이 · 선택 색을 따른다"""

import unittest

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate, QVBoxLayout, QWidget

from tests.kakao_fakes import app, make_demo_state

from client.kakao import main_window, theme
from client.kakao.dnd import DndDialog
from client.kakao.widgets import input_controls_qss, install_input_controls


class InputControlsTests(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        main_window.apply_app_theme(self.state.settings)
        self.addCleanup(main_window.apply_app_theme, self.state.settings)

    def test_app_stylesheet_styles_arrow_and_spin_buttons(self):
        qss = app().styleSheet()
        self.assertIn(theme.base_qss().strip()[:40], qss)
        for rule in ('QComboBox::drop-down', 'QComboBox::down-arrow', 'QAbstractSpinBox::up-button',
                     'QAbstractSpinBox::down-button', 'QAbstractSpinBox::up-arrow', 'QAbstractSpinBox::down-arrow',
                     'combobox-popup: 0', 'QComboBox QAbstractItemView::item'):
            self.assertIn(rule, qss)
        self.assertIn('border: none', qss.split('QComboBox::drop-down', 1)[1].split('}', 1)[0])

    def test_arrow_images_exist_for_light_and_dark(self):
        import os
        import re
        for dark in (False, True):
            theme.set_dark(dark)
            try:
                paths = re.findall(r'url\("([^"]+)"\)', input_controls_qss())
            finally:
                theme.set_dark(False)
            self.assertGreaterEqual(len(set(paths)), 4)            # 아래 · 위 · (꺼짐) 아래 · 위
            for path in paths:
                self.assertTrue(os.path.exists(path), path)

    def test_combo_list_uses_styled_delegate_and_opens_below(self):
        dlg = DndDialog(self.state, self.state.settings)
        self.addCleanup(dlg.close)
        dlg.show()
        combo = dlg.vip_combo
        self.assertGreater(combo.count(), 0)
        self.assertIsInstance(combo.itemDelegate(), QStyledItemDelegate)   # QSS 줄 높이 · 선택 색
        popup = combo.view().parentWidget()
        self.assertTrue(popup.property('kcsPopup'))
        self.assertEqual(popup.frameShape(), popup.NoFrame)
        self.assertTrue(popup.windowFlags() & Qt.NoDropShadowWindowHint)   # macOS 진한 창 윤곽선 없음
        combo.showPopup()
        self.addCleanup(combo.hidePopup)
        top_left = combo.mapToGlobal(combo.rect().bottomLeft())
        self.assertGreater(popup.geometry().top(), top_left.y())           # 칸을 덮지 않고 아래로
        self.assertEqual(popup.geometry().left(), combo.mapToGlobal(combo.rect().topLeft()).x())
        self.assertGreaterEqual(popup.width(), combo.width())

    def test_install_is_idempotent_and_keeps_custom_delegate(self):
        install_input_controls(app())
        first = app()._combo_delegate_filter
        install_input_controls(app())
        self.assertIs(app()._combo_delegate_filter, first)
        host = QWidget()
        self.addCleanup(host.close)
        custom = QStyledItemDelegate()
        combo = QComboBox()
        combo.setItemDelegate(custom)
        QVBoxLayout(host).addWidget(combo)
        host.show()
        self.assertIs(combo.itemDelegate(), custom)                        # 이미 QSS 를 따르는 위임자는 그대로


if __name__ == '__main__':
    unittest.main()


class DatePickerTests(unittest.TestCase):
    """날짜 고르기 달력: 기본 달력 대신 앱 디자인 달력 (일정 · 할 일 기한 · 예약 메시지 · 대화 저장 기간)"""

    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        main_window.apply_app_theme(self.state.settings)

    def test_every_calendar_popup_uses_app_calendar(self):
        from PyQt5.QtCore import QDate
        from PyQt5.QtWidgets import QDateTimeEdit, QDateEdit
        from client.kakao.date_picker import DatePickerCalendar
        from client.kakao.event_dialog import EventDialog
        dlg = EventDialog(self.state)
        self.addCleanup(dlg.close)
        dlg.show()
        for edit in (dlg.start_edit, dlg.end_edit):
            self.assertIsInstance(edit.calendarWidget(), DatePickerCalendar)
        plain = QDateEdit()                                                     # 달력 팝업이 없는 칸은 건드리지 않는다
        plain.show()
        self.addCleanup(plain.close)
        self.assertFalse(plain.calendarPopup())
        cal = dlg.start_edit.calendarWidget()
        cal.setCurrentPage(2027, 3)
        self.assertEqual(cal.title_label.text(), '2027년 3월')                  # 연도 → 월 순서
        self.assertFalse(cal.isNavigationBarVisible())
        cal.next_button.click()
        self.assertEqual((cal.yearShown(), cal.monthShown()), (2027, 4))
        cal.go_today()                                                          # 오늘로 옮기고 칸에도 넣는다
        self.assertEqual(dlg.start_edit.date(), QDate.currentDate())
        self.assertFalse(cal.grab().isNull())                                   # 칸 그리기 (선택 · 오늘 · 다른 달)
        edit = QDateTimeEdit()
        edit.setCalendarPopup(True)
        edit.show()
        self.addCleanup(edit.close)
        self.assertIsInstance(edit.calendarWidget(), DatePickerCalendar)
