# -*- coding: utf-8 -*-
"""
날짜 고르기 달력 (일정 · 할 일 기한 · 예약 메시지 · 대화 저장 기간의 달력 팝업)

Qt 기본 달력은 초록 동그라미 화살표, 원색 빨강 주말(토요일까지 빨강), 다른 달 날짜와 이번 달 날짜가 똑같은 색,
네모난 선택 칸, '10월 2026' 순서의 머리글이라 앱(KCS Ink)과 어울리지 않았다.
- 머리글: ‹ 2026년 10월 › [오늘]  (가는 꺾쇠 아이콘, 연도 → 월 순서)
- 선택한 날: 강조색 동그라미 + 흰 굵은 글자 / 오늘: 강조색 테두리 고리
- 일요일 calendar_sun, 토요일 calendar_sat (테마 토큰), 다른 달 날짜는 흐리게, 고를 수 없는 날은 더 흐리게
- 칸은 36px 안팎 (누르기 쉬운 크기)
widgets.install_input_controls 가 달력 팝업을 쓰는 모든 날짜 칸에 자동으로 끼운다.
"""

from PyQt5.QtCore import Qt, QDate, QRectF, QLocale
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QTextCharFormat, QTransform
from PyQt5.QtWidgets import QCalendarWidget, QWidget, QHBoxLayout, QLabel, QToolButton, QPushButton

from client.kakao import theme

KOREAN = QLocale(QLocale.Korean, QLocale.SouthKorea)


def _chevron_icon(color, flip=False):
    from client.kakao.widgets import make_icon
    from PyQt5.QtGui import QIcon
    icon = make_icon('back', color, 16)
    if not flip:
        return icon
    pm = icon.pixmap(32, 32).transformed(QTransform().rotate(180))
    return QIcon(pm)


class DatePickerCalendar(QCalendarWidget):
    """앱 디자인의 날짜 달력. 기본 탐색 막대 대신 직접 만든 머리글을 맨 위에 둔다"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('kcsDatePicker')
        self.setLocale(KOREAN)
        self.setFirstDayOfWeek(Qt.Sunday)
        self.setGridVisible(False)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        self.setNavigationBarVisible(False)
        self._build_header()
        self._apply_formats()
        self.setMinimumSize(theme.px(288), theme.px(292))
        self.setStyleSheet(self._qss())
        self.currentPageChanged.connect(lambda _y, _m: self._update_title())
        self._update_title()

    # ---- 머리글: ‹ 2026년 10월 ›            [오늘]
    def _build_header(self):
        self.header = QWidget(self)
        self.header.setObjectName('datePickerHeader')
        row = QHBoxLayout(self.header)
        row.setContentsMargins(theme.sp('s'), theme.sp('s'), theme.sp('s'), 2)
        row.setSpacing(2)
        self.prev_button = self._nav_button(_chevron_icon(theme.c('text_sub')), '이전 달', self.showPreviousMonth)
        self.title_label = QLabel()
        self.title_label.setObjectName('datePickerTitle')
        self.next_button = self._nav_button(_chevron_icon(theme.c('text_sub'), flip=True), '다음 달', self.showNextMonth)
        self.today_button = QPushButton('오늘')
        self.today_button.setObjectName('datePickerToday')
        self.today_button.setCursor(Qt.PointingHandCursor)
        self.today_button.setFocusPolicy(Qt.NoFocus)
        self.today_button.clicked.connect(self.go_today)
        row.addWidget(self.title_label)
        row.addSpacing(theme.sp('xs'))
        row.addWidget(self.prev_button)
        row.addWidget(self.next_button)
        row.addStretch(1)
        row.addWidget(self.today_button)
        self.layout().insertWidget(0, self.header)

    def _nav_button(self, icon, name, slot):
        button = QToolButton()
        button.setObjectName('datePickerNav')
        button.setIcon(icon)
        button.setAccessibleName(name)
        button.setToolTip(name)
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.NoFocus)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _update_title(self):
        self.title_label.setText(f'{self.yearShown()}년 {self.monthShown()}월')

    def go_today(self):
        """오늘로 옮기고 고른다 (날짜 칸에도 바로 들어간다 - 팝업은 clicked 로 닫힌다)"""
        today = QDate.currentDate()
        self.setCurrentPage(today.year(), today.month())
        if self.minimumDate() <= today <= self.maximumDate():
            self.setSelectedDate(today)
            self.clicked.emit(today)
            self.activated.emit(today)

    # ---- 요일 머리줄 색 (일 빨강 · 토 파랑 · 평일 보조 글자색)
    def _apply_formats(self):
        caption = QFont(self.font())
        caption.setPixelSize(theme.fs('caption'))
        for day in range(1, 8):
            fmt = QTextCharFormat()
            fmt.setFont(caption)
            color = {Qt.Sunday: 'calendar_sun', Qt.Saturday: 'calendar_sat'}.get(day, 'text_hint')
            fmt.setForeground(QColor(theme.c(color)))
            self.setWeekdayTextFormat(Qt.DayOfWeek(day), fmt)
        header = QTextCharFormat()
        header.setFont(caption)
        self.setHeaderTextFormat(header)

    def _qss(self):
        c = theme.c
        return f"""
            QCalendarWidget#kcsDatePicker {{ background: {c('bg')}; }}
            QWidget#datePickerHeader {{ background: {c('bg')}; }}
            QLabel#datePickerTitle {{ color: {c('text')}; font-size: {theme.fs('emphasis')}px; font-weight: bold;
                padding-left: 6px; }}
            QToolButton#datePickerNav {{ border: none; border-radius: {theme.px(14)}px; padding: 5px;
                min-width: {theme.px(18)}px; min-height: {theme.px(18)}px; }}
            QToolButton#datePickerNav:hover {{ background: {c('bg_hover')}; }}
            QToolButton#datePickerNav:pressed {{ background: {c('bg_selected')}; }}
            QPushButton#datePickerToday {{ background: transparent; color: {c('link')}; border: none;
                border-radius: {theme.px(13)}px; padding: 4px 12px; font-size: {theme.fs('meta')}px; font-weight: bold; }}
            QPushButton#datePickerToday:hover {{ background: {c('bg_hover')}; }}
            QPushButton#datePickerToday:pressed {{ background: {c('bg_selected')}; }}
            QCalendarWidget#kcsDatePicker QWidget {{ alternate-background-color: {c('bg')}; }}
            QCalendarWidget#kcsDatePicker QAbstractItemView {{ background: {c('bg')}; color: {c('text')};
                border: none; outline: 0; selection-background-color: transparent; selection-color: {c('text')}; }}
        """

    # ---- 날짜 칸
    def paintCell(self, painter, rect, date):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(rect, QColor(theme.c('bg')))
        in_month = date.month() == self.monthShown()
        enabled = self.minimumDate() <= date <= self.maximumDate()
        selected = date == self.selectedDate()
        today = date == QDate.currentDate()
        accent = QColor(theme.c('yellow'))
        size = min(rect.width(), rect.height()) - theme.px(6)
        circle = QRectF(rect.center().x() - size / 2 + 0.5, rect.center().y() - size / 2 + 0.5, size, size)
        font = QFont(self.font())
        font.setPixelSize(theme.fs('body'))
        if selected and enabled:
            painter.setPen(Qt.NoPen)
            painter.setBrush(accent)
            painter.drawEllipse(circle)
            color = QColor(theme.c('on_accent'))
            font.setBold(True)
        else:
            weekday = date.dayOfWeek()      # 1 월 … 7 일
            key = 'calendar_sun' if weekday == 7 else 'calendar_sat' if weekday == 6 else 'text'
            color = QColor(theme.c(key))
            if today:
                painter.setPen(QPen(accent, 1.5))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(circle.adjusted(0.75, 0.75, -0.75, -0.75))
                font.setBold(True)
            if not in_month:
                color.setAlphaF(0.38)          # 앞뒤 달 날짜는 흐리게
            if not enabled:
                color = QColor(theme.c('text_hint'))
                color.setAlphaF(0.3)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignCenter, str(date.day()))
        painter.restore()
