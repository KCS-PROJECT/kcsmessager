#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KakaoTalk Real Chat Launcher - Redirect to Unified Launcher
통합 런처로 리다이렉트합니다
"""

import sys
import os
import subprocess

def main():
    """메인 런처 실행 - 통합 런처로 리다이렉트"""
    try:
        # 현재 디렉토리에서 통합 런처 찾기
        current_dir = os.path.dirname(__file__)
        unified_launcher = os.path.join(current_dir, "kakaotalk_launcher.py")
        
        if os.path.exists(unified_launcher):
            print("🚀 통합 런처로 리다이렉트합니다...")
            print(f"📍 위치: {unified_launcher}")
            
            # 통합 런처 실행
            try:
                # 같은 Python 인터프리터로 실행
                result = subprocess.run([sys.executable, unified_launcher], 
                                      cwd=current_dir)
                return result.returncode
            except KeyboardInterrupt:
                print("\n👋 사용자가 런처를 종료했습니다.")
                return 0
            except Exception as e:
                print(f"❌ 런처 실행 중 오류: {e}")
                return 1
        else:
            print("❌ 통합 런처 파일을 찾을 수 없습니다.")
            print("📋 필요한 파일: kakaotalk_launcher.py")
            return 1
                
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())