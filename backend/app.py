import asyncio
import io
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
import logging
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .db import Database, audit, now
from .storage import Storage
from .auth import current_user, require, public_user, valid_email, hash_password, verify_password, session
from .uis import validate_metadata, source_pdf, filename, canonical_uis_ids
from .assessment import requires_two_teachers
from .verification import Verifier, certificate_emails
from pyhanko.pdf_utils.reader import PdfFileReader
from .operations import backup
from .grade_comparison import pdf_grades, reference_grades, compare_grades

MAX_FILE = 20 * 1024 * 1024


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    role: str | None = Field(default=None, pattern=r'^(teacher|head|training|admin)$')


class UserInput(Login):
    name: str = Field(min_length=1, max_length=100)
    role: str
    department: str = Field(min_length=1, max_length=100)
    fingerprint: str = ''


class UserUpdate(BaseModel):
    active: bool
    fingerprint: str = ''
    name: str | None = Field(default=None,min_length=1,max_length=100)
    email: str | None = Field(default=None,max_length=254)
    role: str | None = Field(default=None,pattern=r'^(teacher|head|training|admin)$')
    department: str | None = Field(default=None,min_length=1,max_length=100)
    password: str = Field(default='',max_length=256)


class DepartmentInput(BaseModel):
    code: str = Field(min_length=1,max_length=100)
    name: str = Field(min_length=1,max_length=150)
    statistical: bool = True


class CourseInput(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    year: str
    semester: str
    department: str = Field(min_length=1, max_length=100)
    teacher_id: int
    co_teacher_id: int | None = None
    source_pdf: str = ''
    uis_document_id: str = ''
    uis_component_document_id: str = ''


class CourseMappings(BaseModel):
    uis_document_id: str = ''
    uis_component_document_id: str = ''


class CoTeacher(BaseModel):
    co_teacher_id: int | None = None


class Decision(BaseModel):
    version: int = Field(ge=1)
    reason: str = Field(default='', max_length=2000)


class Deadline(BaseModel):
    deadline: str


def create_app(root=None, key=None, verifier=None, secure=None):
    root = Path(root or os.environ.get('APP_DATA_DIR', 'runtime'))
    key = key or bytes.fromhex(os.environ.get('APP_ENCRYPTION_KEY', ''))
    storage = Storage(root / 'vault', key)
    database = Database(root / 'gradebook.sqlite3')
    verifier = verifier or Verifier(os.environ.get('APP_TRUST_DIR', str(root / 'trust')),
                                   policy=os.environ.get('APP_SIGNATURE_POLICY','strict'))
    secure = secure if secure is not None else os.environ.get('APP_COOKIE_SECURE', 'true') == 'true'
    backup_lock = threading.Lock()
    backup_state = {'configured': bool(os.environ.get('APP_BACKUP_DIR')), 'last_success': None, 'last_error': None}

    def run_backup():
        destination = os.environ.get('APP_BACKUP_DIR')
        if not destination:
            raise HTTPException(503, 'Chưa cấu hình APP_BACKUP_DIR.')
        if not backup_lock.acquire(blocking=False):
            raise HTTPException(409, 'Backup đang chạy.')
        try:
            target = Path(destination) / (datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
            backup(root,target)
            backup_state.update(last_success=now(),last_error=None)
        except Exception:
            backup_state['last_error'] = now()
            logging.exception('Backup failed')
            raise
        finally:
            backup_lock.release()

    @asynccontextmanager
    async def lifespan(app):
        async def periodic_backup():
            while True:
                try:
                    await asyncio.to_thread(run_backup)
                except Exception:
                    logging.error('Scheduled backup unsuccessful; review operator logs.')
                await asyncio.sleep(max(60,int(os.environ.get('APP_BACKUP_INTERVAL','86400'))))
        task = asyncio.create_task(periodic_backup()) if backup_state['configured'] else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title='VKU E-Gradebook', docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.database, app.state.storage, app.state.verifier = database, storage, verifier
    slots = threading.BoundedSemaphore(4)
    login_attempts = defaultdict(deque)
    attempts_lock = threading.Lock()

    @app.middleware('http')
    async def security(request, call_next):
        origin = request.headers.get('origin')
        if request.method not in ('GET','HEAD','OPTIONS') and origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Origin không hợp lệ.'}, status_code=403)
        try:
            length = int(request.headers.get('content-length', '0'))
        except ValueError:
            return JSONResponse({'detail': 'Content-Length không hợp lệ.'}, status_code=400)
        if length > MAX_FILE + 1024 * 1024:
            return JSONResponse({'detail': 'File vượt giới hạn 20 MB.'}, status_code=413)
        receive, received = request._receive, 0
        async def limited_receive():
            nonlocal received
            event = await receive()
            received += len(event.get('body',b''))
            if received > MAX_FILE + 1024 * 1024:
                raise HTTPException(413,'Request vượt giới hạn upload.')
            return event
        request._receive = limited_receive
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
        if secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse({'detail': 'Dữ liệu trùng hoặc tham chiếu không hợp lệ.'}, status_code=409)

    def user(request: Request):
        return current_user(request, database)

    User = Annotated[dict, Depends(user)]

    def get_course(db, cid):
        row = db.execute('SELECT * FROM courses WHERE id=?', (cid,)).fetchone()
        if not row:
            raise HTTPException(404, 'Không tìm thấy lớp học phần.')
        return dict(row)

    def scope(u, row):
        if u['role'] == 'teacher' and u['id'] != row['teacher_id']:
            raise HTTPException(403, 'Hồ sơ không thuộc giảng viên này.')
        if u['role'] == 'head' and u['department'] != row['department']:
            raise HTTPException(403, 'Hồ sơ không thuộc khoa của bạn.')

    def get_submission(db, sid, u):
        row = db.execute('''SELECT s.*,c.code,c.title,c.year,c.semester,c.department,c.source_pdf,
            c.uis_document_id,c.uis_component_document_id,u.name teacher_name FROM submissions s
            JOIN courses c ON c.id=s.course_id JOIN users u ON u.id=s.teacher_id WHERE s.id=?''', (sid,)).fetchone()
        if not row:
            raise HTTPException(404, 'Không tìm thấy hồ sơ.')
        row = dict(row)
        scope(u, row)
        return row

    def deadline_check(db, u):
        row = db.execute("SELECT value FROM settings WHERE key='deadline'").fetchone()
        if row and row['value'] < now() and u['role'] not in ('admin', 'training'):
            raise HTTPException(403, 'Đã hết hạn nộp. Hồ sơ chỉ được xem và tải xuống.')

    def state_check(row, version, statuses):
        if row['version'] != version or row['status'] not in statuses:
            raise HTTPException(409, 'Hồ sơ đã thay đổi hoặc không ở trạng thái phù hợp. Tải lại danh sách.')

    def read_file(file):
        data = file.file.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            raise HTTPException(413, 'File vượt giới hạn 20 MB.')
        return data

    def validate(data, course, expected, assessment_type=None):
        if not slots.acquire(blocking=False):
            raise HTTPException(503, 'Máy chủ đang xử lý nhiều PDF. Vui lòng thử lại.')
        try:
            kind = assessment_type or course.get('assessment_type','final')
            validate_metadata(data, course, kind)
            reports = asyncio.run(verifier.verify(data, expected))
            if requires_two_teachers(course,kind) and reports[0]['fingerprint'] == reports[1]['fingerprint']:
                raise ValueError('Bảng điểm cuối kỳ cần chữ ký của hai GV khác nhau, không dùng chung chứng thư.')
            return reports
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(422, 'Không đọc được PDF gốc hoặc header UIS.') from e
        finally:
            slots.release()

    def check_co_teacher(db, primary_id, secondary_id):
        if secondary_id is None:
            return
        teacher = db.execute("SELECT id FROM users WHERE id=? AND role='teacher' AND active=1",(secondary_id,)).fetchone()
        if secondary_id == primary_id or not teacher:
            raise HTTPException(422,'GV ký thứ hai phải là GV khác đang hoạt động.')

    def teacher_identities(db, course, kind, snapshot=False, data=None):
        ids = [course['teacher_id']]
        if requires_two_teachers(course,kind):
            secondary = course.get('second_teacher_id') if snapshot else None
            if not snapshot:
                try:
                    signatures = PdfFileReader(io.BytesIO(data),strict=True).embedded_regular_signatures
                    if len(signatures) != 2:
                        raise ValueError('PDF cuối kỳ phải có đúng 2 chữ ký GV; cần GV ký thứ hai khác GV phụ trách.')
                    cert = signatures[1].signer_cert
                    fingerprint = cert.sha256.hex()
                    if signatures[0].signer_cert.sha256.hex() == fingerprint:
                        raise ValueError('Bảng điểm cuối kỳ cần chữ ký của hai GV khác nhau, không dùng chung chứng thư.')
                    emails = certificate_emails(cert)
                    candidates = [user['id'] for user in db.execute("SELECT id,email,fingerprint FROM users WHERE role='teacher' AND active=1 AND id<>?",(ids[0],))
                                  if user['fingerprint'].lower()==fingerprint or
                                  (verifier.policy=='local' and not user['fingerprint'] and user['email'].lower() in emails)]
                    if len(candidates) != 1:
                        raise ValueError('GV ký thứ hai phải khớp duy nhất một tài khoản GV đang hoạt động. Kiểm tra email hoặc fingerprint chứng thư.')
                    secondary = candidates[0]
                except ValueError as exc:
                    raise HTTPException(422,str(exc)) from exc
                except Exception as exc:
                    raise HTTPException(422,'Không đọc được chứng thư GV ký thứ hai từ PDF.') from exc
            if secondary is None:
                raise HTTPException(422,'Hồ sơ chưa có thông tin GV ký thứ hai đã xác thực.')
            if snapshot:
                if secondary == ids[0]:
                    raise HTTPException(422,'Hai GV ký cuối kỳ phải khác nhau.')
            else:
                check_co_teacher(db,ids[0],secondary)
            ids.append(secondary)
        identities = []
        for uid in ids:
            user = db.execute("SELECT fingerprint,email FROM users WHERE id=? AND role='teacher'",(uid,)).fetchone()
            if not user:
                raise HTTPException(422,'Không tìm thấy tài khoản GV ký bảng điểm.')
            identities.append(dict(user))
        return ids, identities

    def persist(db, sid, version, data, course, reports):
        path, digest = storage.save(data, course)
        try:
            db.execute('INSERT INTO versions(submission_id,version,path,sha256,signatures,created_at) VALUES(?,?,?,?,?,?)',
                       (sid, version, path, digest, json.dumps(reports), now()))
        except Exception:
            storage.discard(path)
            raise

    def bind_signer(db, uid, report):
        current = db.execute('SELECT email,fingerprint,active FROM users WHERE id=?',(uid,)).fetchone()
        if not current or not current['active']:
            raise HTTPException(403,'Tài khoản người ký đã bị khóa.')
        fingerprint = report['fingerprint']
        if current['fingerprint']:
            if current['fingerprint'] != fingerprint:
                raise HTTPException(409,'Liên kết chứng thư đã thay đổi. Tải lại và thử lại.')
        elif verifier.policy == 'local' and current['email'].lower() in report.get('signer_emails',[]):
            db.execute('UPDATE users SET fingerprint=? WHERE id=?',(fingerprint,uid))
            audit(db,uid,'link_signer_certificate',uid,fingerprint)
        else:
            raise HTTPException(422,'Chưa xác nhận chứng thư đúng người ký.')

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'signature_policy': verifier.policy,
                'trust_configured': any(verifier.trust_dir.glob('*.pem')) if hasattr(verifier, 'trust_dir') else False}

    @app.post('/api/login')
    def login(body: Login, request: Request):
        address = request.client.host if request.client else 'unknown'
        with attempts_lock:
            q = login_attempts[address]
            while q and q[0] < time.monotonic() - 300:
                q.popleft()
            if len(q) >= 10:
                raise HTTPException(429, 'Quá nhiều lần đăng nhập. Thử lại sau 5 phút.')
            q.append(time.monotonic())
        email = body.email.strip().lower()
        with database.connect() as db:
            rows = db.execute('SELECT * FROM users WHERE email=? AND active=1 ORDER BY id', (email,)).fetchall()
            row = next((r for r in rows if r['role']==body.role),None) if body.role else (rows[0] if len(rows)==1 else None)
            if not valid_email(email) or not rows:
                raise HTTPException(401, 'Email trường hoặc mật khẩu không đúng.')
            if row is None:
                if not any(verify_password(body.password,r['password']) for r in rows):
                    raise HTTPException(401, 'Email trường hoặc mật khẩu không đúng.')
                if body.role is None:
                    raise HTTPException(422, 'Email có nhiều vai trò. Hãy chọn vai trò đăng nhập.')
                raise HTTPException(403, 'Tài khoản không có vai trò đã chọn. Hãy chọn đúng vai trò hoặc dùng tài khoản được cấp cho vai trò đó.')
            if not verify_password(body.password,row['password']):
                raise HTTPException(401, 'Email trường hoặc mật khẩu không đúng.')
            token, csrf = session(db, row['id'])
            audit(db, row['id'], 'login')
            response = JSONResponse({'user': public_user(row), 'csrf': csrf})
            response.set_cookie('session', token, httponly=True, secure=secure, samesite='strict', max_age=28800)
            return response

    @app.get('/api/me')
    def me(u: User):
        with database.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key='deadline'").fetchone()
        return {'user': public_user(u), 'csrf': u['csrf'], 'deadline': row['value'] if row else None,
                'signature_policy': verifier.policy}

    @app.post('/api/logout')
    def logout(request: Request, u: User):
        with database.connect() as db:
            db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(request.cookies['session'].encode()).hexdigest(),))
        response = JSONResponse({'ok': True})
        response.delete_cookie('session')
        return response

    @app.get('/api/courses')
    def courses(u: User):
        with database.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM courses ORDER BY year DESC,code')]
            submitted = {}
            assessment_statuses = {}
            progress = {'rejected': 0, 'submitted': 1, 'head_signed': 2, 'archived': 3}
            for record in db.execute('SELECT course_id,assessment_type,status FROM submissions'):
                kinds = submitted.setdefault(record['course_id'],set())
                kinds.add(record['assessment_type'])
                course_statuses = assessment_statuses.setdefault(record['course_id'],{})
                kind, status = record['assessment_type'], record['status']
                if kind not in course_statuses or progress[status] < progress[course_statuses[kind]]:
                    course_statuses[kind] = status
            for row in rows:
                row['submitted_assessments'] = sorted(submitted.get(row['id'],[]))
                row['assessment_statuses'] = assessment_statuses.get(row['id'],{})
        return [r for r in rows if (u['role'] != 'teacher' or r['teacher_id'] == u['id'])
                and (u['role'] != 'head' or r['department'] == u['department'])]

    @app.get('/api/statistics/departments')
    def department_statistics(u: User, year: str = '', semester: str = '', department: str = ''):
        require(u,'training')
        where,args=[],[]
        for column,value in [('c.year',year),('c.semester',semester),('c.department',department)]:
            if value:
                where.append(column+'=?');args.append(value)
        clause=' WHERE '+' AND '.join(where) if where else ''
        with database.connect() as db:
            rows=db.execute('''SELECT c.department,COUNT(*) total_courses,
                SUM(CASE WHEN EXISTS(SELECT 1 FROM submissions s WHERE s.course_id=c.id)
                    THEN 1 ELSE 0 END) submitted_courses
                FROM courses c'''+clause+' GROUP BY c.department ORDER BY c.department',args).fetchall()
            units={r['code']:r['name'] for r in db.execute('SELECT code,name FROM departments WHERE statistical=1 ORDER BY rowid')}
        items={code:{'department':code,'department_name':name,'total_courses':0,'submitted_courses':0}
               for code,name in units.items() if not department or department==code}
        for row in rows:
            items[row['department']]={**dict(row),'department_name':units.get(row['department'],row['department'])}
        return {'items':list(items.values()),
                'total_courses':sum(row['total_courses'] for row in rows),
                'submitted_courses':sum(row['submitted_courses'] for row in rows)}

    @app.get('/api/statistics/departments/{department}/details')
    def department_details(department: str, u: User, year: str = '', semester: str = ''):
        require(u,'training')
        where,args=['c.department=?'],[department]
        for column,value in [('c.year',year),('c.semester',semester)]:
            if value:
                where.append(column+'=?');args.append(value)
        with database.connect() as db:
            rows=db.execute('''SELECT c.id,c.code,c.title,c.year,c.semester,c.teacher_id,
                u.name teacher_name,u.email teacher_email,
                EXISTS(SELECT 1 FROM submissions s WHERE s.course_id=c.id) submitted
                FROM courses c JOIN users u ON u.id=c.teacher_id WHERE '''+' AND '.join(where)+
                ' ORDER BY u.name,u.id,c.year DESC,c.semester,c.title,c.id',args).fetchall()
        teachers={}
        for row in rows:
            teacher=teachers.setdefault(row['teacher_id'],{'id':row['teacher_id'],'name':row['teacher_name'],
                'email':row['teacher_email'],'total_courses':0,'submitted_courses':0,'courses':[]})
            teacher['courses'].append({k:row[k] for k in ('id','code','title','year','semester','submitted')})
            teacher['total_courses']+=1
            teacher['submitted_courses']+=row['submitted']
        summary=department_statistics(u,year,semester,department)
        return {'department':department,
                'department_name':summary['items'][0]['department_name'] if summary['items'] else department,
                'year':year,'semester':semester,'total_courses':len(rows),
                'submitted_courses':sum(row['submitted'] for row in rows),'teachers':list(teachers.values())}

    def pdf_response(data, name, inline=False):
        mode = 'inline' if inline else 'attachment'
        return Response(data, media_type='application/pdf', headers={'Content-Disposition': f'{mode}; filename="{name}"'})

    @app.get('/api/courses/{cid}/export')
    def export(cid: int, u: User):
        with database.connect() as db:
            c = get_course(db, cid)
            scope(u, c)
            teacher = db.execute('SELECT name FROM users WHERE id=?', (c['teacher_id'],)).fetchone()
        try:
            data = source_pdf(c, os.environ.get('UIS_EXPORT_DIR', ''))
        except (ValueError, OSError) as e:
            raise HTTPException(503, 'Chưa có PDF xuất UIS hợp lệ cho lớp này.') from e
        return pdf_response(data, filename(c, teacher['name']))

    @app.get('/api/submissions')
    def submissions(u: User, q: str = '', year: str = '', semester: str = '', department: str = '',
                    code: str = '', title: str = '', teacher: str = '', status: str = '', page: int = 1,
                    course_id: int = 0, assessment_type: str = ''):
        where, args = [], []
        if u['role'] == 'teacher':
            where.append('s.teacher_id=?'); args.append(u['id'])
        if u['role'] == 'head':
            where.append('c.department=?'); args.append(u['department'])
        if course_id:
            where.append('s.course_id=?'); args.append(course_id)
        for col, val in [('c.year',year),('c.semester',semester),('c.department',department),('c.code',code),('s.status',status),('s.assessment_type',assessment_type)]:
            if val:
                where.append(col + '=?'); args.append(val)
        for col, val in [('c.title',title),('u.name',teacher)]:
            if val:
                where.append(col + ' LIKE ?'); args.append('%'+val+'%')
        if q:
            where.append('(c.code LIKE ? OR c.title LIKE ? OR u.name LIKE ?)'); args.extend(['%'+q+'%']*3)
        clause = ' WHERE ' + ' AND '.join(where) if where else ''
        query = ' FROM submissions s JOIN courses c ON c.id=s.course_id JOIN users u ON u.id=s.teacher_id'
        page = max(1, page)
        with database.connect() as db:
            total = db.execute('SELECT COUNT(*)'+query+clause,args).fetchone()[0]
            rows = db.execute('SELECT s.*,c.code,c.title,c.year,c.semester,c.department,u.name teacher_name,'
                              '(SELECT v.signatures FROM versions v WHERE v.submission_id=s.id AND v.version<=s.version ORDER BY v.version DESC LIMIT 1) signatures'+query+clause+
                              ' ORDER BY s.updated_at DESC LIMIT 25 OFFSET ?',args+[(page-1)*25]).fetchall()
        items = [dict(r) for r in rows]
        for item in items:
            item['signatures'] = json.loads(item['signatures'] or '[]')
        return {'items': items, 'total': total, 'page': page, 'pages': max(1,(total+24)//25)}

    @app.post('/api/submissions')
    def submit(u: User, course_id: Annotated[int, Form()], file: Annotated[UploadFile, File()],
               version: Annotated[int, Form()] = 0, submission_id: Annotated[int, Form()] = 0,
               assessment_type: Annotated[str, Form()] = 'final', document_label: Annotated[str, Form()] = ''):
        require(u, 'teacher')
        if assessment_type not in ('component','final','other') or len(document_label.strip()) > 200:
            raise HTTPException(422,'Loại bảng điểm không hợp lệ hoặc tên bảng điểm vượt 200 ký tự.')
        data = read_file(file)
        with database.connect() as db:
            c = get_course(db, course_id); scope(u,c); deadline_check(db,u)
            teacher_ids, expected = teacher_identities(db,c,assessment_type,data=data)
            if submission_id:
                old = get_submission(db,submission_id,u)
                if old['course_id'] != course_id or old['assessment_type'] != assessment_type:
                    raise HTTPException(422,'Hồ sơ nộp lại phải thuộc đúng lớp và loại bảng điểm.')
                state_check(old,version,['rejected'])
        reports = validate(data,c,expected,assessment_type)
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            c = get_course(db, course_id); scope(u,c); deadline_check(db,u)
            fresh_ids, _ = teacher_identities(db,c,assessment_type,data=data)
            if fresh_ids != teacher_ids:
                raise HTTPException(409,'Phân công GV ký đã thay đổi. Tải lại lớp và nộp lại.')
            for uid, report in zip(teacher_ids,reports):
                bind_signer(db,uid,report)
            second_teacher = teacher_ids[1] if len(teacher_ids)>1 else None
            if submission_id:
                old = get_submission(db,submission_id,u)
                if old['course_id'] != course_id or old['assessment_type'] != assessment_type:
                    raise HTTPException(422,'Hồ sơ nộp lại phải thuộc đúng lớp và loại bảng điểm.')
                state_check(old,version,['rejected'])
                sid, v = old['id'], old['version']+1
                db.execute("UPDATE submissions SET status='submitted',version=?,reason='',head_id=NULL,updated_at=?,second_teacher_id=? WHERE id=?",(v,now(),second_teacher,sid))
            else:
                if version != 0:
                    raise HTTPException(409,'Phiên bản hồ sơ không đúng.')
                duplicate = db.execute('''SELECT s.id FROM submissions s JOIN versions v ON v.submission_id=s.id
                    WHERE s.course_id=? AND s.assessment_type=? AND v.sha256=? LIMIT 1''',
                    (course_id,assessment_type,hashlib.sha256(data).hexdigest())).fetchone()
                if duplicate:
                    raise HTTPException(409,f'PDF này đã được nộp ở hồ sơ #{duplicate["id"]} cùng loại. Nếu hồ sơ bị trả, chọn Nộp lại đúng hồ sơ đó.')
                cursor = db.execute("INSERT INTO submissions(course_id,teacher_id,status,updated_at,assessment_type,document_label,second_teacher_id) VALUES(?,?,'submitted',?,?,?,?)",
                                    (course_id,u['id'],now(),assessment_type,document_label.strip(),second_teacher))
                sid, v = cursor.lastrowid, 1
            persist(db,sid,v,data,c,reports)
            audit(db,u['id'],'teacher_submit',sid)
        return {'id': sid, 'version': v}

    @app.get('/api/submissions/{sid}/pdf')
    def pdf(sid: int, u: User, inline: bool = False, version: int | None = None):
        with database.connect() as db:
            row = get_submission(db,sid,u)
            v = db.execute('SELECT * FROM versions WHERE submission_id=? AND version<=? ORDER BY version DESC LIMIT 1',
                           (sid,version or row['version'])).fetchone()
            if not v:
                raise HTTPException(404,'Không có PDF phiên bản này.')
        return pdf_response(storage.read(v['path'],v['sha256']),filename(row,row['teacher_name']),inline)

    @app.get('/api/submissions/{sid}/verification')
    def verification_report(sid: int, u: User):
        with database.connect() as db:
            get_submission(db,sid,u)
            row = db.execute('SELECT signatures FROM versions WHERE submission_id=? ORDER BY version DESC LIMIT 1',(sid,)).fetchone()
        return {'signatures': json.loads(row['signatures']) if row else []}

    def comparison_pdf(db, sid, user, version=None):
        require(user,'training')
        row=get_submission(db,sid,user)
        if version is not None and row['version']!=version:
            raise HTTPException(409,'Hồ sơ đã thay đổi. Mở lại So Khớp để đối chiếu phiên bản mới.')
        pdf=db.execute('SELECT * FROM versions WHERE submission_id=? AND version<=? ORDER BY version DESC LIMIT 1',(sid,row['version'])).fetchone()
        if not pdf:raise HTTPException(404,'Không có PDF để so khớp.')
        try:
            table=pdf_grades(storage.read(pdf['path'],pdf['sha256']))
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        return row,pdf,table

    @app.get('/api/submissions/{sid}/comparison')
    def comparison_info(sid: int,u: User):
        with database.connect() as db:
            row,pdf,table=comparison_pdf(db,sid,u)
        return {'version':row['version'],'pdf_version':pdf['version'],'columns':table['columns'],
                'student_count':len(table['records'])}

    @app.post('/api/submissions/{sid}/comparison/reference')
    def inspect_comparison_reference(sid: int,u: User,file: Annotated[UploadFile,File()],version: Annotated[int,Form()]):
        require(u,'training')
        with database.connect() as db:
            row=get_submission(db,sid,u)
            if row['version']!=version:raise HTTPException(409,'Hồ sơ đã thay đổi. Mở lại So Khớp.')
        try:
            source=reference_grades(read_file(file),file.filename)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        return {'columns':source['columns'],'student_count':len(source['records'])}

    @app.post('/api/submissions/{sid}/comparison')
    def compare_submission(sid: int,u: User,file: Annotated[UploadFile,File()],version: Annotated[int,Form()],mapping: Annotated[str,Form()]):
        require(u,'training')
        try:
            pairs=json.loads(mapping)
            source=reference_grades(read_file(file),file.filename)
            with database.connect() as db:
                row,pdf,table=comparison_pdf(db,sid,u,version)
                result=compare_grades(table,source,pairs)
                result.update({'version':row['version'],'pdf_version':pdf['version'],'source':'file_export','source_name':Path(file.filename or '').name})
            with database.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                fresh=get_submission(db,sid,u)
                if fresh['version']!=version:raise HTTPException(409,'Hồ sơ đã thay đổi trong lúc so khớp. Mở lại So Khớp.')
                audit(db,u['id'],'compare_grade_export',sid,json.dumps({key:result[key] for key in ('version','pdf_version','status','matched','mismatched','missing','extra','unavailable','mapped_columns','total_columns')}))
            return result
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc

    @app.post('/api/submissions/{sid}/reject')
    def reject(sid: int, body: Decision, u: User):
        require(u,'head','training')
        if not body.reason.strip():
            raise HTTPException(422,'Cần nhập lý do trả lại.')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = get_submission(db,sid,u); deadline_check(db,u)
            state_check(row,body.version,['submitted'] if u['role']=='head' else ['head_signed'])
            db.execute("UPDATE submissions SET status='rejected',version=version+1,reason=?,updated_at=? WHERE id=?",(body.reason.strip(),now(),sid))
            audit(db,u['id'],'reject',sid,body.reason.strip())
        return {'ok': True}

    @app.post('/api/submissions/{sid}/head-sign')
    def head_sign(sid: int, u: User, version: Annotated[int, Form()], file: Annotated[UploadFile, File()]):
        require(u,'head')
        with database.connect() as db:
            row = get_submission(db,sid,u); deadline_check(db,u); state_check(row,version,['submitted'])
            original = db.execute('SELECT * FROM versions WHERE submission_id=? ORDER BY version DESC LIMIT 1',(sid,)).fetchone()
            teacher_ids, expected = teacher_identities(db,row,row['assessment_type'],snapshot=True)
        data = read_file(file)
        old = storage.read(original['path'],original['sha256'])
        if len(data) <= len(old) or not data.startswith(old):
            raise HTTPException(422,'PDF lần hai phải giữ nguyên bản GV đã ký và thêm chữ ký bằng incremental update.')
        reports = validate(data,row,expected+[{'fingerprint':u['fingerprint'],'email':u['email']}])
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            fresh = get_submission(db,sid,u); deadline_check(db,u); state_check(fresh,version,['submitted'])
            for uid, report in zip(teacher_ids,reports):
                bind_signer(db,uid,report)
            bind_signer(db,u['id'],reports[-1])
            persist(db,sid,version+1,data,row,reports)
            db.execute("UPDATE submissions SET status='head_signed',version=version+1,head_id=?,updated_at=? WHERE id=?",(u['id'],now(),sid))
            audit(db,u['id'],'head_sign',sid)
        return {'ok': True}

    @app.post('/api/submissions/{sid}/archive')
    def archive(sid: int, body: Decision, u: User):
        require(u,'training')
        with database.connect() as db:
            row = get_submission(db,sid,u); state_check(row,body.version,['head_signed'])
            v = db.execute('SELECT * FROM versions WHERE submission_id=? ORDER BY version DESC LIMIT 1',(sid,)).fetchone()
            _, expected = teacher_identities(db,row,row['assessment_type'],snapshot=True)
            expected.append(dict(db.execute('SELECT fingerprint,email FROM users WHERE id=?',(row['head_id'],)).fetchone()))
        validate(storage.read(v['path'],v['sha256']),row,expected)
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            fresh = get_submission(db,sid,u); state_check(fresh,body.version,['head_signed'])
            db.execute("UPDATE submissions SET status='archived',version=version+1,updated_at=? WHERE id=?",(now(),sid))
            audit(db,u['id'],'archive',sid)
        return {'ok': True}

    @app.get('/api/admin/users')
    def users(u: User):
        require(u,'admin')
        with database.connect() as db:
            return [public_user(r) for r in db.execute('SELECT * FROM users ORDER BY id')]

    @app.get('/api/admin/departments')
    def departments(u: User):
        require(u,'admin')
        with database.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM departments ORDER BY rowid')]

    @app.post('/api/admin/departments')
    def create_department(body: DepartmentInput, u: User):
        require(u,'admin')
        if not body.code.strip() or not body.name.strip() or '/' in body.code or any(ord(c)<32 for c in body.code):
            raise HTTPException(422,'Mã và tên khoa không được trống.')
        with database.connect() as db:
            try:
                db.execute('INSERT INTO departments VALUES(?,?,?)',(body.code.strip(),body.name.strip(),body.statistical))
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409,'Mã khoa đã tồn tại.') from exc
            audit(db,u['id'],'create_department',body.code)
        return {'ok':True}

    @app.put('/api/admin/departments/{code}')
    def edit_department(code: str, body: DepartmentInput, u: User):
        require(u,'admin')
        if body.code != code or not body.name.strip():
            raise HTTPException(422,'Giữ nguyên mã khoa và nhập tên hợp lệ.')
        with database.connect() as db:
            if not db.execute('SELECT 1 FROM departments WHERE code=?',(code,)).fetchone():
                raise HTTPException(404,'Không tìm thấy khoa.')
            db.execute('UPDATE departments SET name=?,statistical=? WHERE code=?',(body.name.strip(),body.statistical,code))
            audit(db,u['id'],'update_department',code)
        return {'ok':True}

    @app.delete('/api/admin/departments/{code}')
    def delete_department(code: str, u: User):
        require(u,'admin')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM departments WHERE code=?',(code,)).fetchone():
                raise HTTPException(404,'Không tìm thấy khoa.')
            if db.execute('SELECT 1 FROM users WHERE department=? UNION SELECT 1 FROM courses WHERE department=?',(code,code)).fetchone():
                raise HTTPException(409,'Khoa đang có tài khoản hoặc lớp học phần; không thể xóa.')
            db.execute('DELETE FROM departments WHERE code=?',(code,))
            audit(db,u['id'],'delete_department',code)
        return {'ok':True}

    def check_department(db, code):
        if not db.execute('SELECT 1 FROM departments WHERE code=?',(code,)).fetchone():
            raise HTTPException(422,'Hãy chọn khoa/đơn vị trong danh mục.')

    def user_has_records(db, uid):
        return db.execute('''SELECT 1 FROM courses WHERE teacher_id=? OR co_teacher_id=?
            UNION SELECT 1 FROM submissions WHERE teacher_id=? OR head_id=? OR second_teacher_id=?
            UNION SELECT 1 FROM audit WHERE user_id=?''',(uid,uid,uid,uid,uid,uid)).fetchone()

    @app.delete('/api/admin/users/{uid}')
    def delete_user(uid: int, u: User):
        require(u,'admin')
        if uid==u['id']:
            raise HTTPException(422,'Không thể xóa tài khoản đang sử dụng.')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():
                raise HTTPException(404,'Không tìm thấy người dùng.')
            if user_has_records(db,uid):
                raise HTTPException(409,'Tài khoản có lớp, hồ sơ hoặc lịch sử; hãy khóa tài khoản thay vì xóa.')
            db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            db.execute('DELETE FROM users WHERE id=?',(uid,))
            audit(db,u['id'],'delete_user',uid)
        return {'ok':True}

    @app.post('/api/admin/users')
    def create_user(body: UserInput, u: User):
        require(u,'admin')
        email = body.email.strip().lower()
        if not valid_email(email) or body.role not in ('teacher','head','training','admin'):
            raise HTTPException(422,'Email hoặc vai trò không hợp lệ.')
        if body.fingerprint and not re.fullmatch('[a-fA-F0-9]{64}',body.fingerprint):
            raise HTTPException(422,'Fingerprint cần 64 ký tự hex SHA-256.')
        try:
            password = hash_password(body.password)
        except ValueError as e:
            raise HTTPException(422,str(e)) from e
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            check_department(db,body.department)
            if not body.name.strip():
                raise HTTPException(422,'Họ tên không được trống.')
            cur = db.execute('INSERT INTO users(email,name,role,department,password,fingerprint) VALUES(?,?,?,?,?,?)',
                             (email,body.name,body.role,body.department,password,body.fingerprint.lower()))
            audit(db,u['id'],'create_user',cur.lastrowid)
        return {'id': cur.lastrowid}

    @app.patch('/api/admin/users/{uid}')
    def update_user(uid: int, body: UserUpdate, u: User):
        require(u,'admin')
        if uid == u['id'] and not body.active:
            raise HTTPException(422,'Không thể khóa chính tài khoản đang sử dụng.')
        if body.fingerprint and not re.fullmatch('[a-fA-F0-9]{64}',body.fingerprint):
            raise HTTPException(422,'Fingerprint cần 64 ký tự hex SHA-256.')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
            if not existing:
                raise HTTPException(404,'Không tìm thấy người dùng.')
            fields={key:getattr(body,key) if getattr(body,key) is not None else existing[key] for key in ('name','email','role','department')}
            fields['name']=fields['name'].strip();fields['email']=fields['email'].strip().lower()
            if not fields['name'] or not valid_email(fields['email']):
                raise HTTPException(422,'Họ tên hoặc email không hợp lệ.')
            check_department(db,fields['department'])
            if uid==u['id'] and fields['role']!='admin':
                raise HTTPException(422,'Không thể bỏ vai trò admin của tài khoản đang sử dụng.')
            if fields['role']!=existing['role'] and user_has_records(db,uid):
                raise HTTPException(409,'Tài khoản có dữ liệu liên kết; hãy cấp vai trò khác cùng email.')
            if fields['department']!=existing['department'] and db.execute('SELECT 1 FROM courses WHERE teacher_id=? AND department<>?',(uid,fields['department'])).fetchone():
                raise HTTPException(409,'GV đang có lớp thuộc khoa hiện tại; cần xử lý phân công trước khi đổi khoa.')
            try:
                password=hash_password(body.password) if body.password else existing['password']
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from exc
            db.execute('UPDATE users SET name=?,email=?,role=?,department=?,password=?,active=?,fingerprint=? WHERE id=?',
                       tuple(fields[k] for k in ('name','email','role','department'))+(password,body.active,body.fingerprint.lower(),uid))
            db.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            audit(db,u['id'],'update_user',uid)
        return {'ok': True}

    @app.post('/api/admin/courses')
    def create_course(body: CourseInput, u: User):
        require(u,'admin')
        if not re.fullmatch(r'\d{4}-\d{4}',body.year) or body.semester not in ('1','2','3'):
            raise HTTPException(422,'Năm học cần YYYY-YYYY; học kỳ là 1, 2 hoặc 3.')
        try:
            body.uis_document_id = canonical_uis_ids(body.uis_document_id)
            body.uis_component_document_id = canonical_uis_ids(body.uis_component_document_id)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            check_department(db,body.department)
            teacher = db.execute("SELECT * FROM users WHERE id=? AND role='teacher' AND active=1",(body.teacher_id,)).fetchone()
            if not teacher or teacher['department'] != body.department:
                raise HTTPException(422,'GV phải thuộc khoa và đang hoạt động.')
            check_co_teacher(db,body.teacher_id,body.co_teacher_id)
            fields = body.model_dump()
            db.execute('INSERT INTO courses('+','.join(fields)+') VALUES('+','.join('?' for _ in fields)+')',list(fields.values()))
            audit(db,u['id'],'create_course',body.code)
        return {'ok': True}

    @app.patch('/api/admin/courses/{cid}/co-teacher')
    def assign_co_teacher(cid: int, body: CoTeacher, u: User):
        require(u,'admin')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            course = get_course(db,cid)
            check_co_teacher(db,course['teacher_id'],body.co_teacher_id)
            db.execute('UPDATE courses SET co_teacher_id=? WHERE id=?',(body.co_teacher_id,cid))
            audit(db,u['id'],'assign_co_teacher',cid,str(body.co_teacher_id))
        return {'ok': True}

    @app.patch('/api/admin/courses/{cid}/mappings')
    def course_mappings(cid: int, body: CourseMappings, u: User):
        require(u,'admin')
        try:
            body.uis_document_id = canonical_uis_ids(body.uis_document_id)
            body.uis_component_document_id = canonical_uis_ids(body.uis_component_document_id)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            get_course(db,cid)
            db.execute('UPDATE courses SET uis_document_id=?,uis_component_document_id=? WHERE id=?',
                       (body.uis_document_id,body.uis_component_document_id,cid))
            audit(db,u['id'],'course_mappings',cid)
        return {'ok': True}

    @app.put('/api/admin/deadline')
    def set_deadline(body: Deadline, u: User):
        require(u,'admin')
        try:
            value = datetime.fromisoformat(body.deadline)
            if not value.tzinfo:
                raise ValueError()
            from datetime import timezone
            value = value.astimezone(timezone.utc).isoformat()
        except ValueError as e:
            raise HTTPException(422,'Thời hạn cần ISO 8601 kèm múi giờ.') from e
        with database.connect() as db:
            db.execute("INSERT INTO settings VALUES('deadline',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(value,))
            audit(db,u['id'],'deadline','',value)
        return {'ok': True}

    @app.get('/api/admin/audit')
    def logs(u: User):
        require(u,'admin')
        with database.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200')]

    @app.get('/api/admin/operations')
    def operations(u: User):
        require(u,'admin')
        trust = any(verifier.trust_dir.glob('*.pem')) if hasattr(verifier,'trust_dir') else False
        return {'backup': dict(backup_state), 'trust_configured': trust,
                'signature_policy': verifier.policy,
                'uis_export_configured': bool(os.environ.get('UIS_EXPORT_DIR'))}

    @app.post('/api/admin/backup')
    def manual_backup(u: User):
        require(u,'admin')
        try:
            run_backup()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(503,'Backup thất bại; kiểm tra quyền ghi và log vận hành.') from e
        with database.connect() as db:
            audit(db,u['id'],'backup')
        return {'ok': True, 'backup': dict(backup_state)}

    frontend = Path(__file__).resolve().parent.parent / 'frontend'
    app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')
    return app
