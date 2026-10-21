"""C03-02C-01 draft: freeze parent and source-only offline fixtures; no mutation."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import os
import subprocess

from configure_triage_admission_3a import observation, private_hashes, inspect, describe, save, container_json, FLAGS_CODE, OFFSET_CODE as LEGACY_OFFSET_CODE
# Copied as data only: importing the legacy finish module installs process-wide
# counter hooks that append to its sealed batch. No legacy module is imported.
METADATA_CODE = "import asyncio,json,os,sys\nfrom aiokafka import AIOKafkaConsumer,TopicPartition\nfrom app.core.kafka_security import kafka_client_kwargs\ncfg=json.load(sys.stdin)\nasync def main():\n security=kafka_client_kwargs();assert security['security_protocol']=='SSL'\n if cfg['kind']=='raw':\n  from app.core.config import settings\n  selected={'raw':(settings.kafka_topic_alerts_raw,settings.kafka_consumer_group)}\n else:\n  selected={'quality':(cfg['broker']['quality_topic'],cfg['broker']['group']),\n   'dlq':(cfg['broker']['dlq_topic'],None),\n   'main':(os.getenv('KAFKA_TOPIC_ALERTS_FUSED','aisoc.alerts.fused'),os.getenv('KAFKA_CONSUMER_GROUP','aisoc-agents-triage'))}\n out={}\n for alias,(topic,group) in selected.items():\n  c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=group,enable_auto_commit=False,**security)\n  await c.start()\n  try:\n   await c._client.add_topic(topic);parts=c.partitions_for_topic(topic);assert parts\n   tps=[TopicPartition(topic,p) for p in sorted(parts)]\n   begins,ends=await c.beginning_offsets(tps),await c.end_offsets(tps)\n   out[alias]={'topic':topic,'group':group,'partitions':[{'partition':tp.partition,'begin':begins[tp],\n    'end':ends[tp],'committed':await c.committed(tp) if group else None} for tp in tps],\n    'physical_record_reads':0,'polls':0,'assigns':0,'commits':0}\n  finally:await c.stop()\n print(json.dumps(out))\nasyncio.run(main())"

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
E = R / 'evidence/c03-triage-authorization-20261021'
P = R / 'private/completion-c03-authorization'
PREVIOUS = R / 'evidence/c03-triage-quality-recheck-20261021'
PARENT_STATE = R / 'private/completion-c03-quality-recheck/state.json'
PLAN = S / 'docs/operations/c03-triage-authorization-plan.md'
INPUTS = S / 'docs/operations/c03-triage-quality-recheck-inputs.json'
FILES = ['services/agents/app/llm/prompt_registry.py', 'services/agents/app/llm/prompts.lock.json']
TEST = 'tests/porting/test_triage_reasoning_prompt_c03.py'
assert LEGACY_OFFSET_CODE.count(';c.assign([tp])') == 1
OFFSET_CODE = LEGACY_OFFSET_CODE.replace(';c.assign([tp])', '')
PARENT = 'sha256:039f2cb09684c29e170b8907572196ff5559c9d7991837fc431a12d113350985'
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read', 'recent_dispositions_read', 'identity_context_read')
MATERIALS = ('organisation_memory', 'tenant_skill', 'knowledge_base', 'recent_dispositions', 'identity_context')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def metadata(state):
    result = container_json(METADATA_CODE, payload={'kind': 'agents', 'broker': state['broker']})
    result.update(container_json(METADATA_CODE, service='fusion', payload={'kind': 'raw'}))
    return result  # Only metadata; this helper never assign/poll/getone/commit.


def freeze_fixture():
    # File reads only: no reader service or old model replay. No rubric/keys.
    base = PREVIOUS / 'cases/case01'
    names = {'facts': base / 'preflight/fact-projection.json',
             'envelope': base / 'ingress/fused-envelope.json', 'inputs': INPUTS}
    projection, first, inputs = read(names['facts']), read(names['envelope']), read(INPUTS)
    assert set(projection['materials']) == set(MATERIALS) and set(projection['reads']) == set(READS)
    assert set(inputs['cases']) == {'case01', 'case02', 'case03', 'case04'}
    assert sha(INPUTS) == read(PREVIOUS / 'acceptance.json')['inputs_sha256']
    cases = {}
    for case, item in inputs['cases'].items():
        envelope = deepcopy(first)
        if case != 'case01':
            envelope['alert'].update(deepcopy(item['alert']))
            for key in ('id', 'alert_row_id'):
                envelope[key] = item['alert']['id']
            # Reuse the controlled A source context for all transport cases.
            # These are offline constructed fixtures, never actual B reads.
            envelope['alert']['tenant_id'] = first['tenant_id']
        cases[case] = {'envelope': envelope, 'materials': deepcopy(projection['materials']),
            'reads': deepcopy(projection['reads']), 'source_alert_tenant_alias': item['tenant'],
            'five_source_fixture_case': '02B-case01', 'actual_reader_calls_this_probe': 0,
            'constructed_transport_fixture_not_current_authorization': True}
    value = {'synthetic_only': True, 'case_order': list(inputs['cases']), 'cases': cases,
        'source_file_sha256': {key: sha(path) for key, path in names.items()},
        'old_unexecuted_cases_not_sent_to_provider': ['02-case02', '02-case03', '02-case04',
                                                    '02B-case02', '02B-case03', '02B-case04'],
        'all_four_use_same_controlled_A_five_source_fixture': True,
        'new_quality_inputs_or_real_reader_evidence': False}
    save(E, 'probe-fixture.json', value)
    os.chown(E / 'probe-fixture.json', 10001, 10001)
    return sha(E / 'probe-fixture.json')


def main():
    os.umask(0o077)
    parent = read(PREVIOUS / 'acceptance.json')
    assert parent['change'] == 'C03-02B' and parent['bounded_closeout_accepted'] is True
    assert parent['four_case_model_quality_accepted'] is False and parent['image_id'] == PARENT
    assert read(PREVIOUS / 'finish-phases/seal/completed.json')['acceptance_sha256'] == sha(PREVIOUS / 'acceptance.json')
    for name in ('finish-independent-audit.json', 'closeout-independent-audit.json'):
        assert read(PREVIOUS / name)['accepted'] is True
    E.mkdir(mode=0o700, exist_ok=False)
    P.mkdir(mode=0o700, exist_ok=False)
    before = observation()
    assert before == read(PREVIOUS / 'finish-after.json')['protected']['observation']
    assert len(before['budget']) == 7 and sum(row['charged_tokens'] for row in before['budget']) == 140000
    assert sum(row['settled_at'] is None for row in before['budget']) == 3
    save(E, 'before.json', before)
    save(E, 'private-input-hashes.json', private_hashes())
    old = inspect('socai2-agents-1')
    assert old['Image'] == PARENT and old['State']['Health']['Status'] == 'healthy'
    assert old['Config']['StopTimeout'] == 60
    save(P, 'agents-container-before.json', old)
    save(E, 'agents-before.json', describe(old))
    (E / 'scope-before.md').write_bytes(PLAN.read_bytes())
    (E / 'scope-before.md').chmod(0o600)
    state = read(PARENT_STATE)
    tenants = [state['identities'][alias]['tenant_id'] for alias in ('a', 'b')]
    flags = container_json(FLAGS_CODE, payload=tenants)
    assert flags['uid'] == 10001 and flags['reader_maps_resolve']
    assert all(flags[key] is False for key in ('worker', 'escalation', 'memory_writeback', 'approvals', 'alert_graph'))
    local = {str(path.relative_to(S)): sha(path) for path in (S / 'services/agents/app').rglob('*.py')}
    assert len(local) == 184 and local == flags['source']
    save(E, 'resident-before.json', flags)
    save(E, 'budget-group-offsets-before.json', container_json(OFFSET_CODE))
    save(E, 'main-quality-raw-metadata-before.json', metadata(state))
    for name in FILES:
        path = E / 'parent-sources' / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        subprocess.run(['docker', 'cp', 'socai2-agents-1:/app/app/' + name.removeprefix('services/agents/app/'), str(path)], check=True, capture_output=True)
        path.chmod(0o600)
        assert sha(path) == sha(S / name)
    test_copy = E / 'parent-sources' / TEST
    test_copy.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    test_copy.write_bytes((S / TEST).read_bytes())
    test_copy.chmod(0o600)
    limits = {'real_models': 0, 'new_broker_send_attempts': 0, 'new_broker_record_deliveries': 0,
        'broker_offset_commits': 0, 'business_pg_writes': 0, 'new_keys': 0, 'new_readers': 0,
        'new_tenants': 0, 'ddl': 0, 'only_recreate': 'agents', 'max_recreates': 1,
        'mock_http_requests': 4, 'expected_direct_tests': 88,
        'new_offset_helper_assigns_polls_record_reads_commits': 0,
        'old_shared_offset_helper_not_modified': True}
    save(E, 'limits.json', limits)
    fixture = freeze_fixture()
    save(E, 'prepared.json', {'batch': E.name, 'scope_sha256': sha(PLAN), 'parent_image': PARENT,
        'parent_sources': {name: sha(S / name) for name in FILES}, 'full_parent_runtime_sources': local,
        'parent_quality_acceptance_sha256': sha(PREVIOUS / 'acceptance.json'),
        'parent_closeout_audit_sha256': sha(PREVIOUS / 'closeout-independent-audit.json'),
        'original_test_sha256': sha(S / TEST), 'probe_fixture_sha256': fixture, 'limits': limits,
        'previous_change_closed': True, 'existing_business_data_unchanged': True})
    print(json.dumps({'prepared': True, 'source_count': 184, 'real_models': 0, 'business_writes': 0}))


if __name__ == '__main__':
    main()
