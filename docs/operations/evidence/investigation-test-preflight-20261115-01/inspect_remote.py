"""T1 evidence probe: execute through SSH stdin; only metadata, SQL SELECT and GET.

Not a launcher or cleanup tool. Credentials stay inside the selected containers.
Read target JSON from stdin. Emits sanitized JSON; makes no remote files.
"""
import datetime
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

cfg = json.load(sys.stdin)
timeout = cfg['probe_timeout_seconds']


def command(argv, body=None):
    p = subprocess.run(argv, input=body, text=True, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('command_exit_' + str(p.returncode))
    return p.stdout


def sql(query):
    body = 'BEGIN READ ONLY; SET LOCAL statement_timeout = \'5s\';\n' + query + ';\nROLLBACK;'
    result = command(['docker', 'exec', '-i', cfg['postgres_container'], 'psql', '-XwAtq',
                      '-v', 'ON_ERROR_STOP=1', '-U', cfg['postgres_admin'], '-d', cfg['database']], body)
    return json.loads(result)


def rows(query):
    return sql('SELECT coalesce(json_agg(t),\'[]\'::json) FROM (' + query + ') t')


def get(base, path):
    req = urllib.request.Request(base + path, method='GET')
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        r = e
    except Exception as e:
        return {'path': path, 'state': type(e).__name__}, None
    with r:
        body = r.read()
        receipt = {'path': path, 'status': r.status, 'bytes': len(body),
                   'sha256': hashlib.sha256(body).hexdigest(), 'content_type': r.headers.get('Content-Type')}
        try:
            data = json.loads(body)
        except (ValueError, UnicodeError):
            data = None
        if isinstance(data, dict):
            receipt['keys'] = sorted(data)
            for key in ['status', 'error_code', 'code', 'ready', 'service']:
                if key in data and isinstance(data[key], (str, bool, int)):
                    receipt['body_' + key] = data[key]
        return receipt, data


out = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'target': cfg['target'], 'mode': 'read_only', 'model_calls': 0}
env_allowed = {
    'SOCAI2_HTTP_RELEASE', 'SOCAI2_SERVICE_DATABASE_NAME', 'AISOC_AGENT_KAFKA_DISABLE',
    'KAFKA_BOOTSTRAP_SERVERS', 'KAFKA_BROKERS', 'KAFKA_SECURITY_PROTOCOL', 'KAFKA_CONSUMER_GROUP',
    'KAFKA_TOPIC_ALERTS_RAW', 'KAFKA_TOPIC_ALERTS_FUSED', 'KAFKA_TOPIC_RAW_EVENTS',
    'SOCAI2_INVESTIGATION_POLICY', 'SOCAI2_ANALYSIS_DISPATCH_CONFIG_FILE',
    'SOCAI2_ANALYSIS_TASKS_CONFIG_FILE', 'SOCAI2_ANALYSIS_PROJECTION_CONFIG_FILE',
    'SOCAI2_CASE_ALLOCATION_CONFIG_FILE', 'SOCAI2_SOURCE_KNOWLEDGE_ENABLED',
    'SOCAI2_SOURCE_UEBA_ENABLED', 'SOCAI2_SOURCE_GRAPH_ENABLED', 'SOCAI2_SOURCE_PRODUCT_HOST_ENABLED',
    'SOCAI2_MODEL_PROTOCOL', 'SOCAI2_MODEL_SCHEMA_PROFILE', 'OPENAI_MODEL', 'OPENAI_BASE_URL',
    'CLICKHOUSE_HOST', 'CLICKHOUSE_PORT', 'CLICKHOUSE_DATABASE', 'SOCAI2_KNOWLEDGE_PROFILE',
    'SOCAI2_BUSINESS_CONTEXT_FILE', 'SOCAI2_TRUSTED_CONTEXT_FILE',
}
out['containers'] = []
for d in json.loads(command(['docker', 'inspect', *cfg['containers']])):
    env = dict(x.split('=', 1) for x in d['Config']['Env'] if '=' in x)
    safe = {k: v for k, v in env.items() if k in env_allowed}
    for key in ['DATABASE_URL', 'SOCAI2_CASE_DATABASE_URL', 'REDIS_URL']:
        if env.get(key):
            url = urllib.parse.urlsplit(env[key])
            safe[key] = {'host': url.hostname, 'port': url.port, 'database': url.path.lstrip('/'), 'user': url.username}
    out['containers'].append({'name': d['Name'].lstrip('/'), 'image': d['Config']['Image'],
        'image_id': d['Image'], 'started_at': d['State']['StartedAt'], 'running': d['State']['Running'],
        'health': d['State'].get('Health', {}).get('Status'), 'ports': d['NetworkSettings']['Ports'],
        'compose': d['Config'].get('Labels', {}).get('com.docker.compose.project.config_files'),
        'environment': safe, 'mounts': [{'source': m['Source'], 'destination': m['Destination'], 'rw': m['RW']} for m in d['Mounts']]})
out['database'] = {
    'identity': rows("SELECT current_database() AS database,current_user AS role,current_setting('transaction_read_only') AS transaction_read_only,current_setting('server_version') AS version"),
    'migrations': rows("SELECT name FROM public.aisoc_schema_migrations WHERE name ~ '^(123|124|125|126|127|128|129)_' ORDER BY name"),
    'columns': rows("SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default FROM information_schema.columns WHERE table_schema='socai2' ORDER BY table_name,ordinal_position"),
    'constraints': rows("SELECT c.relname AS table_name,k.conname,k.contype,k.convalidated,pg_get_constraintdef(k.oid) AS definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relnamespace='socai2'::regnamespace ORDER BY c.relname,k.conname"),
    'indexes': rows("SELECT c.relname AS table_name,i.relname AS index_name,x.indisvalid,x.indisready,pg_get_indexdef(x.indexrelid) AS definition FROM pg_index x JOIN pg_class c ON c.oid=x.indrelid JOIN pg_class i ON i.oid=x.indexrelid WHERE c.relnamespace='socai2'::regnamespace ORDER BY c.relname,i.relname"),
    'triggers': rows("SELECT c.relname AS table_name,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace='socai2'::regnamespace AND NOT t.tgisinternal ORDER BY c.relname,t.tgname"),
    'source_tables': rows("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('assets','users','tenants','alerts','incidents','aisoc_kb_documents') ORDER BY table_name"),
    'runs': rows('SELECT state,count(*) AS count FROM socai2.runs GROUP BY state ORDER BY state'),
}
tables = sorted({x['table_name'] for x in out['database']['columns']})
out['database']['table_count'] = len(tables)
out['database']['column_count'] = len(out['database']['columns'])
out['database']['lifecycle_tables'] = {t: t in tables for t in ['analysis_tasks', 'analysis_attempts', 'analysis_subject_state', 'case_alert_exclusions']}
if 'analysis_tasks' in tables:
    out['database']['task_states'] = rows('SELECT state,count(*) AS count FROM socai2.analysis_tasks GROUP BY state ORDER BY state')
    out['database']['attempt_states'] = rows('SELECT local_state,count(*) AS count FROM socai2.analysis_attempts GROUP BY local_state ORDER BY local_state')
out['database']['sample_case'] = rows("SELECT id FROM socai2.cases WHERE tenant_id='" + cfg['tenant'] + "' ORDER BY created_at DESC LIMIT 1")
out['http'] = []
receipt, api = get(cfg['http_base'], '/openapi.json')
out['http'].append(receipt)
if api and 'paths' in api:
    ops = [{'method': method.upper(), 'path': path, 'operation_id': spec.get('operationId')}
           for path, item in api['paths'].items() for method, spec in item.items()
           if method in ['get', 'post', 'put', 'patch', 'delete']]
    out['openapi'] = {'info': api.get('info'), 'operations': ops,
                      'business_operation_count': sum(x['path'].startswith('/api/v1/socai2/') for x in ops)}
for path in ['/livez', '/readyz', '/api/v1/socai2/cases?limit=1', '/api/v1/socai2/alerts?limit=1',
             '/api/v1/socai2/incidents?limit=1', '/api/v1/socai2/analysis-runs?limit=1']:
    out['http'].append(get(cfg['http_base'], path)[0])
if out['database']['sample_case']:
    case_id = out['database']['sample_case'][0]['id']
    for suffix in ['', '/analysis-tasks', '/related-cases']:
        out['http'].append(get(cfg['http_base'], '/api/v1/socai2/cases/' + case_id + suffix)[0])
out['workbench'] = [get(cfg['workbench_base'], p)[0] for p in ['/index.html', '/api/config', '/test-api/v1/capabilities']]
out['swagger'] = get(cfg['swagger_base'], '/swagger-config.json')[0]
print(json.dumps(out, ensure_ascii=False, indent=2))
