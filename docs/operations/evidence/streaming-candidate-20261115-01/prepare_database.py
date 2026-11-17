"""One selected candidate database: existing SQL installation, identity, and readback."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

payload = json.load(sys.stdin)
identity, profile = payload['identity'], payload['install_profile']
pg = identity['postgres']
for key in ('database', 'owner', 'reader', 'writer', 'admin_role'):
    assert re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', pg[key])
assert profile['database'] == pg['database'] and pg['database'] != payload['metadata_database']
assert profile['function_owner'] == pg['owner'] and profile['reader_role'] == pg['reader']
assert profile['analysis']['writer_role'] == pg['writer']
assert pg['tls_mode'] == 'require'
assert identity['candidate_id'] in identity['root']
secrets = payload['passwords']
out = {'candidate_id': identity['candidate_id'], 'started_at': datetime.now(timezone.utc).isoformat(),
       'database': pg['database'], 'steps': [], 'model_calls': 0, 'kafka_messages': 0,
       'formal_database_changed': False, 'source_hashes': payload['source_hashes']}


def literal(value):
    return "'" + value.replace("'", "''") + "'"


def psql(database, sql, variables=None):
    args = [*profile['psql_argv'], '-U', profile['admin_role'], '-d', database,
            '-v', 'ON_ERROR_STOP=1']
    for key, value in (variables or {}).items():
        args += ['-v', key + '=' + str(value)]
    result = subprocess.run(args, input=sql, capture_output=True, text=True,
                            timeout=profile['timeout_seconds'], check=False)
    if result.returncode:
        error = result.stderr
        for value in secrets.values():
            error = error.replace(value, '<redacted>')
        raise RuntimeError(error[-3000:])
    return result.stdout


variables = {
    'expected_database': pg['database'], 'function_owner': pg['owner'], 'reader_role': pg['reader'],
    'analysis_writer_role': pg['writer'], 'tenant_id': identity['tenant_id'],
    'actor_id': identity['actor_id'], 'actor_name': identity['actor_name'],
    'actor_email': identity['actor_name'] + '@' + identity['candidate_id'] + '.invalid',
    'candidate_id': identity['candidate_id'],
    'cleanup_lock_timeout': str(profile['cleanup']['lock_timeout_seconds']) + 's',
    'cleanup_statement_timeout': str(profile['cleanup']['statement_timeout_seconds']) + 's',
    'analysis_lock_timeout': str(profile['analysis']['lock_timeout_seconds']) + 's',
    'analysis_statement_timeout': str(profile['analysis']['statement_timeout_seconds']) + 's',
}
stage = 'preflight'
try:
    roles = ','.join(literal(pg[key]) for key in ('owner', 'reader', 'writer'))
    preflight = json.loads(psql(payload['metadata_database'],
        'SELECT json_build_object(\'database_exists\',EXISTS(SELECT FROM pg_database WHERE datname='
        + literal(pg['database']) + "),'roles_existing',(SELECT count(*) FROM pg_roles WHERE rolname IN ("
        + roles + ')));'))
    out['preflight'] = preflight
    assert not preflight['database_exists'] and preflight['roles_existing'] == 0
    stage = 'create_roles'
    sql = 'BEGIN; SET LOCAL password_encryption=\'scram-sha-256\';\n'
    sql += f'CREATE ROLE "{pg["owner"]}" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;\n'
    for key in ('reader', 'writer'):
        sql += (f'CREATE ROLE "{pg[key]}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '
                + literal(secrets[key]) + ';\n')
    psql(payload['metadata_database'], sql + 'COMMIT;')
    out['steps'].append(stage)
    stage = 'create_database'
    psql(payload['metadata_database'],
         f'CREATE DATABASE "{pg["database"]}" OWNER "{pg["owner"]}" TEMPLATE template0 ENCODING \'UTF8\';')
    out['steps'].append(stage)
    stage = 'initialize_current'
    out['installation_output'] = psql(pg['database'], payload['initialize_sql'], variables)
    out['steps'].append(stage)
    stage = 'functional_access_and_identity'
    psql(pg['database'], payload['access_sql'], variables)
    out['steps'].append(stage)
    stage = 'verify'
    out['verify_output'] = psql(pg['database'], payload['verify_sql'], variables).strip()
    out['readback'] = json.loads(psql(pg['database'], """BEGIN READ ONLY;
SELECT json_build_object(
 'database',current_database(),
 'tables',(SELECT count(*) FROM pg_class WHERE relnamespace='socai2'::regnamespace AND relkind='r'),
 'columns',(SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
   WHERE c.relnamespace='socai2'::regnamespace AND c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped),
 'migrations',(SELECT json_agg(name ORDER BY name) FROM public.aisoc_schema_migrations),
 'tenants',(SELECT json_agg(id) FROM public.tenants),
 'actors',(SELECT json_agg(json_build_object('id',id,'tenant_id',tenant_id)) FROM public.users),
 'runs',(SELECT count(*) FROM socai2.runs),
 'tasks',(SELECT count(*) FROM socai2.analysis_tasks),
 'alerts',(SELECT count(*) FROM socai2.alerts),
 'cases',(SELECT count(*) FROM socai2.cases),
 'roles',(SELECT json_agg(json_build_object('role',rolname,'login',rolcanlogin,'superuser',rolsuper,
    'bypassrls',rolbypassrls,'createrole',rolcreaterole,'createdb',rolcreatedb,'replication',rolreplication))
    FROM pg_roles WHERE rolname IN (:'function_owner',:'reader_role',:'analysis_writer_role')));
ROLLBACK;
""", variables))
    readback = out['readback']
    assert (readback['tables'], readback['columns']) == (32, 521)
    assert readback['tenants'] == [identity['tenant_id']]
    assert readback['actors'] == [{'id': identity['actor_id'], 'tenant_id': identity['tenant_id']}]
    assert not any(readback[k] for k in ('runs', 'tasks', 'alerts', 'cases'))
    out['steps'].append(stage)
    stage = 'private_http_runtime'
    directory = Path(identity['root']) / 'private'
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / 'http-runtime.json'
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(payload['http_runtime'], stream)
        stream.write('\n')
    out['private_runtime'] = {'path': str(path), 'mode': oct(path.stat().st_mode & 0o777),
                              'keys': sorted(payload['http_runtime'])}
    out['steps'].append(stage)
    out['status'] = 'passed'
except (AssertionError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
    out['status'], out['failed_stage'] = 'failed', stage
    out['error'] = str(exc) or type(exc).__name__
out['finished_at'] = datetime.now(timezone.utc).isoformat()
print(json.dumps(out, ensure_ascii=False, indent=2))
raise SystemExit(0 if out['status'] == 'passed' else 1)
