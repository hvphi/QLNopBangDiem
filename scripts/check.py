import ast
import json
import re
from pathlib import Path

for folder in ('backend','scripts','tests'):
    for path in Path(folder).glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
cards = list(Path('docs/tasks').glob('T-*.md'))
assert len(cards) >= 13
headers = ['Mục tiêu','Ngữ cảnh cần biết','Phạm vi','Đầu vào đã có','Việc phải làm','Quy ước bắt buộc',
           'Checklist đầu ra','Test phải viết','Định nghĩa "xong"','Cạm bẫy đã biết','Đã làm gì']
for i, path in enumerate(sorted(cards),1):
    text = path.read_text(encoding='utf-8')
    assert all('## '+h in text for h in headers),path
    if 1<i<=13:
        assert f'depends_on: ["T-{i-1:02d}"]' in text,path
dependencies = {p.stem:json.loads(re.search(r'^depends_on: (.*)$',p.read_text(encoding='utf-8'),re.M).group(1)) for p in cards}
def check_dependencies(tid, chain):
    assert tid not in chain, 'Dependency cycle: '+tid
    assert tid in dependencies, 'Missing dependency: '+tid
    for parent in dependencies[tid]:check_dependencies(parent,chain+[tid])
for tid in dependencies:check_dependencies(tid,[])
print(f'Python syntax + {len(cards)} task templates/dependencies: OK')
