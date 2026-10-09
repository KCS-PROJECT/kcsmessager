# -*- coding: utf-8 -*-
"""
Image #7 대조 검사 — 표의 각 줄이 코드에 실제로 있는지(기호·파일) 확인하고, 그 줄의 테스트를 실행한다.

사용: python3 scripts/check_image7.py      (모두 통과하면 종료 코드 0)
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def src(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def has(path, *patterns):
    text = src(path)
    return all(re.search(p, text) for p in patterns)


def exists(*paths):
    return all(os.path.exists(os.path.join(ROOT, p)) for p in paths)


T = 'tests.test_kakao_v4.'
ROWS = [
    # (줄, 코드 증거 검사, 실행할 테스트)
    ('impeccable craft·extract', lambda: has('client/kakao/chat_room.py', r'class FailButton\(RoundGlyphButton\)')
     and has('client/kakao/theme.py', r'TYPE_SCALE = \{', r'RADII = \{', r'def button_qss'),
     [T + 'FailedMessageTest', T + 'DesignSystemTest']),
    ('shape', lambda: exists('claudedocs/design/09_shape_failed_messages.md'), []),
    ('adapt', lambda: has('client/kakao/chat_room.py', r'def _time_column_width', r'QBoxLayout\.TopToBottom',
                          r'self\.compact_header ='), [T + 'AdaptTest']),
    ('animate', lambda: has('client/kakao/voice.py', r'class PulseDot\(_PhaseWidget\)', r'class BusyBar\(_PhaseWidget\)')
     and has('client/kakao/chat_room.py', r'def announce'), [T + 'MotionTest']),
    ('audit', lambda: exists('claudedocs/design/08_impeccable_audit_and_fixes.md'), [T + 'AccessibilityTest']),
    ('bolder', lambda: has('client/kakao/chat_room.py', r'if i == 0:.*\n.*font-weight:700'), [T + 'SummaryStyleTest']),
    ('clarify', lambda: has('server/kakao/server.py', r'통화 카드에서 참여하기를 누르세요')
     and has('client/kakao/app.py', r'def install_korean_qt_translation'), [T + 'UxCopyTest']),
    ('colorize', lambda: has('client/kakao/chat_room.py', r'SUMMARY_TAGS = \{'),
     [T + 'SummaryStyleTest.test_tag_colors_meet_aa']),
    ('critique', lambda: exists('claudedocs/design/01_design_critique_v4.md'), []),
    ('delight', lambda: has('client/kakao/chat_room.py', r'self\.real_wave = True'),
     [T + 'V4ChatRoomUiTest.test_voice_record_send_and_play']),
    ('distill', lambda: not has('client/kakao/chats_tab.py', r'class OpenChatButton')
     and not has('client/kakao/chats_tab.py', r'def make_open_chat_icon'), []),
    ('layout', lambda: has('client/kakao/chat_room.py', r"raw\.startswith\('주요 키워드:'\)"), [T + 'SummaryStyleTest']),
    ('optimize', lambda: has('client/kakao/theme.py', r'def _available_families', r'def font_families')
     and exists('scripts/measure_startup.py'),
     [T + 'OptimizeTest']),
    ('overdrive', lambda: has('client/kakao/voice.py', r'class LiveWave\(QWidget\)'),
     [T + 'V4ChatRoomUiTest.test_voice_record_send_and_play']),
    ('polish', lambda: has('client/kakao/theme.py', r"'yellow': '#536ED4'"),
     [T + 'DesignSystemTest.test_button_variants_cover_all_states']),
    ('quieter', lambda: has('client/kakao/chat_room.py', r'def keyword_text_color', r'QPen\(line, 1\.0\)'),
     [T + 'SummaryStyleTest.test_keyword_chip_text_contrast']),
    ('typeset', lambda: has('client/kakao/theme.py', r'def fs\(', r'def size_of', r"'headline': 19", r"'numeral': 26"),
     [T + 'DesignSystemTest']),
    ('frontend-design', lambda: has('client/kakao/chat_room.py', r'class RoundGlyphButton', r'class Waveform'), []),
    ('simplify', lambda: exists('claudedocs/design/11_image7_checklist.md')
     and has('client/kakao/state.py', r'message_removed = pyqtSignal', r'def is_connected\(self\):\n\s+return self\.conn is not None and bool\(self\.conn\.is_connected\)')
     and has('client/kakao/voice.py', r'AudioEngine') and not has('client/kakao/voice.py', r'QAudioOutput|QAudioInput')
     and has('server/kakao/store.py', r'after_msg_id') and has('server/kakao/server.py', r"'done': part == len\(chunks\) - 1")
     and has('client/kakao/chats_tab.py', r'def _on_room_changed', r'def call_icon')
     and has('client/kakao/state.py', r'CALL_MODE_LABELS = \{', r'def org_text\(self, username, sep')
     and not any(has(f, r"\{'voice': '보이스톡'") for f in ('client/kakao/chat_room.py', 'client/kakao/call.py',
                                                           'client/kakao/feature_tour.py', 'client/kakao/chats_tab.py'))
     and not any(has(f, r"get\('company'\), \w+\.get\('department'\)") for f in (
         'client/kakao/chat_room.py', 'client/kakao/friends_tab.py', 'client/kakao/more_tab.py'))
     and has('server/kakao/rag.py', r'FATAL_LLM_ERRORS = '),
     [T + 'EfficiencyFollowupTest', T + 'V4ServerTest']),
    ('ui-ux-pro-max', lambda: has('client/kakao/main_window.py', r'안 읽은 메시지 \{count\}개'),
     [T + 'AccessibilityTest.test_badges_read_with_context_and_no_glyph_icons']),
    ('ui-styling', lambda: exists('web/tailwind.config.ts', 'web/components.json', 'web/src/components/ui/button.tsx',
                                  'web/src/components/ui/tabs.tsx', 'assets/design-tokens.css',
                                  'docs/design/kcs_talk_design_system_light.png')
     and has('web/tailwind.config.ts', r'tailwind_config_gen\.py') and has('web/package.json', r'"shadcn": "2\.3\.0"')
     and has('client/kakao/chat_room.py', r'def focus_compose', r'self\._opener'),
     [T + 'UiStylingPatternsTest', T + 'DesignTokenExportTest']),
    ('순서 shape→craft→animate→polish→audit→adapt', lambda: has('claudedocs/design/10_image7_workflow_run.md',
                                                              r'\| 1 \| \*\*shape\*\*', r'\| 6 \| \*\*adapt\*\*'), []),
]


def main():
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    failed = 0
    for name, check, tests in ROWS:
        ok_code = bool(check())
        ok_test = True
        if tests:
            r = subprocess.run([sys.executable, '-m', 'unittest', *tests], cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=600)
            ok_test = r.returncode == 0
        mark = '✓' if (ok_code and ok_test) else '✗'
        failed += mark == '✗'
        print(f"{mark} {name:<40} 코드 {'있음' if ok_code else '없음'} · 테스트 "
              f"{('통과 ' + str(len(tests)) + '개') if tests and ok_test else ('실패' if tests else '-')}")
    print(f'\n{len(ROWS) - failed}/{len(ROWS)} 줄 확인')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
