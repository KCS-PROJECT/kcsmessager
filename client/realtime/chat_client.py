#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KakaoTalk Real Chat Client - Connect Multiple Windows for Real Conversations
Based on exact replica design with real networking
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

# Set UTF-8 encoding for Windows
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

# Check PyQt5 installation
try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    print("[ERROR] PyQt5 is not installed.")
    print("Please install: pip install PyQt5")
    sys.exit(1)


# ================== Color Scheme ==================

class KakaoColors:
    """KakaoTalk color scheme"""
    CHAT_BACKGROUND = "#B8D4E3"
    SENT_BUBBLE = "#FFE400"
    RECEIVED_BUBBLE = "#FFFFFF"
    HEADER_BG = "#FFFFFF"
    INPUT_BG = "#FFFFFF"
    TEXT_BLACK = "#000000"
    TEXT_GRAY = "#787878"
    TEXT_NAME = "#666666"
    BORDER = "#E0E0E0"
    ICON_GRAY = "#5A5A5A"


# ================== Network Client ==================

class ChatClient(QObject):
    """Socket client for real-time communication"""
    
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
        """Connect to chat server"""
        try:
            self.username = username
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected_flag = True
            
            # Send join message
            join_msg = {
                'type': 'join',
                'username': username
            }
            self.socket.send(json.dumps(join_msg).encode('utf-8'))
            
            # Start receiving thread
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            self.connected.emit()
            return True
            
        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")
            return False
    
    def receive_messages(self):
        """Receive messages from server"""
        while self.connected_flag:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.message_received.emit(message)
                
            except Exception as e:
                if self.connected_flag:
                    print(f"[CLIENT] Receive error: {e}")
                break
        
        self.connected_flag = False
        self.connection_lost.emit()
    
    def send_message(self, content):
        """Send message to server"""
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
                print(f"[CLIENT] Send error: {e}")
                return False
        return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.connected_flag = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


# ================== Login Dialog ==================

class LoginDialog(QDialog):
    """Login dialog for username selection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self.init_ui()
        
    def init_ui(self):
        """Initialize login UI"""
        self.setWindowTitle("로그인")
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Nanum Gothic", sans-serif;
            }
            QLabel {
                font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Nanum Gothic", sans-serif;
                font-size: 15px;
                color: #2C2C2C;
                font-weight: 500;
            }
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 12px 15px;
                font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Nanum Gothic", sans-serif;
                font-size: 15px;
                background-color: #FAFAFA;
                color: #2C2C2C;
            }
            QLineEdit:focus {
                border: 2px solid #FFE400;
            }
            QPushButton {
                background-color: #FFE400;
                border: none;
                border-radius: 6px;
                padding: 12px 16px;
                font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Nanum Gothic", sans-serif;
                font-size: 14px;
                font-weight: bold;
                color: #2C2C2C;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #FFD700;
            }
            QPushButton:pressed {
                background-color: #FFC107;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(35, 35, 35, 35)
        
        # Title
        title = QLabel("사용자 이름을 입력하세요")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px; color: #2C2C2C;")
        layout.addWidget(title)
        
        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("예: 홍길동")
        self.username_input.returnPressed.connect(self.accept_login)
        layout.addWidget(self.username_input)
        
        # Preset buttons for quick selection
        preset_layout = QHBoxLayout()
        
        user1_btn = QPushButton("김철수")
        user1_btn.clicked.connect(lambda: self.quick_login("김철수"))
        preset_layout.addWidget(user1_btn)
        
        user2_btn = QPushButton("이영희")
        user2_btn.clicked.connect(lambda: self.quick_login("이영희"))
        preset_layout.addWidget(user2_btn)
        
        user3_btn = QPushButton("박민수")
        user3_btn.clicked.connect(lambda: self.quick_login("박민수"))
        preset_layout.addWidget(user3_btn)
        
        layout.addLayout(preset_layout)
        
        # Login button
        self.login_btn = QPushButton("입장하기")
        self.login_btn.clicked.connect(self.accept_login)
        layout.addWidget(self.login_btn)
        
        # 내용물 높이에 맞춰 고정 - 위젯이 찌그러지지 않도록 함
        self.setFixedSize(380, self.sizeHint().height())
        
    def quick_login(self, username):
        """Quick login with preset username"""
        self.username = username
        self.accept()
        
    def accept_login(self):
        """Accept login with entered username"""
        username = self.username_input.text().strip()
        if username:
            self.username = username
            self.accept()
        else:
            QMessageBox.warning(self, "경고", "사용자 이름을 입력해주세요")
    
    def get_username(self):
        """Get the entered username"""
        return self.username


# ================== Profile Widget ==================

class ProfileWidget(QLabel):
    """Profile image widget"""
    
    def __init__(self, name="User", parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(40, 40)
        self.setScaledContents(True)
        
        # Create profile with initials
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Random color based on name
        colors = ["#4A90E2", "#7B68EE", "#50C878", "#FF6B6B", "#4ECDC4"]
        color_index = sum(ord(c) for c in name) % len(colors)
        
        gradient = QLinearGradient(0, 0, 40, 40)
        gradient.setColorAt(0, QColor(colors[color_index]))
        gradient.setColorAt(1, QColor(colors[color_index]).darker(150))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 40, 40)
        
        # Draw initials
        painter.setPen(Qt.white)
        font = QFont()
        font.setFamilies(['Arial', 'Helvetica', 'Sans-serif'])
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        initials = name[0].upper() if name else "?"
        painter.drawText(QRect(0, 0, 40, 40), Qt.AlignCenter, initials)
        
        painter.end()
        self.setPixmap(pixmap)


# ================== Bubble Widget with Tail ==================

class BubbleWithTail(QWidget):
    """Custom painted bubble with tail"""
    
    def __init__(self, text, is_sent=False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_sent = is_sent
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Calculate size with proper font - 더 안정적인 폰트 설정
        font = QFont("Malgun Gothic", 14)  # 더 큰 폰트 크기
        font.setStyleHint(QFont.SansSerif)
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(QRect(0, 0, 230, 1000), 
                                        Qt.TextWordWrap, text)
        
        padding = 20
        self.bubble_width = min(text_rect.width() + padding * 2, 250)
        self.bubble_height = text_rect.height() + padding
        
        self.setFixedSize(self.bubble_width + 8, self.bubble_height)
    
    def paintEvent(self, event):
        """Paint bubble with tail"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        
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
            
            tail = QPainterPath()
            tail.moveTo(self.bubble_width - 6, self.bubble_height // 2 - 4)
            tail.lineTo(self.bubble_width + 1, self.bubble_height // 2)
            tail.lineTo(self.bubble_width - 6, self.bubble_height // 2 + 4)
            path = path.united(tail)
        else:
            rect = QRectF(8, 0, self.bubble_width - 3, self.bubble_height)
            path.addRoundedRect(rect, 18, 18)
            
            tail = QPainterPath()
            tail.moveTo(8, self.bubble_height // 2 - 4)
            tail.lineTo(1, self.bubble_height // 2)
            tail.lineTo(8, self.bubble_height // 2 + 4)
            path = path.united(tail)
        
        painter.drawPath(path)
        
        painter.setPen(QColor(KakaoColors.TEXT_BLACK))
        # 더 안정적이고 큰 폰트 설정
        font = QFont("Malgun Gothic", 14)
        font.setStyleHint(QFont.SansSerif)
        font.setWeight(QFont.Normal)
        painter.setFont(font)
        
        if self.is_sent:
            text_rect = QRectF(10, 10, self.bubble_width - 25, self.bubble_height - 20)
        else:
            text_rect = QRectF(18, 10, self.bubble_width - 25, self.bubble_height - 20)
        
        painter.drawText(text_rect, Qt.TextWordWrap, self.text)


# ================== Message Widget ==================

class MessageWidget(QWidget):
    """Complete message with profile, bubble, and time"""
    
    def __init__(self, text, time, is_sent=False, sender_name=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.time = time
        self.is_sent = is_sent
        self.sender_name = sender_name
        self.init_ui()
    
    def init_ui(self):
        """Create message layout"""
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
                    font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
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
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 12px;
                font-weight: 400;
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


# ================== Main Chat Window ==================

class RealKakaoTalkWindow(QMainWindow):
    """Real KakaoTalk chat window with networking"""
    
    def __init__(self):
        super().__init__()
        self.chat_client = ChatClient()
        self.username = ""
        self.other_users = []
        self.input_field = None
        
        # Connect signals
        self.chat_client.message_received.connect(self.handle_server_message)
        self.chat_client.connection_lost.connect(self.handle_connection_lost)
        
        self.init_ui()
        self.show_login()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("KCS Talk - Real Chat")
        
        # 더 큰 윈도우 크기로 설정 - 글씨와 요소들이 잘 보이도록
        screen = QApplication.primaryScreen().geometry()
        width = max(450, min(500, int(screen.width() * 0.3)))
        height = max(600, min(750, int(screen.height() * 0.85)))
        
        # 최소 크기 설정
        self.setMinimumSize(420, 550)
        
        # Center window on screen
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        
        self.setGeometry(x, y, width, height)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = self.create_header()
        layout.addWidget(self.header)
        
        # Chat area
        self.chat_area = self.create_chat_area()
        layout.addWidget(self.chat_area)
        
        # Input area
        input_area = self.create_input_area()
        layout.addWidget(input_area)
        
        # Apply styles
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
        """Create header"""
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
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 18px;
                font-weight: 600;
                color: #2C2C2C;
                padding: 2px;
            }
        """)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        self.status_label = QLabel("● 오프라인")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 13px;
                font-weight: 500;
                padding: 2px;
            }
        """)
        layout.addWidget(self.status_label)
        
        return header
    
    def create_chat_area(self):
        """Create chat area"""
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
        """Create input area"""
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
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("메시지 입력")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 22px;
                padding: 12px 18px;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 15px;
                background-color: #F8F9FA;
                color: #2C2C2C;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 2px solid #FFE400;
                background-color: #FFFFFF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_field)
        
        # Send button
        send_btn = QPushButton("전송")
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {KakaoColors.SENT_BUBBLE};
                border: none;
                border-radius: 22px;
                padding: 12px 24px;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 15px;
                font-weight: bold;
                color: #2C2C2C;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: #FFD700;
            }}
            QPushButton:pressed {{
                background-color: #FFC107;
            }}
        """)
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)
        
        return input_widget
    
    def show_login(self):
        """Show login dialog"""
        dialog = LoginDialog(self)
        if dialog.exec_():
            self.username = dialog.get_username()
            self.setWindowTitle(f"KCS Talk - {self.username}")
            
            # Connect to server
            if self.chat_client.connect_to_server(self.username):
                self.title_label.setText(f"채팅방 - {self.username}")
                self.status_label.setText("● 온라인")
                self.status_label.setStyleSheet("""
                    QLabel { 
                        color: #4CAF50; 
                        font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                        font-size: 13px; 
                        font-weight: 500;
                        padding: 2px;
                    }
                """)
                
                # Add system message
                self.add_system_message(f"{self.username}님이 입장하셨습니다.")
            else:
                QMessageBox.critical(self, "연결 실패", 
                                   "서버에 연결할 수 없습니다.\n서버가 실행 중인지 확인해주세요.")
                self.close()
        else:
            self.close()
    
    def handle_server_message(self, message):
        """Handle message from server"""
        msg_type = message.get('type')
        
        if msg_type == 'message':
            # Regular chat message
            sender = message.get('sender', 'Unknown')
            content = message.get('content', '')
            timestamp = message.get('timestamp', '')
            
            # Format time
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
            
            # Add message to chat
            is_sent = (sender == self.username)
            self.add_message(content, time_str, is_sent, None if is_sent else sender)
            
        elif msg_type == 'user_joined':
            username = message.get('username', 'Unknown')
            if username != self.username:
                self.add_system_message(f"{username}님이 입장하셨습니다.")
                if username not in self.other_users:
                    self.other_users.append(username)
                    
        elif msg_type == 'user_left':
            username = message.get('username', 'Unknown')
            self.add_system_message(f"{username}님이 퇴장하셨습니다.")
            if username in self.other_users:
                self.other_users.remove(username)
                
        elif msg_type == 'users_list':
            users = message.get('users', [])
            self.other_users = [u for u in users if u != self.username]
            if self.other_users:
                self.title_label.setText(f"채팅방 ({len(self.other_users) + 1}명)")
    
    def add_message(self, text, time, is_sent, sender_name=None):
        """Add message to chat"""
        message = MessageWidget(text, time, is_sent, sender_name)
        
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, message)
        
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def add_system_message(self, text):
        """Add system message"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #555555;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
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
        """Send message"""
        text = self.input_field.text().strip()
        if text and self.chat_client.connected_flag:
            # Send to server
            if self.chat_client.send_message(text):
                # Clear input
                self.input_field.clear()
                
                # 메시지는 서버에서 받을 때만 표시 (중복 방지)
                # 서버에서 다시 받아서 표시하므로 여기서는 추가하지 않음
    
    def scroll_to_bottom(self):
        """Scroll to bottom"""
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def handle_connection_lost(self):
        """Handle lost connection"""
        self.status_label.setText("● 오프라인")
        self.status_label.setStyleSheet("""
            QLabel { 
                color: #666666; 
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 13px; 
                font-weight: 500;
                padding: 2px;
            }
        """)
        self.add_system_message("서버와의 연결이 끊어졌습니다.")
    
    def closeEvent(self, event):
        """Handle window close"""
        self.chat_client.disconnect()
        event.accept()


# ================== Main Application ==================

def main():
    """Run the application"""
    # Enable High DPI support BEFORE creating QApplication
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set environment variable for better scaling
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # 더 안정적인 폰트 설정
    font = QFont("Malgun Gothic", 11)  # 더 큰 기본 폰트 크기
    font.setStyleHint(QFont.SansSerif)
    font.setWeight(QFont.Normal)
    app.setFont(font)
    
    window = RealKakaoTalkWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()