"""Bounded host21 client: five synthetic JSON-object calls; no retries or tool actions.

Run in the fixed API image with private gateway-client env. Never retain model
reasoning text, full response headers, credentials, or unsanitized error bodies.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Literal
import uuid

import httpx
from pydantic import BaseModel, ConfigDict

BATCH = '1e-20261020'
ROLES = ('triage', 'recon', 'investigation', 'summary', 'report')
EVIDENCE = Path('/evidence')


class Ready(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    batch: Literal['1e-20261020']
    role: Literal['triage', 'recon', 'investigation', 'summary', 'report']
    status: Literal['ready']
    evidence_count: Literal[0]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(name, value):
    with (EVIDENCE/name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


async def main():
    # Each successful/failed request has its own file. A later failure must not
    # erase earlier successes or cause their requests to be repeated.
    assert not list(EVIDENCE.glob('request-*.json')), 'Retained calls exist; inspect rather than replay'
    base = os.environ['LLM_GATEWAY_URL'].rstrip('/')
    auth = {'Authorization': 'Bearer ' + os.environ['LLM_GATEWAY_API_KEY']}
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=8), trust_env=False) as http:
        models = await http.get(base+'/models', headers=auth)
        models.raise_for_status()
        aliases = sorted(m['id'] for m in models.json()['data'])
        assert aliases == sorted('aisoc-'+r for r in ROLES), aliases
        rejects = []
        for label, headers, alias in (
            ('no-key', {}, 'aisoc-triage'),
            ('wrong-key', {'Authorization':'Bearer sk-socai2-invalid-test'}, 'aisoc-triage'),
            ('unpublished-role', auth, 'aisoc-copilot'),
            ('unknown-alias', auth, 'socai2-does-not-exist'),
        ):
            body = {'model': alias, 'messages':[{'role':'user','content':BATCH+' rejected request'}],
                    'max_tokens':1}
            response = await http.post(base+'/chat/completions', headers=headers, json=body)
            boundary = {'case':label,'model':alias,'http_status':response.status_code,
                        'response_body_sha256':hashlib.sha256(response.content).hexdigest()}
            if label == 'wrong-key' and response.status_code == 400:
                # Fixed upstream's master-only/no-DB mode rejects a nonmaster
                # key as no_db_connection, not 401. Retain this limitation.
                error = response.json().get('error', {})
                boundary['error_type'] = error.get('type')
                assert error.get('type') == 'no_db_connection'
                boundary['known_original_non401_denial'] = True
            else:
                assert response.status_code in ((401,403) if label in ('no-key','wrong-key') else (400,404))
            save('boundary-'+label+'.json', boundary)
            rejects.append(boundary)
        save('access-boundaries.json', {'aliases': aliases, 'rejects': rejects})
        results = []
        for role in ROLES:
            call_id = str(uuid.uuid4())
            prompt = (f'Dependency probe {BATCH}. Return only one JSON object with exactly these values: '
                      f'{{"batch":"{BATCH}","role":"{role}","status":"ready","evidence_count":0}}. '
                      'This is a synthetic gateway check. Do not investigate or call tools.')
            request = {'model':'aisoc-'+role, 'temperature':0, 'max_tokens':128, 'stream':False,
                       'response_format': {'type':'json_object'},
                       'messages':[{'role':'system','content':'Return the requested JSON object only.'},
                                   {'role':'user','content':prompt}]}
            started = time.monotonic()
            record = {'call_id':call_id,'started_at':datetime.now(timezone.utc).isoformat(),
                      'batch':BATCH,'role':role,'endpoint':base+'/chat/completions',
                      'request':request,'request_sha256':digest(request),'cost':None,'cost_source':'unknown',
                      'automatic_client_retries':0}
            try:
                response = await http.post(base+'/chat/completions', headers={**auth,'X-Request-ID':call_id},
                                           json=request)
                record['http_status'] = response.status_code
                if response.status_code != 200:
                    # Error messages can echo headers or internal configuration.
                    record['error_response_sha256'] = hashlib.sha256(response.content).hexdigest()
                    response.raise_for_status()
                data = response.json()
                choice = data['choices'][0]
                message = choice['message']
                # Explicit allowlist excludes reasoning_content/analysis fields.
                record['response'] = {k:data[k] for k in ('id','model','created','usage') if k in data}
                record['response'].update(content=message.get('content'), finish_reason=choice.get('finish_reason'))
                record['response_headers'] = {k:v for k,v in response.headers.items() if k in (
                    'x-litellm-call-id','x-litellm-model-id','x-litellm-model-group','x-litellm-api-base',
                    'x-litellm-response-cost','x-request-id')}
                record['omitted_message_fields'] = sorted(set(message)-{'role','content','refusal','annotations'})
                parsed = Ready.model_validate_json(message['content'])
                assert parsed.role == role
                assert choice.get('finish_reason') == 'stop'
                usage = data.get('usage')
                assert usage and all(isinstance(usage.get(k), int) and usage[k]>=0
                                     for k in ('prompt_tokens','completion_tokens','total_tokens'))
                assert usage['prompt_tokens']+usage['completion_tokens']==usage['total_tokens']
                assert usage['completion_tokens'] > 0
                record.update(status='succeeded',schema_valid=True,parsed=parsed.model_dump())
                results.append({'role':role,'call_id':call_id,'response_id':data.get('id'),'model':data.get('model'),
                                'usage':usage,'schema_valid':True})
            except Exception as exc:
                record.update(status='failed_or_unknown',error_type=type(exc).__name__)
                raise
            finally:
                record['elapsed_seconds'] = round(time.monotonic()-started,6)
                save('request-'+role+'.json',record)
        save('summary.json', {'batch':BATCH,'roles':list(ROLES),'calls':results,
                             'client_transport':'httpx in fixed API image; no mock',
                             'schema':'json_object provider format + strict local Pydantic validation',
                             'total_tokens':sum(x['usage']['total_tokens'] for x in results),
                             'limits':['Routing/structure only, not investigation quality',
                                       'No tool execution, tenant/BYOK or Case/Run integration',
                                       'No inference calls for unpublished roles; no fallback to paid provider']})
        print(json.dumps({'success':True,'roles':list(ROLES),'actual_calls':len(results),
                          'total_tokens':sum(x['usage']['total_tokens'] for x in results)}))


if __name__ == '__main__':
    try: asyncio.run(main())
    except Exception as exc:
        print(json.dumps({'success':False,'error_type':type(exc).__name__,
                          'action':'Inspect retained per-request records; do not replay completed/unknown calls'}))
        raise SystemExit(1)
