"""
KCS Messenger - Exact KakaoTalk UI Clone
PyQt5 implementation matching KakaoTalk desktop interface
"""

import sys
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
import os

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class KakaoTalkColors:
    """KakaoTalk exact color scheme"""
    
    # Background colors
    CHAT_BACKGROUND = "#E3F2FD"  # Light blue-gray background
    WINDOW_BACKGROUND = "#FFFFFF"
    SIDEBAR_BACKGROUND = "#FFFFFF"
    
    # Message bubble colors
    SENT_BUBBLE = "#FFE400"  # KakaoTalk signature yellow
    RECEIVED_BUBBLE = "#FFFFFF"  # White
    
    # Text colors
    MESSAGE_TEXT = "#000000"
    TIMESTAMP_TEXT = "#999999"
    USERNAME_TEXT = "#666666"
    
    # UI element colors
    INPUT_BACKGROUND = "#FFFFFF"
    INPUT_BORDER = "#E0E0E0"
    ICON_COLOR = "#999999"
    BUTTON_HOVER = "#F5F5F5"


class KakaoTalkStyles:
    """KakaoTalk exact stylesheet definitions"""
    
    MAIN_WINDOW = """
    QMainWindow {
        background-color: #FFFFFF;
    }
    """
    
    CHAT_AREA = f"""
    QWidget#chatArea {{
        background-color: {KakaoTalkColors.CHAT_BACKGROUND};
        border: none;
    }}
    """
    
    MESSAGE_LIST = f"""
    QListWidget#messageList {{
        background-color: {KakaoTalkColors.CHAT_BACKGROUND};
        border: none;
        outline: none;
        padding: 10px;
    }}
    
    QListWidget#messageList::item {{
        background-color: transparent;
        border: none;
        padding: 4px 0px;
    }}
    
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}
    
    QScrollBar::handle:vertical {{
        background: rgba(0, 0, 0, 0.2);
        border-radius: 4px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: rgba(0, 0, 0, 0.3);
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
    
    INPUT_AREA = f"""
    QWidget#inputArea {{
        background-color: {KakaoTalkColors.INPUT_BACKGROUND};
        border-top: 1px solid {KakaoTalkColors.INPUT_BORDER};
    }}
    """
    
    INPUT_FIELD = f"""
    QTextEdit#messageInput {{
        background-color: {KakaoTalkColors.INPUT_BACKGROUND};
        border: none;
        color: #000000;
        font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
        font-size: 14px;
        padding: 8px;
    }}
    """
    
    ICON_BUTTON = """
    QPushButton.iconButton {
        background-color: transparent;
        border: none;
        padding: 8px;
        min-width: 32px;
        min-height: 32px;
    }
    
    QPushButton.iconButton:hover {
        background-color: #F5F5F5;
        border-radius: 4px;
    }
    """


class ProfileImage(QLabel):
    """Profile image widget matching KakaoTalk style"""
    
    def __init__(self, image_path: Optional[str] = None, size: int = 40):
        super().__init__()
        self.setFixedSize(size, size)
        self.setScaledContents(True)
        
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
        else:
            # Create default profile with mountain image
            pixmap = self.create_default_profile()
        
        # Make circular profile image
        rounded_pixmap = self.make_circular(pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        self.setPixmap(rounded_pixmap)
    
    def create_default_profile(self) -> QPixmap:
        """Create default mountain profile image"""
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw mountain silhouette
        gradient = QLinearGradient(0, 0, 0, 40)
        gradient.setColorAt(0, QColor("#87CEEB"))  # Sky blue
        gradient.setColorAt(1, QColor("#4682B4"))  # Steel blue
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 40, 40)
        
        # Draw simple mountain shape
        mountain_path = QPainterPath()
        mountain_path.moveTo(0, 40)
        mountain_path.lineTo(10, 25)
        mountain_path.lineTo(20, 30)
        mountain_path.lineTo(30, 20)
        mountain_path.lineTo(40, 35)
        mountain_path.lineTo(40, 40)
        mountain_path.closeSubpath()
        
        painter.setBrush(QColor("#2E7D32"))  # Mountain green
        painter.drawPath(mountain_path)
        
        painter.end()
        return pixmap
    
    def make_circular(self, pixmap: QPixmap) -> QPixmap:
        """Make pixmap circular"""
        size = pixmap.size()
        result = QPixmap(size)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        
        painter.end()
        return result


class KakaoMessageBubble(QWidget):
    """KakaoTalk exact message bubble design"""
    
    def __init__(self, message_data: dict, is_sent: bool = False, parent=None):
        super().__init__(parent)
        self.message_data = message_data
        self.is_sent = is_sent
        self.init_ui()
    
    def init_ui(self):
        """Initialize message bubble matching KakaoTalk exactly"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(16, 4, 16, 4)
        main_layout.setSpacing(8)
        
        if not self.is_sent:
            # Profile image for received messages
            profile = ProfileImage()
            main_layout.addWidget(profile, alignment=Qt.AlignTop)
        
        # Message content container
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        # Username for received messages
        if not self.is_sent:
            username = QLabel(self.message_data.get('sender_name', '안소영'))
            username.setStyleSheet(f"""
                color: {KakaoTalkColors.USERNAME_TEXT};
                font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
                font-size: 13px;
                padding-left: 4px;
                padding-bottom: 2px;
            """)
            content_layout.addWidget(username)
        
        # Message bubble and timestamp container
        bubble_layout = QHBoxLayout()
        bubble_layout.setSpacing(6)
        
        if self.is_sent:
            # Timestamp on left for sent messages
            time_label = self.create_timestamp()
            bubble_layout.addWidget(time_label, alignment=Qt.AlignBottom)
        
        # Message bubble
        bubble = self.create_bubble()
        bubble_layout.addWidget(bubble)
        
        if not self.is_sent:
            # Timestamp on right for received messages
            time_label = self.create_timestamp()
            bubble_layout.addWidget(time_label, alignment=Qt.AlignBottom)
        
        if self.is_sent:
            bubble_layout.addStretch()
        
        content_layout.addLayout(bubble_layout)
        
        if self.is_sent:
            main_layout.addStretch()
        
        main_layout.addLayout(content_layout)
        
        if not self.is_sent:
            main_layout.addStretch()
        
        self.setLayout(main_layout)
    
    def create_bubble(self) -> QWidget:
        """Create message bubble with exact KakaoTalk styling"""
        bubble = QWidget()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        
        # Message text
        message_label = QLabel(self.message_data.get('content', ''))
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message_label.setStyleSheet(f"""
            color: {KakaoTalkColors.MESSAGE_TEXT};
            font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
            font-size: 14px;
            line-height: 1.4;
        """)
        
        bubble_layout.addWidget(message_label)
        
        # Apply bubble style
        if self.is_sent:
            bubble.setStyleSheet(f"""
                QWidget {{
                    background-color: {KakaoTalkColors.SENT_BUBBLE};
                    border-radius: 18px;
                    padding: 2px;
                }}
            """)
        else:
            bubble.setStyleSheet(f"""
                QWidget {{
                    background-color: {KakaoTalkColors.RECEIVED_BUBBLE};
                    border: 1px solid #E0E0E0;
                    border-radius: 18px;
                    padding: 2px;
                }}
            """)
        
        return bubble
    
    def create_timestamp(self) -> QLabel:
        """Create timestamp label"""
        timestamp = self.message_data.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except:
                timestamp = datetime.now()
        
        # Format time Korean style
        time_str = timestamp.strftime("오전 %I:%M") if timestamp.hour < 12 else timestamp.strftime("오후 %I:%M")
        time_str = time_str.replace("오전 0", "오전 ").replace("오후 0", "오후 ")
        
        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"""
            color: {KakaoTalkColors.TIMESTAMP_TEXT};
            font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
            font-size: 11px;
        """)
        
        return time_label


class KakaoInputArea(QWidget):
    """KakaoTalk exact input area design"""
    
    message_sent = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inputArea")
        self.init_ui()
    
    def init_ui(self):
        """Initialize input area matching KakaoTalk exactly"""
        self.setStyleSheet(KakaoTalkStyles.INPUT_AREA)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Emoticon button
        emoticon_btn = self.create_icon_button("😊", "이모티콘")
        layout.addWidget(emoticon_btn)
        
        # File attachment button
        attach_btn = self.create_icon_button("📎", "파일 첨부")
        layout.addWidget(attach_btn)
        
        # Capture button
        capture_btn = self.create_icon_button("📷", "화면 캡처")
        layout.addWidget(capture_btn)
        
        # Voice message button
        voice_btn = self.create_icon_button("🎤", "음성 메시지")
        layout.addWidget(voice_btn)
        
        # Message input field
        self.message_input = QTextEdit()
        self.message_input.setObjectName("messageInput")
        self.message_input.setMaximumHeight(100)
        self.message_input.setPlaceholderText("메시지 입력")
        self.message_input.setStyleSheet(KakaoTalkStyles.INPUT_FIELD)
        layout.addWidget(self.message_input, 1)
        
        # Additional features button
        features_btn = self.create_icon_button("➕", "추가 기능")
        layout.addWidget(features_btn)
        
        # Gift button
        gift_btn = self.create_icon_button("🎁", "선물하기")
        layout.addWidget(gift_btn)
        
        # Sharp (#) button
        sharp_btn = self.create_icon_button("#", "샵 검색")
        layout.addWidget(sharp_btn)
        
        # Send button (hidden by default, shows when typing)
        self.send_btn = QPushButton("전송")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFE400;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
                font-size: 13px;
                font-weight: bold;
                color: #3A1D1D;
            }
            QPushButton:hover {
                background-color: #FADD00;
            }
        """)
        self.send_btn.hide()
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)
        
        self.setLayout(layout)
        
        # Connect text change to show/hide send button
        self.message_input.textChanged.connect(self.on_text_changed)
        
        # Handle Enter key
        self.message_input.installEventFilter(self)
    
    def create_icon_button(self, icon_text: str, tooltip: str) -> QPushButton:
        """Create icon button with KakaoTalk style"""
        btn = QPushButton(icon_text)
        btn.setToolTip(tooltip)
        btn.setProperty("class", "iconButton")
        btn.setStyleSheet(KakaoTalkStyles.ICON_BUTTON)
        btn.setCursor(Qt.PointingHandCursor)
        return btn
    
    def on_text_changed(self):
        """Show/hide send button based on text content"""
        has_text = bool(self.message_input.toPlainText().strip())
        self.send_btn.setVisible(has_text)
    
    def eventFilter(self, obj, event):
        """Handle Enter key press"""
        if obj == self.message_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers():
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def send_message(self):
        """Send message"""
        text = self.message_input.toPlainText().strip()
        if text:
            self.message_sent.emit(text)
            self.message_input.clear()
            self.send_btn.hide()


class KakaoTalkMainWindow(QMainWindow):
    """Main window exactly matching KakaoTalk desktop interface"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_sample_messages()
    
    def init_ui(self):
        """Initialize UI matching KakaoTalk exactly"""
        self.setWindowTitle("안소영")
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
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)
        
        # Chat area
        chat_area = self.create_chat_area()
        main_layout.addWidget(chat_area, 1)
        
        # Input area
        self.input_area = KakaoInputArea()
        self.input_area.message_sent.connect(self.send_message)
        main_layout.addWidget(self.input_area)
    
    def create_title_bar(self) -> QWidget:
        """Create title bar matching KakaoTalk"""
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
        room_label = QLabel("안소영")
        room_label.setStyleSheet("""
            font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
            font-size: 16px;
            font-weight: bold;
            color: #000000;
        """)
        
        # Member count
        member_label = QLabel("2")
        member_label.setStyleSheet("""
            font-family: "맑은 고딕", "Malgun Gothic", sans-serif;
            font-size: 14px;
            color: #999999;
            padding-left: 8px;
        """)
        
        layout.addWidget(room_label)
        layout.addWidget(member_label)
        layout.addStretch()
        
        # Action buttons
        search_btn = self.create_title_button("🔍")
        phone_btn = self.create_title_button("📞")
        video_btn = self.create_title_button("📹")
        menu_btn = self.create_title_button("☰")
        
        layout.addWidget(search_btn)
        layout.addWidget(phone_btn)
        layout.addWidget(video_btn)
        layout.addWidget(menu_btn)
        
        return title_bar
    
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
        """Create chat area matching KakaoTalk"""
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
    
    def add_message(self, message_data: dict, is_sent: bool = False):
        """Add message to chat"""
        item = QListWidgetItem(self.message_list)
        bubble = KakaoMessageBubble(message_data, is_sent)
        item.setSizeHint(bubble.sizeHint())
        self.message_list.addItem(item)
        self.message_list.setItemWidget(item, bubble)
        self.message_list.scrollToBottom()
    
    def load_sample_messages(self):
        """Load sample messages matching the screenshot"""
        messages = [
            {
                'content': '머니 로냇어',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 10, 38),
                'is_sent': True
            },
            {
                'content': '혹시 집에 엿날에 쓰던 사무 컴퓨터 받침대 있나?',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 11, 6),
                'is_sent': True
            },
            {
                'content': '모르겠넹',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 11, 6),
                'is_sent': False
            },
            {
                'content': '집에서 지낵봤장?',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 18, 21),
                'is_sent': False
            },
            {
                'content': '출발할떼 연락줄것',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 18, 21),
                'is_sent': False
            },
            {
                'content': '30분에 나갈계',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 18, 22),
                'is_sent': True
            },
            {
                'content': 'ㅇ ㅇ',
                'sender_name': '안소영',
                'timestamp': datetime(2025, 1, 1, 18, 22),
                'is_sent': False
            }
        ]
        
        for msg in messages:
            self.add_message(msg, msg.get('is_sent', False))
    
    def send_message(self, text: str):
        """Send new message"""
        message_data = {
            'content': text,
            'sender_name': '나',
            'timestamp': datetime.now(),
            'is_sent': True
        }
        self.add_message(message_data, True)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("KCS Talk")
    
    # Set Korean font as default
    font = QFont("맑은 고딕", 10)
    app.setFont(font)
    
    # Create and show window
    window = KakaoTalkMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()