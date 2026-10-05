import asyncio
import io
import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from pyhanko_certvalidator import ValidationContext
from backend.app import create_app
from backend.auth import valid_email
from backend.operations import backup, restore
from backend.storage import Storage
from backend.uis import validate_metadata
from backend.verification import Verifier
from tests.fixtures import TestPKI, unsigned_pdf, seed, PASSWORD, COURSE


@pytest.fixture(scope='session')
def pki(tmp_path_factory):
    return TestPKI(tmp_path_factory.mktemp('pki'))


@pytest.fixture(scope='session')
def pdfs(pki):
    plain=unsigned_pdf();one=pki.sign(pki.sign(plain,0),2);two=pki.sign(one,1)
    return plain,one,two


@pytest.fixture
def env(tmp_path,pki):
    app=create_app(tmp_path/'data',bytes(range(32)),verifier=pki,secure=False)
    seed(app.state.database,pki)
    return app,tmp_path


def login(app,uid):
    role={1:'teacher',2:'head',3:'training',4:'admin',5:'teacher',6:'head',7:'teacher'}[uid]
    client=TestClient(app)
    response=client.post('/api/login',json={'email':f'{role}{uid}@vku.udn.vn','password':PASSWORD})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf']
    return client


def submit(client,pdf,version=0,assessment_type='final',submission_id=None,course_id=1):
    sid=submission_id if submission_id is not None else (1 if version else 0)
    return client.post('/api/submissions',data={'course_id':str(course_id),'version':str(version),'submission_id':str(sid),'assessment_type':assessment_type},files={'file':('grade.pdf',pdf,'application/pdf')})


def head(client,pdf,version=1):
    return client.post('/api/submissions/1/head-sign',data={'version':str(version)},files={'file':('grade.pdf',pdf,'application/pdf')})


def test_full_real_signed_workflow(env,pdfs):
    app,_=env
    gv,tk,dt=login(app,1),login(app,2),login(app,3)
    assert submit(gv,pdfs[1]).status_code==200
    assert head(tk,pdfs[2]).status_code==200
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200
    assert gv.get('/api/submissions').json()['items'][0]['status']=='archived'
    assert gv.get('/api/submissions/1/pdf').content==pdfs[2]
    with app.state.database.connect() as db:
        paths=[r['path'] for r in db.execute('SELECT path FROM versions')]
        assert all(p.startswith('2025-2026/1/CNTT/CSDL01/') for p in paths)
        actions=[r['action'] for r in db.execute('SELECT action FROM audit')]
        assert 'head_sign' in actions and 'archive' in actions


def test_unsigned_tampered_untrusted_and_wrong_signer(pki,pdfs,tmp_path):
    for data,expected in [(pdfs[0],[pki.fingerprints[0]]),
        (pdfs[1].replace(b'8.5',b'9.5'),[pki.fingerprints[0],pki.fingerprints[2]]),
        (pdfs[1],[pki.fingerprints[1],pki.fingerprints[2]]), (pdfs[1]+b'\n% changed',[pki.fingerprints[0],pki.fingerprints[2]])]:
        with pytest.raises(ValueError):
            asyncio.run(pki.verify(data,expected))
    v=Verifier(tmp_path)
    v.context=lambda:ValidationContext(trust_roots=[],allow_fetching=False,revocation_mode='require')
    with pytest.raises(ValueError):
        asyncio.run(v.verify(pdfs[1],[pki.fingerprints[0],pki.fingerprints[2]]))


def test_no_trust_config_fails_closed(tmp_path,pki,pdfs):
    with pytest.raises(ValueError,match='Chưa cấu hình'):
        asyncio.run(Verifier(tmp_path).verify(pdfs[1],[pki.fingerprints[0],pki.fingerprints[2]]))


def test_revoked_certificate_rejected(tmp_path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from asn1crypto import crl as asn_crl
    pki=TestPKI(tmp_path/'revoked')
    signed=pki.sign(unsigned_pdf(),0)
    t=datetime.now(timezone.utc)
    entry=x509.RevokedCertificateBuilder().serial_number(pki.signers[0].signing_cert.serial_number).revocation_date(t-timedelta(hours=2)).build()
    crl=x509.CertificateRevocationListBuilder().issuer_name(pki.ca_cert.subject).last_update(t-timedelta(hours=1)).next_update(t+timedelta(days=1)).add_revoked_certificate(entry).sign(pki.ca_key,hashes.SHA256())
    pki.crl=asn_crl.CertificateList.load(crl.public_bytes(serialization.Encoding.DER))
    with pytest.raises(ValueError):asyncio.run(pki.verify(signed,[pki.fingerprints[0]]))


def test_grade_form_change_between_signatures_rejected(pki):
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.pdf_utils import generic
    from pyhanko.sign import signers
    one=pki.sign(unsigned_pdf(with_form=True),0)
    writer=IncrementalPdfFileWriter(io.BytesIO(one))
    fields=writer.root['/AcroForm']['/Fields']
    grade=next(ref for ref in fields if ref.get_object().get('/T')=='Grade')
    grade.get_object()[generic.pdf_name('/V')]=generic.pdf_string('9.5')
    writer.mark_update(grade)
    altered=signers.sign_pdf(writer,signature_meta=signers.PdfSignatureMetadata(field_name='Head'),signer=pki.signers[1]).getvalue()
    assert altered.startswith(one)
    with pytest.raises(ValueError):asyncio.run(pki.verify(altered,pki.fingerprints[:2]))


def test_metadata_wrong_year_and_domain(pdfs):
    validate_metadata(pdfs[1],COURSE)
    with pytest.raises(ValueError):validate_metadata(pdfs[1],{**COURSE,'year':'2024-2025'})
    for value in ['gv@vku.udn.vn.evil','gv@evil-vku.udn.vn','gv@gmail.com']:
        assert not valid_email(value)
    assert valid_email('GV@vku.udn.vn')


def test_rbac_csrf_and_scope(env,pdfs):
    app,_=env
    gv,other,wrong_head=login(app,1),login(app,5),login(app,6)
    assert submit(gv,pdfs[1]).status_code==200
    assert other.get('/api/submissions').json()['total']==0
    assert other.get('/api/submissions/1/pdf').status_code==403
    assert wrong_head.get('/api/submissions/1/pdf').status_code==403
    assert other.get('/api/courses/1/export').status_code==403
    assert other.post('/api/admin/users',json={}).status_code==422
    assert gv.get('/api/admin/users').status_code==403
    assert head(gv,pdfs[2]).status_code==403
    del gv.headers['X-CSRF-Token']
    assert gv.post('/api/logout').status_code==403


def test_training_reject_after_session_rotation_requires_fresh_csrf(env,pdfs):
    app,_=env;gv,tk,dt=login(app,1),login(app,2),login(app,3)
    assert submit(gv,pdfs[1]).status_code==200
    assert head(tk,pdfs[2]).status_code==200
    old_csrf=dt.headers['X-CSRF-Token']
    rotated=dt.post('/api/login',json={'email':'training3@vku.udn.vn','password':PASSWORD})
    assert rotated.status_code==200 and rotated.json()['csrf']!=old_csrf
    body={'version':2,'reason':'Đào tạo yêu cầu kiểm tra lại.'}
    assert dt.post('/api/submissions/1/reject',json=body).status_code==403
    assert dt.get('/api/submissions').json()['items'][0]['status']=='head_signed'
    dt.headers['X-CSRF-Token']=dt.get('/api/me').json()['csrf']
    assert dt.post('/api/submissions/1/reject',json=body).status_code==200
    item=gv.get('/api/submissions').json()['items'][0]
    assert item['status']=='rejected' and item['reason']==body['reason']


def test_reject_reason_resubmit_and_stale_version(env,pdfs):
    app,_=env;gv,tk=login(app,1),login(app,2)
    assert submit(gv,pdfs[1]).status_code==200
    assert tk.post('/api/submissions/1/reject',json={'version':1,'reason':' '}).status_code==422
    assert tk.post('/api/submissions/1/reject',json={'version':1,'reason':'Cần kiểm tra điểm'}).status_code==200
    assert head(tk,pdfs[2]).status_code==409
    assert submit(gv,pdfs[1],0).status_code==409
    assert submit(gv,pdfs[1],2).status_code==200
    assert submit(gv,pdfs[1],3).status_code==409
    assert head(tk,pdfs[2],3).status_code==200
    assert head(tk,pdfs[2],3).status_code==409


def test_original_bytes_required(env,pdfs,pki):
    app,_=env;gv,tk=login(app,1),login(app,2)
    assert submit(gv,pdfs[1]).status_code==200
    different=pki.sign(pki.sign(unsigned_pdf(),0),1)
    assert head(tk,different).status_code==422


def test_deadline_locks_teacher_head_but_training_can_archive(env,pdfs):
    app,_=env;gv,tk,dt,admin=[login(app,i) for i in (1,2,3,4)]
    assert submit(gv,pdfs[1]).status_code==200
    assert head(tk,pdfs[2]).status_code==200
    past=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    assert admin.put('/api/admin/deadline',json={'deadline':past}).status_code==200
    assert submit(gv,pdfs[1]).status_code==403
    assert tk.post('/api/submissions/1/reject',json={'version':2,'reason':'x'}).status_code==403
    assert gv.get('/api/submissions/1/pdf').status_code==200
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200


def test_locked_user_session_and_invalid_admin_data(env):
    app,_=env;gv,admin=login(app,1),login(app,4)
    assert admin.patch('/api/admin/users/1',json={'active':False,'fingerprint':''}).status_code==200
    assert gv.get('/api/me').status_code==401
    assert admin.put('/api/admin/deadline',json={'deadline':'2026-01-01'}).status_code==422
    assert admin.post('/api/admin/users',json={'email':'x@vku.udn.vn.evil','password':PASSWORD,'name':'X','role':'admin','department':'X'}).status_code==422
    assert admin.patch('/api/admin/users/4',json={'active':False}).status_code==422


def test_search_and_no_archive_overwrite(env,pdfs):
    app,_=env;gv,tk,dt=login(app,1),login(app,2),login(app,3)
    assert submit(gv,pdfs[1]).status_code==200
    assert head(tk,pdfs[2]).status_code==200
    assert dt.get('/api/submissions?year=2025-2026&semester=1&department=CNTT&code=CSDL01&title=Cơ&teacher=Giảng').json()['total']==1
    assert dt.get('/api/submissions?year=2024-2025').json()['total']==0
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200
    assert dt.post('/api/submissions/1/reject',json={'version':3,'reason':'x'}).status_code==409
    assert head(tk,pdfs[2],3).status_code==409


def test_archive_revalidates_not_just_prior_report(env,pdfs,monkeypatch):
    app,_=env;gv,tk,dt=login(app,1),login(app,2),login(app,3)
    assert submit(gv,pdfs[1]).status_code==200
    assert head(tk,pdfs[2]).status_code==200
    async def invalid(*args):raise ValueError('Chứng thư đã bị thu hồi')
    monkeypatch.setattr(app.state.verifier,'verify',invalid)
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==422
    assert dt.get('/api/submissions').json()['items'][0]['status']=='head_signed'


def test_encrypted_storage_and_backup_restore(env,pdfs,tmp_path):
    app,root=env;gv=login(app,1)
    assert submit(gv,pdfs[1]).status_code==200
    files=list((root/'data/vault').rglob('*.enc'));assert len(files)==1
    assert not files[0].read_bytes().startswith(b'%PDF')
    with pytest.raises(ValueError):app.state.storage.resolve('../../escape.pdf')
    target=backup(root/'data',tmp_path/'snapshot')
    restore(target,tmp_path/'restored')
    restored=create_app(tmp_path/'restored',bytes(range(32)),app.state.verifier,secure=False)
    assert login(restored,1).get('/api/submissions/1/pdf').content==pdfs[1]
    (target/'vault'/files[0].relative_to(root/'data/vault')).write_bytes(b'corrupt')
    with pytest.raises(ValueError):restore(target,tmp_path/'bad-restore')


def test_upload_limit_and_origin(env):
    app,_=env;gv=login(app,1)
    assert gv.post('/api/submissions',data={'course_id':1},files={'file':('x.pdf',b'x'*(21*1024*1024))}).status_code==413
    assert gv.post('/api/logout',headers={'Origin':'https://evil.example'}).status_code==403


def test_backup_admin_and_scheduled_lifecycle(env,monkeypatch,tmp_path):
    app,root=env;admin=login(app,4)
    assert admin.post('/api/admin/backup').status_code==503
    assert login(app,1).get('/api/admin/operations').status_code==403
    destination=tmp_path/'periodic'
    monkeypatch.setenv('APP_BACKUP_DIR',str(destination))
    assert admin.post('/api/admin/backup').status_code==200
    assert len(list(destination.glob('*/manifest.json')))==1
    # Configuration is snapshotted at application startup, as in deployment.
    scheduled=create_app(root/'scheduled',bytes(range(32)),app.state.verifier,secure=False)
    with TestClient(scheduled):
        import time
        for _ in range(50):
            if len(list(destination.glob('*/manifest.json')))==2:break
            time.sleep(.1)
        assert len(list(destination.glob('*/manifest.json')))==2


def test_export_missing_configuration(env):
    app,_=env
    assert login(app,1).get('/api/courses/1/export').status_code==503


def test_configured_uis_export_keeps_bytes_and_filename(env,pdfs,monkeypatch,tmp_path):
    app,_=env;exports=tmp_path/'uis';exports.mkdir();(exports/'source.pdf').write_bytes(pdfs[0])
    monkeypatch.setenv('UIS_EXPORT_DIR',str(exports))
    with app.state.database.connect() as db:
        db.execute("UPDATE courses SET source_pdf='source.pdf' WHERE id=1")
    result=login(app,1).get('/api/courses/1/export')
    assert result.status_code==200 and result.content==pdfs[0]
    assert 'CSDL01_Co_so_du_lieu_1_2025-2026_Giang_vien.pdf' in result.headers['content-disposition']
    with app.state.database.connect() as db:
        db.execute("UPDATE courses SET source_pdf='../outside.pdf' WHERE id=1")
    assert login(app,1).get('/api/courses/1/export').status_code==503


def test_given_uis_sample_document_mapping():
    from pathlib import Path
    sample=Path('bang-diem-CK_N1.signed.pdf').read_bytes()
    mapped={**COURSE,'title':'Cơ sở dữ liệu (1)_GIT_TA','uis_document_id':'17210'}
    validate_metadata(sample,mapped)
    validate_metadata(sample,{**mapped,'code':'TKB-local','uis_document_id':'99999'})
    validate_metadata(sample,{**mapped,'code':'TKB-local','uis_document_id':''})


@pytest.mark.parametrize('changes,message',[
    ({'title':'Cơ sở dữ liệu (10)_TA'},'Lớp/nhóm'),
    ({'title':'Cơ sở dữ liệu (1)_TA nâng cao'},'Tên lớp'),
    ({'title':'Cơ sở dữ liệu nâng cao (1)_TA'},'Môn học'),
    ({'title':'Cơ sở dữ liệu'},'Lớp/nhóm'),
    ({'year':'2026-2027'},'Năm học'),
    ({'semester':'2'},'Học kỳ'),
])
def test_header_rejects_wrong_subject_group_and_period(changes,message):
    selected={**COURSE,'code':'TKB-local','title':'Cơ sở dữ liệu (1)_TA'}
    data=unsigned_pdf(title='Cơ sở dữ liệu (1)_TA',code='not-a-local-code',**{
        k:v for k,v in changes.items() if k in ('year','semester')}) if 'title' not in changes else unsigned_pdf(title=changes['title'],code='not-a-local-code')
    with pytest.raises(ValueError,match=message):
        validate_metadata(data,selected)


def test_signed_upload_without_uis_mapping_checks_class_and_owner(env,pki):
    app,_=env
    with app.state.database.connect() as db:
        db.execute("UPDATE courses SET code='TKB-local',title='Cơ sở dữ liệu (1)_TA' WHERE id=1")
    data=pki.sign(pki.sign(unsigned_pdf(title='Cơ sở dữ liệu (1)_TA',code=''),0),2)
    gv=login(app,1)
    assert submit(login(app,5),data).status_code==403
    response=submit(gv,data)
    assert response.status_code==200,response.text
    assert gv.get('/api/submissions/1/pdf').content==data
    wrong=pki.sign(unsigned_pdf(title='Cơ sở dữ liệu (10)_TA',code=''),0)
    assert submit(gv,wrong).status_code==422


def test_restore_rejects_absolute_manifest_paths(env,tmp_path):
    app,root=env
    snapshot=backup(root/'data',tmp_path/'malicious-snapshot')
    manifest=json.loads((snapshot/'manifest.json').read_text())
    digest=manifest['files'].pop('gradebook.sqlite3')
    manifest['files'][str(snapshot/'gradebook.sqlite3')]=digest
    (snapshot/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError):restore(snapshot,tmp_path/'malicious-restored')


def test_concurrent_head_decisions(env,pdfs):
    from concurrent.futures import ThreadPoolExecutor
    app,_=env;gv=login(app,1);assert submit(gv,pdfs[1]).status_code==200
    clients=[login(app,2),login(app,2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda c:head(c,pdfs[2]).status_code,clients))
    assert sorted(results)==[200,409]


@pytest.mark.parametrize('file_name',['bang-diem-CK_N1.signed.pdf','bang-diem-CK_N10.signed.pdf'])
def test_vgca_local_compatibility_real_sample(tmp_path,file_name):
    from pathlib import Path
    data=Path(file_name).read_bytes()
    verifier=Verifier(tmp_path/'empty-trust',policy='local')
    reports=asyncio.run(verifier.verify(data,[{'email':'hvphi@vku.udn.vn','fingerprint':''}]))
    assert reports[0]['valid'] and reports[0]['vgca_algorithm_compatibility']
    assert reports[0]['signer_name']=='Hồ Văn Phi'
    assert reports[0]['signer_emails']==['hvphi@vku.udn.vn']
    assert not reports[0]['trust_verified'] and not reports[0]['revocation_verified']
    assert Path(file_name).read_bytes()==data
    with pytest.raises(ValueError,match='Email chứng thư'):
        asyncio.run(verifier.verify(data,[{'email':'someone@vku.udn.vn','fingerprint':''}]))
    with pytest.raises(ValueError):
        asyncio.run(verifier.verify(data,[{'email':'hvphi@vku.udn.vn'},{'email':'head@vku.udn.vn'}]))


def test_local_auto_link_requires_matching_verified_email(tmp_path):
    from pathlib import Path
    from backend.auth import hash_password
    app=create_app(tmp_path/'data',bytes(range(32)),Verifier(tmp_path/'trust',policy='local'),secure=False)
    with app.state.database.connect() as db:
        db.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(1,'hvphi@vku.udn.vn','GV','teacher','CNTT',?)",(hash_password(PASSWORD),))
        db.execute("INSERT INTO courses(id,code,title,year,semester,department,teacher_id,uis_document_id) VALUES(1,'CSDL01','Cơ sở dữ liệu (1)_GIT_TA','2025-2026','1','CNTT',1,'17210')")
    data=Path('bang-diem-TP_N1.signed.pdf').read_bytes()
    client=TestClient(app)
    response=client.post('/api/login',json={'email':'hvphi@vku.udn.vn','password':PASSWORD})
    client.headers['X-CSRF-Token']=response.json()['csrf']
    assert submit(client,data,assessment_type='component').status_code==200
    assert client.get('/api/submissions/1/pdf').content==data
    report=client.get('/api/submissions/1/verification').json()['signatures'][0]
    assert report['validation_policy']=='local' and not report['trust_verified']
    with app.state.database.connect() as db:
        assert db.execute('SELECT fingerprint FROM users WHERE id=1').fetchone()['fingerprint']==report['fingerprint']
        assert db.execute("SELECT COUNT(*) FROM audit WHERE action='link_signer_certificate'").fetchone()[0]==1


def test_local_wrong_email_does_not_link_or_persist(tmp_path):
    from pathlib import Path
    from backend.auth import hash_password
    app=create_app(tmp_path/'data',bytes(range(32)),Verifier(tmp_path/'trust',policy='local'),secure=False)
    with app.state.database.connect() as db:
        db.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(1,'wrong@vku.udn.vn','GV','teacher','CNTT',?)",(hash_password(PASSWORD),))
        db.execute("INSERT INTO courses(id,code,title,year,semester,department,teacher_id,uis_document_id) VALUES(1,'CSDL01','Cơ sở dữ liệu (1)_GIT_TA','2025-2026','1','CNTT',1,'17210')")
    client=TestClient(app)
    response=client.post('/api/login',json={'email':'wrong@vku.udn.vn','password':PASSWORD})
    client.headers['X-CSRF-Token']=response.json()['csrf']
    assert submit(client,Path('bang-diem-TP_N1.signed.pdf').read_bytes(),assessment_type='component').status_code==422
    with app.state.database.connect() as db:
        assert db.execute('SELECT fingerprint FROM users WHERE id=1').fetchone()['fingerprint']==''
        assert db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0]==0


def test_local_rejects_forged_signature_even_when_digest_intact(tmp_path,pki,pdfs):
    from pyhanko.pdf_utils.reader import PdfFileReader
    data=pdfs[1]
    sig=PdfFileReader(io.BytesIO(data)).embedded_regular_signatures[0]
    offset=data.lower().find(sig.signer_info['signature'].native.hex().encode())
    assert offset>=0
    forged=bytearray(data);forged[offset]=ord('1') if forged[offset]==ord('0') else ord('0')
    verifier=Verifier(tmp_path/'trust',policy='local')
    with pytest.raises(ValueError,match='mật mã'):
        asyncio.run(verifier.verify(bytes(forged),[pki.fingerprints[0],pki.fingerprints[2]]))


def test_local_still_rejects_tamper_unsigned_and_form_changes(tmp_path,pki,pdfs):
    verifier=Verifier(tmp_path/'trust',policy='local')
    for data in (pdfs[0],pdfs[1].replace(b'8.5',b'9.5'),pdfs[1]+b'\n%changed'):
        with pytest.raises(ValueError):asyncio.run(verifier.verify(data,[pki.fingerprints[0],pki.fingerprints[2]]))


def test_local_keeps_known_fingerprint_binding(tmp_path,pki,pdfs):
    verifier=Verifier(tmp_path/'trust',policy='local')
    with pytest.raises(ValueError,match='không khớp'):
        asyncio.run(verifier.verify(pdfs[1],[{'fingerprint':pki.fingerprints[1],'email':'hvphi@vku.udn.vn'},pki.fingerprints[2]]))
    with pytest.raises(ValueError,match='Chưa liên kết'):
        asyncio.run(Verifier(tmp_path/'trust').verify(pdfs[1],[{'email':'hvphi@vku.udn.vn'}]))


def test_one_course_accepts_multiple_independent_gradebooks(env,pki,pdfs):
    app,_=env;gv,tk=login(app,1),login(app,2)
    component=pki.sign(unsigned_pdf(assessment_type='component'),0)
    first=submit(gv,component,assessment_type='component');assert first.status_code==200
    second=submit(gv,pdfs[1]);assert second.status_code==200
    assert first.json()['id']!=second.json()['id']
    sid=first.json()['id'];fid=second.json()['id']
    assert gv.get('/api/submissions?course_id=1').json()['total']==2
    assert gv.get('/api/submissions?assessment_type=component').json()['total']==1
    assert tk.post(f'/api/submissions/{sid}/reject',json={'version':1,'reason':'Sửa thành phần'}).status_code==200
    assert submit(gv,component,version=2,assessment_type='component',submission_id=sid).status_code==200
    rows={r['id']:r for r in gv.get('/api/submissions?course_id=1').json()['items']}
    assert rows[sid]['version']==3 and rows[fid]['version']==1
    assert gv.get(f'/api/submissions/{sid}/pdf').content==component
    assert gv.get(f'/api/submissions/{fid}/pdf').content==pdfs[1]
    assert gv.get(f'/api/submissions/{sid}/pdf').headers['content-disposition']!=gv.get(f'/api/submissions/{fid}/pdf').headers['content-disposition']
    assert submit(gv,pdfs[1]).status_code==409
    assert submit(gv,pdfs[1],version=3,assessment_type='final',submission_id=sid).status_code==422


def test_resubmit_cannot_select_other_teachers_document(env,pdfs):
    app,_=env;gv,other,tk=login(app,1),login(app,5),login(app,2)
    assert submit(gv,pdfs[1]).status_code==200
    assert tk.post('/api/submissions/1/reject',json={'version':1,'reason':'Sửa'}).status_code==200
    assert submit(other,pdfs[1],version=2,submission_id=1).status_code==403


def test_migrate_legacy_single_document_preserves_versions_and_ids(tmp_path,pki,pdfs):
    import sqlite3
    from contextlib import closing
    from backend.db import Database
    app=create_app(tmp_path/'data',bytes(range(32)),pki,secure=False);seed(app.state.database,pki)
    assert submit(login(app,1),pdfs[1]).status_code==200
    # Reconstruct the pre-change table, preserving the existing PDF references.
    with closing(sqlite3.connect(app.state.database.path)) as db:
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('BEGIN IMMEDIATE')
        db.execute('''CREATE TABLE legacy_submissions (id INTEGER PRIMARY KEY,course_id INTEGER UNIQUE REFERENCES courses(id),
          teacher_id INTEGER REFERENCES users(id),status TEXT NOT NULL,version INTEGER NOT NULL,reason TEXT NOT NULL,
          head_id INTEGER REFERENCES users(id),updated_at TEXT NOT NULL)''')
        db.execute('INSERT INTO legacy_submissions SELECT id,course_id,teacher_id,status,version,reason,head_id,updated_at FROM submissions')
        db.execute('DROP TABLE submissions');db.execute('ALTER TABLE legacy_submissions RENAME TO submissions');db.commit()
    migrated=Database(app.state.database.path)
    with migrated.connect() as db:
        assert db.execute('SELECT id,assessment_type FROM submissions').fetchone()['id']==1
        assert db.execute('SELECT submission_id FROM versions').fetchone()['submission_id']==1
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert login(app,1).get('/api/submissions/1/pdf').content==pdfs[1]
    component=pki.sign(unsigned_pdf(assessment_type='component'),0)
    assert submit(login(app,1),component,assessment_type='component').status_code==200
    # Restarting a second time must be idempotent.
    Database(app.state.database.path)
    assert login(app,1).get('/api/submissions').json()['total']==2


def test_uis_ids_do_not_replace_class_and_assessment_checks(tmp_path):
    from pathlib import Path
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,TextStringObject,ArrayObject,FloatObject
    sample=Path('bang-diem-CK_N10.signed.pdf').read_bytes()
    selected={**COURSE,'title':'Cơ sở dữ liệu (10)_TA','code':'TKB-local'}
    validate_metadata(sample,{**selected,'uis_document_id':'17210'})
    validate_metadata(sample,{**selected,'uis_document_id':''})
    with pytest.raises(ValueError,match='Lớp/nhóm'):
        validate_metadata(sample,{**selected,'title':'Cơ sở dữ liệu (1)_TA'})
    writer=PdfWriter();writer.append(io.BytesIO(unsigned_pdf(assessment_type='component')))
    annotation=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/Link'),
        NameObject('/Rect'):ArrayObject([FloatObject(0)]*4),NameObject('/A'):DictionaryObject({NameObject('/S'):NameObject('/URI'),NameObject('/URI'):TextStringObject('https://daotao.vku.udn.vn/gv/bang-diem-thanh-phan/777')})})
    writer.add_annotation(0,annotation);out=io.BytesIO();writer.write(out)
    validate_metadata(out.getvalue(),{**COURSE,'uis_document_id':'17210','uis_component_document_id':'777'},'component')
    with pytest.raises(ValueError,match='lớp/nhóm'):
        validate_metadata(out.getvalue(),{**COURSE,'code':'NOT-IN-HEADER'},'component')
    with pytest.raises(ValueError,match='chọn đúng loại'):
        validate_metadata(unsigned_pdf(),COURSE,'component')


def test_admin_configures_per_type_document_links(env):
    app,_=env;admin,gv=login(app,4),login(app,1)
    body={'uis_document_id':'17210','uis_component_document_id':'777'}
    assert gv.patch('/api/admin/courses/1/mappings',json=body).status_code==403
    assert admin.patch('/api/admin/courses/1/mappings',json=body).status_code==200
    assert gv.get('/api/courses').json()[0]['uis_component_document_id']=='777'


@pytest.mark.parametrize('urls',[
    ['https://evil-daotao.vku.udn.vn/gv/bang-diem-cuoi-ky/17210'],
    ['https://daotao.vku.udn.vn/gv/bang-diem-cuoi-ky/17210','https://daotao.vku.udn.vn/gv/bang-diem-cuoi-ky/17219'],
])
def test_urls_are_not_class_evidence(urls):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,TextStringObject,ArrayObject,FloatObject
    writer=PdfWriter();writer.append(io.BytesIO(unsigned_pdf()))
    for url in urls:
        writer.add_annotation(0,DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/Link'),
            NameObject('/Rect'):ArrayObject([FloatObject(0)]*4),NameObject('/A'):DictionaryObject({NameObject('/S'):NameObject('/URI'),NameObject('/URI'):TextStringObject(url)})}))
    out=io.BytesIO();writer.write(out)
    validate_metadata(out.getvalue(),{**COURSE,'uis_document_id':'99999'})
    with pytest.raises(ValueError,match='lớp/nhóm'):
        validate_metadata(out.getvalue(),{**COURSE,'code':'NOT-IN-HEADER'})


def test_admin_configures_multiple_uis_ids(env):
    app,_=env;admin,gv=login(app,4),login(app,1)
    body={'uis_document_id':' 17210, 17219,17210 ', 'uis_component_document_id':'777, 778'}
    assert gv.patch('/api/admin/courses/1/mappings',json=body).status_code==403
    assert admin.patch('/api/admin/courses/1/mappings',json=body).status_code==200
    course=gv.get('/api/courses').json()[0]
    assert course['uis_document_id']=='17210,17219'
    assert course['uis_component_document_id']=='777,778'
    for value in ['17210,,17219','17210,abc','17210,','-17210']:
        assert admin.patch('/api/admin/courses/1/mappings',json={**body,'uis_document_id':value}).status_code==422
    assert gv.get('/api/courses').json()[0]['uis_document_id']=='17210,17219'


def test_real_pdfs_with_multiple_allowed_uis_ids(tmp_path):
    from pathlib import Path
    from backend.auth import hash_password
    app=create_app(tmp_path/'data',bytes(range(32)),Verifier(tmp_path/'trust',policy='local'),secure=False)
    with app.state.database.connect() as db:
        db.execute("INSERT INTO users(id,email,name,role,department,password) VALUES(1,'hvphi@vku.udn.vn','GV','teacher','CNTT',?)",(hash_password(PASSWORD),))
        for cid,group in [(1,'1'),(2,'10')]:
            db.execute("INSERT INTO courses(id,code,title,year,semester,department,teacher_id) VALUES(?,?,?,'2025-2026','1','CNTT',1)",
                       (cid,f'TKB-{cid}',f'Cơ sở dữ liệu ({group})_TA'))
    client=TestClient(app)
    response=client.post('/api/login',json={'email':'hvphi@vku.udn.vn','password':PASSWORD})
    client.headers['X-CSRF-Token']=response.json()['csrf']
    for index,name in enumerate(['bang-diem-CK_N1.signed.pdf','bang-diem-CK_N10.signed.pdf',
                                'bang-diem-TP_N1.signed.pdf','bang-diem-TP_N10.signed.pdf'],1):
        data=Path(name).read_bytes()
        kind='component' if 'TP_' in name else 'final'
        cid=2 if 'N10' in name else 1
        response=submit(client,data,assessment_type=kind,course_id=cid)
        if kind=='final':
            assert response.status_code==422 and 'GV ký thứ hai' in response.text
        else:
            assert response.status_code==200,response.text
            assert client.get(f'/api/submissions/{index-2}/pdf').content==data
        group='10' if 'N10' in name else '1'
        validate_metadata(data,{**COURSE,'title':f'Cơ sở dữ liệu ({group})_TA','uis_document_id':'99999,88888'},kind)
        if kind=='component':
            assert submit(client,data,assessment_type='final',course_id=cid).status_code==422
    assert len(client.get('/api/submissions').json()['items'])==2


def test_uis_midterm_url_annotation():
    from pypdf import PdfWriter
    from pypdf.annotations import Link
    writer=PdfWriter();writer.append(io.BytesIO(unsigned_pdf(assessment_type='component')))
    writer.add_annotation(0,Link(rect=(0,0,1,1),url='https://daotao.vku.udn.vn/gv/bang-diem-giua-ky/17210'))
    out=io.BytesIO();writer.write(out)
    validate_metadata(out.getvalue(),{**COURSE,'uis_document_id':'99999'},'component')
    with pytest.raises(ValueError,match='lớp/nhóm'):
        validate_metadata(out.getvalue(),{**COURSE,'code':'NO-HEADER'},'component')


def test_submission_list_exposes_current_pdf_signers_with_scope(env,pdfs):
    app,_=env;gv,tk=login(app,1),login(app,2)
    assert submit(gv,pdfs[1]).status_code==200
    for client in [gv,tk]:
        row=client.get('/api/submissions').json()['items'][0]
        assert row['signatures']==client.get('/api/submissions/1/verification').json()['signatures']
        assert row['signatures'][0]['signer_name']=='Teacher'
    assert login(app,5).get('/api/submissions').json()['items']==[]
    assert tk.post('/api/submissions/1/reject',json={'version':1,'reason':'Kiểm tra điểm'}).status_code==200
    row=gv.get('/api/submissions').json()['items'][0]
    assert row['version']==2 and row['status']=='rejected'
    assert [report['signer_name'] for report in row['signatures']]==['Teacher','SecondTeacher']
    assert row['signatures']==gv.get('/api/submissions/1/verification').json()['signatures']
    assert submit(gv,pdfs[1],version=2).status_code==200
    assert head(tk,pdfs[2],version=3).status_code==200
    row=tk.get('/api/submissions').json()['items'][0]
    assert row['version']==4
    assert [report['signer_name'] for report in row['signatures']]==['Teacher','SecondTeacher','Head']
    dt=login(app,3)
    assert dt.post('/api/submissions/1/archive',json={'version':4}).status_code==200
    for client in [gv,tk,dt]:
        saved=client.get('/api/submissions').json()['items'][0]
        assert saved['version']==5 and saved['status']=='archived'
        assert saved['signatures']==row['signatures']==client.get('/api/submissions/1/verification').json()['signatures']
    assert login(app,5).get('/api/submissions').json()['items']==[]


def test_same_certificate_for_teacher_and_head(env,pki,pdfs):
    app,root=env
    from pyhanko.sign import signers
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from unittest.mock import patch
    writer=IncrementalPdfFileWriter(io.BytesIO(pdfs[1]))
    # Sign a second field while preserving /Info metadata. This fixture tests
    # shared signer identity, without introducing an unrelated metadata edit.
    with patch.object(writer,'_update_meta'):
        twice=signers.sign_pdf(writer,
            signature_meta=signers.PdfSignatureMetadata(field_name='Head'),signer=pki.signers[0]).getvalue()
    fp=pki.fingerprints[0]
    expected=[fp,pki.fingerprints[2],fp]
    strict=asyncio.run(pki.verify(twice,expected))
    local=asyncio.run(Verifier(root/'empty-trust',policy='local').verify(twice,expected))
    assert len(strict)==len(local)==3
    assert all(report['fingerprint']==expected[i%3] for i,report in enumerate(strict+local))
    gv,tk,dt=login(app,1),login(app,2),login(app,3)
    assert submit(gv,pdfs[1]).status_code==200
    assert head(tk,twice).status_code==422
    admin=login(app,4)
    assert admin.patch('/api/admin/users/2',json={'fingerprint':fp,'active':True}).status_code==200
    tk=login(app,2)
    assert head(tk,pdfs[1]).status_code==422
    assert head(tk,twice).status_code==200
    assert dt.post('/api/submissions/1/archive',json={'version':2}).status_code==200
    assert gv.get('/api/submissions/1/pdf').content==twice


def test_vgca_two_visible_signatures_same_person(tmp_path):
    from pathlib import Path
    original=Path('bang-diem-CK_N1.signed.pdf').read_bytes()
    data=Path('bang-diem-CK_N1.signed.signed.pdf').read_bytes()
    assert data.startswith(original)
    reports=asyncio.run(Verifier(tmp_path/'trust',policy='local').verify(data,[{'email':'hvphi@vku.udn.vn'}]*2))
    assert [r['signer_name'] for r in reports]==['Hồ Văn Phi','Hồ Văn Phi']
    assert all(r['valid'] and not r['trust_verified'] for r in reports)
    from backend.auth import hash_password
    app=create_app(tmp_path/'data',bytes(range(32)),Verifier(tmp_path/'trust',policy='local'),secure=False)
    with app.state.database.connect() as db:
        for uid,email,role in [(1,'hvphi@vku.udn.vn','teacher'),(2,'hvphi+tk@vku.udn.vn','head')]:
            db.execute('INSERT INTO users(id,email,name,role,department,password,fingerprint) VALUES(?,?,?,?,?,?,?)',
                       (uid,email,'Hồ Văn Phi',role,'CNTT',hash_password(PASSWORD),reports[0]['fingerprint']))
        db.execute("INSERT INTO courses(id,code,title,year,semester,department,teacher_id,uis_document_id) VALUES(1,'CSDL01','Cơ sở dữ liệu (1)_GIT_TA','2025-2026','1','CNTT',1,'17210')")
    clients=[]
    for email in ['hvphi@vku.udn.vn','hvphi+tk@vku.udn.vn']:
        client=TestClient(app)
        response=client.post('/api/login',json={'email':email,'password':PASSWORD})
        client.headers['X-CSRF-Token']=response.json()['csrf'];clients.append(client)
    # Cryptographic VGCA compatibility remains valid; this older final PDF has
    # only one GV (and then TK), so cannot satisfy the newly required two GVs.
    response=submit(clients[0],original)
    assert response.status_code==422 and 'GV ký thứ hai' in response.text
    assert clients[0].get('/api/submissions').json()['total']==0


@pytest.mark.parametrize('change',['role','parent_mapping','widget_type'])
def test_signature_tag_rule_refuses_non_signature_changes(change):
    from pathlib import Path
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.pdf_utils import generic
    from backend.verification_rules import SignatureTagRule
    reader=PdfFileReader(io.BytesIO(Path('bang-diem-CK_N1.signed.signed.pdf').read_bytes()))
    old=reader.get_historical_resolver(1);new=reader.get_historical_resolver(2)
    rule=SignatureTagRule()
    assert list(rule.apply(old,new))
    tree=new.root['/StructTreeRoot'];tag=tree['/K']['/K'][-1]
    if change=='role':tag[generic.pdf_name('/S')]=generic.pdf_name('/Div')
    elif change=='parent_mapping':tree['/ParentTree']['/Nums'][0]=generic.NumberObject(999)
    else:tag['/K']['/Obj'][generic.pdf_name('/FT')]=generic.pdf_name('/Tx')
    assert list(rule.apply(old,new))==[]


@pytest.mark.parametrize('uid,role',[(1,'teacher'),(2,'head'),(3,'training'),(4,'admin')])
def test_login_selected_role_is_enforced(env,uid,role):
    app,_=env;client=TestClient(app)
    body={'email':f'{role}{uid}@vku.udn.vn','password':PASSWORD,'role':role}
    wrong={**body,'role':'admin' if role!='admin' else 'teacher'}
    assert client.post('/api/login',json=wrong).status_code==403
    assert client.get('/api/me').status_code==401
    assert client.post('/api/login',json={**body,'role':'superuser'}).status_code==422
    response=client.post('/api/login',json=body)
    assert response.status_code==200
    assert response.json()['user']['role']==role


def test_shared_email_login_chooses_exact_role(env):
    app,_=env
    with app.state.database.connect() as db:
        db.execute("UPDATE users SET email='shared@vku.udn.vn' WHERE id IN (1,2,3,4)")
    for uid,role in [(1,'teacher'),(2,'head'),(3,'training'),(4,'admin')]:
        client=TestClient(app)
        r=client.post('/api/login',json={'email':'shared@vku.udn.vn','password':PASSWORD,'role':role})
        assert r.status_code==200
        assert r.json()['user']['id']==uid
        assert client.get('/api/me').json()['user']['role']==role
    client=TestClient(app)
    assert client.post('/api/login',json={'email':'shared@vku.udn.vn','password':PASSWORD}).status_code==422
    assert client.get('/api/me').status_code==401
    from backend.auth import hash_password
    with app.state.database.connect() as db:
        db.execute('UPDATE users SET password=? WHERE id=2',(hash_password('Head-Only-Password-2026!'),))
    assert client.post('/api/login',json={'email':'shared@vku.udn.vn','password':PASSWORD,'role':'head'}).status_code==401


def test_admin_adds_role_to_existing_email(env):
    app,_=env;admin=login(app,4)
    body={'email':'teacher1@vku.udn.vn','password':PASSWORD,'name':'Teacher as head','role':'head','department':'CNTT'}
    assert admin.post('/api/admin/users',json=body).status_code==200
    assert admin.post('/api/admin/users',json=body).status_code==409
    client=TestClient(app)
    assert client.post('/api/login',json={'email':body['email'],'password':PASSWORD,'role':'admin'}).status_code==403


def test_user_email_role_migration_preserves_ids_and_references(env,pdfs):
    from backend.db import Database
    app,_=env;assert submit(login(app,1),pdfs[1]).status_code==200
    with app.state.database.connect() as db:
        tables=['users','sessions','courses','submissions','versions','audit']
        before={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in tables}
        schema=db.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone()[0]
        db.commit();db.execute('PRAGMA foreign_keys=OFF')
        db.execute(schema.replace('CREATE TABLE users','CREATE TABLE users_legacy').replace('UNIQUE(email,role)','UNIQUE(email)'))
        db.execute('INSERT INTO users_legacy SELECT * FROM users');db.execute('DROP TABLE users')
        db.execute('ALTER TABLE users_legacy RENAME TO users');db.commit()
    Database(app.state.database.path);Database(app.state.database.path)
    with app.state.database.connect() as db:
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert before=={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in tables}
        db.execute("UPDATE users SET email='shared@vku.udn.vn' WHERE id IN (1,2,3,4)")


def test_import_teacher_timetable_preserves_existing_courses(env,pdfs):
    from scripts.import_timetable import import_snapshot
    app,_=env
    assert submit(login(app,1),pdfs[1]).status_code==200
    with app.state.database.connect() as db:
        before={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in ['courses','submissions','versions']}
    args=(app.state.database,'docs/reports/TKB_VKU_theo_GV_HK1_2026-2027.html',
          'teacher1@vku.udn.vn','TS.Hồ Văn Phi','2026-2027','1')
    assert import_snapshot(*args)==15
    assert import_snapshot(*args)==0
    courses=login(app,1).get('/api/courses').json()
    assert len(courses)==16
    assert len([c for c in courses if c['year']=='2026-2027' and c['semester']=='1'])==15
    assert login(app,5).get('/api/courses').json()==[]
    with app.state.database.connect() as db:
        assert tuple(db.execute('SELECT * FROM courses WHERE id=1').fetchone())==before['courses'][0]
        for table in ['submissions','versions']:
            assert [tuple(r) for r in db.execute('SELECT * FROM '+table)]==before[table]
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
