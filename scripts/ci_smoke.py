# -*- coding: utf-8 -*-
"""
세 OS 실제 실행 점검 (GitHub Actions 의 Windows · Ubuntu · macOS 러너에서, 또는 각 PC 에서)

    python scripts/ci_smoke.py source            소스 실행: 서버를 띄우고 접속 · 클라이언트 --self-check
    python scripts/ci_smoke.py built DIST_DIR    빌드한 메신저 --self-check + 빌드한 서버 실행 · 접속 · DB 위치

실패하면 종료 코드 1.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from client.kakao import osenv  # noqa: E402

NAME = osenv.APP_NAME


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_connect(port, proc, seconds=40):
    end = time.time() + seconds
    while time.time() < end:
        if proc.poll() is not None:
            return False
        try:
            socket.create_connection(('127.0.0.1', port), 1).close()
            return True
        except OSError:
            time.sleep(0.5)
    return False


def check(label, ok, detail=''):
    print(f"{'✓' if ok else '✗'} {label}" + (f' - {detail}' if detail else ''), flush=True)
    return ok


def run_server(cmd, port, env=None):
    proc = subprocess.Popen(cmd + ['--port', str(port)], cwd=ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        ok = wait_connect(port, proc)
    finally:
        proc.terminate()
        try:
            out = proc.communicate(timeout=15)[0].decode('utf-8', 'replace')
        except subprocess.TimeoutExpired:
            proc.kill()
            out = proc.communicate()[0].decode('utf-8', 'replace')
    return ok, out


def env_with_home():
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONIOENCODING='utf-8',
               KCS_MESSENGER_HOME=tempfile.mkdtemp(prefix='kcs_ci_home_'))
    return env


def source():
    env = env_with_home()
    results = []
    db = os.path.join(tempfile.mkdtemp(prefix='kcs_ci_db_'), 'kakao.db')
    ok, out = run_server([sys.executable, 'kcs.py', 'server', '--db', db], free_port(), env)
    results.append(check(f'[{osenv.os_label()}] kcs.py server 접속', ok, '' if ok else out[-800:]))
    r = subprocess.run([sys.executable, 'kcs.py', 'client', '--self-check'], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    print(r.stdout + r.stderr)
    results.append(check('kcs.py client --self-check', r.returncode == 0))
    r = subprocess.run([sys.executable, 'kcs.py', 'doctor'], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    print(r.stdout + r.stderr)
    results.append(check('kcs.py doctor', r.returncode == 0))
    return all(results)


def built(dist):
    env = env_with_home()
    exe = {'mac': os.path.join(dist, f'{NAME}.app', 'Contents', 'MacOS', NAME),
           'windows': os.path.join(dist, NAME, f'{NAME}.exe'),
           'linux': os.path.join(dist, NAME, NAME)}[osenv.current()]
    results = [check('빌드한 메신저 파일', os.path.exists(exe), exe)]
    if results[0]:
        log = os.path.join(env['KCS_MESSENGER_HOME'], 'logs', 'kcs_talk.log')   # 콘솔 없는 창 모드 앱의 출력
        try:
            r = subprocess.run([exe, '--self-check'], env=env, capture_output=True, timeout=120)
            code, out = r.returncode, (r.stdout + r.stderr).decode('utf-8', 'replace')
        except subprocess.TimeoutExpired:
            code, out = None, '(120초 안에 끝나지 않음)'
        if os.path.exists(log):
            with open(log, encoding='utf-8', errors='replace') as f:
                out += '\n[logs/kcs_talk.log]\n' + f.read()
        print(out)
        results.append(check('빌드한 메신저 --self-check', code == 0, f'종료 코드 {code}'))
    server_dir = os.path.join(dist, f'{NAME} Server')
    server = os.path.join(server_dir, f'{NAME} Server' + ('.exe' if osenv.is_windows() else ''))
    results.append(check('빌드한 서버 파일', os.path.exists(server), server))
    if os.path.exists(server):
        ok, out = run_server([server], free_port(), env)
        results.append(check('빌드한 서버 실행 · 접속', ok, '' if ok else out[-800:]))
        db = os.path.join(server_dir, 'server_data', 'kakao.db')
        results.append(check('서버 DB 가 실행 파일 옆에', os.path.exists(db), db))
    return all(results)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ('source', 'built'):
        print(__doc__)
        return 2
    ok = source() if argv[0] == 'source' else built(argv[1] if len(argv) > 1 else os.path.join(ROOT, 'dist'))
    print('통과' if ok else '실패')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
