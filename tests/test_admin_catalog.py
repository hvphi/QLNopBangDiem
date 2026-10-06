from fastapi.testclient import TestClient
from backend.auth import verify_password
from backend.db import Database
from tests.test_system import env, pki, login
from tests.fixtures import PASSWORD


def test_departments_crud_dynamic_statistics_and_used_delete(env):
    app,_=env;admin=login(app,4)
    body={'code':'TEST','name':'Khoa thử','statistical':True}
    assert admin.post('/api/admin/departments',json=body).status_code==200
    assert admin.post('/api/admin/departments',json=body).status_code==409
    assert admin.put('/api/admin/departments/TEST',json={**body,'name':'Khoa đổi'}).status_code==200
    rows=login(app,3).get('/api/statistics/departments').json()['items']
    assert next(r for r in rows if r['department']=='TEST')['department_name']=='Khoa đổi'
    assert admin.delete('/api/admin/departments/CNTT').status_code==409
    assert admin.delete('/api/admin/departments/TEST').status_code==200
    Database(app.state.database.path)
    assert all(r['code']!='TEST' for r in admin.get('/api/admin/departments').json())
    assert admin.put('/api/admin/departments/CNTT',json={'code':'NEW','name':'X'}).status_code==422


def test_accounts_crud_password_sessions_multi_role(env):
    app,_=env;admin=login(app,4)
    body={'name':'Người thử','email':'new@vku.udn.vn','password':PASSWORD,'role':'teacher','department':'KTS'}
    response=admin.post('/api/admin/users',json=body);assert response.status_code==200
    uid=response.json()['id']
    assert admin.post('/api/admin/users',json=body).status_code==409
    another=admin.post('/api/admin/users',json={**body,'role':'head'});assert another.status_code==200
    c=TestClient(app);assert c.post('/api/login',json={'email':body['email'],'password':PASSWORD,'role':'teacher'}).status_code==200
    update={'active':True,'fingerprint':'','name':'Đã sửa','email':'changed@vku.udn.vn','role':'teacher','department':'CB','password':''}
    assert admin.patch(f'/api/admin/users/{uid}',json=update).status_code==200
    assert c.get('/api/me').status_code==401
    with app.state.database.connect() as db:
        assert verify_password(PASSWORD,db.execute('SELECT password FROM users WHERE id=?',(uid,)).fetchone()[0])
    assert admin.patch(f'/api/admin/users/{uid}',json={**update,'password':'New-Password-2026!'}).status_code==200
    assert c.post('/api/login',json={'email':'changed@vku.udn.vn','password':'New-Password-2026!','role':'teacher'}).status_code==200
    assert admin.delete(f'/api/admin/users/{uid}').status_code==409 # login audit must be retained
    assert admin.delete('/api/admin/users/'+str(another.json()['id'])).status_code==200
    assert all('password' not in r for r in admin.get('/api/admin/users').json())


def test_accounts_protect_self_links_validation_and_role_conflict(env):
    app,_=env;admin=login(app,4)
    assert admin.delete('/api/admin/users/4').status_code==422
    assert admin.delete('/api/admin/users/1').status_code==409
    assert admin.patch('/api/admin/users/4',json={'active':False}).status_code==422
    assert admin.patch('/api/admin/users/4',json={'active':True,'role':'teacher'}).status_code==422
    assert admin.patch('/api/admin/users/1',json={'active':True,'role':'head'}).status_code==409
    assert admin.patch('/api/admin/users/1',json={'active':True,'department':'CB'}).status_code==409
    assert admin.patch('/api/admin/users/1',json={'active':True,'email':'x@evil.vn'}).status_code==422
    assert admin.patch('/api/admin/users/1',json={'active':True,'password':'short'}).status_code==422
    body={'name':'X','email':'x@vku.udn.vn','password':PASSWORD,'role':'teacher','department':'Unknown'}
    assert admin.post('/api/admin/users',json=body).status_code==422
    assert admin.delete('/api/admin/users/9999').status_code==404


def test_catalog_rbac_and_csrf(env):
    app,_=env
    for uid in (1,2,3):
        c=login(app,uid)
        assert c.get('/api/admin/departments').status_code==403
        assert c.delete('/api/admin/departments/CNTT').status_code==403
        assert c.delete('/api/admin/users/1').status_code==403
    assert TestClient(app).get('/api/admin/departments').status_code==401
    admin=login(app,4);admin.headers.pop('X-CSRF-Token')
    assert admin.post('/api/admin/departments',json={'code':'X','name':'X'}).status_code==403


def test_department_migration_preserves_legacy_units(tmp_path):
    path=tmp_path/'legacy.sqlite3';database=Database(path)
    with database.connect() as db:
        db.execute('DROP TABLE departments')
        db.execute("INSERT INTO users(email,name,role,department,password) VALUES('legacy@vku.udn.vn','Legacy','admin','ĐT & BĐCL','unchanged')")
    migrated=Database(path)
    with migrated.connect() as db:
        assert db.execute("SELECT statistical FROM departments WHERE code='ĐT & BĐCL'").fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM departments').fetchone()[0]==8
        assert db.execute('SELECT password FROM users').fetchone()[0]=='unchanged'
