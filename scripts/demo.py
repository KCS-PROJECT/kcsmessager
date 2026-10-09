# -*- coding: utf-8 -*-
"""
KCS Talk 데모 - 명령 하나로 모든 기능을 바로 써 볼 수 있게 한다.

    python3 scripts/demo.py                      # 서버 + 데모 데이터 + 클라이언트 2개
    python3 scripts/demo.py --clients 3          # 클라이언트 3개
    python3 scripts/demo.py --users 홍길동,김철수   # 사용할 사용자 지정
    python3 scripts/demo.py --headless-check     # GUI 없이 시드 → 기능별 ✓/✗ 표 (실패 시 종료 코드 1)

동작
  1. 임시 폴더에 DB를 만든다. server_data/org.json 이 있으면 복사해 실제 조직도로, 없으면 기본 데모 사용자로 시작
  2. 빈 포트에 KakaoServer 실행 (오늘의 브리핑 켬, URL 미리보기 끔)
  3. 실제 클라이언트 연결(NDJSON)로 데모 데이터 시드: 그룹방(텍스트·수정·조용히·답장·공감·공지·투표·사다리·
     게시판·일정·사진·파일·링크), 비밀채팅 1:1, 오픈채팅방, 펑, 할 일, 멀티프로필, 각 사용자 채팅방 폴더
  4. client/kakao/app.py 를 사용자별로 실행하고 Ctrl+C 까지 서버 유지 (종료 시 자식 프로세스 정리)

클라이언트들은 임시 홈(KCS_MESSENGER_HOME, HOME)을 쓰므로 실제 ~/.kcs_messenger 설정·키는 건드리지 않는다.
"""

import argparse
import base64
import itertools
import json
import os
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zlib
from collections import namedtuple
from datetime import datetime, date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ORG_SOURCE = os.path.join(ROOT, 'server_data', 'org.json')
APP_PATH = os.path.join(ROOT, 'client', 'kakao', 'app.py')
DEMO_USERS = ['홍길동', '김철수', '이영희', '박민수', '최지우']
BOT = 'AI 비서'
TIMEOUT = 5.0

Check = namedtuple('Check', 'name ok detail')
_req_ids = itertools.count(1)


class DemoError(Exception):
    """서버가 error 로 답했거나 응답이 오지 않음"""


# ================================================================ NDJSON 클라이언트
class DemoClient:
    """시드/검증용 실제 소켓 클라이언트. 받은 메시지는 버퍼에 쌓고 조건으로 꺼낸다."""

    def __init__(self, port, username, host='127.0.0.1'):
        self.username = username
        self.sock = socket.create_connection((host, port), timeout=TIMEOUT)
        self.sock.settimeout(None)
        self.buffer = []
        self.cond = threading.Condition()
        self.closed = False
        threading.Thread(target=self._read_loop, daemon=True).start()
        self.welcome = self.request({'type': 'join', 'username': username}, 'welcome')

    def _read_loop(self):
        data = b''
        try:
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                while b'\n' in data:
                    line, data = data.split(b'\n', 1)
                    if line.strip():
                        try:
                            msg = json.loads(line.decode('utf-8'))
                        except ValueError:
                            continue
                        with self.cond:
                            self.buffer.append(msg)
                            self.cond.notify_all()
        except OSError:
            pass
        finally:
            with self.cond:
                self.closed = True
                self.cond.notify_all()

    def send(self, payload):
        self.sock.sendall((json.dumps(payload, ensure_ascii=False) + '\n').encode('utf-8'))

    def wait_for(self, mtype, predicate=None, timeout=TIMEOUT, req_id=None):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for i, msg in enumerate(self.buffer):
                    if req_id is not None and msg.get('type') == 'error' and msg.get('req_id') == req_id:
                        self.buffer.pop(i)
                        raise DemoError(msg.get('message') or '서버 오류')
                    if msg.get('type') == mtype and (predicate is None or predicate(msg)):
                        return self.buffer.pop(i)
                remaining = deadline - time.monotonic()
                if remaining <= 0 or self.closed:
                    raise DemoError(f'{mtype} 응답이 없습니다' + (' (연결 끊김)' if self.closed else ''))
                self.cond.wait(remaining)

    def request(self, payload, mtype, predicate=None, timeout=TIMEOUT):
        req_id = f'demo{next(_req_ids)}'
        self.send(dict(payload, req_id=req_id))
        return self.wait_for(mtype, predicate, timeout, req_id=req_id)

    def send_message(self, room_id, kind='text', content='', **extra):
        tmp = f'tmp{next(_req_ids)}'
        payload = {'type': 'send', 'room_id': room_id, 'kind': kind, 'content': content, 'client_tmp_id': tmp}
        payload.update(extra)
        return self.request(payload, 'msg_new', lambda m: m.get('client_tmp_id') == tmp)['message']

    def history(self, room_id, limit=200):
        return self.request({'type': 'history', 'room_id': room_id, 'limit': limit}, 'history',
                            lambda m: m.get('room_id') == room_id)['messages']

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()


# ================================================================ 준비
def default_users(org_path=ORG_SOURCE, count=3):
    """org.json 이 있으면 앞쪽 사용자들(봇 제외), 없으면 기본 데모 사용자"""
    try:
        with open(org_path, encoding='utf-8') as f:
            org = json.load(f)
        names = [u['username'] for u in org.get('users', []) if u.get('username') and u['username'] != BOT
                 and not u.get('is_bot')]
        if names:
            return names[:count]
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return DEMO_USERS[:count]


def prepare_db_dir(db_dir, org_source=ORG_SOURCE):
    """임시 DB 폴더를 만들고 org.json 이 있으면 복사(서버는 <db 폴더>/org.json 을 읽는다)"""
    os.makedirs(db_dir, exist_ok=True)
    if org_source and os.path.exists(org_source):
        shutil.copy2(org_source, os.path.join(db_dir, 'org.json'))
    return db_dir


def settings_dir(home):
    """클라이언트가 쓰는 설정 폴더 (HOME=home 이면 ~/.kcs_messenger 와 같다)"""
    return os.path.join(home, '.kcs_messenger')


def write_client_settings(home, username, folders, pinned=(), **extra):
    """사용자 설정 JSON(LocalSettings 형식)에 채팅방 폴더·고정 방 등을 기록"""
    base = settings_dir(home)
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f'{username}.json')
    data = {}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        pass
    data['chat_folders'] = list(folders)
    data['pinned_rooms'] = list(pinned)
    data.update(extra)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def start_server(db_path, port=0, rag_off=False):
    os.environ.setdefault('KCS_LINK_PREVIEW', 'off')
    from server.kakao.server import KakaoServer
    kwargs = dict(port=port, db_path=db_path, tick_seconds=0.5, daily_briefing=True, link_preview=False)
    if rag_off:
        kwargs['rag_factory'] = _no_rag
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    server = KakaoServer(**kwargs)
    server.serve_in_thread()
    return server


def _no_rag(_path):
    raise ImportError('데모 테스트: RAG 사용 안 함')


def demo_png(width=240, height=160):
    """그라데이션 + 줄무늬 데모 PNG (Qt 없이 생성)"""
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            band = ((x + y) // 20) % 2
            row += bytes((42 + x * 150 // width, 56 + y * 120 // height + band * 20, 108 + band * 60))
        rows.append(bytes(row))
    raw = zlib.compress(b''.join(rows), 9)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', raw) + chunk(b'IEND', b''))


def _b64(data):
    return base64.b64encode(data).decode('ascii')


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


# ================================================================ 시드
def seed(port, users, home, quiet=False):
    """데모 데이터 생성. report = {'rooms': {...}, 'ids': {...}, 'errors': {단계: 사유}}"""
    report = {'rooms': {}, 'ids': {}, 'errors': {}, 'users': list(users)}
    log = (lambda *_a: None) if quiet else (lambda text: print(f'  · {text}', flush=True))
    users = list(dict.fromkeys(users))
    if len(users) < 2:
        raise ValueError('데모에는 사용자가 2명 이상 필요합니다.')
    A, B = users[0], users[1]
    C = users[2] if len(users) > 2 else None
    clients = {}

    def step(name, fn):
        try:
            fn()
            log(f'{name} ✓')
        except Exception as e:  # 한 단계가 실패해도(서버 미지원 등) 나머지는 계속
            report['errors'][name] = f'{e.__class__.__name__}: {e}' if not isinstance(e, DemoError) else str(e)
            log(f'{name} ✗ ({report["errors"][name]})')

    for u in users:
        clients[u] = DemoClient(port, u)
    a, b = clients[A], clients[B]
    c = clients.get(C)
    rooms, ids = report['rooms'], report['ids']
    keyrings = {}

    def keys():
        from client.kakao.secret import SecretKeyring
        kdir = os.path.join(settings_dir(home), 'keys')
        for u, cl in clients.items():
            keyrings[u] = SecretKeyring(u, directory=kdir)
            cl.send({'type': 'key_publish', 'public_key_b64': keyrings[u].public_key_b64})
        for u, cl in clients.items():
            cl.wait_for('user_updated', lambda m, u=u: m['user'].get('username') == u and m['user'].get('public_key'))
    step('비밀채팅 키', keys)

    def group():
        members = [B] + ([C] if C else [])
        room = a.request({'type': 'room_create', 'name': 'KCS Talk 데모방', 'members': members}, 'room_updated',
                         lambda m: m['room']['type'] == 'group' and m['room']['name'] == 'KCS Talk 데모방')['room']
        rooms['group'] = room['room_id']
        for cl in clients.values():
            if cl is not a:
                cl.wait_for('room_updated', lambda m: m['room']['room_id'] == room['room_id'])
    step('그룹 채팅', group)
    g = rooms.get('group')

    def texts():
        b.send_message(g, content='안녕하세요! KCS Talk 데모방입니다 👋')
        link = a.send_message(g, content='오늘 회의 자료는 https://example.com/kcs-talk 에 올려 두었어요')
        ids['link'] = link['msg_id']
        (c or b).send_message(g, content='확인했습니다. 회의 전에 읽어 볼게요')
        b.send_message(g, kind='emoticon', content='🎉')
    step('텍스트 메시지', texts)

    def edit():
        m = a.send_message(g, content='회의는 2시에 시작합니다')
        a.request({'type': 'edit', 'msg_id': m['msg_id'], 'content': '회의는 3시에 시작합니다 (시간 변경)'},
                  'msg_updated', lambda x: x['message']['msg_id'] == m['msg_id'])
        ids['edited'] = m['msg_id']
    step('메시지 수정', edit)

    def silent():
        ids['silent'] = b.send_message(g, content='늦은 시간이라 조용히 보내요 🌙', silent=True)['msg_id']
    step('조용히 보내기', silent)

    def reply():
        who = c or b
        m = who.send_message(g, content=f'@{A} 자료 잘 받았어요! 3시에 뵐게요', reply_to_id=ids['link'], mentions=[A])
        ids['reply'] = m['msg_id']
    step('답장', reply)

    def reactions():
        for cl, emoji in ((b, '👍'), (c, '👍'), (a, '❤️')):
            if cl is None:
                continue
            target = ids['link'] if cl is not a else ids.get('reply', ids['link'])
            cl.request({'type': 'react', 'msg_id': target, 'emoji': emoji}, 'msg_updated',
                       lambda m, t=target: m['message']['msg_id'] == t)
    step('공감', reactions)

    def notice():
        a.request({'type': 'notice_set', 'room_id': g, 'msg_id': ids['link']}, 'room_updated',
                  lambda m: m['room']['room_id'] == g and m['room'].get('notice'))
    step('공지', notice)

    def poll():
        a.send({'type': 'poll_create', 'room_id': g, 'question': '회의 후 점심 메뉴는?',
                'options': ['김치찌개', '돈까스', '샐러드'], 'multiple': False})
        m = a.wait_for('msg_new', lambda x: x['message']['kind'] == 'poll' and x['message']['room_id'] == g)['message']
        pid = m['poll']['poll_id']
        ids['poll'] = m['msg_id']
        for cl, idx in ((b, 1), (c, 0), (a, 1)):
            if cl is not None:
                cl.request({'type': 'poll_vote', 'poll_id': pid, 'option_indexes': [idx]}, 'msg_updated',
                           lambda x: x['message']['msg_id'] == m['msg_id'])
    step('투표', poll)

    def ladder():
        people = [A, B] + ([C] if C else [])
        results = ['커피 쏘기'] + ['통과'] * (len(people) - 1)
        m = a.request({'type': 'ladder_create', 'room_id': g, 'participants': people, 'results': results},
                      'msg_new', lambda x: x['message']['kind'] == 'ladder')['message']
        ids['ladder'] = m['msg_id']
    step('사다리 게임', ladder)

    def board():
        post = b.request({'type': 'board_post', 'room_id': g, 'title': '10월 업무 공유',
                          'content': '1. 데모 준비\n2. 회의록 정리\n3. 배포 일정 확인'}, 'board_updated')['post']
        (c or a).request({'type': 'board_comment', 'post_id': post['post_id'], 'content': '좋아요, 2번은 제가 할게요'},
                         'board_updated', lambda x: x['post']['post_id'] == post['post_id'])
        ids['board'] = post['post_id']
    step('톡게시판', board)

    def event():
        start = datetime.combine(date.today() + timedelta(days=1), datetime.min.time()) + timedelta(hours=15)
        ev = a.request({'type': 'event_create', 'room_id': g, 'title': '주간 회의', 'description': '안건: 데모 리뷰',
                        'location': '3층 회의실', 'start': _iso(start), 'end': _iso(start + timedelta(hours=1)),
                        'remind_minutes': 10, 'color': '#4CB6F2'}, 'event_updated')['event']
        ids['event'] = ev['event_id']
        b.request({'type': 'event_rsvp', 'event_id': ev['event_id'], 'response': 'yes'}, 'event_updated',
                  lambda x: x['event']['event_id'] == ev['event_id'])
        a.request({'type': 'event_create', 'title': '데모 발표', 'start': _iso(datetime.now() + timedelta(hours=2)),
                   'end': _iso(datetime.now() + timedelta(hours=3))}, 'event_updated')
    step('일정 공유', event)

    def photo():
        b.send_message(g, kind='image', content='demo_chart.png',
                       attachment={'name': 'demo_chart.png', 'mime': 'image/png', 'data_b64': _b64(demo_png())})
    step('사진', photo)

    def file():
        text = 'KCS Talk 데모 안내\n- 채팅 탭 ＃ 버튼: 오픈채팅\n- 서랍 버튼: 톡서랍\n- 더보기 → 기능 둘러보기\n'
        a.send_message(g, kind='file', content='KCS_Talk_안내.txt',
                       attachment={'name': 'KCS_Talk_안내.txt', 'mime': 'text/plain', 'data_b64': _b64(text.encode('utf-8'))})
    step('파일', file)

    def direct():
        room = a.request({'type': 'room_open_direct', 'target': B}, 'room_updated',
                         lambda m: m['room']['type'] == 'direct' and set(m['room']['members']) == {A, B})['room']
        rooms['direct'] = room['room_id']
        a.send_message(room['room_id'], content='오늘 데모 준비 다 됐어요?')
        b.send_message(room['room_id'], content='네! 거의 다 됐어요. 톡서랍이랑 오픈채팅도 확인해 보세요 😀')
        b.send_message(room['room_id'], content='링크도 하나 드려요 https://www.kakaocorp.com')
    step('1:1 채팅', direct)

    def secret():
        room = a.request({'type': 'room_open_secret', 'target': B}, 'room_updated',
                         lambda m: m['room']['type'] == 'secret')['room']
        rid = rooms['secret'] = room['room_id']
        a.send_message(rid, kind='secret',
                       content=keyrings[A].encrypt(rid, keyrings[B].public_key_b64, '이 대화는 우리 PC에서만 보여요 🔒'))
        b.send_message(rid, kind='secret',
                       content=keyrings[B].encrypt(rid, keyrings[A].public_key_b64, '서버도 못 읽는 비밀채팅이네요!'))
    step('비밀채팅', secret)

    def open_chat():
        room = a.request({'type': 'open_room_create', 'name': 'KCS 개발자 오픈채팅', 'description': 'PyQt·서버·AI 이야기',
                          'tags': ['개발', '파이썬', 'KCS']}, 'room_updated',
                         lambda m: m['room']['type'] == 'open')['room']
        rid = rooms['open'] = room['room_id']
        for cl, nick in ((b, '파이썬러버'), (c, '서버장인')):
            if cl is not None:
                cl.request({'type': 'open_room_join', 'room_id': rid, 'nickname': nick}, 'room_updated',
                           lambda m: m['room']['room_id'] == rid)
        a.send_message(rid, content='오픈채팅에 오신 걸 환영합니다! 닉네임으로 대화해요')
        b.send_message(rid, content='반가워요 🙌')
    step('오픈채팅', open_chat)

    def stories():
        a.request({'type': 'story_post', 'kind': 'text', 'content': '오늘도 화이팅! 💪', 'bg_color': '#2A386C'}, 'story_new')
        b.request({'type': 'story_post', 'kind': 'image', 'content': '데모 차트',
                   'attachment': {'name': 'story.png', 'mime': 'image/png', 'data_b64': _b64(demo_png(180, 320))}},
                  'story_new')
    step('펑', stories)

    def todos():
        for cl, title, due in ((a, '데모 자료 정리', date.today()), (a, '회의록 작성', date.today() + timedelta(days=1)),
                               (b, '배포 체크리스트 확인', date.today())):
            cl.request({'type': 'todo_create', 'title': title, 'due': due.isoformat()}, 'todo_updated')
    step('할 일', todos)

    def multi_profile():
        a.request({'type': 'multi_profile_set', 'profiles': [
            {'name': '회사용', 'display_name': f'{A} (업무)', 'status_message': '업무 시간에는 회사 프로필',
             'viewers': [B]}]}, 'multi_profile_list')
    step('멀티프로필', multi_profile)

    def folders():
        work = [r for r in (rooms.get('group'), rooms.get('open')) if r]
        for u in users:
            write_client_settings(home, u, [{'name': '업무', 'room_ids': work},
                                            {'name': '개인', 'room_ids': [r for r in (rooms.get('direct'),
                                                                                     rooms.get('secret')) if r]}],
                                  pinned=[rooms['group']] if rooms.get('group') else [])
    step('채팅방 폴더', folders)

    time.sleep(0.3)   # 브리핑(백그라운드) 등 마무리
    for cl in clients.values():
        cl.close()
    return report


# ================================================================ 검증
def verify(port, users, report, home):
    """새 연결로 접속해 각 기능의 데이터가 서버에 남았는지 확인 → [Check]"""
    A, B = users[0], users[1]
    rooms, errors = report['rooms'], report['errors']
    checks = []
    a = DemoClient(port, A)
    b = DemoClient(port, B)
    by_id = {r['room_id']: r for r in a.welcome.get('rooms', [])}

    def check(name, fn, step=None):
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, str(e) if isinstance(e, DemoError) else f'{e.__class__.__name__}: {e}'
        if not ok and (step or name) in errors:
            detail = f"시드 실패: {errors[step or name]}"
        checks.append(Check(name, bool(ok), detail or ''))

    hist = []
    if rooms.get('group'):
        try:
            hist = a.history(rooms['group'])
        except DemoError:
            hist = []

    def has(pred, label):
        found = [m for m in hist if pred(m)]
        return bool(found), f'{label} {len(found)}개' if found else f'{label} 없음'

    check('그룹 채팅', lambda: (rooms.get('group') in by_id, f"멤버 {len(by_id.get(rooms.get('group'), {}).get('members', []))}명"))
    check('텍스트 메시지', lambda: has(lambda m: m['kind'] == 'text' and not m.get('deleted'), '텍스트'))
    check('이모티콘', lambda: has(lambda m: m['kind'] == 'emoticon', '이모티콘'), '텍스트 메시지')
    check('메시지 수정', lambda: has(lambda m: m.get('edited'), '수정됨'))
    check('조용히 보내기', lambda: has(lambda m: m.get('silent'), 'silent'))
    check('답장', lambda: has(lambda m: m.get('reply_to'), '답장'))
    check('멘션', lambda: has(lambda m: A in (m.get('mentions') or []), '멘션'), '답장')
    check('공감', lambda: has(lambda m: m.get('reactions'), '공감 달린 메시지'))
    check('공지', lambda: (bool(by_id.get(rooms.get('group'), {}).get('notice')), '상단 공지 등록됨'))
    check('투표', lambda: has(lambda m: m['kind'] == 'poll' and sum(len(o['voters']) for o in m['poll']['options']) >= 2,
                            '투표(2표 이상)'))
    check('사다리 게임', lambda: has(lambda m: m['kind'] == 'ladder' and (m.get('ladder') or {}).get('mapping'), '사다리'))

    def board():
        posts = a.request({'type': 'board_list', 'room_id': rooms['group']}, 'board_list')['posts']
        return bool(posts and posts[0].get('comments')), f'게시글 {len(posts)}개, 댓글 {len(posts[0]["comments"]) if posts else 0}개'
    check('톡게시판', board)

    def event():
        today = date.today()
        evs = a.request({'type': 'event_list', 'start': _iso(datetime(today.year, today.month, today.day)),
                         'end': _iso(datetime(today.year, today.month, today.day) + timedelta(days=7))},
                        'event_list')['events']
        shared = [e for e in evs if e.get('room_id') == rooms.get('group')]
        card = any(m['kind'] == 'event' for m in hist)
        ok = bool(shared) and card and shared[0]['attendees'].get(B) == 'yes'
        return ok, f'일정 {len(evs)}개 · 방 일정 카드 {"있음" if card else "없음"} · {B} 응답 {shared[0]["attendees"].get(B) if shared else "-"}'
    check('일정 공유', event)
    check('사진', lambda: has(lambda m: m['kind'] == 'image', '사진'))
    check('파일', lambda: has(lambda m: m['kind'] == 'file', '파일'))
    check('링크', lambda: has(lambda m: m['kind'] == 'text' and 'https://' in m.get('content', ''), '링크'), '텍스트 메시지')

    def retention():
        atts = [m['attachment'] for m in hist if m.get('attachment')]
        ok = bool(atts) and all(a_.get('expires_at') for a_ in atts)
        return ok, f"보관 만료일 {atts[0].get('expires_at', '없음')[:10] if atts else '-'}"
    check('받은 파일 보관 기간', retention, '파일')

    def drawer():
        counts = {}
        for kind in ('image', 'file', 'link'):
            counts[kind] = len(a.request({'type': 'drawer_query', 'kind': kind}, 'drawer_result',
                                         lambda m, k=kind: m.get('kind') == k)['messages'])
        return all(counts.values()), f"사진 {counts['image']} · 파일 {counts['file']} · 링크 {counts['link']}"
    check('톡서랍', drawer, '사진')

    def direct():
        room = by_id.get(rooms.get('direct')) or {}
        return bool(room) and room.get('unread_count', 0) >= 1, f"안 읽은 메시지 {room.get('unread_count', 0)}개"
    check('1:1 채팅 · 안 읽은 수', direct, '1:1 채팅')

    def secret():
        rid = rooms.get('secret')
        if not rid:
            return False, '비밀채팅방 없음'
        from client.kakao.secret import SecretKeyring
        kdir = os.path.join(settings_dir(home), 'keys')
        mine, peer = SecretKeyring(A, directory=kdir), SecretKeyring(B, directory=kdir)
        msgs = [m for m in a.history(rid) if m['kind'] == 'secret']
        plain = [mine.decrypt(rid, peer.public_key_b64, m['content']) for m in msgs]
        readable = [p for p in plain if p]
        leaked = any('PC에서만' in m['content'] for m in msgs)
        return bool(readable) and not leaked, f'암호문 {len(msgs)}개 · 복호화 {len(readable)}개 · 서버 평문 노출 {"있음" if leaked else "없음"}'
    check('비밀채팅', secret)

    def open_chat():
        found = b.request({'type': 'open_room_search', 'query': '개발'}, 'open_room_search')['rooms']
        room = next((r for r in found if r['room_id'] == rooms.get('open')), None)
        nick = (by_id.get(rooms.get('open')) or {}).get('nicknames') or {}
        return bool(room) and room.get('member_count', 0) >= 2 and bool(nick), \
            f"검색 {len(found)}건 · 인원 {room.get('member_count') if room else 0} · 닉네임 {', '.join(nick.values()) or '없음'}"
    check('오픈채팅', open_chat)

    def stories():
        st = a.request({'type': 'story_list'}, 'story_list')['stories']
        return len(st) >= 2, f'펑 {len(st)}개'
    check('펑', stories)

    def todos():
        td = a.request({'type': 'todo_list'}, 'todo_list')['todos']
        return len(td) >= 2, f'할 일 {len(td)}개'
    check('할 일', todos)

    def multi():
        profiles = a.request({'type': 'multi_profile_list'}, 'multi_profile_list')['profiles']
        seen = (b.welcome.get('users') and next((u for u in b.welcome['users'] if u['username'] == A), {})) or {}
        return bool(profiles), f"프로필 {len(profiles)}개 · {B}에게 보이는 이름 '{seen.get('display_name', '')}'"
    check('멀티프로필', multi)

    def folders():
        path = os.path.join(settings_dir(home), f'{A}.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        names = [x['name'] for x in data.get('chat_folders', [])]
        return bool(names) and all(x['room_ids'] for x in data['chat_folders']), f"폴더 {', '.join(names)}"
    check('채팅방 폴더', folders)

    def briefing():
        bot_room = next((r for r in a.welcome.get('rooms', []) if r['type'] == 'direct' and BOT in r['members']), None)
        if bot_room is None:
            return False, 'AI 비서 방 없음'
        msgs = [m for m in a.history(bot_room['room_id']) if m['sender'] == BOT and '브리핑' in m.get('content', '')]
        return bool(msgs), f'브리핑 {len(msgs)}개'
    check('오늘의 브리핑', briefing)

    a.close()
    b.close()
    return checks


def print_table(checks, out=sys.stdout):
    width = max(len(c.name) for c in checks) + 2
    out.write('\n  결과  ' + '기능'.ljust(width) + '상세\n')
    out.write('  ' + '-' * (width + 50) + '\n')
    for c in checks:
        out.write(f"  {'✓' if c.ok else '✗'}     {c.name.ljust(width)}{c.detail}\n")
    passed = sum(1 for c in checks if c.ok)
    out.write(f'\n  {passed}/{len(checks)} 통과\n')
    out.flush()


# ================================================================ 실행
def launch_clients(port, names, home):
    env = dict(os.environ, KCS_MESSENGER_HOME=settings_dir(home), HOME=home, PYTHONPATH=ROOT)
    procs = []
    for i, name in enumerate(names):
        procs.append(subprocess.Popen([sys.executable, APP_PATH, '--port', str(port), '--user', name],
                                      cwd=ROOT, env=env))
        time.sleep(0.4 if i < len(names) - 1 else 0)
    return procs


def stop_children(procs):
    for p in procs:
        if p.poll() is None:
            p.terminate()
    deadline = time.monotonic() + 5
    for p in procs:
        try:
            p.wait(max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            p.kill()


def _raise_interrupt(*_args):
    raise KeyboardInterrupt


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='KCS Talk 데모: 서버 + 데모 데이터 + 클라이언트')
    ap.add_argument('--port', type=int, default=0, help='서버 포트 (기본: 빈 포트 자동)')
    ap.add_argument('--clients', type=int, default=2, help='실행할 클라이언트 수 (기본 2)')
    ap.add_argument('--users', default='', help='사용자 이름 (쉼표 구분). 기본: org.json 앞쪽 사용자 또는 홍길동·김철수·이영희')
    ap.add_argument('--headless-check', action='store_true', help='GUI 없이 시드 후 기능별 검증 표 출력')
    ap.add_argument('--keep', action='store_true', help='종료 후 임시 폴더(DB·설정)를 지우지 않음')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    tmp = tempfile.mkdtemp(prefix='kcs_demo_')
    home = os.path.join(tmp, 'home')
    os.makedirs(settings_dir(home), exist_ok=True)
    os.environ['KCS_MESSENGER_HOME'] = settings_dir(home)
    users = [u.strip() for u in args.users.split(',') if u.strip()] or default_users(count=max(3, args.clients))
    if len(users) < 2:
        users += [u for u in DEMO_USERS if u not in users][:2 - len(users)]
    db_dir = prepare_db_dir(os.path.join(tmp, 'db'))
    org_note = 'server_data/org.json 조직도' if os.path.exists(os.path.join(db_dir, 'org.json')) else '기본 데모 사용자'
    print(f'KCS Talk 데모 · 임시 폴더 {tmp}\n  조직: {org_note} · 사용자: {", ".join(users)}', flush=True)
    server = start_server(os.path.join(db_dir, 'kakao.db'), port=args.port)
    print(f'  서버: 127.0.0.1:{server.port} (오늘의 브리핑 켬, URL 미리보기 끔)\n데모 데이터 만드는 중…', flush=True)
    procs = []
    code = 0
    # 백그라운드로 실행돼 SIGINT 가 무시 상태로 상속되었어도 Ctrl+C / kill 로 깔끔하게 끝나도록
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        report = seed(server.port, users[:3], home)
        if args.headless_check:
            checks = verify(server.port, users[:3], report, home)
            print_table(checks)
            return 0 if all(c.ok for c in checks) else 1
        names = users[:max(1, args.clients)]
        print(f'\n클라이언트 {len(names)}개 실행: {", ".join(names)}', flush=True)
        print(f'  다른 클라이언트: python3 client/kakao/app.py --port {server.port} --user 이름', flush=True)
        print('  끝내려면 Ctrl+C', flush=True)
        procs = launch_clients(server.port, names, home)
        while True:
            time.sleep(0.5)
            if procs and all(p.poll() is not None for p in procs):
                print('모든 클라이언트가 종료되었습니다. 서버는 Ctrl+C 로 끝낼 때까지 계속 실행됩니다.', flush=True)
                procs = []
    except KeyboardInterrupt:
        print('\n종료하는 중…', flush=True)
    finally:
        stop_children(procs)
        server.stop()
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f'임시 폴더를 남겨 두었습니다: {tmp}')
    return code


if __name__ == '__main__':
    sys.exit(main())
