from backend.db import now
from tests.test_system import env, pki, login


def test_department_statistics_counts_courses_and_filters(env):
    app,_=env
    with app.state.database.connect() as db:
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OTHER','Other','2025-2026','2','KTS',1)")
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('EMPTY','Empty','2024-2025','1','CNTT',1)")
        for kind,status in [('component','rejected'),('final','archived')]:
            db.execute('INSERT INTO submissions(course_id,teacher_id,assessment_type,status,updated_at) VALUES(1,1,?,?,?)',(kind,status,now()))
    dt=login(app,3)
    endpoint='/api/statistics/departments'
    result=dt.get(endpoint).json()
    assert len(result['items'])==5
    units={row['department']:row for row in result['items']}
    assert units['CNTT']['total_courses']==2 and units['CNTT']['submitted_courses']==1
    assert units['KTS']['total_courses']==1 and units['KTS']['submitted_courses']==0
    assert units['AIDS']['department_name']=='Khoa Trí tuệ nhân tạo và Khoa học dữ liệu'
    assert units['CB']['total_courses']==0 and units['CB']['submitted_courses']==0
    assert set(units)=={'CNTT','KTMT','KTS','AIDS','CB'}
    assert result['total_courses']==3 and result['submitted_courses']==1
    filtered=dt.get(endpoint,params={'year':'2025-2026','semester':'1'}).json()
    assert filtered['total_courses']==1 and filtered['submitted_courses']==1
    assert dt.get(endpoint,params={'department':'KTS'}).json()['submitted_courses']==0
    empty=dt.get(endpoint,params={'year':'2099-2100'}).json()
    assert len(empty['items'])==5 and empty['total_courses']==0 and empty['submitted_courses']==0
    assert all(row['total_courses']==0 for row in empty['items'])
    with app.state.database.connect() as db:
        db.execute("UPDATE submissions SET status='rejected' WHERE course_id=1")
    assert dt.get(endpoint).json()['submitted_courses']==1
    assert dt.get(endpoint,params={'q':'none','status':'submitted','page':'99'}).json()==result
    assert len(dt.get(endpoint,params={'department':'CB'}).json()['items'])==1
    with app.state.database.connect() as db:
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('UNKNOWN','Other unit','2025-2026','1','Khác',1)")
    extended=dt.get(endpoint).json()
    assert len(extended['items'])==6 and extended['total_courses']==4


def test_department_statistics_training_only(env):
    app,_=env
    for uid in (1,2,4):assert login(app,uid).get('/api/statistics/departments').status_code==403
    from fastapi.testclient import TestClient
    assert TestClient(app).get('/api/statistics/departments').status_code==401


def test_department_details_scope_counts_and_safe_fields(env):
    app,_=env
    with app.state.database.connect() as db:
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OLD','Old','2024-2025','2','CNTT',1)")
        db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OTHER','Other','2025-2026','1','KTS',1)")
        for kind in ('component','final'):
            db.execute("INSERT INTO submissions(course_id,teacher_id,assessment_type,status,updated_at) VALUES(1,1,?,'rejected',?)",(kind,now()))
    dt=login(app,3)
    endpoint='/api/statistics/departments/CNTT/details'
    result=dt.get(endpoint,params={'year':'2025-2026','semester':'1'}).json()
    assert result['total_courses']==1 and result['submitted_courses']==1
    assert len(result['teachers'])==1
    teacher=result['teachers'][0]
    assert teacher['id']==1 and teacher['total_courses']==1 and teacher['submitted_courses']==1
    assert set(teacher)=={'id','name','email','total_courses','submitted_courses','courses'}
    assert set(teacher['courses'][0])=={'id','code','title','year','semester','submitted'}
    assert teacher['courses'][0]['submitted']==1
    all_years=dt.get(endpoint).json()
    assert all_years['total_courses']==2 and all_years['submitted_courses']==1
    other=dt.get('/api/statistics/departments/KTS/details').json()
    assert other['total_courses']==1 and other['submitted_courses']==0
    assert other['teachers'][0]['courses'][0]['title']=='Other'
    empty=dt.get('/api/statistics/departments/CB/details').json()
    assert empty['department_name']=='Tổ Cơ bản' and empty['teachers']==[] and empty['total_courses']==0
    assert dt.get(endpoint,params={'year':'2025-2026','semester':'2'}).json()['teachers']==[]
    assert dt.get('/api/statistics/departments/UNKNOWN/details').json()['total_courses']==0


def test_department_details_training_only(env):
    app,_=env
    for uid in (1,2,4):
        assert login(app,uid).get('/api/statistics/departments/CNTT/details').status_code==403
    from fastapi.testclient import TestClient
    assert TestClient(app).get('/api/statistics/departments/CNTT/details').status_code==401
