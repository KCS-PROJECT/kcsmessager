"""
KCS Messenger - Modern PyQt5 Desktop Client
KakaoTalk-style messaging interface
"""

import sys
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *

# For async integration with Qt
import qasync


class StyleSheet:
    """Application-wide stylesheet"""
    
    MAIN = """
    QMainWindow {
        background-color: #f0f0f0;
    }
    
    QWidget#sidebar {
        background-color: #2c3e50;
        border-right: 1px solid #34495e;
    }
    
    QWidget#chatArea {
        background-color: #ecf0f1;
    }
    
    QPushButton {
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: 500;
    }
    
    QPushButton:hover {
        background-color: #3498db;
        color: white;
    }
    
    QLineEdit, QTextEdit {
        border: 1px solid #bdc3c7;
        border-radius: 4px;
        padding: 8px;
        font-size: 14px;
    }
    
    QLineEdit:focus, QTextEdit:focus {
        border: 2px solid #3498db;
        outline: none;
    }
    """
    
    MESSAGE_BUBBLE_SENT = """
    QWidget#messageBubbleSent {
        background-color: #FFE400;
        border-radius: 12px;
        padding: 8px 12px;
        margin: 4px;
    }
    """
    
    MESSAGE_BUBBLE_RECEIVED = """
    QWidget#messageBubbleReceived {
        background-color: white;
        border-radius: 12px;
        padding: 8px 12px;
        margin: 4px;
        border: 1px solid #e0e0e0;
    }
    """
    
    CHAT_ITEM = """
    QWidget#chatItem {
        background-color: transparent;
        padding: 12px;
        border-bottom: 1px solid #34495e;
    }
    
    QWidget#chatItem:hover {
        background-color: #34495e;
    }
    
    QWidget#chatItemSelected {
        background-color: #3498db;
    }
    """


class MessageBubble(QWidget):
    """KakaoTalk-style message bubble"""
    
    def __init__(self, message: dict, is_sent: bool = False, parent=None):
        super().__init__(parent)
        self.message = message
        self.is_sent = is_sent
        self.init_ui()
    
    def init_ui(self):
        """Initialize message bubble UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Message content widget
        bubble = QWidget()
        bubble.setObjectName("messageBubbleSent" if self.is_sent else "messageBubbleReceived")
        bubble.setStyleSheet(StyleSheet.MESSAGE_BUBBLE_SENT if self.is_sent else StyleSheet.MESSAGE_BUBBLE_RECEIVED)
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)
        
        # Sender name (for received messages)
        if not self.is_sent:
            sender_label = QLabel(self.message.get('sender_name', 'Unknown'))
            sender_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #7f8c8d;")
            bubble_layout.addWidget(sender_label)
        
        # Message content
        content_label = QLabel(self.message.get('content', ''))
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_label.setStyleSheet("font-size: 14px; color: #2c3e50;")
        bubble_layout.addWidget(content_label)
        
        # Timestamp and read receipt
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        
        # Timestamp
        timestamp = self.message.get('created_at', datetime.now().isoformat())
        time_label = QLabel(self.format_time(timestamp))
        time_label.setStyleSheet("font-size: 11px; color: #95a5a6;")
        info_layout.addWidget(time_label)
        
        # Read receipt (for sent messages)
        if self.is_sent:
            read_count = self.message.get('read_count', 0)
            if read_count > 0:
                read_label = QLabel(str(read_count) if read_count > 1 else "✓✓")
                read_label.setStyleSheet("font-size: 11px; color: #3498db;")
                info_layout.addWidget(read_label)
        
        info_layout.addStretch()
        bubble_layout.addLayout(info_layout)
        
        # Add avatar for received messages
        if not self.is_sent:
            avatar = self.create_avatar(self.message.get('sender_name', 'U'))
            layout.addWidget(avatar)
            layout.addWidget(bubble)
            layout.addStretch()
        else:
            layout.addStretch()
            layout.addWidget(bubble)
        
        self.setLayout(layout)
    
    def create_avatar(self, name: str) -> QLabel:
        """Create avatar widget"""
        avatar = QLabel()
        avatar.setFixedSize(40, 40)
        avatar.setStyleSheet("""
            background-color: #3498db;
            border-radius: 20px;
            color: white;
            font-weight: bold;
            font-size: 16px;
        """)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setText(name[0].upper())
        return avatar
    
    def format_time(self, timestamp: str) -> str:
        """Format timestamp to readable time"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now()
            
            if dt.date() == now.date():
                return dt.strftime("%H:%M")
            elif (now - dt).days == 1:
                return "Yesterday " + dt.strftime("%H:%M")
            else:
                return dt.strftime("%m/%d %H:%M")
        except:
            return ""


class ChatListItem(QWidget):
    """Chat room list item"""
    
    clicked = pyqtSignal(str)  # room_id
    
    def __init__(self, room_data: dict, parent=None):
        super().__init__(parent)
        self.room_data = room_data
        self.init_ui()
    
    def init_ui(self):
        """Initialize chat item UI"""
        self.setObjectName("chatItem")
        self.setStyleSheet(StyleSheet.CHAT_ITEM)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Avatar
        avatar = self.create_avatar(self.room_data.get('name', 'R'))
        layout.addWidget(avatar)
        
        # Chat info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Room name and time
        name_time_layout = QHBoxLayout()
        name_label = QLabel(self.room_data.get('name', 'Unknown'))
        name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        name_time_layout.addWidget(name_label)
        
        time_label = QLabel(self.room_data.get('last_message_time', ''))
        time_label.setStyleSheet("font-size: 11px; color: #95a5a6;")
        name_time_layout.addStretch()
        name_time_layout.addWidget(time_label)
        
        info_layout.addLayout(name_time_layout)
        
        # Last message and unread count
        msg_unread_layout = QHBoxLayout()
        last_msg = QLabel(self.room_data.get('last_message', 'No messages'))
        last_msg.setStyleSheet("font-size: 12px; color: #bdc3c7;")
        last_msg.setMaximumWidth(200)
        msg_unread_layout.addWidget(last_msg)
        
        unread_count = self.room_data.get('unread_count', 0)
        if unread_count > 0:
            unread_badge = QLabel(str(unread_count))
            unread_badge.setStyleSheet("""
                background-color: #e74c3c;
                color: white;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: bold;
            """)
            msg_unread_layout.addStretch()
            msg_unread_layout.addWidget(unread_badge)
        
        info_layout.addLayout(msg_unread_layout)
        
        layout.addLayout(info_layout)
        self.setLayout(layout)
    
    def create_avatar(self, name: str) -> QLabel:
        """Create avatar widget"""
        avatar = QLabel()
        avatar.setFixedSize(50, 50)
        avatar.setStyleSheet("""
            background-color: #3498db;
            border-radius: 25px;
            color: white;
            font-weight: bold;
            font-size: 20px;
        """)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setText(name[0].upper())
        return avatar
    
    def mousePressEvent(self, event):
        """Handle click event"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.room_data.get('id', ''))


class MessageListWidget(QListWidget):
    """Custom message list with virtual scrolling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QListWidget {
                background-color: #ecf0f1;
                border: none;
                outline: none;
            }
            
            QListWidget::item {
                background-color: transparent;
                border: none;
                padding: 2px;
            }
            
            QScrollBar:vertical {
                background: #ecf0f1;
                width: 8px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background: #95a5a6;
                border-radius: 4px;
                min-height: 30px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #7f8c8d;
            }
        """)
    
    def add_message(self, message: dict, is_sent: bool = False):
        """Add message to list"""
        item = QListWidgetItem(self)
        bubble = MessageBubble(message, is_sent)
        item.setSizeHint(bubble.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, bubble)
        
        # Auto scroll to bottom
        self.scrollToBottom()


class ChatInputWidget(QWidget):
    """Chat input area with attachments and emoji"""
    
    message_sent = pyqtSignal(str)  # message content
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        """Initialize input UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        
        # Attach button
        attach_btn = QPushButton()
        attach_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        attach_btn.setFixedSize(32, 32)
        attach_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        layout.addWidget(attach_btn)
        
        # Message input
        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(100)
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bdc3c7;
                border-radius: 20px;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.message_input)
        
        # Emoji button
        emoji_btn = QPushButton("😊")
        emoji_btn.setFixedSize(32, 32)
        emoji_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 16px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #ecf0f1;
            }
        """)
        layout.addWidget(emoji_btn)
        
        # Send button
        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFE400;
                color: #2c3e50;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #FDD835;
            }
        """)
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)
        
        self.setLayout(layout)
        
        # Enter key to send
        self.message_input.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle enter key press"""
        if obj == self.message_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers():
                self.send_message()
                return True
            elif event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier:
                # Shift+Enter for new line
                return False
        return super().eventFilter(obj, event)
    
    def send_message(self):
        """Send message"""
        text = self.message_input.toPlainText().strip()
        if text:
            self.message_sent.emit(text)
            self.message_input.clear()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_room_id = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize main window UI"""
        self.setWindowTitle("KCS Messenger")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(StyleSheet.MAIN)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Chat area
        chat_area = self.create_chat_area()
        main_layout.addWidget(chat_area)
        
        # Set layout stretch
        main_layout.setStretchFactor(sidebar, 1)
        main_layout.setStretchFactor(chat_area, 3)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().showMessage("Connected")
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction("New Chat", self.new_chat)
        file_menu.addAction("Settings", self.show_settings)
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        
        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Toggle Sidebar", self.toggle_sidebar)
        view_menu.addAction("Dark Mode", self.toggle_dark_mode)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About", self.show_about)
    
    def create_sidebar(self) -> QWidget:
        """Create sidebar widget"""
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # User profile section
        profile_widget = QWidget()
        profile_widget.setStyleSheet("background-color: #34495e; padding: 16px;")
        profile_layout = QHBoxLayout(profile_widget)
        
        # Profile avatar
        avatar = QLabel("U")
        avatar.setFixedSize(50, 50)
        avatar.setStyleSheet("""
            background-color: #3498db;
            border-radius: 25px;
            color: white;
            font-weight: bold;
            font-size: 24px;
        """)
        avatar.setAlignment(Qt.AlignCenter)
        profile_layout.addWidget(avatar)
        
        # Profile info
        info_layout = QVBoxLayout()
        name_label = QLabel("User Name")
        name_label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        status_label = QLabel("Online")
        status_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        info_layout.addWidget(name_label)
        info_layout.addWidget(status_label)
        info_layout.addStretch()
        
        profile_layout.addLayout(info_layout)
        profile_layout.addStretch()
        
        layout.addWidget(profile_widget)
        
        # Search bar
        search_bar = QLineEdit()
        search_bar.setPlaceholderText("Search...")
        search_bar.setStyleSheet("""
            QLineEdit {
                background-color: #34495e;
                border: none;
                border-bottom: 1px solid #2c3e50;
                color: white;
                padding: 12px;
                font-size: 14px;
            }
        """)
        layout.addWidget(search_bar)
        
        # Tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background-color: #2c3e50;
                border: none;
            }
            
            QTabBar::tab {
                background-color: #34495e;
                color: #95a5a6;
                padding: 8px 16px;
                border: none;
            }
            
            QTabBar::tab:selected {
                background-color: #2c3e50;
                color: white;
            }
        """)
        
        # Chats tab
        self.chat_list = QListWidget()
        self.chat_list.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50;
                border: none;
            }
        """)
        
        # Add sample chats
        for i in range(5):
            room_data = {
                'id': f'room_{i}',
                'name': f'Chat Room {i+1}',
                'last_message': 'Hello, how are you?',
                'last_message_time': '12:30',
                'unread_count': i
            }
            chat_item = ChatListItem(room_data)
            chat_item.clicked.connect(self.open_chat)
            
            item = QListWidgetItem(self.chat_list)
            item.setSizeHint(chat_item.sizeHint())
            self.chat_list.addItem(item)
            self.chat_list.setItemWidget(item, chat_item)
        
        tab_widget.addTab(self.chat_list, "Chats")
        
        # Users tab
        user_list = QListWidget()
        user_list.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50;
                border: none;
                color: white;
            }
        """)
        tab_widget.addTab(user_list, "Users")
        
        layout.addWidget(tab_widget)
        
        return sidebar
    
    def create_chat_area(self) -> QWidget:
        """Create chat area widget"""
        chat_area = QWidget()
        chat_area.setObjectName("chatArea")
        
        layout = QVBoxLayout(chat_area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Chat header
        header = QWidget()
        header.setStyleSheet("background-color: white; border-bottom: 1px solid #ecf0f1;")
        header.setFixedHeight(60)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        
        # Room info
        room_name = QLabel("Select a chat")
        room_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        room_status = QLabel("No messages")
        room_status.setStyleSheet("font-size: 12px; color: #95a5a6;")
        
        room_info_layout = QVBoxLayout()
        room_info_layout.addWidget(room_name)
        room_info_layout.addWidget(room_status)
        
        header_layout.addLayout(room_info_layout)
        header_layout.addStretch()
        
        # Action buttons
        search_btn = QPushButton()
        search_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        search_btn.setFixedSize(32, 32)
        
        call_btn = QPushButton()
        call_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        call_btn.setFixedSize(32, 32)
        
        more_btn = QPushButton()
        more_btn.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        more_btn.setFixedSize(32, 32)
        
        for btn in [search_btn, call_btn, more_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #ecf0f1;
                }
            """)
            header_layout.addWidget(btn)
        
        layout.addWidget(header)
        
        # Message list
        self.message_list = MessageListWidget()
        layout.addWidget(self.message_list)
        
        # Input area
        input_widget = ChatInputWidget()
        input_widget.message_sent.connect(self.send_message)
        layout.addWidget(input_widget)
        
        return chat_area
    
    def open_chat(self, room_id: str):
        """Open chat room"""
        self.current_room_id = room_id
        # Load messages for room
        self.load_messages(room_id)
    
    def load_messages(self, room_id: str):
        """Load messages for room"""
        # Clear current messages
        self.message_list.clear()
        
        # Add sample messages
        for i in range(10):
            message = {
                'id': f'msg_{i}',
                'content': f'This is message {i+1}',
                'sender_name': 'Other User' if i % 2 == 0 else 'Me',
                'created_at': datetime.now().isoformat(),
                'read_count': 2 if i % 2 == 1 else 0
            }
            self.message_list.add_message(message, is_sent=(i % 2 == 1))
    
    def send_message(self, content: str):
        """Send message"""
        if self.current_room_id and content:
            message = {
                'id': f'msg_new',
                'content': content,
                'sender_name': 'Me',
                'created_at': datetime.now().isoformat(),
                'read_count': 0
            }
            self.message_list.add_message(message, is_sent=True)
            
            # TODO: Send to server via WebSocket
    
    def new_chat(self):
        """Create new chat"""
        pass
    
    def show_settings(self):
        """Show settings dialog"""
        pass
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", "KCS Messenger v2.0\nModern messaging application")
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        pass
    
    def toggle_dark_mode(self):
        """Toggle dark mode"""
        pass


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("KCS Messenger")
    
    # Set application icon
    app.setWindowIcon(QIcon())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()