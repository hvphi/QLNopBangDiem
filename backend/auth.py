import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from .db import now


def valid_email(email):
    return bool(re.fullmatch(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@vku\.udn\.vn', email.lower()))


def hash_password(password, *, minimum_length=12):
    if len(password) < minimum_length:
        raise ValueError(f'Mật khẩu cần ít nhất {minimum_length} ký tự.')
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
    return salt + ':' + digest.hex()


def verify_password(password, stored):
    try:
        salt, digest = stored.split(':')
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError):
        return False


def session(db, user_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat()
    db.execute('DELETE FROM sessions WHERE expires < ?', (now(),))
    db.execute('INSERT INTO sessions VALUES(?,?,?,?)',
               (hashlib.sha256(token.encode()).hexdigest(), user_id, csrf, expires))
    return token, csrf


def current_user(request, database):
    token = request.cookies.get('session', '')
    with database.connect() as db:
        row = db.execute('''SELECT u.*,s.csrf FROM users u JOIN sessions s ON s.user_id=u.id
            WHERE s.token=? AND s.expires>? AND u.active=1''',
            (hashlib.sha256(token.encode()).hexdigest(), now())).fetchone()
    if row is None:
        raise HTTPException(401, 'Vui lòng đăng nhập.')
    user = dict(row)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), user['csrf']):
            raise HTTPException(403, 'CSRF token không hợp lệ. Tải lại trang rồi thử lại.')
    return user


def require(user, *roles):
    if user['role'] not in roles:
        raise HTTPException(403, 'Bạn không có quyền thực hiện thao tác này.')


def public_user(user):
    return {k: user[k] for k in ('id', 'email', 'name', 'role', 'department', 'fingerprint', 'active')}
