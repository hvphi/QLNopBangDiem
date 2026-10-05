"""Provision local teacher accounts from the reviewed timetable snapshot."""
import argparse
import json
import re
import secrets
import string
import unicodedata
from pathlib import Path
from backend.auth import hash_password, verify_password, valid_email
from backend.db import Database, audit


OVERRIDES = {
    'ThS.Nguyễn Thành Tâm': 'nttam2@vku.udn.vn',
    'ThS.Ngô Thị Hiền Trang': 'nthtrang2@vku.udn.vn',
    'ThS.Nguyễn Thị Thanh Thuý (ĐHNN)': 'nttthuy2@vku.udn.vn',
}
EXISTING_ALIASES = {('TS.Hồ Văn Phi', 'Giảng viên HV Phi')}


def plain_name(source):
    return re.sub(r'^(?:(?:PGS|TS|ThS|KS)\s*\.\s*)+', '', source).strip()


def ascii_name(source):
    name = re.sub(r'\s*\([^)]*\)', '', plain_name(source))
    name = name.casefold().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', name) if not unicodedata.combining(c))


def teacher_email(source):
    if source in OVERRIDES:
        return OVERRIDES[source]
    words = ascii_name(source).split()
    if len(words) < 2 or not all(re.fullmatch('[a-z]+', word) for word in words):
        raise ValueError('Không xác định được tên cá nhân: ' + source)
    return ''.join(word[0] for word in words[:-1]) + words[-1] + '@vku.udn.vn'


def new_password():
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(8))
        if all(any(c in chars for c in password) for chars in (string.ascii_lowercase, string.ascii_uppercase, string.digits)):
            return password


def provision(database, snapshot, credentials_path):
    html = Path(snapshot).read_text(encoding='utf-8')
    rows = json.loads(re.search(r'const rows=(.*?);const names=', html, re.S).group(1))
    names = sorted(set(row['teacher'] for row in rows))
    excluded = [name for name in names if name.startswith('Khoa.') or name == 'ThS.Bank Agribank']
    names = [name for name in names if name not in excluded]
    emails = [teacher_email(name) for name in names]
    if len(set(emails)) != len(emails) or not all(valid_email(email) for email in emails):
        raise ValueError('Email trùng hoặc không hợp lệ; cần xác định email riêng trước khi cấp tài khoản.')
    credential_file = Path(credentials_path)
    previous = json.loads(credential_file.read_text(encoding='utf-8')) if credential_file.exists() else {'accounts': []}
    known = {item['email']: item['password'] for item in previous['accounts']}
    accounts = []
    created = 0
    with database.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for source, email in zip(names, emails):
            existing = db.execute("SELECT * FROM users WHERE email=? AND role='teacher'", (email,)).fetchone()
            note = 'Email thêm số để phân biệt tên trùng.' if source in OVERRIDES else ''
            if existing:
                if ascii_name(existing['name']) != ascii_name(source) and (source, existing['name']) not in EXISTING_ALIASES:
                    raise ValueError('Email đã thuộc GV khác: ' + email)
                password = known.get(email, '')
                if password and not verify_password(password, existing['password']):
                    password = ''
                uid = existing['id']
                status = 'Đã có — giữ nguyên'
                note = (note + ' Giữ mật khẩu hiện tại.' + (' Không có mật khẩu gốc để xuất.' if not password else '')).strip()
                department = existing['department']
            else:
                password = new_password()
                # Explicitly requested 8-character passwords for this provisioning batch only.
                cursor = db.execute('INSERT INTO users(email,name,role,department,password) VALUES(?,?,?,?,?)',
                                    (email, plain_name(source), 'teacher', 'Chưa phân khoa', hash_password(password, minimum_length=8)))
                uid = cursor.lastrowid
                audit(db, None, 'provision_teacher_account', uid, json.dumps({'source': source, 'email': email}, ensure_ascii=False))
                created += 1
                status, department = 'Đã tạo', 'Chưa phân khoa'
            accounts.append({'source': source, 'name': plain_name(source), 'email': email, 'password': password,
                             'role': 'GV', 'department': department, 'status': status, 'note': note, 'id': uid})
    result = {'source_url': 'https://daotao.vku.udn.vn/thoi-khoa-bieu', 'period': 'HK1 2026–2027',
              'accounts': accounts, 'excluded': excluded, 'created': created}
    credential_file.parent.mkdir(parents=True, exist_ok=True)
    credential_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='runtime/gradebook.sqlite3')
    parser.add_argument('--snapshot', default='docs/reports/TKB_VKU_theo_GV_HK1_2026-2027.html')
    parser.add_argument('--credentials', required=True)
    args = parser.parse_args()
    result = provision(Database(args.database), args.snapshot, args.credentials)
    print('Created:', result['created'], '| Total teachers:', len(result['accounts']), '| Excluded:', len(result['excluded']))
