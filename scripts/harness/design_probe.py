# -*- coding: utf-8 -*-
"""
디자인 품질 측정 도구 (품질 하네스 11번 영역에서 사용, 단독 실행 가능)

- contrast_failures(): 테마 토큰 글자/배경 쌍의 WCAG 명암비 (라이트·다크 × 브랜드)
- widget_audit(root): 보이는 위젯 트리에서 접근성 이름 없는 아이콘 버튼 · 24px 미만 클릭 영역 · 잘린 글자
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractButton, QLabel, QWidget

# (글자 토큰, 배경 토큰, 최소 명암비) — 본문 4.5, 보조·굵은 짧은 숫자 3.0 (WCAG 1.4.3 / 1.4.11)
CONTRAST_PAIRS = [
    ('text', 'bg', 4.5), ('text', 'bg_alt', 4.5), ('text_sub', 'bg', 4.5), ('text_sub', 'bg_alt', 4.5),
    ('text_hint', 'bg', 4.5), ('on_accent', 'yellow', 4.5), ('bubble_mine_text', 'bubble_mine', 4.5),
    ('bubble_text', 'bubble_other', 4.5), ('link', 'bg', 4.5), ('link', 'bg_alt', 4.5),
    ('mention', 'bubble_other', 4.5), ('danger_text', 'bg', 4.5), ('on_badge', 'badge', 4.5),
    ('unread_num', 'chat_bg', 3.0), ('text', 'chat_bg', 4.5), ('text', 'input_bg', 4.5),
]


def _rgb(value):
    v = str(value).strip()
    if not v.startswith('#') or len(v) != 7:
        return None
    return tuple(int(v[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _lum(rgb):
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    a, b = _rgb(fg), _rgb(bg)
    if a is None or b is None:
        return None
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_failures():
    """[(모드, 글자, 배경, 비율, 기준)] — 라이트/다크 × 앱이 쓰는 브랜드 테마"""
    from client.kakao import theme
    old_dark, old_brand = theme.is_dark(), theme.brand()
    bad = []
    try:
        for brand in ('kcs',):
            theme.set_brand(brand)
            for dark in (False, True):
                theme.set_dark(dark)
                for fg, bg, need in CONTRAST_PAIRS:
                    ratio = contrast(theme.c(fg), theme.c(bg))
                    if ratio is not None and ratio + 1e-6 < need:
                        bad.append((f"{brand}/{'다크' if dark else '라이트'}", fg, bg, round(ratio, 2), need))
    finally:
        theme.set_brand(old_brand)
        theme.set_dark(old_dark)
    return bad


def _visible(w):
    return w.isVisible() and w.width() > 0 and w.height() > 0


def _widgets(root):
    out = [root] if isinstance(root, QWidget) else []
    out += root.findChildren(QWidget)
    return [w for w in out if _visible(w)]


def widget_audit(root, min_target=24):
    """보이는 위젯 검사 → {'unnamed': [...], 'small': [...], 'clipped': [...]} (각 항목은 설명 문자열)"""
    unnamed, small, clipped = [], [], []
    for w in _widgets(root):
        cls = type(w).__name__
        if isinstance(w, QAbstractButton):
            text = (w.text() or '').strip() if hasattr(w, 'text') else ''
            if not text and not (w.accessibleName() or w.toolTip()):
                unnamed.append(f'{cls}#{w.objectName() or "-"}')
            if w.isEnabled() and w.focusPolicy() != Qt.NoFocus and (w.width() < min_target or w.height() < min_target) \
                    and not text:
                small.append(f'{cls}#{w.objectName() or "-"} {w.width()}x{w.height()}')
        elif isinstance(w, QLabel) and not w.wordWrap() and w.textFormat() != Qt.RichText:
            text = w.text()
            if not text or '<' in text or w.pixmap() is not None and not w.pixmap().isNull():
                continue
            if type(w).__name__ in ('ElidedLabel',):   # 일부러 말줄임하는 라벨
                continue
            need = max(w.fontMetrics().horizontalAdvance(line) for line in text.split('\n'))
            margins = w.contentsMargins()
            avail = w.width() - margins.left() - margins.right() - 2 * w.margin()
            if need > avail + 2:
                clipped.append(f'{cls}#{w.objectName() or "-"} "{text[:24]}" {need}>{avail}')
    return {'unnamed': unnamed, 'small': small, 'clipped': clipped}


DIALOG_MODULES = ('event_dialog', 'chat_room', 'chat_export', 'drawer', 'more_tab', 'chats_tab', 'main_window',
                  'feature_tour', 'dnd', 'friends_tab', 'thread_view', 'org_tab', 'logout_dialog', 'story', 'voice',
                  'wallpaper', 'admin')


def iter_dialogs(state, room_win):
    """앱의 대화상자를 하나씩 만들어 돌려준다 (흔한 생성자 모양을 차례로 시도, 못 만들면 건너뜀)"""
    import importlib
    import inspect
    from PyQt5.QtWidgets import QDialog
    for mname in DIALOG_MODULES:
        mod = importlib.import_module('client.kakao.' + mname)
        for name, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ != mod.__name__ or not issubclass(cls, QDialog) or name.startswith('_'):
                continue
            other = next((u for u in state.users if u != state.me), state.me)
            for args in ((state, other), (room_win,), (state, state.settings, room_win), (state, room_win),
                         (state.settings, room_win), (state, room_win.room_id, room_win), (room_win, 2), (state,)):
                try:
                    dlg = cls(*args)
                except Exception:
                    continue
                yield name, dlg
                break
