"""Direct checks for this deployment-documentation batch; no runtime connections."""
import ast
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

import tomllib

ROOT = Path(__file__).resolve().parents[4]
DOCS = [
    'deploy/README.md', 'deploy/aisoc21/README.md', 'deploy/local-investigation/README.md',
    'deploy/database/CURRENT.md', 'docs/operations/configuration.md',
    'docs/operations/deployment-datastores.md', 'docs/operations/deployment-processing.md',
    'docs/operations/deployment-support-services.md', 'docs/operations/deployment-models.md',
    'deploy/http-service/README.md', 'deploy/http-service/CONFIGURATION.md',
    'deploy/api-docs/README.md', 'deploy/investigation-test/README.md',
]
CONFIGS = [
    'deploy/local-investigation/analysis-tasks.json',
    'deploy/local-investigation/analysis-aic-dispatch.example.json',
    'deploy/local-investigation/analysis-aic-executors.example.json',
    'deploy/local-investigation/case-allocation.json',
    'deploy/aisoc21/analysis-projection.example.json',
    'deploy/aisoc21/production-profile.example.toml',
    'deploy/aisoc21/streaming-candidate-20261115-01/processing-build.toml',
    'deploy/aisoc21/streaming-candidate-20261115-01/transport.json',
    'deploy/aisoc21/streaming-candidate-20261115-01/identity.json',
    'deploy/database/reader-install.example.toml',
    'docs/operations/processing_audit_view.json',
]
SETTINGS = [
    'services/fusion/app/core/config.py', 'services/ueba/app/core/config.py',
    'services/actions/app/core/config.py', 'services/threatintel/app/config.py',
]
errors, links, tables = [], 0, 0
all_text = '\n'.join((ROOT / name).read_text() for name in DOCS)
for name in DOCS:
    path = ROOT / name
    text = path.read_text()
    in_code, columns = False, None
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith('```'):
            in_code = not in_code
        if in_code:
            continue
        if line.startswith('|'):
            count = len(re.split(r'(?<!\\)\|', line)) - 2
            if columns is None:
                tables += 1
                columns = count
            elif count != columns:
                errors.append(f'{name}:{number}: table columns {count} != {columns}')
        else:
            columns = None
        if line.rstrip() != line:
            errors.append(f'{name}:{number}: trailing whitespace')
    if in_code:
        errors.append(f'{name}: unclosed fence')
    for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text):
        if target.startswith(('https:', 'http:', 'mailto:', '#')):
            continue
        target = unquote(target.split('#')[0].strip('<>'))
        target = re.sub(r':\d+$', '', target)
        if not (path.parent / target).resolve().exists():
            errors.append(f'{name}: missing {target}')
        links += 1

def leaves(data, prefix=''):
    for key, value in data.items():
        path = prefix + key
        if isinstance(value, dict):
            yield from leaves(value, path + '.')
        else:
            yield path

coverage = []
for name in CONFIGS:
    raw = (ROOT / name).read_bytes()
    data = tomllib.loads(raw.decode()) if name.endswith('.toml') else json.loads(raw)
    keys = list(leaves(data))
    missing = [key for key in keys if key not in all_text and key.rsplit('.', 1)[-1] not in all_text]
    errors.extend(f'{name}: undocumented {key}' for key in missing)
    coverage.append({'source': name, 'leaf_fields': len(keys), 'missing': missing,
                     'sha256': hashlib.sha256(raw).hexdigest()})
for name in SETTINGS:
    tree = ast.parse((ROOT / name).read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name.endswith('Settings'))
    keys = []
    for node in cls.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        key = node.target.id
        if isinstance(node.value, ast.Call):
            for item in node.value.keywords:
                if item.arg == 'alias':
                    key = ast.literal_eval(item.value)
                elif item.arg == 'validation_alias' and isinstance(item.value, ast.Call):
                    key = ast.literal_eval(item.value.args[0])
        keys.append(key)
    missing = [key for key in keys if key not in all_text]
    errors.extend(f'{name}: undocumented {key}' for key in missing)
    coverage.append({'source': name, 'settings_fields': len(keys), 'missing': missing})
name = 'services/enrichment/internal/config/config.go'
keys = sorted(set(re.findall(r'getEnv\("([A-Z_]+)"', (ROOT / name).read_text())))
missing = [key for key in keys if key not in all_text]
errors.extend(f'{name}: undocumented {key}' for key in missing)
coverage.append({'source': name, 'settings_fields': len(keys), 'missing': missing})
receipt = {'state': 'passed' if not errors else 'failed', 'documents': len(DOCS),
           'local_links': links, 'tables': tables, 'coverage': coverage, 'errors': errors,
           'coverage_limit': 'field-name presence and structure; manual source review establishes meaning',
           'database_calls': 0, 'model_calls': 0, 'service_changes': 0}
print(json.dumps(receipt, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
