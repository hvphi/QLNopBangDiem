"""Sync explicitly supplied local account roles; never remove other roles."""
import argparse
import json
from pathlib import Path
import openpyxl
from backend.auth import hash_password, verify_password, valid_email
from backend.db import Database, audit
from scripts.provision_teachers import plain_name, new_password

ROLES = {'GV': 'teacher', 'TK': 'head', 'ĐT': 'training', 'TP ĐT': 'training'}
LABELS = {'teacher': 'GV', 'head': 'TK', 'training': 'ĐT', 'admin': 'admin'}


def parse_rows(rows):
    records, seen = [], set()
    for row in rows:
        if len(row) < 6 or not row[2]:
            continue
        if any(isinstance(v, str) and v.startswith('=') for v in row[1:6]):
            raise ValueError('Không chấp nhận công thức trong dữ liệu tài khoản.')
        name, email = plain_name(str(row[1] or '')), str(row[2]).strip().lower()
        password = str(row[3]) if row[3] is not None else ''
        labels = [r.strip() for r in str(row[4] or '').split(',')]
        if not name or not valid_email(email):
            raise ValueError('Tên hoặc email không hợp lệ.')
        if password and len(password) < 8:
            raise ValueError('Mật khẩu cần ít nhất 8 ký tự.')
        if any(label not in ROLES for label in labels):
            raise ValueError('Vai trò không hợp lệ.')
        roles = [ROLES[label] for label in labels]
        if len(set(roles)) != len(roles) or email in seen:
            raise ValueError('Email hoặc vai trò trùng.')
        seen.add(email)
        records.append({'name': name, 'email': email, 'password': password,
                        'roles': roles, 'department': str(row[5] or 'Chưa phân khoa').strip()})
    return records


def read_accounts(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        rows = list(workbook['Tai khoan GV'].values)
        header = next(i for i, row in enumerate(rows) if row[2] == 'Email đăng nhập')
        return parse_rows(rows[header + 1:])
    finally:
        workbook.close()


def sync_accounts(database, records, credentials):
    # Validate even programmatic input before any database mutation.
    records = parse_rows([(None, r['name'], r['email'], r['password'],
                          ','.join(LABELS[role] for role in r['roles']), r['department']) for r in records])
    path = Path(credentials)
    previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'accounts': []}
    known = {(a['email'], a['role']): a['password'] for a in previous['accounts']}
    accounts, created, updated = [], 0, 0
    with database.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        for record in records:
            email = record['email']
            existing = {r['role']: r for r in db.execute('SELECT * FROM users WHERE email=?', (email,))}
            password = record['password']
            if not password:
                for role, user in existing.items():
                    candidate = known.get((email, LABELS[role]), '')
                    if candidate and verify_password(candidate, user['password']):
                        password = candidate
                        break
            if not password and not existing:
                password = new_password()
            for role in record['roles']:
                user = existing.get(role)
                stored = (user or next(iter(existing.values()), None))
                hashed = stored['password'] if stored else None
                if password and (not hashed or not verify_password(password, hashed)):
                    hashed = hash_password(password, minimum_length=8)
                if user:
                    changed = (user['name'], user['department'], user['password']) != (record['name'], record['department'], hashed)
                    if changed:
                        db.execute('UPDATE users SET name=?,department=?,password=? WHERE id=?',
                                   (record['name'], record['department'], hashed, user['id']))
                        db.execute('DELETE FROM sessions WHERE user_id=?', (user['id'],))
                        audit(db, None, 'sync_account_excel', user['id'], json.dumps({'email': email, 'role': role}, ensure_ascii=False))
                        updated += 1
                else:
                    cursor = db.execute('INSERT INTO users(email,name,role,department,password) VALUES(?,?,?,?,?)',
                                        (email, record['name'], role, record['department'], hashed))
                    audit(db, None, 'sync_account_excel_create', cursor.lastrowid, json.dumps({'email': email, 'role': role}, ensure_ascii=False))
                    created += 1
            for user in db.execute('SELECT * FROM users WHERE email=? ORDER BY id', (email,)):
                label = LABELS[user['role']]
                candidate = password or known.get((email, label), '')
                exported = candidate if candidate and verify_password(candidate, user['password']) else ''
                accounts.append({'id': user['id'], 'name': user['name'], 'email': email, 'password': exported,
                                 'role': label, 'department': user['department'],
                                 'status': 'Hoạt động' if user['active'] else 'Tạm khóa',
                                 'note': 'Giữ vai trò hiện có ngoài file.' if user['role'] not in record['roles'] else ''})
    result = {'accounts': accounts, 'created': created, 'updated': updated}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='Acc/DS_tai_khoan_GV_VKU.xlsx')
    parser.add_argument('--database', default='runtime/gradebook.sqlite3')
    parser.add_argument('--credentials', default='.local/account-imports/account-sync-20261005.json')
    args = parser.parse_args()
    records = read_accounts(args.source)
    records.append({'name': 'Nguyễn Thị Thùy Giang', 'email': 'nttgiang@vku.udn.vn',
                    'password': '', 'roles': ['training'], 'department': 'ĐT & BĐCL'})
    result = sync_accounts(Database(args.database), records, args.credentials)
    print('Created:', result['created'], '| Updated:', result['updated'], '| Account roles:', len(result['accounts']))
