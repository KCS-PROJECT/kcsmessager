#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KakaoTalk Real Chat Client - Improved with User List
개선 사항:
- 왼쪽 사이드바에 온라인 사용자 목록 표시
- 우클릭 메뉴로 대화하기
- 더블클릭으로 대화 시작
- 실시간 온라인 상태 표시
"""

import sys
import socket
import threading
import json
import locale
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# UTF-8 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    try:
        locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Korean_Korea.949')
        except:
            pass

# PyQt5 확인
try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("[ERROR] PyQt5가 설치되지 않았습니다.")
    print("설치: pip install PyQt5")
    sys.exit(1)


# ================== 색상 테마 ==================

class KakaoColors:
    """카카오톡 색상"""
    CHAT_BACKGROUND = "#B8D4E3"
    SENT_BUBBLE = "#FFE400"
    RECEIVED_BUBBLE = "#FFFFFF"
    HEADER_BG = "#FFFFFF"
    INPUT_BG = "#FFFFFF"
    SIDEBAR_BG = "#F5F5F5"
    TEXT_BLACK = "#000000"
    TEXT_GRAY = "#787878"
    TEXT_NAME = "#666666"
    BORDER = "#E0E0E0"
    ONLINE_GREEN = "#4CAF50"
    OFFLINE_GRAY = "#999999"


# ================== 네트워크 클라이언트 ==================

class ChatClient(QObject):
    """실시간 통신용 소켓 클라이언트"""

    message_received = pyqtSignal(dict)
    connection_lost = pyqtSignal()
    connected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.socket = None
        self.connected_flag = False
        self.username = ""
        self.receive_thread = None

    def connect_to_server(self, username, host='127.0.0.1', port=5555):
        """서버 연결"""
        try:
            self.username = username
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected_flag = True

            # 입장 메시지 전송
            join_msg = {'type': 'join', 'username': username}
            self.socket.send(json.dumps(join_msg).encode('utf-8'))

            # 수신 스레드 시작
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            self.connected.emit()
            return True

        except Exception as e:
            print(f"[CLIENT] 연결 오류: {e}")
            return False

    def receive_messages(self):
        """서버로부터 메시지 수신"""
        while self.connected_flag:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break

                message = json.loads(data)
                self.message_received.emit(message)

            except Exception as e:
                if self.connected_flag:
                    print(f"[CLIENT] 수신 오류: {e}")
                break

        self.connected_flag = False
        self.connection_lost.emit()

    def send_message(self, content):
        """메시지 전송"""
        if self.connected_flag and self.socket:
            try:
                message = {
                    'type': 'message',
                    'content': content,
                    'sender': self.username
                }
                self.socket.send(json.dumps(message).encode('utf-8'))
                return True
            except Exception as e:
                print(f"[CLIENT] 전송 오류: {e}")
                return False
        return False

    def disconnect(self):
        """연결 종료"""
        self.connected_flag = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


# ================== 로그인 다이얼로그 ==================

class LoginDialog(QDialog):
    """로그인 화면"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("로그인")
        self.setFixedSize(380, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
            }
            QLabel {
                font-size: 15px;
                color: #2C2C2C;
                font-weight: 500;
            }
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 12px 15px;
                font-size: 15px;
                background-color: #FAFAFA;
            }
            QLineEdit:focus {
                border: 2px solid #FFE400;
            }
            QPushButton {
                background-color: #FFE400;
                border: none;
                border-radius: 6px;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: bold;
                color: #2C2C2C;
            }
            QPushButton:hover {
                background-color: #FFD700;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(35, 35, 35, 35)

        # 제목
        title = QLabel("사용자 이름을 입력하세요")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        # 입력창
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("예: 홍길동")
        self.username_input.returnPressed.connect(self.accept_login)
        layout.addWidget(self.username_input)

        # 빠른 선택 버튼
        preset_layout = QHBoxLayout()
        for name in ["김철수", "이영희", "박민수"]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, n=name: self.quick_login(n))
            preset_layout.addWidget(btn)
        layout.addLayout(preset_layout)

        # 로그인 버튼
        login_btn = QPushButton("입장하기")
        login_btn.clicked.connect(self.accept_login)
        layout.addWidget(login_btn)

    def quick_login(self, username):
        """빠른 로그인"""
        self.username = username
        self.accept()

    def accept_login(self):
        """로그인 승인"""
        username = self.username_input.text().strip()
        if username:
            self.username = username
            self.accept()
        else:
            QMessageBox.warning(self, "경고", "사용자 이름을 입력해주세요")

    def get_username(self):
        """사용자 이름 반환"""
        return self.username


# ================== 사용자 목록 아이템 ==================

class UserListItem(QWidget):
    """사용자 목록 커스텀 위젯"""

    def __init__(self, username, is_online=True, parent=None):
        super().__init__(parent)
        self.username = username
        self.is_online = is_online
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 프로필 아이콘
        profile = self.create_profile()
        layout.addWidget(profile)

        # 사용자 이름
        name_label = QLabel(self.username)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {KakaoColors.TEXT_BLACK};
                font-size: 14px;
                font-weight: 500;
            }}
        """)
        layout.addWidget(name_label)

        layout.addStretch()

        # 온라인 상태
        status_label = QLabel("●" if self.is_online else "○")
        color = KakaoColors.ONLINE_GREEN if self.is_online else KakaoColors.OFFLINE_GRAY
        status_label.setStyleSheet(f"color: {color}; font-size: 16px;")
        layout.addWidget(status_label)

    def create_profile(self):
        """프로필 아이콘 생성"""
        label = QLabel()
        label.setFixedSize(32, 32)

        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 이름 기반 색상
        colors = ["#4A90E2", "#7B68EE", "#50C878", "#FF6B6B", "#4ECDC4"]
        color_idx = sum(ord(c) for c in self.username) % len(colors)

        painter.setBrush(QBrush(QColor(colors[color_idx])))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 32, 32)

        # 이니셜
        painter.setPen(Qt.white)
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        initial = self.username[0].upper() if self.username else "?"
        painter.drawText(QRect(0, 0, 32, 32), Qt.AlignCenter, initial)

        painter.end()
        label.setPixmap(pixmap)

        return label


# ================== 프로필 위젯 ==================

class ProfileWidget(QLabel):
    """채팅 메시지용 프로필 이미지"""

    def __init__(self, name="User", parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(40, 40)

        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = ["#4A90E2", "#7B68EE", "#50C878", "#FF6B6B", "#4ECDC4"]
        color_idx = sum(ord(c) for c in name) % len(colors)

        gradient = QLinearGradient(0, 0, 40, 40)
        gradient.setColorAt(0, QColor(colors[color_idx]))
        gradient.setColorAt(1, QColor(colors[color_idx]).darker(150))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 40, 40)

        painter.setPen(Qt.white)
        font = QFont("Arial", 16, QFont.Bold)
        painter.setFont(font)
        initial = name[0].upper() if name else "?"
        painter.drawText(QRect(0, 0, 40, 40), Qt.AlignCenter, initial)

        painter.end()
        self.setPixmap(pixmap)


# ================== 말풍선 위젯 ==================

class BubbleWithTail(QWidget):
    """꼬리가 있는 말풍선"""

    def __init__(self, text, is_sent=False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_sent = is_sent
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 크기 계산
        font = QFont("Malgun Gothic", 14)
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(QRect(0, 0, 230, 1000), Qt.TextWordWrap, text)

        padding = 20
        self.bubble_width = min(text_rect.width() + padding * 2, 250)
        self.bubble_height = text_rect.height() + padding

        self.setFixedSize(self.bubble_width + 8, self.bubble_height)

    def paintEvent(self, event):
        """말풍선 그리기"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        if self.is_sent:
            bubble_color = QColor(KakaoColors.SENT_BUBBLE)
            painter.setPen(Qt.NoPen)
        else:
            bubble_color = QColor(KakaoColors.RECEIVED_BUBBLE)
            painter.setPen(QPen(QColor(KakaoColors.BORDER), 1))

        painter.setBrush(QBrush(bubble_color))

        path = QPainterPath()

        if self.is_sent:
            rect = QRectF(0, 0, self.bubble_width - 3, self.bubble_height)
            path.addRoundedRect(rect, 18, 18)

            # 꼬리
            tail = QPainterPath()
            tail.moveTo(self.bubble_width - 6, self.bubble_height // 2 - 4)
            tail.lineTo(self.bubble_width + 1, self.bubble_height // 2)
            tail.lineTo(self.bubble_width - 6, self.bubble_height // 2 + 4)
            path = path.united(tail)
        else:
            rect = QRectF(8, 0, self.bubble_width - 3, self.bubble_height)
            path.addRoundedRect(rect, 18, 18)

            # 꼬리
            tail = QPainterPath()
            tail.moveTo(8, self.bubble_height // 2 - 4)
            tail.lineTo(1, self.bubble_height // 2)
            tail.lineTo(8, self.bubble_height // 2 + 4)
            path = path.united(tail)

        painter.drawPath(path)

        # 텍스트
        painter.setPen(QColor(KakaoColors.TEXT_BLACK))
        font = QFont("Malgun Gothic", 14)
        painter.setFont(font)

        if self.is_sent:
            text_rect = QRectF(10, 10, self.bubble_width - 25, self.bubble_height - 20)
        else:
            text_rect = QRectF(18, 10, self.bubble_width - 25, self.bubble_height - 20)

        painter.drawText(text_rect, Qt.TextWordWrap, self.text)


# ================== 메시지 위젯 ==================

class MessageWidget(QWidget):
    """프로필 + 말풍선 + 시간"""

    def __init__(self, text, time, is_sent=False, sender_name=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.time = time
        self.is_sent = is_sent
        self.sender_name = sender_name
        self.init_ui()

    def init_ui(self):
        """메시지 레이아웃"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 2, 12, 2)
        main_layout.setSpacing(6)

        content_widget = QWidget()
        content_widget.setMaximumWidth(300)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        if not self.is_sent and self.sender_name:
            profile = ProfileWidget(self.sender_name)
            main_layout.addWidget(profile, alignment=Qt.AlignTop)

            name_label = QLabel(self.sender_name)
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {KakaoColors.TEXT_NAME};
                    font-size: 13px;
                    font-weight: 500;
                    padding-left: 12px;
                    padding-bottom: 4px;
                }}
            """)
            content_layout.addWidget(name_label)

        bubble_row = QHBoxLayout()
        bubble_row.setSpacing(4)

        bubble = BubbleWithTail(self.text, self.is_sent)

        time_label = QLabel(self.time)
        time_label.setStyleSheet(f"""
            QLabel {{
                color: {KakaoColors.TEXT_GRAY};
                font-size: 12px;
                padding: 2px 4px;
            }}
        """)

        if self.is_sent:
            bubble_row.addWidget(time_label, alignment=Qt.AlignBottom)
            bubble_row.addWidget(bubble)
        else:
            bubble_row.addWidget(bubble)
            bubble_row.addWidget(time_label, alignment=Qt.AlignBottom)

        content_layout.addLayout(bubble_row)

        if self.is_sent:
            main_layout.addStretch()
            main_layout.addWidget(content_widget)
        else:
            main_layout.addWidget(content_widget)
            main_layout.addStretch()


# ================== 메인 채팅 창 ==================

class ImprovedChatWindow(QMainWindow):
    """개선된 채팅 창 - 사용자 목록 포함"""

    def __init__(self):
        super().__init__()
        self.chat_client = ChatClient()
        self.username = ""
        self.online_users = {}  # {username: is_online}
        self.input_field = None
        self.user_list_widget = None

        # 시그널 연결
        self.chat_client.message_received.connect(self.handle_server_message)
        self.chat_client.connection_lost.connect(self.handle_connection_lost)

        self.init_ui()
        self.show_login()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("KCS Talk - 개선된 채팅")

        # 창 크기
        screen = QApplication.primaryScreen().geometry()
        width = max(600, min(700, int(screen.width() * 0.4)))
        height = max(600, min(750, int(screen.height() * 0.85)))

        self.setMinimumSize(550, 550)

        # 중앙 배치
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.setGeometry(x, y, width, height)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 헤더
        self.header = self.create_header()
        main_layout.addWidget(self.header)

        # 사이드바 + 채팅 영역
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # 사용자 목록 사이드바
        self.sidebar = self.create_user_sidebar()
        content_layout.addWidget(self.sidebar)

        # 채팅 영역
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        self.chat_area = self.create_chat_area()
        chat_layout.addWidget(self.chat_area)

        input_area = self.create_input_area()
        chat_layout.addWidget(input_area)

        content_layout.addWidget(chat_container)

        main_layout.addLayout(content_layout)

        # 스타일
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {KakaoColors.CHAT_BACKGROUND};
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(0, 0, 0, 0.2);
                border-radius: 3px;
            }}
        """)

    def create_header(self):
        """헤더 생성"""
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {KakaoColors.HEADER_BG};
                border-bottom: 1px solid {KakaoColors.BORDER};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 0, 16, 0)

        self.title_label = QLabel("연결 중...")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #2C2C2C;
            }
        """)
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.status_label = QLabel("● 오프라인")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.status_label)

        return header

    def create_user_sidebar(self):
        """사용자 목록 사이드바"""
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"""
            QWidget {{
                background-color: {KakaoColors.SIDEBAR_BG};
                border-right: 1px solid {KakaoColors.BORDER};
            }}
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 제목
        title = QLabel("온라인 사용자")
        title.setStyleSheet(f"""
            QLabel {{
                background-color: {KakaoColors.HEADER_BG};
                color: {KakaoColors.TEXT_BLACK};
                font-size: 14px;
                font-weight: 600;
                padding: 12px;
                border-bottom: 1px solid {KakaoColors.BORDER};
            }}
        """)
        layout.addWidget(title)

        # 사용자 목록
        self.user_list_widget = QListWidget()
        self.user_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {KakaoColors.SIDEBAR_BG};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {KakaoColors.BORDER};
                padding: 0px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 228, 0, 0.1);
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 228, 0, 0.2);
            }}
        """)

        # 컨텍스트 메뉴 활성화
        self.user_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.user_list_widget.customContextMenuRequested.connect(self.show_context_menu)

        # 더블클릭 활성화
        self.user_list_widget.itemDoubleClicked.connect(self.on_user_double_click)

        layout.addWidget(self.user_list_widget)

        return sidebar

    def create_chat_area(self):
        """채팅 영역"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {KakaoColors.CHAT_BACKGROUND};
            }}
        """)

        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(0, 10, 0, 10)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()

        scroll.setWidget(self.chat_widget)
        return scroll

    def create_input_area(self):
        """입력 영역"""
        input_widget = QWidget()
        input_widget.setFixedHeight(60)
        input_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {KakaoColors.INPUT_BG};
                border-top: 1px solid {KakaoColors.BORDER};
            }}
        """)

        layout = QHBoxLayout(input_widget)
        layout.setContentsMargins(12, 10, 12, 10)

        # 입력창
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("메시지 입력")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 22px;
                padding: 12px 18px;
                font-size: 15px;
                background-color: #F8F9FA;
                color: #2C2C2C;
            }
            QLineEdit:focus {
                border: 2px solid #FFE400;
                background-color: #FFFFFF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_field)

        # 전송 버튼
        send_btn = QPushButton("전송")
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {KakaoColors.SENT_BUBBLE};
                border: none;
                border-radius: 22px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: bold;
                color: #2C2C2C;
            }}
            QPushButton:hover {{
                background-color: #FFD700;
            }}
        """)
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)

        return input_widget

    def show_login(self):
        """로그인 화면 표시"""
        dialog = LoginDialog(self)
        if dialog.exec_():
            self.username = dialog.get_username()
            self.setWindowTitle(f"KCS Talk - {self.username}")

            # 서버 연결
            if self.chat_client.connect_to_server(self.username):
                self.title_label.setText(f"채팅방 - {self.username}")
                self.status_label.setText("● 온라인")
                self.status_label.setStyleSheet("""
                    QLabel {
                        color: #4CAF50;
                        font-size: 13px;
                        font-weight: 500;
                    }
                """)

                self.add_system_message(f"{self.username}님이 입장하셨습니다.")
            else:
                QMessageBox.critical(self, "연결 실패",
                                   "서버에 연결할 수 없습니다.\n서버가 실행 중인지 확인해주세요.")
                self.close()
        else:
            self.close()

    def update_user_list(self):
        """사용자 목록 업데이트"""
        self.user_list_widget.clear()

        for username in sorted(self.online_users.keys()):
            if username == self.username:
                continue  # 자신은 표시하지 않음

            is_online = self.online_users[username]
            item = QListWidgetItem(self.user_list_widget)
            item.setData(Qt.UserRole, username)

            widget = UserListItem(username, is_online)
            item.setSizeHint(widget.sizeHint())

            self.user_list_widget.addItem(item)
            self.user_list_widget.setItemWidget(item, widget)

    def show_context_menu(self, position):
        """우클릭 메뉴 표시"""
        item = self.user_list_widget.itemAt(position)
        if not item:
            return

        username = item.data(Qt.UserRole)

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 32px 8px 16px;
                font-size: 14px;
            }
            QMenu::item:selected {
                background-color: #FFE400;
            }
        """)

        chat_action = menu.addAction(f"💬 {username}님과 대화하기")

        action = menu.exec_(self.user_list_widget.mapToGlobal(position))

        if action == chat_action:
            self.start_chat_with(username)

    def on_user_double_click(self, item):
        """더블클릭 처리"""
        username = item.data(Qt.UserRole)
        self.start_chat_with(username)

    def start_chat_with(self, username):
        """특정 사용자와 대화 시작"""
        self.input_field.setFocus()
        self.input_field.setText(f"@{username} ")
        self.input_field.setCursorPosition(len(self.input_field.text()))

        self.add_system_message(f"{username}님과 대화를 시작합니다.")

    def handle_server_message(self, message):
        """서버 메시지 처리"""
        msg_type = message.get('type')

        if msg_type == 'message':
            sender = message.get('sender', 'Unknown')
            content = message.get('content', '')
            timestamp = message.get('timestamp', '')

            # 시간 포맷
            try:
                dt = datetime.fromisoformat(timestamp)
                hour = dt.hour
                minute = dt.minute
                period = "오전" if hour < 12 else "오후"
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                time_str = f"{period} {display_hour}:{minute:02d}"
            except:
                time_str = ""

            is_sent = (sender == self.username)
            self.add_message(content, time_str, is_sent, None if is_sent else sender)

        elif msg_type == 'user_joined':
            username = message.get('username', 'Unknown')
            if username != self.username:
                self.add_system_message(f"{username}님이 입장하셨습니다.")
                self.online_users[username] = True
                self.update_user_list()

        elif msg_type == 'user_left':
            username = message.get('username', 'Unknown')
            self.add_system_message(f"{username}님이 퇴장하셨습니다.")
            if username in self.online_users:
                self.online_users[username] = False
                self.update_user_list()

        elif msg_type == 'users_list':
            users = message.get('users', [])
            self.online_users = {user: True for user in users}
            self.update_user_list()

            online_count = len([u for u in self.online_users.values() if u])
            self.title_label.setText(f"채팅방 ({online_count}명)")

    def add_message(self, text, time, is_sent, sender_name=None):
        """메시지 추가"""
        message = MessageWidget(text, time, is_sent, sender_name)

        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, message)

        QTimer.singleShot(50, self.scroll_to_bottom)

    def add_system_message(self, text):
        """시스템 메시지 추가"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 13px;
                font-weight: 500;
                padding: 8px 12px;
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(224, 224, 224, 0.5);
                border-radius: 12px;
                margin: 8px 50px;
            }
        """)

        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, label)

        QTimer.singleShot(50, self.scroll_to_bottom)

    def send_message(self):
        """메시지 전송"""
        text = self.input_field.text().strip()
        if text and self.chat_client.connected_flag:
            if self.chat_client.send_message(text):
                self.input_field.clear()

    def scroll_to_bottom(self):
        """하단으로 스크롤"""
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def handle_connection_lost(self):
        """연결 끊김 처리"""
        self.status_label.setText("● 오프라인")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        self.add_system_message("서버와의 연결이 끊어졌습니다.")

        # 모든 사용자 오프라인 처리
        for username in self.online_users:
            self.online_users[username] = False
        self.update_user_list()

    def closeEvent(self, event):
        """창 닫기"""
        self.chat_client.disconnect()
        event.accept()


# ================== 메인 함수 ==================

def main():
    """애플리케이션 실행"""
    # High DPI 지원
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    font = QFont("Malgun Gothic", 11)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    window = ImprovedChatWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
