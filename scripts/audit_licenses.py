"""Inventory active dependencies and preserve their supplied license files verbatim.

Run with scripts/run.py so resolution matches the local application environment.
No packages are installed or upgraded by this command.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import shutil
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

LICENSE_FILE = re.compile(r'(^|[/\\])(licen[sc]e[^/\\]*|copying[^/\\]*|copyright[^/\\]*|notice[^/\\]*|thirdparty[^/\\]*)([/\\]|$)', re.I)


def collect(requirements, destination):
    roots = [Requirement(line.strip()) for line in Path(requirements).read_text().splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    pending = [r.name for r in roots if not r.marker or r.marker.evaluate()]
    packages, missing = {}, []
    while pending:
        name = canonicalize_name(pending.pop())
        if name in packages or name in missing:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
            continue
        info = distribution.metadata
        dependencies = []
        for raw in distribution.requires or []:
            requirement = Requirement(raw)
            if not requirement.marker or requirement.marker.evaluate({'extra': ''}):
                dependencies.append(requirement.name)
                pending.append(requirement.name)
        copied = []
        for relative in distribution.files or []:
            if relative.suffix.lower() in {'.py', '.pyc', '.pyo'} or '__pycache__' in relative.parts:
                continue
            if not LICENSE_FILE.search(str(relative)):
                continue
            source = Path(distribution.locate_file(relative))
            if not source.is_file():
                continue
            # Preserve the layout supplied by the wheel, including binary notices.
            if '..' in relative.parts:
                raise ValueError('License path outside distribution: ' + str(relative))
            target = destination / name / distribution.version / str(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest != hashlib.sha256(target.read_bytes()).hexdigest():
                raise ValueError('License copy changed: ' + str(relative))
            copied.append({'file': target.as_posix(), 'sha256': digest})
        packages[name] = {'name': info['Name'], 'version': distribution.version,
                          'license_expression': info.get('License-Expression'), 'license': info.get('License'),
                          'license_classifiers': [c for c in info.get_all('Classifier', []) if c.startswith('License')],
                          'project_urls': info.get_all('Project-URL', []), 'dependencies': dependencies,
                          'license_copies': copied}
    mismatches = [{'name': r.name, 'declared': str(r.specifier), 'installed': packages[canonicalize_name(r.name)]['version']}
                  for r in roots if canonicalize_name(r.name) in packages
                  and not r.specifier.contains(packages[canonicalize_name(r.name)]['version'], prereleases=True)]
    return {'declared_requirements': [str(r) for r in roots], 'python': sys.version.split()[0],
            'packages': dict(sorted(packages.items())), 'missing': missing, 'version_mismatches': mismatches}


def collect_node(path, destination):
    path = Path(path)
    manifest = path / 'package.json'
    if not manifest.exists():
        return {'missing': path.name}
    info = json.loads(manifest.read_text(encoding='utf-8'))
    copied = []
    for source in path.iterdir():
        if source.is_file() and LICENSE_FILE.search(source.name):
            target = destination / info['name'] / info['version'] / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
            copied.append({'file': target.as_posix(), 'sha256': digest})
    return {'name': info['name'], 'version': info['version'], 'license': info.get('license'), 'license_copies': copied}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--requirements', default='requirements.txt')
    parser.add_argument('--output', default='docs/dependency-licenses.json')
    parser.add_argument('--license-dir', default='docs/licenses/runtime')
    parser.add_argument('--node-tools-root', default=str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'))
    args = parser.parse_args()
    destination = Path(args.license_dir)
    result = collect(args.requirements, destination)
    result['node_tools'] = [collect_node('node_modules/typescript', destination),
                            collect_node(Path(args.node_tools_root)/'playwright', destination),
                            collect_node(Path(args.node_tools_root)/'playwright-core', destination)]
    result['checked_at'] = datetime.now(timezone.utc).isoformat()
    result['scope'] = 'Installed active Python dependency closure; TypeScript and test-only Playwright tools. Native notices only as shipped in these distributions.'
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    count = sum(len(p['license_copies']) for p in result['packages'].values()) + sum(len(p.get('license_copies', [])) for p in result['node_tools'])
    print('Python packages:',len(result['packages']),'| Node tools:',len(result['node_tools']),'| License copies:',count)
    print('Missing packages:',result['missing'],'| Version mismatches:',result['version_mismatches'])
    print('No supplied license file:',[p['name'] for p in result['packages'].values() if not p['license_copies']])


if __name__ == '__main__':
    main()
