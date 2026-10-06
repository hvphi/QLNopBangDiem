import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            new_departments = not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='departments'").fetchone()
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('teacher','head','training','admin')),
                department TEXT NOT NULL, password TEXT NOT NULL,
                fingerprint TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(email,role));
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id),
                csrf TEXT NOT NULL, expires TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY, code TEXT NOT NULL, title TEXT NOT NULL,
                year TEXT NOT NULL, semester TEXT NOT NULL, department TEXT NOT NULL,
                teacher_id INTEGER NOT NULL REFERENCES users(id), source_pdf TEXT NOT NULL DEFAULT '',
                uis_document_id TEXT NOT NULL DEFAULT '',
                uis_component_document_id TEXT NOT NULL DEFAULT '',
                UNIQUE(code, year, semester));
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY, course_id INTEGER REFERENCES courses(id),
                teacher_id INTEGER REFERENCES users(id), status TEXT NOT NULL
                CHECK(status IN ('submitted','head_signed','rejected','archived')),
                version INTEGER NOT NULL DEFAULT 1, reason TEXT NOT NULL DEFAULT '',
                head_id INTEGER REFERENCES users(id), updated_at TEXT NOT NULL,
                assessment_type TEXT NOT NULL DEFAULT 'final' CHECK(assessment_type IN ('component','final','other')),
                document_label TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY, submission_id INTEGER REFERENCES submissions(id),
                version INTEGER NOT NULL, path TEXT UNIQUE NOT NULL, sha256 TEXT NOT NULL,
                signatures TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(submission_id,version));
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id),
                action TEXT NOT NULL, target TEXT NOT NULL, details TEXT NOT NULL,
                created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')
            self.migrate_users(db)
            self.migrate_documents(db)
            if 'receiving_department' not in {r['name'] for r in db.execute('PRAGMA table_info(submissions)')}:
                db.execute("ALTER TABLE submissions ADD COLUMN receiving_department TEXT NOT NULL DEFAULT ''")
                db.execute("UPDATE submissions SET receiving_department=COALESCE((SELECT department FROM courses WHERE id=submissions.course_id),'')")
            for table, column in [('courses','co_teacher_id'),('submissions','second_teacher_id')]:
                if column not in {r['name'] for r in db.execute('PRAGMA table_info('+table+')')}:
                    db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' INTEGER REFERENCES users(id)')
            db.execute('CREATE TABLE IF NOT EXISTS departments (code TEXT PRIMARY KEY, name TEXT NOT NULL, statistical INTEGER NOT NULL DEFAULT 1)')
            if new_departments:
                db.executemany('INSERT INTO departments(code,name) VALUES(?,?)',[
                    ('CNTT','Khoa Khoa học máy tính'),('KTMT','Khoa Kỹ thuật máy tính và Điện tử'),
                    ('KTS','Khoa Kinh tế số và Thương mại điện tử'),('AIDS','Khoa Trí tuệ nhân tạo và Khoa học dữ liệu'),('CB','Tổ Cơ bản')])
                db.executemany('INSERT INTO departments(code,name,statistical) VALUES(?,?,0)',[
                    ('VKU','Trường VKU'),('ĐT & BĐCL','Phòng Đào tạo & BĐCL'),('Chưa phân khoa','Chưa phân khoa')])
                for row in db.execute('SELECT department FROM users UNION SELECT department FROM courses').fetchall():
                    if row['department']:
                        db.execute('INSERT OR IGNORE INTO departments(code,name,statistical) VALUES(?,?,0)',(row['department'],row['department']))

    def migrate_users(self, db):
        legacy = any(index['unique'] and
                     [r['name'] for r in db.execute('SELECT name FROM pragma_index_info(?)',(index['name'],))]==['email']
                     for index in db.execute('PRAGMA index_list(users)').fetchall())
        if not legacy:
            return
        db.commit()
        db.execute('PRAGMA foreign_keys=OFF')
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE users_new (
                id INTEGER PRIMARY KEY, email TEXT NOT NULL, name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('teacher','head','training','admin')),
                department TEXT NOT NULL, password TEXT NOT NULL,
                fingerprint TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(email,role))''')
            db.execute('INSERT INTO users_new SELECT * FROM users')
            db.execute('DROP TABLE users')
            db.execute('ALTER TABLE users_new RENAME TO users')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('Migration tài khoản có tham chiếu dữ liệu không hợp lệ.')
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.execute('PRAGMA foreign_keys=ON')

    def migrate_documents(self, db):
        course_columns = {r['name'] for r in db.execute('PRAGMA table_info(courses)')}
        for column in ('teaching_schedule','teaching_room','teaching_weeks'):
            if column not in course_columns:
                db.execute('ALTER TABLE courses ADD COLUMN '+column+" TEXT NOT NULL DEFAULT ''")
        if 'uis_component_document_id' not in course_columns:
            db.execute("ALTER TABLE courses ADD COLUMN uis_component_document_id TEXT NOT NULL DEFAULT ''")
            db.commit()
        columns = {r['name'] for r in db.execute('PRAGMA table_info(submissions)')}
        unique_course = False
        for index in db.execute('PRAGMA index_list(submissions)').fetchall():
            if index['unique']:
                names = [r['name'] for r in db.execute('SELECT name FROM pragma_index_info(?)',(index['name'],))]
                unique_course |= names == ['course_id']
        if 'assessment_type' in columns and not unique_course:
            db.execute('CREATE INDEX IF NOT EXISTS submissions_course ON submissions(course_id,assessment_type)')
            return
        # Rebuild atomically, preserving all IDs referenced by versions/audit.
        # Foreign keys must be disabled before BEGIN to avoid cascade/rename effects.
        db.commit()
        db.execute('PRAGMA foreign_keys=OFF')
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('''CREATE TABLE submissions_new (
                id INTEGER PRIMARY KEY, course_id INTEGER REFERENCES courses(id),
                teacher_id INTEGER REFERENCES users(id), status TEXT NOT NULL
                CHECK(status IN ('submitted','head_signed','rejected','archived')),
                version INTEGER NOT NULL DEFAULT 1, reason TEXT NOT NULL DEFAULT '',
                head_id INTEGER REFERENCES users(id), updated_at TEXT NOT NULL,
                assessment_type TEXT NOT NULL DEFAULT 'final' CHECK(assessment_type IN ('component','final','other')),
                document_label TEXT NOT NULL DEFAULT '')''')
            kind = 'assessment_type' if 'assessment_type' in columns else "'final'"
            label = 'document_label' if 'document_label' in columns else "''"
            db.execute('''INSERT INTO submissions_new
                SELECT id,course_id,teacher_id,status,version,reason,head_id,updated_at,'''+kind+','+label+' FROM submissions')
            db.execute('DROP TABLE submissions')
            db.execute('ALTER TABLE submissions_new RENAME TO submissions')
            db.execute('CREATE INDEX submissions_course ON submissions(course_id,assessment_type)')
            if db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('Migration có tham chiếu dữ liệu không hợp lệ.')
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.execute('PRAGMA foreign_keys=ON')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def audit(db, user, action, target='', details=''):
    db.execute('INSERT INTO audit(user_id,action,target,details,created_at) VALUES(?,?,?,?,?)',
               (user, action, str(target), details, now()))
