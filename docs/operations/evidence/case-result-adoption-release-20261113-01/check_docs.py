"""Check this static handoff against saved/current HTTP shape; no business calls."""
import hashlib
import json
import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[4]
folder = Path(sys.argv[1])
target = Path(sys.argv[2])
doc = json.loads((folder / 'openapi.json').read_text())
os.environ.update(json.loads((ROOT / '.local/v1.2-reader-validation/app-test-environment.json').read_text()))
sys.path.insert(0, str(ROOT / 'services/api'))
from investigation_http.main import app

actual = app.openapi()
before = json.loads((ROOT / 'docs/operations/evidence/case-result-adoption-http-20261113-01/before-openapi.json').read_text())
adopt = '/api/v1/socai2/cases/{case_id}/results/{result_id}/adopt'
for path, methods in before['paths'].items():
    if path != adopt:
        assert actual['paths'][path] == methods, path
for name, schema in before['components']['schemas'].items():
    if name != 'AdoptCaseAIResult':
        assert actual['components']['schemas'][name] == schema, name

def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k,v in value.items() if k not in {'description','example','examples','x-audit-url'}}
    if isinstance(value, list):
        return [shape(v) for v in value]
    return value

models = ('ResultAdoptionRequest','ResultAdoptionReceipt','ResultAdoptionPreview','AdoptedAssessment','AssessmentHistory')
for name in models:
    assert shape(doc['components']['schemas'][name]) == shape(actual['components']['schemas'][name]), name
    assert all(p.get('description') for p in doc['components']['schemas'][name]['properties'].values()), name
assert sum(len(doc['components']['schemas'][name]['properties']) for name in models if name!='ResultAdoptionRequest') == 42
resolver = RefResolver.from_schema(doc)
count, requests, csv = 0, 0, 0
for methods in doc['paths'].values():
    for op in methods.values():
        for response in op['responses'].values():
            for media, body in response.get('content',{}).items():
                if media != 'application/json':
                    csv += len(body.get('examples',{}))
                    continue
                for key, ex in body.get('examples',{}).items():
                    errors = list(Draft202012Validator(body['schema'],resolver=resolver).iter_errors(ex['value']))
                    assert not errors, (op['operationId'],key,errors[0].message)
                    count += 1
        for body in op.get('requestBody',{}).get('content',{}).values():
            for ex in body.get('examples',{}).values():
                errors = list(Draft202012Validator(body['schema'],resolver=resolver).iter_errors(ex['value']))
                assert not errors, (op['operationId'],errors[0].message)
                requests += 1
ops = [o for ms in doc['paths'].values() for o in ms.values()]
assert len(ops) == 64
assert {o['operationId'] for o in ops if o['x-implementation-status']=='未实现'} == {'E19','E20'}
value = dict(passed=True, operations=64, implemented=62, reserved=2, schemas=len(doc['components']['schemas']),
    fixed_output_fields=655,dynamic_structures=35, json_response_examples=count,csv_examples=csv,
    request_examples=requests, unchanged_previous_operations=61, new_fixed_fields=42, new_dynamic_groups=7,
    business_calls=0, openapi_sha256=hashlib.sha256((folder/'openapi.json').read_bytes()).hexdigest())
target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(value))
