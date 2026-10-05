import argparse
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path, PureWindowsPath
from .db import Database, now


def backup(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.is_relative_to(root):
        raise ValueError('Backup phải ở ngoài thư mục dữ liệu.')
    destination.mkdir(parents=True, exist_ok=False)
    database = Database(root / 'gradebook.sqlite3')
    # Exclude app writes throughout snapshot; writers acquire SQLite IMMEDIATE too.
    with database.connect() as lock:
        lock.execute('BEGIN IMMEDIATE')
        with closing(sqlite3.connect(database.path)) as source, closing(sqlite3.connect(destination / 'gradebook.sqlite3')) as target:
            source.backup(target)
        shutil.copytree(root / 'vault', destination / 'vault')
    with closing(sqlite3.connect(destination / 'gradebook.sqlite3')) as snapshot:
        snapshot.execute('DELETE FROM sessions')
        snapshot.commit()
        snapshot.execute('PRAGMA journal_mode=DELETE')
    files = {str(p.relative_to(destination)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in destination.rglob('*') if p.is_file()}
    (destination / 'manifest.json').write_text(json.dumps({'created_at': now(), 'files': files}, indent=2),encoding='utf-8')
    return destination


def restore(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('Chỉ phục hồi vào thư mục mới; dừng dịch vụ trước khi chuyển đổi.')
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    for relative, digest in manifest['files'].items():
        name = Path(relative)
        if name.is_absolute() or PureWindowsPath(relative).is_absolute() or '..' in name.parts or not (
            relative == 'gradebook.sqlite3' or relative.startswith('vault/')):
            raise ValueError('Manifest chứa đường dẫn không hợp lệ.')
        path = (source / relative).resolve()
        if not path.is_relative_to(source) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Backup sai checksum hoặc đường dẫn không hợp lệ.')
    with closing(sqlite3.connect((source / 'gradebook.sqlite3').as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Database backup lỗi.')
        for path, in db.execute('SELECT path FROM versions'):
            if 'vault/' + path not in manifest['files']:
                raise ValueError('Backup thiếu PDF được tham chiếu.')
    destination.mkdir(parents=True)
    for relative in manifest['files']:
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, path)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['backup','restore'])
    parser.add_argument('source')
    parser.add_argument('destination')
    args = parser.parse_args()
    print(globals()[args.operation](args.source,args.destination))
