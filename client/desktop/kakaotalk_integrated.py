"""
KCS Messenger - Integrated KakaoTalk Client
Complete working messenger with server connection
"""

import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import socketio
from socketio import AsyncClient
import aiohttp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Import UI components from kakaotalk_ui
try:
    # Try importing from the same directory (when run directly)
    from kakaotalk_ui import (
        KakaoTalkColors,
        KakaoTalkStyles,
        ProfileImage,
        KakaoMessageBubble,
        KakaoInputArea
    )
except ImportError:
    # Try importing from the client.desktop module (when run from root)
    from client.desktop.kakaotalk_ui import (
        KakaoTalkColors,
        KakaoTalkStyles,
        ProfileImage,
        KakaoMessageBubble,
        KakaoInputArea
    )


@dataclass
class User:
    """User data model"""
    id: str
    username: str
    nickname: str
    avatar_url: Optional[str] = None
    status: str = 'offline'
    last_seen: Optional[datetime] = None


@dataclass
class Message:
    """Message data model"""
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: datetime
    is_sent: bool = False
    read_count: int = 0
    message_type: str = 'text'


class MessageSignals(QObject):
    """Signals for message events"""
    new_message = pyqtSignal(dict)
    user_joined = pyqtSignal(str)
    user_left = pyqtSignal(str)
    typing_update = pyqtSignal(list)
    connection_status = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)


class SocketIOClient(QThread):
    """WebSocket client thread"""
    
    def __init__(self, server_url: str = 'http://localhost:8000'):
        super().__init__()
        self.server_url = server_url
        self.sio = socketio.Client()
        self.connected = False
        self.user_id = None
        self.room_id = 'general'
        self.signals = MessageSignals()
        
        # Setup Socket.IO event handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.sio.event
        def connect():
            logger.info("Connected to server")
            self.connected = True
            self.signals.connection_status.emit(True)
        
        @self.sio.event
        def disconnect():
            logger.info("Disconnected from server")
            self.connected = False
            self.signals.connection_status.emit(False)
        
        @self.sio.event
        def authenticated(data):
            logger.info(f"Authentication successful: {data}")
            self.join_room(self.room_id)
        
        @self.sio.event
        def new_message(data):
            logger.info(f"New message received: {data}")
            self.signals.new_message.emit(data)
        
        @self.sio.event
        def user_joined(data):
            logger.info(f"User joined: {data}")
            self.signals.user_joined.emit(data.get('user_id', ''))
        
        @self.sio.event
        def user_left(data):
            logger.info(f"User left: {data}")
            self.signals.user_left.emit(data.get('user_id', ''))
        
        @self.sio.event
        def typing_update(data):
            users = data.get('users', [])
            self.signals.typing_update.emit(users)
        
        @self.sio.event
        def error(data):
            logger.error(f"Server error: {data}")
            self.signals.error_occurred.emit(str(data))
    
    def run(self):
        """Run the Socket.IO client"""
        try:
            self.sio.connect(self.server_url)
            self.sio.wait()
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.signals.error_occurred.emit(str(e))
    
    def authenticate(self, user_id: str, token: str = 'dummy_token'):
        """Authenticate with server"""
        self.user_id = user_id
        if self.connected:
            self.sio.emit('authenticate', {
                'user_id': user_id,
                'token': token
            })
    
    def join_room(self, room_id: str):
        """Join a chat room"""
        self.room_id = room_id
        if self.connected:
            self.sio.emit('join_room', {'room_id': room_id})
    
    def send_message(self, content: str, message_type: str = 'text'):
        """Send message to server"""
        if self.connected and self.room_id:
            message_data = {
                'room_id': self.room_id,
                'content': content,
                'type': message_type
            }
            self.sio.emit('send_message', message_data)
            logger.info(f"Message sent: {content}")
    
    def start_typing(self):
        """Send typing indicator"""
        if self.connected and self.room_id:
            self.sio.emit('typing_start', {'room_id': self.room_id})
    
    def stop_connection(self):
        """Stop the Socket.IO connection"""
        if self.connected:
            self.sio.disconnect()


class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize login UI"""
        self.setWindowTitle("KCS Messenger 로그인")
        self.setFixedSize(350, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #FFE400;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #FADD00;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo/Title
        title = QLabel("KCS Messenger")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #3A1D1D;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("사용자 이름을 입력하세요")
        layout.addWidget(self.username_input)
        
        # Login button
        login_btn = QPushButton("로그인")
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)
        
        self.setLayout(layout)
        
        # Enter key to login
        self.username_input.returnPressed.connect(self.login)
    
    def login(self):
        """Handle login"""
        username = self.username_input.text().strip()
        if username:
            self.username = username
            self.accept()
        else:
            QMessageBox.warning(self, "경고", "사용자 이름을 입력해주세요.")


class IntegratedKakaoTalkWindow(QMainWindow):
    """Main window with server integration"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.socket_client = None
        self.messages = []
        self.init_ui()
        self.show_login()
    
    def init_ui(self):
        """Initialize UI matching KakaoTalk exactly"""
        self.setWindowTitle("KCS Messenger")
        self.setGeometry(100, 100, 400, 600)
        self.setStyleSheet(KakaoTalkStyles.MAIN_WINDOW)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Title bar
        self.title_bar = self.create_title_bar()
        main_layout.addWidget(self.title_bar)
        
        # Status bar
        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)
        
        # Chat area
        chat_area = self.create_chat_area()
        main_layout.addWidget(chat_area, 1)
        
        # Input area
        self.input_area = KakaoInputArea()
        self.input_area.message_sent.connect(self.send_message)
        main_layout.addWidget(self.input_area)
    
    def create_title_bar(self) -> QWidget:
        """Create title bar"""
        title_bar = QWidget()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(16, 0, 16, 0)
        
        # Room name
        self.room_label = QLabel("General Chat")
        self.room_label.setStyleSheet("""
            font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
            font-size: 16px;
            font-weight: bold;
            color: #000000;
        """)
        
        # Member count
        self.member_label = QLabel("1")
        self.member_label.setStyleSheet("""
            font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
            font-size: 14px;
            color: #999999;
            padding-left: 8px;
        """)
        
        layout.addWidget(self.room_label)
        layout.addWidget(self.member_label)
        layout.addStretch()
        
        # Action buttons
        search_btn = self.create_title_button("🔍")
        settings_btn = self.create_title_button("⚙️")
        
        layout.addWidget(search_btn)
        layout.addWidget(settings_btn)
        
        return title_bar
    
    def create_status_bar(self) -> QWidget:
        """Create connection status bar"""
        status_bar = QWidget()
        status_bar.setFixedHeight(25)
        status_bar.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(16, 0, 16, 0)
        
        # Connection status
        self.connection_status = QLabel("● 연결 중...")
        self.connection_status.setStyleSheet("""
            color: #FFA500;
            font-size: 12px;
        """)
        
        # Typing indicator
        self.typing_indicator = QLabel("")
        self.typing_indicator.setStyleSheet("""
            color: #999999;
            font-size: 12px;
            font-style: italic;
        """)
        
        layout.addWidget(self.connection_status)
        layout.addWidget(self.typing_indicator)
        layout.addStretch()
        
        return status_bar
    
    def create_title_button(self, icon: str) -> QPushButton:
        """Create title bar button"""
        btn = QPushButton(icon)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-radius: 4px;
            }
        """)
        btn.setCursor(Qt.PointingHandCursor)
        return btn
    
    def create_chat_area(self) -> QWidget:
        """Create chat area"""
        chat_area = QWidget()
        chat_area.setObjectName("chatArea")
        chat_area.setStyleSheet(KakaoTalkStyles.CHAT_AREA)
        
        layout = QVBoxLayout(chat_area)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Message list
        self.message_list = QListWidget()
        self.message_list.setObjectName("messageList")
        self.message_list.setStyleSheet(KakaoTalkStyles.MESSAGE_LIST)
        self.message_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.message_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        layout.addWidget(self.message_list)
        
        return chat_area
    
    def show_login(self):
        """Show login dialog"""
        login_dialog = LoginDialog(self)
        if login_dialog.exec_() == QDialog.Accepted:
            self.current_user = login_dialog.username
            self.setWindowTitle(f"KCS Messenger - {self.current_user}")
            self.connect_to_server()
        else:
            self.close()
    
    def connect_to_server(self):
        """Connect to server"""
        # Initialize Socket.IO client
        self.socket_client = SocketIOClient()
        
        # Connect signals
        self.socket_client.signals.new_message.connect(self.on_new_message)
        self.socket_client.signals.connection_status.connect(self.on_connection_status)
        self.socket_client.signals.typing_update.connect(self.on_typing_update)
        self.socket_client.signals.error_occurred.connect(self.on_error)
        
        # Start connection
        self.socket_client.start()
        
        # Wait a bit for connection then authenticate
        QTimer.singleShot(1000, self.authenticate_user)
    
    def authenticate_user(self):
        """Authenticate user with server"""
        if self.socket_client and self.current_user:
            self.socket_client.authenticate(self.current_user)
    
    def on_connection_status(self, connected: bool):
        """Handle connection status change"""
        if connected:
            self.connection_status.setText("● 연결됨")
            self.connection_status.setStyleSheet("color: #00C851; font-size: 12px;")
        else:
            self.connection_status.setText("● 연결 끊김")
            self.connection_status.setStyleSheet("color: #FF4444; font-size: 12px;")
    
    def on_new_message(self, message_data: dict):
        """Handle new message from server"""
        # Check if message is from current user
        is_sent = message_data.get('sender_id') == self.current_user
        
        # Add sender name if not from current user
        if not is_sent and 'sender_name' not in message_data:
            message_data['sender_name'] = message_data.get('sender_id', 'Unknown')
        
        # Convert timestamp
        if 'created_at' in message_data:
            try:
                message_data['timestamp'] = datetime.fromisoformat(
                    message_data['created_at'].replace('Z', '+00:00')
                )
            except:
                message_data['timestamp'] = datetime.now()
        else:
            message_data['timestamp'] = datetime.now()
        
        # Add message to UI
        self.add_message(message_data, is_sent)
    
    def on_typing_update(self, users: list):
        """Handle typing indicator update"""
        if users:
            # Filter out current user
            other_users = [u for u in users if u != self.current_user]
            if other_users:
                if len(other_users) == 1:
                    self.typing_indicator.setText(f"{other_users[0]}님이 입력 중...")
                else:
                    self.typing_indicator.setText(f"{len(other_users)}명이 입력 중...")
            else:
                self.typing_indicator.setText("")
        else:
            self.typing_indicator.setText("")
    
    def on_error(self, error_msg: str):
        """Handle error from server"""
        QMessageBox.warning(self, "오류", f"서버 오류: {error_msg}")
    
    def add_message(self, message_data: dict, is_sent: bool = False):
        """Add message to chat"""
        item = QListWidgetItem(self.message_list)
        bubble = KakaoMessageBubble(message_data, is_sent)
        item.setSizeHint(bubble.sizeHint())
        self.message_list.addItem(item)
        self.message_list.setItemWidget(item, bubble)
        self.message_list.scrollToBottom()
        
        # Store message
        self.messages.append(message_data)
    
    def send_message(self, content: str):
        """Send message to server"""
        if self.socket_client and self.socket_client.connected and content:
            # Send to server
            self.socket_client.send_message(content)
            
            # Add to local UI immediately
            message_data = {
                'content': content,
                'sender_id': self.current_user,
                'sender_name': self.current_user,
                'timestamp': datetime.now(),
                'is_sent': True
            }
            self.add_message(message_data, True)
    
    def closeEvent(self, event):
        """Handle window close"""
        if self.socket_client:
            self.socket_client.stop_connection()
            self.socket_client.wait()
        event.accept()


class StandaloneMode(QMainWindow):
    """Standalone mode without server connection"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_demo_messages()
    
    def init_ui(self):
        """Initialize UI for standalone mode"""
        self.setWindowTitle("KCS Messenger - 오프라인 모드")
        self.setGeometry(100, 100, 400, 600)
        
        # Import the original KakaoTalk UI
        from kakaotalk_ui import KakaoTalkMainWindow
        
        # Create instance
        self.ui = KakaoTalkMainWindow()
        self.setCentralWidget(self.ui.centralWidget())
    
    def load_demo_messages(self):
        """Load demo messages for standalone mode"""
        demo_messages = [
            {
                'content': '안녕하세요! KCS Messenger입니다.',
                'sender_name': '시스템',
                'timestamp': datetime.now(),
                'is_sent': False
            },
            {
                'content': '서버 연결 없이 UI를 테스트할 수 있습니다.',
                'sender_name': '시스템',
                'timestamp': datetime.now(),
                'is_sent': False
            },
            {
                'content': '테스트 메시지입니다.',
                'sender_name': '나',
                'timestamp': datetime.now(),
                'is_sent': True
            }
        ]
        
        for msg in demo_messages:
            if hasattr(self, 'ui'):
                self.ui.add_message(msg, msg.get('is_sent', False))


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("KCS Messenger")
    
    # Set Korean font as default
    font = QFont("맑은 고딕", 10)
    app.setFont(font)
    
    # Check for server connection
    try:
        import requests
        response = requests.get('http://localhost:8000/health', timeout=2)
        server_available = response.status_code == 200
    except:
        server_available = False
    
    if server_available or '--online' in sys.argv:
        # Online mode with server
        logger.info("Starting in online mode")
        window = IntegratedKakaoTalkWindow()
    else:
        # Standalone mode
        logger.info("Starting in standalone mode")
        reply = QMessageBox.question(
            None,
            "서버 연결",
            "서버에 연결할 수 없습니다.\n오프라인 모드로 시작하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            window = StandaloneMode()
        else:
            sys.exit(0)
    
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()