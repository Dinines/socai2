import hashlib
import json
import os
import secrets
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'docs/operations'))
from production_case_probe import query, remote, save
from verify_current_release import snapshot

folder = ROOT / 'docs/operations/evidence' / Path(__file__).parent.name
cfg = json.loads((folder / 'run-config.json').read_text())
t = cfg['transport']

def ssh(code, payload):
    p = subprocess.run([t['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UpdateHostKeys=no', '-o', f"ConnectTimeout={t['connect_timeout_seconds']}", t['ssh_target'],
        shlex.join([t['remote_python'], '-c', code])], input=json.dumps(payload), text=True,
        capture_output=True, timeout=t['command_timeout_seconds'], check=False)
    if p.returncode:
        raise RuntimeError('transport_failed_inspect_before_retry')
    return json.loads(p.stdout)

mode = sys.argv[1]
if mode == 'source':
    for c in cfg['cases']:
        data = snapshot(cfg, c['source_case_id'])
        assert sorted(a['id'] for a in data['data']['alerts']) == c['alert_ids']
        save(folder / (c['name'] + '-source.json'), data)
        print(json.dumps({'case':c['name'], 'source_tables':{k:len(v) for k,v in data['data'].items()}},ensure_ascii=False), flush=True)
elif mode == 'key':
    path = Path(cfg['target']['user_api_key_file'])
    assert not path.exists() and not (folder / 'key-create-intent.json').exists()
    raw = 'aisoc_' + secrets.token_hex(24)
    identity = str(uuid4())
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'api_key':raw,'id':identity},f)
    save(folder / 'key-create-intent.json', {'id':identity,'actor_id':cfg['target']['actor_id'],
        'tenant_id':cfg['target']['tenant_id'], **cfg['key_config'], 'at':datetime.now(UTC).isoformat(),
        'scope':'new bounded credential for existing test actor; no role or table grants'})
    code = '''import json,subprocess,sys
p=json.load(sys.stdin); t=p['transport']
def q(s): return "'"+s.replace("'","''")+"'"
sql="BEGIN; SET LOCAL statement_timeout='10s'; SET LOCAL lock_timeout='5s'; WITH inserted AS (INSERT INTO public.api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,expires_at,created_at) SELECT "+q(p['id'])+"::uuid,"+q(p['tenant'])+"::uuid,id,"+q(p['name'])+","+q(p['prefix'])+","+q(p['hash'])+","+q(json.dumps(p['scopes']))+"::jsonb,true,now()+make_interval(days=>"+str(p['ttl_days'])+"),now() FROM public.users WHERE id="+q(p['actor'])+"::uuid AND tenant_id="+q(p['tenant'])+"::uuid RETURNING id,tenant_id,user_id,name,scopes,is_active,expires_at) SELECT coalesce(jsonb_agg(to_jsonb(inserted)),'[]') FROM inserted; COMMIT;"
r=subprocess.run([t['remote_docker'],'exec','-i',t['pg_container'],t['pg_client'],'-wXAtq','-v','ON_ERROR_STOP=1','-U',t['pg_admin_role'],'-d',p['database']],input=sql,text=True,capture_output=True)
print(json.dumps({'exit_code':r.returncode,'rows':json.loads(r.stdout.strip()) if r.returncode==0 else [],'error':None if r.returncode==0 else 'credential_insert_failed'}))
'''
    result = ssh(code, {'transport':t,'database':cfg['target']['database'],'id':identity,
        'tenant':cfg['target']['tenant_id'],'actor':cfg['target']['actor_id'],
        **cfg['key_config'],'prefix':raw[:12],'hash':hashlib.sha256(raw.encode()).hexdigest()})
    save(folder / 'key-created.json',result)
    assert result['exit_code']==0 and len(result['rows'])==1
    print(json.dumps(result))
elif mode == 'auth':
    result = remote(cfg, {'mode':'http','method':'GET','path':'/api/v1/auth/me','body':None})
    assert result['status']==200, result['status']
    body=result['body']
    assert body['id']==cfg['target']['actor_id'] and body['tenant_id']==cfg['target']['tenant_id']
    safe={k:body[k] for k in ('id','tenant_id','username')}
    save(folder/'authenticated.json',safe)
    print(json.dumps(safe))
elif mode in ('progress','capture'):
    c=next(c for c in cfg['cases'] if c['name']==sys.argv[2])
    created=json.loads((folder/(c['name']+'-create-receipt.json')).read_text())['receipt']
    if mode=='capture':
        data=snapshot(cfg,created['case_id'])
        save(folder/(c['name']+'-snapshot-'+datetime.now(UTC).strftime('%H%M%S')+'.json'),data)
        print(json.dumps({'case_id':created['case_id'],'counts':{k:len(v) for k,v in data['data'].items()}}))
    else:
        cid=str(UUID(created['case_id']))
        data=query(cfg,f"SELECT jsonb_build_object('runs',(SELECT jsonb_agg(jsonb_build_object('id',id,'state',state,'stop_reason',stop_reason,'delivery_state',delivery_state,'started_at',started_at,'ended_at',ended_at)) FROM socai2.runs WHERE case_id='{cid}'),'steps',(SELECT jsonb_agg(jsonb_build_object('stage',s.stage_code,'state',s.state,'seq',s.seq,'error',s.error) ORDER BY s.seq) FROM socai2.run_steps s JOIN socai2.runs r ON r.id=s.run_id WHERE r.case_id='{cid}'));" )
        save(folder/(c['name']+'-progress-'+datetime.now(UTC).strftime('%H%M%S')+'.json'),data)
        print(json.dumps(data))
elif mode in ('create','prepare','start','followup_prepare','followup_start'):
    c=next(c for c in cfg['cases'] if c['name']==sys.argv[2])
    stem=c['name']+'-'+mode
    key=str(UUID(c['operation_keys'][mode]))
    if mode=='create':
        args=['case-create','--title',c['title'],'--incident-id',c['incident_id'],'--operation-key',key]
    else:
        created=json.loads((folder/(c['name']+'-create-receipt.json')).read_text())['receipt']
        action=mode.removeprefix('followup_')
        args=['case-'+action,'--subject',created['case_id'],'--scope-revision',str(created['scope_revision']),'--operation-key',key]
        if action=='start':
            preparation='followup_prepare' if mode.startswith('followup_') else 'prepare'
            prepared=json.loads((folder/(c['name']+'-'+preparation+'-receipt.json')).read_text())['receipt']
            assert (prepared['pending_run_id']==created['pending_run_id']) == (mode=='start')
            args += ['--run-id',prepared['pending_run_id'],'--window-start',c['window_start'],'--window-end',c['window_end']]
            if mode=='followup_start':
                first=json.loads((folder/(c['name']+'-start-receipt.json')).read_text())['receipt']
                assert len(first['result_ids'])==1
                args += ['--comparison-result-id',first['result_ids'][0]]
    save(folder/(stem+'-intent.json'),{'at':datetime.now(UTC).isoformat(),'arguments':args})
    print(json.dumps({'started':stem}),flush=True)
    result=remote(cfg,{'mode':'job','tenant':cfg['target']['tenant_id'],'actor':cfg['target']['actor_id'],'arguments':args},job=True)
    save(folder/(stem+'-receipt.json'),{'at':datetime.now(UTC).isoformat(),**result})
    print(json.dumps(result,ensure_ascii=False),flush=True)
    if mode in ('start','followup_start'):
        assert result.get('receipt',{}).get('state') in {'completed','failed','cancelled'}, 'inspect uncertain Run'
    else:
        assert result['exit_code']==0 and 'error' not in result['receipt']
else:
    raise ValueError(mode)
