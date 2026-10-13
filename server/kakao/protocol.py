# -*- coding: utf-8 -*-
"""요청 검사 공용 도구: ProtocolError(사용자에게 보일 오류) · 필드 꺼내기(_req_str 등) · ISO 시각 · 검증 정규식
server.py 와 관리자 처리(admin_handlers.py)가 함께 쓴다"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from .store import ISO_FMT

ACCOUNT_DISABLED = '사용이 중지된 계정입니다. 관리자에게 문의해 주세요.'
ADMIN_ONLY = '관리자만 사용할 수 있습니다.'
EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
EMPLOYEE_NO_RE = re.compile(r'[0-9A-Za-z][0-9A-Za-z_-]{0,19}')   # 사번: 영문·숫자(-, _) 1~20자


class ProtocolError(Exception):
    """클라이언트에게 error 로 돌려줄 검증 오류 (메시지는 한국어)."""


# ---------------------------------------------------------------------- 입력 검증 헬퍼
def _req_str(msg: dict, key: str, max_len: int, allow_empty: bool = False, label: str = '') -> str:
    value = msg.get(key)
    if not isinstance(value, str):
        raise ProtocolError(f'{label or key} 값이 올바르지 않습니다.')
    value = value.strip()
    if not value and not allow_empty:
        raise ProtocolError(f'{label or key} 값을 입력하세요.')
    if len(value) > max_len:
        raise ProtocolError(f'{label or key} 값은 {max_len}자를 넘을 수 없습니다.')
    return value


def _opt_str(msg: dict, key: str, max_len: int, default: str = '') -> str:
    if msg.get(key) is None:
        return default
    return _req_str(msg, key, max_len, allow_empty=True)


INT_LIMIT = 2 ** 62   # SQLite INTEGER(부호 있는 64비트)에 넣을 수 있는 범위 안 (더 크면 OverflowError)


def _req_int(msg: dict, key: str) -> int:
    value = msg.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not -INT_LIMIT <= value <= INT_LIMIT:
        raise ProtocolError(f'{key} 값이 올바르지 않습니다.')
    return value


def _opt_int(msg: dict, key: str) -> Optional[int]:
    return None if msg.get(key) is None else _req_int(msg, key)


def _bool(msg: dict, key: str, default: bool = False) -> bool:
    value = msg.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ProtocolError(f'{key} 값이 올바르지 않습니다.')


def _str_list(msg: dict, key: str, required: bool = True) -> list[str]:
    value = msg.get(key)
    if value is None and not required:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ProtocolError(f'{key} 값이 올바르지 않습니다.')
    seen: list[str] = []
    for v in value:
        v = v.strip()
        if v and v not in seen:
            seen.append(v)
    return seen


def parse_iso(value: Any, key: str) -> datetime:
    """ISO 문자열 → 서버 로컬 naive datetime. 시간대가 있으면 로컬로 변환."""
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError(f'{key} 시각 형식이 올바르지 않습니다.')
    text = value.strip()
    if text.endswith('Z'):
        text = text[:-1] + '+00:00'
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ProtocolError(f'{key} 시각 형식이 올바르지 않습니다.') from None
    if dt.tzinfo is not None:
        try:
            dt = dt.astimezone().replace(tzinfo=None)
        except (OverflowError, OSError):        # 0001-01-01T00:00:00+09:00 처럼 로컬로 바꿀 수 없는 시각
            raise ProtocolError(f'{key} 시각 형식이 올바르지 않습니다.') from None
    return dt


def _norm_iso(value: Any, key: str) -> str:
    return parse_iso(value, key).strftime(ISO_FMT)
