"""Send one existing-alert fixture and capture its real Fusion result; no model.

There is deliberately no replay/resume mode. A sending checkpoint means that
publication may have happened, even when the HTTP outcome is unknown.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.core.kafka_security import kafka_client_kwargs

E = Path('/evidence')
B = '3a-triage-durability-20261020'
POLL_LIMIT = 80
CAPTURE_SECONDS = 30
QUIET_SECONDS = 2


def now():
    return datetime.now(timezone.utc).isoformat()


def save(name, value):
    path = E / name
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
    path.chmod(0o600)


def journal(name, value):
    """Replace only the growing status journal; final evidence uses save(x)."""
    path = E / name
    temporary = E / (name + '.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
    temporary.chmod(0o600)
    temporary.replace(path)


async def main():
    assert not any((E / name).exists() for name in
                   ['normal-sending.json', 'normal-ack.json', 'normal-ingress-acceptance.json']), \
        'Prior input may be published; inspect existing evidence, never resubmit'
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    ids = state['identities']
    assert {'a', 'b', 'denied'} <= set(ids)
    tenant = str(uuid.UUID(ids['a']['tenant_id']))
    assert tenant == ids['a']['tenant_id'] and ids['a']['key']
    assert tenant != ids['b']['tenant_id']
    # Importing a worker would load model code. Check its explicit OFF setting
    # directly instead; this operator never creates or invokes a worker.
    assert os.environ.get('AISOC_AGENT_KAFKA_DISABLE', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
    security = kafka_client_kwargs()
    assert security['security_protocol'] in {'SSL', 'SASL_SSL'}
    save('normal-ingress-started.json', {'batch': B, 'at': now(), 'tenant_id': tenant,
                                       'resident_worker_enabled': False, 'model_calls': 0,
                                       'consumer_group': None, 'enable_auto_commit': False})
    body = {
        'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/normal')),
        'source': 'socai2-' + B, 'source_event_ids': [str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/normal-event'))],
        'title': 'Account access review', 'severity': 'medium',
        'rule_id': 'R-DURABILITY-A', 'hostname': 'DURABILITY-HOST-A', 'username': 'svc-identity-a',
        'risk_score': None, 'mitre_tactics': [], 'mitre_techniques': [], 'tags': ['review-074'],
        'raw_event': {'evidence_summary': 'Limited synthetic account-access material for a reliability check. '
                      'Current authorization, process ancestry and job evidence are unavailable.'},
        'event_time': now(),
    }
    checks, polls, matches = [], [], []
    stage = 'consumer_start'
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                **security, group_id=None, enable_auto_commit=False)
    try:
        await consumer.start()
        partitions = sorted(consumer.partitions_for_topic(topic) or [])
        assert partitions == [0, 1, 2], ('Expected the three existing fused partitions', partitions)
        assigned = [TopicPartition(topic, partition) for partition in partitions]
        consumer.unsubscribe()
        consumer.assign(assigned)
        starts = await consumer.end_offsets(assigned)
        for partition, offset in starts.items():
            consumer.seek(partition, offset)
        save('normal-fused-read-starts.json', {'topic': topic, 'group_id': None,
                                             'enable_auto_commit': False, 'security_protocol': security['security_protocol'],
                                             'partitions': [{'partition': part.partition, 'offset': starts[part]}
                                                            for part in assigned], 'at': now()})
        async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
            headers = {'Authorization': 'Bearer ' + ids['a']['key']}
            stage = 'http_publish_outcome_unknown'
            save('normal-sending.json', body)
            checks.append({'sequence': 1, 'method': 'POST', 'path': '/api/v1/alert-ingress',
                           'identity': 'a', 'status': None, 'expected': 202, 'at': now(),
                           'outcome': 'request_started_outcome_unknown'})
            journal('normal-http-checks.json', checks)
            response = await client.post('/api/v1/alert-ingress', headers=headers, json=body)
            checks[-1].update(status=response.status_code, outcome='response_received', completed_at=now())
            journal('normal-http-checks.json', checks)
            save('normal-publish-response.json', {'status': response.status_code,
                                                  'body': response.json() if response.content else None})
            assert response.status_code == 202, 'Publish not confirmed; never resubmit this input'
            ack = response.json()
            save('normal-ack.json', ack)
            canonical = str(uuid.UUID(ack['canonical_alert_id']))
            assert ack['input_id'] == body['id'] and ack['tenant_id'] == tenant
            assert ack['identity_version'] == 'source-v1' and ack['processing_confirmed'] is False
            stage = 'accepted_pg_result_unknown'
            stored = None
            for index in range(POLL_LIMIT):
                path = '/api/v1/alerts/' + canonical
                check = {'sequence': len(checks) + 1, 'method': 'GET', 'path': path, 'identity': 'a',
                         'status': None, 'allowed': [404, 200], 'poll': index + 1, 'at': now(),
                         'outcome': 'request_started_outcome_unknown'}
                checks.append(check)
                poll = {'poll': index + 1, 'status': None, 'at': check['at'], 'outcome': check['outcome']}
                polls.append(poll)
                journal('normal-alert-polls.json', polls)
                journal('normal-http-checks.json', checks)
                response = await client.get(path, headers=headers)
                check.update(status=response.status_code, outcome='response_received', completed_at=now())
                poll.update(status=response.status_code, outcome='response_received', completed_at=check['completed_at'])
                journal('normal-alert-polls.json', polls)
                journal('normal-http-checks.json', checks)
                poll['body'] = response.json() if response.content else None
                save(f'normal-alert-poll-{index + 1:03d}.json', poll)
                journal('normal-alert-polls.json', polls)
                journal('normal-http-checks.json', checks)
                assert response.status_code in {404, 200}, 'Unexpected read-back result; inspect without replay'
                if response.status_code == 200:
                    stored = response.json()
                    save('normal-stored-alert.json', stored)
                    break
                await asyncio.sleep(.25)
            assert stored is not None, 'Accepted input has no confirmed PG/API result; never resubmit'
            assert stored['id'] == canonical and stored['tenant_id'] == tenant
            assert stored['raw_event']['evidence_summary'] == body['raw_event']['evidence_summary']
            assert body['id'] in stored['source_event_ids']
            assert stored['fusion_identity']['source_alert_id'] == body['id']
            assert stored['fusion_identity']['source'] == body['source']

        stage = 'accepted_fused_result_unknown'
        loop = asyncio.get_running_loop()
        deadline, quiet_deadline = loop.time() + CAPTURE_SECONDS, None
        observed = {str(part.partition): 0 for part in assigned}
        while loop.time() < (quiet_deadline if quiet_deadline is not None else deadline):
            records = await consumer.getmany(timeout_ms=250, max_records=100)
            for messages in records.values():
                for message in messages:
                    observed[str(message.partition)] += 1
                    value = json.loads(message.value)
                    if str(value.get('alert_row_id')) != canonical:
                        continue
                    coordinate = {'topic': message.topic, 'partition': message.partition, 'offset': message.offset,
                                  'timestamp': message.timestamp, 'sha256': hashlib.sha256(message.value).hexdigest()}
                    matches.append(coordinate)
                    journal('normal-fused-matches.json', matches)
                    assert len(matches) == 1, 'Multiple matching Fusion messages observed; inspect, never resend'
                    save('normal-fused-envelope.json', value)
                    save('normal-fused-coordinate.json', coordinate)
                    assert value['tenant_id'] == tenant and value['id'] == canonical
                    assert value['persist_outcome'] == 'inserted'
                    alert = value['alert']
                    assert alert['id'] == canonical and alert['tenant_id'] == tenant
                    assert alert['source_alert_id'] == body['id'] and alert['source'] == body['source']
                    assert alert['rule_id'] == body['rule_id'] and alert['hostname'] == body['hostname']
                    assert alert['username'] == body['username'] and alert['risk_score'] is None
                    assert not alert['mitre_tactics'] and not alert['mitre_techniques']
                    assert alert['raw_event'] == body['raw_event']
                    quiet_deadline = loop.time() + QUIET_SECONDS
            if quiet_deadline is not None and loop.time() >= quiet_deadline:
                break
        assert len(matches) == 1, 'Fused outcome unconfirmed; never resubmit'
        stage = 'accepted'
        acceptance = {'batch': B, 'at': now(), 'input_id': body['id'], 'canonical_alert_id': canonical,
                      'tenant_id': tenant, 'ack': ack, 'fused_coordinate': matches[0],
                      'http': {'explicit_requests': len(checks), 'ingress_posts': 1, 'alert_polls': len(polls),
                               'poll_statuses': [item['status'] for item in polls], 'final_poll_status': 200},
                      'checks': checks, 'stored_alert_via_real_pg_backed_api': True,
                      'kafka': {'security_protocol': security['security_protocol'], 'group_id': None,
                                'enable_auto_commit': False, 'commit_calls': 0, 'partitions': partitions,
                                'observed_records_by_partition': observed, 'matching_records': len(matches),
                                'post_match_observation_seconds': QUIET_SECONDS,
                                'uniqueness_limited_to_observed_window': True},
                      'new_inputs': 1, 'model_calls': 0, 'worker_invocations': 0,
                      'real_model_not_imported_or_called_by_operator': True,
                      'does_not_claim_infinite_deduplication_or_model_quality': True}
        save('normal-ingress-acceptance.json', acceptance)
        print(json.dumps({'accepted': True, 'canonical_alert_id': canonical, 'http_requests': len(checks),
                          'polls': len(polls), 'fused_coordinate': matches[0], 'model_calls': 0}))
    except BaseException as exc:
        if not (E / 'normal-ingress-failure.json').exists():
            save('normal-ingress-failure.json', {'batch': B, 'at': now(), 'stage': stage,
                                                'error_type': type(exc).__name__, 'error': str(exc)[:1000],
                                                'sending_checkpoint_exists': (E / 'normal-sending.json').exists(),
                                                'ack_exists': (E / 'normal-ack.json').exists(),
                                                'http_requests_recorded': len(checks), 'polls_recorded': len(polls),
                                                'matching_fused_records': len(matches), 'model_calls': 0,
                                                'automatic_retry_or_republish_allowed': False})
        raise
    finally:
        with contextlib.suppress(asyncio.CancelledError):
            await consumer.stop()


if __name__ == '__main__':
    assert len(sys.argv) == 1, 'This operator has no retry or replay mode'
    asyncio.run(main())
