# -*- coding: utf-8 -*-
"""
사내 포털(portal.kcins.co.kr) RAG 연동 점검 (명세 §7.6.1)

    python3 scripts/portal_check.py                      # 기본 질문으로 점검
    python3 scripts/portal_check.py "연차 규정 알려줘"     # 질문 지정
    python3 scripts/portal_check.py --no-save             # 저장 API 는 호출하지 않음
    python3 scripts/portal_check.py --config 경로/portal.json

서버와 같은 설정(server_data/portal.json + 환경변수)을 읽어 질문 1건, 저장 1건을 보내고 결과를 보여 준다.
보낼 함(portal_outbox.db)에 밀린 기록 수도 함께 보여 준다. 실패가 있으면 종료 코드 1.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server.kakao.portal import PortalClient, PortalError, SOURCE_TAG, load_config  # noqa: E402
from server.kakao.server import DEFAULT_DB_PATH  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description='사내 포털 RAG 연동 점검')
    parser.add_argument('question', nargs='?', default='연결 점검입니다. 간단히 인사해 주세요.')
    parser.add_argument('--config', default=os.path.join(os.path.dirname(DEFAULT_DB_PATH), 'portal.json'))
    parser.add_argument('--no-save', action='store_true', help='저장 API 는 호출하지 않음')
    args = parser.parse_args(argv)

    config = load_config(args.config)
    if config is None:
        print('포털 연동이 꺼져 있습니다 (portal.json enabled:false 또는 KCS_PORTAL=off).')
        return 1
    token = '있음' if config.get('token') else '없음'
    print(f"포털: {config['base_url']}  방식: {config['api_style']}  토큰: {token}")
    print(f"  질문 API: {config['ask_path']}   저장 API: {config['save_path']}")
    client = PortalClient(config)
    ok = True
    user = {'username': 'portal-check', 'name': '연동 점검', 'room_id': None}
    try:
        text, sources, conv = client.ask(args.question, user, [], None)
        print(f'✓ 질문 성공 (대화 id: {conv or "-"})\n  답변: {text[:300]}')
        for s in sources:
            print(f'  출처: {s}')
    except PortalError as exc:
        ok = False
        print(f'✗ 질문 실패: {exc}')
        if '403' in str(exc):
            print('  → 사내망(허용된 IP)에서 실행했는지, 토큰이 맞는지 확인하세요.')
        elif '404' in str(exc):
            print('  → 질문 API 경로가 다릅니다. portal.json 의 ask_path(또는 KCS_PORTAL_ASK_PATH)를 맞추세요.')
        text = ''
    if not args.no_save:
        now = datetime.now().isoformat(timespec='seconds')
        try:
            client.save({'source': SOURCE_TAG, 'conversation_id': None, 'user': user['username'],
                         'user_name': user['name'], 'room_id': None, 'room_name': '연동 점검',
                         'answered_by': 'portal', 'created_at': now,
                         'messages': [{'role': 'user', 'content': args.question, 'timestamp': now},
                                      {'role': 'assistant', 'content': text or '(질문 실패)', 'timestamp': now}]})
            print('✓ 대화 저장 성공')
        except PortalError as exc:
            ok = False
            print(f'✗ 대화 저장 실패: {exc}')
    outbox = os.path.join(os.path.dirname(os.path.abspath(args.config)), 'portal_outbox.db')
    if os.path.exists(outbox):
        db = sqlite3.connect(outbox)
        try:
            pending = db.execute('SELECT COUNT(*) FROM portal_outbox WHERE sent_at IS NULL').fetchone()[0]
            print(f'보낼 함에 밀린 대화 기록: {pending}건')
        except sqlite3.Error:
            pass
        finally:
            db.close()
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
