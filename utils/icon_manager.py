# -*- coding: utf-8 -*-
"""
Icon Manager Utility for KCS Messenger
Handles loading, caching, and color manipulation of SVG icons
"""

import os
from typing import Optional
from functools import lru_cache
from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QByteArray, QSize


class IconManager:
    """
    Singleton class for managing SVG icons throughout the application.

    Features:
    - SVG icon loading from assets directory
    - Dynamic color replacement for theming
    - Multiple size support
    - LRU caching for performance
    - Fallback mechanisms for missing icons
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'assets', 'icons'
        )

        # Icon name to file path mapping
        self.icon_paths = {
            # Navigation icons
            'profile': 'navigation/profile.svg',
            'friends': 'navigation/friends.svg',
            'chat': 'navigation/chat.svg',
            'organization': 'navigation/organization.svg',
            'more': 'navigation/more.svg',
            'settings': 'navigation/settings.svg',

            # Action icons
            'search': 'actions/search.svg',
            'add': 'actions/add.svg',
            'chevron-down': 'actions/chevron-down.svg',
            'chevron-right': 'actions/chevron-right.svg',
            'star': 'actions/star.svg',
            'star-outline': 'actions/star-outline.svg',
            'cake': 'actions/cake.svg',
            'gift': 'actions/gift.svg',

            # Status icons
            'status-online': 'status/online.svg',
            'status-offline': 'status/offline.svg',

            # Misc icons
            'folder': 'misc/folder.svg',
            'info': 'misc/info.svg',
            'verified': 'misc/verified.svg',
            'channel': 'misc/channel.svg',
            'moon': 'misc/moon.svg',
            'sun': 'misc/sun.svg',
        }

        # Default colors
        self.default_color = '#333333'
        self.accent_color = '#FFE400'

    @lru_cache(maxsize=128)
    def get_icon(self, name: str, size: int = 24, color: Optional[str] = None) -> QIcon:
        """
        Get QIcon for the specified icon name.

        Args:
            name: Icon name from icon_paths mapping
            size: Icon size in pixels (default: 24)
            color: Color in hex format (e.g., '#333333')
                   If None, uses default_color

        Returns:
            QIcon object

        Example:
            icon = icon_manager.get_icon('profile', size=24, color='#FFFFFF')
            button.setIcon(icon)
        """
        pixmap = self.get_pixmap(name, size, color)
        return QIcon(pixmap)

    @lru_cache(maxsize=128)
    def get_pixmap(self, name: str, size: int = 24, color: Optional[str] = None) -> QPixmap:
        """
        Get QPixmap for the specified icon name.

        Args:
            name: Icon name from icon_paths mapping
            size: Icon size in pixels (default: 24)
            color: Color in hex format

        Returns:
            QPixmap object

        Example:
            pixmap = icon_manager.get_pixmap('status-online', size=12, color='#00FF00')
            label.setPixmap(pixmap)
        """
        if color is None:
            color = self.default_color

        svg_path = self._get_svg_path(name)
        if not os.path.exists(svg_path):
            print(f"Warning: Icon '{name}' not found at {svg_path}")
            return self._create_fallback_pixmap(size, color)

        # Read SVG content
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
        except Exception as e:
            print(f"Error reading icon '{name}': {e}")
            return self._create_fallback_pixmap(size, color)

        # Replace color in SVG
        svg_content = svg_content.replace('currentColor', color)
        svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')

        # Render SVG to pixmap
        svg_bytes = QByteArray(svg_content.encode('utf-8'))
        renderer = QSvgRenderer(svg_bytes)

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return pixmap

    def _get_svg_path(self, name: str) -> str:
        """Get full file path for icon name."""
        relative_path = self.icon_paths.get(name, '')
        return os.path.join(self.base_path, relative_path)

    def _create_fallback_pixmap(self, size: int, color: str) -> QPixmap:
        """Create a simple fallback pixmap when icon is missing."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        return pixmap

    def clear_cache(self):
        """Clear the icon cache to free memory."""
        self.get_icon.cache_clear()
        self.get_pixmap.cache_clear()

    def preload_icons(self, icon_names: list, size: int = 24):
        """
        Preload a list of icons into cache.

        Args:
            icon_names: List of icon names to preload
            size: Size to cache

        Example:
            icon_manager.preload_icons(['profile', 'friends', 'chat'], size=24)
        """
        for name in icon_names:
            self.get_icon(name, size)


# Global singleton instance
icon_manager = IconManager()
