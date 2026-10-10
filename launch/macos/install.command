#!/bin/bash
# KCS Talk 처음 설치: 패키지 설치 + 점검 + 바탕화면 바로가기
cd "$(dirname "$0")/../.." || exit 1
python3 -m pip install -r requirements-kcs.txt && python3 kcs.py doctor && python3 kcs.py shortcut \
  && echo "설치 완료. 바탕화면의 'KCS Talk.command' 로 실행하세요."
