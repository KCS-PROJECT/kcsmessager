#!/bin/sh
# KCS Talk 채팅 서버 실행. 다른 PC 접속 허용: ./kcs-talk-server.sh --host 0.0.0.0
cd "$(dirname "$0")/../.." || exit 1
exec python3 kcs.py server "$@"
