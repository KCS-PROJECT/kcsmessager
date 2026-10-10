# -*- coding: utf-8 -*-
"""
관리자용: 사용자 비밀번호 설정/초기화 (명세 §4.1)

    python3 scripts/set_password.py 김명수            # 새 비밀번호를 물어본다
    python3 scripts/set_password.py kmkim --clear     # 비밀번호 삭제 → 다음에 [처음 사용 등록]으로 다시 등록
    python3 scripts/set_password.py 김명수 --db server_data/kakao.db

아이디는 사용자 이름, 이메일 또는 사내 계정. 저장된 자동 로그인 토큰도 모두 폐기한다.
서버가 켜져 있어도 된다(SQLite).
"""

import argparse
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server.chat.chat_server import DEFAULT_DB_PATH  # noqa: E402
from server.kakao.store import Store  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description='KCS Talk 사용자 비밀번호 설정/초기화')
    parser.add_argument('login_id', help='사용자 이름, 이메일 또는 사내 계정')
    parser.add_argument('--db', default=DEFAULT_DB_PATH, help=f'SQLite DB 경로 (기본: {DEFAULT_DB_PATH})')
    parser.add_argument('--clear', action='store_true', help='비밀번호를 지워 [처음 사용 등록]을 다시 하게 한다')
    parser.add_argument('--password', help='새 비밀번호 (생략하면 입력 받음)')
    args = parser.parse_args(argv)

    store = Store(args.db)
    try:
        username = store.resolve_login(args.login_id)
        if username is None:
            print(f'사용자를 찾을 수 없습니다: {args.login_id}', file=sys.stderr)
            return 1
        if args.clear:
            store.clear_password(username)
            print(f'{username}: 비밀번호를 지웠습니다. 로그인 창의 [처음 사용 등록]으로 다시 등록하면 됩니다.')
            return 0
        password = args.password or getpass.getpass('새 비밀번호: ')
        if not 4 <= len(password) <= 64:
            print('비밀번호는 4~64자로 입력해 주세요.', file=sys.stderr)
            return 1
        if args.password is None and getpass.getpass('한 번 더: ') != password:
            print('두 비밀번호가 다릅니다.', file=sys.stderr)
            return 1
        store.set_password(username, password)
        store.revoke_all_login_tokens(username)
        print(f'{username}: 비밀번호를 바꿨습니다. 저장된 자동 로그인은 모두 해제되었습니다.')
        return 0
    finally:
        store.close()


if __name__ == '__main__':
    sys.exit(main())
