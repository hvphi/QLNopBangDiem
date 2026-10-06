import json
import pytest
import openpyxl
from backend.db import Database, now
from scripts.sync_timetable_departments import read_timetable, read_teacher_accounts, plan_import, apply_plan


def database(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    with db.connect() as c:
        c.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(1,'hvphi@vku.udn.vn','Hồ Văn Phi','teacher','CNTT','unchanged')")
        c.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(2,'hvphi@vku.udn.vn','Hồ Văn Phi','head','CNTT','unchanged')")
    return db


def account(name='Hồ Văn Phi', email='hvphi@vku.udn.vn', department='AIDS'):
    return dict(name=name, email=email, department=department)


def row(teacher='TS.Hồ Văn Phi', course='Cơ sở dữ liệu (1)', schedule='Thứ Hai', source_id='1'):
    return dict(teacher=teacher, course=course, schedule=schedule, room='A1', weeks='1-15', source_id=source_id)


def test_upsert_preserves_submission_and_password_and_is_idempotent(tmp_path):
    db = database(tmp_path)
    plan = plan_import(db, [row(), row(schedule='Thứ Ba'), row()], [account()], {'AIDS': 'Khoa AI'}, '2026-2027', '1')
    assert plan['counts'] == {'AIDS': 1}
    assert len(plan['courses'][0]['assignments']) == 2
    assert apply_plan(db, plan) == {'created': 1, 'updated': 0}
    with db.connect() as c:
        cid = c.execute('SELECT id FROM courses').fetchone()[0]
        c.execute("UPDATE courses SET department='CNTT'")
        c.execute("INSERT INTO submissions(course_id,teacher_id,status,updated_at) VALUES(?,1,'archived',?)", (cid, now()))
    assert apply_plan(db, plan) == {'created': 0, 'updated': 1}
    assert apply_plan(db, plan) == {'created': 0, 'updated': 0}
    with db.connect() as c:
        assert c.execute('SELECT course_id,status FROM submissions').fetchone()[:] == (cid, 'archived')
        assert c.execute('SELECT COUNT(*) FROM courses').fetchone()[0] == 1
        assert c.execute('SELECT password FROM users WHERE id=1').fetchone()[0] == 'unchanged'


def test_missing_ambiguous_unknown_department_and_inactive_are_unresolved(tmp_path):
    db = database(tmp_path)
    for accounts, teacher in [([], 'TS.Hồ Văn Phi'), ([account(), account(email='other@vku.udn.vn')], 'Ho Van Phi'),
                              ([account(department='Unknown')], 'TS.Hồ Văn Phi'), ([account(email='missing@vku.udn.vn')], 'TS.Hồ Văn Phi')]:
        plan = plan_import(db, [row(teacher)], accounts, {'AIDS': 'AI'}, '2026-2027', '1')
        assert not plan['courses'] and len(plan['unresolved']) == 1


def test_titles_of_different_teachers_stay_separate_and_accent_fallback_matches(tmp_path):
    db = database(tmp_path)
    with db.connect() as c:
        c.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(3,'other@vku.udn.vn','Lê Văn An','teacher','AIDS','unchanged')")
    plan = plan_import(db, [row('TS.  Ho Van Phi'), row('ThS.Lê Văn An')],
                       [account(), account('Lê Văn An', 'other@vku.udn.vn')], {'AIDS': 'AI'}, '2026-2027', '1')
    assert len(plan['courses']) == 2 and len(plan['shared_titles']) == 1
    assert len({c['code'] for c in plan['courses']}) == 2


def test_rowspan_and_source_period(tmp_path):
    html = '''<select class="namhoc"><option selected value="10">Năm học 2026 - 2027</option></select>
    <select class="hocky"><option selected value="1">Học kỳ 1</option></select><tbody class="lophocphan">
    <tr><td rowspan="2">1</td><td rowspan="2">Cơ sở dữ liệu (1)</td><td rowspan="2">TS.Hồ Văn Phi</td>
    <td>Thứ Hai</td><td>A1</td><td>1-15</td><td rowspan="2">60</td><td><a href="/noidunggiangday/123">link</a></td></tr>
    <tr><td>Thứ Ba</td><td>A2</td><td>2-15</td><td><a href="/noidunggiangday/124">link</a></td></tr></tbody>'''
    path = tmp_path / 'timetable.html'
    path.write_text(html, encoding='utf-8')
    rows = read_timetable(path, '2026-2027', '1')
    assert len(rows) == 2 and rows[1]['teacher'] == 'TS.Hồ Văn Phi'
    assert rows[1]['course'] == rows[0]['course'] and rows[1]['schedule'] == 'Thứ Ba'
    assert rows[1]['source_id'] == '124'
    with pytest.raises(ValueError, match='Học kỳ'):
        read_timetable(path, '2025-2026', '1')


def test_excel_multiple_roles_deduplicate_and_ignore_password_column(tmp_path):
    path = tmp_path / 'accounts.xlsx'
    wb = openpyxl.Workbook()
    wb.active.title = 'Danh muc Khoa'
    wb.active.append(['STT', 'Mã khoa', 'Tên'])
    wb.active.append([1, 'AIDS', 'AI'])
    ws = wb.create_sheet('Tai khoan VKU')
    ws.append(['STT', 'Họ và tên', 'Email đăng nhập', 'Mật khẩu', 'Vai trò', 'Khoa / Đơn vị'])
    ws.append([1, 'Hồ Văn Phi', 'hvphi@vku.udn.vn', '=SECRET()', 'GV, TK', 'AIDS'])
    ws.append([2, 'Hồ Văn Phi', 'hvphi@vku.udn.vn', '=SECRET()', 'TK', 'AIDS'])
    wb.save(path)
    accounts, units = read_teacher_accounts(path)
    assert accounts == [account()] and units == {'AIDS': 'AI'}
    assert 'password' not in json.dumps(accounts)


def test_changed_permissions_roll_back_entire_import(tmp_path):
    db = database(tmp_path)
    plan = plan_import(db, [row()], [account()], {'AIDS': 'AI'}, '2026-2027', '1')
    with db.connect() as c:
        c.execute('UPDATE users SET active=0 WHERE id=1')
    with pytest.raises(ValueError, match='Quyền GV'):
        apply_plan(db, plan)
    with db.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM courses').fetchone()[0] == 0
