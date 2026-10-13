#!/bin/sh
# KCS Talk 메신저 실행. 처음 한 번: ./install.sh
cd "$(dirname "$0")/../.." || exit 1
exec python3 kcs.py client "$@"
