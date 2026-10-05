const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const bundled = path.join(process.env.USERPROFILE || '', '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe');
const python = process.env.PYTHON || (fs.existsSync(bundled) ? bundled : 'python');
const args = process.argv.slice(2);
const result = spawnSync(python, ['scripts/run.py', ...args], {stdio: 'inherit', env:{...process.env,PYTHONUTF8:'1'}});
if(result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
