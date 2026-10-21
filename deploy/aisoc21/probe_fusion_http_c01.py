"""One C01 HTTP ingress through the deployed Fusion; no model invocation.

Host usage: python probe_fusion_http_c01.py run
The sending checkpoint forbids replay even if the HTTP outcome is unknown.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
E = R / 'evidence/c01-fusion-delivery-20261020'
P = R / 'private/completion-c01'


def save(directory, name, value):
    with (directory / name).open('x') as output:
        json.dump(value, output, indent=2, default=str)
        output.write('\n')
    (directory / name).chmod(0o600)


async def inside():
    import asyncio
    from datetime import datetime, timezone
    import uuid
    import httpx
    import structlog
    from aiokafka import AIOKafkaConsumer, TopicPartition
    from app.core.config import settings
    from app.core.kafka_security import kafka_client_kwargs
    from app.models.alert import RawAlert
    from app.services.alert_sink import AlertSink
    from app.services.delivery_recovery import restore_snapshot

    e = Path('/evidence')
    contract = json.loads((e / 'contract.json').read_text())
    body = {'id': str(uuid.uuid5(uuid.NAMESPACE_URL, contract['batch'] + '/http1')),
            'source': 'socai2-c01-20261020', 'title': 'C01 HTTP persistence sample',
            'description': 'Synthetic bounded HTTP/Fusion delivery evidence. Authorization is unavailable.',
            'severity': 'medium', 'hostname': 'C01-HTTP-01', 'username': 'c01-http',
            'source_event_ids': ['socai2-c01-20261020-http1-event'],
            'rule_id': 'C01-HTTP', 'risk_score': None, 'event_time': datetime.now(timezone.utc).isoformat(),
            'raw_event': {'batch': contract['batch'], 'sample': 'http1'},
            'tags': ['socai2-c01-20261020']}
    assert os.getuid() == 10001
    security = kafka_client_kwargs()
    assert security['security_protocol'] == 'SSL'
    consumer = AIOKafkaConsumer(settings.kafka_topic_alerts_fused, bootstrap_servers=settings.kafka_bootstrap_servers,
                                group_id=None, enable_auto_commit=False, **security)
    def drop_log(_logger, _method, _event):
        raise structlog.DropEvent
    structlog.configure(processors=[drop_log])
    sink = AlertSink(settings.database_url)
    await consumer.start()
    try:
        partitions = consumer.partitions_for_topic(settings.kafka_topic_alerts_fused)
        assert partitions
        tps = [TopicPartition(settings.kafka_topic_alerts_fused, p) for p in sorted(partitions)]
        consumer.unsubscribe()
        consumer.assign(tps)
        starts = await consumer.end_offsets(tps)
        for tp in tps:
            consumer.seek(tp, starts[tp])
        save(e, 'read-starts.json', {'topic': settings.kafka_topic_alerts_fused, 'group': None,
             'enable_auto_commit': False, 'starts': [{'partition': p.partition, 'offset': o} for p, o in starts.items()]})
        checks = []
        async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=20) as client:
            save(e, 'sending.json', body)
            response = await client.post('/api/v1/alert-ingress', json=body,
                                        headers={'Authorization': 'Bearer ' + os.environ['C01_HTTP_A_KEY']})
            ack = response.json()
            save(e, 'ingress-response.json', {'status': response.status_code, 'body': ack})
            assert response.status_code == 202
            canonical = ack['canonical_alert_id']
            assert ack['tenant_id'] == contract['tenants']['a'] and ack['identity_version'] == 'source-v1'
            assert ack['processing_confirmed'] is False
            path = '/api/v1/alerts/' + canonical
            stored = None
            for index in range(80):
                response = await client.get(path, headers={'Authorization': 'Bearer ' + os.environ['C01_HTTP_A_KEY']})
                checks.append({'method': 'GET', 'identity': 'a', 'path': path, 'status': response.status_code})
                assert response.status_code in [200, 404]
                if response.status_code == 200:
                    stored = response.json()
                    break
                await asyncio.sleep(.25)
            assert stored and stored['id'] == canonical and stored['tenant_id'] == contract['tenants']['a']
            assert stored['raw_event'] == body['raw_event'] and stored['description'] == body['description']
            save(e, 'stored-alert.json', stored)
            for alias, headers, expected in [('b', {'Authorization': 'Bearer ' + os.environ['C01_HTTP_B_KEY']}, 404),
                                              ('none', {}, 401)]:
                response = await client.get(path, headers=headers)
                checks.append({'method': 'GET', 'identity': alias, 'path': path, 'status': response.status_code})
                assert response.status_code == expected
            save(e, 'http-checks.json', checks)
        matches = []
        deadline = asyncio.get_running_loop().time() + 20
        while not matches and asyncio.get_running_loop().time() < deadline:
            records = await consumer.getmany(timeout_ms=250, max_records=100)
            for messages in records.values():
                for message in messages:
                    payload = json.loads(message.value)
                    if payload.get('alert_row_id') == canonical:
                        matches.append({'topic': message.topic, 'partition': message.partition,
                                        'offset': message.offset, 'value': payload})
        save(e, 'fused-matches.json', matches)
        assert len(matches) == 1
        fused = matches[0]['value']
        assert fused['persist_outcome'] == 'inserted' and fused['incident_id']
        assert fused['alert']['description'] == body['description'] and fused['alert']['raw_event'] == body['raw_event']
        alert = RawAlert.model_validate(fused['alert'])
        assert str(alert.deterministic_id()) == canonical
        await sink.start()
        found = await sink.lookup_delivery(alert)
        assert found.exists and found.alert_id == canonical and found.snapshot
        recovered = restore_snapshot(found.snapshot, alert).model_dump(mode='json')
        assert all(fused[k] == value for k, value in recovered.items())
        save(e, 'pg-snapshot.json', found.snapshot)
        save(e, 'acceptance.json', {'accepted': True, 'image_id': contract['image_id'],
             'canonical_alert_id': canonical, 'incident_id': fused['incident_id'],
             'actual_http_requests': 1 + len(checks), 'new_alert_rows': 1,
             'http_publishes': 1, 'fused_captured': 1, 'real_models': 0,
             'pg_snapshot_matches_actual_fused': True, 'unauthorized_401': True, 'other_tenant_404': True})
        print(json.dumps({'http_accepted': True, 'canonical_alert_id': canonical, 'real_models': 0}))
    finally:
        await sink.stop()
        await consumer.stop()


def host(*, startup_recovery=False):
    from configure_triage_admission_3a import inspect
    os.umask(0o077)
    assert (E / 'deployment.json').is_file()
    directory = E / 'http'
    if startup_recovery:
        assert sorted(p.name for p in directory.iterdir()) == ['contract.json']
        old_exit = json.loads((E / 'http-exit.json').read_text())
        assert old_exit['exit_code'] == 1
        assert hashlib.sha256((E / 'http.log').read_bytes()).hexdigest() == old_exit['log_sha256']
        assert 'ImportError' in (E / 'http.log').read_text() and 'partially initialized module' in (E / 'http.log').read_text()
        assert (E / 'http-first-operator.py').is_file()
        assert hashlib.sha256((E / 'http-first-operator.py').read_bytes()).hexdigest() == json.loads((E / 'http-started.json').read_text())['operator_sha256']
        from deploy_fusion_delivery_c01 import raw_offsets
        assert raw_offsets() == json.loads((E / 'production-offsets-before.json').read_text())
    else:
        directory.mkdir(mode=0o700, exist_ok=False)
        os.chown(directory, 10001, 10001)
    state = json.loads((P / 'state.json').read_text())
    image = json.loads((E / 'built-image.json').read_text())['fusion']
    current = inspect('socai2-fusion-1')
    assert current['Image'] == image and current['State']['Health']['Status'] == 'healthy'
    networks = list(current['NetworkSettings']['Networks'])
    assert len(networks) == 1
    contract = {'batch': state['batch'], 'image_id': image,
                'tenants': {a: v['tenant_id'] for a, v in state['identities'].items()}}
    key_env = ''.join('C01_HTTP_' + alias.upper() + '_KEY=' + state['identities'][alias]['key'] + '\n' for alias in ['a', 'b'])
    if startup_recovery:
        assert json.loads((directory / 'contract.json').read_text()) == contract
        assert (P / 'http.env').read_text() == key_env
    else:
        save(directory, 'contract.json', contract)
        os.chown(directory / 'contract.json', 10001, 10001)
        with (P / 'http.env').open('x') as output:
            output.write(key_env)
        (P / 'http.env').chmod(0o600)
    operator = S / 'deploy/aisoc21/probe_fusion_http_c01.py'
    prefix = 'http-startup-fixed' if startup_recovery else 'http'
    name = 'socai2-c01-' + prefix
    save(E, prefix + '-started.json', {'image_id': image, 'operator_sha256': hashlib.sha256(operator.read_bytes()).hexdigest(),
         'network': networks[0], 'uid': 10001, 'source_mount': 'read-only',
         'startup_recovery_before_any_request': startup_recovery, 'prior_records_preserved': startup_recovery})
    command = ['docker', 'run', '--rm', '--pull', 'never', '--name', name,
               '--network', networks[0], '--user', '10001:10001', '--read-only', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges:true', '--env-file', str(P / 'probe.env'),
               '--env-file', str(P / 'http.env'), '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'PYTHONPATH=/app',
               '-v', str(directory) + ':/evidence:rw', '-v', str(operator) + ':/c01_http_probe.py:ro',
               '-v', str(R / 'certificates/socai2-ca.crt') + ':/run/certs/ca.crt:ro',
               image, 'python', '/c01_http_probe.py', 'inside']
    log = E / (prefix + '.log')
    with log.open('x') as output:
        try:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=80)
            code = result.returncode
        except subprocess.TimeoutExpired:
            cleanup = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
            output.write('Only the C01 HTTP container was removed after the probe deadline.\n')
            code = 124
    log.chmod(0o600)
    save(E, prefix + '-exit.json', {'exit_code': code, 'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()})
    assert code == 0, 'HTTP probe failed; inspect sending/ack before any recovery'
    accepted = json.loads((directory / 'acceptance.json').read_text())
    print(json.dumps(accepted))


if __name__ == '__main__':
    if sys.argv[1:] == ['run']:
        host()
    elif sys.argv[1:] == ['run-fixed-startup']:
        host(startup_recovery=True)
    elif sys.argv[1:] == ['inside']:
        import asyncio
        try:
            asyncio.run(inside())
        except BaseException as exc:
            save(Path('/evidence'), 'failure.json', {'exception_type': type(exc).__name__, 'no_exception_text_or_locals': True})
            print(json.dumps({'failed': True, 'exception_type': type(exc).__name__}))
            raise SystemExit(1)
    else:
        raise SystemExit('Usage: probe_fusion_http_c01.py run')
