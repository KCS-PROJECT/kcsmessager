# -*- coding: utf-8 -*-
"""
로컬 사용자 설정 - 사용자별 JSON 파일(~/.kcs_messenger/<username>.json)
즐겨찾기, 채팅방 고정/알림끔, 나에게서 삭제한 메시지, 다크모드, 글자 크기
"""

import json
import os

from PyQt5.QtCore import QObject, pyqtSignal

DEFAULTS = {
    'favorites': [],
    'pinned_rooms': [],
    'muted_rooms': [],
    'hidden_messages': [],
    'dark_mode': False,
    'font_scale': 1.0,
    'reduce_motion': False,      # 동작 줄이기 (녹음 표시 깜빡임·요약 진행 막대 정지)
    'notifications': True,
    'brand_theme': 'kcs',
    'chat_wallpaper': None,
    'room_wallpapers': {},
    'chat_folders': [],
    'hidden_friends': [],
    'hidden_story_users': [],
    'failed_messages': [],      # 연결이 끊겨 보내지 못한 메시지 (재전송/삭제 전까지 보존)   # 소식(펑)을 숨긴 친구 (카카오톡 2026 2차 업데이트)
    'alert_keywords': [],
    'room_alert_modes': {},
    'bubble_style': 'basic',
    'lock_pin_hash': '',
    'lock_salt': '',
    'lock_minutes': 5,
    'call_auto_record': False,   # 보이스톡 자동 녹음 (카카오톡 2025-11)
    'social_features': False,    # 펑·생일·선물하기 (회사 메신저는 기본 끔 - 업무 우선)
}


class LocalSettings(QObject):
    """키 단위 변경 시그널을 내보내는 간단한 설정 저장소"""

    changed = pyqtSignal(str)  # key

    def __init__(self, username, base_dir=None, parent=None):
        super().__init__(parent)
        base_dir = base_dir or os.environ.get('KCS_MESSENGER_HOME') or os.path.join(os.path.expanduser('~'), '.kcs_messenger')
        self.path = os.path.join(base_dir, f'{username}.json')
        self._data = dict(DEFAULTS)
        try:
            with open(self.path, encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self._data.update(loaded)
        except (OSError, ValueError):
            pass

    def get(self, key):
        value = self._data.get(key, DEFAULTS.get(key))
        if isinstance(value, list):
            return list(value)
        if isinstance(value, dict):
            return dict(value)
        return value

    def set(self, key, value):
        self._data[key] = value
        self._save()
        self.changed.emit(key)

    def toggle_in(self, key, item):
        """리스트형 설정에서 item을 넣거나 뺀다. 결과 포함 여부를 돌려준다."""
        items = list(self.get(key) or [])
        if item in items:
            items.remove(item)
            included = False
        else:
            items.append(item)
            included = True
        self.set(key, items)
        return included

    def contains(self, key, item):
        return item in self._data.get(key, [])

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
