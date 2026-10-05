import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.auth import hash_password, verify_password
from backend.db import Database
from scripts.provision_teachers import provision, teacher_email
from scripts.sync_account_excel import parse_rows, sync_accounts, read_accounts


def snapshot(path, names):
    path.write_text('const rows=' + json.dumps([{'teacher': n} for n in names]) + ';const names=', encoding='utf-8')
    return path


def test_email_rules_and_authorized_collision_suffixes():
    assert teacher_email('TS. Đặng Quang Hiển') == 'dqhien@vku.udn.vn'
    assert teacher_email('ThS. Hà Thị Minh Phương') == 'htmphuong@vku.udn.vn'
    assert teacher_email('ThS.Nguyễn Thành Tâm') == 'nttam2@vku.udn.vn'
    assert teacher_email('ThS.Ngô Thị Hiền Trang') == 'nthtrang2@vku.udn.vn'
    assert teacher_email('ThS.Nguyễn Thị Thanh Thuý (ĐHNN)') == 'nttthuy2@vku.udn.vn'


def test_provision_login_idempotency_and_preservation(tmp_path):
    app = create_app(tmp_path/'data', bytes(range(32)), secure=False)
    database = app.state.database
    with database.connect() as db:
        db.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(1,'hvphi@vku.udn.vn','Giảng viên HV Phi','teacher','CNTT',?)", (hash_password('Keep-Existing-Password'),))
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OLD','Old course','2025-2026','1','CNTT',1)")
    with database.connect() as db:
        before = dict(db.execute('SELECT * FROM users WHERE id=1').fetchone())
        courses = [dict(r) for r in db.execute('SELECT * FROM courses')]
    path = snapshot(tmp_path/'source.html', ['TS.Hồ Văn Phi', 'TS.Đặng Quang Hiển', 'ThS.Hà Thị Minh Phương', 'Khoa.KH MT', 'ThS.Bank Agribank'])
    credentials = tmp_path/'accounts.json'
    result = provision(database, path, credentials)
    assert result['created'] == 2 and len(result['excluded']) == 2
    client = TestClient(app)
    for account in result['accounts']:
        if account['email'] == 'hvphi@vku.udn.vn':
            assert account['password'] == ''
            continue
        password = account['password']
        assert len(password) == 8
        response = client.post('/api/login', json={'email': account['email'], 'password': password, 'role': 'teacher'})
        assert response.status_code == 200
        assert response.json()['user']['role'] == 'teacher'
        with database.connect() as db:
            stored = db.execute('SELECT * FROM users WHERE id=?', (account['id'],)).fetchone()
            assert stored['department'] == 'Chưa phân khoa'
            assert stored['password'] != password and verify_password(password, stored['password'])
            assert password not in ''.join(r['details'] for r in db.execute('SELECT * FROM audit'))
    second = provision(database, path, credentials)
    assert second['created'] == 0
    assert [(r['id'],r['password']) for r in second['accounts']] == [(r['id'],r['password']) for r in result['accounts']]
    with database.connect() as db:
        assert dict(db.execute('SELECT * FROM users WHERE id=1').fetchone()) == before
        assert [dict(r) for r in db.execute('SELECT * FROM courses')] == courses
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    with pytest.raises(ValueError, match='12'):
        hash_password('Short123')


def test_provision_conflict_rolls_back(tmp_path):
    database = Database(tmp_path/'db.sqlite3')
    with database.connect() as db:
        db.execute("INSERT INTO users(email,name,role,department,password) VALUES('htmphuong@vku.udn.vn','Other Person','teacher','OLD',?)", (hash_password('Old-password-kept'),))
    path = snapshot(tmp_path/'source.html', ['TS.Đặng Quang Hiển','ThS.Hà Thị Minh Phương'])
    with pytest.raises(ValueError, match='GV khác'):
        provision(database, path, tmp_path/'credentials.json')
    with database.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM audit').fetchone()[0] == 0
    assert not (tmp_path/'credentials.json').exists()


def test_excel_roles_login_and_preservation(tmp_path):
    app = create_app(tmp_path/'data', bytes(range(32)), secure=False)
    database = app.state.database
    with database.connect() as db:
        for role in ('teacher', 'head', 'admin'):
            db.execute('INSERT INTO users(email,name,role,department,password,fingerprint) VALUES(?,?,?,?,?,?)',
                       ('hvphi@vku.udn.vn', 'Old name', role, 'OLD', hash_password('Existing-password'), 'cert-kept'))
        before = [dict(r) for r in db.execute('SELECT * FROM users')]
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OLD','Old course','2025-2026','1','OLD',1)")
        courses = [dict(r) for r in db.execute('SELECT * FROM courses')]
    records = parse_rows([
        [1,'TS.Hồ Văn Phi','hvphi@vku.udn.vn','Existing-password','GV, TP ĐT','CNTT'],
        [2,'TS.Đặng Quang Hiển','dqhien@vku.udn.vn','Abcd1234','GV,TK','KTMT'],
        [3,'Nguyễn Thị Thùy Giang','nttgiang@vku.udn.vn',None,'ĐT','ĐT & BĐCL']])
    path = tmp_path/'credentials.json'
    result = sync_accounts(database, records, path)
    assert result['created'] == 4
    client = TestClient(app)
    labels = {'GV':'teacher', 'TK':'head', 'ĐT':'training', 'admin':'admin'}
    for account in result['accounts']:
        response = client.post('/api/login', json={'email':account['email'], 'password':account['password'], 'role':labels[account['role']]})
        assert response.status_code == 200
        assert response.json()['user']['role'] == labels[account['role']]
        if account['email'] == 'nttgiang@vku.udn.vn':
            assert len(account['password']) == 8
    again = sync_accounts(database, records, path)
    assert again['created'] == again['updated'] == 0
    assert again['accounts'] == result['accounts']
    with database.connect() as db:
        for user in before:
            after = dict(db.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone())
            assert after['fingerprint'] == user['fingerprint']
            if user['role'] != 'teacher':
                assert after == user
        assert [dict(r) for r in db.execute('SELECT * FROM courses')] == courses
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert all(a['password'] not in row['details'] for a in result['accounts'] for row in db.execute('SELECT * FROM audit'))
    blank = parse_rows([[1,'Hồ Văn Phi','hvphi@vku.udn.vn',None,'GV','CNTT']])
    with database.connect() as db:
        hashed = db.execute('SELECT password FROM users WHERE id=1').fetchone()[0]
    sync_accounts(database, blank, tmp_path/'unknown-password.json')
    with database.connect() as db:
        assert db.execute('SELECT password FROM users WHERE id=1').fetchone()[0] == hashed


@pytest.mark.parametrize('change', [(2,'bad@email.org'), (4,'GV,UNKNOWN'), (1,'=BAD()'), (4,'GV,GV')])
def test_excel_rejects_invalid_data(change):
    row = [1,'Some Name','name@vku.udn.vn','Abcd1234','GV','CNTT']
    row[change[0]] = change[1]
    with pytest.raises(ValueError):
        parse_rows([row])
    with pytest.raises(ValueError, match='trùng'):
        parse_rows([[1,'Some Name','name@vku.udn.vn',None,'GV','CNTT']] * 2)


def test_authoritative_excel_role_count():
    if not Path('Acc/DS_tai_khoan_GV_VKU.xlsx').exists():
        pytest.skip('Private account workbook is not included in source distribution.')
    rows = read_accounts('Acc/DS_tai_khoan_GV_VKU.xlsx')
    assert len(rows) == 197
    assert sum('head' in r['roles'] for r in rows) == 10
