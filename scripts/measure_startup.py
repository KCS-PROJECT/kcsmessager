# -*- coding: utf-8 -*-
"""
메인 창 첫 화면 시간 측정 (impeccable optimize 근거를 다시 재현).

  python3 scripts/measure_startup.py            # 지금 (설치된 글꼴만 체인에)
  python3 scripts/measure_startup.py --legacy   # 예전 (없는 글꼴 '맑은 고딕'까지 체인에 → Qt 별칭 표 생성)

각 실행은 새 프로세스에서 한 번 잰다 (글꼴 캐시는 프로세스마다 처음부터). --runs 로 반복 횟수.
"""
import argparse
import os
import statistics
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ONE_RUN = r'''
import os, sys, time, tempfile
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['KCS_MESSENGER_HOME'] = tempfile.mkdtemp()
sys.path.insert(0, ROOT)
from PyQt5.QtWidgets import QApplication
app = QApplication([])
from client.kakao import theme
if LEGACY:
    theme.font_families = lambda: list(theme.FONT_FAMILIES)
    theme.installed = lambda names: list(names)
from tests.kakao_fakes import make_demo_state
from client.kakao.main_window import MainWindow, apply_app_theme
t = time.perf_counter()
st, c = make_demo_state(); apply_app_theme(st.settings)
w = MainWindow(st, st.settings); w.show()
for _ in range(5):
    app.processEvents()
print(round(1000 * (time.perf_counter() - t)))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legacy', action='store_true')
    ap.add_argument('--runs', type=int, default=5)
    args = ap.parse_args()
    code = f'ROOT = {ROOT!r}\nLEGACY = {args.legacy}\n' + ONE_RUN
    times = []
    for _ in range(args.runs):
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=120)
        times.append(int(out.stdout.strip().splitlines()[-1]))
    label = '예전(없는 글꼴 포함)' if args.legacy else '지금(설치된 글꼴만)'
    print(f'{label}: 중앙값 {statistics.median(times)}ms  ({", ".join(map(str, times))})')


if __name__ == '__main__':
    main()
