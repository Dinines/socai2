#!/usr/bin/env python3
"""Prepare private host21 configs and narrowly scoped test principals for 1F."""
import base64
import hashlib
import json
from pathlib import Path
import secrets
import uuid

from shared_1b import SharedBatch

ROOT = Path('/opt/sting-aisoc-socai2')
BATCH = '1f-20261020'


def main():
    b = SharedBatch(ROOT)
    state_path = ROOT / 'private/app-1f.json'
    if state_path.exists():
        raise RuntimeError('Private state already exists; do not rotate/reseed blindly')
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, 'socai2/' + BATCH)
    state = {name: secrets.token_hex(32) for name in
             ('secret_key','jwt_secret','metrics_token','realtime_internal_token','realtime_jwt_secret')}
    state['credential_key'] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    identities = {}
    for name, tenant, scopes in [('a','a',['alerts:read','alerts:write']),
                                  ('b','b',['alerts:read','alerts:write']),
                                  ('readonly','a',['alerts:read'])]:
        key = 'aisoc_' + secrets.token_hex(24)
        identities[name] = {'tenant_id':str(uuid.uuid5(namespace,'tenant-'+tenant)),
                            'user_id':str(uuid.uuid5(namespace,'user-'+tenant)),
                            'key_id':str(uuid.uuid5(namespace,'key-'+name)),
                            'key':key,'scopes':scopes}
    state['identities'] = identities
    state_path.write_text(json.dumps(state,indent=2)+'\n');state_path.chmod(0o600)
    def env_file(name, values):
        p = ROOT / 'private' / name
        p.write_text(''.join(k+'='+str(v)+'\n' for k,v in values.items()));p.chmod(0o600)
    pg = 'postgresql+asyncpg://aisoc_app:' + b.config['app_password'] + '@192.168.1.21:5432/aisoc?sslmode=verify-full'
    common = {'ENVIRONMENT':'production','ENV':'production','DATABASE_URL':pg,
              'PGSSLROOTCERT':'/run/certs/ca.crt','KAFKA_BOOTSTRAP_SERVERS':'192.168.1.21:19093',
              'KAFKA_SECURITY_PROTOCOL':'SSL','KAFKA_SSL_CAFILE':'/run/certs/ca.crt',
              'KAFKA_TOPIC_ALERTS_RAW':'socai2.alerts.raw','KAFKA_TOPIC_ALERTS_FUSED':'socai2.alerts.fused',
              'PYTHONDONTWRITEBYTECODE':'1','PYTHONUNBUFFERED':'1','OTEL_EXPORTER':'none'}
    api = {**common, 'REDIS_URL':'redis://socai2:'+b.config['redis_password']+'@192.168.1.21:6379/8',
           'SECRET_KEY':state['secret_key'],'JWT_SECRET':state['jwt_secret'],
           'METRICS_TOKEN':state['metrics_token'],'AISOC_CREDENTIAL_KEY':state['credential_key'],
           'REALTIME_INTERNAL_TOKEN':state['realtime_internal_token'],
           'AISOC_REALTIME_JWT_SECRET':state['realtime_jwt_secret'],
           'AISOC_DISABLE_CLICKHOUSE':'true','AISOC_DISABLE_NEO4J':'true',
           'AISOC_DEMO_MODE':'false','AISOC_DEV_AUTH_BYPASS':'false',
           'PLUGIN_TRUST_MODE':'strict','AISOC_PUBLISHED_BIND_ADDRS':'127.0.0.1',
           'AISOC_WAR_ROOM_SYNC_ENABLED':'false','OAUTH_REFRESH_WORKER_ENABLED':'false',
           'WEEKLY_DIGEST_WORKER_ENABLED':'false','HUNT_SCHEDULER_ENABLED':'false',
           'RETRO_HUNT_ENABLED':'false','REPORT_SCHEDULER_ENABLED':'false',
           'OUTBOUND_WEBHOOK_WORKER_ENABLED':'false','RETENTION_WORKER_ENABLED':'false',
           'PHISHING_INTAKE_WORKER_ENABLED':'false','APPROVAL_EXPIRY_ENABLED':'false',
           'SHADOW_RECONCILE_ENABLED':'false','AUTONOMY_DRIFT_ENABLED':'false',
           'AISOC_SIEM_WRITEBACK_EXECUTE':'false'}
    fusion = {**common,'REDIS_URL':'redis://socai2:'+b.config['redis_password']+'@192.168.1.21:6379/9',
              'KAFKA_CONSUMER_GROUP':'socai2-fusion-consumer','AISOC_EVENT_PROMOTION_ENABLED':'false',
              'AISOC_DETECTION_ENGINE_ENABLED':'false','AISOC_WINDOWED_DETECTION_ENABLED':'false',
              'AISOC_LAKE_WRITER_ENABLED':'false','AISOC_UEBA_FUSION_ENABLED':'false',
              'AISOC_FUSION_MEMORY_NUDGE':'0','AISOC_FUSE_ENRICHMENT':'false',
              'AISOC_TENANT_IOC_MATCH':'0','AISOC_ALERT_SINK_ENABLED':'true'}
    env_file('api-1f.env',api);env_file('fusion-1f.env',fusion)
    env_file('migrate-1f.env',{**api,'DATABASE_MIGRATION_URL':
              'postgresql+asyncpg://aisoc:'+b.config['owner_password']+'@192.168.1.21:5432/aisoc?sslmode=verify-full',
              'AISOC_MIGRATIONS_REQUIRED':'1','AISOC_MIGRATIONS_STRICT':'1'})
    # Isolated fixtures only, no shared databases or existing tenants touched.
    for tenant in ('a','b'):
        identity=identities[tenant]
        b.pg(f"SET ROLE aisoc; INSERT INTO tenants(id,name,slug) VALUES ('{identity['tenant_id']}',"
             f"'socai2 {BATCH} {tenant}','socai2-{BATCH}-{tenant}');"
             "INSERT INTO users(id,tenant_id,email,username,hashed_password,role,is_active) VALUES "
             f"('{identity['user_id']}','{identity['tenant_id']}','{BATCH}-{tenant}@test.invalid',"
             f"'socai2-{tenant}','!disabled-api-key-only','soc_analyst',true);")
    for name, identity in identities.items():
        h=hashlib.sha256(identity['key'].encode()).hexdigest()
        b.pg("SET ROLE aisoc; INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes) VALUES "
             f"('{identity['key_id']}','{identity['tenant_id']}','{identity['user_id']}',"
             f"'socai2-{BATCH}-{name}','{identity['key'][:12]}','{h}','{json.dumps(identity['scopes'])}'::jsonb);")
    receipt={'batch':BATCH,'private_configuration':str(ROOT/'private'),
             'identities':{n:{k:v for k,v in i.items() if k!='key'} for n,i in identities.items()},
             'environment':'production','demo':False,'anonymous_auth_bypass':False,
             'kafka_transport':'SSL/19093 with CA and hostname verification',
             'postgres_transport':'verify-full with PGSSLROOTCERT',
             'runtime_role':'aisoc_app','owner_credential_in_runtime_env':False,
             'api_disabled_workers':[k for k,v in api.items() if v=='false' and ('ENABLED' in k or 'WORKER' in k)],
             'fusion_disabled_branches':[k for k,v in fusion.items() if v in ('false','0')],
             'api_port':'127.0.0.1:18000','fusion_port':'127.0.0.1:18003'}
    (ROOT/'evidence'/BATCH/'configuration.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
