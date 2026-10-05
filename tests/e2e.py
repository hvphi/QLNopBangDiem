import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
import httpx
import uvicorn
from backend.app import create_app
from backend.verification import Verifier
from backend.auth import session, public_user
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from tests.fixtures import TestPKI, unsigned_pdf, seed, grade_table_pdf


def main():
    with tempfile.TemporaryDirectory(prefix='vku-e2e-') as tmp:
        root=Path(tmp)
        pki=TestPKI(root/'trust')
        one=pki.sign(pki.sign(unsigned_pdf(),0),2);two=pki.sign(one,1)
        (root/'one.pdf').write_bytes(one);(root/'two.pdf').write_bytes(two)
        (root/'component.pdf').write_bytes(pki.sign(unsigned_pdf(assessment_type='component'),0))
        policy=os.environ.get('E2E_SIGNATURE_POLICY','strict')
        verifier=Verifier(root/'trust',policy='local') if policy=='local' else pki
        app=create_app(root/'data',bytes(range(32)),verifier=verifier,secure=False)
        seed(app.state.database,pki)
        # Test-only session rotation avoids consuming the production login throttle.
        @app.post('/__test__/rotate-session')
        async def rotate_test_session(request: Request):
            body=await request.json()
            with app.state.database.connect() as db:
                user=db.execute('SELECT * FROM users WHERE email=? AND role=?',('shared@vku.udn.vn',body['role'])).fetchone()
                token,csrf=session(db,user['id'])
                response=JSONResponse({'user':public_user(user),'csrf':csrf})
                response.set_cookie('session',token,httponly=True,samesite='strict')
                return response
        # create_app mounts the frontend at /; put the test route before that mount.
        app.router.routes.insert(0,app.router.routes.pop())
        @app.post('/__test__/comparison-fixture')
        def seed_comparison_fixture():
            from backend.db import now
            import json, asyncio
            data=pki.sign(pki.sign(grade_table_pdf(),0),2)
            reports=asyncio.run(pki.verify(data,[pki.fingerprints[0],pki.fingerprints[2]]))
            with app.state.database.connect() as db:
                course=dict(db.execute('SELECT * FROM courses WHERE id=1').fetchone())
                stored,digest=app.state.storage.save(data,course)
                cursor=db.execute("INSERT INTO submissions(course_id,teacher_id,status,updated_at,assessment_type,document_label,second_teacher_id) VALUES(1,1,'submitted',?,'other','So khớp thử',7)",(now(),))
                sid=cursor.lastrowid
                db.execute('INSERT INTO versions(submission_id,version,path,sha256,signatures,created_at) VALUES(?,1,?,?,?,?)',(sid,stored,digest,json.dumps(reports),now()))
            return {'id':sid}
        app.router.routes.insert(0,app.router.routes.pop())
        @app.get('/__test__/comparison-reference')
        def comparison_reference(changed: bool=False):
            return Response(grade_table_pdf('9' if changed else '8.5'),media_type='application/pdf')
        app.router.routes.insert(0,app.router.routes.pop())
        with app.state.database.connect() as db:
            db.execute("UPDATE users SET email='shared@vku.udn.vn' WHERE id IN (1,2,3,4)")
            db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OLD01','Học phần năm trước','2024-2025','2','CNTT',1)")
            db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES('OTHER01','Lớp của GV khác','2026-2027','1','CNTT',5)")
            for index,title in enumerate(['Đồ án tốt nghiệp (1)','Đề án (1)','Thực tập (1)','Kiến tập (1)']):
                db.execute("INSERT INTO courses(code,title,year,semester,department,teacher_id) VALUES(?,?,'2023-2024','1','CNTT',1)",(f'SPECIAL{index}',title))
        # Seed a second department record to check actual rendered empty scopes.
        config=uvicorn.Config(app,host='127.0.0.1',port=8765,log_level='error')
        server=uvicorn.Server(config)
        thread=threading.Thread(target=server.run,daemon=True);thread.start()
        try:
            for _ in range(100):
                try:
                    if httpx.get('http://127.0.0.1:8765/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError('E2E server not ready')
            node=shutil.which('node') or str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
            result=subprocess.run([node,'tests/browser.cjs',str(root)],env={**os.environ,'PYTHONUTF8':'1'})
            if result.returncode:raise SystemExit(result.returncode)
        finally:
            server.should_exit=True;thread.join(10)


if __name__=='__main__':main()
