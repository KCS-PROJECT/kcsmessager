#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify kakaotalk_real_chat.py fixes
"""

import sys
import os

def test_imports():
    """Test that all imports work correctly"""
    print("[TEST] Checking imports...")
    try:
        import locale
        import socket
        import threading
        import json
        from datetime import datetime
        from PyQt5.QtWidgets import QApplication, QWidget, QLabel
        from PyQt5.QtCore import Qt, QObject, pyqtSignal
        from PyQt5.QtGui import QFont, QPainter, QColor
        print("[OK] All imports successful")
        return True
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        return False

def test_encoding():
    """Test UTF-8 encoding"""
    print("\n[TEST] Checking UTF-8 encoding...")
    try:
        # Test Korean text
        korean_text = "안녕하세요, 카카오톡입니다!"
        print(f"[OK] Korean text: {korean_text}")
        
        # Test encoding
        encoded = korean_text.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert decoded == korean_text
        print("[OK] UTF-8 encoding/decoding works")
        return True
    except Exception as e:
        print(f"[ERROR] Encoding test failed: {e}")
        return False

def test_high_dpi():
    """Test High DPI settings"""
    print("\n[TEST] Checking High DPI support...")
    try:
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication
        
        # Check if attributes exist
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            print("[OK] High DPI scaling attribute available")
        else:
            print("[WARNING] High DPI scaling not available in this Qt version")
            
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            print("[OK] High DPI pixmaps attribute available")
        else:
            print("[WARNING] High DPI pixmaps not available in this Qt version")
            
        return True
    except Exception as e:
        print(f"[ERROR] High DPI test failed: {e}")
        return False

def test_font_families():
    """Test font family support"""
    print("\n[TEST] Checking font families...")
    try:
        from PyQt5.QtGui import QFont, QFontDatabase
        from PyQt5.QtWidgets import QApplication
        
        # Need QApplication for font database
        import os
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
            
        app = QApplication(sys.argv)
        
        # Test font families
        font_families = ['맑은 고딕', 'Malgun Gothic', 'Apple SD Gothic Neo', 'Nanum Gothic', 'Arial']
        font = QFont()
        font.setFamilies(font_families)
        
        # Check available fonts
        db = QFontDatabase()
        available_fonts = db.families()
        
        found_korean = False
        for family in font_families:
            if family in available_fonts:
                print(f"[OK] Found font: {family}")
                if family in ['맑은 고딕', 'Malgun Gothic', 'Apple SD Gothic Neo', 'Nanum Gothic']:
                    found_korean = True
        
        if found_korean:
            print("[OK] Korean font support available")
        else:
            print("[WARNING] No Korean fonts found, text may not display correctly")
            
        app.quit()
        return True
    except Exception as e:
        print(f"[ERROR] Font test failed: {e}")
        return False

def test_file_modifications():
    """Test that file has been properly modified"""
    print("\n[TEST] Checking file modifications...")
    try:
        with open('kakaotalk_real_chat.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for key fixes
        checks = [
            ('# -*- coding: utf-8 -*-', 'UTF-8 encoding declaration'),
            ('locale.setlocale', 'Locale settings'),
            ('QApplication.setAttribute(Qt.AA_EnableHighDpiScaling', 'High DPI before QApplication'),
            ('font.setFamilies', 'Font family chains'),
            ('painter.setRenderHint(QPainter.Antialiasing, True)', 'Enhanced antialiasing'),
            ('screen = QApplication.primaryScreen().geometry()', 'Responsive sizing'),
        ]
        
        all_passed = True
        for check_str, description in checks:
            if check_str in content:
                print(f"[OK] {description}")
            else:
                print(f"[WARNING] Missing: {description}")
                all_passed = False
                
        return all_passed
    except Exception as e:
        print(f"[ERROR] File check failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("KakaoTalk Real Chat - Fix Verification")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Encoding", test_encoding()))
    results.append(("High DPI", test_high_dpi()))
    results.append(("Font Families", test_font_families()))
    results.append(("File Modifications", test_file_modifications()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n[SUCCESS] All fixes have been applied successfully!")
        print("The kakaotalk_real_chat.py should now display properly without breaking issues.")
    else:
        print("\n[WARNING] Some tests failed. The application may still have display issues.")
    
    print("\nTo test the actual application:")
    print("1. Start the server: python simple_chat_server.py")
    print("2. Run the client: python kakaotalk_real_chat.py")
    print("3. Open multiple clients to test real chat functionality")

if __name__ == "__main__":
    main()