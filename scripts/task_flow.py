"""Persist task transitions; refuse dependency and concurrent touches conflicts."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def field(text, key):
    return re.search(r'^'+key+r': (.*)$',text,re.M).group(1)


def transition(tid, status, note=''):
    path=Path('docs/tasks')/(tid+'.md')
    text=path.read_text(encoding='utf-8')
    current=field(text,'status')
    allowed={'todo':['in_progress','blocked'],'in_progress':['review','blocked'],'review':['done','in_progress','blocked'],
             'blocked':['in_progress'],'done':[]}
    if status not in allowed[current]:raise ValueError(f'{tid}: {current} → {status} forbidden')
    if status in ('in_progress','done'):
        for dependency in json.loads(field(text,'depends_on')):
            dep=Path('docs/tasks',dependency+'.md').read_text(encoding='utf-8')
            if field(dep,'status')!='done':raise ValueError('Dependency unfinished: '+dependency)
    if status=='in_progress':
        touches=re.search(r'touches:\n(.*?)prd_refs:',text,re.S).group(1)
        for other in Path('docs/tasks').glob('T-*.md'):
            if other==path:continue
            body=other.read_text(encoding='utf-8')
            if field(body,'status')!='in_progress':continue
            their=re.search(r'touches:\n(.*?)prd_refs:',body,re.S).group(1)
            a=[p.strip()[2:] for p in touches.splitlines() if p.strip().startswith('- ')]
            b=[p.strip()[2:] for p in their.splitlines() if p.strip().startswith('- ')]
            if any(x.startswith(y.rstrip('/')) or y.startswith(x.rstrip('/')) for x in a for y in b):
                raise ValueError('Touches conflict: '+other.stem)
    stamp=datetime.now(timezone.utc).isoformat()
    text=re.sub(r'^status: .*$', 'status: '+status,text,flags=re.M)
    if status=='in_progress':
        text=re.sub(r'^owner: .*$', 'owner: codex-local',text,flags=re.M)
        text=re.sub(r'^started_at: .*$', 'started_at: "'+stamp+'"',text,flags=re.M)
    if status=='review':
        text=re.sub(r'^finished_at: .*$', 'finished_at: "'+stamp+'"',text,flags=re.M)
        text=text.replace('- [ ]','- [x]')
    if note:text=text.replace('(agent điền khi xong)',note)
    path.write_text(text,encoding='utf-8')
    with Path('docs/tasks/HISTORY.jsonl').open('a',encoding='utf-8') as log:
        log.write(json.dumps({'task':tid,'from':current,'to':status,'at':stamp},ensure_ascii=False)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('task');parser.add_argument('status');parser.add_argument('--note',default='')
    args=parser.parse_args();transition(args.task,args.status,args.note)
