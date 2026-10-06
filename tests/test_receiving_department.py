from fastapi.testclient import TestClient
from backend.db import Database
from tests.test_system import env, pki, pdfs, login, head


def upload(client,data,department=None,**extra):
    body={'course_id':1,**extra}
    if department is not None:body['receiving_department']=department
    return client.post('/api/submissions',data=body,files={'file':('grade.pdf',data,'application/pdf')})


def test_default_and_invalid_recipient(env,pdfs):
    app,_=env;gv=login(app,1)
    assert TestClient(app).get('/api/departments').status_code==401
    codes={r['code'] for r in gv.get('/api/departments').json()}
    assert {'CNTT','KTS','KTMT','AIDS','CB'}<=codes
    assert 'VKU' not in codes
    for bad in ('UNKNOWN','VKU'):
        assert upload(gv,pdfs[1],bad).status_code==422
    with app.state.database.connect() as db:db.execute("UPDATE courses SET department='KTS' WHERE id=1")
    assert upload(gv,pdfs[1]).status_code==200
    row=gv.get('/api/submissions').json()['items'][0]
    assert row['department']==row['receiving_department']=='CNTT'
    assert row['course_department']=='KTS'


def test_cross_department_scopes_and_real_signing(env,pdfs):
    app,_=env
    with app.state.database.connect() as db:db.execute("UPDATE users SET department='KTS' WHERE id=6")
    gv,old,new,dt=login(app,1),login(app,2),login(app,6),login(app,3)
    assert upload(gv,pdfs[1],'KTS').status_code==200
    assert old.get('/api/submissions').json()['total']==0
    assert new.get('/api/submissions').json()['total']==1
    assert new.get('/api/submissions?department=KTS').json()['total']==1
    assert new.get('/api/submissions?department=CNTT').json()['total']==0
    assert any(c['id']==1 for c in new.get('/api/courses').json())
    for path in ('/api/submissions/1/pdf','/api/submissions/1/verification'):
        assert old.get(path).status_code==403
    assert old.post('/api/submissions/1/reject',json={'version':1,'reason':'X'}).status_code==403
    assert head(old,pdfs[2]).status_code==403
    assert new.get('/api/submissions/1/pdf').content==pdfs[1]
    assert head(new,pdfs[2]).status_code==200
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200
    assert dt.get('/api/submissions/1/pdf').content==pdfs[2]
    with app.state.database.connect() as db:
        assert db.execute('SELECT department FROM courses WHERE id=1').fetchone()[0]=='CNTT'
        assert db.execute('SELECT department FROM users WHERE id=1').fetchone()[0]=='CNTT'


def test_resubmit_can_change_recipient_only_when_rejected(env,pdfs):
    app,_=env
    with app.state.database.connect() as db:db.execute("UPDATE users SET department='KTS' WHERE id=6")
    gv,old,new=login(app,1),login(app,2),login(app,6)
    assert upload(gv,pdfs[1],'KTS').status_code==200
    assert upload(gv,pdfs[1],'CNTT',submission_id=1,version=1).status_code==409
    assert new.post('/api/submissions/1/reject',json={'version':1,'reason':'Sửa lại'}).status_code==200
    assert upload(gv,pdfs[1],None,submission_id=1,version=2).status_code==200
    assert gv.get('/api/submissions').json()['items'][0]['receiving_department']=='KTS'
    assert new.post('/api/submissions/1/reject',json={'version':3,'reason':'Sửa lại'}).status_code==200
    assert upload(gv,pdfs[1],'CNTT',submission_id=1,version=4).status_code==200
    assert old.get('/api/submissions').json()['total']==1
    assert new.get('/api/submissions').json()['total']==0
    assert new.get('/api/submissions/1/pdf').status_code==403


def test_recipient_migration_and_delete_protection(env,pdfs):
    app,_=env;gv=login(app,1);admin=login(app,4)
    assert upload(gv,pdfs[1],'KTS').status_code==200
    assert admin.delete('/api/admin/departments/KTS').status_code==409
    database=app.state.database
    Database(database.path)
    assert gv.get('/api/submissions').json()['items'][0]['receiving_department']=='KTS'
    with database.connect() as db:
        old_versions=[tuple(r) for r in db.execute('SELECT * FROM versions')]
        db.execute('ALTER TABLE submissions DROP COLUMN receiving_department')
    Database(database.path)
    with database.connect() as db:
        assert db.execute('SELECT receiving_department FROM submissions').fetchone()[0]=='CNTT'
        assert [tuple(r) for r in db.execute('SELECT * FROM versions')]==old_versions
