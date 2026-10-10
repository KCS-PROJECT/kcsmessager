@echo off
rem KCS Talk 처음 설치: 필요한 파이썬 패키지 설치 + 점검 + 바탕화면/시작 메뉴 바로가기
chcp 65001 >nul
cd /d "%~dp0..\.."
set PY=python
where py >nul 2>nul && set PY=py
%PY% -m pip install -r requirements-kcs.txt || goto :fail
%PY% kcs.py doctor || goto :fail
%PY% kcs.py shortcut
echo.
echo 설치 완료. 바탕화면의 'KCS Talk' 로 실행하세요.
pause
exit /b 0
:fail
echo 설치 중 문제가 있습니다. 위 메시지를 확인하세요. (Python 3.8 이상: https://www.python.org/downloads/ )
pause
exit /b 1
