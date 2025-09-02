#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KCS Messenger - Comprehensive Test Suite
Tests all versions to ensure they work properly
"""

import sys
import os
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class VersionTester(QThread):
    log_signal = pyqtSignal(str)
    
    def __init__(self, script_name):
        super().__init__()
        self.script_name = script_name
        self.process = None
        
    def run(self):
        try:
            self.log_signal.emit(f"[START] Testing {self.script_name}...")
            
            # Start the process
            self.process = subprocess.Popen(
                [sys.executable, self.script_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Wait for 3 seconds to see if it starts properly
            time.sleep(3)
            
            # Check if process is still running
            if self.process.poll() is None:
                self.log_signal.emit(f"[OK] {self.script_name} - Started successfully")
                # Terminate the process
                self.process.terminate()
                time.sleep(1)
            else:
                # Process crashed
                stdout, stderr = self.process.communicate()
                self.log_signal.emit(f"[ERROR] {self.script_name} - Failed to start")
                if stderr:
                    self.log_signal.emit(f"  Error: {stderr[:200]}")
                    
        except Exception as e:
            self.log_signal.emit(f"[ERROR] {self.script_name} - Exception: {str(e)}")
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()

class TestAllVersionsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.testers = []
        
    def init_ui(self):
        self.setWindowTitle("KCS Messenger - Version Tester")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("KCS Messenger Version Tester")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Test buttons
        button_layout = QHBoxLayout()
        
        self.test_all_btn = QPushButton("Test All Versions")
        self.test_all_btn.clicked.connect(self.test_all_versions)
        button_layout.addWidget(self.test_all_btn)
        
        self.test_fixed_btn = QPushButton("Test Fixed Version")
        self.test_fixed_btn.clicked.connect(lambda: self.test_single("kakaotalk_fixed.py"))
        button_layout.addWidget(self.test_fixed_btn)
        
        self.test_real_btn = QPushButton("Test Real Chat")
        self.test_real_btn.clicked.connect(lambda: self.test_single("kakaotalk_real_chat.py"))
        button_layout.addWidget(self.test_real_btn)
        
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(lambda: self.log_area.clear())
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace;")
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
        # Initial log
        self.log("KCS Messenger Version Tester Ready")
        self.log("=" * 60)
        
    def log(self, message):
        self.log_area.append(message)
        
    def test_single(self, script_name):
        if not os.path.exists(script_name):
            self.log(f"[ERROR] {script_name} not found")
            return
            
        tester = VersionTester(script_name)
        tester.log_signal.connect(self.log)
        tester.start()
        self.testers.append(tester)
        
    def test_all_versions(self):
        self.log("\n" + "=" * 60)
        self.log("Starting comprehensive test of all versions...")
        self.log("=" * 60)
        
        versions_to_test = [
            "../client/standalone/standalone_chat.py",
            "../client/realtime/chat_client.py",
            "../client/launcher/chat_launcher.py",
            "../kakaotalk_fixed.py",  # Legacy for compatibility
            "../kakaotalk_real_chat.py",  # Legacy for compatibility
        ]
        
        for version in versions_to_test:
            if os.path.exists(version):
                self.test_single(version)
                time.sleep(0.5)  # Small delay between tests
            else:
                self.log(f"[SKIP] {version} - File not found")
                
        self.log("\n" + "=" * 60)
        self.log("Test sequence initiated. Results will appear above.")
        
    def closeEvent(self, event):
        # Clean up any running testers
        for tester in self.testers:
            if tester.process and tester.process.poll() is None:
                tester.process.terminate()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Enable High DPI support
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    window = TestAllVersionsWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()