@echo off
rem KCS Talk 채팅 서버 실행 (창을 닫으면 서버가 멈춥니다). 다른 PC 에서 접속하게 하려면: KCS_Talk_Server.bat --host 0.0.0.0
chcp 65001 >nul
cd /d "%~dp0..\.."
where py >nul 2>nul && (py kcs.py server %*) || (python kcs.py server %*)
pause
