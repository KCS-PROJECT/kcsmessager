# -*- coding: utf-8 -*-
"""
KCS Talk 디자인 시스템 보드 + 토큰 내보내기 (ui-styling 스킬의 Canvas · 테마 계층 적용)

출력:
  docs/design/kcs_talk_design_system_light.png / _dark.png
      - Canvas 원칙: 색 면 · 기하 리듬 · 최소 글자. client/kakao/theme.py 토큰과 실제 위젯을 그대로 캡처
  assets/design-tokens.json   - 라이트/다크 토큰 + 글자·간격·모서리 단계
  assets/design-tokens.css    - shadcn/ui 형식 CSS 변수 (:root / .dark, HSL) → 웹 클라이언트를 만들면 그대로 사용

사용: python scripts/make_design_board.py
"""

import colorsys
import json
import os
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('KCS_MESSENGER_HOME', tempfile.mkdtemp(prefix='kcs_board_'))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PyQt5.QtCore import Qt, QRectF, QPointF  # noqa: E402
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QRegion  # noqa: E402
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget, QHBoxLayout  # noqa: E402

W, H = 1600, 1000
M = 72                     # 바깥 여백
SWATCHES = [('yellow', '주 강조'), ('yellow_dark', '강조 진하게'), ('on_accent', '강조 위 글자'),
            ('bg', '배경'), ('bg_alt', '보조 배경'), ('chat_bg', '채팅 배경'), ('text', '글자'),
            ('text_sub', '보조 글자'), ('text_hint', '안내 글자'), ('border', '선'),
            ('badge', '배지'), ('danger_text', '경고 글자')]
# shadcn/ui 의미 이름 ← KCS 토큰
SHADCN = {'background': 'bg', 'foreground': 'text', 'card': 'bubble_other', 'card-foreground': 'bubble_text',
          'primary': 'yellow', 'primary-foreground': 'on_accent', 'secondary': 'bg_alt', 'secondary-foreground': 'text',
          'muted': 'bg_alt', 'muted-foreground': 'text_sub', 'accent': 'bg_hover', 'accent-foreground': 'text',
          'destructive': 'badge', 'destructive-foreground': '#FFFFFF', 'border': 'border', 'input': 'border',
          'ring': 'yellow_dark'}


def hsl(color):
    q = QColor(color)
    h, l, s = colorsys.rgb_to_hls(q.redF(), q.greenF(), q.blueF())
    return f'{h * 360:.1f} {s * 100:.1f}% {l * 100:.1f}%'


def solid(theme, key):
    """rgba(...) 토큰은 배경 위에 합성한 불투명 색으로"""
    value = key if key.startswith('#') else theme.c(key)
    q = QColor(value)
    if value.startswith('rgba'):
        parts = value[value.index('(') + 1:-1].split(',')
        r, g, b, a = (float(x) for x in parts)
        base = QColor(theme.c('bg'))
        q = QColor(int(r * a + base.red() * (1 - a)), int(g * a + base.green() * (1 - a)),
                   int(b * a + base.blue() * (1 - a)))
    return q.name()


def export_tokens(theme):
    from client.kakao.chat_room import SUMMARY_TAGS
    data = {'name': 'KCS Talk', 'source': 'client/kakao/theme.py', 'summary_tags': SUMMARY_TAGS,
            'type_scale': dict(theme.TYPE_SCALE), 'space': dict(theme.SPACE), 'radius': dict(theme.RADII),
            'light': {}, 'dark': {}, 'shadcn': {'light': {}, 'dark': {}}}
    css = ['/* KCS Talk 디자인 토큰 — scripts/make_design_board.py 가 theme.py 에서 생성 (shadcn/ui 형식) */',
           '@layer base {']
    for mode in ('light', 'dark'):
        theme.set_dark(mode == 'dark')
        data[mode] = {k: solid(theme, k) for k, _ in SWATCHES}
        data['shadcn'][mode] = {name: solid(theme, key) for name, key in SHADCN.items()}
        css.append('  :root {' if mode == 'light' else '  .dark {')
        css += [f'    --{name}: {hsl(value)};' for name, value in data['shadcn'][mode].items()]
        if mode == 'light':
            css.append(f"    --radius: {theme.radius('card') / 16:.2f}rem;")
        css.append('  }')
    css.append('}')
    theme.set_dark(False)
    os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
    with open(os.path.join(ROOT, 'assets', 'design-tokens.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open(os.path.join(ROOT, 'assets', 'design-tokens.css'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(css) + '\n')
    return data


def capture(widget):
    """배경 없이 위젯과 자식만 그린다 (둥근 모서리 바깥이 투명하게)"""
    from PyQt5.QtWidgets import QWidget as _W
    img = QImage(widget.size(), QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    widget.render(p, QPointF(0, 0).toPoint(), QRegion(widget.rect()), _W.RenderFlags(_W.DrawChildren))
    p.end()
    return img


def grab_widget(widget, width=None):
    widget.ensurePolished()
    widget.adjustSize()
    if width:
        widget.setFixedWidth(width)
    widget.show()
    for _ in range(4):
        QApplication.processEvents()
    return capture(widget)


def specimens(theme):
    """실제 부품을 캡처: 버튼 변형 5종, 음성 말풍선, 연락처 카드, 전송 실패, 요약 태그"""
    from tests.kakao_fakes import make_demo_state
    from client.kakao.chat_room import ChatRoomWindow, summary_html
    from PyQt5.QtWidgets import QTextEdit
    out = {}
    row = QWidget()
    row.setStyleSheet(''.join(theme.button_qss(f'b_{v}', v) for v in theme.BUTTON_VARIANTS)
                      + f"QWidget {{ background: {theme.c('bg')}; }}")
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(12)
    for v, label in zip(theme.BUTTON_VARIANTS, ('1:1 채팅', '프로필 보기', '취소', '더보기', '삭제')):
        b = QPushButton(label)
        b.setObjectName(f'b_{v}')
        h.addWidget(b)
    out['buttons'] = grab_widget(row)
    state, conn = make_demo_state()
    win = ChatRoomWindow(state, 'r1')
    win.resize(420, 700)
    win.show()
    now = '2026-10-09T09:30:00'
    base = dict(room_id='r1', timestamp=now, reactions={}, mentions=[], deleted=False)
    conn.push('msg_new', message=dict(base, msg_id=901, sender='김철수', kind='contact', content='박민수'))
    conn.push('msg_new', message=dict(base, msg_id=902, sender='홍길동', kind='voice', content='12',
                                      attachment={'attachment_id': 1, 'name': 'v', 'mime': 'audio/wav', 'size': 1}))
    for _ in range(10):
        QApplication.processEvents()
    win._relayout_rows()
    out['contact'] = capture(win.rows[901].card)
    out['voice'] = capture(win.rows[902].card)
    conn.is_connected = False
    conn.send = lambda *a, **k: None
    state.send_text('r1', '보내지 못한 메시지')
    for _ in range(10):
        QApplication.processEvents()
    fail_row = win.rows[state.failed_messages('r1')[0]['msg_id']]
    out['failed'] = capture(fail_row)
    tags = QTextEdit()
    tags.setFrameShape(0)
    tags.setStyleSheet(f"background: {theme.c('bg')};")
    tags.setHtml(summary_html('대화 요약\n• [결정] 출시는 금요일\n• [요청] 자료 공유\n• [일정] 내일 10시 회의\n• [질문] 회의실은?'))
    tags.setFixedSize(360, 190)
    out['summary'] = grab_widget(tags)
    win.close()
    return out


def draw_board(theme, mode, path):
    from PyQt5.QtGui import QFont
    theme.set_dark(mode == 'dark')
    c = theme.c
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(c('bg')))
    spec = specimens(theme)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)

    def text(x, y, s, size, color, weight=QFont.Normal):
        f = theme.font(size)
        f.setPixelSize(size)
        f.setWeight(weight)
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(QPointF(x, y), s)

    # 머리: 브랜드 띠 + 이름 (글자는 최소)
    p.fillRect(QRectF(0, 0, 12, H), QColor(c('yellow')))
    text(M, M + 8, 'KCS Talk', 44, c('text'), QFont.Light)
    text(M, M + 40, 'design system · ' + ('light' if mode == 'light' else 'dark'), 15, c('text_sub'))

    # 1) 색 면: 12칸 격자 (큰 색 면 + 아주 작은 이름)
    gx, gy, cw, ch, gap = M, 170, 108, 108, 12
    for i, (key, label) in enumerate(SWATCHES):
        x = gx + (i % 6) * (cw + gap)
        y = gy + (i // 6) * (ch + 34 + gap)
        p.setPen(QPen(QColor(c('border')), 1))
        p.setBrush(QColor(solid(theme, key)))
        p.drawRoundedRect(QRectF(x, y, cw, ch), theme.radius('card'), theme.radius('card'))
        text(x, y + ch + 18, label, 12, c('text_sub'))
        text(x, y + ch + 32, solid(theme, key).upper(), 11, c('text_hint'))

    # 2) 글자 단계: 사다리
    tx, ty = M + 6 * (cw + gap) + 48, 170
    text(tx, ty - 14, 'type', 12, c('text_hint'))
    y = ty + 8
    for name, size in theme.TYPE_SCALE.items():
        y += size + 14
        text(tx, y, '가나다 Aa', size, c('text'), QFont.Medium if size >= 15 else QFont.Normal)
        text(tx + 250, y, f'{name} {size}', 11, c('text_hint'))

    # 3) 모서리·간격 리듬
    rx, ry = M, 500
    text(rx, ry - 14, 'radius · space', 12, c('text_hint'))
    x = rx
    for name, r in theme.RADII.items():
        p.setPen(QPen(QColor(c('yellow')), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(x, ry, 64, 64), r, r)
        text(x, ry + 84, f'{name} {r}', 11, c('text_hint'))
        x += 88
    x += 24
    for name, s in theme.SPACE.items():
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(c('yellow')))
        p.drawRect(QRectF(x, ry + 64 - s * 2, 14, s * 2))
        text(x - 2, ry + 84, str(s), 11, c('text_hint'))
        x += 30

    # 4) 실제 부품
    sx, sy = M, 640
    text(sx, sy - 14, 'components', 12, c('text_hint'))
    p.drawImage(QPointF(sx, sy), spec['buttons'])
    p.drawImage(QPointF(sx, sy + 70), spec['contact'])
    p.drawImage(QPointF(sx + 270, sy + 70), spec['voice'])
    p.drawImage(QPointF(sx + 270, sy + 140), spec['failed'].scaled(int(spec['failed'].width() * 0.8),
                                                                    int(spec['failed'].height() * 0.8),
                                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))
    p.drawImage(QPointF(sx + 900, sy), spec['summary'])
    p.end()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    theme.set_dark(False)


def main():
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841 (살아 있어야 그릴 수 있다)
    from client.kakao import theme
    from client.kakao.main_window import apply_app_theme
    apply_app_theme(None)
    data = export_tokens(theme)
    print(f"토큰 → assets/design-tokens.json, assets/design-tokens.css (shadcn 변수 {len(data['shadcn']['light'])}개)")
    for mode in ('light', 'dark'):
        path = os.path.join(ROOT, 'docs', 'design', f'kcs_talk_design_system_{mode}.png')
        draw_board(theme, mode, path)
        print(f'보드 → {os.path.relpath(path, ROOT)}')


if __name__ == '__main__':
    main()
