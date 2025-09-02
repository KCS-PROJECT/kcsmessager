#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KakaoTalk Fixed Version - All UI Issues Resolved
Fixes: Encoding, Layout, Bubble Rendering, Window Scaling
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import random

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8' if 'ko_KR' in locale.locale_alias else '')

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


# ================== Profile Widget ==================

class ProfileWidget(QLabel):
    """Profile image widget with proper sizing"""
    
    def __init__(self, name="User", parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(40, 40)
        self.setScaledContents(True)
        
        # Create rounded profile
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Gradient background
        colors = ["#4A90E2", "#7B68EE", "#50C878", "#FF6B6B", "#4ECDC4"]
        color_index = sum(ord(c) for c in name) % len(colors)
        
        gradient = QLinearGradient(0, 0, 40, 40)
        gradient.setColorAt(0, QColor(colors[color_index]))
        gradient.setColorAt(1, QColor(colors[color_index]).darker(150))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 40, 40)
        
        # Draw initial
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        initial = name[0].upper() if name else "?"
        painter.drawText(QRect(0, 0, 40, 40), Qt.AlignCenter, initial)
        
        painter.end()
        self.setPixmap(pixmap)


# ================== Enhanced Bubble Widget ==================

class EnhancedBubble(QWidget):
    """Enhanced bubble widget with proper rendering and sizing"""
    
    def __init__(self, text, is_sent=False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_sent = is_sent
        self.setMinimumHeight(35)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Calculate proper size
        self._calculate_size()
        
    def _calculate_size(self):
        """Calculate bubble size based on text"""
        font = QFont("Malgun Gothic", 13)
        metrics = QFontMetrics(font)
        
        # Calculate text rectangle with proper width
        max_width = 220
        text_rect = metrics.boundingRect(
            QRect(0, 0, max_width, 1000),
            Qt.TextWordWrap | Qt.AlignLeft,
            self.text
        )
        
        # Add padding
        padding_h = 24
        padding_v = 16
        self.bubble_width = min(text_rect.width() + padding_h, max_width + padding_h)
        self.bubble_height = text_rect.height() + padding_v
        
        # Minimum size
        self.bubble_width = max(self.bubble_width, 60)
        self.bubble_height = max(self.bubble_height, 35)
        
        # Set widget size (add space for tail)
        tail_space = 10
        total_width = self.bubble_width + tail_space
        self.setFixedSize(int(total_width), int(self.bubble_height))
    
    def paintEvent(self, event):
        """Paint bubble with improved rendering"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Colors
        if self.is_sent:
            bubble_color = QColor(KakaoColors.SENT_BUBBLE)
            text_color = QColor(KakaoColors.TEXT_BLACK)
            painter.setPen(Qt.NoPen)
        else:
            bubble_color = QColor(KakaoColors.RECEIVED_BUBBLE)
            text_color = QColor(KakaoColors.TEXT_BLACK)
            painter.setPen(QPen(QColor(KakaoColors.BORDER), 1))
        
        painter.setBrush(QBrush(bubble_color))
        
        # Draw bubble with tail
        path = QPainterPath()
        
        if self.is_sent:
            # Right-aligned bubble with right tail
            bubble_rect = QRectF(0, 0, self.bubble_width - 2, self.bubble_height)
            path.addRoundedRect(bubble_rect, 16, 16)
            
            # Tail
            tail_path = QPainterPath()
            tail_y = self.bubble_height / 2
            tail_path.moveTo(self.bubble_width - 4, tail_y - 4)
            tail_path.lineTo(self.bubble_width + 3, tail_y)
            tail_path.lineTo(self.bubble_width - 4, tail_y + 4)
            tail_path.closeSubpath()
            
            path = path.united(tail_path)
        else:
            # Left-aligned bubble with left tail
            bubble_rect = QRectF(7, 0, self.bubble_width - 2, self.bubble_height)
            path.addRoundedRect(bubble_rect, 16, 16)
            
            # Tail
            tail_path = QPainterPath()
            tail_y = self.bubble_height / 2
            tail_path.moveTo(7, tail_y - 4)
            tail_path.lineTo(0, tail_y)
            tail_path.lineTo(7, tail_y + 4)
            tail_path.closeSubpath()
            
            path = path.united(tail_path)
        
        painter.drawPath(path)
        
        # Draw text with proper font
        painter.setPen(text_color)
        font = QFont("Malgun Gothic", 13)
        font.setHintingPreference(QFont.PreferFullHinting)
        painter.setFont(font)
        
        # Text rectangle
        if self.is_sent:
            text_rect = QRectF(12, 8, self.bubble_width - 24, self.bubble_height - 16)
        else:
            text_rect = QRectF(19, 8, self.bubble_width - 24, self.bubble_height - 16)
        
        painter.drawText(text_rect, Qt.TextWordWrap | Qt.AlignLeft, self.text)


# ================== Message Container ==================

class MessageContainer(QWidget):
    """Container for complete message with all elements"""
    
    def __init__(self, text, time, is_sent=False, sender_name=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.time = time
        self.is_sent = is_sent
        self.sender_name = sender_name
        self.init_ui()
    
    def init_ui(self):
        """Initialize message UI"""
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 4, 10, 4)
        main_layout.setSpacing(8)
        
        # Content container
        content_widget = QWidget()
        content_widget.setMaximumWidth(280)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)
        
        # Profile for received messages
        if not self.is_sent and self.sender_name:
            profile = ProfileWidget(self.sender_name)
            main_layout.addWidget(profile, alignment=Qt.AlignTop)
            
            # Sender name
            name_label = QLabel(self.sender_name)
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {KakaoColors.TEXT_NAME};
                    font-size: 12px;
                    font-family: "Malgun Gothic";
                    padding-left: 8px;
                    margin-bottom: 2px;
                }}
            """)
            content_layout.addWidget(name_label)
        
        # Message row (bubble + time)
        message_row = QHBoxLayout()
        message_row.setSpacing(6)
        
        # Create bubble
        bubble = EnhancedBubble(self.text, self.is_sent)
        
        # Time label
        time_label = QLabel(self.time)
        time_label.setStyleSheet(f"""
            QLabel {{
                color: {KakaoColors.TEXT_GRAY};
                font-size: 11px;
                font-family: "Malgun Gothic";
                margin: 0px;
                padding: 2px;
            }}
        """)
        
        # Arrange based on sent/received
        if self.is_sent:
            message_row.addWidget(time_label, alignment=Qt.AlignBottom)
            message_row.addWidget(bubble, alignment=Qt.AlignRight)
        else:
            message_row.addWidget(bubble, alignment=Qt.AlignLeft)
            message_row.addWidget(time_label, alignment=Qt.AlignBottom)
        
        content_layout.addLayout(message_row)
        
        # Position the entire message
        if self.is_sent:
            main_layout.addStretch()
            main_layout.addWidget(content_widget)
        else:
            main_layout.addWidget(content_widget)
            main_layout.addStretch()


# ================== Main Window ==================

class KakaoTalkFixedWindow(QMainWindow):
    """Fixed KakaoTalk window with all issues resolved"""
    
    def __init__(self):
        super().__init__()
        self.input_field = None
        self.messages = []
        self.init_ui()
        self.load_sample_messages()
    
    def init_ui(self):
        """Initialize UI with proper settings"""
        self.setWindowTitle("KakaoTalk - Fixed Version")
        
        # Responsive window sizing
        screen = QApplication.primaryScreen().geometry()
        width = min(420, int(screen.width() * 0.3))
        height = min(720, int(screen.height() * 0.8))
        self.setGeometry(100, 50, width, height)
        self.setMinimumSize(360, 500)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Chat area
        self.chat_area = self.create_chat_area()
        layout.addWidget(self.chat_area, stretch=1)
        
        # Input area
        input_area = self.create_input_area()
        layout.addWidget(input_area)
        
        # Apply global styles
        self.apply_styles()
    
    def create_header(self):
        """Create header with fixed layout"""
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {KakaoColors.HEADER_BG};
                border-bottom: 1px solid {KakaoColors.BORDER};
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        # Back button
        back_btn = QPushButton("◀")
        back_btn.setFixedSize(36, 36)
        back_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 18px;
                color: #333333;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        layout.addWidget(back_btn)
        
        # Title
        title = QLabel("KCS Messenger")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                font-family: "Malgun Gothic";
                color: #000000;
            }
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Action buttons
        for icon in ["🔍", "📞", "☰"]:
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 18px;
                    border-radius: 18px;
                }
                QPushButton:hover {
                    background-color: #F0F0F0;
                }
            """)
            layout.addWidget(btn)
        
        return header
    
    def create_chat_area(self):
        """Create scrollable chat area"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Chat widget
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(5, 10, 5, 10)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()
        
        scroll.setWidget(self.chat_widget)
        return scroll
    
    def create_input_area(self):
        """Create input area with fixed layout"""
        input_widget = QWidget()
        input_widget.setFixedHeight(65)
        input_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {KakaoColors.INPUT_BG};
                border-top: 1px solid {KakaoColors.BORDER};
            }}
        """)
        
        layout = QHBoxLayout(input_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Plus button
        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(36, 36)
        plus_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: none;
                border-radius: 18px;
                font-size: 20px;
                font-weight: bold;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
            }
        """)
        layout.addWidget(plus_btn)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("메시지를 입력하세요")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: none;
                border-radius: 18px;
                padding: 8px 15px;
                font-size: 14px;
                font-family: "Malgun Gothic";
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                outline: none;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_field, stretch=1)
        
        # Send button
        send_btn = QPushButton("전송")
        send_btn.setFixedSize(60, 36)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {KakaoColors.SENT_BUBBLE};
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: bold;
                font-family: "Malgun Gothic";
                color: #3C1E1E;
            }}
            QPushButton:hover {{
                background-color: #FFD700;
            }}
            QPushButton:pressed {{
                background-color: #FFC700;
            }}
        """)
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)
        
        return input_widget
    
    def apply_styles(self):
        """Apply global styles"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {KakaoColors.CHAT_BACKGROUND};
            }}
            QScrollArea {{
                background-color: {KakaoColors.CHAT_BACKGROUND};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgba(0, 0, 0, 0.3);
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
    
    def load_sample_messages(self):
        """Load sample messages"""
        messages = [
            {"text": "안녕하세요! 화면이 깨지는 문제를 해결했습니다.", "sent": False, "sender": "시스템"},
            {"text": "정말 감사합니다! 이제 잘 보이네요.", "sent": True},
            {"text": "인코딩, 레이아웃, 버블 렌더링 모두 수정했습니다.", "sent": False, "sender": "시스템"},
            {"text": "완벽해요! 👍", "sent": True},
        ]
        
        for msg in messages:
            self.add_message(
                msg["text"],
                self.get_current_time(),
                msg["sent"],
                msg.get("sender")
            )
    
    def add_message(self, text, time, is_sent, sender_name=None):
        """Add message to chat"""
        message = MessageContainer(text, time, is_sent, sender_name)
        
        # Insert before stretch
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, message)
        
        # Scroll to bottom
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def send_message(self):
        """Send message from input"""
        text = self.input_field.text().strip()
        if text:
            # Add user message
            self.add_message(text, self.get_current_time(), True)
            self.input_field.clear()
            
            # Simulate response
            QTimer.singleShot(1500, lambda: self.simulate_response())
    
    def simulate_response(self):
        """Simulate response message"""
        responses = [
            "네, 알겠습니다!",
            "좋은 생각이에요.",
            "확인했습니다.",
            "감사합니다!",
            "동의합니다.",
        ]
        
        response = random.choice(responses)
        sender = random.choice(["김철수", "이영희", "박민수"])
        
        self.add_message(response, self.get_current_time(), False, sender)
    
    def get_current_time(self):
        """Get current time in Korean format"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        period = "오전" if hour < 12 else "오후"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        
        return f"{period} {display_hour}:{minute:02d}"
    
    def scroll_to_bottom(self):
        """Scroll to bottom of chat"""
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        # Adjust message widths if needed
        QTimer.singleShot(10, self.scroll_to_bottom)


# ================== Main Application ==================

def main():
    """Run application with proper settings"""
    app = QApplication(sys.argv)
    
    # Set application attributes for high DPI
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set style
    app.setStyle('Fusion')
    
    # Set font with fallback
    font_families = [
        "Malgun Gothic",
        "맑은 고딕",
        "Apple SD Gothic Neo",
        "Noto Sans CJK KR",
        "Arial",
        "sans-serif"
    ]
    
    font = QFont()
    font.setFamilies(font_families)
    font.setPointSize(10)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)
    
    # Create and show window
    window = KakaoTalkFixedWindow()
    window.show()
    
    # Center on screen
    screen = app.primaryScreen().geometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()