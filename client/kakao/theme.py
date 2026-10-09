# -*- coding: utf-8 -*-
"""
테마 - 카카오톡 PC 색상 팔레트(라이트/다크), 한글 폰트 체인, 공용 QSS
모든 위젯은 색상을 하드코딩하지 말고 theme.c('키')로 가져온다.
"""

from PyQt5.QtGui import QFont, QColor

FONT_FAMILIES = ['맑은 고딕', 'Malgun Gothic', 'Apple SD Gothic Neo',
                 'Nanum Gothic', 'Noto Sans CJK KR', 'Arial']

LIGHT = {
    'bg': '#FFFFFF',
    'bg_alt': '#F7F7F7',
    'bg_hover': '#F2F2F2',
    'bg_selected': '#EBEBEB',
    'chat_bg': '#BACEE0',          # 카카오톡 채팅방 배경
    'sidebar': '#ECECED',
    'sidebar_icon': '#A9A9AA',
    'sidebar_icon_active': '#1E1E1E',
    'text': '#191919',
    'text_sub': '#6B6B6B',
    'text_hint': '#6A6A6A',        # AA 4.5:1 이상 (흰 배경 5.3)
    'border': '#E5E5E5',
    'yellow': '#FEE500',           # 카카오 옐로
    'yellow_dark': '#F5D800',
    'bubble_mine': '#FEE500',
    'bubble_other': '#FFFFFF',
    'bubble_text': '#191919',
    'unread_num': '#E5B800',       # 안 읽은 사람 수 숫자
    'badge': '#D93025',            # 안 읽은 메시지 배지 (흰 글자 4.6:1)
    'danger_text': '#B3261E',      # 경고 글자(부재중·전송 실패) — 흰 배경·채팅 배경(#DCE3EE) 모두 4.5:1 이상
    'link': '#2E6FD8',
    'notice_bg': '#FFFFFF',
    'system_bg': 'rgba(28,36,64,0.56)',
    'system_text': '#FFFFFF',
    'date_chip_bg': 'rgba(28,36,64,0.56)',
    'mention': '#2E6FD8',
    'reaction_bg': '#FFFFFF',
    'calendar_today': '#FEE500',
    'calendar_sun': '#E64545',
    'calendar_sat': '#3C78D8',
    'input_bg': '#FFFFFF',
}

DARK = {
    'bg': '#1F1F1F',
    'bg_alt': '#262626',
    'bg_hover': '#2E2E2E',
    'bg_selected': '#383838',
    'chat_bg': '#2B2F33',
    'sidebar': '#151515',
    'sidebar_icon': '#6E6E6E',
    'sidebar_icon_active': '#F2F2F2',
    'text': '#EDEDED',
    'text_sub': '#A6A6A6',
    'text_hint': '#ABABAB',        # 다크 카드(#3A3D41) 위에서도 4.5:1
    'border': '#333333',
    'yellow': '#FEE500',
    'yellow_dark': '#F5D800',
    'bubble_mine': '#FEE500',
    'bubble_other': '#3A3D41',
    'bubble_text': '#EDEDED',
    'unread_num': '#FEE500',
    'badge': '#D93025',
    'danger_text': '#FF8A80',      # 다크 배경 위 경고 글자 4.5:1 이상
    'link': '#7AA7F0',
    'notice_bg': '#2E2E2E',
    'system_bg': 'rgba(255,255,255,0.12)',
    'system_text': '#DDDDDD',
    'date_chip_bg': 'rgba(255,255,255,0.10)',
    'mention': '#7AA7F0',
    'reaction_bg': '#3A3D41',
    'calendar_today': '#FEE500',
    'calendar_sun': '#FF7070',
    'calendar_sat': '#7AA7F0',
    'input_bg': '#2A2A2A',
}

# 간격 체계 (4px 단위). 묶음 안은 S/M, 묶음 사이는 L/XL, 화면 가장자리는 L(16)
SPACE = {'xxs': 2, 'xs': 4, 's': 8, 'm': 12, 'l': 16, 'xl': 24, 'xxl': 32}
GUTTER = 16      # 탭 화면 좌우 여백


def sp(name):
    return SPACE[name]


# 글자 단계 (px, 글자 크기 배율 적용 전). 새 코드는 숫자 대신 이름을 쓴다: theme.fs('meta')
TYPE_SCALE = {
    'micro': 10,     # 배지 숫자, 공감 선택 창 수
    'caption': 11,   # 시간, 보조 칩
    'meta': 12,      # 부제, 안내, 카드 보조 글자
    'body': 13,      # 말풍선 본문, 목록 미리보기
    'emphasis': 14,  # 목록 제목, 카드 제목
    'title': 15,     # 대화상자 제목
    'lead': 16,      # 섹션·카드 큰 제목
    'heading': 17,   # 대화상자·카드 큰 제목
    'headline': 19,  # 탭 제목 · 프로필 이름
    'display': 22,   # 로그인 · 통화 화면 큰 글자
    'numeral': 26,   # 큰 숫자 (녹음 시간 · 잠금 숫자판)
}
# 모서리 단계
RADII = {'xs': 4, 's': 6, 'm': 8, 'card': 12, 'bubble': 16, 'pill': 15}


def fs(name):
    """이름 있는 글자 단계 → 배율 적용 px"""
    return px(TYPE_SCALE[name])


def radius(name):
    return RADII[name]


# 버튼 변형 (shadcn/ui 원칙: 변형마다 기본·hover·pressed·focus·disabled 를 빠짐없이 같은 규칙으로)
BUTTON_VARIANTS = ('primary', 'secondary', 'outline', 'ghost', 'danger')


def button_qss(selector, variant='primary', size='meta', bold=None, pad='6px 8px', fam=''):
    """QPushButton 선택자 하나에 변형 규칙 전체(QSS)를 만든다"""
    if variant not in BUTTON_VARIANTS:
        raise ValueError(variant)
    bg, fg, border, hover, pressed = {
        'primary': (c('yellow'), c('on_accent'), c('yellow'), c('yellow_dark'), c('yellow_dark')),
        'secondary': (c('bg_alt'), c('text'), c('border'), c('bg_hover'), c('bg_selected')),
        'outline': ('transparent', c('text'), c('border'), c('bg_hover'), c('bg_selected')),
        'ghost': ('transparent', c('text_sub'), 'transparent', c('bg_hover'), c('bg_selected')),
        'danger': (c('badge'), '#FFFFFF', c('badge'), c('badge'), c('badge')),
    }[variant]
    weight = 'bold' if (bold if bold is not None else variant in ('primary', 'danger')) else 'normal'
    r = radius('s')
    return (f"QPushButton#{selector} {{ {fam} background: {bg}; color: {fg}; border: 1px solid {border};"
            f" border-radius: {r}px; padding: {pad}; font-size: {fs(size)}px; font-weight: {weight}; }}"
            f" QPushButton#{selector}:hover {{ background: {hover}; }}"
            f" QPushButton#{selector}:pressed {{ background: {pressed}; }}"
            f" QPushButton#{selector}:focus {{ border: 2px solid {c('yellow_dark') if variant != 'primary' else c('text')}; }}"
            f" QPushButton#{selector}:disabled {{ background: {c('bg_alt')}; color: {c('text_hint')};"
            f" border: 1px solid {c('border')}; }}")


# 강조색(브랜드) 오버레이 - 'kcs'(기본, 회사 CI 네이비) / 'kakao'(클래식 옐로)
# 'yellow*' 키 이름은 호환을 위해 유지하며 의미는 '주 강조색'이다.
BRAND_NAVY = '#2A386C'
LIGHT.update({'on_accent': '#191919', 'bubble_mine_text': '#191919', 'bubble_mine_sub': 'rgba(0,0,0,0.55)',
              'bubble_mine_line': 'rgba(0,0,0,0.12)', 'bubble_mine_link': '#1F4FB8', 'brand': BRAND_NAVY,
              'sidebar_badge_ring': '#ECECED', 'sidebar_active_bg': 'rgba(0,0,0,0.06)',
              'sidebar_icon_hover': '#6B6B6B', 'sidebar_logo': BRAND_NAVY,
              'header_panel': 'rgba(255,255,255,0.82)', 'header_line': 'rgba(0,0,0,0.07)'})
DARK.update({'on_accent': '#191919', 'bubble_mine_text': '#191919', 'bubble_mine_sub': 'rgba(0,0,0,0.55)',
             'bubble_mine_line': 'rgba(0,0,0,0.12)', 'bubble_mine_link': '#1F4FB8', 'brand': '#8FA3E8',
             'sidebar_badge_ring': '#151515', 'sidebar_active_bg': 'rgba(255,255,255,0.08)',
             'sidebar_icon_hover': '#A6A6A6', 'sidebar_logo': '#8FA3E8',
             'header_panel': 'rgba(31,31,31,0.86)', 'header_line': 'rgba(255,255,255,0.07)'})

ACCENTS = {
    'kakao': {'light': {}, 'dark': {}},
    'kcs': {
        'light': {
            'yellow': BRAND_NAVY, 'yellow_dark': '#1E2955', 'on_accent': '#FFFFFF',
            'bubble_mine': '#33478F', 'bubble_mine_text': '#FFFFFF', 'bubble_mine_sub': 'rgba(255,255,255,0.72)',
            'bubble_mine_line': 'rgba(255,255,255,0.28)', 'bubble_mine_link': '#C9D6FF',
            'unread_num': '#3F5BD9', 'calendar_today': BRAND_NAVY, 'chat_bg': '#DCE3EE',
            'sidebar': BRAND_NAVY, 'sidebar_icon': '#C3CBE6', 'sidebar_icon_active': '#FFFFFF',
            'sidebar_badge_ring': BRAND_NAVY, 'link': '#2F55D4', 'mention': '#2F55D4',
            'sidebar_active_bg': 'rgba(255,255,255,0.14)', 'sidebar_icon_hover': '#D3DAF0', 'sidebar_logo': '#FFFFFF',
        },
        'dark': {
            'yellow': '#536ED4', 'yellow_dark': '#4A62C2', 'on_accent': '#FFFFFF',
            'bubble_mine': '#3A4E9C', 'bubble_mine_text': '#FFFFFF', 'bubble_mine_sub': 'rgba(255,255,255,0.70)',
            'bubble_mine_line': 'rgba(255,255,255,0.25)', 'bubble_mine_link': '#C9D6FF',
            'unread_num': '#8FA3E8', 'calendar_today': '#536ED4', 'chat_bg': '#1D2130',
            'sidebar': '#141A30', 'sidebar_icon': '#9AA6CC', 'sidebar_icon_active': '#FFFFFF',
            'sidebar_badge_ring': '#141A30',
            'sidebar_active_bg': 'rgba(255,255,255,0.10)', 'sidebar_icon_hover': '#B4BEDF', 'sidebar_logo': '#FFFFFF',
        },
    },
}
BRANDS = {'kcs': 'KCS 블루', 'kakao': '옐로 (사용 안 함)'}   # 앱은 KCS 블루로 고정, 'kakao'는 내부 호환용

# 말풍선 꾸미기 (명세 §8.11) - 내 말풍선 배경/글자색/모서리. None 이면 현재 테마 값 사용
BUBBLE_STYLES = {
    'basic': {'label': '기본', 'bg': None, 'fg': None, 'radius': 13},
    'round': {'label': '동글동글', 'bg': None, 'fg': None, 'radius': 20},
    'square': {'label': '반듯하게', 'bg': None, 'fg': None, 'radius': 5},
    'yellow': {'label': '옐로', 'bg': '#FEE500', 'fg': '#191919', 'radius': 13},
    'pastel': {'label': '파스텔 핑크', 'bg': '#FFD6E0', 'fg': '#3B2730', 'radius': 16},
    'mint': {'label': '민트', 'bg': '#C9F2E4', 'fg': '#163B30', 'radius': 16},
    'mono': {'label': '모노', 'bg': '#3C3C3C', 'fg': '#FFFFFF', 'radius': 10},
}


def bubble_style(name):
    """말풍선 스타일 → {'bg', 'fg', 'radius', 'label'} (bg/fg 는 테마 값으로 채움)"""
    st = dict(BUBBLE_STYLES.get(name or 'basic') or BUBBLE_STYLES['basic'])
    st['bg'] = st['bg'] or c('bubble_mine')
    st['fg'] = st['fg'] or c('bubble_mine_text')
    return st


EVENT_COLORS = ['#2A386C', '#FEE500', '#FF7A59', '#4CB6F2', '#6DCC7B', '#B184F2', '#F27AB0']

_state = {'dark': False, 'scale': 1.0, 'brand': 'kcs', 'reduce_motion': False}


def set_brand(name):
    _state['brand'] = name if name in ACCENTS else 'kcs'


def brand():
    return _state['brand']


def set_dark(dark):
    _state['dark'] = bool(dark)


def is_dark():
    return _state['dark']


def set_reduce_motion(on):
    """동작 줄이기: 켜면 깜빡임·움직이는 표시를 멈추고 정지 상태로 보여 준다"""
    _state['reduce_motion'] = bool(on)


def reduce_motion():
    return _state['reduce_motion']


def set_font_scale(scale):
    _state['scale'] = max(0.8, min(2.0, float(scale)))   # 200% 까지 (WCAG 1.4.4 글자 크기 조정)


def font_scale():
    return _state['scale']


def c(key):
    """현재 테마(밝기 + 브랜드 강조색)의 색상 문자열"""
    overlay = ACCENTS[_state['brand']]['dark' if _state['dark'] else 'light']
    if key in overlay:
        return overlay[key]
    return (DARK if _state['dark'] else LIGHT)[key]


def qc(key):
    """현재 테마의 QColor ('rgba(...)' 문자열도 처리)"""
    value = c(key)
    if value.startswith('rgba'):
        r, g, b, a = [x.strip() for x in value[5:-1].split(',')]
        color = QColor(int(r), int(g), int(b))
        color.setAlphaF(float(a))
        return color
    return QColor(value)


def px(size):
    """글자 크기 배율을 적용한 픽셀 크기"""
    return max(8, int(round(size * _state['scale'])))


_available = None


def _available_families():
    """이 PC에 설치된 글꼴 이름 집합 (한 번만 조회). 앱이 없으면 None"""
    global _available
    if _available is None:
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QFontDatabase
        if QApplication.instance() is None:
            return None
        _available = set(QFontDatabase().families())
    return _available


def installed(names):
    """names 중 설치된 글꼴만, 순서 유지 (앱이 없으면 그대로).
    없는 글꼴('맑은 고딕' on macOS 등)을 넘기면 Qt 가 별칭 표를 만드느라 첫 그리기가 약 130ms 늦어진다"""
    available = _available_families()
    return list(names) if available is None else [n for n in names if n in available]


def font_families():
    """FONT_FAMILIES 중 설치된 것 (하나도 없으면 원래 목록)"""
    return installed(FONT_FAMILIES) or list(FONT_FAMILIES)


def size_of(size):
    """글자 크기: 단계 이름('meta') 또는 px 숫자 → px 숫자 (배율 적용 전)"""
    return TYPE_SCALE[size] if isinstance(size, str) else size


def font(size='body', bold=False):
    """size: 단계 이름(권장, 예 'meta') 또는 단계에 없는 특수 크기 숫자"""
    f = QFont()
    f.setFamilies(font_families())
    f.setPixelSize(px(size_of(size)))
    f.setBold(bold)
    f.setStyleHint(QFont.SansSerif)
    return f


def font_css():
    return 'font-family: ' + ', '.join(f'"{name}"' for name in font_families()) + ';'


def scrollbar_qss():
    return f"""
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: rgba(128,128,128,0.45); border-radius: 4px; min-height: 30px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0; }}
        QScrollBar::handle:horizontal {{ background: rgba(128,128,128,0.45); border-radius: 4px; min-width: 30px; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """


def base_qss():
    """앱 전역 스타일시트(QApplication.setStyleSheet용)"""
    return f"""
        QWidget {{ {font_css()} font-size: {fs('body')}px; color: {c('text')}; }}
        QMainWindow, QDialog {{ background: {c('bg')}; }}
        QLineEdit, QTextEdit, QPlainTextEdit, QDateTimeEdit, QDateEdit, QTimeEdit, QSpinBox, QComboBox {{
            background: {c('input_bg')}; border: 1px solid {c('border')}; border-radius: 6px;
            padding: 6px 8px; selection-background-color: {c('yellow')}; selection-color: {c('on_accent')};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {c('yellow_dark')}; }}
        QPushButton {{
            background: {c('bg_alt')}; border: 1px solid {c('border')}; border-radius: 6px;
            padding: 7px 14px;
        }}
        QPushButton:hover {{ background: {c('bg_hover')}; }}
        QPushButton:focus {{ border: 2px solid {c('yellow_dark')}; }}
        QPushButton:disabled {{ color: {c('text_hint')}; }}
        QPushButton[primary="true"] {{ background: {c('yellow')}; border: none; color: {c('on_accent')}; font-weight: bold; }}
        QPushButton[primary="true"]:hover {{ background: {c('yellow_dark')}; }}
        QPushButton[flat="true"] {{ background: transparent; border: none; padding: 4px; border-radius: 8px; }}
        QPushButton[flat="true"]:hover {{ background: {c('bg_hover')}; }}
        QPushButton[flat="true"]:pressed {{ background: {c('bg_selected')}; }}
        QPushButton[flat="true"]:focus {{ border: 2px solid {c('yellow_dark')}; }}
        QMenu {{ background: {c('bg')}; border: 1px solid {c('border')}; padding: 4px; }}
        QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
        QMenu::item:selected {{ background: {c('bg_hover')}; color: {c('text')}; }}
        QListWidget {{ background: {c('bg')}; border: none; outline: 0; }}
        QListWidget::item {{ border: none; }}
        QListWidget::item:selected {{ background: {c('bg_selected')}; }}
        QListWidget::item:hover {{ background: {c('bg_hover')}; }}
        QToolTip {{ background: {c('bg')}; color: {c('text')}; border: 1px solid {c('border')}; }}
        QCheckBox, QRadioButton {{ spacing: 6px; }}
        {scrollbar_qss()}
    """
