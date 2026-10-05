import hashlib
import os
import re
import unicodedata
import uuid
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def slug(value):
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9_-]', '_', value)[:100] or 'unknown'


class Storage:
    def __init__(self, root, key):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if len(key) != 32:
            raise ValueError('APP_ENCRYPTION_KEY phải là 64 ký tự hex (32 byte).')
        self.cipher = AESGCM(key)

    def resolve(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Đường dẫn kho không hợp lệ.')
        return path

    def save(self, data, course):
        relative = '/'.join(slug(course[k]) for k in ('year', 'semester', 'department', 'code'))
        relative += '/' + uuid.uuid4().hex + '.pdf.enc'
        path = self.resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        nonce = os.urandom(12)
        encrypted = nonce + self.cipher.encrypt(nonce, data, relative.encode())
        with path.open('xb') as f:
            f.write(encrypted)
            f.flush()
            os.fsync(f.fileno())
        return relative, hashlib.sha256(data).hexdigest()

    def read(self, relative, expected_hash):
        payload = self.resolve(relative).read_bytes()
        data = self.cipher.decrypt(payload[:12], payload[12:], relative.encode())
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError('Kho dữ liệu không còn toàn vẹn.')
        return data

    def discard(self, relative):
        self.resolve(relative).unlink(missing_ok=True)
