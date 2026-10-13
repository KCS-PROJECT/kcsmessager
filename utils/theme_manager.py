# -*- coding: utf-8 -*-
"""
Theme Manager for KCS Messenger
Manages light/dark mode themes with dynamic color schemes
"""

from PyQt5.QtCore import QObject, pyqtSignal


class ThemeManager(QObject):
    """
    Singleton class for managing application themes.

    Features:
    - Light and dark mode support
    - Dynamic color scheme generation
    - Signal-based theme change notification
    - Stylesheet generation for all UI components
    """

    theme_changed = pyqtSignal(str)  # Emits 'light' or 'dark'

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        super().__init__()
        self._initialized = True
        self.current_theme = 'light'  # Default theme

        # Light mode color scheme
        self.light_colors = {
            # Background colors
            'bg_primary': '#FFFFFF',
            'bg_secondary': '#F8F8F8',
            'bg_tertiary': '#FAFAFA',
            'bg_hover': '#F5F5F5',
            'bg_selected': '#E8E8E8',
            'bg_chat': '#ABC1D1',

            # Text colors
            'text_primary': '#333333',
            'text_secondary': '#666666',
            'text_tertiary': '#999999',
            'text_inverse': '#FFFFFF',

            # Border colors
            'border_light': '#F0F0F0',
            'border_medium': '#E0E0E0',
            'border_dark': '#CCCCCC',

            # Accent colors
            'accent_primary': '#FFE400',  # KakaoTalk Yellow
            'accent_secondary': '#4A90E2',  # Blue
            'accent_success': '#5CB85C',
            'accent_warning': '#F0AD4E',
            'accent_danger': '#FF3B30',
            'accent_orange': '#FF6B00',

            # Sidebar
            'sidebar_bg': '#3A3A3C',
            'sidebar_hover': 'rgba(255, 255, 255, 0.1)',
            'sidebar_selected': 'rgba(255, 255, 255, 0.15)',

            # Scrollbar
            'scrollbar_bg': '#F0F0F0',
            'scrollbar_handle': '#CCCCCC',
        }

        # Dark mode color scheme
        self.dark_colors = {
            # Background colors
            'bg_primary': '#1E1E1E',
            'bg_secondary': '#2A2A2A',
            'bg_tertiary': '#252525',
            'bg_hover': '#333333',
            'bg_selected': '#3A3A3A',
            'bg_chat': '#2C3E50',

            # Text colors
            'text_primary': '#E0E0E0',
            'text_secondary': '#B0B0B0',
            'text_tertiary': '#808080',
            'text_inverse': '#1E1E1E',

            # Border colors
            'border_light': '#3A3A3A',
            'border_medium': '#444444',
            'border_dark': '#555555',

            # Accent colors
            'accent_primary': '#FFE400',  # KakaoTalk Yellow
            'accent_secondary': '#5CA7E2',  # Brighter Blue for dark mode
            'accent_success': '#6CC76C',
            'accent_warning': '#F5BA5A',
            'accent_danger': '#FF4D40',
            'accent_orange': '#FF7B10',

            # Sidebar
            'sidebar_bg': '#252525',
            'sidebar_hover': 'rgba(255, 255, 255, 0.08)',
            'sidebar_selected': 'rgba(255, 255, 255, 0.12)',

            # Scrollbar
            'scrollbar_bg': '#2A2A2A',
            'scrollbar_handle': '#555555',
        }

    def get_colors(self):
        """현재 테마의 색상 딕셔너리 반환"""
        return self.dark_colors if self.current_theme == 'dark' else self.light_colors

    def toggle_theme(self):
        """테마 전환 (라이트 ↔ 다크)"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.theme_changed.emit(self.current_theme)

    def set_theme(self, theme_name):
        """특정 테마로 설정"""
        if theme_name in ['light', 'dark']:
            self.current_theme = theme_name
            self.theme_changed.emit(self.current_theme)

    def get_friend_list_item_style(self):
        """친구 목록 아이템 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['bg_primary']};
                border-bottom: 1px solid {c['border_light']};
            }}
            QWidget:hover {{
                background-color: {c['bg_hover']};
            }}
        """

    def get_section_header_style(self):
        """섹션 헤더 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['bg_secondary']};
                border-bottom: 1px solid {c['border_medium']};
            }}
            QWidget:hover {{
                background-color: {c['bg_hover']};
            }}
        """

    def get_user_list_style(self):
        """사용자 목록 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QListWidget {{
                background-color: {c['bg_primary']};
                border: none;
                font-size: 14px;
                color: {c['text_primary']};
            }}
            QListWidget::item {{
                padding: 0px;
                border: none;
                color: {c['text_primary']};
            }}
            QListWidget::item:hover {{
                background-color: {c['bg_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {c['bg_selected']};
            }}
        """

    def get_header_style(self):
        """헤더 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['bg_secondary']};
                border-bottom: 1px solid {c['border_medium']};
            }}
        """

    def get_profile_card_style(self):
        """프로필 카드 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['bg_tertiary']};
                border-bottom: 1px solid {c['border_medium']};
            }}
        """

    def get_sidebar_style(self):
        """사이드바 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['sidebar_bg']};
            }}
        """

    def get_sidebar_button_style(self, selected=False):
        """사이드바 버튼 스타일시트 생성"""
        c = self.get_colors()
        if selected:
            return f"""
                QPushButton {{
                    background-color: {c['sidebar_selected']};
                    border: none;
                    font-size: 24px;
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.2);
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    font-size: 24px;
                    color: #AAAAAA;
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    background-color: {c['sidebar_hover']};
                }}
            """

    def get_icon_color(self, color_type='primary'):
        """아이콘 색상 반환"""
        c = self.get_colors()
        color_map = {
            'primary': c['text_primary'],
            'secondary': c['text_secondary'],
            'tertiary': c['text_tertiary'],
            'inverse': c['text_inverse'],
            'accent': c['accent_primary'],
        }
        return color_map.get(color_type, c['text_primary'])

    def get_birthday_item_style(self):
        """생일 아이템 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['bg_primary']};
                border-bottom: 1px solid {c['border_light']};
            }}
            QWidget:hover {{
                background-color: {c['bg_hover']};
            }}
        """

    def get_channel_item_style(self):
        """채널 아이템 스타일시트 생성"""
        c = self.get_colors()
        return f"""
            QWidget {{
                background-color: {c['bg_primary']};
                border-bottom: 1px solid {c['border_light']};
            }}
            QWidget:hover {{
                background-color: {c['bg_hover']};
            }}
        """


# Global singleton instance
theme_manager = ThemeManager()
