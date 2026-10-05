"""Import the reviewed timetable snapshot for an existing teacher only."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from backend.db import Database, audit


def import_snapshot(database, path, email, teacher_name, year, semester):
    html=Path(path).read_text(encoding='utf-8')
    rows=json.loads(re.search(r'const rows=(.*?);const names=',html,re.S).group(1))
    rows=[r for r in rows if r['teacher']==teacher_name]
    if not rows:
        raise ValueError('Snapshot không có giảng viên đã chọn.')
    with database.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        teacher=db.execute("SELECT * FROM users WHERE email=? AND role='teacher' AND active=1",(email,)).fetchone()
        if not teacher:
            raise ValueError('Chưa có tài khoản GV được cấp quyền.')
        classes={}
        for row in rows:
            classes.setdefault(row['course'],[]).append(row)
        count=0
        for title,assignments in classes.items():
            code='TKB-'+hashlib.sha256((email+'|'+year+'|'+semester+'|'+title).encode()).hexdigest()[:10].upper()
            cursor=db.execute('''INSERT INTO courses(code,title,year,semester,department,teacher_id,
                teaching_schedule,teaching_room,teaching_weeks) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(code,year,semester) DO NOTHING''',
                (code,title,year,semester,teacher['department'],teacher['id'],
                 '\n'.join(r['schedule'] for r in assignments),'\n'.join(r['room'] for r in assignments),
                 '\n'.join(r['weeks'] for r in assignments)))
            count+=cursor.rowcount
        if count:
            audit(db,teacher['id'],'import_timetable_snapshot',year+'/'+semester,str(count))
    return count


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('snapshot');parser.add_argument('--email',required=True)
    parser.add_argument('--teacher',required=True);parser.add_argument('--year',required=True)
    parser.add_argument('--semester',choices=['1','2','3'],required=True)
    args=parser.parse_args()
    print('Imported:',import_snapshot(Database('runtime/gradebook.sqlite3'),args.snapshot,args.email,args.teacher,args.year,args.semester))
