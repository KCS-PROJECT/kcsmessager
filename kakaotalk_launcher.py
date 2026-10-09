#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KakaoTalk Unified Launcher - 통합 런처 (개선된 UI)
모든 기능을 하나로 통합한 최종 런처
- 실시간 채팅 서버/클라이언트 관리
- 독립 실행 데모 모드
- 개선된 UI 가시성
"""

import sys
import subprocess
import time
import os
import locale
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# Windows UTF-8 인코딩 설정
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


class UnifiedKakaoTalkLauncher(QMainWindow):
    """통합 카카오톡 런처 - 개선된 UI"""
    
    def __init__(self):
        super().__init__()
        self.server_process = None
        self.client_processes = []
        self.demo_windows = []
        self.init_ui()
        
    def init_ui(self):
        """런처 UI 초기화 - 개선된 가시성"""
        self.setWindowTitle("🚀 KCS Talk 통합 런처 v3.1")
        
        # 더 큰 윈도우 크기 설정
        self.setMinimumSize(850, 750)
        self.resize(900, 800)
        
        # 윈도우 아이콘 설정
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # Central widget with scroll area
        central = QWidget()
        self.setCentralWidget(central)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        central_layout.addWidget(scroll)
        
        # Main content widget
        content = QWidget()
        scroll.setWidget(content)
        
        # Main layout
        layout = QVBoxLayout(content)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title - 더 작게
        title = QLabel("🚀 KCS Talk 통합 런처")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #2C2C2C;
                margin: 10px 0px 15px 0px;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFE400, stop:1 #FFD700);
                border-radius: 12px;
                border: 2px solid #E6C200;
            }
        """)
        layout.addWidget(title)
        
        # 실시간 채팅 섹션
        realtime_group = QGroupBox("💬 실시간 채팅")
        realtime_group.setStyleSheet(self.get_groupbox_style())
        realtime_layout = QVBoxLayout(realtime_group)
        realtime_layout.setSpacing(12)
        realtime_layout.setContentsMargins(15, 20, 15, 15)
        
        # 서버 상태 - 더 눈에 띄게
        self.server_status = QLabel("● 서버 상태: 중지됨")
        self.server_status.setStyleSheet(self.get_status_style(False))
        self.server_status.setMinimumHeight(35)
        realtime_layout.addWidget(self.server_status)
        
        # 서버 버튼들
        server_btn_layout = QHBoxLayout()
        server_btn_layout.setSpacing(10)
        
        self.start_server_btn = QPushButton("🚀 서버 시작")
        self.start_server_btn.setStyleSheet(self.get_button_style("#4CAF50", "#45A049"))
        self.start_server_btn.setMinimumHeight(45)
        self.start_server_btn.clicked.connect(self.start_server)
        server_btn_layout.addWidget(self.start_server_btn)
        
        self.stop_server_btn = QPushButton("⏹️ 서버 중지")
        self.stop_server_btn.setStyleSheet(self.get_button_style("#F44336", "#E53935"))
        self.stop_server_btn.setMinimumHeight(45)
        self.stop_server_btn.clicked.connect(self.stop_server)
        self.stop_server_btn.setEnabled(False)
        server_btn_layout.addWidget(self.stop_server_btn)
        
        realtime_layout.addLayout(server_btn_layout)
        
        # 클라이언트 상태 - 더 눈에 띄게
        self.client_status = QLabel("활성 클라이언트: 0개")
        self.client_status.setStyleSheet(self.get_status_style(False))
        self.client_status.setMinimumHeight(35)
        realtime_layout.addWidget(self.client_status)
        
        # 클라이언트 버튼들
        client_btn_layout = QHBoxLayout()
        client_btn_layout.setSpacing(10)
        
        self.open_client_btn = QPushButton("💬 채팅창 열기")
        self.open_client_btn.setStyleSheet(self.get_button_style("#FFE400", "#FFD700", "#2C2C2C"))
        self.open_client_btn.setMinimumHeight(45)
        self.open_client_btn.clicked.connect(self.open_client)
        client_btn_layout.addWidget(self.open_client_btn)
        
        self.open_two_btn = QPushButton("👥 2개 창 열기")
        self.open_two_btn.setStyleSheet(self.get_button_style("#2196F3", "#1976D2"))
        self.open_two_btn.setMinimumHeight(45)
        self.open_two_btn.clicked.connect(self.open_two_clients)
        client_btn_layout.addWidget(self.open_two_btn)
        
        realtime_layout.addLayout(client_btn_layout)
        layout.addWidget(realtime_group)
        
        # 빠른 실행 섹션
        quick_group = QGroupBox("⚡ 빠른 실행")
        quick_group.setStyleSheet(self.get_groupbox_style())
        quick_layout = QVBoxLayout(quick_group)
        quick_layout.setSpacing(12)
        quick_layout.setContentsMargins(15, 20, 15, 15)
        
        # 완전한 시작 버튼
        self.quick_start_btn = QPushButton("🚀 완전한 시작 (서버 + 2개 채팅창)")
        self.quick_start_btn.setStyleSheet(self.get_large_button_style("#9C27B0", "#7B1FA2"))
        self.quick_start_btn.setMinimumHeight(50)
        self.quick_start_btn.clicked.connect(self.quick_start)
        quick_layout.addWidget(self.quick_start_btn)
        
        # 데모 모드 버튼
        self.demo_btn = QPushButton("🎨 데모 모드 (서버 없이 UI 테스트)")
        self.demo_btn.setStyleSheet(self.get_large_button_style("#FF9800", "#F57C00"))
        self.demo_btn.setMinimumHeight(50)
        self.demo_btn.clicked.connect(self.start_demo_mode)
        quick_layout.addWidget(self.demo_btn)
        
        # 내장 데모 버튼
        self.builtin_demo_btn = QPushButton("🎭 내장 데모 (완전 독립 실행)")
        self.builtin_demo_btn.setStyleSheet(self.get_large_button_style("#4CAF50", "#45A049"))
        self.builtin_demo_btn.setMinimumHeight(50)
        self.builtin_demo_btn.clicked.connect(self.start_builtin_demo)
        quick_layout.addWidget(self.builtin_demo_btn)
        
        layout.addWidget(quick_group)
        
        # 상태 및 정보 섹션 - 더 크고 눈에 띄게
        info_group = QGroupBox("📊 상태 정보")
        info_group.setStyleSheet(self.get_groupbox_style())
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(15, 20, 15, 15)
        
        self.info_label = QLabel("런처가 준비되었습니다.")
        self.info_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
                font-weight: 500;
                padding: 12px;
                background-color: #F8F9FA;
                border-radius: 8px;
                border: 2px solid #E9ECEF;
                min-height: 25px;
            }
        """)
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(info_group)
        
        # Instructions - 더 읽기 쉽게
        instructions = QLabel(
            "📋 사용 가이드:\n\n"
            "🚀 완전한 시작: 서버를 시작하고 2개의 채팅창을 열어 실시간 채팅을 시작합니다\n"
            "🎨 데모 모드: 외부 데모 파일을 실행하여 UI를 테스트합니다\n"
            "🎭 내장 데모: 런처 내장 데모로 서버 없이 완전 독립 실행됩니다\n"
            "💬 각 채팅창에서 다른 이름으로 로그인하여 실시간 메시지를 주고받을 수 있습니다"
        )
        instructions.setStyleSheet("""
            QLabel {
                color: #444444;
                font-size: 13px;
                line-height: 1.6;
                padding: 15px 20px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8F9FA);
                border: 2px solid #DEE2E6;
                border-radius: 10px;
                margin-top: 5px;
            }
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Add stretch to push content up
        layout.addStretch()
        
        # Apply global style
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F5F5F5);
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
        
        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # 2초마다 상태 업데이트
    
    def get_groupbox_style(self):
        """그룹박스 공통 스타일 - 개선된 가시성"""
        return """
            QGroupBox {
                font-size: 15px;
                font-weight: bold;
                color: #2C2C2C;
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
                padding: 4px 10px 4px 10px;
                background-color: #FFFFFF;
                border: 2px solid #D0D0D0;
                border-radius: 5px;
            }
        """
    
    def get_status_style(self, is_active=False):
        """상태 라벨 스타일 - 더 눈에 띄게"""
        if is_active:
            return """
                QLabel {
                    color: #2E7D32;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px 14px;
                    background-color: #E8F5E9;
                    border-radius: 6px;
                    border: 2px solid #4CAF50;
                }
            """
        else:
            return """
                QLabel {
                    color: #555555;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 10px 14px;
                    background-color: #F0F0F0;
                    border-radius: 6px;
                    border: 2px solid #E0E0E0;
                }
            """
    
    def get_button_style(self, color1, color2, text_color="white"):
        """버튼 스타일 - 최적화된 크기"""
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color1}, stop:1 {color2});
                color: {text_color};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color2}, stop:1 {color1});
            }}
            QPushButton:pressed {{
                background: {color2};
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #888888;
            }}
        """
    
    def get_large_button_style(self, color1, color2):
        """큰 버튼 스타일 - 최적화된 크기"""
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color1}, stop:1 {color2});
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color2}, stop:1 {color1});
            }}
            QPushButton:pressed {{
                background: {color2};
            }}
        """
    
    def start_server(self):
        """서버 시작"""
        if not self.server_process:
            try:
                # 사용 가능한 서버 파일 찾기
                server_files = [
                    "simple_chat_server.py",
                    os.path.join("server", "chat", "chat_server.py"),
                ]
                
                server_path = None
                for path in server_files:
                    if os.path.exists(path):
                        server_path = path
                        break
                
                if not server_path:
                    raise FileNotFoundError("채팅 서버 파일을 찾을 수 없습니다")
                
                self.server_process = subprocess.Popen(
                    [sys.executable, server_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
                )
                
                # 서버 시작 대기
                time.sleep(1.5)
                
                self.server_status.setText("● 서버 상태: 실행 중 🟢")
                self.server_status.setStyleSheet(self.get_status_style(True))
                
                self.start_server_btn.setEnabled(False)
                self.stop_server_btn.setEnabled(True)
                self.info_label.setText("✅ 서버가 성공적으로 시작되었습니다! 이제 채팅창을 열 수 있습니다.")
                
                QMessageBox.information(self, "✅ 서버 시작 완료", 
                                      "채팅 서버가 성공적으로 시작되었습니다!\n이제 채팅창을 열 수 있습니다.")
                
            except Exception as e:
                self.info_label.setText(f"❌ 서버 시작 실패: {str(e)}")
                QMessageBox.critical(self, "❌ 서버 시작 실패", f"서버 시작 중 오류가 발생했습니다:\n{str(e)}")
    
    def stop_server(self):
        """서버 중지"""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process = None
                
                self.server_status.setText("● 서버 상태: 중지됨 🔴")
                self.server_status.setStyleSheet(self.get_status_style(False))
                
                self.start_server_btn.setEnabled(True)
                self.stop_server_btn.setEnabled(False)
                
                # 모든 클라이언트 창 닫기
                for process in self.client_processes:
                    try:
                        process.terminate()
                    except:
                        pass
                self.client_processes.clear()
                self.update_client_count()
                
                self.info_label.setText("⏹️ 서버가 중지되었습니다.")
                
            except Exception as e:
                self.info_label.setText(f"❌ 서버 중지 실패: {str(e)}")
                QMessageBox.critical(self, "❌ 서버 중지 실패", f"서버 중지 중 오류가 발생했습니다:\n{str(e)}")
    
    def open_client(self):
        """클라이언트 창 열기"""
        try:
            # 사용 가능한 클라이언트 파일 찾기
            client_files = [
                "kakaotalk_real_chat.py",
                os.path.join("client", "realtime", "chat_client.py"),
            ]
            
            client_path = None
            for path in client_files:
                if os.path.exists(path):
                    client_path = path
                    break
            
            if not client_path:
                raise FileNotFoundError("채팅 클라이언트 파일을 찾을 수 없습니다")
            
            process = subprocess.Popen(
                [sys.executable, client_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            self.client_processes.append(process)
            self.update_client_count()
            self.info_label.setText("💬 새 채팅창이 열렸습니다.")
            
        except Exception as e:
            self.info_label.setText(f"❌ 클라이언트 실행 실패: {str(e)}")
            QMessageBox.critical(self, "❌ 클라이언트 실행 실패", f"클라이언트 실행 중 오류가 발생했습니다:\n{str(e)}")
    
    def open_two_clients(self):
        """2개 클라이언트 창 열기"""
        self.open_client()
        time.sleep(0.8)  # 창이 겹치지 않도록 지연
        self.open_client()
        self.info_label.setText("👥 2개의 채팅창이 열렸습니다.")
    
    def start_demo_mode(self):
        """외부 데모 모드 시작"""
        try:
            # 독립 실행 가능한 데모 파일 찾기
            demo_files = [
                "kakaotalk_standalone.py",
                os.path.join("client", "standalone", "standalone_chat.py"),
            ]
            
            demo_path = None
            for path in demo_files:
                if os.path.exists(path):
                    demo_path = path
                    break
            
            if not demo_path:
                QMessageBox.information(self, "ℹ️ 데모 모드", 
                                      "외부 데모 파일을 찾을 수 없습니다.\n내장 데모를 사용하거나 일반 클라이언트를 실행합니다.")
                self.start_builtin_demo()
                return
            
            subprocess.Popen(
                [sys.executable, demo_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            
            self.info_label.setText("🎨 외부 데모 모드가 시작되었습니다.")
            QMessageBox.information(self, "🎨 데모 모드 시작", 
                                  "외부 데모 모드가 시작되었습니다!\n서버 없이 UI를 테스트할 수 있습니다.")
            
        except Exception as e:
            self.info_label.setText(f"❌ 데모 시작 실패: {str(e)}")
            QMessageBox.critical(self, "❌ 데모 시작 실패", f"데모 모드 시작 중 오류가 발생했습니다:\n{str(e)}")
    
    def start_builtin_demo(self):
        """내장 데모 시작"""
        try:
            demo_window = BuiltinDemoWindow()
            demo_window.show()
            self.demo_windows.append(demo_window)
            self.info_label.setText("🎭 내장 데모가 시작되었습니다.")
            QMessageBox.information(self, "🎭 내장 데모 시작", 
                                  "내장 데모가 시작되었습니다!\n완전히 독립적으로 작동합니다.")
        except Exception as e:
            self.info_label.setText(f"❌ 내장 데모 실패: {str(e)}")
            QMessageBox.critical(self, "❌ 내장 데모 실패", f"내장 데모 시작 중 오류가 발생했습니다:\n{str(e)}")
    
    def quick_start(self):
        """빠른 시작 - 서버 + 2개 클라이언트"""
        if not self.server_process:
            self.start_server()
            time.sleep(2)  # 서버 완전 시작 대기
        
        self.open_two_clients()
        self.info_label.setText("🚀 빠른 시작 완료! 서버와 2개 채팅창이 실행되었습니다.")
        
        QMessageBox.information(self, "🚀 빠른 시작 완료", 
                              "서버와 2개의 채팅창이 시작되었습니다!\n각 창에서 다른 이름으로 로그인하세요.")
    
    def update_client_count(self):
        """클라이언트 개수 업데이트"""
        # 종료된 프로세스 정리
        self.client_processes = [p for p in self.client_processes if p.poll() is None]
        count = len(self.client_processes)
        
        if count == 0:
            status_text = "활성 클라이언트: 없음 ⭕"
            style = self.get_status_style(False)
        else:
            status_text = f"활성 클라이언트: {count}개 🟢"
            style = self.get_status_style(True)
            
        self.client_status.setText(status_text)
        self.client_status.setStyleSheet(style)
    
    def update_status(self):
        """전체 상태 업데이트"""
        self.update_client_count()
        
        # 데모 창 정리
        self.demo_windows = [w for w in self.demo_windows if not w.isHidden()]
    
    def closeEvent(self, event):
        """창 닫기 이벤트 처리"""
        reply = QMessageBox.question(self, '종료 확인', 
                                   '런처를 종료하시겠습니까?\n실행 중인 모든 프로세스가 함께 종료됩니다.',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 모든 프로세스 종료
            if self.server_process:
                try:
                    self.server_process.terminate()
                except:
                    pass
            
            for process in self.client_processes:
                try:
                    process.terminate()
                except:
                    pass
            
            for window in self.demo_windows:
                try:
                    window.close()
                except:
                    pass
            
            event.accept()
        else:
            event.ignore()


class BuiltinDemoWindow(QMainWindow):
    """내장 데모 창 - 완전 독립 실행"""
    
    def __init__(self):
        super().__init__()
        self.messages = []
        self.init_ui()
        self.start_demo_sequence()
    
    def init_ui(self):
        """데모 UI 초기화"""
        self.setWindowTitle("KCS Talk - 내장 데모")
        self.setGeometry(100, 100, 450, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        
        title_label = QLabel("데모 채팅방")
        title_label.setStyleSheet("""
            QLabel {
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 18px;
                font-weight: 600;
                color: #2C2C2C;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        status_label = QLabel("● 데모 모드")
        status_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        header_layout.addWidget(status_label)
        
        layout.addWidget(header)
        
        # 채팅 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #B8D4E3;
                border: none;
            }
        """)
        
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background-color: #B8D4E3;")
        
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        
        scroll.setWidget(self.chat_widget)
        layout.addWidget(scroll)
        
        # 입력 영역
        input_widget = QWidget()
        input_widget.setFixedHeight(60)
        input_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-top: 1px solid #E0E0E0;
            }
        """)
        
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(12, 10, 12, 10)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("메시지 입력 (데모용)")
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 2px solid #E0E0E0;
                border-radius: 22px;
                padding: 12px 18px;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 15px;
                background-color: #F8F9FA;
                color: #2C2C2C;
            }
            QLineEdit:focus {
                border: 2px solid #FFE400;
                background-color: #FFFFFF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_demo_message)
        input_layout.addWidget(self.input_field)
        
        send_btn = QPushButton("전송")
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFE400;
                border: none;
                border-radius: 22px;
                padding: 12px 24px;
                font-family: "Malgun Gothic", "맑은 고딕", sans-serif;
                font-size: 15px;
                font-weight: bold;
                color: #2C2C2C;
            }
            QPushButton:hover {
                background-color: #FFD700;
            }
            QPushButton:pressed {
                background-color: #FFC107;
            }
        """)
        send_btn.clicked.connect(self.send_demo_message)
        input_layout.addWidget(send_btn)
        
        layout.addWidget(input_widget)
    
    def start_demo_sequence(self):
        """데모 시퀀스 시작"""
        # 시작 메시지
        QTimer.singleShot(500, lambda: self.add_system_message("데모 모드로 실행 중입니다"))
        QTimer.singleShot(1000, lambda: self.add_system_message("실제 네트워크 연결 없이 동작합니다"))
        
        # 샘플 대화
        demo_messages = [
            ("안녕하세요! 데모 모드입니다", "오전 10:30", False, "데모봇"),
            ("네, 안녕하세요!", "오전 10:31", True, None),
            ("이 창에서 메시지를 입력해보세요", "오전 10:32", False, "데모봇"),
            ("모든 기능이 정상 작동합니다", "오전 10:33", False, "데모봇"),
        ]
        
        for i, (text, time_str, is_sent, sender) in enumerate(demo_messages):
            QTimer.singleShot(2000 + i * 800, 
                            lambda t=text, tm=time_str, s=is_sent, sn=sender: 
                            self.add_demo_message(t, tm, s, sn))
    
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
    
    def add_demo_message(self, text, time_str, is_sent, sender_name=None):
        """데모 메시지 추가"""
        message_widget = DemoMessageWidget(text, time_str, is_sent, sender_name)
        count = self.chat_layout.count()
        self.chat_layout.insertWidget(count - 1, message_widget)
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def send_demo_message(self):
        """데모 메시지 전송"""
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            
            # 현재 시간
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            period = "오전" if hour < 12 else "오후"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            time_str = f"{period} {display_hour}:{minute:02d}"
            
            # 내 메시지 추가
            self.add_demo_message(text, time_str, True)
            
            # 자동 응답 (1초 후)
            responses = [
                "좋은 메시지네요!",
                "데모 모드에서 잘 작동하고 있습니다.",
                "실제 채팅과 동일한 느낌이죠?",
                "계속 테스트해보세요!",
                "멋진 기능입니다!",
            ]
            import random
            response = random.choice(responses)
            
            QTimer.singleShot(1000, lambda: self.add_demo_message(response, time_str, False, "데모봇"))
    
    def scroll_to_bottom(self):
        """하단으로 스크롤"""
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scrollbar = scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())


class DemoMessageWidget(QWidget):
    """데모용 메시지 위젯"""
    
    def __init__(self, text, time_str, is_sent, sender_name=None):
        super().__init__()
        self.text = text
        self.time_str = time_str
        self.is_sent = is_sent
        self.sender_name = sender_name
        self.init_ui()
    
    def init_ui(self):
        """메시지 UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(6)
        
        if not self.is_sent and self.sender_name:
            # 프로필 이미지 (간단한 원)
            profile = QLabel()
            profile.setFixedSize(40, 40)
            profile.setStyleSheet("""
                QLabel {
                    background-color: #4A90E2;
                    border-radius: 20px;
                    color: white;
                    font-weight: bold;
                    font-size: 16px;
                }
            """)
            profile.setAlignment(Qt.AlignCenter)
            profile.setText(self.sender_name[0] if self.sender_name else "?")
            layout.addWidget(profile, alignment=Qt.AlignTop)
        
        # 메시지 내용
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        
        if not self.is_sent and self.sender_name:
            name_label = QLabel(self.sender_name)
            name_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 13px;
                    font-weight: 500;
                    padding-left: 12px;
                    padding-bottom: 4px;
                }
            """)
            content_layout.addWidget(name_label)
        
        # 메시지 버블과 시간
        bubble_layout = QHBoxLayout()
        bubble_layout.setSpacing(4)
        
        # 메시지 버블
        bubble = QLabel(self.text)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(250)
        
        if self.is_sent:
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #FFE400;
                    color: #000000;
                    padding: 10px 15px;
                    border-radius: 18px;
                    font-size: 14px;
                }
            """)
        else:
            bubble.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    color: #000000;
                    padding: 10px 15px;
                    border-radius: 18px;
                    border: 1px solid #E0E0E0;
                    font-size: 14px;
                }
            """)
        
        # 시간 라벨
        time_label = QLabel(self.time_str)
        time_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                padding: 2px 4px;
            }
        """)
        
        if self.is_sent:
            bubble_layout.addWidget(time_label, alignment=Qt.AlignBottom)
            bubble_layout.addWidget(bubble)
        else:
            bubble_layout.addWidget(bubble)
            bubble_layout.addWidget(time_label, alignment=Qt.AlignBottom)
        
        content_layout.addLayout(bubble_layout)
        
        if self.is_sent:
            layout.addStretch()
            layout.addWidget(content_widget)
        else:
            layout.addWidget(content_widget)
            layout.addStretch()


def main():
    """메인 함수 - 통합 런처 실행"""
    # High DPI 지원 설정
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 환경 변수 설정
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    
    app = QApplication(sys.argv)
    
    # 애플리케이션 스타일 설정
    app.setStyle('Fusion')
    
    # 시스템에 맞는 폰트 설정
    if os.name == 'nt':  # Windows
        font = QFont("Malgun Gothic", 10)
    else:  # macOS, Linux
        font = QFont("Arial", 10)
    
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)
    
    # 애플리케이션 정보 설정
    app.setApplicationName("KCS Talk Unified Launcher")
    app.setApplicationVersion("3.1")
    app.setOrganizationName("KCS Messenger")
    
    # 런처 생성 및 표시
    launcher = UnifiedKakaoTalkLauncher()
    launcher.show()
    
    # 시작 메시지
    QMessageBox.information(launcher, "🎉 KCS Talk 통합 런처 v3.1", 
                          "KCS Talk 통합 런처에 오신 것을 환영합니다!\n\n"
                          "🚀 완전한 시작: 실시간 채팅 (서버 + 클라이언트)\n"
                          "🎨 데모 모드: 외부 데모 파일 실행\n"
                          "🎭 내장 데모: 완전 독립 실행 데모\n"
                          "⚙️ 개별 관리: 세부 제어\n\n"
                          "UI가 개선되어 모든 버튼과 상태가 더 잘 보입니다!")
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()