# -*- coding: utf-8 -*-
"""
비밀채팅 종단간 암호화 (명세 §8.1)
- 사용자별 X25519 키쌍을 이 PC에만 보관: <KCS_MESSENGER_HOME 또는 ~/.kcs_messenger>/keys/<username>.key (권한 600)
- 방 키 = HKDF-SHA256(X25519(내 비밀키, 상대 공개키), salt=room_id, info=b'kcs-secret-v1')
- 메시지 = base64(nonce 12바이트 + AES-256-GCM 암호문), 평문은 {"text": "..."} JSON
서버는 공개키만 알고, 비밀키·평문은 절대 서버로 가지 않는다.
"""

import base64
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

INFO = b'kcs-secret-v1'


def key_dir():
    base = os.environ.get('KCS_MESSENGER_HOME') or os.path.join(os.path.expanduser('~'), '.kcs_messenger')
    return os.path.join(base, 'keys')


class SecretKeyring:
    """한 사용자의 비밀키 보관 + 방 키 유도 + 암복호화"""

    def __init__(self, username, directory=None):
        self.username = username
        self.path = os.path.join(directory or key_dir(), f'{username}.key')
        self._private = self._load_or_create()
        self._room_keys = {}

    def _load_or_create(self):
        try:
            with open(self.path, 'rb') as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
            if isinstance(key, X25519PrivateKey):
                return key
            raise ValueError('X25519 키가 아닙니다')
        except (OSError, ValueError):
            key = X25519PrivateKey.generate()
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption())
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(pem)
            return key

    @property
    def public_key_b64(self):
        raw = self._private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return base64.b64encode(raw).decode('ascii')

    def room_key(self, room_id, peer_public_b64):
        cache_key = (room_id, peer_public_b64)
        if cache_key not in self._room_keys:
            peer = X25519PublicKey.from_public_bytes(base64.b64decode(peer_public_b64))
            shared = self._private.exchange(peer)
            self._room_keys[cache_key] = HKDF(algorithm=hashes.SHA256(), length=32,
                                              salt=room_id.encode('utf-8'), info=INFO).derive(shared)
        return self._room_keys[cache_key]

    def encrypt(self, room_id, peer_public_b64, text):
        key = self.room_key(room_id, peer_public_b64)
        nonce = os.urandom(12)
        plain = json.dumps({'text': text}, ensure_ascii=False).encode('utf-8')
        return base64.b64encode(nonce + AESGCM(key).encrypt(nonce, plain, room_id.encode('utf-8'))).decode('ascii')

    def decrypt(self, room_id, peer_public_b64, blob):
        """복호화한 텍스트. 키가 다르거나 변조되었으면 None"""
        try:
            raw = base64.b64decode(blob)
            key = self.room_key(room_id, peer_public_b64)
            plain = AESGCM(key).decrypt(raw[:12], raw[12:], room_id.encode('utf-8'))
            return json.loads(plain.decode('utf-8')).get('text', '')
        except (InvalidTag, ValueError, TypeError, KeyError):
            return None
