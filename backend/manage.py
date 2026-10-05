import argparse
import getpass
import os
from .auth import hash_password, valid_email
from .db import Database, audit


def main():
    parser = argparse.ArgumentParser(description='Bootstrap admin cho VKU E-Gradebook')
    parser.add_argument('--email', required=True)
    parser.add_argument('--name', default='Quản trị viên')
    args = parser.parse_args()
    email = args.email.lower().strip()
    if not valid_email(email):
        parser.error('Cần email @vku.udn.vn.')
    password = os.environ.get('APP_ADMIN_PASSWORD') or getpass.getpass('Mật khẩu admin (>=12 ký tự): ')
    db = Database(os.path.join(os.environ.get('APP_DATA_DIR', 'runtime'), 'gradebook.sqlite3'))
    with db.connect() as conn:
        if conn.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone():
            parser.error('Tài khoản đã tồn tại. Không ghi đè mật khẩu/quyền.')
        cur = conn.execute("INSERT INTO users(email,name,role,department,password) VALUES(?,?,'admin','VKU',?)",
                           (email,args.name,hash_password(password)))
        audit(conn,cur.lastrowid,'bootstrap_admin',cur.lastrowid)
    print('Đã tạo tài khoản admin. Không tự tạo tài khoản GV/TK/ĐT.')


if __name__ == '__main__':
    main()
