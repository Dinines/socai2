"""Read-only recovery of C01's legacy-replay probe assertion failure.

This never launches a worker, creates a topic/group, publishes, commits,
deletes, or reruns the failed phase. It reads PostgreSQL in a READ ONLY
transaction and existing Kafka group/end-offset metadata, then exclusively
writes an explicit recovered checkpoint. Original failure evidence remains.
Run once on host21: python recover_fusion_boundaries_c01.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

import probe_fusion_boundaries_c01 as boundary_probe
import probe_fusion_delivery_c01 as main_probe
from configure_triage_admission_3a import pg
from prepare_identity_read_3a import lit

E, S = main_probe.E, main_probe.S
read, save, sha, digest, sources = main_probe.read, main_probe.save, main_probe.sha, main_probe.digest, main_probe.sources


# Manual assignment plus committed/end_offsets only: no group subscription,
# no getone/getmany, no producer, no commit or seek/reset operation.
METADATA = '''import asyncio,json,sys,ssl
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.config import settings
from app.core.kafka_security import kafka_client_kwargs
async def main():
 cfg=json.load(sys.stdin);security=kafka_client_kwargs()
 assert security['security_protocol']=='SSL'
 assert security['ssl_context'].check_hostname and security['ssl_context'].verify_mode==ssl.CERT_REQUIRED
 result={}
 for alias,value in cfg.items():
  c=AIOKafkaConsumer(bootstrap_servers=settings.kafka_bootstrap_servers,group_id=value['group'],enable_auto_commit=False,**security)
  await c.start()
  try:
   tp=TopicPartition(value['raw'],0);output=TopicPartition(value['fused'],0)
   c.assign([tp])
   result[alias]={'committed':await c.committed(tp),'raw_end':(await c.end_offsets([tp]))[tp],
                  'fused_end':(await c.end_offsets([output]))[output]}
  finally:await c.stop()
 print(json.dumps(result))
asyncio.run(main())'''


def tree_hashes(directory):
    return {str(path.relative_to(directory)): sha(path) for path in sorted(directory.rglob('*')) if path.is_file()}


def metadata(cfg):
    result = subprocess.run(['docker', 'exec', '-i', 'socai2-fusion-1', 'python', '-c', METADATA],
                            input=json.dumps(cfg), text=True, capture_output=True, timeout=100)
    if result.returncode:
        raise RuntimeError('Read-only Kafka metadata check failed; no replay attempted')
    return json.loads(result.stdout.splitlines()[-1])


def inspect(name, *, image=False):
    command = ['docker', 'image', 'inspect', name] if image else ['docker', 'inspect', name]
    return json.loads(subprocess.check_output(command))[0]


def main():
    assert len(sys.argv) == 1
    os.umask(0o077)
    directory = E / 'boundaries'
    recovery_path = directory / 'legacy-replay-readonly-recovery.json'
    done_path = directory / 'legacy-replay-done.json'
    assert not recovery_path.exists() and not done_path.exists(), 'Recovery is exclusive; do not repeat.'
    original_evidence = tree_hashes(directory)
    contract = read(directory / 'contract.json')
    built = read(E / 'built-image.json')
    assert contract['batch'] == main_probe.BATCH and contract['source'] == main_probe.SOURCE
    assert contract['operator_sha256'] == sha(boundary_probe.__file__)
    assert contract['main_operator_sha256'] == sha(main_probe.__file__)
    assert contract['runtime_source_sha256'] == sources(S) == built['source_sha256']
    assert contract['candidate_image'] == built['fusion']
    assert inspect(built['fusion'], image=True)['Id'] == built['fusion']
    assert inspect('socai2-fusion-1')['Image'] == contract['parent_image']
    assert sha(E / 'limits-amended.json') == contract['amended_limits_sha256']
    tests = [path for path in E.glob('tests-fusion-*.json') if sha(path) == contract['unit_test_record_sha256']]
    assert len(tests) == 1
    tested = read(tests[0])
    assert tested['exit_code'] == tested['failed'] == tested['errors'] == 0 and tested['passed'] > 0
    assert tested['source_unchanged'] and tested['test_inputs_unchanged']
    assert tested['tested_runtime_source_sha256'] == built['source_sha256']
    assert all(sha(S / name) == value for name, value in tested['test_input_sha256'].items())

    failure = read(directory / 'legacy-replay-failure.json')
    host_exit = read(E / 'boundaries-host-legacy-replay-exit.json')
    host_started = read(E / 'boundaries-host-legacy-replay-started.json')
    assert failure['phase'] == 'legacy-replay' and failure['exception_type'] == 'AssertionError'
    assert host_exit['exit_code'] == 1 and host_exit['source_unchanged'] is True
    assert host_started['operator_sha256'] == contract['operator_sha256']
    assert host_started['contract_sha256'] == sha(directory / 'contract.json')
    assert host_started['candidate_image'] == built['fusion']
    assert (directory / 'legacy-replay-started.json').is_file()
    assert not (directory / 'legacy-replay-worker-exception.json').exists()
    assert not (directory / 'gap-seed-started.json').exists(), 'Later mutations require a separate review.'

    inputs = read(directory / 'inputs.json')
    assert {key: digest(value) for key, value in inputs.items()} == read(directory / 'input-hashes.json')
    original_row = read(directory / 'legacy-first-done.json')['material']['rows'][0]
    first = read(directory / 'first-result-legacy.json')
    canonical_id, tenant = inputs['legacy']['id'], contract['tenant_id']
    assert original_row['id'] == canonical_id and original_row['tenant_id'] == tenant
    assert inputs['legacy_replay']['id'] == canonical_id
    sql = ('SELECT row_to_json(a)::text FROM alerts a WHERE tenant_id=' + lit(tenant) +
           '::uuid AND id=' + lit(canonical_id) + '::uuid;')
    rows = pg(sql).stdout.strip().splitlines()
    assert len(rows) == 1
    current_row = json.loads(rows[0])
    without_provenance = lambda row: {key: value for key, value in row.items() if key != 'source_event_ids'}
    assert without_provenance(current_row) == without_provenance(original_row)
    assert current_row['enrichment_data']['socai2_fusion']['delivery_snapshot'] == first
    assert original_row['enrichment_data']['socai2_fusion']['delivery_snapshot'] == first
    old_ids = original_row['source_event_ids']
    assert canonical_id in old_ids  # validate_event also supplies raw.id lineage.
    additions = [value for value in inputs['legacy_replay']['source_event_ids'] if value not in old_ids]
    assert additions == [main_probe.SOURCE + '-boundary-legacy-later']
    expected_ids = old_ids + additions
    assert current_row['source_event_ids'] == expected_ids

    cfg = boundary_probe.resources()
    assert cfg == contract['resources']
    positions = metadata(cfg)
    assert positions == {'legacy': {'committed': 2, 'raw_end': 2, 'fused_end': 2},
                         'gap': {'committed': 0, 'raw_end': 0, 'fused_end': 0},
                         'dlq': {'committed': 0, 'raw_end': 0, 'fused_end': 0}}
    publishes = [read(path) for path in sorted(directory.glob('event-publish-*.json'))]
    acknowledgements = [read(path) for path in sorted(directory.glob('event-fused_ack-*.json'))]
    deliveries = [read(path) for path in sorted(directory.glob('event-delivery-*.json'))]
    assert len(publishes) == 4 and sum(value['kind'] == 'raw' for value in publishes) == 2
    assert len(acknowledgements) == len(deliveries) == 2
    assert all(value['kind'] == 'worker' and value['alias'] == 'legacy' for value in deliveries)
    mapped = []
    for offset, phase in enumerate(('legacy-first', 'legacy-replay')):
        body = dict(first['fused'], alert_row_id=canonical_id, persist_outcome='inserted' if offset == 0 else 'duplicate')
        body_hash = digest(body)
        publication = next(value for value in publishes if value['kind'] == 'fused' and value['phase'] == phase)
        acknowledgement = next(value for value in acknowledgements if value['phase'] == phase)
        assert publication['body_sha256'] == acknowledgement['body_sha256'] == body_hash
        assert acknowledgement['topic'] == cfg['legacy']['fused'] and acknowledgement['partition'] == 0
        assert acknowledgement['offset'] == offset
        delivery = next(value for value in deliveries if value['phase'] == phase)
        assert delivery['topic'] == cfg['legacy']['raw'] and delivery['partition'] == 0 and delivery['offset'] == offset
        raw_label = 'legacy' if offset == 0 else 'legacy_replay'
        raw_ack = read(directory / ('raw-' + raw_label + '-ack.json'))
        assert raw_ack['topic'] == cfg['legacy']['raw'] and raw_ack['partition'] == 0 and raw_ack['offset'] == offset
        assert raw_ack['input_sha256'] == digest(inputs[raw_label]) == delivery['input_sha256']
        mapped.append({'phase': phase, 'raw_coordinate': {'topic': raw_ack['topic'], 'partition': 0, 'offset': offset},
                       'fused_coordinate': {'topic': acknowledgement['topic'], 'partition': 0, 'offset': offset},
                       'fused_body_sha256': body_hash})
    assert tree_hashes(directory) == original_evidence
    assert sources(S) == built['source_sha256']
    recovery = {
        'phase': 'legacy-replay', 'recovered_after_probe_assertion_error': True,
        'original_probe_passed': False, 'not_original_pass': True, 'no_resend': True,
        'cause': 'Probe expected replay.source_event_ids and omitted the canonical raw.id lineage already retained on the first row.',
        'correct_expectation': 'first PG source_event_ids plus the new later source event; all other PG fields and first snapshot unchanged',
        'operator_sha256': sha(__file__), 'original_operator_sha256': contract['operator_sha256'],
        'original_contract_sha256': sha(directory / 'contract.json'), 'original_evidence_sha256': original_evidence,
        'candidate_image': built['fusion'], 'image_id': built['fusion'], 'source_sha256': built['source_sha256'],
        'original_failure_sha256': sha(directory / 'legacy-replay-failure.json'),
        'original_host_exit_sha256': sha(E / 'boundaries-host-legacy-replay-exit.json'),
        'positions': positions, 'source_event_ids_before': old_ids, 'source_event_ids_after': current_row['source_event_ids'],
        'expected_source_event_ids': expected_ids, 'all_other_pg_fields_equal': True,
        'pg_snapshot_exactly_first_result': True, 'transport_coordinate_mapping': mapped,
        'read_only_pg': True, 'kafka_metadata_only': True, 'record_deliveries_added': 0,
        'publishes_added': 0, 'commits_added': 0, 'deletes_added': 0, 'workers_started': 0,
        'new_schema_or_topics_or_groups': 0, 'real_models': 0,
    }
    save(directory, recovery_path.name, recovery)
    os.chown(recovery_path, 10001, 10001)
    done = {
        'phase': 'legacy-replay', 'recovered_after_probe_assertion_error': True,
        'original_probe_passed': False, 'not_original_pass': True, 'no_resend': True,
        'recovery_record': recovery_path.name, 'recovery_record_sha256': sha(recovery_path),
        'material': {'rows': [current_row], 'dead_letters': [], 'read_only_host_pg': True, 'pg_tls_not_remeasured': True},
        'positions': positions, 'real_models': 0, 'shared_restarts': 0, 'ddl': 0,
    }
    save(directory, done_path.name, done)
    os.chown(done_path, 10001, 10001)
    assert {name: sha(directory / name) for name in original_evidence} == original_evidence
    print(json.dumps({'legacy_replay_recovered_from_readonly_checks': True, 'original_probe_passed': False,
                      'no_resend': True, 'no_commit': True, 'later_phases_started': False,
                      'recovery_record': str(recovery_path)}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'recovery_failed': True, 'exception_type': type(exc).__name__,
                          'action': 'Inspect existing checkpoints; do not replay the original phase.'}))
        raise SystemExit(1) from None
