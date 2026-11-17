import json, sys
from pathlib import Path
runtime, swagger = [json.loads(Path(p).read_text()) for p in sys.argv[1:]]
methods = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}
maps = {'properties', 'patternProperties', '$defs', 'definitions',
        'schemas', 'mapping', 'dependentSchemas'}
annotations = {'description', 'title', 'example', 'examples', 'externalDocs'}
def clean(value, mapping=False):
    if isinstance(value, list):
        return [clean(v) for v in value]
    if not isinstance(value, dict):
        return value
    if mapping:
        return {k: clean(v) for k, v in value.items()}
    return {k: clean(v, k in maps) for k, v in value.items()
            if k not in annotations and not k.startswith('x-')}
def operations(doc):
    return {(p, m): op for p, entries in doc['paths'].items()
            for m, op in entries.items()
            if p.startswith('/api/v1/socai2/') and m in methods}
def canonical(op):
    return clean({k: v for k, v in op.items()
                  if k not in {'tags', 'summary', 'operationId'}})
a, b = operations(runtime), operations(swagger)
assert len(a) == len(b) == 80
assert sum(m == 'get' for _, m in b) == 55
assert a.keys() == b.keys(), 'missing or obsolete operations'
changed = [f'{m.upper()} {p}' for p, m in a
           if canonical(a[p, m]) != canonical(b[p, m])]
assert not changed, changed
assert clean(runtime['components']['schemas'], True) == \
       clean(swagger['components']['schemas'], True), 'Schema contract differs'
assert [v['name'] for v in swagger['tags']] == ['告警', '事件', '调查']
assert all(set(op.get('tags', [])) <= {'告警', '事件', '调查'}
           and op.get('tags') for op in b.values())
assert not swagger.get('security')
assert not swagger.get('components', {}).get('securitySchemes')
assert all(not op.get('security') for op in b.values())
print('PASS: 80 operations / 55 GET; requests, responses and Schema match')
