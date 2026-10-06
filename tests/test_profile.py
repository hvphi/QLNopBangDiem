import pytest
from fastapi.testclient import TestClient
from backend.auth import verify_password
from tests.test_system import env, pki, login
from tests.fixtures import PASSWORD

NEW = 'New-Profile-Password-2026!'


@pytest.mark.parametrize('uid', [1, 2, 3, 4])
def test_profile_all_roles_self_only(env, uid):
    app,_ = env
    client = login(app, uid)
    original = client.get('/api/me').json()['user']
    result = client.patch('/api/me/profile', json={'name':'  Tên đã sửa  '})
    assert result.status_code == 200
    assert result.json()['user'] == {**original, 'name':'Tên đã sửa'}
    assert 'password' not in result.text
    assert client.patch('/api/me/profile', json={'name':'X','role':'admin'}).status_code == 422
    assert client.patch('/api/me/profile', json={'name':'X','email':'x@vku.udn.vn'}).status_code == 422
    assert client.patch('/api/me/profile', json={'name':'X','department':'KTS'}).status_code == 422
    assert client.patch('/api/me/profile', json={'name':'   '}).status_code == 422


def test_password_validation_csrf_and_throttle(env):
    app,_=env
    client=login(app,1)
    body={'current_password':PASSWORD,'new_password':NEW,'confirm_password':NEW}
    assert TestClient(app).post('/api/me/password',json=body).status_code==401
    client.headers.pop('X-CSRF-Token')
    assert client.patch('/api/me/profile',json={'name':'X'}).status_code==403
    assert client.post('/api/me/password',json=body).status_code==403
    client.headers['X-CSRF-Token']=client.get('/api/me').json()['csrf']
    assert client.post('/api/me/password',json={**body,'new_password':'short'}).status_code==422
    assert client.post('/api/me/password',json={**body,'confirm_password':'other'}).status_code==422
    assert client.post('/api/me/password',json={**body,'new_password':PASSWORD,'confirm_password':PASSWORD}).status_code==422
    for _ in range(5):
        assert client.post('/api/me/password',json={**body,'current_password':'wrong'}).status_code==422
    assert client.post('/api/me/password',json=body).status_code==429
    with app.state.database.connect() as db:
        assert verify_password(PASSWORD,db.execute('SELECT password FROM users WHERE id=1').fetchone()[0])


def test_shared_email_profile_password_revokes_sessions_and_preserves_others(env):
    app,_=env
    with app.state.database.connect() as db:
        db.execute("UPDATE users SET email='shared@vku.udn.vn' WHERE id IN (1,2,3,4)")
    clients=[]
    for role in ('teacher','head','training','admin'):
        c=TestClient(app)
        r=c.post('/api/login',json={'email':'shared@vku.udn.vn','role':role,'password':PASSWORD})
        assert r.status_code==200
        c.headers['X-CSRF-Token']=r.json()['csrf'];clients.append(c)
    other=login(app,5)
    assert clients[0].patch('/api/me/profile',json={'name':'Tên chung'}).status_code==200
    assert all(c.get('/api/me').json()['user']['name']=='Tên chung' for c in clients)
    body={'current_password':PASSWORD,'new_password':NEW,'confirm_password':NEW}
    response=clients[0].post('/api/me/password',json=body)
    assert response.status_code==200
    assert 'Max-Age=0' in response.headers['set-cookie']
    assert all(c.get('/api/me').status_code==401 for c in clients)
    assert other.get('/api/me').status_code==200
    old_login=TestClient(app).post('/api/login',json={'email':'shared@vku.udn.vn','role':'teacher','password':PASSWORD})
    assert old_login.status_code==401
    for role in ('teacher','head','training','admin'):
        c=TestClient(app)
        assert c.post('/api/login',json={'email':'shared@vku.udn.vn','role':role,'password':NEW}).status_code==200
    with app.state.database.connect() as db:
        assert all(verify_password(NEW,r[0]) for r in db.execute('SELECT password FROM users WHERE id IN (1,2,3,4)'))
        assert verify_password(PASSWORD,db.execute('SELECT password FROM users WHERE id=5').fetchone()[0])
        logs=[dict(r) for r in db.execute("SELECT * FROM audit WHERE action IN ('change_password','update_profile')")]
        assert len(logs)==2
        assert all(NEW not in str(r) and PASSWORD not in str(r) for r in logs)
