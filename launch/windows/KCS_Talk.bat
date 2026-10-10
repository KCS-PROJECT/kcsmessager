@echo off
rem KCS Talk 메신저 실행 (더블클릭). 처음 한 번: 설치.bat
chcp 65001 >nul
cd /d "%~dp0..\.."
where pyw >nul 2>nul && (start "" pyw kcs.py client %*) || (start "" pythonw kcs.py client %*)
