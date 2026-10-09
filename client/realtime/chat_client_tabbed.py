# -*- coding: utf-8 -*-
"""
KCS Messenger - Tabbed Main Screen Version
로그인 후 탭 기반 메인 화면으로 진입
Tab 1: 친구 목록 (온라인 상태)
Tab 2: 채팅방 목록 (대화 이력)
"""

import sys
import os
import socket
import json
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
                             QLabel, QDialog, QComboBox, QScrollArea, QFrame,
                             QListWidget, QListWidgetItem, QMenu, QTabWidget,
                             QSplitter)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QPixmap

# Import icon manager and theme manager
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.icon_manager import icon_manager
from utils.theme_manager import theme_manager

# High DPI 지원
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# ============================================================================
# 로그인 다이얼로그
# ============================================================================

class LoginDialog(QDialog):
    """로그인 다이얼로그"""
    def __init__(self):
        super().__init__()
        self.username = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('KCS Messenger - 로그인')
        self.setFixedSize(300, 150)

        layout = QVBoxLayout()

        # 제목
        title = QLabel('KCS Messenger')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 18px; font-weight: bold; margin: 10px;')
        layout.addWidget(title)

        # 사용자 선택
        user_label = QLabel('사용자 선택:')
        layout.addWidget(user_label)

        self.user_combo = QComboBox()
        self.user_combo.addItems(['홍길동', '김철수', '이영희', '박민수', '최지우'])
        layout.addWidget(self.user_combo)

        # 로그인 버튼
        login_btn = QPushButton('로그인')
        login_btn.clicked.connect(self.accept_login)
        layout.addWidget(login_btn)

        self.setLayout(layout)

    def accept_login(self):
        self.username = self.user_combo.currentText()
        self.accept()


# ============================================================================
# 메시지 버블 위젯
# ============================================================================

class BubbleWithTail(QWidget):
    """카카오톡 스타일 말풍선 (꼬리 포함)"""
    def __init__(self, text, is_mine, sender_name="", timestamp="", parent=None):
        super().__init__(parent)
        self.text = text
        self.is_mine = is_mine
        self.sender_name = sender_name
        self.timestamp = timestamp

        # 폰트 설정 (크로스 플랫폼 지원)
        font_family = QFont()
        font_family.setFamilies(['Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕', 'Noto Sans CJK KR', 'Arial'])

        self.font = QFont()
        self.font.setFamilies(['Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕', 'Noto Sans CJK KR', 'Arial'])
        self.font.setPointSize(10)

        self.name_font = QFont()
        self.name_font.setFamilies(['Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕', 'Noto Sans CJK KR', 'Arial'])
        self.name_font.setPointSize(9)

        # 크기 계산
        self.calculate_size()

    def calculate_size(self):
        """텍스트 크기에 따라 위젯 크기 계산 (개선)"""
        from PyQt5.QtGui import QFontMetrics
        from PyQt5.QtCore import QRect

        fm = QFontMetrics(self.font)

        # 최대 너비 280px (패딩 제외)
        max_text_width = 260

        # boundingRect를 사용하여 정확한 텍스트 영역 계산
        text_rect = fm.boundingRect(
            QRect(0, 0, max_text_width, 1000),
            Qt.AlignLeft | Qt.TextWordWrap,
            self.text
        )

        # 실제 필요한 크기 계산 (패딩 포함)
        bubble_width = min(text_rect.width() + 32, max_text_width + 32)
        bubble_height = text_rect.height() + 24

        # 최소 크기 보장
        bubble_width = max(bubble_width, 60)
        bubble_height = max(bubble_height, 40)

        # 발신자 이름 공간 추가 (상대방 메시지만)
        y_offset = 0
        if not self.is_mine and self.sender_name:
            y_offset = 22
            bubble_height += y_offset

        # 꼬리 공간 추가
        total_width = bubble_width + 20
        self.setFixedSize(int(total_width), int(bubble_height + 10))

    def paintEvent(self, event):
        painter = QPainter(self)
        # 고품질 렌더링 힌트 설정
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.HighQualityAntialiasing, True)

        # 여백
        y_offset = 0

        # 발신자 이름 표시 (상대방 메시지만)
        if not self.is_mine and self.sender_name:
            painter.setFont(self.name_font)
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(15, 17, self.sender_name)
            y_offset = 22

        # 말풍선 색상
        if self.is_mine:
            bubble_color = QColor(255, 228, 0)  # 카카오톡 노란색
        else:
            bubble_color = QColor(255, 255, 255)  # 흰색

        # 말풍선 테두리
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.setBrush(QBrush(bubble_color))

        # 말풍선 그리기
        bubble_rect = self.rect().adjusted(10, y_offset + 5, -10, -5)
        painter.drawRoundedRect(bubble_rect, 18, 18)

        # 꼬리 그리기
        tail_path = QPainterPath()
        if self.is_mine:
            # 오른쪽 꼬리
            tail_x = bubble_rect.right()
            tail_y = bubble_rect.top() + 10
            tail_path.moveTo(tail_x, tail_y)
            tail_path.lineTo(tail_x + 8, tail_y + 5)
            tail_path.lineTo(tail_x, tail_y + 10)
        else:
            # 왼쪽 꼬리
            tail_x = bubble_rect.left()
            tail_y = bubble_rect.top() + 10
            tail_path.moveTo(tail_x, tail_y)
            tail_path.lineTo(tail_x - 8, tail_y + 5)
            tail_path.lineTo(tail_x, tail_y + 10)

        painter.drawPath(tail_path)
        painter.fillPath(tail_path, QBrush(bubble_color))

        # 텍스트 그리기 (충분한 패딩 확보)
        painter.setFont(self.font)
        painter.setPen(QColor(0, 0, 0))
        text_rect = bubble_rect.adjusted(16, 8, -16, -8)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.text)


# ============================================================================
# 채팅 창 (개별 1:1 대화)
# ============================================================================

class ChatWindow(QWidget):
    """개별 1:1 채팅 창"""
    message_sent = pyqtSignal(str, str)  # (target_user, message)

    def __init__(self, target_user, my_username, parent=None):
        super().__init__(parent)
        self.target_user = target_user
        self.my_username = my_username
        self.messages = []  # [(sender, message, timestamp)]

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f'KCS Messenger - {self.target_user}')
        self.resize(400, 600)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 상단 바 (상대방 이름)
        header = QWidget()
        header.setStyleSheet('background-color: #FFFFFF; padding: 10px; border-bottom: 1px solid #E0E0E0;')
        header_layout = QHBoxLayout()

        name_label = QLabel(self.target_user)
        name_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #333333;')
        header_layout.addWidget(name_label)
        header.setLayout(header_layout)
        layout.addWidget(header)

        # 메시지 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet('background-color: #ABC1D1; border: none;')

        self.message_container = QWidget()
        self.message_layout = QVBoxLayout()
        self.message_layout.addStretch()
        self.message_container.setLayout(self.message_layout)

        self.scroll_area.setWidget(self.message_container)
        layout.addWidget(self.scroll_area)

        # 입력 영역
        input_widget = QWidget()
        input_widget.setStyleSheet('background-color: white; padding: 10px;')
        input_layout = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText('메시지를 입력하세요...')
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        send_btn = QPushButton('전송')
        send_btn.setStyleSheet('background-color: #FFE400; border: none; padding: 8px 20px; font-weight: bold;')
        send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(send_btn)

        input_widget.setLayout(input_layout)
        layout.addWidget(input_widget)

        self.setLayout(layout)

    def send_message(self):
        """메시지 전송"""
        message = self.input_field.text().strip()
        if message:
            self.message_sent.emit(self.target_user, message)
            self.add_message(self.my_username, message, datetime.now().strftime('%H:%M'), is_mine=True)
            self.input_field.clear()

    def add_message(self, sender, text, timestamp, is_mine=False):
        """메시지 추가"""
        self.messages.append((sender, text, timestamp))

        # 메시지 버블 생성
        bubble = BubbleWithTail(
            text=text,
            is_mine=is_mine,
            sender_name=sender if not is_mine else "",
            timestamp=timestamp
        )

        # 레이아웃에 추가
        msg_layout = QHBoxLayout()
        if is_mine:
            msg_layout.addStretch()
            msg_layout.addWidget(bubble)
        else:
            msg_layout.addWidget(bubble)
            msg_layout.addStretch()

        # stretch 위에 삽입
        self.message_layout.insertLayout(self.message_layout.count() - 1, msg_layout)

        # 스크롤 최하단으로
        QTimer.singleShot(100, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        """스크롤을 최하단으로 이동"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """창 닫기 이벤트 - 숨김 처리"""
        self.hide()
        event.ignore()


# ============================================================================
# 친구 목록 아이템 위젯 (뱃지 포함)
# ============================================================================

class FriendListItemWidget(QWidget):
    """친구 목록 아이템 (온라인 상태 + 이름 + 읽지 않은 메시지 뱃지)"""
    def __init__(self, username, is_online, unread_count=0, parent=None):
        super().__init__(parent)
        self.username = username
        self.is_online = is_online
        self.unread_count = unread_count

        self.init_ui()

    def init_ui(self):
        # 위젯 배경 및 border 설정
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F0F0F0;
            }
            QWidget:hover {
                background-color: #F8F8F8;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(10)

        # 온라인 상태 아이콘 (SVG)
        status_label = QLabel()
        if self.is_online:
            pixmap = icon_manager.get_pixmap('status-online', size=12, color='#00D000')
        else:
            pixmap = icon_manager.get_pixmap('status-offline', size=12, color='#999999')
        status_label.setPixmap(pixmap)
        status_label.setFixedSize(12, 12)
        layout.addWidget(status_label)

        # 사용자 이름
        text_color = "#333333" if self.is_online else "#999999"
        name_label = QLabel(self.username)
        name_label.setStyleSheet(f"""
            QLabel {{
                font-size: 15px;
                font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕', 'Noto Sans CJK KR', 'Arial';
                color: {text_color};
                background-color: transparent;
                border: none;
            }}
        """)
        layout.addWidget(name_label)

        # 빈 공간
        layout.addStretch()

        # 읽지 않은 메시지 뱃지 (0보다 클 때만 표시)
        if self.unread_count > 0:
            self.badge_label = QLabel(str(self.unread_count))
            self.badge_label.setFixedSize(24, 24)
            self.badge_label.setAlignment(Qt.AlignCenter)
            self.badge_label.setStyleSheet("""
                QLabel {
                    background-color: #FF3B30;
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 12px;
                    border: none;
                    font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', 'Arial';
                }
            """)
            layout.addWidget(self.badge_label)
        else:
            self.badge_label = None

    def update_unread_count(self, count):
        """읽지 않은 메시지 수 업데이트"""
        self.unread_count = count

        # 뱃지 표시 여부 결정
        if count > 0:
            if self.badge_label is None:
                # 뱃지 새로 생성
                self.badge_label = QLabel(str(count))
                self.badge_label.setFixedSize(24, 24)
                self.badge_label.setAlignment(Qt.AlignCenter)
                self.badge_label.setStyleSheet("""
                    QLabel {
                        background-color: #FF3B30;
                        color: white;
                        font-size: 11px;
                        font-weight: bold;
                        border-radius: 12px;
                        border: none;
                        font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', 'Arial';
                    }
                """)
                self.layout().addWidget(self.badge_label)
            else:
                # 기존 뱃지 업데이트
                self.badge_label.setText(str(count))
        else:
            # 뱃지 제거
            if self.badge_label is not None:
                self.badge_label.deleteLater()
                self.badge_label = None


# ============================================================================
# 친구 목록 탭
# ============================================================================

class FriendsTab(QWidget):
    """친구 목록 탭"""
    chat_requested = pyqtSignal(str)  # username

    def __init__(self, my_username, parent=None):
        super().__init__(parent)
        self.my_username = my_username
        self.all_users = []  # 전체 사용자 목록
        self.online_users = set()  # 온라인 사용자 집합
        self.unread_counts = {}  # 읽지 않은 메시지 카운트 {username: count}
        self.item_widgets = {}  # 아이템 위젯 캐시 {username: FriendListItemWidget}

        # 카카오톡 스타일 기능 데이터
        self.favorites = set()  # 즐겨찾기 사용자 집합
        self.section_states = {
            'favorites': True,
            'updated_profile': True,
            'birthday': True,
            'channels': True,
            'online': True,
            'offline': False,
        }

        # 샘플 데이터
        self.profile_updates = {
            '노승한': datetime(2025, 10, 14, 15, 30),
            '정현아': datetime(2025, 10, 13, 10, 20),
            '박희정': datetime(2025, 10, 12, 18, 45)
        }

        self.birthdays = {
            '도기현': (10, 16),
            '장모님': (10, 16),
            '조원택': (10, 16),
        }

        # 채널 데이터
        self.channels = [
            {
                'name': 'KCS 공지사항',
                'description': '회사 공지 및 소식',
                'verified': True,
                'icon_color': '#4A90E2'
            },
            {
                'name': 'IT 개발팀',
                'description': '개발 관련 정보 공유',
                'verified': False,
                'icon_color': '#5CB85C'
            },
            {
                'name': '자유 게시판',
                'description': '자유로운 소통 공간',
                'verified': False,
                'icon_color': '#F0AD4E'
            }
        ]

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 헤더 (친구 + 검색/추가 버튼)
        header = self.create_header()
        layout.addWidget(header)

        # 내 프로필 카드
        my_profile = self.create_my_profile()
        layout.addWidget(my_profile)

        # 친구 목록 (스크롤 가능)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: white; }")

        # 친구 목록 컨테이너
        friends_container = QWidget()
        friends_layout = QVBoxLayout()
        friends_layout.setContentsMargins(0, 0, 0, 0)
        friends_layout.setSpacing(0)

        # 친구 목록
        self.user_list = QListWidget()
        self.user_list.setStyleSheet('''
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                font-size: 14px;
                color: #333333;
            }
            QListWidget::item {
                padding: 0px;
                border: none;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
            }
            QListWidget::item:selected {
                background-color: #E8E8E8;
            }
        ''')

        # 더블클릭 및 우클릭 이벤트
        self.user_list.itemDoubleClicked.connect(self.on_user_double_click)
        self.user_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.user_list.customContextMenuRequested.connect(self.show_context_menu)

        friends_layout.addWidget(self.user_list)
        friends_container.setLayout(friends_layout)
        scroll_area.setWidget(friends_container)

        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def create_header(self):
        """헤더 생성 (친구 + 검색/추가 버튼)"""
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #F8F8F8;
                border-bottom: 1px solid #E0E0E0;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)

        # 친구 제목
        title = QLabel("친구")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333333;
            }
        """)
        layout.addWidget(title)

        layout.addStretch()

        # 검색 버튼 (SVG)
        search_btn = QPushButton()
        search_btn.setIcon(icon_manager.get_icon('search', size=20, color='#333333'))
        search_btn.setIconSize(QSize(20, 20))
        search_btn.setFixedSize(40, 40)
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
        """)
        layout.addWidget(search_btn)

        # 친구 추가 버튼 (SVG)
        add_btn = QPushButton()
        add_btn.setIcon(icon_manager.get_icon('add', size=20, color='#333333'))
        add_btn.setIconSize(QSize(20, 20))
        add_btn.setFixedSize(40, 40)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
        """)
        layout.addWidget(add_btn)

        header.setLayout(layout)
        return header

    def create_my_profile(self):
        """내 프로필 카드"""
        profile_card = QWidget()
        profile_card.setFixedHeight(80)
        profile_card.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                border-bottom: 1px solid #E8E8E8;
            }
        """)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)

        # 프로필 이미지 (원형)
        profile_img = QLabel()
        profile_img.setFixedSize(50, 50)
        profile_img.setStyleSheet("""
            QLabel {
                background-color: #4A90E2;
                border-radius: 25px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        profile_img.setAlignment(Qt.AlignCenter)
        profile_img.setText(self.my_username[0].upper() if self.my_username else "?")
        layout.addWidget(profile_img)

        # 이름
        name_label = QLabel(self.my_username)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333333;
            }
        """)
        layout.addWidget(name_label)

        layout.addStretch()

        profile_card.setLayout(layout)
        return profile_card

    def update_all_users(self, all_users, online_users):
        """전체 사용자 목록 + 온라인 상태 업데이트"""
        self.all_users = all_users
        self.online_users = set(online_users)
        self.refresh_user_list()

    def update_user_status(self, username, status):
        """특정 사용자 상태 업데이트"""
        if status == 'online':
            self.online_users.add(username)
        elif status == 'offline':
            self.online_users.discard(username)
        self.refresh_user_list()

    def refresh_user_list(self):
        """사용자 목록 UI 갱신 (카카오톡 스타일 섹션 포함)"""
        self.user_list.clear()
        self.item_widgets.clear()

        # 상단 간격
        self._add_spacer(20)

        # 사용자 분류
        favorite_list = [u for u in self.all_users if u in self.favorites and u != self.my_username]
        online_list = [u for u in self.all_users if u in self.online_users and u != self.my_username and u not in self.favorites]
        offline_list = [u for u in self.all_users if u not in self.online_users and u != self.my_username and u not in self.favorites]

        favorite_list.sort()
        online_list.sort()
        offline_list.sort()

        # 1. 즐겨찾기 섹션
        if favorite_list:
            self._add_section('favorites', '즐겨찾기', len(favorite_list), favorite_list, is_online=True)

        # 2. 업데이트한 프로필 섹션
        updated_profiles = self._get_recently_updated_profiles()
        if updated_profiles:
            if favorite_list:
                self._add_spacer(20)
            self._add_updated_profile_section(updated_profiles)

        # 3. 생일 섹션
        birthday_list = [u for u in self.all_users if u in self.birthdays and u != self.my_username]
        if birthday_list:
            if favorite_list or updated_profiles:
                self._add_spacer(20)
            self._add_birthday_section(birthday_list)

        # 4. 채널 섹션
        if self.channels:
            if favorite_list or updated_profiles or birthday_list:
                self._add_spacer(20)
            self._add_channel_section()

        # 5. 온라인 친구 섹션
        if online_list:
            if favorite_list or updated_profiles or birthday_list or self.channels:
                self._add_spacer(20)
            self._add_section('online', '온라인 친구', len(online_list), online_list, is_online=True)

        # 6. 오프라인 친구 섹션
        if offline_list:
            if favorite_list or updated_profiles or birthday_list or self.channels or online_list:
                self._add_spacer(20)
            self._add_section('offline', '오프라인 친구', len(offline_list), offline_list, is_online=False)

    def _add_spacer(self, height):
        """간격 추가"""
        spacer = QWidget()
        spacer.setFixedHeight(height)
        spacer.setStyleSheet("background-color: #FFFFFF;")
        spacer_item = QListWidgetItem()
        spacer_item.setSizeHint(QSize(0, height))
        spacer_item.setFlags(Qt.NoItemFlags)
        self.user_list.addItem(spacer_item)
        self.user_list.setItemWidget(spacer_item, spacer)

    def _add_section(self, section_name, title, count, user_list, is_online):
        """일반 섹션 추가"""
        # 헤더 추가
        header = self.create_section_header(section_name, title, count)
        header_item = QListWidgetItem()
        header_item.setSizeHint(header.sizeHint())
        header_item.setFlags(Qt.NoItemFlags)
        self.user_list.addItem(header_item)
        self.user_list.setItemWidget(header_item, header)

        # 섹션이 펼쳐져 있으면 아이템 추가
        if self.section_states.get(section_name, True):
            for user in user_list:
                unread = self.unread_counts.get(user, 0)
                is_favorite = user in self.favorites
                widget = FriendListItemWidget(user, is_online=is_online, unread_count=unread)
                self.item_widgets[user] = widget

                item = QListWidgetItem()
                item.setData(Qt.UserRole, user)
                item.setSizeHint(widget.sizeHint())
                self.user_list.addItem(item)
                self.user_list.setItemWidget(item, widget)

    def _add_birthday_section(self, birthday_list):
        """생일 섹션 추가"""
        header = self.create_section_header('birthday', '생일인 친구', len(birthday_list))
        header_item = QListWidgetItem()
        header_item.setSizeHint(header.sizeHint())
        header_item.setFlags(Qt.NoItemFlags)
        self.user_list.addItem(header_item)
        self.user_list.setItemWidget(header_item, header)

        if self.section_states.get('birthday', True):
            for user in birthday_list:
                birthday_widget = self._create_birthday_item(user)
                item = QListWidgetItem()
                item.setSizeHint(birthday_widget.sizeHint())
                item.setFlags(Qt.NoItemFlags)
                self.user_list.addItem(item)
                self.user_list.setItemWidget(item, birthday_widget)

    def _create_birthday_item(self, username):
        """생일 아이템 위젯 생성"""
        widget = QWidget()
        widget.setFixedHeight(70)
        widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F0F0F0;
            }
            QWidget:hover {
                background-color: #F8F8F8;
            }
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)

        # 프로필 이미지
        profile_img = QLabel()
        profile_img.setFixedSize(50, 50)
        profile_img.setStyleSheet("""
            QLabel {
                background-color: #4A90E2;
                border-radius: 25px;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        profile_img.setAlignment(Qt.AlignCenter)
        profile_img.setText(username[0].upper() if username else "?")
        layout.addWidget(profile_img)

        # 정보 영역
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(username)
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #333333;")
        info_layout.addWidget(name_label)

        birthday_info = QLabel("🎂 오늘 10월 16일")
        birthday_info.setStyleSheet("font-size: 12px; color: #666666;")
        info_layout.addWidget(birthday_info)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 선물하기 버튼
        gift_btn = QPushButton("선물하기")
        gift_btn.setFixedSize(80, 32)
        gift_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3C;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4A4A4C;
            }
        """)
        gift_btn.clicked.connect(lambda: self._on_gift_click(username))
        layout.addWidget(gift_btn)

        return widget

    def _on_gift_click(self, username):
        """선물하기 버튼 클릭"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "선물하기",
            f"{username}님에게 선물을 보내시겠습니까?\n(추후 구현 예정)")

    def _get_recently_updated_profiles(self):
        """최근 7일 이내 프로필 업데이트한 사용자 목록 반환"""
        from datetime import timedelta
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)

        recent_updates = []
        for username, update_time in self.profile_updates.items():
            if username != self.my_username and update_time >= seven_days_ago:
                recent_updates.append((username, update_time))

        # 최신 업데이트 순으로 정렬
        recent_updates.sort(key=lambda x: x[1], reverse=True)
        return [username for username, _ in recent_updates]

    def _add_updated_profile_section(self, updated_profiles):
        """업데이트한 프로필 섹션 추가 (가로 스크롤)"""
        header = self.create_section_header('updated_profile', '업데이트한 프로필', len(updated_profiles))
        header_item = QListWidgetItem()
        header_item.setSizeHint(header.sizeHint())
        header_item.setFlags(Qt.NoItemFlags)
        self.user_list.addItem(header_item)
        self.user_list.setItemWidget(header_item, header)

        if self.section_states.get('updated_profile', True):
            # 가로 스크롤 컨테이너
            scroll_widget = self._create_horizontal_profile_scroll(updated_profiles)
            scroll_item = QListWidgetItem()
            scroll_item.setSizeHint(QSize(0, 120))
            scroll_item.setFlags(Qt.NoItemFlags)
            self.user_list.addItem(scroll_item)
            self.user_list.setItemWidget(scroll_item, scroll_widget)

    def _create_horizontal_profile_scroll(self, updated_profiles):
        """가로 스크롤 프로필 위젯 생성"""
        container = QWidget()
        container.setFixedHeight(120)
        container.setStyleSheet("background-color: #FFFFFF;")

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 10, 0, 10)

        # 가로 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(False)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FFFFFF;
            }
            QScrollBar:horizontal {
                height: 6px;
                background-color: #F0F0F0;
            }
            QScrollBar::handle:horizontal {
                background-color: #CCCCCC;
                border-radius: 3px;
            }
        """)

        # 프로필 아이템 컨테이너
        profiles_widget = QWidget()
        profiles_layout = QHBoxLayout(profiles_widget)
        profiles_layout.setContentsMargins(15, 0, 15, 0)
        profiles_layout.setSpacing(15)

        for username in updated_profiles:
            profile_item = self._create_profile_update_item(username)
            profiles_layout.addWidget(profile_item)

        profiles_layout.addStretch()
        scroll_area.setWidget(profiles_widget)
        main_layout.addWidget(scroll_area)

        return container

    def _create_profile_update_item(self, username):
        """업데이트한 프로필 아이템 생성"""
        widget = QWidget()
        widget.setFixedSize(70, 90)
        widget.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)

        # 프로필 이미지 컨테이너 (오렌지 테두리 + 점)
        profile_container = QWidget()
        profile_container.setFixedSize(60, 60)

        # 원형 프로필 이미지
        profile_img = QLabel(profile_container)
        profile_img.setFixedSize(56, 56)
        profile_img.setStyleSheet("""
            QLabel {
                background-color: #4A90E2;
                border: 2px solid #FF6B00;
                border-radius: 28px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        profile_img.setAlignment(Qt.AlignCenter)
        profile_img.setText(username[0].upper() if username else "?")
        profile_img.move(2, 2)

        # 업데이트 인디케이터 (오렌지 점)
        indicator = QLabel(profile_container)
        indicator.setFixedSize(14, 14)
        indicator.setStyleSheet("""
            QLabel {
                background-color: #FF6B00;
                border: 2px solid #FFFFFF;
                border-radius: 7px;
            }
        """)
        indicator.move(46, 0)

        layout.addWidget(profile_container, alignment=Qt.AlignCenter)

        # 이름
        name_label = QLabel(username)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #333333;
            }
        """)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # 클릭 이벤트
        widget.mousePressEvent = lambda event: self.chat_requested.emit(username)

        return widget

    def _add_channel_section(self):
        """채널 섹션 추가"""
        header = self.create_section_header('channels', '채널', len(self.channels))
        header_item = QListWidgetItem()
        header_item.setSizeHint(header.sizeHint())
        header_item.setFlags(Qt.NoItemFlags)
        self.user_list.addItem(header_item)
        self.user_list.setItemWidget(header_item, header)

        if self.section_states.get('channels', True):
            for channel in self.channels:
                channel_widget = self._create_channel_item(channel)
                item = QListWidgetItem()
                item.setSizeHint(channel_widget.sizeHint())
                item.setFlags(Qt.NoItemFlags)
                self.user_list.addItem(item)
                self.user_list.setItemWidget(item, channel_widget)

    def _create_channel_item(self, channel):
        """채널 아이템 위젯 생성"""
        widget = QWidget()
        widget.setFixedHeight(70)
        widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #F0F0F0;
            }
            QWidget:hover {
                background-color: #F8F8F8;
            }
        """)
        widget.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(15)

        # 채널 아이콘
        channel_icon = QLabel()
        channel_icon.setFixedSize(50, 50)
        channel_icon.setStyleSheet(f"""
            QLabel {{
                background-color: {channel['icon_color']};
                border-radius: 10px;
            }}
        """)
        channel_icon.setAlignment(Qt.AlignCenter)
        # 채널 아이콘 표시 (SVG 아이콘 사용)
        channel_icon.setPixmap(icon_manager.get_pixmap('channel', size=28, color='#FFFFFF'))
        layout.addWidget(channel_icon)

        # 채널 정보 영역
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 채널 이름 + 인증 배지
        name_container = QHBoxLayout()
        name_container.setSpacing(5)

        name_label = QLabel(channel['name'])
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #333333;")
        name_container.addWidget(name_label)

        if channel.get('verified', False):
            verified_icon = QLabel()
            verified_icon.setPixmap(icon_manager.get_pixmap('verified', size=16, color='#4A90E2'))
            verified_icon.setFixedSize(16, 16)
            name_container.addWidget(verified_icon)

        name_container.addStretch()

        info_layout.addLayout(name_container)

        # 채널 설명
        desc_label = QLabel(channel['description'])
        desc_label.setStyleSheet("font-size: 12px; color: #666666;")
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 클릭 이벤트
        widget.mousePressEvent = lambda event: self._on_channel_click(channel['name'])

        return widget

    def _on_channel_click(self, channel_name):
        """채널 클릭"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, "채널",
            f"{channel_name} 채널을 열었습니다.\n(추후 구현 예정)")

    def create_section_header(self, section_name, title, count=0):
        """섹션 헤더 생성 (접기/펼치기 기능 포함)"""
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("""
            QWidget {
                background-color: #F9F9F9;
                border-bottom: 1px solid #E8E8E8;
            }
            QWidget:hover {
                background-color: #F0F0F0;
            }
        """)
        header.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        # 화살표 아이콘 (접기/펼치기)
        is_expanded = self.section_states.get(section_name, True)
        arrow_icon = 'chevron-down' if is_expanded else 'chevron-right'
        arrow_label = QLabel()
        arrow_label.setPixmap(icon_manager.get_pixmap(arrow_icon, size=16, color='#666666'))
        arrow_label.setFixedSize(16, 16)
        layout.addWidget(arrow_label)

        # 제목 라벨
        title_text = f"{title} {count}" if count > 0 else title
        label = QLabel(title_text)
        label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #666666;
            }
        """)
        layout.addWidget(label)
        layout.addStretch()

        header.setLayout(layout)

        # 클릭 이벤트로 섹션 토글
        header.mousePressEvent = lambda event: self.toggle_section(section_name)

        return header

    def toggle_section(self, section_name):
        """섹션 접기/펼치기 토글"""
        self.section_states[section_name] = not self.section_states.get(section_name, True)
        self.refresh_user_list()

    def update_unread_count(self, username, count):
        """특정 사용자의 읽지 않은 메시지 카운트 업데이트"""
        self.unread_counts[username] = count

        # 해당 사용자의 위젯이 있으면 업데이트
        if username in self.item_widgets:
            self.item_widgets[username].update_unread_count(count)

    def increment_unread_count(self, username):
        """특정 사용자의 읽지 않은 메시지 카운트 증가"""
        current = self.unread_counts.get(username, 0)
        self.update_unread_count(username, current + 1)

    def clear_unread_count(self, username):
        """특정 사용자의 읽지 않은 메시지 카운트 초기화"""
        self.update_unread_count(username, 0)

    def on_user_double_click(self, item):
        """사용자 더블클릭"""
        username = item.data(Qt.UserRole)
        self.chat_requested.emit(username)

    def show_context_menu(self, position):
        """우클릭 컨텍스트 메뉴"""
        item = self.user_list.itemAt(position)
        if not item:
            return

        username = item.data(Qt.UserRole)
        if not username:  # 헤더나 다른 아이템
            return

        menu = QMenu(self)
        chat_action = menu.addAction(f"💬 {username}님과 대화하기")

        # 즐겨찾기 추가/제거
        if username in self.favorites:
            fav_action = menu.addAction(f"☆ 즐겨찾기 해제")
        else:
            fav_action = menu.addAction(f"★ 즐겨찾기 추가")

        action = menu.exec_(self.user_list.mapToGlobal(position))
        if action == chat_action:
            self.chat_requested.emit(username)
        elif action == fav_action:
            self.toggle_favorite(username)

    def toggle_favorite(self, username):
        """즐겨찾기 추가/제거"""
        if username in self.favorites:
            self.favorites.discard(username)
        else:
            self.favorites.add(username)
        self.refresh_user_list()


# ============================================================================
# 채팅 목록 탭
# ============================================================================

class ChatsTab(QWidget):
    """채팅 목록 탭"""
    chat_opened = pyqtSignal(str)  # username

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chat_list_data = {}  # {username: (last_message, timestamp)}

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # 채팅 목록
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet('''
            QListWidget {
                background-color: white;
                border: none;
                font-size: 14px;
                color: #333333;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #f0f0f0;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        ''')

        # 더블클릭 이벤트
        self.chat_list.itemDoubleClicked.connect(self.on_chat_double_click)

        layout.addWidget(self.chat_list)
        self.setLayout(layout)

    def add_or_update_chat(self, username, message, timestamp):
        """채팅 목록에 추가 또는 업데이트"""
        self.chat_list_data[username] = (message, timestamp)
        self.refresh_chat_list()

    def refresh_chat_list(self):
        """채팅 목록 새로고침"""
        self.chat_list.clear()

        # 최근 시간 순으로 정렬
        sorted_chats = sorted(
            self.chat_list_data.items(),
            key=lambda x: x[1][1],
            reverse=True
        )

        for username, (message, timestamp) in sorted_chats:
            item = QListWidgetItem()

            # 텍스트 표시
            preview = message[:30] + "..." if len(message) > 30 else message
            time_str = timestamp.strftime('%m-%d %H:%M')

            item.setText(f"{username}\n{preview}\n{time_str}")
            item.setData(Qt.UserRole, username)

            self.chat_list.addItem(item)

    def on_chat_double_click(self, item):
        """채팅 더블클릭"""
        username = item.data(Qt.UserRole)
        self.chat_opened.emit(username)


# ============================================================================
# 조직도 탭
# ============================================================================

class OrganizationTab(QWidget):
    """조직도 탭"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # 제목
        title = QLabel("조직도")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(title)

        # 조직도 트리 (추후 확장)
        org_list = QListWidget()
        org_list.setStyleSheet('''
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                padding: 10px;
                color: #333333;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
                color: #333333;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        ''')

        # 샘플 조직도 데이터
        departments = [
            "📁 경영지원팀",
            "  └ 홍길동 (팀장)",
            "  └ 김철수 (사원)",
            "📁 개발팀",
            "  └ 이영희 (팀장)",
            "  └ 박민수 (사원)",
            "  └ 최지우 (사원)"
        ]

        for dept in departments:
            item = QListWidgetItem(dept)
            org_list.addItem(item)

        layout.addWidget(org_list)

        # 안내 메시지
        info_label = QLabel("💡 조직도 기능은 추후 확장 예정입니다")
        info_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                margin-top: 10px;
                padding: 10px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }
        """)
        layout.addWidget(info_label)

        layout.addStretch()
        self.setLayout(layout)


# ============================================================================
# 메인 윈도우
# ============================================================================

class MainWindow(QMainWindow):
    """메인 윈도우 - 탭 기반"""
    # 스레드 안전 Signal 정의
    user_list_updated = pyqtSignal(list, list)  # (all_users, online_users)
    user_status_changed = pyqtSignal(str, str)  # (username, status)
    message_received = pyqtSignal(str, str, str)  # (sender, content, timestamp)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.socket = None
        self.online_users = set()
        self.chat_windows = {}  # {username: ChatWindow}

        self.init_ui()
        self.connect_signals()
        self.connect_to_server()

    def connect_signals(self):
        """Signal을 Slot에 연결 (메인 스레드에서 GUI 업데이트)"""
        self.user_list_updated.connect(self._handle_user_list_update)
        self.user_status_changed.connect(self._handle_user_status_change)
        self.message_received.connect(self._handle_message_receive)

    def init_ui(self):
        self.setWindowTitle(f'KCS Messenger - {self.username}')
        self.resize(500, 700)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃 (가로)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 왼쪽 사이드바 (카카오톡 스타일)
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)

        # 오른쪽 컨텐츠 영역
        self.content_stack = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 컨텐츠 영역 초기화
        self.friends_tab = FriendsTab(self.username)
        self.friends_tab.chat_requested.connect(self.open_chat_window)

        self.chats_tab = ChatsTab()
        self.chats_tab.chat_opened.connect(self.open_chat_window)

        self.org_tab = OrganizationTab()

        # 기본으로 친구 탭 표시
        self.current_tab = self.friends_tab
        self.content_layout.addWidget(self.current_tab)

        # 초기 탭 가시성 명시적 설정 (친구 탭만 표시)
        self.friends_tab.show()
        self.chats_tab.hide()
        self.org_tab.hide()

        self.content_stack.setLayout(self.content_layout)
        main_layout.addWidget(self.content_stack, stretch=1)

        central_widget.setLayout(main_layout)

    def create_sidebar(self):
        """왼쪽 사이드바 생성"""
        sidebar = QWidget()
        sidebar.setFixedWidth(80)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #3A3A3C;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(15)

        # 프로필 버튼 (상단) - SVG
        profile_btn = QPushButton()
        profile_btn.setIcon(icon_manager.get_icon('profile', size=28, color='#AAAAAA'))
        profile_btn.setIconSize(QSize(28, 28))
        profile_btn.setFixedSize(60, 60)
        profile_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(profile_btn, alignment=Qt.AlignHCenter)

        layout.addSpacing(30)

        # 친구 버튼 - SVG
        self.friends_btn = QPushButton()
        self.friends_btn.setIcon(icon_manager.get_icon('friends', size=24, color='#FFFFFF'))
        self.friends_btn.setIconSize(QSize(24, 24))
        self.friends_btn.setFixedSize(50, 50)
        self.friends_btn.setStyleSheet(self.get_sidebar_btn_style(selected=True))
        self.friends_btn.clicked.connect(lambda: self.switch_tab("friends"))
        layout.addWidget(self.friends_btn, alignment=Qt.AlignHCenter)

        # 채팅 버튼 + 뱃지
        chat_container = QWidget()
        chat_container.setFixedSize(50, 50)
        chat_layout = QVBoxLayout()
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self.chats_btn = QPushButton()
        self.chats_btn.setIcon(icon_manager.get_icon('chat', size=24, color='#AAAAAA'))
        self.chats_btn.setIconSize(QSize(24, 24))
        self.chats_btn.setFixedSize(50, 50)
        self.chats_btn.setStyleSheet(self.get_sidebar_btn_style(selected=False))
        self.chats_btn.clicked.connect(lambda: self.switch_tab("chats"))

        # 뱃지 (읽지 않은 채팅)
        self.chat_badge = QLabel("3")
        self.chat_badge.setFixedSize(20, 20)
        self.chat_badge.setAlignment(Qt.AlignCenter)
        self.chat_badge.setStyleSheet("""
            QLabel {
                background-color: #FF3B30;
                color: white;
                font-size: 10px;
                font-weight: bold;
                border-radius: 10px;
            }
        """)
        self.chat_badge.move(35, 0)
        self.chat_badge.setParent(self.chats_btn)

        layout.addWidget(self.chats_btn, alignment=Qt.AlignHCenter)

        # 조직도 버튼 - SVG
        self.org_btn = QPushButton()
        self.org_btn.setIcon(icon_manager.get_icon('organization', size=24, color='#AAAAAA'))
        self.org_btn.setIconSize(QSize(24, 24))
        self.org_btn.setFixedSize(50, 50)
        self.org_btn.setStyleSheet(self.get_sidebar_btn_style(selected=False))
        self.org_btn.clicked.connect(lambda: self.switch_tab("org"))
        layout.addWidget(self.org_btn, alignment=Qt.AlignHCenter)

        # 더보기 버튼 - SVG
        layout.addSpacing(20)
        more_btn = QPushButton()
        more_btn.setIcon(icon_manager.get_icon('more', size=24, color='#AAAAAA'))
        more_btn.setIconSize(QSize(24, 24))
        more_btn.setFixedSize(50, 50)
        more_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(more_btn, alignment=Qt.AlignHCenter)

        layout.addStretch()

        # 설정 버튼 (하단) - SVG
        settings_btn = QPushButton()
        settings_btn.setIcon(icon_manager.get_icon('settings', size=24, color='#AAAAAA'))
        settings_btn.setIconSize(QSize(24, 24))
        settings_btn.setFixedSize(50, 50)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(settings_btn, alignment=Qt.AlignHCenter)

        sidebar.setLayout(layout)
        return sidebar

    def get_sidebar_btn_style(self, selected=False):
        """사이드바 버튼 스타일"""
        if selected:
            return """
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.15);
                    border: none;
                    font-size: 24px;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-size: 24px;
                    color: #AAAAAA;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            """

    def switch_tab(self, tab_name):
        """탭 전환"""
        # 이전 탭 숨김
        self.content_layout.removeWidget(self.current_tab)
        self.current_tab.hide()

        # 버튼 스타일 및 아이콘 색상 초기화
        self.friends_btn.setStyleSheet(self.get_sidebar_btn_style(selected=False))
        self.friends_btn.setIcon(icon_manager.get_icon('friends', size=24, color='#AAAAAA'))

        self.chats_btn.setStyleSheet(self.get_sidebar_btn_style(selected=False))
        self.chats_btn.setIcon(icon_manager.get_icon('chat', size=24, color='#AAAAAA'))

        self.org_btn.setStyleSheet(self.get_sidebar_btn_style(selected=False))
        self.org_btn.setIcon(icon_manager.get_icon('organization', size=24, color='#AAAAAA'))

        # 새 탭 표시 및 선택된 버튼 스타일 적용
        if tab_name == "friends":
            self.current_tab = self.friends_tab
            self.friends_btn.setStyleSheet(self.get_sidebar_btn_style(selected=True))
            self.friends_btn.setIcon(icon_manager.get_icon('friends', size=24, color='#FFFFFF'))
        elif tab_name == "chats":
            self.current_tab = self.chats_tab
            self.chats_btn.setStyleSheet(self.get_sidebar_btn_style(selected=True))
            self.chats_btn.setIcon(icon_manager.get_icon('chat', size=24, color='#FFFFFF'))
        elif tab_name == "org":
            self.current_tab = self.org_tab
            self.org_btn.setStyleSheet(self.get_sidebar_btn_style(selected=True))
            self.org_btn.setIcon(icon_manager.get_icon('organization', size=24, color='#FFFFFF'))

        self.content_layout.addWidget(self.current_tab)
        self.current_tab.show()

    def connect_to_server(self):
        """서버 연결"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('localhost', 5555))

            # 로그인 메시지 전송
            login_msg = {
                'type': 'join',
                'username': self.username
            }
            self.socket.send(json.dumps(login_msg).encode('utf-8'))

            # 수신 스레드 시작
            receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            receive_thread.start()

        except Exception as e:
            print(f"서버 연결 실패: {e}")

    def receive_messages(self):
        """메시지 수신 스레드"""
        buffer = ""
        while True:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if not data:
                    break

                buffer += data

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        self.handle_message(line)

            except Exception as e:
                print(f"수신 오류: {e}")
                break

    def handle_message(self, data):
        """메시지 처리 (백그라운드 스레드) - Signal만 emit"""
        try:
            msg = json.loads(data)
            msg_type = msg.get('type')

            if msg_type == 'all_users_list':
                # Signal emit: 사용자 목록 업데이트
                all_users = msg.get('users', [])
                online_users = msg.get('online_users', [])
                self.user_list_updated.emit(all_users, online_users)

            elif msg_type == 'user_status_changed':
                # Signal emit: 사용자 상태 변경
                username = msg.get('username')
                status = msg.get('status')
                self.user_status_changed.emit(username, status)

            elif msg_type == 'message':
                # Signal emit: 메시지 수신
                sender = msg.get('sender')
                content = msg.get('content')
                timestamp = msg.get('timestamp', datetime.now().strftime('%H:%M'))

                if sender != self.username:
                    self.message_received.emit(sender, content, timestamp)

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")

    def _handle_user_list_update(self, all_users, online_users):
        """사용자 목록 업데이트 처리 (메인 스레드)"""
        self.online_users = set(online_users)
        self.friends_tab.update_all_users(all_users, online_users)

    def _handle_user_status_change(self, username, status):
        """사용자 상태 변경 처리 (메인 스레드)"""
        if status == 'online':
            self.online_users.add(username)
        elif status == 'offline':
            self.online_users.discard(username)

        self.friends_tab.update_user_status(username, status)

    def _handle_message_receive(self, sender, content, timestamp):
        """메시지 수신 처리 (메인 스레드)"""
        # 채팅 목록에 추가
        self.chats_tab.add_or_update_chat(sender, content, datetime.now())

        # 해당 채팅 창이 열려있으면 메시지 표시
        if sender in self.chat_windows:
            chat_window = self.chat_windows[sender]
            chat_window.add_message(sender, content, timestamp, is_mine=False)
        else:
            # 채팅 창이 열려있지 않으면 읽지 않은 메시지 카운트 증가
            self.friends_tab.increment_unread_count(sender)

    def open_chat_window(self, target_user):
        """채팅 창 열기"""
        # 채팅 창을 열면 읽지 않은 메시지 카운트 초기화
        self.friends_tab.clear_unread_count(target_user)

        if target_user in self.chat_windows:
            # 기존 창 활성화
            chat_window = self.chat_windows[target_user]
            chat_window.show()
            chat_window.activateWindow()
        else:
            # 새 창 생성
            chat_window = ChatWindow(target_user, self.username)
            chat_window.message_sent.connect(self.send_message)
            self.chat_windows[target_user] = chat_window
            chat_window.show()

    def send_message(self, target_user, message):
        """메시지 전송"""
        try:
            msg = {
                'type': 'message',
                'sender': self.username,
                'content': message,
                'timestamp': datetime.now().strftime('%H:%M')
            }
            self.socket.send((json.dumps(msg) + '\n').encode('utf-8'))

            # 채팅 목록 업데이트
            self.chats_tab.add_or_update_chat(target_user, message, datetime.now())

        except Exception as e:
            print(f"메시지 전송 실패: {e}")

    def closeEvent(self, event):
        """종료 이벤트"""
        try:
            # 퇴장 메시지 전송
            leave_msg = {
                'type': 'leave',
                'username': self.username
            }
            self.socket.send(json.dumps(leave_msg).encode('utf-8'))
            self.socket.close()
        except:
            pass
        event.accept()


# ============================================================================
# 메인 실행
# ============================================================================

def main():
    app = QApplication(sys.argv)

    # 로그인 다이얼로그
    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        username = login_dialog.username

        # 메인 윈도우 표시
        main_window = MainWindow(username)
        main_window.show()

        sys.exit(app.exec_())
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
