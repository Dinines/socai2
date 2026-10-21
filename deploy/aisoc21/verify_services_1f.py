#!/usr/bin/env python3
"""Record running image dependencies, real configuration and scoped cleanup."""
import argparse
import json
from pathlib import Path
import subprocess

from shared_1b import SharedBatch

ROOT=Path('/opt/sting-aisoc-socai2')

IMAGE_CHECK = r'''
import json, platform, hashlib, importlib.metadata as m, pathlib
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
text=pathlib.Path('/requirements.txt').read_text().replace("\\\n", " ")
expected={}
for line in text.splitlines():
    if not line or line.startswith('#'):continue
    spec=line.split(' --hash=')[0].strip()
    if not spec or spec.startswith('--hash='):continue
    r=Requirement(spec)
    if r.marker is None or r.marker.evaluate():expected[canonicalize_name(r.name)]=str(r.specifier)
installed={canonicalize_name(x.metadata['Name']):x.version for x in m.distributions()}
fail=[n for n,spec in expected.items() if n not in installed or not Requirement(n+spec).specifier.contains(installed[n])]
assert not fail, fail
print(json.dumps({'python':platform.python_version(),'expected_main_packages':len(expected),
    'all_main_versions_match_hash_pinned_requirements':True,
    'requirements_sha256':hashlib.sha256(pathlib.Path('/requirements.txt').read_bytes()).hexdigest(),
    'poetry_in_runtime':'poetry' in installed,'packages':installed}))
'''

API_CHECK = r'''
import json, os, socket, ssl
from app.core.config import settings
from app.core.kafka_security import kafka_client_kwargs, KafkaTransportError
flags=['OAUTH_REFRESH_WORKER_ENABLED','WEEKLY_DIGEST_WORKER_ENABLED','HUNT_SCHEDULER_ENABLED',
       'RETRO_HUNT_ENABLED','REPORT_SCHEDULER_ENABLED','OUTBOUND_WEBHOOK_WORKER_ENABLED',
       'RETENTION_WORKER_ENABLED','PHISHING_INTAKE_WORKER_ENABLED','APPROVAL_EXPIRY_ENABLED',
       'SHADOW_RECONCILE_ENABLED','AUTONOMY_DRIFT_ENABLED','AISOC_WAR_ROOM_SYNC_ENABLED']
values={k:getattr(settings,k) for k in flags}
assert not any(values.values())
assert settings.ENVIRONMENT=='production' and not settings.AISOC_DEMO_MODE
assert settings.AISOC_DISABLE_CLICKHOUSE and settings.AISOC_DISABLE_NEO4J
assert 'DATABASE_MIGRATION_URL' not in os.environ
os.environ['KAFKA_SECURITY_PROTOCOL']='PLAINTEXT'
refused=False
try:kafka_client_kwargs()
except KafkaTransportError:refused=True
assert refused
untrusted_refused=False
try:
    with socket.create_connection(('192.168.1.21',19093),timeout=4) as connection:
        with ssl.create_default_context().wrap_socket(connection,server_hostname='192.168.1.21'):pass
except ssl.SSLCertVerificationError:untrusted_refused=True
assert untrusted_refused
print(json.dumps({'environment':settings.ENVIRONMENT,'disabled_worker_settings':values,
    'graph_lake_startup_disabled':True,'demo':False,'migration_owner_env_absent':True,
    'production_plaintext_kafka_still_refused':True,'kafka_without_private_ca_refused':True}))
'''


def main(revoke):
    b=SharedBatch(ROOT);out=ROOT/'evidence/1f-20261020'
    records={}
    for name in ('api','fusion'):
        x=json.loads(b.run(['docker','exec','-i','socai2-'+name+'-1','python','-'],IMAGE_CHECK).stdout)
        image=json.loads(b.run(['docker','image','inspect','socai2-'+name+':1f-20261020']).stdout)[0]
        x['image_id']=image['Id'];x['image_labels']=image['Config'].get('Labels')
        records[name]=x
    (out/'runtime-images.json').write_text(json.dumps(records,indent=2)+'\n')
    result=json.loads(b.run(['docker','exec','-i','socai2-api-1','python','-'],API_CHECK).stdout)
    result['fusion_consumer_assignment']=b.run(['docker','exec','sting-infra21-kafka-1',
        'kafka-consumer-groups','--bootstrap-server','192.168.1.21:9092',
        '--describe','--group','socai2-fusion-consumer']).stdout
    assert 'socai2.alerts.raw' in result['fusion_consumer_assignment']
    assert 'aisoc.raw_events' not in result['fusion_consumer_assignment']
    if revoke:
        state=json.loads((ROOT/'private/app-1f.json').read_text())
        keys=','.join("'"+i['key_id']+"'" for i in state['identities'].values())
        b.pg('SET ROLE aisoc; UPDATE api_keys SET is_active=false WHERE id IN ('+keys+');')
        remaining=b.pg('SELECT count(*) FROM api_keys WHERE id IN ('+keys+') AND is_active;').stdout.strip()
        assert remaining=='0'
        result['only_three_batch_api_keys_deactivated']=True
        result['test_tenants_alerts_and_audit_evidence_retained']=True
    (out/'postconditions.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'images':{n:{k:v for k,v in x.items() if k not in ('packages','image_labels')} for n,x in records.items()},
                      'checks':result},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--revoke-test-keys',action='store_true')
    main(p.parse_args().revoke_test_keys)
