# -*- coding: utf-8 -*-
"""
서버 연결 계층 - 줄 단위 JSON(NDJSON) 소켓 통신
수신은 별도 스레드에서 처리하고, Qt 시그널(queued)로 GUI 스레드에 전달한다.
"""

import json
import socket
import threading

from PyQt5.QtCore import QObject, pyqtSignal


class ChatConnection(QObject):
    """서버와의 TCP 연결 하나를 관리한다"""

    connected = pyqtSignal()
    disconnected = pyqtSignal(str)          # 사유
    event_received = pyqtSignal(str, dict)  # (type, payload)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sock = None
        self._send_lock = threading.Lock()
        self._reader = None
        self._closing = False
        self._req_seq = 0

    @property
    def is_connected(self):
        return self._sock is not None

    def connect_to(self, host, port, username, timeout=5.0):
        """연결 후 join 요청을 보낸다. 실패 시 OSError를 그대로 올린다."""
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(None)
        self._sock = sock
        self._closing = False
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self.connected.emit()
        self.send('join', username=username)

    def send(self, msg_type, **payload):
        """요청 전송. 요청 번호(req_id)를 돌려준다. 연결이 없으면 None."""
        if not self._sock:
            return None
        self._req_seq += 1
        payload['type'] = msg_type
        payload.setdefault('req_id', self._req_seq)
        data = (json.dumps(payload, ensure_ascii=False) + '\n').encode('utf-8')
        try:
            with self._send_lock:
                self._sock.sendall(data)
        except OSError as e:
            self._handle_disconnect(f"전송 실패: {e}")
            return None
        return payload['req_id']

    def close(self):
        if not self._sock:
            return
        self._closing = True
        try:
            self.send('leave')
        except Exception:
            pass
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass
        self._sock = None

    # ---- 내부 ----
    def _read_loop(self):
        buf = b''
        sock = self._sock
        if sock is None:
            return
        reason = "서버 연결이 종료되었습니다"
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line.decode('utf-8'))
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if isinstance(msg, dict) and 'type' in msg:
                        self.event_received.emit(msg['type'], msg)
        except OSError as e:
            reason = f"연결 오류: {e}"
        if not self._closing:
            self._handle_disconnect(reason)

    def _handle_disconnect(self, reason):
        if self._sock is None and self._closing:
            return
        self._sock = None
        self.disconnected.emit(reason)
