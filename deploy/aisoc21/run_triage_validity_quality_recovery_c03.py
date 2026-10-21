"""Run exactly one C03-02D-02 phase/case in the unchanged, fixed Agents image.

Host21 only. No import-time I/O, automatic loop, replay, cleanup of business
data, or service recreation. A failed/unknown phase remains reserved. The
first verify phase may read back a stopped case; repeating verify requires a
separately reviewed recovery operator, never replacing its canonical output.
"""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from uuid import NAMESPACE_URL, UUID, uuid5

import prepare_triage_validity_quality_c03 as prepare
import recover_triage_validity_quality_c03 as recovery
from prepare_triage_validity_quality_c03 import (
    R, S, E, P, AUDIT_GATES, IMAGE, INSIDE, POLICY, INPUT, PLAN, sha, read, save,
)

INSIDE = recovery.INSIDE
RECOVERY_STATE = recovery.NEW_STATE
RECOVERY_E = recovery.D

CASES = ('case01', 'case02', 'case03', 'case04')
PHASES = ('ingress', 'preflight', 'invoke', 'verify')
TIMEOUT_SECONDS = 240
LOCK = 'services/agents/app/llm/prompts.lock.json'
OUTPUTS = {'ingress': 'accepted.json', 'preflight': 'accepted.json',
           'invoke': 'completed.json', 'verify': 'case-completed.json'}
ADDITIONS = {'alerts': 4, 'investigation_runs': 4, 'investigation_events': 12,
             'investigation_artifacts': 28, 'aisoc_run_costs': 4,
             'aisoc_shadow_decisions': 4}
EXTRA_TABLES = ('public.incidents', 'public.aisoc_cases', 'public.alert_source_links')


def sethostrun(phase):
    """Label every explicit host SQL helper call, including finish reuse."""
    prepare.PHASE = phase


def extra_tables():
    tables = {}
    for name in EXTRA_TABLES:
        exists = prepare.base.pg("SELECT to_regclass('" + name + "') IS NOT NULL;").stdout.strip() == 't'
        hashes = []
        if exists:
            output = prepare.base.pg("SELECT COALESCE(json_agg(x),'[]'::json) FROM "
                "(SELECT row_to_json(t)::text AS material FROM " + name +
                " t ORDER BY row_to_json(t)::text) x;").stdout
            hashes = [hashlib.sha256(row['material'].encode()).hexdigest() for row in json.loads(output)]
        tables[name] = {'exists': exists, 'row_sha256': sorted(hashes)}
    return {'tables': tables}


def budget_scope(state):
    """Derive only already-ingressed, frozen live workflow identities."""
    namespace = uuid5(NAMESPACE_URL, 'tryaisoc.com/agents/auto-triage')
    allowed = {}
    for case, item in read(INPUT)['cases'].items():
        accepted = E / 'cases' / case / 'ingress/accepted.json'
        if accepted.is_file():
            alert = str(UUID(read(accepted)['canonical_alert_id']))
            run = str(uuid5(namespace, alert + ':auto-triage-v1'))
            allowed[run] = state['identities'][item['tenant']]['tenant_id']
    return allowed


def observed_state(label):
    """The prepare module instruments its exact metrics subprocess once."""
    sethostrun(label)
    return prepare.base.observation()


def closure_qa(state):
    """Bound the inherited auxiliary sampler without certifying its Alert FK."""
    baseline = read(E / 'before-closure-qa.json')['tables']
    snapshots, fresh = {}, []
    for table in ('aisoc_closure_policies', 'aisoc_closure_qa_samples'):
        data = json.loads(prepare.base.pg("SELECT COALESCE(json_agg(x),'[]'::json) FROM "
            "(SELECT row_to_json(t)::text AS material FROM public." + table +
            " t ORDER BY row_to_json(t)::text) x;").stdout)
        prior = Counter(baseline[table]['row_sha256'])
        hashes = [hashlib.sha256(row['material'].encode()).hexdigest() for row in data]
        assert baseline[table]['exists'] is True and not prior - Counter(hashes)
        snapshots[table] = {'exists': True, 'row_sha256': sorted(hashes)}
        for item, digest in zip(data, hashes):
            if prior[digest]:
                prior[digest] -= 1
            else:
                assert table == 'aisoc_closure_qa_samples', 'Closure policy changed'
                fresh.append(json.loads(item['material']))
    assert len(fresh) <= 4
    lineage = []
    for case in CASES:
        path = E / 'cases' / case / 'ingress/fused-envelope.json'
        if path.is_file():
            envelope = read(path)
            canonical = str(UUID(envelope['alert_row_id']))
            run = str(uuid5(uuid5(NAMESPACE_URL, 'tryaisoc.com/agents/auto-triage'), canonical + ':auto-triage-v1'))
            lineage.append({'case': case, 'tenant_id': envelope['tenant_id'],
                'fusion_incident_id': envelope['incident_id'], 'canonical_alert_id': canonical, 'run_id': run})
    relations = []
    for sample in fresh:
        assert sample['tenant_id'] in {state['identities'][who]['tenant_id'] for who in ('a', 'b')}
        assert sample['status'] == 'pending'
        assert all(value is None for key, value in sample.items()
                   if key.startswith('score_') or key in {'reviewer', 'reviewed_at', 'reviewer_disposition', 'reviewer_note'})
        matches = [item for item in lineage if item['tenant_id'] == sample['tenant_id']
                   and sample['alert_id'] in {item['fusion_incident_id'], item['canonical_alert_id']}]
        assert len(matches) == 1, 'QA row is outside this batch lineage'
        item = matches[0]
        run = json.loads(prepare.base.pg("SELECT row_to_json(t) FROM (SELECT id,tenant_id,case_id FROM investigation_runs "
            "WHERE id='" + str(UUID(item['run_id'])) + "') t;").stdout.strip() or 'null')
        relations.append({**item, 'qa_record_id': sample['id'], 'qa_alert_id': sample['alert_id'],
            'qa_status': sample['status'], 'actual_run': run,
            'qa_alert_id_equals_fusion_incident': sample['alert_id'] == item['fusion_incident_id'],
            'qa_alert_id_equals_canonical_alert': sample['alert_id'] == item['canonical_alert_id'],
            'canonical_QA_association_validated': False,
            'identity_limit': 'Q2: upstream samples state.incident_id into alert_id without an Alert foreign key'})
    assert len({item['case'] for item in relations}) == len(relations)
    return {'tables': snapshots, 'new_pending_samples': len(fresh), 'relationships': relations,
            'old_QA_and_policy_hashes_preserved': True, 'reviewer_or_scores_written': False,
            'canonical_QA_association_validated': False}


def protected_output(*, label='host-protected-output', previous=None, previous_qa=None):
    """Read-only preservation/caps check, also usable by the final operator.

    Only the fourteen named material projections are covered. Optional extra
    table hashes extend that boundary; this never claims all PG tables were
    observed. Prior rows are multisets, so duplicate material cannot conceal
    the deletion or mutation of an old row.
    """
    sethostrun(label)
    state, before = read(RECOVERY_STATE), read(E / 'before.json')
    now = observed_state(label)
    assert now['environment'] == before['environment']
    assert len(now['environment']['containers']) == 36 and len(now['environment']['volumes']) == 18
    assert now['readers'] == before['readers'] and now['migrations'] == before['migrations'] == 134
    assert now['policy_sha256'] == state['policy_sha256'] == sha(POLICY)
    expected_private = dict(read(E / 'private-input-hashes-before.json'))
    expected_private['private/triage-budget-3a/policy.json'] = state['policy_sha256']
    assert prepare.base.private_hashes() == expected_private
    assert set(now['materials']) == set(before['materials']) and len(now['materials']) == 14
    deltas = {}
    for table, old in before['materials'].items():
        current = now['materials'][table]
        assert not Counter(old) - Counter(current), 'Old material changed: ' + table
        added = len(current) - len(old)
        assert 0 <= added <= ADDITIONS.get(table, 0), 'Material cap: ' + table
        deltas[table] = added
    old_budget = {row['run_id']: row for row in before['budget']}
    current_budget = {row['run_id']: row for row in now['budget']}
    assert len(old_budget) == 10 and all(current_budget.get(key) == row for key, row in old_budget.items())
    fresh = [row for key, row in current_budget.items() if key not in old_budget]
    allowed = budget_scope(state)
    assert len(fresh) <= 4 and sum(row['charged_tokens'] for row in fresh) <= 80000
    assert all(row['charged_tokens'] == 20000 and allowed.get(row['run_id']) == row['tenant_id'] for row in fresh)
    tenants = Counter(row['tenant_id'] for row in fresh)
    assert tenants[state['identities']['a']['tenant_id']] <= 3
    assert tenants[state['identities']['b']['tenant_id']] <= 1
    gateway_delta = {}
    for model in set(before['gateway']) | set(now['gateway']):
        difference = now['gateway'].get(model, 0) - before['gateway'].get(model, 0)
        assert 0 <= difference <= (4 if model == 'aisoc-triage' else 0), 'Gateway role/cap'
        gateway_delta[model] = difference
    assert gateway_delta.get('aisoc-triage', 0) <= len(list((E / 'cases').glob('*/invoke/sdk-send-started.json')))
    extra = None
    if (E / 'before-extra-tables.json').is_file():
        extra = extra_tables()
        frozen_tables = read(E / 'before-extra-tables.json')['tables']
        for name, current in extra['tables'].items():
            frozen = frozen_tables.get(name, frozen_tables.get(name.removeprefix('public.')))
            assert frozen is not None and current['exists'] == frozen['exists']
            assert Counter(current['row_sha256']) == Counter(frozen['row_sha256']), 'Extra table material changed'
    if previous is not None:
        # preflight and verify are observational phases: no new ledger,
        # reservation settlement, gateway request or material mutation.
        assert now == previous, 'Read-only phase changed an observed product'
    qa = closure_qa(state)
    if previous_qa is not None:
        assert qa['tables'] == previous_qa['tables'], 'Read-only phase changed closure QA/policy'
    return {'observation': now, 'material_deltas': deltas,
            'old_material_multisets_preserved': True, 'old_budget_rows_preserved': 10,
            'old_unknown_reservations_preserved': 3, 'new_budget_rows': len(fresh),
            'new_reserved_units': sum(row['charged_tokens'] for row in fresh),
            'reserved_units_are_not_usage': True, 'gateway_success_delta': gateway_delta,
            'private_input_hashes_preserved_except_authorized_policy': True,
            'extra_table_hashes': extra, 'closure_qa': qa, 'all_PG_tables_observed': False}


def binding(*, allow_new_stop=False):
    state = recovery.business_binding(allow_new_stop=allow_new_stop)
    assert state['execution_authorized'] is True and state['image_id'] == IMAGE
    assert state['batch'] == E.name == read(INPUT)['batch']
    assert sha(INPUT) == sha(P / 'inputs.json') == state['inputs_sha256'] == prepare.INPUT_SHA
    assert sha(PLAN) == sha(E / 'scope-before.md') == state['plan_sha256']
    assert sha(INSIDE) == state['operator_sha256']
    assert sha(S / LOCK) == state['prompt_lock_sha256'] == read(E / 'prompt-before.json')['lock_sha256']
    sources = {str(path.relative_to(S)): sha(path) for path in sorted((S / 'services/agents/app').rglob('*.py'))}
    assert len(sources) == 184 and sources == state['source_sha256'] == read(E / 'resident-before.json')['source']
    assert read(E / 'topics-ready.json')['initial_commit'] == 0
    return state


def gates(phase, case):
    state = binding()
    if phase != 'verify':
        for previous in CASES[:CASES.index(case)]:
            completion = E / 'cases' / previous / 'verify/case-completed.json'
            gate = read(AUDIT_GATES / (previous + '.json'))
            assert gate['accepted'] is True and gate['case'] == previous
            assert gate['input_sha256'] == state['inputs_sha256']
            assert gate['completion_sha256'] == sha(completion) and read(completion)['gate_eligible'] is True
            gate_info = (AUDIT_GATES / (previous + '.json')).stat()
            assert gate_info.st_uid == 10001 and gate_info.st_mode & 0o777 == 0o600
    if phase != 'ingress':
        assert (E / 'cases' / case / 'ingress/accepted.json').is_file()
    if phase == 'invoke':
        assert read(E / 'cases' / case / 'preflight/accepted.json')['synthetic_only'] is True
    if phase == 'verify':
        assert (E / 'cases' / case / 'invoke/started.json').is_file()
    for path in (INSIDE, RECOVERY_STATE, P / 'inputs.json', P / 'probe.env'):
        assert stat.S_ISREG(path.lstat().st_mode), 'Regular files only'
    assert INSIDE.stat().st_mode & 0o777 == 0o644
    assert not AUDIT_GATES.is_symlink()
    for path in (RECOVERY_STATE, P / 'inputs.json'):
        info = path.stat()
        assert info.st_uid == 10001 and info.st_mode & 0o777 == 0o600
    for path in (E, AUDIT_GATES):
        info = path.stat()
        assert info.st_uid == 10001 and info.st_mode & 0o777 == 0o700
    return state


def command(phase, case, state, name, *, contract_only=False):
    resident = prepare.base.inspect('socai2-agents-1')
    frozen = read(P / 'agents-before.json')
    assert resident['Id'] == frozen['Id'] and resident['Image'] == IMAGE
    assert resident['State']['Health']['Status'] == 'healthy'
    networks = resident['NetworkSettings']['Networks']
    assert len(networks) == 1 and set(networks) == set(frozen['NetworkSettings']['Networks'])
    values = dict(line.split('=', 1) for line in (P / 'probe.env').read_text().splitlines())
    assert values == prepare.base.env(resident), 'Do not alter or forward host environment'
    mounts = resident['Mounts']
    assert len(mounts) == 7 and all(item['Type'] == 'bind' and not item['RW'] for item in mounts)
    argv = ['docker', 'run', '--rm', '--pull', 'never', '--name', name,
            '--network', next(iter(networks)), '--user', '10001:10001', '--read-only',
            '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges:true',
            '--tmpfs', '/tmp:rw,nosuid,nodev,size=128m', '--env-file', str(P / 'probe.env'),
            '-e', 'C03_PROBE_IMAGE_ID=' + IMAGE, '-e', 'PYTHONPATH=/app',
            '-e', 'PYTHONDONTWRITEBYTECODE=1',
            '-e', 'C03_RECOVERY_REVIEW_SHA256=' + sha(RECOVERY_E / 'independent-review.json'),
            '-e', 'C03_RECOVERY_RUNNER_SHA256=' + sha(Path(__file__)),
            '-e', 'C03_RECOVERY_AUTH_SHA256=' + (sha(RECOVERY_E / 'authorized.json') if not contract_only else 'contract-only')]
    if contract_only:
        argv += ['-e', 'C03_RECOVERY_CONTRACT_ONLY=1']
    pairs = [(item['Source'], item['Destination'], False) for item in mounts]
    pairs += [(str(INSIDE), '/operators/quality.py', False),
              (str(RECOVERY_STATE), '/private/state.json', False),
              (str(P / 'inputs.json'), '/private/inputs.json', False),
              (str(AUDIT_GATES), '/quality-gates', False), (str(E), '/evidence', True)]
    assert len({destination for _, destination, _ in pairs}) == len(pairs)
    for source, destination, writable in pairs:
        assert ',' not in source and ',' not in destination
        assert source != str(S) and not source.startswith(str(prepare.G))
        value = 'type=bind,src=' + source + ',dst=' + destination
        argv += ['--mount', value + ('' if writable else ',readonly')]
    return argv + ['-w', '/app', IMAGE, 'python', '/operators/quality.py', phase, case]


def counters():
    cases = E / 'cases'
    raw = len(list(cases.glob('*/ingress/http-sending.json')))
    fused = len(list(cases.glob('*/ingress/fused-coordinate.json')))
    quality = len(list(cases.glob('*/invoke/quality-sending.json')))
    models = len(list(cases.glob('*/invoke/sdk-send-started.json')))
    deliveries = len(list((E / 'record-deliveries').glob('*.json')))
    http = [read(path) for path in (E / 'http-events').glob('*-started.json')]
    actual = sum(not row['synthetic_model_transport'] for row in http)
    synthetic = len(http) - actual
    host_slots = sum(row.get('host_http_slot_reserved', row.get('host_metrics_slot_reserved', False)) for row in http)
    assert raw <= 4 and fused <= 4 and quality <= 4 and models <= 4
    assert raw + fused + quality <= 12 and raw + deliveries <= 12
    assert actual <= 240 and synthetic <= 4
    return {'raw_ingress_sending_checkpoints': raw, 'observed_original_fused_records': fused,
            'quality_sending_checkpoints': quality, 'model_sending_checkpoints': models,
            'temporary_consumer_physical_records': deliveries,
            'resident_raw_delivery_slots_reserved': raw, 'delivery_slots_used_or_reserved': raw + deliveries,
            'resident_raw_deliveries_not_directly_observed_here': True,
            'inside_actual_network_http_send_entries': actual - host_slots,
            'host_HTTP_sending_slots_reserved': host_slots,
            'operator_HTTP_sends_used_or_reserved_toward_cap': actual,
            'synthetic_sdk_http_attempts': synthetic}


def stop(case, phase, error_type):
    if not (E / 'recovery-stop.json').exists():
        save(E / 'recovery-stop.json', {'case': case, 'phase': phase,
             'reason': 'host phase failed or not confirmed; inspect read-only, never replay',
             'error_type': error_type, 'automatic_retry_allowed': False})


@contextmanager
def serial():
    descriptor = os.open(E / 'host-phase.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def run(phase, case):
    assert phase in PHASES and case in CASES
    os.umask(0o077)
    with serial():
        state = gates(phase, case)
        sethostrun('host-' + case + '-' + phase)
        directory = RECOVERY_E / 'host-phases' / case / phase
        directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.mkdir(mode=0o700, exist_ok=False)
        save(directory / 'started.json', {'phase': phase, 'case': case,
            'started_at': datetime.now(timezone.utc).isoformat(), 'image_id': IMAGE,
            'host_runner_sha256': sha(Path(__file__)), 'inside_operator_sha256': sha(INSIDE),
            'plan_sha256': sha(PLAN), 'inputs_sha256': sha(INPUT),
            'private_state_sha256': sha(RECOVERY_STATE), 'timeout_seconds': TIMEOUT_SECONDS,
            'automatic_loop_or_retry': False, 'rubric_mounted': False, 'whole_source_mounted': False})
        code, timed_out = None, False
        try:
            before = protected_output(label='host-before-' + case + '-' + phase)
            save(directory / 'before.json', before)
            counters()
            name = 'socai2-c03-validity-quality-r02-' + case + '-' + phase
            argv = command(phase, case, state, name)
            with (directory / 'container.log').open('xb') as stream:
                try:
                    result = subprocess.run(argv, capture_output=True, timeout=TIMEOUT_SECONDS)
                    stream.write(result.stdout + result.stderr)
                    code = result.returncode
                except subprocess.TimeoutExpired as error:
                    timed_out, code = True, 124
                    stream.write((error.stdout or b'') + (error.stderr or b''))
                    try:
                        removed = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
                        stream.write(b'\nHost deadline: removed only this named phase container.\n')
                        stream.write(removed.stdout + removed.stderr)
                    except (OSError, subprocess.TimeoutExpired) as removal_error:
                        stream.write(('Named container cleanup unconfirmed: ' + type(removal_error).__name__).encode())
            save(directory / 'exit.json', {'exit_code': code, 'timed_out': timed_out,
                'container_log_sha256': sha(directory / 'container.log')})
            # Even an unsuccessful invocation is inspected without replay.
            after = protected_output(label='host-after-' + case + '-' + phase,
                previous=before['observation'] if phase in {'preflight', 'verify'} else None,
                previous_qa=before['closure_qa'] if phase in {'preflight', 'verify'} else None)
            save(directory / 'after.json', after)
            counts = counters()
            gates(phase, case)
            assert code == 0 and not timed_out
            product = E / 'cases' / case / phase / OUTPUTS[phase]
            assert product.is_file()
            if phase == 'invoke':
                assert read(product)['model_attempts'] == 1
                assert read(product)['committed'] == CASES.index(case) + 1
            if phase == 'verify':
                assert read(product)['infrastructure_passed'] is True
                # Raw schema/quality failure never grants the next input.
                assert read(product)['gate_eligible'] is True
            accepted = {'phase': phase, 'case': case, 'phase_completed': True,
                'image_id': IMAGE, 'output_sha256': sha(product),
                'host_runner_sha256': sha(Path(__file__)), 'inside_operator_sha256': sha(INSIDE),
                'before_sha256': sha(directory / 'before.json'), 'after_sha256': sha(directory / 'after.json'),
                'counters': counts, 'model_quality_accepted_by_host': False,
                'next_case_requires_independent_hash_bound_quality_gate': True}
            save(directory / 'accepted.json', accepted)
            print(json.dumps(accepted))
        except BaseException as error:
            stop(case, phase, type(error).__name__)
            save(directory / 'failure.json', {'phase_failed': True, 'error_type': type(error).__name__,
                'exit_code': code, 'timed_out': timed_out, 'automatic_retry_allowed': False,
                'checkpoint_and_original_outputs_preserved': True})
            raise


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3:
            raise ValueError('Expected one phase and one case')
        run(sys.argv[1], sys.argv[2])
    except BaseException as error:
        try:stop(sys.argv[2] if len(sys.argv)>2 else 'unknown',sys.argv[1] if len(sys.argv)>1 else 'unknown',type(error).__name__)
        except BaseException:pass
        print(json.dumps({'host_phase_failed': True, 'error_type': type(error).__name__,
                          'message_or_locals_recorded': False, 'automatic_retry_allowed': False}))
        raise SystemExit(1) from None
