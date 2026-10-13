#!/bin/bash
# KCS Talk 채팅 서버 실행 (터미널 창을 닫으면 멈춤). 다른 PC 접속 허용: --host 0.0.0.0
cd "$(dirname "$0")/../.." || exit 1
exec python3 kcs.py server "$@"
