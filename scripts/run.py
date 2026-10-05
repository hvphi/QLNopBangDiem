"""Run with system Python or bundled runtime; project packages take precedence."""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT / '.local' / 'packages'))
os.chdir(ROOT)
os.environ.setdefault('PYTHONUTF8', '1')
if len(sys.argv) < 2:
    raise SystemExit('Usage: python scripts/run.py MODULE [arguments]')
module = sys.argv.pop(1)
if module == 'serve':
    import uvicorn
    uvicorn.run('backend.app:create_app', factory=True, host='127.0.0.1',port=int(os.environ.get('PORT','8000')))
else:
    runpy.run_module(module,run_name='__main__')
