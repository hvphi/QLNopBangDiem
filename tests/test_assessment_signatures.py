import pytest
from backend.assessment import guidance_course, requires_two_teachers
from tests.fixtures import unsigned_pdf
from tests.test_system import env, pki, pdfs, login, submit, head


@pytest.mark.parametrize('title', ['Đồ án cơ sở 4 (32)','ĐỀ ÁN tốt nghiệp','Thực tập doanh nghiệp (25)','Kiến tập (1)'])
def test_guidance_classification(title):
    assert guidance_course(title)
    assert not requires_two_teachers({'title':title},'final')
    assert not guidance_course('Cơ sở dữ liệu (1)_TA')
    assert requires_two_teachers({'title':'Cơ sở dữ liệu'},'final')
    assert not requires_two_teachers({'title':'Cơ sở dữ liệu'},'component')


def test_assignment_admin_only_and_distinct_active_teacher(env,pdfs):
    app,_=env;gv,admin=login(app,1),login(app,4)
    endpoint='/api/admin/courses/1/co-teacher'
    assert gv.patch(endpoint,json={'co_teacher_id':5}).status_code==403
    for uid in (1,2,999):
        assert admin.patch(endpoint,json={'co_teacher_id':uid}).status_code==422
    assert admin.patch(endpoint,json={'co_teacher_id':None}).status_code==200
    assert submit(gv,pdfs[1]).status_code==200
    assert admin.patch(endpoint,json={'co_teacher_id':7}).status_code==200
    assert submit(gv,pdfs[1]).status_code==409
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'final':'submitted'}
    assert login(app,7).get('/api/submissions').json()['total']==0


def test_regular_final_rejects_missing_wrong_or_duplicate_gv_signatures(env,pki,pdfs):
    app,_=env;gv=login(app,1)
    one=pki.sign(unsigned_pdf(),0)
    response=submit(gv,one);assert response.status_code==422 and 'đúng 2 chữ ký' in response.text
    assert submit(gv,one,assessment_type='other').status_code==422
    wrong=pki.sign(one,1)
    assert submit(gv,wrong).status_code==422
    with app.state.database.connect() as db:
        db.execute('UPDATE users SET fingerprint=? WHERE id=7',(pki.fingerprints[0],))
    same=pki.sign(one,0,field_name='SecondTeacher')
    response=submit(gv,same);assert response.status_code==422 and 'hai GV khác nhau' in response.text
    assert gv.get('/api/submissions').json()['total']==0


def test_three_signature_workflow_keeps_submission_assignment_snapshot(env,pdfs):
    app,_=env;gv,tk,dt,admin=login(app,1),login(app,2),login(app,3),login(app,4)
    assert submit(gv,pdfs[1]).status_code==200
    assert len(gv.get('/api/submissions/1/verification').json()['signatures'])==2
    assert admin.patch('/api/admin/courses/1/co-teacher',json={'co_teacher_id':5}).status_code==200
    assert head(tk,pdfs[1]).status_code==422
    assert head(tk,pdfs[2]).status_code==200
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'final':'head_signed'}
    reports=dt.get('/api/submissions/1/verification').json()['signatures']
    assert [r['signer_name'] for r in reports]==['Teacher','SecondTeacher','Head']
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'final':'archived'}
    assert gv.get('/api/submissions/1/pdf').content==pdfs[2]
    with app.state.database.connect() as db:
        assert db.execute('SELECT second_teacher_id FROM submissions').fetchone()[0]==7


def test_guidance_council_keeps_one_gv_then_head(env,pki):
    app,_=env
    with app.state.database.connect() as db:
        db.execute("UPDATE courses SET title='Đồ án tốt nghiệp (1)',co_teacher_id=NULL WHERE id=1")
    one=pki.sign(unsigned_pdf(title='Đồ án tốt nghiệp (1)'),0)
    two=pki.sign(one,1)
    gv,tk=login(app,1),login(app,2)
    assert submit(gv,one).status_code==200
    assert head(tk,two).status_code==200


def test_courses_submission_flags_per_type_and_independent_of_filters(env,pki,pdfs):
    app,_=env;gv,tk=login(app,1),login(app,2)
    assert gv.get('/api/courses').json()[0]['submitted_assessments']==[]
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={}
    assert submit(gv,pdfs[1]).status_code==200
    assert gv.get('/api/submissions?year=1999-2000').json()['total']==0
    assert gv.get('/api/courses').json()[0]['submitted_assessments']==['final']
    assert tk.post('/api/submissions/1/reject',json={'version':1,'reason':'Kiểm tra lại'}).status_code==200
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'final':'rejected'}
    assert gv.get('/api/courses').json()[0]['submitted_assessments']==['final']
    component=pki.sign(unsigned_pdf(assessment_type='component'),0)
    assert submit(gv,component,assessment_type='component').status_code==200
    assert gv.get('/api/courses').json()[0]['submitted_assessments']==['component','final']
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'component':'submitted','final':'rejected'}
    assert login(app,5).get('/api/courses').json()==[]


def test_course_assessment_complete_only_when_all_documents_archived(env):
    app,_=env;gv=login(app,1)
    with app.state.database.connect() as db:
        for status,kind in [('archived','final'),('head_signed','final'),('submitted','final'),('archived','component')]:
            db.execute('INSERT INTO submissions(course_id,teacher_id,status,updated_at,assessment_type) VALUES(1,1,?,CURRENT_TIMESTAMP,?)',(status,kind))
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'final':'submitted','component':'archived'}
    assert gv.get('/api/submissions?year=1999-2000').json()['total']==0
    with app.state.database.connect() as db:
        db.execute("UPDATE submissions SET status='head_signed' WHERE status='submitted'")
    assert gv.get('/api/courses').json()[0]['assessment_statuses']['final']=='head_signed'
    with app.state.database.connect() as db:
        db.execute("UPDATE submissions SET status='archived'")
    assert gv.get('/api/courses').json()[0]['assessment_statuses']=={'final':'archived','component':'archived'}


@pytest.mark.parametrize('configured',[None,5])
def test_second_signer_not_teaching_course_or_department(env,pdfs,configured):
    app,_=env;gv,tk,dt=login(app,1),login(app,2),login(app,3)
    with app.state.database.connect() as db:
        db.execute('UPDATE courses SET co_teacher_id=?',(configured,))
        db.execute("UPDATE users SET department='KINHTE' WHERE id=7")
        assert not db.execute('SELECT id FROM courses WHERE teacher_id=7').fetchall()
    assert submit(gv,pdfs[1]).status_code==200
    with app.state.database.connect() as db:
        assert db.execute('SELECT second_teacher_id FROM submissions').fetchone()[0]==7
    assert head(tk,pdfs[2]).status_code==200
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200
    assert gv.get('/api/submissions/1/pdf').content==pdfs[2]
    assert login(app,7).get('/api/courses').json()==[]
    assert login(app,7).get('/api/submissions').json()['total']==0


@pytest.mark.parametrize('change',['inactive','unknown','ambiguous'])
def test_second_signer_must_match_unique_active_teacher(env,pdfs,change):
    app,_=env;gv=login(app,1)
    with app.state.database.connect() as db:
        if change=='inactive':
            db.execute('UPDATE users SET active=0 WHERE id=7')
        elif change=='unknown':
            db.execute("UPDATE users SET fingerprint='' WHERE id=7")
        else:
            db.execute('UPDATE users SET fingerprint=(SELECT fingerprint FROM users WHERE id=7) WHERE id=5')
    response=submit(gv,pdfs[1])
    assert response.status_code==422 and 'khớp duy nhất' in response.text
    assert gv.get('/api/submissions').json()['total']==0
