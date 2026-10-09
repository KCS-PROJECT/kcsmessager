# -*- coding: utf-8 -*-
"""
KCS Messenger 서버 (카카오톡 기능 프로토콜 v2).

프로토콜 계약: claudedocs/KAKAO_FEATURE_SPEC.md §2~§5
- TCP + NDJSON(UTF-8). 줄바꿈 없이 이어 붙은 JSON(구버전 클라이언트)도 허용.
- 클라이언트마다 수신 스레드 1개, 소켓마다 송신 Lock.
- 스케줄러 스레드가 예약 메시지와 일정 알림을 처리.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import json
import logging
import os
import queue
import random
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from . import summary as chat_summary
from .store import BOT_USERNAME, ISO_FMT, PRESENCES, Store, now_iso

logger = logging.getLogger('kakao.server')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, 'server_data', 'kakao.db')

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_AVATAR_BYTES = 512 * 1024
MAX_BUFFER_CHARS = 16 * 1024 * 1024
MAX_CONTENT_LEN = 10000
MAX_HISTORY_LIMIT = 200
DELETE_WINDOW = timedelta(hours=24)
REMINDER_GRACE = timedelta(seconds=60)
SOCKET_TIMEOUT = 30.0
RECV_SIZE = 65536

SEND_KINDS = ('text', 'emoticon', 'image', 'file', 'secret', 'contact', 'voice')
ATTACHMENT_KINDS = ('image', 'file', 'voice')   # 첨부 데이터를 함께 보내는 종류
MAX_VOICE_SECONDS = 300                     # 음성메시지 최대 5분 (§9.3)
MAX_REACTION_KINDS = 30                     # 말풍선 하나에 달 수 있는 공감 종류 (카카오톡 v26.4.0, §9.2)
MAX_EXPORT_MESSAGES = 20000                 # 대화 내보내기 상한 (§9.5)
EXPORT_PAGE = 500
EXPORT_CHUNK = 2000                         # 내보내기 응답 한 조각의 메시지 수
MAX_SUMMARY_MESSAGES = 300                  # 대화 요약 대상 최근 메시지 수 (§9.1)
MAX_CALL_HISTORY = 200
SECRET_SEND_KINDS = ('secret', 'emoticon')   # 비밀채팅방에서 허용되는 send 종류 (평문 text 불가)
MAX_SECRET_CONTENT = 64 * 1024               # base64(nonce12 + AES-GCM 암호문)
SECRET_MIN_BYTES = 12 + 16                   # nonce + GCM 태그
SECRET_PEER_NO_KEY = '상대방이 아직 비밀채팅을 사용할 수 없습니다'
SECRET_FORBIDDEN = '비밀채팅방에서는 사용할 수 없는 기능입니다.'

CALL_MODES = ('voice', 'video', 'voiceroom')
CALL_ROLES = ('host', 'speaker', 'listener')
MEDIA_KINDS = ('audio', 'video', 'screen')
AUDIO_CODECS = ('pcm', 'zpcm')
MAX_VIDEO_PARTICIPANTS = 10
MAX_VOICEROOM_PARTICIPANTS = 1500
MAX_VOICEROOM_SPEAKERS = 10                  # host + speaker
MAX_MEDIA_B64 = 2 * 1024 * 1024
CALL_GONE = '종료되었거나 존재하지 않는 통화입니다.'
CALL_NOT_PARTICIPANT = '통화 참여자가 아닙니다.'

DEFAULT_STORY_TTL = 24 * 3600
DEFAULT_VOICEROOM_MAX = 48 * 3600
DEFAULT_STORY_COLOR = '#FEE500'
ATTACHMENT_EXPIRED = '보관 기간이 지난 파일입니다'
MAX_MULTI_PROFILES = 10
LADDER_ROWS = 10
LADDER_MIN, LADDER_MAX = 2, 10
MAX_DRAWER_LIMIT = 200
RSVP_RESPONSES = ('yes', 'no', 'maybe')
COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
DEFAULT_EVENT_COLOR = '#FEE500'

RAG_UNAVAILABLE = 'AI 기능을 사용할 수 없습니다'
RAG_FAILED = '답변을 생성하는 중 오류가 발생했습니다.'
BOT_MENTION = '@' + BOT_USERNAME
URL_RE = re.compile(r'https?://[^\s<>"]+')
EMAIL_RE = re.compile(r'[^@\s]+@[^@\s]+\.[^@\s]+')
PREVIEW_TIMEOUT = 3.0
PREVIEW_MAX_BYTES = 256 * 1024


def fetch_link_preview(url: str) -> Optional[dict]:
    """URL 의 og:title / og:description / og:site_name (없으면 <title>). 실패하면 None."""
    import html as html_mod
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'KCSTalk-LinkPreview/1.0'})
        with urllib.request.urlopen(req, timeout=PREVIEW_TIMEOUT) as resp:
            ctype = resp.headers.get('Content-Type', '')
            if 'html' not in ctype:
                return None
            charset = resp.headers.get_content_charset() or 'utf-8'
            raw = resp.read(PREVIEW_MAX_BYTES)
    except Exception:
        return None
    text = raw.decode(charset, errors='replace')

    def meta(prop: str) -> str:
        for pattern in (rf'<meta[^>]+(?:property|name)=["\']{prop}["\'][^>]*content=["\']([^"\']*)',
                        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']{prop}["\']'):
            m = re.search(pattern, text, re.I)
            if m:
                return html_mod.unescape(m.group(1)).strip()
        return ''
    title = meta('og:title')
    if not title:
        m = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
        title = html_mod.unescape(re.sub(r'\s+', ' ', m.group(1))).strip() if m else ''
    if not title:
        return None
    return {'url': url, 'title': title[:200], 'description': (meta('og:description') or meta('description'))[:300],
            'site': meta('og:site_name')[:80]}
RAG_HISTORY_LIMIT = 20

_IMAGE_SIGNATURES = (
    (b'\x89PNG\r\n\x1a\n', 'image/png', 'png'),
    (b'\xff\xd8\xff', 'image/jpeg', 'jpg'),
    (b'GIF87a', 'image/gif', 'gif'),
    (b'GIF89a', 'image/gif', 'gif'),
    (b'BM', 'image/bmp', 'bmp'),
)


def _sniff_image(data: bytes) -> Optional[tuple[str, str]]:
    """이미지 시그니처로 (mime, 확장자) 판별. 이미지가 아니면 None."""
    for sig, mime, ext in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            return mime, ext
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp', 'webp'
    return None


def _decode_b64(data_b64: Any, max_bytes: int, too_big: str) -> bytes:
    if not isinstance(data_b64, str) or not data_b64:
        raise ProtocolError('첨부 파일 데이터가 없습니다.')
    if len(data_b64) > (max_bytes * 4) // 3 + 8:
        raise ProtocolError(too_big)
    try:
        data = base64.b64decode(data_b64, validate=True)
    except (binascii.Error, ValueError):
        raise ProtocolError('첨부 파일 데이터(base64)가 올바르지 않습니다.') from None
    if len(data) > max_bytes:
        raise ProtocolError(too_big)
    return data


# ---------------------------------------------------------------------- 사다리 게임 (명세 §8.7)
def generate_ladder_rungs(columns: int, rows: int = LADDER_ROWS, rng: Optional[random.Random] = None) -> list[list[int]]:
    """무작위 가로줄 [[row, col], ...] 생성. col 은 왼쪽 세로줄 인덱스, 같은 row 에 인접한 가로줄은 없다."""
    rng = rng or random.SystemRandom()
    rungs: list[list[int]] = []
    for row in range(rows):
        prev = False
        for col in range(columns - 1):
            if not prev and rng.random() < 0.5:
                rungs.append([row, col])
                prev = True
            else:
                prev = False
    return rungs


def compute_ladder_mapping(participants: list[str], results: list[str], rungs: list) -> dict[str, str]:
    """위에서부터 내려가며 가로줄을 만나면 옆 세로줄로 이동 → {participant: result}.

    가로줄이 범위를 벗어나거나 같은 row 에 인접해 있으면 ValueError.
    """
    n = len(participants)
    if n != len(results):
        raise ValueError('참가자와 결과의 개수가 같아야 합니다.')
    rung_set: set[tuple[int, int]] = set()
    for rung in rungs:
        row, col = int(rung[0]), int(rung[1])
        if row < 0 or not 0 <= col < n - 1:
            raise ValueError('가로줄 위치가 올바르지 않습니다.')
        if (row, col - 1) in rung_set or (row, col + 1) in rung_set:
            raise ValueError('같은 줄에 인접한 가로줄이 있습니다.')
        rung_set.add((row, col))
    rows = max([LADDER_ROWS] + [r + 1 for r, _ in rung_set])
    mapping: dict[str, str] = {}
    for start, name in enumerate(participants):
        col = start
        for row in range(rows):
            if (row, col) in rung_set:
                col += 1
            elif (row, col - 1) in rung_set:
                col -= 1
        mapping[name] = results[col]
    return mapping


def _default_rag_factory(db_path: str) -> Any:
    from .rag import RagService  # 지연 import: rag.py 가 없어도 서버는 동작
    return RagService(db_path)


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


def _req_int(msg: dict, key: str) -> int:
    value = msg.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
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
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def _norm_iso(value: Any, key: str) -> str:
    return parse_iso(value, key).strftime(ISO_FMT)


def _validate_birthday(value: Any) -> Optional[str]:
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{2}-\d{2}', value):
        raise ProtocolError('생일은 MM-DD 형식이어야 합니다.')
    try:
        datetime.strptime('2000-' + value, '%Y-%m-%d')
    except ValueError:
        raise ProtocolError('존재하지 않는 날짜입니다.') from None
    return value


def _validate_due(value: Any) -> Optional[str]:
    if value is None or value == '':
        return None
    if not isinstance(value, str):
        raise ProtocolError('마감일은 YYYY-MM-DD 형식이어야 합니다.')
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        raise ProtocolError('마감일은 YYYY-MM-DD 형식이어야 합니다.') from None


# ---------------------------------------------------------------------- 연결
class Connection:
    """클라이언트 연결 1개. 송신은 Lock 으로 보호된다."""

    def __init__(self, sock: socket.socket, address: Any) -> None:
        self.sock = sock
        self.address = address
        self.username: Optional[str] = None
        self.alive = True
        self._send_lock = threading.Lock()

    def send(self, payload: dict) -> bool:
        if not self.alive:
            return False
        data = (json.dumps(payload, ensure_ascii=False) + '\n').encode('utf-8')
        try:
            with self._send_lock:
                self.sock.sendall(data)
            return True
        except OSError as exc:
            logger.info('send failed to %s: %s', self.address, exc)
            self.close()
            return False

    def close(self) -> None:
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class FrameDecoder:
    """NDJSON + 줄바꿈 없는 연속 JSON 을 모두 처리하는 수신 버퍼."""

    def __init__(self) -> None:
        self._utf8 = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self._parts: list[str] = []   # 아직 완성되지 않은 프레임 조각 (대용량 첨부 시 재복사 방지)
        self._size = 0
        self._json = json.JSONDecoder()

    def _reset(self, rest: str) -> None:
        self._parts = [rest] if rest else []
        self._size = len(rest)

    def feed(self, data: bytes) -> list[Any]:
        """수신 바이트를 넣고 완성된 항목 목록을 반환. 파싱 실패 줄은 ``ValueError`` 인스턴스로 반환."""
        text = self._utf8.decode(data)
        if not text:
            return []
        self._parts.append(text)
        self._size += len(text)
        items: list[Any] = []
        if '\n' in text:
            lines = ''.join(self._parts).split('\n')
            self._reset(lines.pop())
            for line in lines:
                items.extend(self._decode_line(line))
        # 줄바꿈 없는 구버전 프레임: 끝이 '}' 일 때만 시도(부분 수신 재파싱 비용 절감)
        if self._parts and self._parts[-1].rstrip().endswith('}'):
            buf = ''.join(self._parts)
            decoded, rest = self._decode_prefix(buf.strip())
            if decoded:
                items.extend(decoded)
                self._reset(rest)
            else:
                self._parts = [buf]
        if self._size > MAX_BUFFER_CHARS:
            raise OverflowError('수신 버퍼 한도 초과')
        return items

    def _decode_prefix(self, text: str) -> tuple[list[Any], str]:
        out: list[Any] = []
        idx, n = 0, len(text)
        while idx < n:
            while idx < n and text[idx].isspace():
                idx += 1
            if idx >= n:
                break
            try:
                obj, idx = self._json.raw_decode(text, idx)
            except json.JSONDecodeError:
                break
            out.append(obj)
        return out, text[idx:]

    def _decode_line(self, line: str) -> list[Any]:
        decoded, rest = self._decode_prefix(line)
        if rest.strip():
            decoded.append(ValueError('JSON 형식이 올바르지 않습니다.'))
        return decoded


@dataclass
class Ctx:
    """요청 1건의 처리 문맥."""
    conn: Connection
    username: str
    req_type: str
    req_id: Any = None
    has_req_id: bool = False
    extra: dict = field(default_factory=dict)


@dataclass
class Call:
    """진행 중인 통화 1건 (메모리에만 존재, KakaoServer._calls_lock 으로 보호)."""
    call_id: int
    room_id: str
    mode: str
    host: str
    started_at: str
    started_mono: float
    participants: dict = field(default_factory=dict)
    joined: set = field(default_factory=set)        # 한 번이라도 참여한 사람 (통화 기록·부재중 판정)

    @staticmethod
    def new_participant(role: str, mode: str) -> dict:
        return {'role': role, 'muted': False, 'video': mode == 'video', 'screen': False, 'hand': False}

    def has_host(self) -> bool:
        return any(p['role'] == 'host' for p in self.participants.values())

    def stage_count(self) -> int:
        return sum(1 for p in self.participants.values() if p['role'] in ('host', 'speaker'))

    def to_dict(self) -> dict:
        return {'call_id': self.call_id, 'room_id': self.room_id, 'mode': self.mode, 'host': self.host,
                'started_at': self.started_at,
                'participants': {u: dict(p) for u, p in self.participants.items()}}


# ---------------------------------------------------------------------- 서버
class KakaoServer:
    """카카오톡 기능 서버. ``start()``(블로킹) / ``serve_in_thread()`` / ``stop()``."""

    def __init__(self, host: str = '127.0.0.1', port: int = 5555, db_path: Optional[str] = None,
                 tick_seconds: float = 1.0, rag_factory: Optional[Callable[[str], Any]] = None,
                 link_preview: Optional[bool] = None, daily_briefing: bool = False,
                 preview_fetcher: Optional[Callable[[str], Optional[dict]]] = None,
                 retention_days: float = 90, story_ttl_seconds: float = DEFAULT_STORY_TTL,
                 voiceroom_max_seconds: float = DEFAULT_VOICEROOM_MAX) -> None:
        self.host = host
        self.retention_days = float(retention_days)          # 받은 파일 보관 기간 (§8.10)
        self.story_ttl_seconds = float(story_ttl_seconds)    # 펑 유지 시간 (§8.3)
        self.voiceroom_max_seconds = float(voiceroom_max_seconds)  # 보이스룸 자동 종료 (§8.2)
        # 통화 레지스트리 (영속화하지 않음)
        self._calls_lock = threading.Lock()
        self._calls: dict[int, Call] = {}
        self._summary_lock = threading.Lock()
        self._summaries_running: set = set()      # (username, room_id) 요약 진행 중
        self._room_calls: dict[str, int] = {}
        self._next_call_id = 1
        # URL 미리보기 (명세 §7.8) - 환경변수 KCS_LINK_PREVIEW=off 로 끌 수 있다
        if link_preview is None:
            link_preview = os.environ.get('KCS_LINK_PREVIEW', '').lower() not in ('off', '0', 'false')
        self.link_preview = bool(link_preview)
        self.preview_fetcher = preview_fetcher or fetch_link_preview
        self._preview_queue: 'queue.Queue[Optional[dict]]' = queue.Queue()
        self.daily_briefing = bool(daily_briefing)
        self.rag_factory = rag_factory or _default_rag_factory
        self.rag: Any = None
        self._rag_queue: 'queue.Queue[Optional[Callable[[], None]]]' = queue.Queue()
        self.port = port
        self.db_path = db_path or DEFAULT_DB_PATH
        self.tick_seconds = max(0.05, float(tick_seconds))
        self.store: Optional[Store] = None
        self._listener: Optional[socket.socket] = None
        self._stop = threading.Event()
        self._conns_lock = threading.Lock()
        self._conns: set[Connection] = set()
        self._by_user: dict[str, set[Connection]] = {}
        self._threads: list[threading.Thread] = []
        self._threads_lock = threading.Lock()
        self._handlers: dict[str, Callable[[Ctx, dict], None]] = {
            'message': self._h_legacy_message,
            'room_open_direct': self._h_room_open_direct,
            'room_create': self._h_room_create,
            'room_invite': self._h_room_invite,
            'room_leave': self._h_room_leave,
            'room_rename': self._h_room_rename,
            'history': self._h_history,
            'send': self._h_send,
            'read': self._h_read,
            'react': self._h_react,
            'delete': self._h_delete,
            'edit': self._h_edit,
            'notice_set': self._h_notice_set,
            'search': self._h_search,
            'poll_create': self._h_poll_create,
            'poll_vote': self._h_poll_vote,
            'poll_close': self._h_poll_close,
            'event_create': self._h_event_create,
            'event_update': self._h_event_update,
            'event_delete': self._h_event_delete,
            'event_rsvp': self._h_event_rsvp,
            'event_list': self._h_event_list,
            'todo_create': self._h_todo_create,
            'todo_update': self._h_todo_update,
            'todo_delete': self._h_todo_delete,
            'todo_list': self._h_todo_list,
            'profile_update': self._h_profile_update,
            'attachment_get': self._h_attachment_get,
            'presence_set': self._h_presence_set,
            'rag_doc_list': self._h_rag_doc_list,
            'rag_doc_add': self._h_rag_doc_add,
            'rag_doc_delete': self._h_rag_doc_delete,
            # v3 (명세 §8)
            'key_publish': self._h_key_publish,
            'room_open_secret': self._h_room_open_secret,
            'call_start': self._h_call_start,
            'call_join': self._h_call_join,
            'call_leave': self._h_call_leave,
            'call_hand': self._h_call_hand,
            'call_role': self._h_call_role,
            'call_state': self._h_call_state,
            'call_media': self._h_call_media,
            'call_list': self._h_call_list,
            'story_post': self._h_story_post,
            'story_list': self._h_story_list,
            'story_view': self._h_story_view,
            'story_delete': self._h_story_delete,
            'multi_profile_set': self._h_multi_profile_set,
            'multi_profile_list': self._h_multi_profile_list,
            'block_set': self._h_block_set,
            'friend_add': self._h_friend_add,
            'friend_remove': self._h_friend_remove,
            'friend_list': self._h_friend_list,
            'ladder_create': self._h_ladder_create,
            'board_post': self._h_board_post,
            'board_list': self._h_board_list,
            'board_comment': self._h_board_comment,
            'board_delete': self._h_board_delete,
            'open_room_create': self._h_open_room_create,
            'open_room_search': self._h_open_room_search,
            'open_room_join': self._h_open_room_join,
            'drawer_query': self._h_drawer_query,
            # v4: 2026 업데이트 (명세 §9)
            'room_summary': self._h_room_summary,
            'call_history': self._h_call_history,
            'room_export': self._h_room_export,
        }

    # ------------------------------------------------------------------ 생명주기
    def _bind(self) -> None:
        self._stop.clear()
        self.store = Store(self.db_path, retention_days=self.retention_days)
        with self._calls_lock:
            self._calls.clear()
            self._room_calls.clear()
            self._next_call_id = self.store.max_call_id() + 1   # 저장된 call 메시지와 id 충돌 방지
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
            sock.listen(64)
        except OSError:
            sock.close()
            self.store.close()
            raise
        sock.settimeout(0.5)
        self._listener = sock
        self._init_rag()
        self.port = sock.getsockname()[1]
        logger.info('KCS Messenger 서버 시작: %s:%s (db=%s)', self.host, self.port, self.db_path)

    def _rag_db_path(self) -> str:
        if self.db_path == ':memory:':
            return ':memory:'
        return os.path.join(os.path.dirname(os.path.abspath(self.db_path)), 'rag.db')

    def _init_rag(self) -> None:
        try:
            self.rag = self.rag_factory(self._rag_db_path())
        except Exception as exc:  # ImportError 포함: AI 기능만 비활성화
            logger.warning('RAG 비활성화: %s', exc)
            self.rag = None
        self._rag_queue = queue.Queue()

    def _spawn(self, target: Callable, *args: Any, name: str = '') -> threading.Thread:
        t = threading.Thread(target=target, args=args, daemon=True, name=name or None)
        with self._threads_lock:
            self._threads = [x for x in self._threads if x.is_alive()]
            self._threads.append(t)
        t.start()
        return t

    def start(self) -> None:
        """서버를 시작하고 stop() 될 때까지 블로킹."""
        self._bind()
        self._spawn(self._scheduler_loop, name='kakao-scheduler')
        self._spawn(self._rag_worker, name='kakao-rag')
        self._spawn(self._preview_worker, name='kakao-preview')
        try:
            self._accept_loop()
        finally:
            self.stop()

    def serve_in_thread(self) -> threading.Thread:
        """listen 상태가 된 뒤 반환. 실제 포트는 ``self.port``."""
        self._bind()
        self._spawn(self._scheduler_loop, name='kakao-scheduler')
        self._spawn(self._rag_worker, name='kakao-rag')
        self._spawn(self._preview_worker, name='kakao-preview')
        return self._spawn(self._accept_loop, name='kakao-accept')

    def stop(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
        with self._conns_lock:
            conns = list(self._conns)
        for conn in conns:
            conn.close()
        self._rag_queue.put(None)
        self._preview_queue.put(None)
        current = threading.current_thread()
        with self._threads_lock:
            threads = list(self._threads)
        for t in threads:
            if t is not current:
                t.join(timeout=2.0)
        if self.store is not None:
            self.store.close()
        close_rag = getattr(self.rag, 'close', None)
        if callable(close_rag):
            try:
                close_rag()
            except Exception:
                logger.exception('RAG 종료 오류')
        logger.info('KCS Messenger 서버 종료')

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                sock, address = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            sock.settimeout(SOCKET_TIMEOUT)
            conn = Connection(sock, address)
            with self._conns_lock:
                self._conns.add(conn)
            self._spawn(self._client_loop, conn, name=f'kakao-client-{address}')

    # ------------------------------------------------------------------ 연결 관리
    def _online_users(self) -> set[str]:
        with self._conns_lock:
            online = {u for u, cs in self._by_user.items() if cs}
        online.add(BOT_USERNAME)  # 봇은 항상 접속 중
        return online

    @staticmethod
    def _apply_profile(user: dict, override: Optional[dict]) -> dict:
        return {**user, **override} if override else user

    def _users_for(self, viewer: str, online: set[str]) -> list[dict]:
        """viewer 에게 보낼 사용자 목록 (멀티프로필 적용, 조회 1회)."""
        overrides = self.store.profile_overrides_for_viewer(viewer)
        return [self._apply_profile(u, overrides.get(u['username'])) for u in self.store.list_users(online)]

    def _broadcast_user(self, username: str, ctx: Optional[Ctx] = None, exclude_user: Optional[str] = None) -> None:
        """user_updated 를 수신자별(멀티프로필)로 만들어 모든 접속자에게 보낸다."""
        base = self.store.get_user(username, self._online_users())
        if base is None:
            return
        overrides = self.store.profile_overrides_for_owner(username)
        for conn in self._all_joined_conns():
            if exclude_user is not None and conn.username == exclude_user:
                continue
            payload = {'type': 'user_updated', 'user': self._apply_profile(base, overrides.get(conn.username))}
            if ctx is not None and conn is ctx.conn and ctx.has_req_id:
                payload['req_id'] = ctx.req_id
            conn.send(payload)

    def _user_conns(self, usernames: Any) -> list[Connection]:
        with self._conns_lock:
            out: list[Connection] = []
            for u in usernames:
                out.extend(self._by_user.get(u, ()))
            return out

    def _all_joined_conns(self) -> list[Connection]:
        with self._conns_lock:
            return [c for cs in self._by_user.values() for c in cs]

    def _deliver(self, conns: list[Connection], payload: dict, ctx: Optional[Ctx] = None) -> None:
        for conn in conns:
            if ctx is not None and conn is ctx.conn and ctx.has_req_id:
                conn.send({**payload, 'req_id': ctx.req_id})
            else:
                conn.send(payload)

    def _push(self, usernames: Any, payload: dict, ctx: Optional[Ctx] = None) -> None:
        self._deliver(self._user_conns(set(usernames)), payload, ctx)

    def _broadcast(self, payload: dict, ctx: Optional[Ctx] = None, exclude_user: Optional[str] = None) -> None:
        conns = [c for c in self._all_joined_conns() if c.username != exclude_user]
        self._deliver(conns, payload, ctx)

    def _reply(self, ctx: Ctx, payload: dict) -> None:
        if ctx.has_req_id:
            payload = {**payload, 'req_id': ctx.req_id}
        ctx.conn.send(payload)

    def _send_error(self, conn: Connection, req_type: str, message: str, request: Optional[dict]) -> None:
        payload: dict = {'type': 'error', 'req_type': req_type, 'message': message}
        if isinstance(request, dict) and 'req_id' in request:
            payload['req_id'] = request['req_id']
        conn.send(payload)

    def _client_loop(self, conn: Connection) -> None:
        decoder = FrameDecoder()
        try:
            while conn.alive and not self._stop.is_set():
                try:
                    data = conn.sock.recv(RECV_SIZE)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                try:
                    items = decoder.feed(data)
                except OverflowError:
                    self._send_error(conn, '', '요청이 너무 큽니다.', None)
                    break
                for item in items:
                    if not conn.alive:
                        break
                    self._handle_item(conn, item)
        finally:
            self._disconnect(conn)

    def _handle_item(self, conn: Connection, item: Any) -> None:
        if isinstance(item, ValueError):
            self._send_error(conn, '', str(item), None)
            return
        if not isinstance(item, dict) or not isinstance(item.get('type'), str):
            self._send_error(conn, '', '요청 형식이 올바르지 않습니다.', item if isinstance(item, dict) else None)
            return
        req_type = item['type']
        try:
            if req_type == 'join':
                self._h_join(conn, item)
                return
            if req_type == 'leave':
                conn.close()
                return
            if conn.username is None:
                raise ProtocolError('먼저 로그인(join)해야 합니다.')
            handler = self._handlers.get(req_type)
            if handler is None:
                raise ProtocolError(f'알 수 없는 요청입니다: {req_type}')
            ctx = Ctx(conn=conn, username=conn.username, req_type=req_type,
                      req_id=item.get('req_id'), has_req_id='req_id' in item)
            handler(ctx, item)
        except ProtocolError as exc:
            self._send_error(conn, req_type, str(exc), item)
        except Exception:  # 한 요청의 오류가 연결을 끊지 않도록
            logger.exception('요청 처리 중 오류: %s', req_type)
            self._send_error(conn, req_type, '서버 오류가 발생했습니다.', item)

    def _disconnect(self, conn: Connection) -> None:
        conn.close()
        went_offline = False
        username = conn.username
        with self._conns_lock:
            self._conns.discard(conn)
            if username is not None:
                conns = self._by_user.get(username)
                if conns is not None:
                    conns.discard(conn)
                    if not conns:
                        del self._by_user[username]
                        went_offline = True
        if went_offline and not self._stop.is_set():
            logger.info('%s 오프라인', username)
            self._broadcast({'type': 'user_status_changed', 'username': username,
                             'status': 'offline', 'timestamp': now_iso()})
            self._broadcast_user(username)
            self._leave_all_calls(username)   # 접속 종료 = 통화 나가기

    # ------------------------------------------------------------------ 공용 헬퍼
    def _require_room_member(self, room_id: Any, username: str) -> dict:
        if not isinstance(room_id, str) or not room_id:
            raise ProtocolError('room_id 값이 올바르지 않습니다.')
        meta = self.store.room_meta(room_id)
        if meta is None:
            raise ProtocolError('존재하지 않는 채팅방입니다.')
        if username not in meta['members']:
            raise ProtocolError('이 채팅방의 대화상대가 아닙니다. 초대를 받은 뒤 이용할 수 있습니다.')
        return meta

    def _require_message_member(self, msg_id: int, username: str) -> dict:
        message = self.store.get_message(msg_id)
        if message is None:
            raise ProtocolError('존재하지 않는 메시지입니다.')
        if not self.store.is_member(message['room_id'], username):
            raise ProtocolError('이 채팅방의 대화상대가 아닙니다. 초대를 받은 뒤 이용할 수 있습니다.')
        return message

    def _push_room_updated(self, room_id: str, usernames: Any, ctx: Optional[Ctx] = None) -> None:
        """room_updated 는 수신자별 unread_count 가 다르므로 사용자마다 계산해 보낸다."""
        for u in set(usernames):
            conns = self._user_conns([u])
            if not conns:
                continue
            room = self.store.room_dict(room_id, u)
            if room is not None:
                self._deliver(conns, {'type': 'room_updated', 'room': room}, ctx)

    def _post_system(self, room_id: str, text: str) -> None:
        message = self.store.add_message(room_id, '', 'system', text)
        self._push(self.store.members(room_id), {'type': 'msg_new', 'message': message, 'client_tmp_id': None})

    def _publish_new_message(self, message: dict, ctx: Optional[Ctx] = None,
                             client_tmp_id: Any = None) -> None:
        """msg_new + 발신자 read_update 를 방 멤버에게 전송."""
        room_id = message['room_id']
        members = self.store.members(room_id)
        self._push(self._message_recipients(members, message), {'type': 'msg_new', 'message': message,
                                                                 'client_tmp_id': client_tmp_id}, ctx)
        sender = message['sender']
        if sender:
            self._push(members, {'type': 'read_update', 'room_id': room_id, 'username': sender,
                                 'last_read_msg_id': self.store.read_pointer(room_id, sender)})

    def _message_recipients(self, members: list[str], message: dict) -> list[str]:
        """발신자를 차단한 멤버를 제외 (명세 §8.6 - 발신자는 차단 사실을 알 수 없다)."""
        sender = message.get('sender')
        if not sender:
            return list(members)
        blockers = self.store.blockers_of(sender)
        return [m for m in members if m not in blockers]

    def _push_msg_updated(self, message: dict, ctx: Optional[Ctx] = None) -> None:
        members = self.store.members(message['room_id'])
        self._push(self._message_recipients(members, message), {'type': 'msg_updated', 'message': message}, ctx)

    def _require_not_secret(self, meta: dict) -> None:
        if meta['type'] == 'secret':
            raise ProtocolError(SECRET_FORBIDDEN)

    def _names(self, usernames: list[str]) -> str:
        return ', '.join(self.store.display_name(u) for u in usernames)

    def _require_users_exist(self, usernames: list[str]) -> None:
        missing = [u for u in usernames if not self.store.user_exists(u)]
        if missing:
            raise ProtocolError(f'존재하지 않는 사용자입니다: {", ".join(missing)}')

    # ------------------------------------------------------------------ join / 구버전
    def _h_join(self, conn: Connection, msg: dict) -> None:
        username = _req_str(msg, 'username', 20, label='사용자 이름')
        if any(ord(ch) < 32 for ch in username):
            raise ProtocolError('사용자 이름에 사용할 수 없는 문자가 있습니다.')
        if username == BOT_USERNAME or self.store.is_bot(username):
            raise ProtocolError('봇 계정으로는 로그인할 수 없습니다.')
        if conn.username is not None:
            raise ProtocolError('이미 로그인된 연결입니다.')
        created = self.store.ensure_user(username)
        with self._conns_lock:
            conns = self._by_user.setdefault(username, set())
            first_conn = not conns
            conns.add(conn)
            conn.username = username
        online = self._online_users()
        ctx = Ctx(conn=conn, username=username, req_type='join', req_id=msg.get('req_id'),
                  has_req_id='req_id' in msg)
        self._reply(ctx, {
            'type': 'welcome',
            'me': self.store.get_user(username, online),
            'users': self._users_for(username, online),
            'rooms': self.store.rooms_for_user(username),
            'org': self.store.org_meta,
            'calls': self._calls_for_user(username),
            'blocked': self.store.blocked_list(username),
            'friends': self.store.friends_of(username),
        })
        conn.send({'type': 'all_users_list',
                   'users': [u['username'] for u in self.store.list_users()],
                   'online_users': sorted(online)})
        if first_conn:
            self._broadcast({'type': 'user_status_changed', 'username': username,
                             'status': 'online', 'timestamp': now_iso()}, exclude_user=username)
        if created or first_conn:
            # 신규 사용자 등록 / 접속 상태(presence) 변경 알림
            self._broadcast_user(username, exclude_user=username)
        if self.daily_briefing and first_conn and username != BOT_USERNAME \
                and self.store.take_briefing_slot(username, date.today().isoformat()):
            self._rag_queue.put(lambda: self._send_briefing(username))
        logger.info('%s 접속 (%s)', username, conn.address)

    def _h_legacy_message(self, ctx: Ctx, msg: dict) -> None:
        content = msg.get('content')
        if not isinstance(content, str):
            raise ProtocolError('content 값이 올바르지 않습니다.')
        if len(content) > MAX_CONTENT_LEN:
            raise ProtocolError(f'메시지는 {MAX_CONTENT_LEN}자를 넘을 수 없습니다.')
        self._broadcast({'type': 'message', 'sender': ctx.username, 'content': content,
                         'timestamp': datetime.now().isoformat()})

    # ------------------------------------------------------------------ 채팅방
    def _h_room_open_direct(self, ctx: Ctx, msg: dict) -> None:
        target = _req_str(msg, 'target', 20, label='대상')
        self._require_users_exist([target])
        room_id, _added = self.store.get_or_create_direct(ctx.username, target)
        self._push_room_updated(room_id, {ctx.username, target}, ctx)

    def _h_room_create(self, ctx: Ctx, msg: dict) -> None:
        name = _opt_str(msg, 'name', 50)
        members = [m for m in _str_list(msg, 'members') if m != ctx.username]
        if not members:
            raise ProtocolError('초대할 친구를 1명 이상 선택하세요.')
        if len(members) > 100:
            raise ProtocolError('한 번에 초대할 수 있는 인원을 초과했습니다.')
        self._require_users_exist(members)
        room_id = self.store.create_group(ctx.username, name, members)
        self._push_room_updated(room_id, [ctx.username] + members, ctx)
        self._post_system(room_id, f'{self.store.display_name(ctx.username)}님이 {self._names(members)}님을 초대했습니다.')

    def _h_room_invite(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        if meta['type'] != 'group':
            raise ProtocolError('1:1 채팅방에는 초대할 수 없습니다.')
        usernames = [u for u in _str_list(msg, 'usernames') if u not in meta['members']]
        if not usernames:
            raise ProtocolError('새로 초대할 친구가 없습니다.')
        self._require_users_exist(usernames)
        self.store.add_members(meta['room_id'], usernames)
        self._push_room_updated(meta['room_id'], meta['members'] + usernames, ctx)
        self._post_system(meta['room_id'],
                          f'{self.store.display_name(ctx.username)}님이 {self._names(usernames)}님을 초대했습니다.')

    def _h_room_leave(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        room_id = meta['room_id']
        leaver = self._member_label(meta, ctx.username)
        self.store.remove_member(room_id, ctx.username)
        self._leave_all_calls(ctx.username, room_id)
        self._push([ctx.username], {'type': 'room_removed', 'room_id': room_id}, ctx)
        remaining = [u for u in meta['members'] if u != ctx.username]
        if remaining:
            self._push_room_updated(room_id, remaining)
            self._post_system(room_id, f'{leaver}님이 나갔습니다.')

    def _h_room_rename(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        if meta['type'] != 'group':
            raise ProtocolError('그룹 채팅방만 이름을 변경할 수 있습니다.')
        name = _req_str(msg, 'name', 50, allow_empty=True, label='채팅방 이름')
        self.store.rename_room(meta['room_id'], name)
        self._push_room_updated(meta['room_id'], meta['members'], ctx)

    def _h_history(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        before = _opt_int(msg, 'before_msg_id')
        limit = _opt_int(msg, 'limit')
        limit = 50 if limit is None else max(1, min(limit, MAX_HISTORY_LIMIT))
        messages, has_more = self.store.history(meta['room_id'], before, limit, viewer=ctx.username)
        self._reply(ctx, {'type': 'history', 'room_id': meta['room_id'], 'messages': messages,
                          'has_more': has_more})

    # ------------------------------------------------------------------ 메시지
    def _decode_attachment(self, att: Any) -> tuple[str, str, bytes]:
        if not isinstance(att, dict):
            raise ProtocolError('첨부 파일 정보가 올바르지 않습니다.')
        name = _req_str(att, 'name', 200, label='파일 이름')
        mime = _opt_str(att, 'mime', 100, 'application/octet-stream') or 'application/octet-stream'
        data = _decode_b64(att.get('data_b64'), MAX_ATTACHMENT_BYTES, '첨부 파일은 10MB를 초과할 수 없습니다.')
        return name, mime, data

    def _h_send(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        room_id = meta['room_id']
        kind = msg.get('kind', 'text')
        if kind not in SEND_KINDS:
            raise ProtocolError('지원하지 않는 메시지 종류입니다.')
        if meta['type'] == 'secret' and kind not in SECRET_SEND_KINDS:
            raise ProtocolError('비밀채팅방에서는 암호화된 메시지와 이모티콘만 보낼 수 있습니다.')
        if kind == 'secret' and meta['type'] != 'secret':
            raise ProtocolError('비밀채팅 메시지는 비밀채팅방에서만 보낼 수 있습니다.')
        content = msg.get('content', '')
        if content is None:
            content = ''
        if not isinstance(content, str):
            raise ProtocolError('content 값이 올바르지 않습니다.')
        if kind == 'secret':
            self._validate_secret_content(content)
        elif len(content) > MAX_CONTENT_LEN:
            raise ProtocolError(f'메시지는 {MAX_CONTENT_LEN}자를 넘을 수 없습니다.')
        if kind in ('text', 'emoticon') and not content.strip():
            raise ProtocolError('메시지 내용을 입력하세요.')
        if kind == 'contact' and not self.store.user_exists(content):
            raise ProtocolError('보낼 연락처를 찾을 수 없습니다. 연락처 목록에서 다시 골라 주세요.')
        if kind == 'voice':
            if not content.isdigit() or not 1 <= int(content) <= MAX_VOICE_SECONDS:
                raise ProtocolError(f'음성메시지는 1초에서 {MAX_VOICE_SECONDS // 60}분 사이로 녹음해 주세요.')

        reply_to_id = _opt_int(msg, 'reply_to_id')
        if reply_to_id is not None:
            orig = self.store.get_message(reply_to_id)
            if orig is None or orig['room_id'] != room_id:
                raise ProtocolError('답장할 메시지를 찾을 수 없습니다.')

        mentions = [m for m in _str_list(msg, 'mentions', required=False) if m in meta['members']]

        attachment_id = None
        if kind in ATTACHMENT_KINDS:
            name, mime, data = self._decode_attachment(msg.get('attachment'))
            if kind == 'voice' and not mime.startswith('audio/'):
                raise ProtocolError('음성메시지는 오디오 파일이어야 합니다.')
        elif msg.get('attachment') is not None:
            raise ProtocolError('텍스트 메시지에는 첨부 파일을 보낼 수 없습니다.')

        send_at = None
        if msg.get('send_at') is not None:
            send_at = _norm_iso(msg.get('send_at'), 'send_at')
            if send_at <= now_iso():
                send_at = None  # 과거/현재 시각이면 즉시 전송

        if kind in ATTACHMENT_KINDS:
            attachment_id = self.store.save_attachment(name, mime, data, ctx.username)

        client_tmp_id = msg.get('client_tmp_id')
        silent = bool(msg.get('silent'))
        if send_at is not None:
            payload = {'kind': kind, 'content': content, 'reply_to_id': reply_to_id, 'mentions': mentions,
                       'attachment_id': attachment_id, 'client_tmp_id': client_tmp_id, 'silent': silent}
            scheduled_id = self.store.add_scheduled(room_id, ctx.username, send_at, payload)
            self._reply(ctx, {'type': 'scheduled_ok', 'scheduled_id': scheduled_id, 'room_id': room_id,
                              'send_at': send_at, 'content': content})
            return

        self._deliver_message(room_id, ctx.username, kind, content, reply_to_id, mentions,
                              attachment_id, client_tmp_id, ctx, silent=silent)

    @staticmethod
    def _validate_secret_content(content: str) -> None:
        """서버는 복호화하지 않고 형식(base64, 최소 길이)만 확인한다."""
        if not content or len(content) > MAX_SECRET_CONTENT:
            raise ProtocolError('비밀채팅 메시지 형식이 올바르지 않습니다.')
        try:
            raw = base64.b64decode(content, validate=True)
        except (binascii.Error, ValueError):
            raise ProtocolError('비밀채팅 메시지 형식이 올바르지 않습니다.') from None
        if len(raw) < SECRET_MIN_BYTES:
            raise ProtocolError('비밀채팅 메시지 형식이 올바르지 않습니다.')

    def _deliver_message(self, room_id: str, sender: str, kind: str, content: str,
                         reply_to_id: Optional[int], mentions: list[str], attachment_id: Optional[int],
                         client_tmp_id: Any, ctx: Optional[Ctx], silent: bool = False) -> None:
        restored = self.store.restore_direct_members(room_id)
        if restored:
            self._push_room_updated(room_id, restored)
        message = self.store.add_message(room_id, sender, kind, content, reply_to_id, mentions, attachment_id,
                                         silent=silent)
        self._publish_new_message(message, ctx, client_tmp_id)
        self._after_user_message(message)

    def _h_read(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        last = _req_int(msg, 'last_msg_id')
        value = self.store.update_read(meta['room_id'], ctx.username, last)
        self._push(meta['members'], {'type': 'read_update', 'room_id': meta['room_id'],
                                     'username': ctx.username, 'last_read_msg_id': value}, ctx)

    def _h_react(self, ctx: Ctx, msg: dict) -> None:
        message = self._require_message_member(_req_int(msg, 'msg_id'), ctx.username)
        emoji = _req_str(msg, 'emoji', 16, label='이모지')
        if message['deleted'] or message['kind'] == 'system':
            raise ProtocolError('이 메시지에는 공감할 수 없습니다.')
        current = message.get('reactions') or {}
        if emoji not in current and len(current) >= MAX_REACTION_KINDS:
            raise ProtocolError(f'공감은 메시지 하나에 {MAX_REACTION_KINDS}종류까지 달 수 있습니다. 이미 달린 공감을 누르면 함께 공감할 수 있습니다.')
        updated = self.store.toggle_reaction(message['msg_id'], ctx.username, emoji)
        self._push_msg_updated(updated, ctx)

    def _h_delete(self, ctx: Ctx, msg: dict) -> None:
        message = self._require_message_member(_req_int(msg, 'msg_id'), ctx.username)
        if message['sender'] != ctx.username:
            raise ProtocolError('본인이 보낸 메시지만 삭제할 수 있습니다.')
        if message['deleted']:
            raise ProtocolError('이미 삭제된 메시지입니다.')
        sent = datetime.strptime(message['timestamp'], ISO_FMT)
        if datetime.now() - sent > DELETE_WINDOW:
            raise ProtocolError('보낸 지 24시간이 지난 메시지는 모두에게서 삭제할 수 없습니다. 나에게서 삭제는 할 수 있습니다.')
        updated = self.store.delete_message(message['msg_id'])
        self._push_msg_updated(updated, ctx)
        if self.rag is not None and hasattr(self.rag, 'remove_message'):
            self._rag_queue.put(lambda: self.rag.remove_message(updated['msg_id']))

    def _h_edit(self, ctx: Ctx, msg: dict) -> None:
        """메시지 수정 (카카오톡 2025-09 개편) - 본인 텍스트 메시지, 24시간 이내"""
        message = self._require_message_member(_req_int(msg, 'msg_id'), ctx.username)
        if message['sender'] != ctx.username:
            raise ProtocolError('본인이 보낸 메시지만 수정할 수 있습니다.')
        if message['deleted']:
            raise ProtocolError('삭제된 메시지는 수정할 수 없습니다.')
        if message['kind'] != 'text':
            raise ProtocolError('텍스트 메시지만 수정할 수 있습니다.')
        content = msg.get('content')
        if not isinstance(content, str) or not content.strip():
            raise ProtocolError('수정할 내용을 입력하세요.')
        if len(content) > MAX_CONTENT_LEN:
            raise ProtocolError(f'메시지는 {MAX_CONTENT_LEN}자를 넘을 수 없습니다.')
        sent = datetime.strptime(message['timestamp'], ISO_FMT)
        if datetime.now() - sent > DELETE_WINDOW:
            raise ProtocolError('보낸 지 24시간이 지난 메시지는 수정할 수 없습니다.')
        if content == message['content']:
            self._reply(ctx, {'type': 'msg_updated', 'message': message})
            return
        updated = self.store.edit_message(message['msg_id'], content)
        self._push_msg_updated(updated, ctx)
        if self.rag is not None and hasattr(self.rag, 'remove_message'):
            self._rag_queue.put(lambda: (self.rag.remove_message(updated['msg_id']),
                                         self.rag.index_message(updated)))
        self._queue_link_preview(updated)

    def _h_notice_set(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        msg_id = _opt_int(msg, 'msg_id')
        if msg_id is not None:
            target = self.store.get_message(msg_id)
            if target is None or target['room_id'] != meta['room_id']:
                raise ProtocolError('공지로 등록할 메시지를 찾을 수 없습니다.')
            if target['deleted'] or target['kind'] == 'system':
                raise ProtocolError('이 메시지는 공지로 등록할 수 없습니다.')
        self.store.set_notice(meta['room_id'], msg_id)
        self._push_room_updated(meta['room_id'], meta['members'], ctx)
        if msg_id is not None:
            self._post_system(meta['room_id'], f'{self.store.display_name(ctx.username)}님이 공지를 등록했습니다.')

    def _h_search(self, ctx: Ctx, msg: dict) -> None:
        query = _req_str(msg, 'query', 100, label='검색어')
        room_id = msg.get('room_id')
        if room_id is not None:
            self._require_room_member(room_id, ctx.username)
        messages = self.store.search(ctx.username, query, room_id)
        self._reply(ctx, {'type': 'search_result', 'query': query, 'room_id': room_id, 'messages': messages})

    # ------------------------------------------------------------------ 투표
    def _h_poll_create(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        self._require_not_secret(meta)
        question = _req_str(msg, 'question', 200, label='질문')
        options = msg.get('options')
        if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
            raise ProtocolError('options 값이 올바르지 않습니다.')
        options = [o.strip() for o in options]
        if any(not o for o in options):
            raise ProtocolError('빈 항목은 사용할 수 없습니다.')
        if len(options) < 2:
            raise ProtocolError('투표 항목은 2개 이상이어야 합니다.')
        if len(options) > 20 or any(len(o) > 100 for o in options):
            raise ProtocolError('투표 항목이 너무 많거나 깁니다.')
        multiple = _bool(msg, 'multiple')
        message = self.store.create_poll(meta['room_id'], ctx.username, question, options, multiple)
        self._publish_new_message(message, ctx)

    def _require_poll(self, poll_id: int, username: str) -> dict:
        poll = self.store.poll_meta(poll_id)
        if poll is None:
            raise ProtocolError('존재하지 않는 투표입니다.')
        if not self.store.is_member(poll['room_id'], username):
            raise ProtocolError('이 채팅방의 대화상대가 아닙니다. 초대를 받은 뒤 이용할 수 있습니다.')
        return poll

    def _h_poll_vote(self, ctx: Ctx, msg: dict) -> None:
        poll = self._require_poll(_req_int(msg, 'poll_id'), ctx.username)
        if poll['closed']:
            raise ProtocolError('마감된 투표입니다.')
        indexes = msg.get('option_indexes')
        if not isinstance(indexes, list) or not all(isinstance(i, int) and not isinstance(i, bool)
                                                    for i in indexes):
            raise ProtocolError('option_indexes 값이 올바르지 않습니다.')
        indexes = sorted(set(indexes))
        if any(i < 0 or i >= poll['option_count'] for i in indexes):
            raise ProtocolError('존재하지 않는 투표 항목입니다.')
        if not poll['multiple'] and len(indexes) > 1:
            raise ProtocolError('하나의 항목만 선택할 수 있습니다.')
        updated = self.store.vote(poll['poll_id'], ctx.username, indexes)
        self._push_msg_updated(updated, ctx)

    def _h_poll_close(self, ctx: Ctx, msg: dict) -> None:
        poll = self._require_poll(_req_int(msg, 'poll_id'), ctx.username)
        if poll['creator'] != ctx.username:
            raise ProtocolError('투표를 만든 사람만 마감할 수 있습니다.')
        if poll['closed']:
            raise ProtocolError('이미 마감된 투표입니다.')
        updated = self.store.close_poll(poll['poll_id'])
        self._push_msg_updated(updated, ctx)

    # ------------------------------------------------------------------ 일정
    @staticmethod
    def _related(event: dict) -> set[str]:
        return {event['creator'], *event['attendees'].keys()}

    def _event_fields(self, msg: dict, partial: bool) -> dict:
        fields: dict = {}
        if not partial or 'title' in msg:
            fields['title'] = _req_str(msg, 'title', 100, label='일정 제목')
        if not partial or 'start' in msg:
            fields['start'] = _norm_iso(msg.get('start'), 'start')
        if not partial or 'end' in msg:
            fields['end'] = _norm_iso(msg.get('end'), 'end')
        if not partial or 'all_day' in msg:
            fields['all_day'] = _bool(msg, 'all_day')
        if not partial or 'description' in msg:
            fields['description'] = _opt_str(msg, 'description', 2000)
        if not partial or 'location' in msg:
            fields['location'] = _opt_str(msg, 'location', 200)
        if not partial or 'remind_minutes' in msg:
            remind = _opt_int(msg, 'remind_minutes')
            if remind is not None and not 0 <= remind <= 60 * 24 * 30:
                raise ProtocolError('알림 시간이 올바르지 않습니다.')
            fields['remind_minutes'] = remind
        if not partial or 'color' in msg:
            color = msg.get('color')
            if color is None:
                color = DEFAULT_EVENT_COLOR
            if not isinstance(color, str) or not COLOR_RE.match(color):
                raise ProtocolError('색상은 #RRGGBB 형식이어야 합니다.')
            fields['color'] = color.upper()
        return fields

    def _h_event_create(self, ctx: Ctx, msg: dict) -> None:
        fields = self._event_fields(msg, partial=False)
        if fields['end'] < fields['start']:
            raise ProtocolError('종료 시각이 시작 시각보다 빠릅니다.')
        room_id = msg.get('room_id')
        if room_id is not None:
            meta = self._require_room_member(room_id, ctx.username)
            self._require_not_secret(meta)
            attendees = meta['members']
        else:
            attendees = _str_list(msg, 'attendees', required=False)
            self._require_users_exist(attendees)
        event, message = self.store.create_event(ctx.username, fields, attendees, room_id)
        if message is not None:
            self._publish_new_message(message)
        self._push(self._related(event), {'type': 'event_updated', 'event': event}, ctx)

    def _require_event(self, event_id: int) -> dict:
        event = self.store.get_event(event_id)
        if event is None:
            raise ProtocolError('존재하지 않는 일정입니다.')
        return event

    def _h_event_update(self, ctx: Ctx, msg: dict) -> None:
        event = self._require_event(_req_int(msg, 'event_id'))
        if event['creator'] != ctx.username:
            raise ProtocolError('일정을 만든 사람만 수정할 수 있습니다.')
        fields = self._event_fields(msg, partial=True)
        start = fields.get('start', event['start'])
        end = fields.get('end', event['end'])
        if end < start:
            raise ProtocolError('종료 시각이 시작 시각보다 빠릅니다.')
        updated = self.store.update_event(event['event_id'], fields)
        self._push(self._related(updated), {'type': 'event_updated', 'event': updated}, ctx)

    def _h_event_delete(self, ctx: Ctx, msg: dict) -> None:
        event = self._require_event(_req_int(msg, 'event_id'))
        if event['creator'] != ctx.username:
            raise ProtocolError('일정을 만든 사람만 삭제할 수 있습니다.')
        self.store.delete_event(event['event_id'])
        self._push(self._related(event), {'type': 'event_deleted', 'event_id': event['event_id']}, ctx)

    def _h_event_rsvp(self, ctx: Ctx, msg: dict) -> None:
        event = self._require_event(_req_int(msg, 'event_id'))
        response = msg.get('response')
        if response not in RSVP_RESPONSES:
            raise ProtocolError('응답은 yes/no/maybe 중 하나여야 합니다.')
        if ctx.username not in event['attendees']:
            raise ProtocolError('일정 참석자가 아닙니다.')
        updated = self.store.rsvp(event['event_id'], ctx.username, response)
        self._push(self._related(updated), {'type': 'event_updated', 'event': updated}, ctx)

    def _h_event_list(self, ctx: Ctx, msg: dict) -> None:
        start = _norm_iso(msg.get('start'), 'start')
        end = _norm_iso(msg.get('end'), 'end')
        events = self.store.list_events(ctx.username, start, end)
        self._reply(ctx, {'type': 'event_list', 'start': msg.get('start'), 'end': msg.get('end'),
                          'events': events})

    # ------------------------------------------------------------------ 할 일
    def _require_todo(self, todo_id: int, username: str) -> dict:
        todo = self.store.get_todo(todo_id)
        if todo is None:
            raise ProtocolError('존재하지 않는 할 일입니다.')
        if todo['owner'] != username:
            raise ProtocolError('본인의 할 일만 변경할 수 있습니다.')
        return todo

    def _h_todo_create(self, ctx: Ctx, msg: dict) -> None:
        title = _req_str(msg, 'title', 200, label='할 일')
        todo = self.store.create_todo(ctx.username, title, _validate_due(msg.get('due')))
        self._push([ctx.username], {'type': 'todo_updated', 'todo': todo}, ctx)

    def _h_todo_update(self, ctx: Ctx, msg: dict) -> None:
        todo = self._require_todo(_req_int(msg, 'todo_id'), ctx.username)
        fields: dict = {}
        if 'title' in msg:
            fields['title'] = _req_str(msg, 'title', 200, label='할 일')
        if 'due' in msg:
            fields['due'] = _validate_due(msg.get('due'))
        if 'done' in msg:
            fields['done'] = _bool(msg, 'done')
        updated = self.store.update_todo(todo['todo_id'], fields)
        self._push([ctx.username], {'type': 'todo_updated', 'todo': updated}, ctx)

    def _h_todo_delete(self, ctx: Ctx, msg: dict) -> None:
        todo = self._require_todo(_req_int(msg, 'todo_id'), ctx.username)
        self.store.delete_todo(todo['todo_id'])
        self._push([ctx.username], {'type': 'todo_deleted', 'todo_id': todo['todo_id']}, ctx)

    def _h_todo_list(self, ctx: Ctx, msg: dict) -> None:
        self._reply(ctx, {'type': 'todo_list', 'todos': self.store.list_todos(ctx.username)})

    # ------------------------------------------------------------------ 프로필 / 첨부
    def _h_profile_update(self, ctx: Ctx, msg: dict) -> None:
        fields: dict = {}
        if msg.get('display_name') is not None:
            fields['display_name'] = _req_str(msg, 'display_name', 20, label='이름')
        if msg.get('status_message') is not None:
            fields['status_message'] = _req_str(msg, 'status_message', 60, allow_empty=True,
                                                label='상태메시지')
        if 'birthday' in msg:
            fields['birthday'] = _validate_birthday(msg.get('birthday'))
        if _bool(msg, 'avatar_clear'):
            fields['avatar_id'] = None
        elif msg.get('avatar_b64') is not None:
            data = _decode_b64(msg.get('avatar_b64'), MAX_AVATAR_BYTES, '프로필 사진은 512KB를 초과할 수 없습니다.')
            sniffed = _sniff_image(data)
            if sniffed is None:
                raise ProtocolError('프로필 사진은 이미지 파일(PNG/JPEG/GIF/BMP/WEBP)이어야 합니다.')
            mime, ext = sniffed
            fields['avatar_id'] = self.store.save_attachment(f'avatar.{ext}', mime, data, ctx.username)
        if 'mobile' in msg:
            mobile = (msg.get('mobile') or '').strip()
            if mobile and not (9 <= len(Store.phone_digits(mobile)) <= 13):
                raise ProtocolError('전화번호 형식이 올바르지 않습니다.')
            fields['mobile'] = mobile[:20]
        if 'email' in msg:
            email = (msg.get('email') or '').strip()
            if email and not EMAIL_RE.fullmatch(email):
                raise ProtocolError('이메일 형식이 올바르지 않습니다.')
            fields['email'] = email[:120]
        if not fields:
            raise ProtocolError('변경할 항목이 없습니다.')
        self.store.update_profile(ctx.username, fields)
        self._broadcast_user(ctx.username, ctx)

    # ------------------------------------------------------------------ 친구 등록
    def _h_friend_add(self, ctx: Ctx, msg: dict) -> None:
        """전화번호 또는 이메일로 친구 추가 (정확히 일치할 때만 - 목록 조회 방지)"""
        query = _req_str(msg, 'query', 120, label='전화번호 또는 이메일')
        if '@' in query and not EMAIL_RE.fullmatch(query.strip()):
            raise ProtocolError('이메일 형식이 올바르지 않습니다.')
        if '@' not in query and len(Store.phone_digits(query)) < 9:
            raise ProtocolError('전화번호를 정확히 입력해 주세요.')
        target = self.store.find_user_by_contact(query)
        if target is None:
            raise ProtocolError('해당 전화번호·이메일로 가입한 사용자가 없습니다. 상대가 프로필에 등록한 번호·이메일인지 확인하세요.')
        if target == ctx.username:
            raise ProtocolError('나 자신은 친구로 추가할 수 없습니다.')
        added = self.store.add_friend(ctx.username, target)
        base = self.store.get_user(target, self._online_users())
        user = self._apply_profile(base, self.store.profile_overrides_for_viewer(ctx.username).get(target))
        self._reply(ctx, {'type': 'friend_added', 'user': user, 'already': not added})
        self._reply(ctx, {'type': 'friend_list', 'friends': self.store.friends_of(ctx.username)})

    def _h_friend_remove(self, ctx: Ctx, msg: dict) -> None:
        self.store.remove_friend(ctx.username, _req_str(msg, 'username', 64, label='친구'))
        self._reply(ctx, {'type': 'friend_list', 'friends': self.store.friends_of(ctx.username)})

    def _h_friend_list(self, ctx: Ctx, msg: dict) -> None:
        self._reply(ctx, {'type': 'friend_list', 'friends': self.store.friends_of(ctx.username)})

    def _h_presence_set(self, ctx: Ctx, msg: dict) -> None:
        presence = msg.get('presence')
        if presence not in PRESENCES:
            raise ProtocolError('상태는 online/away/busy/meeting 중 하나여야 합니다.')
        self.store.update_profile(ctx.username, {'presence': presence})
        self._broadcast_user(ctx.username, ctx)

    def _h_attachment_get(self, ctx: Ctx, msg: dict) -> None:
        att = self.store.get_attachment_for(_req_int(msg, 'attachment_id'), ctx.username)
        if att is None:
            raise ProtocolError('첨부 파일을 찾을 수 없거나 접근 권한이 없습니다.')
        if att.get('expired'):
            raise ProtocolError(ATTACHMENT_EXPIRED)
        self._reply(ctx, {'type': 'attachment_data', 'attachment_id': att['attachment_id'],
                          'name': att['name'], 'mime': att['mime'],
                          'data_b64': base64.b64encode(att['data']).decode('ascii')})

    # ------------------------------------------------------------------ 스케줄러
    def _scheduler_loop(self) -> None:
        while not self._stop.wait(self.tick_seconds):
            try:
                self._run_scheduled()
                self._run_reminders()
                self._run_voiceroom_timeouts()
                self._run_story_expiry()
                self._run_retention()
            except Exception:
                if self._stop.is_set():
                    break
                logger.exception('스케줄러 오류')

    def _run_scheduled(self) -> None:
        for item in self.store.pop_due_scheduled(now_iso()):
            room_id, sender, p = item['room_id'], item['sender'], item['payload']
            if not self.store.is_member(room_id, sender):
                logger.info('예약 메시지 %s 취소: 발신자가 방을 나감', item['scheduled_id'])
                continue
            reply_to_id = p.get('reply_to_id')
            if reply_to_id is not None:
                orig = self.store.get_message(reply_to_id)
                if orig is None or orig['room_id'] != room_id:
                    reply_to_id = None
            members = set(self.store.members(room_id))
            mentions = [m for m in p.get('mentions', []) if m in members]
            self._deliver_message(room_id, sender, p['kind'], p['content'], reply_to_id, mentions,
                                  p.get('attachment_id'), p.get('client_tmp_id'), None,
                                  silent=bool(p.get('silent')))

    def _run_reminders(self) -> None:
        for event, minutes in self.store.due_reminders(datetime.now(), REMINDER_GRACE):
            targets = {u for u, r in event['attendees'].items() if r != 'no'}
            targets.add(event['creator'])
            self._push(targets, {'type': 'event_reminder', 'event': event, 'minutes_before': minutes})

    # ------------------------------------------------------------------ URL 미리보기
    def _queue_link_preview(self, message: dict) -> None:
        if not self.link_preview or message.get('kind') != 'text' or message.get('deleted'):
            return
        match = URL_RE.search(message.get('content') or '')
        if match:
            self._preview_queue.put({'msg_id': message['msg_id'], 'room_id': message['room_id'],
                                     'url': match.group(0)})

    def _preview_worker(self) -> None:
        while True:
            job = self._preview_queue.get()
            if job is None or self._stop.is_set():
                break
            try:
                preview = self.preview_fetcher(job['url'])
            except Exception:
                preview = None
            if not preview or self._stop.is_set():
                continue
            current = self.store.get_message(job['msg_id'])
            if current is None or current['deleted'] or job['url'] not in (current['content'] or ''):
                continue  # 그 사이 수정/삭제됨
            updated = self.store.set_link_preview(job['msg_id'], preview)
            if updated is not None:
                self._push_msg_updated(updated)

    # ------------------------------------------------------------------ 오늘의 브리핑 (선톡)
    def _send_briefing(self, username: str) -> None:
        """AI 비서가 그날 첫 접속한 사용자에게 먼저 보내는 요약 (카카오톡 '선톡 브리핑' 대응)"""
        if self._stop.is_set():
            return
        room_id, _members = self.store.get_or_create_direct(username, BOT_USERNAME)
        self._push_room_updated(room_id, [username])
        today = date.today()
        start = datetime(today.year, today.month, today.day)
        events = self.store.list_events(username, start.strftime(ISO_FMT),
                                        (start + timedelta(days=1)).strftime(ISO_FMT))
        pending = [e for e in self.store.list_events(username, start.strftime(ISO_FMT),
                                                     (start + timedelta(days=14)).strftime(ISO_FMT))
                   if e['attendees'].get(username) == 'pending']
        todos = [t for t in self.store.list_todos(username)
                 if not t['done'] and t.get('due') and t['due'] <= today.isoformat()]
        unread = self.store.unread_total(username)
        name = self.store.display_name(username)
        lines = [f'☀️ {name}님, 오늘의 브리핑이에요 ({today.month}월 {today.day}일)']
        if events:
            lines.append(f'📅 오늘 일정 {len(events)}개')
            for e in events[:5]:
                when = '종일' if e.get('all_day') else e['start'][11:16]
                lines.append(f"  · {when} {e['title']}")
        else:
            lines.append('📅 오늘 일정이 없어요')
        if pending:
            lines.append(f"🙋 참석 여부를 알려 주세요: {', '.join(e['title'] for e in pending[:3])}")
        if todos:
            lines.append(f"✅ 마감된 할 일 {len(todos)}개: {', '.join(t['title'] for t in todos[:3])}")
        if unread:
            lines.append(f'💬 안 읽은 메시지 {unread}개')
        lines.append('궁금한 건 언제든 저에게 물어보세요!')
        self._bot_reply(room_id, '\n'.join(lines))

    # ------------------------------------------------------------------ RAG (AI 비서)
    def _rag_worker(self) -> None:
        """RAG 작업(색인·답변·문서 학습)을 순서대로 처리하는 단일 워커."""
        while True:
            job = self._rag_queue.get()
            if job is None or self._stop.is_set():
                break
            try:
                job()
            except Exception:
                logger.exception('RAG 작업 오류')

    def _bot_reply(self, room_id: str, text: str) -> None:
        if self._stop.is_set() or not self.store.is_member(room_id, BOT_USERNAME):
            return
        message = self.store.add_message(room_id, BOT_USERNAME, 'text', text[:MAX_CONTENT_LEN])
        self._publish_new_message(message)

    def _after_user_message(self, message: dict) -> None:
        """사용자 메시지 저장 후: 색인 + 봇 트리거 판정 (실제 작업은 RAG 워커에서)."""
        sender = message['sender']
        if not sender or sender == BOT_USERNAME or message['kind'] == 'system':
            return
        room_id = message['room_id']
        meta = self.store.room_meta(room_id)
        if meta is None:
            return
        bot_in_room = BOT_USERNAME in meta['members']
        is_bot_direct = bot_in_room and meta['type'] == 'direct'

        if message['kind'] == 'text':
            self._queue_link_preview(message)
            if self.rag is not None:
                self._rag_queue.put(lambda: self.rag.index_message(message))
            mentioned = BOT_USERNAME in message['mentions'] or BOT_MENTION in message['content']
            if is_bot_direct or (bot_in_room and meta['type'] == 'group' and mentioned):
                self._rag_queue.put(lambda: self._rag_answer(message))
        elif message['kind'] in ('file', 'image') and is_bot_direct and message['attachment']:
            self._rag_queue.put(lambda: self._rag_learn(message))

    def _rag_answer(self, message: dict) -> None:
        room_id, asker = message['room_id'], message['sender']
        if self.rag is None:
            self._bot_reply(room_id, RAG_UNAVAILABLE)
            return
        question = message['content'].replace(BOT_MENTION, '').strip() or message['content']
        history, _ = self.store.history(room_id, None, RAG_HISTORY_LIMIT)
        try:
            answer = self.rag.answer(question, asker, self.store.room_ids_for_user(asker), history)
        except Exception:
            logger.exception('RAG 답변 생성 실패')
            answer = RAG_FAILED
        self._bot_reply(room_id, answer if isinstance(answer, str) and answer.strip() else RAG_FAILED)

    def _rag_learn(self, message: dict) -> None:
        room_id = message['room_id']
        if self.rag is None:
            self._bot_reply(room_id, RAG_UNAVAILABLE)
            return
        att = self.store.get_attachment(message['attachment']['attachment_id'])
        if att is None:
            return
        try:
            doc = self.rag.add_document(message['sender'], att['name'], att['data'], att['mime'])
        except ValueError as exc:
            self._bot_reply(room_id, str(exc) or RAG_FAILED)
            return
        except Exception:
            logger.exception('RAG 문서 학습 실패')
            self._bot_reply(room_id, RAG_FAILED)
            return
        self._bot_reply(room_id, f"📚 '{att['name']}' 문서를 학습했습니다 ({doc.get('chunks', 0)}개 조각)")

    def _require_rag(self) -> Any:
        if self.rag is None:
            raise ProtocolError(RAG_UNAVAILABLE)
        return self.rag

    def _h_rag_doc_list(self, ctx: Ctx, msg: dict) -> None:
        docs = self._require_rag().list_documents(ctx.username)
        self._reply(ctx, {'type': 'rag_doc_list', 'docs': docs})

    def _h_rag_doc_add(self, ctx: Ctx, msg: dict) -> None:
        rag = self._require_rag()
        name = _req_str(msg, 'name', 200, label='문서 이름')
        data = _decode_b64(msg.get('data_b64'), MAX_ATTACHMENT_BYTES, '문서는 10MB를 초과할 수 없습니다.')
        mime = _opt_str(msg, 'mime', 100, 'application/octet-stream') or 'application/octet-stream'
        try:
            doc = rag.add_document(ctx.username, name, data, mime)
        except ValueError as exc:
            raise ProtocolError(str(exc) or '문서를 추가할 수 없습니다.') from None
        self._reply(ctx, {'type': 'rag_doc_added', 'doc': doc})

    def _h_rag_doc_delete(self, ctx: Ctx, msg: dict) -> None:
        rag = self._require_rag()
        doc_id = _req_int(msg, 'doc_id')
        if not rag.delete_document(doc_id, ctx.username):
            raise ProtocolError('문서를 찾을 수 없거나 삭제 권한이 없습니다.')
        self._reply(ctx, {'type': 'rag_doc_deleted', 'doc_id': doc_id})

    # ================================================================== v3 (명세 §8)
    def _member_label(self, meta: dict, username: str) -> str:
        """시스템 메시지용 이름 - 오픈채팅은 닉네임, 그 외는 표시 이름."""
        if meta['type'] == 'open':
            nickname = self.store.member_nickname(meta['room_id'], username)
            if nickname:
                return nickname
        return self.store.display_name(username)

    # ------------------------------------------------------------------ 8.1 비밀채팅
    def _h_key_publish(self, ctx: Ctx, msg: dict) -> None:
        key_b64 = msg.get('public_key_b64')
        if not isinstance(key_b64, str):
            raise ProtocolError('공개키 형식이 올바르지 않습니다.')
        try:
            raw = base64.b64decode(key_b64, validate=True)
        except (binascii.Error, ValueError):
            raise ProtocolError('공개키 형식이 올바르지 않습니다.') from None
        if len(raw) != 32:
            raise ProtocolError('X25519 공개키는 32바이트여야 합니다.')
        self.store.set_public_key(ctx.username, key_b64)
        self._broadcast_user(ctx.username, ctx)

    def _h_room_open_secret(self, ctx: Ctx, msg: dict) -> None:
        target = _req_str(msg, 'target', 20, label='대상')
        if target == ctx.username:
            raise ProtocolError('나와의 비밀채팅은 만들 수 없습니다.')
        self._require_users_exist([target])
        if not self.store.public_key(target):
            raise ProtocolError(SECRET_PEER_NO_KEY)
        room_id, _added = self.store.get_or_create_direct(ctx.username, target, secret=True)
        self._push_room_updated(room_id, {ctx.username, target}, ctx)

    # ------------------------------------------------------------------ 8.2 통화
    def _calls_for_user(self, username: str, room_id: Optional[str] = None) -> list[dict]:
        rooms = set(self.store.room_ids_for_user(username))
        if room_id is not None:
            rooms &= {room_id}
        with self._calls_lock:
            return [c.to_dict() for c in self._calls.values() if c.room_id in rooms]

    def _get_call(self, call_id: int) -> Call:
        """_calls_lock 을 잡은 상태에서 호출."""
        call = self._calls.get(call_id)
        if call is None:
            raise ProtocolError(CALL_GONE)
        return call

    def _push_call(self, snapshot: dict, ctx: Optional[Ctx] = None) -> None:
        self._push(self.store.members(snapshot['room_id']), {'type': 'call_updated', 'call': snapshot}, ctx)

    def _h_call_start(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        mode = msg.get('mode')
        if mode not in CALL_MODES:
            raise ProtocolError('통화 종류는 voice/video/voiceroom 중 하나여야 합니다.')
        with self._calls_lock:
            if meta['room_id'] in self._room_calls:
                raise ProtocolError('이 채팅방에서 이미 통화 중입니다. 채팅방의 통화 카드에서 참여하기를 누르세요.')
            call = Call(call_id=self._next_call_id, room_id=meta['room_id'], mode=mode, host=ctx.username,
                        started_at=now_iso(), started_mono=time.monotonic())
            call.participants[ctx.username] = Call.new_participant('host', mode)
            call.joined.add(ctx.username)
            self._next_call_id += 1
            self._calls[call.call_id] = call
            self._room_calls[call.room_id] = call.call_id
            snapshot = call.to_dict()
        message = self.store.add_message(meta['room_id'], ctx.username, 'call', mode, call_id=snapshot['call_id'])
        self._publish_new_message(message)
        self._push_call(snapshot, ctx)

    def _h_call_join(self, ctx: Ctx, msg: dict) -> None:
        call_id = _req_int(msg, 'call_id')
        with self._calls_lock:
            call = self._get_call(call_id)
            if not self.store.is_member(call.room_id, ctx.username):
                raise ProtocolError('이 채팅방의 대화상대가 아닙니다. 초대를 받은 뒤 이용할 수 있습니다.')
            if ctx.username not in call.participants:
                if call.mode == 'video' and len(call.participants) >= MAX_VIDEO_PARTICIPANTS:
                    raise ProtocolError('페이스톡은 최대 10명까지 참여할 수 있습니다. 누군가 나간 뒤 다시 참여하세요.')
                if call.mode == 'voiceroom' and len(call.participants) >= MAX_VOICEROOM_PARTICIPANTS:
                    raise ProtocolError('보이스룸 정원(1500명)이 가득 찼습니다.')
                role = 'listener' if call.mode == 'voiceroom' else 'speaker'
                call.participants[ctx.username] = Call.new_participant(role, call.mode)
            call.joined.add(ctx.username)
            snapshot = call.to_dict()
        self._push_call(snapshot, ctx)

    def _remove_participant(self, call: Call, username: str) -> bool:
        """_calls_lock 안에서 호출. 통화가 끝나야 하면 레지스트리에서 빼고 True."""
        call.participants.pop(username, None)
        if not call.participants or (call.mode == 'voiceroom' and not call.has_host()):
            self._calls.pop(call.call_id, None)
            self._room_calls.pop(call.room_id, None)
            return True
        return False

    def _h_call_leave(self, ctx: Ctx, msg: dict) -> None:
        call_id = _req_int(msg, 'call_id')
        with self._calls_lock:
            call = self._get_call(call_id)
            if ctx.username not in call.participants:
                raise ProtocolError(CALL_NOT_PARTICIPANT)
            ended = self._remove_participant(call, ctx.username)
            snapshot = call.to_dict()
        if ended:
            self._finish_call(call, ctx)
        else:
            self._push_call(snapshot, ctx)

    def _leave_all_calls(self, username: str, room_id: Optional[str] = None) -> None:
        """접속 종료/방 나가기 시 그 사용자가 참여 중인 통화에서 뺀다."""
        updated: list[dict] = []
        ended: list[Call] = []
        with self._calls_lock:
            for call in list(self._calls.values()):
                if username not in call.participants or (room_id is not None and call.room_id != room_id):
                    continue
                if self._remove_participant(call, username):
                    ended.append(call)
                else:
                    updated.append(call.to_dict())
        for snapshot in updated:
            self._push_call(snapshot)
        for call in ended:
            self._finish_call(call)

    def _finish_call(self, call: Call, ctx: Optional[Ctx] = None) -> None:
        """레지스트리에서 이미 빠진 통화의 종료 알림 + 시스템 메시지."""
        if self._stop.is_set():
            return
        duration = max(0, int(time.monotonic() - call.started_mono))
        self.store.log_call(call.call_id, call.room_id, call.mode, call.host, call.started_at, duration,
                            sorted(call.joined))
        self._push(self.store.members(call.room_id), {'type': 'call_ended', 'call_id': call.call_id,
                                                       'room_id': call.room_id, 'duration_seconds': duration}, ctx)
        if call.mode == 'voiceroom':
            text = '보이스룸이 종료되었습니다'
        else:
            text = f'통화 종료 · {duration // 60}:{duration % 60:02d}'
        self._post_system(call.room_id, text)

    def _h_call_hand(self, ctx: Ctx, msg: dict) -> None:
        call_id = _req_int(msg, 'call_id')
        raised = _bool(msg, 'raised', default=True)
        with self._calls_lock:
            call = self._get_call(call_id)
            me = call.participants.get(ctx.username)
            if me is None:
                raise ProtocolError(CALL_NOT_PARTICIPANT)
            if call.mode != 'voiceroom' or me['role'] != 'listener':
                raise ProtocolError('보이스룸 청취자만 손을 들 수 있습니다.')
            me['hand'] = raised
            snapshot = call.to_dict()
        self._push_call(snapshot, ctx)

    def _h_call_role(self, ctx: Ctx, msg: dict) -> None:
        call_id = _req_int(msg, 'call_id')
        target = _req_str(msg, 'username', 20, label='대상')
        role = msg.get('role')
        if role not in CALL_ROLES:
            raise ProtocolError('역할은 host/speaker/listener 중 하나여야 합니다.')
        with self._calls_lock:
            call = self._get_call(call_id)
            me = call.participants.get(ctx.username)
            if me is None or me['role'] != 'host':
                raise ProtocolError('호스트만 역할을 바꿀 수 있습니다.')
            person = call.participants.get(target)
            if person is None:
                raise ProtocolError(CALL_NOT_PARTICIPANT)
            old = person['role']
            if old == 'host' and role != 'host' \
                    and sum(1 for p in call.participants.values() if p['role'] == 'host') <= 1:
                raise ProtocolError('호스트가 최소 1명 있어야 합니다.')
            if call.mode == 'voiceroom' and old == 'listener' and role != 'listener' \
                    and call.stage_count() >= MAX_VOICEROOM_SPEAKERS:
                raise ProtocolError('호스트와 스피커는 최대 10명까지 가능합니다.')
            person['role'] = role
            if role != 'listener':
                person['hand'] = False
            snapshot = call.to_dict()
        self._push_call(snapshot, ctx)

    def _h_call_state(self, ctx: Ctx, msg: dict) -> None:
        call_id = _req_int(msg, 'call_id')
        changes = {k: _bool(msg, k) for k in ('muted', 'video', 'screen') if msg.get(k) is not None}
        if not changes:
            raise ProtocolError('변경할 상태가 없습니다.')
        with self._calls_lock:
            call = self._get_call(call_id)
            me = call.participants.get(ctx.username)
            if me is None:
                raise ProtocolError(CALL_NOT_PARTICIPANT)
            me.update(changes)
            snapshot = call.to_dict()
        self._push_call(snapshot, ctx)

    def _h_call_media(self, ctx: Ctx, msg: dict) -> None:
        """미디어 프레임 중계 (저장 안 함). 참여자가 아니거나 보이스룸 청취자의 오디오는 조용히 버린다."""
        call_id = _req_int(msg, 'call_id')
        kind = msg.get('kind')
        if kind not in MEDIA_KINDS:
            raise ProtocolError('미디어 종류가 올바르지 않습니다.')
        seq = _req_int(msg, 'seq')
        data_b64 = msg.get('data_b64')
        if not isinstance(data_b64, str) or not data_b64 or len(data_b64) > MAX_MEDIA_B64:
            raise ProtocolError('미디어 데이터가 올바르지 않습니다.')
        codec = msg.get('codec')
        if kind == 'audio' and codec is not None and codec not in AUDIO_CODECS:
            raise ProtocolError('오디오 코덱은 pcm/zpcm 중 하나여야 합니다.')
        with self._calls_lock:
            call = self._calls.get(call_id)
            if call is None:
                return
            me = call.participants.get(ctx.username)
            if me is None:
                return
            if call.mode == 'voiceroom' and kind == 'audio' and me['role'] == 'listener':
                return
            targets = [u for u in call.participants if u != ctx.username]
        payload = {'type': 'call_media', 'call_id': call_id, 'from': ctx.username, 'kind': kind, 'seq': seq,
                   'data_b64': data_b64}
        if kind == 'audio':
            payload['codec'] = codec or 'pcm'
        self._deliver(self._user_conns(targets), payload)

    def _h_call_list(self, ctx: Ctx, msg: dict) -> None:
        room_id = msg.get('room_id')
        if room_id is not None:
            self._require_room_member(room_id, ctx.username)
        self._reply(ctx, {'type': 'call_list', 'calls': self._calls_for_user(ctx.username, room_id)})

    def _run_voiceroom_timeouts(self) -> None:
        now = time.monotonic()
        with self._calls_lock:
            expired = [c for c in self._calls.values()
                       if c.mode == 'voiceroom' and now - c.started_mono >= self.voiceroom_max_seconds]
            for call in expired:
                self._calls.pop(call.call_id, None)
                self._room_calls.pop(call.room_id, None)
        for call in expired:
            self._finish_call(call)

    # ------------------------------------------------------------------ 8.3 펑(스토리)
    def _h_story_post(self, ctx: Ctx, msg: dict) -> None:
        kind = msg.get('kind', 'text')
        if kind not in ('text', 'image'):
            raise ProtocolError('펑 종류는 text/image 중 하나여야 합니다.')
        content = _opt_str(msg, 'content', 500)
        bg_color = msg.get('bg_color') or DEFAULT_STORY_COLOR
        if not isinstance(bg_color, str) or not COLOR_RE.match(bg_color):
            raise ProtocolError('색상은 #RRGGBB 형식이어야 합니다.')
        attachment_id = None
        if kind == 'text':
            if not content:
                raise ProtocolError('펑 내용을 입력하세요.')
            if msg.get('attachment') is not None:
                raise ProtocolError('텍스트 펑에는 첨부 파일을 보낼 수 없습니다.')
        else:
            name, _mime, data = self._decode_attachment(msg.get('attachment'))
            sniffed = _sniff_image(data)
            if sniffed is None:
                raise ProtocolError('사진 펑은 이미지 파일(PNG/JPEG/GIF/BMP/WEBP)이어야 합니다.')
            attachment_id = self.store.save_attachment(name, sniffed[0], data, ctx.username)
        story = self.store.create_story(ctx.username, kind, content, attachment_id, bg_color.upper(),
                                        self.story_ttl_seconds)
        self._broadcast({'type': 'story_new', 'story': story}, ctx)

    def _h_story_list(self, ctx: Ctx, msg: dict) -> None:
        self._reply(ctx, {'type': 'story_list', 'stories': self.store.list_stories(ctx.username)})

    def _h_story_view(self, ctx: Ctx, msg: dict) -> None:
        story_id = _req_int(msg, 'story_id')
        story = self.store.get_story(story_id, ctx.username)
        if story is None:
            raise ProtocolError('존재하지 않거나 만료된 펑입니다.')
        if story['owner'] == ctx.username:
            self._reply(ctx, {'type': 'story_updated', 'story': story})
            return
        self.store.add_story_view(story_id, ctx.username)
        owner_view = self.store.get_story(story_id, story['owner'])
        if owner_view is not None:
            self._push([story['owner']], {'type': 'story_updated', 'story': owner_view})

    def _h_story_delete(self, ctx: Ctx, msg: dict) -> None:
        story_id = _req_int(msg, 'story_id')
        story = self.store.get_story(story_id, ctx.username)
        if story is None:
            raise ProtocolError('존재하지 않거나 만료된 펑입니다.')
        if story['owner'] != ctx.username:
            raise ProtocolError('본인의 펑만 삭제할 수 있습니다.')
        self.store.delete_story(story_id)
        self._broadcast({'type': 'story_deleted', 'story_id': story_id}, ctx)

    def _run_story_expiry(self) -> None:
        for story_id in self.store.pop_expired_stories():
            self._broadcast({'type': 'story_deleted', 'story_id': story_id})

    # ------------------------------------------------------------------ 8.5 멀티프로필
    def _h_multi_profile_set(self, ctx: Ctx, msg: dict) -> None:
        profiles = msg.get('profiles')
        if not isinstance(profiles, list) or not all(isinstance(p, dict) for p in profiles):
            raise ProtocolError('profiles 값이 올바르지 않습니다.')
        if len(profiles) > MAX_MULTI_PROFILES:
            raise ProtocolError(f'멀티프로필은 최대 {MAX_MULTI_PROFILES}개까지 만들 수 있습니다.')
        existing = {p['profile_id'] for p in self.store.list_multi_profiles(ctx.username)}
        seen_viewers: set[str] = set()
        cleaned: list[dict] = []
        for p in profiles:
            pid = _opt_int(p, 'profile_id')
            if pid is not None and pid not in existing:
                raise ProtocolError('존재하지 않는 멀티프로필입니다.')
            viewers = [v for v in _str_list(p, 'viewers', required=False)]
            if ctx.username in viewers:
                raise ProtocolError('나 자신은 멀티프로필 대상이 될 수 없습니다.')
            self._require_users_exist(viewers)
            if seen_viewers & set(viewers):
                raise ProtocolError('한 친구는 하나의 멀티프로필에만 지정할 수 있습니다.')
            seen_viewers |= set(viewers)
            item = {'profile_id': pid, 'name': _req_str(p, 'name', 20, label='프로필 이름'),
                    'display_name': _req_str(p, 'display_name', 20, label='이름'),
                    'status_message': _opt_str(p, 'status_message', 60), 'viewers': viewers}
            if _bool(p, 'avatar_clear'):
                item['avatar_id'] = None
            elif p.get('avatar_b64') is not None:
                data = _decode_b64(p.get('avatar_b64'), MAX_AVATAR_BYTES, '프로필 사진은 512KB를 초과할 수 없습니다.')
                sniffed = _sniff_image(data)
                if sniffed is None:
                    raise ProtocolError('프로필 사진은 이미지 파일(PNG/JPEG/GIF/BMP/WEBP)이어야 합니다.')
                item['avatar_data'] = (sniffed, data)
            else:
                item['avatar_keep'] = True
            cleaned.append(item)
        for item in cleaned:   # 검증이 모두 끝난 뒤에 사진 저장
            if 'avatar_data' in item:
                (mime, ext), data = item.pop('avatar_data')
                item['avatar_id'] = self.store.save_attachment(f'avatar.{ext}', mime, data, ctx.username)
        result = self.store.replace_multi_profiles(ctx.username, cleaned)
        self._reply(ctx, {'type': 'multi_profile_list', 'profiles': result})
        self._broadcast_user(ctx.username, exclude_user=ctx.username)

    def _h_multi_profile_list(self, ctx: Ctx, msg: dict) -> None:
        self._reply(ctx, {'type': 'multi_profile_list', 'profiles': self.store.list_multi_profiles(ctx.username)})

    # ------------------------------------------------------------------ 8.6 차단
    def _h_block_set(self, ctx: Ctx, msg: dict) -> None:
        target = _req_str(msg, 'username', 20, label='대상')
        if target == ctx.username:
            raise ProtocolError('나 자신은 차단할 수 없습니다.')
        if msg.get('blocked') is None:
            raise ProtocolError('blocked 값이 올바르지 않습니다.')
        blocked = _bool(msg, 'blocked')
        self._require_users_exist([target])
        self._reply(ctx, {'type': 'block_list', 'blocked': self.store.set_block(ctx.username, target, blocked)})

    # ------------------------------------------------------------------ 8.7 사다리 게임
    @staticmethod
    def _ladder_items(msg: dict, key: str) -> list[str]:
        value = msg.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ProtocolError(f'{key} 값이 올바르지 않습니다.')
        items = [v.strip() for v in value]
        if any(not v or len(v) > 30 for v in items):
            raise ProtocolError('사다리 항목은 1~30자여야 합니다.')
        return items

    def _h_ladder_create(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        self._require_not_secret(meta)
        participants = self._ladder_items(msg, 'participants')
        results = self._ladder_items(msg, 'results')
        if not LADDER_MIN <= len(participants) <= LADDER_MAX:
            raise ProtocolError('사다리 참가자는 2~10명이어야 합니다.')
        if len(participants) != len(results):
            raise ProtocolError('참가자와 결과의 개수가 같아야 합니다.')
        if len(set(participants)) != len(participants):
            raise ProtocolError('참가자 이름이 중복되었습니다.')
        rungs = generate_ladder_rungs(len(participants))
        ladder = {'participants': participants, 'results': results, 'rungs': rungs,
                  'mapping': compute_ladder_mapping(participants, results, rungs)}
        message = self.store.add_message(meta['room_id'], ctx.username, 'ladder', '사다리 게임', ladder=ladder)
        self._publish_new_message(message, ctx)

    # ------------------------------------------------------------------ 8.8 톡게시판
    def _require_post(self, post_id: int, username: str) -> dict:
        post = self.store.get_post(post_id)
        if post is None:
            raise ProtocolError('존재하지 않는 게시글입니다.')
        if not self.store.is_member(post['room_id'], username):
            raise ProtocolError('이 채팅방의 대화상대가 아닙니다. 초대를 받은 뒤 이용할 수 있습니다.')
        return post

    def _h_board_post(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        self._require_not_secret(meta)
        title = _req_str(msg, 'title', 100, label='제목')
        content = _opt_str(msg, 'content', MAX_CONTENT_LEN)
        post, message = self.store.create_post(meta['room_id'], ctx.username, title, content)
        self._publish_new_message(message)
        self._push(meta['members'], {'type': 'board_updated', 'post': post}, ctx)

    def _h_board_list(self, ctx: Ctx, msg: dict) -> None:
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        self._reply(ctx, {'type': 'board_list', 'room_id': meta['room_id'],
                          'posts': self.store.list_posts(meta['room_id'])})

    def _h_board_comment(self, ctx: Ctx, msg: dict) -> None:
        post = self._require_post(_req_int(msg, 'post_id'), ctx.username)
        content = _req_str(msg, 'content', 1000, label='댓글')
        updated = self.store.add_comment(post['post_id'], ctx.username, content)
        self._push(self.store.members(post['room_id']), {'type': 'board_updated', 'post': updated}, ctx)

    def _h_board_delete(self, ctx: Ctx, msg: dict) -> None:
        post = self._require_post(_req_int(msg, 'post_id'), ctx.username)
        if post['author'] != ctx.username:
            raise ProtocolError('작성자만 삭제할 수 있습니다.')
        message = self.store.delete_post(post['post_id'])
        if message is not None:
            self._push_msg_updated(message)
        self._push(self.store.members(post['room_id']),
                   {'type': 'board_deleted', 'post_id': post['post_id'], 'room_id': post['room_id']}, ctx)

    # ------------------------------------------------------------------ 8.9 오픈채팅
    def _h_open_room_create(self, ctx: Ctx, msg: dict) -> None:
        name = _req_str(msg, 'name', 50, label='채팅방 이름')
        description = _opt_str(msg, 'description', 500)
        tags = _str_list(msg, 'tags', required=False)
        if len(tags) > 10 or any(len(t) > 20 for t in tags):
            raise ProtocolError('태그는 20자 이하, 최대 10개까지 가능합니다.')
        nickname = _opt_str(msg, 'nickname', 20) or self.store.display_name(ctx.username)
        room_id = self.store.create_open_room(ctx.username, name, description, tags, nickname)
        self._push_room_updated(room_id, [ctx.username], ctx)

    def _h_open_room_search(self, ctx: Ctx, msg: dict) -> None:
        query = _opt_str(msg, 'query', 100)
        self._reply(ctx, {'type': 'open_room_search', 'query': query, 'rooms': self.store.search_open_rooms(query)})

    def _h_open_room_join(self, ctx: Ctx, msg: dict) -> None:
        room_id = msg.get('room_id')
        if not isinstance(room_id, str) or not room_id:
            raise ProtocolError('room_id 값이 올바르지 않습니다.')
        meta = self.store.room_meta(room_id)
        if meta is None or meta['type'] != 'open':
            raise ProtocolError('존재하지 않는 오픈채팅방입니다.')
        if ctx.username in meta['members']:
            raise ProtocolError('이미 참여한 오픈채팅방입니다.')
        nickname = _req_str(msg, 'nickname', 20, label='닉네임')
        self.store.join_open_room(room_id, ctx.username, nickname)
        self._push_room_updated(room_id, meta['members'] + [ctx.username], ctx)
        self._post_system(room_id, f'{nickname}님이 들어왔습니다')

    # ------------------------------------------------------------------ 8.10 보관 기간 / 톡서랍
    def _h_drawer_query(self, ctx: Ctx, msg: dict) -> None:
        kind = msg.get('kind')
        if kind not in ('image', 'file', 'link'):
            raise ProtocolError('서랍 종류는 image/file/link 중 하나여야 합니다.')
        limit = _opt_int(msg, 'limit')
        limit = 50 if limit is None else max(1, min(limit, MAX_DRAWER_LIMIT))
        self._reply(ctx, {'type': 'drawer_result', 'kind': kind,
                          'messages': self.store.drawer(ctx.username, kind, limit)})

    def _run_retention(self) -> None:
        for message in self.store.purge_expired_attachments():
            self._push_msg_updated(message)

    # ------------------------------------------------------------------ §9 v4 (2026 업데이트)
    def _summary_llm(self) -> Any:
        """요약용 Claude 클라이언트: RAG 서비스의 것을 재사용 (없거나 꺼져 있으면 None)"""
        getter = getattr(self.rag, '_llm', None)
        try:
            return getter() if getter else None
        except Exception:
            return None

    def _h_room_summary(self, ctx: Ctx, msg: dict) -> None:
        """채팅방 대화 요약. unread_only=True 면 내 읽음 위치 이후, since_msg_id 면 그 이후 메시지만"""
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        if meta['type'] == 'secret':
            raise ProtocolError('비밀채팅방의 대화는 서버가 읽을 수 없어 요약할 수 없습니다.')
        room_id = meta['room_id']
        unread_only = bool(msg.get('unread_only'))
        since = _opt_int(msg, 'since_msg_id')
        if unread_only and since is None:
            since = self.store.read_pointer(room_id, ctx.username)
        unread_only = unread_only or since is not None
        messages, _ = self.store.history(room_id, None, MAX_SUMMARY_MESSAGES, viewer=ctx.username,
                                         after_msg_id=since)          # '이후만'은 SQL 에서 거른다
        llm = self._summary_llm()

        def work() -> None:
            text, source = chat_summary.summarize(messages, self._name_of, llm, on_fatal=self._disable_summary_llm)
            self._reply(ctx, {'type': 'room_summary', 'room_id': room_id, 'summary': text, 'source': source,
                              'count': len(chat_summary._usable(messages)), 'unread_only': unread_only})

        if llm is None:              # 추출형은 몇 ms — 스레드 없이 바로
            work()
            return
        key = (ctx.username, room_id)
        with self._summary_lock:
            if key in self._summaries_running:      # 칩을 여러 번 눌러도 Claude 요약은 하나만
                return
            self._summaries_running.add(key)

        def run() -> None:
            try:
                work()
            finally:
                with self._summary_lock:
                    self._summaries_running.discard(key)

        self._spawn(run, name='room-summary')

    def _disable_summary_llm(self) -> None:
        """API 키 인증 실패: RAG 와 같은 표시를 세워 이후 요약·답변이 매번 실패 호출을 하지 않게"""
        if self.rag is not None:
            self.rag._llm_failed = True

    def _name_of(self, username: str) -> str:
        return self.store.display_name(username) if username else ''

    def _h_call_history(self, ctx: Ctx, msg: dict) -> None:
        limit = min(max(_opt_int(msg, 'limit') or 100, 1), MAX_CALL_HISTORY)
        calls = self.store.call_history(ctx.username, limit)
        for c in calls:
            c['joined'] = ctx.username in c['participants']
            c['missed'] = not c['joined']
        self._reply(ctx, {'type': 'call_history', 'calls': calls})

    def _h_room_export(self, ctx: Ctx, msg: dict) -> None:
        """대화 내보내기: 500개씩 읽고(저장소 잠금은 쪽마다) 2000개씩 여러 조각으로 보낸다.
        room_export {room_id, messages(이 조각, 오래된 순), part, done, truncated}"""
        meta = self._require_room_member(msg.get('room_id'), ctx.username)
        room_id = meta['room_id']
        messages, before, truncated = [], None, False
        while True:
            page, more = self.store.history(room_id, before, EXPORT_PAGE, viewer=ctx.username)
            messages = page + messages
            if not more or not page:
                break
            if len(messages) >= MAX_EXPORT_MESSAGES:
                truncated = True
                break
            before = page[0]['msg_id']
        messages = messages[-MAX_EXPORT_MESSAGES:]
        chunks = [messages[k:k + EXPORT_CHUNK] for k in range(0, len(messages), EXPORT_CHUNK)] or [[]]
        for part, chunk in enumerate(chunks):
            self._reply(ctx, {'type': 'room_export', 'room_id': room_id, 'messages': chunk, 'part': part,
                              'done': part == len(chunks) - 1, 'truncated': truncated})
