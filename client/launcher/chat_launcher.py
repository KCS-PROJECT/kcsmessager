#!/usr/bin/env python
"""
Launcher for Real KakaoTalk Chat System
Starts server and multiple client windows for real communication
"""

import sys
import subprocess
import time
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import os


class ChatLauncher(QMainWindow):
    """Launcher window for managing chat server and clients"""
    
    def __init__(self):
        super().__init__()
        self.server_process = None
        self.client_processes = []
        self.init_ui()
        
    def init_ui(self):
        """Initialize launcher UI"""
        self.setWindowTitle("KakaoTalk Real Chat Launcher")
        # 충분한 크기 설정 - 모든 요소가 잘 보이도록 조정
        self.setMinimumSize(600, 500)
        self.resize(650, 550)
        
        # 윈도우 아이콘 설정 (옵션)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout - 더 넉넉한 여백과 간격 설정
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title - 더 나은 타이포그래피
        title = QLabel("KakaoTalk 실시간 채팅 런처")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #2C2C2C;
                margin: 10px 0px 20px 0px;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFE400, stop:1 #FFD700);
                border-radius: 8px;
                border: 1px solid #E6C200;
            }
        """)
        layout.addWidget(title)
        
        # Server section - 개선된 그룹박스 스타일
        server_group = QGroupBox("서버 관리")
        server_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                border: 2px solid #D0D0D0;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 2px 8px 2px 8px;
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
            }
        """)
        server_layout = QVBoxLayout(server_group)
        server_layout.setSpacing(12)
        server_layout.setContentsMargins(15, 20, 15, 15)
        
        # Server status - 더 나은 시각적 피드백
        self.server_status = QLabel("● 서버 상태: 중지됨")
        self.server_status.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
                padding: 8px 12px;
                background-color: #F0F0F0;
                border-radius: 6px;
                border: 1px solid #E0E0E0;
            }
        """)
        server_layout.addWidget(self.server_status)
        
        # Server buttons
        server_btn_layout = QHBoxLayout()
        server_btn_layout.setSpacing(10)
        
        self.start_server_btn = QPushButton("서버 시작")
        self.start_server_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45A049);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 14px 28px;
                font-size: 14px;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45A049, stop:1 #3E8E41);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3E8E41, stop:1 #357A32);
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.start_server_btn.clicked.connect(self.start_server)
        server_btn_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("서버 중지")
        self.stop_server_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F44336, stop:1 #E53935);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 14px 28px;
                font-size: 14px;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E53935, stop:1 #D32F2F);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D32F2F, stop:1 #C62828);
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.stop_server_btn.clicked.connect(self.stop_server)
        self.stop_server_btn.setEnabled(False)
        server_btn_layout.addWidget(self.stop_server_btn)
        
        server_layout.addLayout(server_btn_layout)
        layout.addWidget(server_group)
        
        # Client section - 서버 섹션과 동일한 스타일 적용
        client_group = QGroupBox("클라이언트 관리")
        client_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
                border: 2px solid #D0D0D0;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 15px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 2px 8px 2px 8px;
                background-color: #FFFFFF;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
            }
        """)
        client_layout = QVBoxLayout(client_group)
        client_layout.setSpacing(12)
        client_layout.setContentsMargins(15, 20, 15, 15)
        
        # Client status - 서버 상태와 동일한 스타일
        self.client_status = QLabel("활성 클라이언트: 0개")
        self.client_status.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
                padding: 8px 12px;
                background-color: #F0F0F0;
                border-radius: 6px;
                border: 1px solid #E0E0E0;
            }
        """)
        client_layout.addWidget(self.client_status)
        
        # Client buttons
        client_btn_layout = QHBoxLayout()
        client_btn_layout.setSpacing(10)
        
        self.open_client_btn = QPushButton("채팅창 열기")
        self.open_client_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFE400, stop:1 #FFD700);
                color: #2C2C2C;
                border: none;
                border-radius: 6px;
                padding: 14px 28px;
                font-size: 14px;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFD700, stop:1 #FFC107);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFC107, stop:1 #FF9800);
            }
        """)
        self.open_client_btn.clicked.connect(self.open_client)
        client_btn_layout.addWidget(self.open_client_btn)
        
        self.open_two_btn = QPushButton("2개 창 열기")
        self.open_two_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2196F3, stop:1 #1976D2);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 14px 28px;
                font-size: 14px;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1976D2, stop:1 #1565C0);
                transform: translateY(-1px);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1565C0, stop:1 #0D47A1);
            }
        """)
        self.open_two_btn.clicked.connect(self.open_two_clients)
        client_btn_layout.addWidget(self.open_two_btn)
        
        client_layout.addLayout(client_btn_layout)
        layout.addWidget(client_group)
        
        # Quick start button - 더 눈에 띄는 디자인
        self.quick_start_btn = QPushButton("🚀 빠른 시작 (서버 + 2개 창)")
        self.quick_start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9C27B0, stop:1 #7B1FA2);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 18px 36px;
                font-size: 16px;
                font-weight: bold;
                margin: 20px 0px 15px 0px;
                min-height: 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7B1FA2, stop:1 #6A1B9A);
                transform: translateY(-2px);
                box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6A1B9A, stop:1 #4A148C);
                transform: translateY(0px);
            }
        """)
        self.quick_start_btn.clicked.connect(self.quick_start)
        layout.addWidget(self.quick_start_btn)
        
        # Instructions - 더 읽기 쉬운 스타일
        instructions = QLabel(
            "📋 사용법:\n"
            "• '빠른 시작' 버튼으로 서버와 2개 창을 한번에 시작\n"
            "• 각 창에서 다른 이름으로 로그인\n"
            "• 실시간으로 메시지 주고받기 가능"
        )
        instructions.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 12px;
                line-height: 1.4;
                padding: 16px 20px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F8F9FA, stop:1 #E9ECEF);
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                margin-top: 5px;
            }
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Apply global style - 더 나은 전체 테마
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8F9FA);
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
            }
        """)
    
    def start_server(self):
        """Start the chat server"""
        if not self.server_process:
            try:
                # 프로젝트 루트 디렉토리 기준으로 경로 설정
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                server_path = os.path.join(project_root, "server", "chat", "chat_server.py")
                
                self.server_process = subprocess.Popen(
                    [sys.executable, server_path],
                    cwd=project_root,  # 작업 디렉토리를 프로젝트 루트로 설정
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                )
                
                # Wait a moment for server to start
                time.sleep(1)
                
                self.server_status.setText("● 서버 상태: 실행 중")
                self.server_status.setStyleSheet("""
                    QLabel {
                        color: #2E7D32;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 8px 12px;
                        background-color: #E8F5E8;
                        border-radius: 6px;
                        border: 1px solid #4CAF50;
                    }
                """)
                
                self.start_server_btn.setEnabled(False)
                self.stop_server_btn.setEnabled(True)
                
                QMessageBox.information(self, "서버 시작", 
                                      "채팅 서버가 시작되었습니다.\n이제 채팅창을 열 수 있습니다.")
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"서버 시작 실패: {str(e)}")
    
    def stop_server(self):
        """Stop the chat server"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process = None
                
                self.server_status.setText("● 서버 상태: 중지됨")
                self.server_status.setStyleSheet("""
                    QLabel {
                        color: #666666;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 8px 12px;
                        background-color: #F0F0F0;
                        border-radius: 6px;
                        border: 1px solid #E0E0E0;
                    }
                """)
                
                self.start_server_btn.setEnabled(True)
                self.stop_server_btn.setEnabled(False)
                
                # Close all client windows
                for process in self.client_processes:
                    try:
                        process.terminate()
                    except:
                        pass
                self.client_processes.clear()
                self.update_client_count()
                
            except Exception as e:
                QMessageBox.critical(self, "오류", f"서버 중지 실패: {str(e)}")
    
    def open_client(self):
        """Open a single client window"""
        try:
            # 프로젝트 루트 디렉토리 기준으로 경로 설정
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            client_path = os.path.join(project_root, "client", "realtime", "chat_client.py")
            
            process = subprocess.Popen(
                [sys.executable, client_path],
                cwd=project_root,  # 작업 디렉토리를 프로젝트 루트로 설정
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            self.client_processes.append(process)
            self.update_client_count()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"클라이언트 실행 실패: {str(e)}")
    
    def open_two_clients(self):
        """Open two client windows"""
        self.open_client()
        time.sleep(0.5)  # Small delay to prevent overlap
        self.open_client()
    
    def quick_start(self):
        """Quick start server and two clients"""
        if not self.server_process:
            self.start_server()
            time.sleep(1)  # Wait for server to fully start
        
        self.open_two_clients()
    
    def update_client_count(self):
        """Update client count display"""
        # Clean up terminated processes
        self.client_processes = [p for p in self.client_processes if p.poll() is None]
        count = len(self.client_processes)
        self.client_status.setText(f"활성 클라이언트: {count}개")
    
    def closeEvent(self, event):
        """Handle window close"""
        # Stop server and clients
        if self.server_process:
            self.stop_server()
        
        for process in self.client_processes:
            try:
                process.terminate()
            except:
                pass
        
        event.accept()


def main():
    """Run the launcher"""
    # High DPI 지원 설정
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # 더 나은 스타일과 폰트 설정
    app.setStyle('Fusion')
    
    # 시스템에 맞는 폰트 설정
    if os.name == 'nt':  # Windows
        font = QFont("Malgun Gothic", 9)
    else:  # macOS, Linux
        font = QFont("Arial", 9)
    
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("KakaoTalk Real Chat Launcher")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("KCS Messenger")
    
    launcher = ChatLauncher()
    launcher.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()