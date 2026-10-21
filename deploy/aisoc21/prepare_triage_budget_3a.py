"""Back up/restore the project DB before the single additive budget migration."""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import secrets
import subprocess
import sys
import uuid

from shared_1b import SharedBatch, PG_CONTAINER
from prepare_2a import snapshot
from prepare_identity_read_3a import TABLES, lit
from prepare_triage_request_3a import material, readers
from finish_model_triage_3a import METRICS

R=Path('/opt/sting-aisoc-socai2')
B='3a-triage-budget-20261020'
E=R/'evidence'/B
STATE=R/'private/app-triage-budget-3a.json'
RESTORE_DB='socai2_budget_restore_20261020'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name,value):
    with (E/name).open('x') as f:json.dump(value,f,indent=2,default=str)
    (E/name).chmod(0o600)


def hashes(batch,table):return [hashlib.sha256(row['material'].encode()).hexdigest() for row in material(batch,table)]


def main(mode='prepare'):
    os.umask(0o077)
    assert mode in {'prepare','resume-restored'} and not STATE.exists()
    batch=SharedBatch(R)
    old=json.loads((R/'private/app-triage-request-3a.json').read_text())
    receipt=json.loads((R/'source/docs/operations/3a-triage-request.json').read_text())
    expected={**old['images'],**receipt['deployment']['images']}
    env=snapshot()
    assert len(env['containers'])==36 and len(env['volumes'])==18
    assert all(env['containers']['socai2-'+n+'-1']['image']==h for n,h in expected.items())
    assert batch.pg("SELECT to_regclass('public.socai2_triage_budget_reservations') IS NULL;").stdout.strip()=='t'
    counts={}
    for table in ['alerts']+TABLES:
        data=hashes(batch,table);counts[table]=len(data)
        if mode=='prepare':save('prior-'+table+'.json',data)
        else:assert data==json.loads((E/('prior-'+table+'.json')).read_text()),table
    assert [counts[n] for n in ['alerts','investigation_runs','investigation_events','investigation_artifacts','aisoc_run_costs']]==[61,32,83,92,21]
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()=='134'
    credentials=readers(batch)
    backup=R/'private/triage-budget-3a-before.dump'
    if mode=='prepare':
        assert not (E/'environment-before.json').exists() and not backup.exists()
        save('environment-before.json',env)
        (E/'scope-plan-before.md').write_bytes((R/'source/docs/operations/3a-triage-budget-plan.md').read_bytes());(E/'scope-plan-before.md').chmod(0o600)
        save('reader-credentials-before.json',credentials)
        save('gateway-before.json',json.loads(subprocess.check_output(['docker','exec','socai2-litellm-1','python','-c',METRICS])))
        data=subprocess.check_output(['docker','exec',PG_CONTAINER,'pg_dump','-U',batch.pg_admin,'-d','aisoc','-Fc'])
        with backup.open('xb') as f:f.write(data)
        backup.chmod(0o600)
        save('backup-created.json',{'private_path':str(backup),'sha256':sha(backup),'bytes':len(data),'format':'pg_dump custom','project_database':'aisoc'})
        assert batch.pg('SELECT count(*) FROM pg_database WHERE datname='+lit(RESTORE_DB)+';',database='postgres').stdout.strip()=='0'
        save('restore-started.json',{'temporary_database':RESTORE_DB,'source_database_untouched':True})
        batch.pg('CREATE DATABASE '+RESTORE_DB+' TEMPLATE template0;',database='postgres')
        restored=subprocess.run(['docker','exec','-i',PG_CONTAINER,'pg_restore','-U',batch.pg_admin,'--no-owner','--exit-on-error','-d',RESTORE_DB],input=data,capture_output=True)
        if restored.returncode:
            save('restore-failed.json',{'exit_code':restored.returncode,'stderr':restored.stderr.decode()[:2000]})
            raise RuntimeError('Inspect restore checkpoint; do not recreate or overwrite backup')
    else:
        assert (E/'restore-started.json').exists() and not (E/'restore-verified.json').exists()
        assert env==json.loads((E/'environment-before.json').read_text())
        assert credentials==json.loads((E/'reader-credentials-before.json').read_text())
        assert sha(backup)==json.loads((E/'backup-created.json').read_text())['sha256']
        save('prepare-recovery-preconditions.json',{'only_resume_existing_restore':True,'original_14_tables_unchanged':True,'backup_hash_unchanged':True,'schema_still_absent':True,'backup_or_restore_repeated':False,'reason':'--no-owner restore belongs to admin; verification must not SET ROLE aisoc'})
    isolated=SimpleNamespace(pg=lambda sql:batch.pg(sql.replace('SET ROLE aisoc;',''),database=RESTORE_DB))
    assert all(hashes(isolated,t)==json.loads((E/('prior-'+t+'.json')).read_text()) for t in ['alerts']+TABLES)
    assert batch.pg('SELECT count(*) FROM aisoc_schema_migrations;',database=RESTORE_DB).stdout.strip()=='134'
    save('restore-verified.json',{'temporary_database':RESTORE_DB,'all_14_material_tables_match':True,'migrations':134})
    batch.pg('DROP DATABASE '+RESTORE_DB+';',database='postgres')
    save('restore-cleanup.json',{'only_removed_database':RESTORE_DB,'project_database_preserved':True})
    migration=R/'source/deploy/aisoc21/migrations/001_triage_budget.sql'
    batch.pg(migration.read_text())
    schema=json.loads(batch.pg("SELECT row_to_json(x) FROM (SELECT c.relrowsecurity,c.relforcerowsecurity,pg_get_userbyid(c.relowner) AS owner,(SELECT count(*) FROM pg_indexes WHERE tablename='socai2_triage_budget_reservations') AS indexes FROM pg_class c WHERE c.oid='socai2_triage_budget_reservations'::regclass) x;").stdout)
    assert schema['relrowsecurity'] and schema['relforcerowsecurity'] and schema['owner']=='aisoc'
    assert batch.pg('SELECT count(*) FROM socai2_triage_budget_reservations;').stdout.strip()=='0'
    save('schema-applied.json',{'file_sha256':sha(migration),'new_table':'socai2_triage_budget_reservations','schema':schema,'upstream_migrations_unchanged':134,'runtime_ddl':False})
    now=datetime.fromisoformat(batch.pg('SELECT now()::text;').stdout.strip());ns=uuid.uuid5(uuid.NAMESPACE_URL,'socai2/'+B)
    ids={}
    for alias in ['a','b','denied']:
        prior=old['identities']['a' if alias=='denied' else alias]
        ids[alias]={'tenant_id':prior['tenant_id'],'user_id':prior['user_id'],'key_id':str(uuid.uuid5(ns,alias)),
                    'key':'aisoc_'+secrets.token_hex(24),'scopes':['settings:read'] if alias=='denied' else ['alerts:read','alerts:write','cases:read'],
                    'expires_at':(now+timedelta(hours=3)).isoformat()}
    policy={'schema_version':1,'tenants':{ids['a']['tenant_id']:{'window_seconds':86400,'max_calls':2,'max_reserved_tokens':40000,'max_unsettled':1},
                                        ids['b']['tenant_id']:{'window_seconds':86400,'max_calls':3,'max_reserved_tokens':20000,'max_unsettled':1}}}
    directory=R/'private/triage-budget-3a';directory.mkdir(mode=0o700);os.chown(directory,10001,10001)
    path=directory/'policy.json';path.write_text(json.dumps(policy,indent=2));path.chmod(0o600);os.chown(path,10001,10001)
    state={'batch':B,'identities':ids,'images':expected,'reader_credentials':credentials,'counts_before':counts,
           'graph_config_sha256':sha(R/'private/identity-graph-3a/config.json'),'policy_sha256':sha(path),
           'limits':{'new_alerts':6,'broker_publishes':12,'deliveries':16,'runs':6,'http_model_substitutes':6,'real_models':0}}
    with STATE.open('x') as f:json.dump(state,f,indent=2)
    sql='SET ROLE aisoc; BEGIN; '
    for alias,key in ids.items():
        fields=[lit(key[k]) for k in ['key_id','tenant_id','user_id']]
        fields += [lit('socai2-'+B+'-'+alias),lit(key['key'][:12]),lit(hashlib.sha256(key['key'].encode()).hexdigest()),lit(json.dumps(key['scopes']))+'::jsonb',lit(key['expires_at'])]
        sql+='INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,expires_at) VALUES ('+','.join(fields)+'); '
    batch.pg(sql+'COMMIT;')
    values={}
    for name in ['agents','fusion']:
        item=json.loads(subprocess.check_output(['docker','inspect','socai2-'+name+'-1']))[0]
        for entry in item['Config']['Env']:
            k,v=entry.split('=',1)
            if name=='agents' or k.startswith('KAFKA_'):values[k]=v
    values.update({'AISOC_TRIAGE_BUDGET_POLICY_FILE':'/run/secrets/triage-budget/policy.json','AISOC_AGENT_RAISE_APPROVALS':'0'})
    with (R/'private/probe-triage-budget-3a.env').open('x') as f:f.write(''.join(k+'='+v+'\n' for k,v in values.items()))
    save('prepared.json',{'counts':counts,'operation_keys':3,'new_readers':0,'new_schema_tables':1,'backup_restored_verified':True,'real_models':0,'policy_file_sha256':sha(path)})
    print(json.dumps({'batch':B,'prepared':True,'backup_restore_verified':True,'additive_tables':1,'original_migrations':134,'operation_keys':3}))


if __name__=='__main__':main(*sys.argv[1:])
