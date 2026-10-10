#!/bin/bash
# KCS Talk 메신저 실행 (Finder 에서 더블클릭). 처음 한 번: install.command
cd "$(dirname "$0")/../.." || exit 1
exec python3 kcs.py client "$@"
