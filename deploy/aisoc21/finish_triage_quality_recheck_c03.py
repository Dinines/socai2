"""Close C03-02B without replay, model calls, restarts or business cleanup.

Host21, one exclusive phase at a time:
  inspect {passed|stopped} -> independent finish audit
  revoke  {passed|stopped} -> independent post-revocation closeout audit
  seal    {passed|stopped}

Only revoke changes external state: one transaction deactivates the three
hash-bound operation keys, followed by three real API denial observations.
Failed/unknown products, reservations, topics and offsets are retained. A
stopped closeout never claims model quality passed. No grading rubric or
provider response body is read or copied by this operator.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
from uuid import NAMESPACE_URL, UUID, uuid5

import run_triage_quality_recheck_c03 as runner
from run_triage_quality_recheck_c03 import prepare, CASES, PHASES, OUTPUTS
from prepare_triage_quality_recheck_c03 import E, P, S, AUDIT_GATES, IMAGE, INPUT, INSIDE, PLAN, read, save, sha
from prepare_identity_read_3a import lit
from shared_1b import SharedBatch

MODES = ('passed', 'stopped')
LOCK = 'services/agents/app/llm/prompts.lock.json'

# Every consumer below starts without a subscription or assignment. Only
# metadata/OffsetFetch requests are permitted: no fetch/getone/poll/commit.
METADATA_CODE = '''import asyncio,json,os,sys
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
cfg=json.load(sys.stdin)
async def main():
 security=kafka_client_kwargs();assert security['security_protocol']=='SSL'
 if cfg['kind']=='raw':
  from app.core.config import settings
  selected={'raw':(settings.kafka_topic_alerts_raw,settings.kafka_consumer_group)}
 else:
  selected={'quality':(cfg['broker']['quality_topic'],cfg['broker']['group']),
   'dlq':(cfg['broker']['dlq_topic'],None),
   'main':(os.getenv('KAFKA_TOPIC_ALERTS_FUSED','aisoc.alerts.fused'),os.getenv('KAFKA_CONSUMER_GROUP','aisoc-agents-triage'))}
 out={}
 for alias,(topic,group) in selected.items():
  c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=group,enable_auto_commit=False,**security)
  await c.start()
  try:
   await c._client.add_topic(topic);parts=c.partitions_for_topic(topic);assert parts
   tps=[TopicPartition(topic,p) for p in sorted(parts)]
   begins,ends=await c.beginning_offsets(tps),await c.end_offsets(tps)
   out[alias]={'topic':topic,'group':group,'partitions':[{'partition':tp.partition,'begin':begins[tp],
    'end':ends[tp],'committed':await c.committed(tp) if group else None} for tp in tps],
    'physical_record_reads':0,'polls':0,'assigns':0,'commits':0}
  finally:await c.stop()
 print(json.dumps(out))
asyncio.run(main())'''

FUSION_METRICS_CODE = '''import json,urllib.request
from app.core.config import settings
with urllib.request.urlopen('http://127.0.0.1:'+str(settings.http_port)+'/metrics',timeout=10) as response:
 value=json.load(response)
 assert response.status==200 and value['status']=='ok'
 print(json.dumps(value))'''

PROMPT_CODE = '''import hashlib,json
from pathlib import Path
from app.llm.prompt_registry import default_registry,load_lock
r=default_registry();assert not r.verify_against_lock(load_lock());p=r.get('triage.system')
print(json.dumps({'version':p.version,'sha256':p.sha256,
 'lock_sha256':hashlib.sha256(Path('/app/app/llm/prompts.lock.json').read_bytes()).hexdigest()}))'''


def contract(mode):
    assert mode in MODES and os.geteuid() == 0
    state = read(P / 'state.json')
    assert state['execution_authorized'] is True and state['batch'] == E.name
    provisioned = read(P / 'state-provisioned.json')
    assert provisioned['execution_authorized'] is False
    provisioned['execution_authorized'] = True
    assert state == provisioned
    assert state['image_id'] == IMAGE and state['inputs_sha256'] == prepare.INPUT_SHA
    assert sha(INPUT) == sha(P / 'inputs.json') == state['inputs_sha256']
    assert sha(PLAN) == sha(E / 'scope-before.md') == state['plan_sha256']
    assert sha(INSIDE) == state['operator_sha256']
    assert sha(S / LOCK) == state['prompt_lock_sha256']
    sources = {str(p.relative_to(S)): sha(p) for p in sorted((S / 'services/agents/app').rglob('*.py'))}
    assert len(sources) == 184 and sources == state['source_sha256']
    review = read(E / 'pre-execution-independent-audit.json')
    assert review['accepted'] is True and review['image_id'] == IMAGE
    assert review['inside_operator_sha256'] == state['operator_sha256']
    assert review['host_runner_sha256'] == sha(Path(runner.__file__))
    authorized = read(E / 'execution-authorized.json')
    assert authorized['audit_sha256'] == sha(E / 'pre-execution-independent-audit.json')
    assert authorized['inside_operator_sha256'] == state['operator_sha256']
    assert set(state['identities']) == {'a', 'b', 'denied'}
    assert len({UUID(v['key_id']) for v in state['identities'].values()}) == 3
    for alias, item in state['identities'].items():
        namespace = uuid5(NAMESPACE_URL, 'socai2/' + E.name)
        assert str(uuid5(namespace, 'key/' + alias)) == item['key_id']
    return state


def preserved_files():
    """Hash immutable original checkpoints, including every failure found."""
    paths = set()
    for directory in (E / 'cases', E / 'host-phases', E / 'launch-recovery-case01'):
        paths.update(p for p in directory.rglob('*') if p.is_file())
    paths.update(p for p in E.rglob('*failure*.json') if p.is_file() and not p.name.startswith('finish-'))
    if (E / 'safety-stop.json').is_file():
        paths.add(E / 'safety-stop.json')
    return {'evidence': {str(p.relative_to(E)): sha(p) for p in sorted(paths)},
            'quality_gates': {p.name: sha(p) for p in sorted(AUDIT_GATES.glob('*.json'))},
            'scope_addenda': {p.name: sha(p) for p in sorted(E.glob('*addendum*')) if p.is_file()}}


def cases(mode, state):
    result = {}
    for case in CASES:
        phases = {}
        for phase in PHASES:
            host = E / 'host-phases' / case / phase / 'accepted.json'
            product = E / 'cases' / case / phase / OUTPUTS[phase]
            phases[phase] = {'host_accepted': host.is_file(), 'inside_output_present': product.is_file()}
            if host.is_file():
                value = read(host)
                assert value['phase_completed'] is True and value['phase'] == phase and value['case'] == case
                assert value['image_id'] == IMAGE and value['output_sha256'] == sha(product)
                assert value['inside_operator_sha256'] == state['operator_sha256']
                assert value['host_runner_sha256'] == sha(Path(runner.__file__))
                phases[phase].update(host_sha256=sha(host), output_sha256=sha(product))
            if mode == 'passed':
                assert host.is_file() and product.is_file()
        gate_path = AUDIT_GATES / (case + '.json')
        gate_passed = False
        if gate_path.is_file():
            gate = read(gate_path)
            assert gate['case'] == case and gate['input_sha256'] == state['inputs_sha256']
            completion = E / 'cases' / case / 'verify/case-completed.json'
            assert completion.is_file() and gate['completion_sha256'] == sha(completion)
            gate_passed = gate.get('accepted') is True and read(completion).get('gate_eligible') is True
        if mode == 'passed':
            assert gate_passed
            completion = read(E / 'cases' / case / 'verify/case-completed.json')
            assert completion['infrastructure_passed'] is completion['raw_schema_valid'] is completion['actual_usage_confirmed'] is True
        failures = sorted(str(p.relative_to(E)) for directory in
            (E / 'cases' / case, E / 'host-phases' / case) for p in directory.rglob('*failure*.json'))
        if mode == 'passed':
            assert not failures
        result[case] = {'phases': phases, 'independent_quality_gate_passed': gate_passed,
                        'gate_sha256': sha(gate_path) if gate_path.is_file() else None,
                        'failure_artifacts': failures}
    if mode == 'passed':
        assert not (E / 'safety-stop.json').exists()
    else:
        assert (E / 'safety-stop.json').is_file(), 'Controlled stopped mode requires the existing stop checkpoint'
    return result


def rows_by_partition(value):
    return {row['partition']: row for row in value['partitions']}


def runtime(state):
    flags = prepare.base.container_json(prepare.base.FLAGS_CODE,
        payload=[state['identities'][alias]['tenant_id'] for alias in ('a', 'b')])
    assert flags['uid'] == 10001 and flags['reader_maps_resolve']
    assert flags['source'] == state['source_sha256']
    assert all(flags[k] is False for k in ('worker', 'escalation', 'memory_writeback', 'approvals', 'alert_graph'))
    prompt = prepare.base.container_json(PROMPT_CODE)
    assert prompt == read(E / 'prompt-before.json') and prompt['version'] == '3'
    offsets = prepare.base.container_json(prepare.base.OFFSET_CODE)
    assert offsets == read(E / 'old-budget-offsets-before.json')
    for name in ('api', 'fusion', 'agents', 'actions'):
        resident = prepare.base.inspect('socai2-' + name + '-1')
        assert resident['State']['Health']['Status'] == 'healthy'
        if name == 'agents':
            assert resident['Image'] == IMAGE and resident['Config']['StopTimeout'] == 60
    metadata = prepare.base.container_json(METADATA_CODE, payload={'kind': 'agents', 'broker': state['broker']})
    metadata.update(prepare.base.container_json(METADATA_CODE, service='fusion', payload={'kind': 'raw'}))
    sequence = prepare.http_start(path='/metrics', host='127.0.0.1', port=8003)
    try:
        metrics = prepare.base.container_json(FUSION_METRICS_CODE, service='fusion')
    except BaseException as error:
        prepare.http_finish(sequence, error_type=type(error).__name__)
        raise
    else:
        prepare.http_finish(sequence, status=200, confirmed=True)
    return {'resident_flags': flags, 'prompt': prompt, 'old_six_budget_groups': offsets,
            'broker_metadata': metadata, 'fusion_metrics': metrics,
            'additional_broker_physical_reads': 0, 'additional_broker_commits': 0}


def delivery_proof(mode, current):
    """Join actual processing evidence without calling slots physical reads."""
    metadata = current['broker_metadata']
    baseline_raw = read(E / 'fusion-raw-metadata-before.json')
    baseline_main = read(E / 'main-fused-metadata-before.json')
    before_metrics = read(E / 'fusion-metrics-before.json')['metrics']
    after_metrics = current['fusion_metrics']['metrics']
    delta = {key: after_metrics[key] - value for key, value in before_metrics.items()}
    assert all(value >= 0 for value in delta.values())
    count = runner.counters()
    raw_attempts, quality_attempts = count['raw_ingress_sending_checkpoints'], count['quality_sending_checkpoints']
    assert 0 <= delta['processed'] <= raw_attempts
    result = {'raw_processing_metric_delta': delta, 'cases': {},
              'resident_raw_slots_reserved': raw_attempts,
              'raw_slots_are_not_direct_physical_delivery_observations': True,
              'raw_processing_proof_uses_ack_fused_PG_metrics_and_offset_together': True,
              'metadata_alone_does_not_prove_exact_physical_delivery_count': True}
    raw_after, raw_before = rows_by_partition(metadata['raw']), rows_by_partition(baseline_raw)
    main_after, main_before = rows_by_partition(metadata['main']), rows_by_partition(baseline_main)
    assert metadata['raw']['topic'] == baseline_raw['topic'] and metadata['raw']['group'] == baseline_raw['group']
    assert metadata['main']['topic'] == baseline_main['topic'] and metadata['main']['group'] == baseline_main['group']
    assert set(raw_after) == set(raw_before) and set(main_after) == set(main_before)
    for part, old in raw_before.items():
        now = raw_after[part]
        assert now['begin'] == old['begin'] and now['end'] >= old['end']
        assert type(now['committed']) is int and old['committed'] <= now['committed'] <= now['end']
    for part, old in main_before.items():
        now = main_after[part]
        assert now['begin'] == old['begin'] and now['committed'] == old['committed']
        assert now['end'] >= old['end']
    raw_delta = sum(raw_after[p]['end'] - old['end'] for p, old in raw_before.items())
    fused_delta = sum(main_after[p]['end'] - old['end'] for p, old in main_before.items())
    assert 0 <= raw_delta <= raw_attempts and 0 <= fused_delta <= raw_attempts
    confirmed, raw_coordinates, fused_coordinates = 0, set(), set()
    for case in CASES:
        directory = E / 'cases' / case / 'ingress'
        ack_path = directory / 'http-ack.json'
        if not ack_path.is_file():
            continue
        ack, row = read(ack_path), {'ack_sha256': sha(ack_path)}
        coordinate = ack['message']
        part, offset = coordinate['partition'], coordinate['offset']
        assert coordinate['topic'] == metadata['raw']['topic']
        assert raw_before[part]['end'] <= offset < raw_after[part]['end']
        raw_coordinates.add((part, offset))
        row.update(raw_ack=coordinate, raw_group_committed=raw_after[part]['committed'],
                   raw_group_advanced_past_input=raw_after[part]['committed'] >= offset + 1)
        files = [directory / name for name in ('accepted.json', 'fused-envelope.json', 'stored-alert.json', 'fused-coordinate.json')]
        if all(path.is_file() for path in files):
            accepted, fused, stored, fused_coordinate = (read(path) for path in files)
            assert ack['canonical_alert_id'] == accepted['canonical_alert_id'] == fused['alert_row_id'] == stored['id']
            assert ack['tenant_id'] == fused['tenant_id'] == stored['tenant_id']
            assert fused_coordinate['topic'] == metadata['main']['topic']
            fp, fo = fused_coordinate['partition'], fused_coordinate['offset']
            assert main_before[fp]['end'] <= fo < main_after[fp]['end']
            fused_coordinates.add((fp, fo))
            row.update(canonical_alert_id=fused['alert_row_id'], fusion_incident_id=fused['incident_id'],
                       original_fused_coordinate=fused_coordinate, stored_alert_sha256=sha(files[2]),
                       first_fused_sha256=sha(files[1]), first_material_and_fused_confirmed=True)
            if row['raw_group_advanced_past_input']:
                confirmed += 1
        else:
            row['first_material_and_fused_confirmed'] = False
        result['cases'][case] = row
    assert len(raw_coordinates) == len(result['cases'])
    assert delta['processed'] >= confirmed
    quality = metadata['quality']
    assert quality['topic'] == read(P / 'state.json')['broker']['quality_topic']
    assert len(quality['partitions']) == len(metadata['dlq']['partitions']) == 1
    q, dlq = quality['partitions'][0], metadata['dlq']['partitions'][0]
    assert q['partition'] == 0 and q['begin'] == 0 and 0 <= q['end'] <= quality_attempts
    assert type(q['committed']) is int and 0 <= q['committed'] <= q['end']
    assert dlq['begin'] == dlq['end'] == 0, 'Unexpected DLQ output needs separate read-only review'
    raw_contract_inferred = (
        raw_attempts == len(raw_coordinates) == confirmed == delta['processed'] ==
        delta['persisted'] == raw_delta == fused_delta == len(fused_coordinates)
        and all(delta[k] == 0 for k in ('errors', 'duplicates', 'dead_lettered', 'persist_failed', 'persist_unavailable'))
        and all(row['committed'] == row['end'] for row in raw_after.values()))
    if mode == 'passed':
        assert raw_attempts == quality_attempts == confirmed == 4 and raw_contract_inferred
        assert count['model_sending_checkpoints'] == count['synthetic_sdk_http_attempts'] == 4
        assert count['temporary_consumer_physical_records'] == 8
        assert q['end'] == q['committed'] == 4
    result.update(raw_acknowledged_inputs=len(raw_coordinates), confirmed_raw_processing_chains=confirmed,
        raw_topic_end_delta=raw_delta, original_fused_topic_end_delta=fused_delta,
        original_main_group_commits_preserved=True, quality_position=q, dlq_position=dlq,
        temporary_consumer_direct_physical_records=count['temporary_consumer_physical_records'],
        used_or_reserved_delivery_slots=count['delivery_slots_used_or_reserved'],
        raw_deliveries_inferred_from_processing_contract=confirmed if raw_contract_inferred else None,
        total_deliveries_inferred_from_contract=(confirmed + count['temporary_consumer_physical_records']) if raw_contract_inferred else None,
        inference_requires_unchanged_container_restart_count_and_runtime=True,
        raw_deliveries_directly_instrumented_at_consumer_yield=False)
    return result


def new_run_projection(state):
    allowed = runner.budget_scope(state)
    if not allowed:
        return []
    ids = ','.join(lit(value) + '::uuid' for value in allowed)
    sql = '''SELECT COALESCE(json_agg(t),'[]'::json) FROM
 (SELECT r.id,r.tenant_id,r.case_id,r.status,r.model_used,r.total_tokens,
   (SELECT json_agg(e.seq ORDER BY e.seq) FROM investigation_events e WHERE e.run_id=r.id AND e.tenant_id=r.tenant_id) AS event_sequences,
   (SELECT count(*) FROM investigation_artifacts a WHERE a.run_id=r.id AND a.tenant_id=r.tenant_id) AS artifact_count
  FROM investigation_runs r WHERE r.id IN (''' + ids + ') ORDER BY r.id) t;'
    values = json.loads(prepare.base.pg(sql).stdout)
    namespace = uuid5(NAMESPACE_URL, 'tryaisoc.com/agents/auto-triage')
    alerts = {}
    for case in CASES:
        path = E / 'cases' / case / 'ingress/accepted.json'
        if path.is_file():
            alert = str(UUID(read(path)['canonical_alert_id']))
            alerts[str(uuid5(namespace, alert + ':auto-triage-v1'))] = alert
    for row in values:
        assert allowed[row['id']] == row['tenant_id'] and alerts[row['id']] == row['case_id']
    return values


def key_metadata(state):
    ids = ','.join(lit(value['key_id']) + '::uuid' for value in state['identities'].values())
    sql = "SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT id,tenant_id,user_id,name,is_active,scopes,expires_at FROM api_keys WHERE id IN (" + ids + ') ORDER BY id) t;'
    values = json.loads(prepare.base.pg(sql).stdout)
    assert len(values) == 3
    expected = {item['key_id']: (alias, item) for alias, item in state['identities'].items()}
    for row in values:
        alias, item = expected[row['id']]
        assert row['tenant_id'] == item['tenant_id'] and row['user_id'] == item['user_id']
        assert row['name'] == E.name + '-' + alias and row['scopes'] == item['scopes']
        assert datetime.fromisoformat(row['expires_at']) == datetime.fromisoformat(item['expires_at'])
    return values


def inspect_phase(mode):
    state = contract(mode)
    assert not (E / 'finish-started.json').exists()
    case_status = cases(mode, state)
    save(E / 'finish-started.json', {'mode': mode, 'finish_operator_sha256': sha(Path(__file__)),
        'model_or_ingress_or_broker_mutations': 0, 'automatic_retry': False})
    protected = runner.protected_output(label='finish-inspect')
    if mode == 'passed':
        required = {'alerts': 4, 'investigation_runs': 4, 'investigation_events': 12,
                    'investigation_artifacts': 28, 'aisoc_run_costs': 4}
        assert all(protected['material_deltas'][name] == count for name, count in required.items())
        assert protected['new_budget_rows'] == 4 and protected['new_reserved_units'] == 80000
    live = runtime(state)
    keys = key_metadata(state)
    assert all(row['is_active'] is True for row in keys)
    proof = delivery_proof(mode, live)
    products = new_run_projection(state)
    snapshot = {'batch': E.name, 'mode': mode, 'image_id': IMAGE,
        'finish_operator_sha256': sha(Path(__file__)), 'host_runner_sha256': sha(Path(runner.__file__)),
        'inside_operator_sha256': state['operator_sha256'], 'inputs_sha256': state['inputs_sha256'],
        'plan_sha256': state['plan_sha256'], 'private_state_sha256': sha(P / 'state.json'),
        'protected': protected, 'runtime': live, 'delivery_proof': proof, 'new_run_projection': products,
        'cases': case_status, 'operation_key_metadata': keys, 'counters': runner.counters(),
        'preserved_files': preserved_files(), 'model_quality_accepted': False,
        'quality_success_requires_four_gates_and_both_finish_audits': True}
    save(E / 'finish-before.json', snapshot)
    return {'phase': 'inspect', 'mode': mode, 'finish_before_sha256': sha(E / 'finish-before.json'),
            'ready_for_independent_finish_audit': True, 'operation_keys_deactivated': 0}


def finish_audit(mode, state):
    before = read(E / 'finish-before.json')
    audit = read(E / 'finish-independent-audit.json')
    assert before['mode'] == mode and before['finish_operator_sha256'] == sha(Path(__file__))
    assert before['private_state_sha256'] == sha(P / 'state.json')
    assert audit['accepted'] is True and audit['mode'] == mode and audit['image_id'] == IMAGE
    assert audit['finish_before_sha256'] == sha(E / 'finish-before.json')
    assert audit['finish_operator_sha256'] == sha(Path(__file__))
    assert audit['inside_operator_sha256'] == state['operator_sha256']
    assert audit['host_runner_sha256'] == sha(Path(runner.__file__))
    assert audit['inputs_sha256'] == state['inputs_sha256']
    assert preserved_files() == before['preserved_files']
    assert cases(mode, state) == before['cases']
    return before


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def denial_observation(alias, item):
    path = '/api/v1/alerts'
    sequence = prepare.http_start(path=path, host='127.0.0.1', port=18000)
    status, error_type = None, None
    try:
        request = urllib.request.Request('http://127.0.0.1:18000' + path,
            headers={'Authorization': 'Bearer ' + item['key']})
        with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
            status = response.status  # Deliberately do not retain any body.
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
    except Exception as error:
        error_type = type(error).__name__
    prepare.http_finish(sequence, status=status, error_type=error_type, confirmed=status is not None)
    return {'identity': alias, 'key_id': item['key_id'], 'path': path, 'status': status,
            'error_type': error_type, 'http_sequence': sequence, 'response_body_saved': False}


def revoke_phase(mode):
    state = contract(mode)
    before = finish_audit(mode, state)
    assert not (E / 'finish-revoke-started.json').exists()
    runner.protected_output(label='finish-before-revoke', previous=before['protected']['observation'],
                            previous_qa=before['protected']['closure_qa'])
    assert new_run_projection(state) == before['new_run_projection']
    assert key_metadata(state) == before['operation_key_metadata']
    # Reserve three denials plus gateway/Fusion reads for revoke and seal:
    # seven shared HTTP slots remain after this point.
    assert runner.counters()['operator_HTTP_sends_used_or_reserved_toward_cap'] <= 233
    save(E / 'finish-revoke-started.json', {'mode': mode,
        'finish_audit_sha256': sha(E / 'finish-independent-audit.json'),
        'only_external_write': 'deactivate_exactly_three_current_batch_operation_keys',
        'automatic_retry_or_refund_or_replay': False})
    clauses = []
    for alias, item in state['identities'].items():
        clauses.append('(id=' + lit(item['key_id']) + '::uuid AND tenant_id=' + lit(item['tenant_id']) +
            '::uuid AND user_id=' + lit(item['user_id']) + '::uuid AND name=' + lit(E.name + '-' + alias) + ')')
    sql = '''SET ROLE aisoc; BEGIN; DO $c03_quality_revoke$
DECLARE affected integer;
BEGIN
 UPDATE api_keys SET is_active=false WHERE is_active=true AND (''' + ' OR '.join(clauses) + ''');
 GET DIAGNOSTICS affected = ROW_COUNT;
 IF affected <> 3 THEN RAISE EXCEPTION 'C03 operation-key count mismatch'; END IF;
END; $c03_quality_revoke$; COMMIT;'''
    runner.sethostrun('finish-revoke-exact-keys')
    prepare.write_pg(SharedBatch(prepare.R), sql)
    keys = key_metadata(state)
    assert all(row['is_active'] is False for row in keys)
    checks = [denial_observation(alias, item) for alias, item in state['identities'].items()]
    save(E / 'key-lifecycle.json', {'mode': mode, 'operation_keys_deactivated': 3,
        'keys': keys, 'real_api_checks': checks, 'reader_keys_rotated': 0,
        'automatic_HTTP_retry': False, 'only_this_batch_keys': True})
    protected = runner.protected_output(label='finish-after-revoke', previous=before['protected']['observation'],
        previous_qa=before['protected']['closure_qa'])
    live = runtime(state)
    assert live == before['runtime']
    assert preserved_files() == before['preserved_files']
    assert new_run_projection(state) == before['new_run_projection']
    save(E / 'finish-after.json', {'batch': E.name, 'mode': mode, 'image_id': IMAGE,
        'finish_operator_sha256': sha(Path(__file__)), 'finish_before_sha256': sha(E / 'finish-before.json'),
        'finish_audit_sha256': sha(E / 'finish-independent-audit.json'),
        'key_lifecycle_sha256': sha(E / 'key-lifecycle.json'), 'protected': protected,
        'runtime': live, 'counters': runner.counters(), 'preserved_files': preserved_files(),
        'new_run_projection': before['new_run_projection'], 'delivery_proof': delivery_proof(mode, live),
        'all_three_real_API_denials_confirmed': all(row['status'] == 401 for row in checks),
        'new_model_or_broker_or_business_mutations': 0, 'ready_for_closeout_independent_audit': True})
    assert all(row['status'] == 401 for row in checks), 'Inspect saved results; no automatic auth retry'
    return {'phase': 'revoke', 'mode': mode, 'operation_keys_deactivated': 3,
            'API_denials_confirmed': 3, 'ready_for_independent_closeout_audit': True}


def seal_phase(mode):
    state = contract(mode)
    before = finish_audit(mode, state)
    after = read(E / 'finish-after.json')
    audit = read(E / 'closeout-independent-audit.json')
    assert after['mode'] == mode and after['all_three_real_API_denials_confirmed'] is True
    assert audit['accepted'] is True and audit['mode'] == mode and audit['image_id'] == IMAGE
    assert audit['finish_after_sha256'] == sha(E / 'finish-after.json')
    assert audit['key_lifecycle_sha256'] == sha(E / 'key-lifecycle.json')
    assert audit['finish_operator_sha256'] == sha(Path(__file__))
    assert audit['inputs_sha256'] == state['inputs_sha256']
    assert not (E / 'acceptance.json').exists()
    protected = runner.protected_output(label='finish-seal', previous=after['protected']['observation'],
        previous_qa=after['protected']['closure_qa'])
    live = runtime(state)
    assert live == after['runtime']
    assert key_metadata(state) == read(E / 'key-lifecycle.json')['keys']
    assert new_run_projection(state) == before['new_run_projection']
    assert preserved_files() == before['preserved_files']
    counts = runner.counters()
    budget = protected['observation']['budget']
    old_runs = {row['run_id'] for row in read(E / 'before.json')['budget']}
    fresh = [row for row in budget if row['run_id'] not in old_runs]
    unknown = [row['run_id'] for row in fresh if row['settled_at'] is None]
    result = {'batch': E.name, 'change': 'C03-02B', 'finished_at': datetime.now(timezone.utc).isoformat(),
        'bounded_closeout_accepted': True, 'quality_outcome': 'four_case_bounded_pass' if mode == 'passed' else 'stopped_no_quality_pass',
        'four_case_model_quality_accepted': mode == 'passed', 'full_model_quality_or_worker_admission_accepted': False,
        'full_migration_complete': False, 'resident_worker_enabled': False,
        'image_id': IMAGE, 'source_count': 184, 'source_map_sha256': hashlib.sha256(json.dumps(state['source_sha256'], sort_keys=True).encode()).hexdigest(),
        'prompt_lock_sha256': state['prompt_lock_sha256'], 'inputs_sha256': state['inputs_sha256'],
        'plan_sha256': state['plan_sha256'], 'scope_addendum_sha256': before['preserved_files']['scope_addenda'],
        'inside_operator_sha256': state['operator_sha256'], 'host_runner_sha256': sha(Path(runner.__file__)),
        'finish_operator_sha256': sha(Path(__file__)), 'compose_layers': 25, 'source_layers': 22,
        'case_gate_sha256': {case: value['gate_sha256'] for case, value in before['cases'].items()},
        'case_quality_gates_passed': sum(value['independent_quality_gate_passed'] for value in before['cases'].values()),
        'material_deltas': protected['material_deltas'], 'old_material_tables_preserved': 14,
        'old_budget_rows_preserved': 6, 'old_unknown_reservations_preserved': 3,
        'new_budget_rows': len(fresh), 'new_reserved_units': sum(row['charged_tokens'] for row in fresh),
        'reserved_units_are_not_usage': True, 'new_unknown_reservations': unknown,
        'known_observed_tokens': sum(row['observed_tokens'] for row in fresh if row['observed_tokens'] is not None),
        'usage_missing_reservations': sum(row['observed_tokens'] is None for row in fresh),
        'original_failures_and_unknown_products_preserved': True, 'counter_summary': counts,
        'raw_delivery_confirmation': before['delivery_proof'],
        'gateway_success_delta': protected['gateway_success_delta'], 'new_operation_keys_deactivated': 3,
        'real_operation_key_API401_checks': 3, 'reader_keys_preserved': 10, 'new_reader_keys': 0,
        'old_six_budget_group_offsets_preserved': True, 'main_fused_group_commits_preserved': True,
        'finish_model_calls': 0, 'finish_ingress_or_broker_publishes_or_commits': 0,
        'finish_business_row_mutations': 0, 'services_restarted': 0, 'DDL_changes': 0,
        'containers_preserved': 36, 'volumes_preserved': 18, 'upstream_migrations_preserved': 134,
        'new_pending_QA_samples': protected['closure_qa']['new_pending_samples'],
        'QA_canonical_Alert_association_or_quality_validated': False,
        'explicit_host_SQL_helper_calls': len(list((E / 'host-sql-attempts').glob('*.json'))),
        'all_internal_service_SQL_counted': False,
        'finish_independent_audit_sha256': sha(E / 'finish-independent-audit.json'),
        'closeout_independent_audit_sha256': sha(E / 'closeout-independent-audit.json'),
        'postconditions_body_and_provider_body_copied_to_public_acceptance': False,
        'next': 'C03-03 separately scoped resident admission' if mode == 'passed' else 'Record quality failure/unknown and scope the next correction; no automatic retry'}
    save(E / 'acceptance.json', result)
    return {'phase': 'seal', 'bounded_closeout_accepted': True,
            'four_case_model_quality_accepted': mode == 'passed', 'resident_worker_enabled': False,
            'acceptance_sha256': sha(E / 'acceptance.json')}


def main(phase, mode):
    assert phase in {'inspect', 'revoke', 'seal'} and mode in MODES
    os.umask(0o077)
    with runner.serial():
        runner.sethostrun('finish-' + phase)
        directory = E / 'finish-phases' / phase
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        save(directory / 'started.json', {'phase': phase, 'mode': mode,
            'finish_operator_sha256': sha(Path(__file__)), 'automatic_retry': False})
        try:
            result = {'inspect': inspect_phase, 'revoke': revoke_phase, 'seal': seal_phase}[phase](mode)
            save(directory / 'completed.json', result)
            print(json.dumps(result))
        except BaseException as error:
            save(directory / 'failure.json', {'error_type': type(error).__name__, 'phase': phase,
                'mode': mode, 'automatic_retry': False, 'original_evidence_and_unknowns_retained': True})
            raise


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('Expected one phase and one mode')
        main(*sys.argv[1:])
    except BaseException as error:
        print(json.dumps({'finish_failed': True, 'error_type': type(error).__name__,
                          'message_or_locals_recorded': False, 'automatic_retry': False}))
        raise SystemExit(1) from None
