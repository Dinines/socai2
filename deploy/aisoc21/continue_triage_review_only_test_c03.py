"""C03-R01 test-only continuation candidate. No automatic execution/retries.

Import exactly the hash-bound pure-stdlib982 controller; never call its main or
prepare/stage/finish. Its four operation functions are reused with explicit
E/P/PG/metrics/audit overrides. Parent checkpoints are references, not new runs.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
BATCH = 'c03-triage-review-only-20261021'
ROOT_E = R / 'evidence' / BATCH
PARENT_E = ROOT_E / 'observation-recovery-r02'
E = PARENT_E / 'test-recovery-r03'
PARENT_P = R / 'private/completion-c03-review-only'
P = PARENT_P / 'test-recovery-r03'
BASE_SHA = '982f46b75fc5ef359c8853a8a813b4521e4f7307005af1ee7648abcb4bda866e'
PROFILE_TEST = 'tests/porting/test_triage_review_only_profile_c03.py'
NEW_TEST_SHA = 'fc444a32c655abe16cd0a24c44a81c7de7f538cb0a582fdabd21f799944bbd8e'
PHASES = ('stage-test', 'build', 'deploy', 'verify', 'finish')
DIRECTORY = {'stage-test': 'test', 'build': 'build', 'deploy': 'deploy', 'verify': 'verify', 'finish': 'finish'}


def require(value, message):
    if not value:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    path.chmod(0o600)


def copy_once(source, destination):
    with Path(destination).open('xb') as stream:
        stream.write(Path(source).read_bytes())
    Path(destination).chmod(0o600)


def parent_guard(binding):
    actual = {}
    for path in sorted(ROOT_E.rglob('*')):
        if path == E or E in path.parents:
            continue
        require(not path.is_symlink(), 'parent evidence symlink')
        if path.is_file():
            actual[str(path.relative_to(ROOT_E))] = sha(path)
    require(actual == binding['continuation']['parent_tree_sha256'] and len(actual) == 123, 'parent123 evidence changed')
    parent_binding = read(PARENT_E / 'execution-bindings.json')
    for name in ('runtime_source_sha256', 'parent_runtime_source_sha256', 'parent_compose_sha256', 'parent_compose_order',
                 'scope_sha256', 'document_sha256', 'parent_test_input_sha256', 'prompt_lock_sha256',
                 'broker_metadata_selectors', 'parent_broker_metadata', 'overlay_sha256', 'dockerfile_sha256',
                 'host_policy_sha256', 'parent_handoff_sha256', 'parent_source_manifest_sha256', 'parent_environment'):
        require(binding[name] == parent_binding[name], 'continuation changed immutable base input: ' + name)
    require(binding['new_test_sha256'] == {**parent_binding['new_test_sha256'], PROFILE_TEST: NEW_TEST_SHA}, 'more than one test input changed')
    for phase in ('prepare', 'stage'):
        checkpoint = read(PARENT_E / phase / 'completed.json')
        require(checkpoint['operator_sha256'] == BASE_SHA and checkpoint['bindings_sha256'] == binding['continuation']['parent_bindings_sha256'], 'parent successful checkpoint not frozen982/668')
    require(not (PARENT_E / 'test/completed.json').exists(), 'parent failed test unexpectedly completed')
    old = read(PARENT_E / 'test/result.json')
    require(old['exit_code'] == 1 and old['junit']['collected'] == 191 and old['summary']['passed'] == 189 and old['summary']['failed'] == 2,
            'not the frozen189pass2fixturefail')
    require(len(list((PARENT_E / 'sql-events').glob('*-started.json'))) == 37 and
            len(list((PARENT_E / 'http-events').glob('*-started.json'))) == 1, 'parent observation count drift')
    for phase in ('build', 'deploy', 'verify', 'finish'):
        require(not (PARENT_E / phase).exists(), 'parent downstream action exists')


def load_base(binding):
    path = PARENT_P / 'operate_triage_review_only_c03_observation_recovery_r02.py'
    require(sha(path) == BASE_SHA, 'pure stdlib base source changed')
    spec = importlib.util.spec_from_file_location('c03_r01_frozen_host_base_982', path)
    base = importlib.util.module_from_spec(spec)
    previous_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(base)  # Exact stdlib-only definitions; no __main__, no old-P bytecode writes.
    finally:
        sys.dont_write_bytecode = previous_bytecode
    base.E, base.P = E, P
    original_pg, original_metrics = base.pg, base.metrics

    def pg(sql):
        require(len(list((E / 'sql-events').glob('*-started.json'))) < 59, 'prior41 + continuation PG cap59 exhausted')
        return original_pg(sql)

    def metrics(which):
        require(which == 'after' and not list((E / 'http-events').glob('*-started.json')), 'only one inherited-window after metrics is allowed')
        return original_metrics(which)

    base.pg, base.metrics = pg, metrics
    base.gate = lambda path, phase, current, image: audit(path, phase, current, image, base)
    return base


def audit(path, phase, binding, image, base):
    value = read(path)
    require(value['accepted'] is True and value['batch'] == BATCH and value['phase'] == phase and
            value['operator_sha256'] == sha(__file__) and value['base_operator_sha256'] == BASE_SHA and
            value['bindings_sha256'] == sha(binding['_path']) and value['image_id'] == image, 'audit not exact wrapper/base/image/bindings')
    for name in ('prepare', 'stage'):
        require(value['inherited_' + name + '_completed_sha256'] == sha(PARENT_E / name / 'completed.json'), 'inherited audit checkpoint mismatch')
    require(value['inherited_parent_bindings_sha256'] == binding['continuation']['parent_bindings_sha256'] and
            value['inherited_before_sha256'] == sha(E / 'before.json') and
            value['inheritance_manifest_sha256'] == sha(E / 'inherited-inputs.json'), 'audit inheritance mismatch')
    require(value['runtime_source_sha256'] == base.expected_sources(binding) and value['test_input_sha256'] == base.input_map(binding), 'audit runtime/test mismatch')
    require(value['scope_sha256'] == binding['scope_sha256'] and
            value['observer_recovery_scope_sha256'] == binding['observer_recovery']['scope_sha256'] and
            value['continuation_scope_sha256'] == binding['continuation']['scope_sha256'], 'audit scope mismatch')
    for name in ('test', 'build') + (('deploy', 'verify') if phase == 'postdeploy' else ()):
        require(value[name + '_completed_sha256'] == sha(E / name / 'completed.json'), 'new audit checkpoint mismatch')
    if phase == 'postdeploy':
        require(value['after_sha256'] == sha(E / 'after.json'), 'postdeploy observation mismatch')
    return value


def stage_test(binding, base):
    test_review = P / 'test-independent-review.json'
    require(sha(test_review) == 'f429f044dcb92c8c291808fd30d4393381ac0d22a714cfb6014975d7d392403f', 'test-only review bytes changed')
    reviewed = read(test_review)
    require(reviewed['accepted'] is True and reviewed['candidate_test_sha256'] == NEW_TEST_SHA and
            reviewed['candidate_manifest_sha256'] == '2764c9ac62484b6e20c08d661a21ad42c434d7ec6056804cc602c02e78ce927c', 'test review not exact fc444 candidate')
    require(base.inspect(base.AGENTS)['Image'] == base.BASE_IMAGE, 'parent runtime is not9cb')
    base.no_candidate_tag()
    require(base.source_map() == base.expected_sources(binding), 'application runtime source changed')
    require(sha(S / PROFILE_TEST) == read(PARENT_E / 'execution-bindings.json')['new_test_sha256'][PROFILE_TEST], 'test already changed outside continuation')
    revised = P / 'revised-profile-test.py'
    require(sha(revised) == NEW_TEST_SHA == binding['new_test_sha256'][PROFILE_TEST], 'unique revised test bytes mismatch')
    for name in ('build-context', 'candidate-inspect.json'):
        require(not (PARENT_P / name).exists(), 'parent private build/deploy artifact exists')
    inherited = {'public': {}, 'private': {}}
    copy_once(PARENT_E / 'before.json', E / 'before.json')
    inherited['public']['before.json'] = {'source': str(PARENT_E / 'before.json'), 'sha256': sha(E / 'before.json'), 'new_observation': False}
    for name in ('parent-inspect.json', 'parent-render.json', 'candidate-render.json', 'agents-rollback.json'):
        copy_once(PARENT_P / name, P / name)
        require(sha(P / name) == sha(PARENT_P / name), 'private inherited byte mismatch')
        inherited['private'][name] = {'source': str(PARENT_P / name), 'sha256': sha(P / name), 'private_bytes_exported': False}
    stage = read(PARENT_E / 'stage/completed.json')['result']
    require(sha(P / 'parent-render.json') == stage['rendered_parent_sha256'] and
            sha(P / 'candidate-render.json') == stage['rendered_candidate_sha256'], 'parent render inheritance mismatch')
    inherited['inherited_prepare_completed_sha256'] = sha(PARENT_E / 'prepare/completed.json')
    inherited['inherited_stage_completed_sha256'] = sha(PARENT_E / 'stage/completed.json')
    inherited['no_new_prepare_or_source_stage_executed'] = True
    save(E / 'inherited-inputs.json', inherited)
    copy_once(__file__, E / 'wrapper-source.py')
    copy_once(PARENT_P / 'operate_triage_review_only_c03_observation_recovery_r02.py', E / 'base-operator-source.py')
    copy_once(binding['_path'], E / 'execution-bindings.json')
    scope = binding['continuation']['scope_markdown'].encode()
    require(hashlib.sha256(scope).hexdigest() == binding['continuation']['scope_sha256'], 'continuation scope text mismatch')
    with (E / 'test-continuation-scope-before.md').open('xb') as stream:
        stream.write(scope)
    (E / 'test-continuation-scope-before.md').chmod(0o600)
    copy_once(P / 'continuation-independent-audit.json', E / 'continuation-independent-audit.json')
    copy_once(test_review, E / 'test-independent-review.json')
    temporary = (S / PROFILE_TEST).with_name(Path(PROFILE_TEST).name + '.r03-replacement')
    copy_once(revised, temporary)
    temporary.chmod(0o644)
    require(sha(S / PROFILE_TEST) == read(PARENT_E / 'execution-bindings.json')['new_test_sha256'][PROFILE_TEST], 'concurrent profile test write')
    os.replace(temporary, S / PROFILE_TEST)
    require(base.input_map(binding) == {**binding['parent_test_input_sha256'], **binding['new_test_sha256']}, 'test cohort changed beyond one file')
    result = base.phase_test(binding)
    require(result['junit']['collected'] == result['summary']['passed'] == 191 and
            result['summary'].get('skipped', 0) == 0 and sum(v['collected'] for v in result['junit']['new_files'].values()) == 22,
            'continuation cohort is not191/22new all passed')
    return result


def finish(binding, base):
    built = read(E / 'built-image.json')
    audit(E / 'postdeploy-independent-audit.json', 'postdeploy', binding, built['image_id'], base)
    result = {'batch': BATCH, 'change': 'C03-R01', 'bounded_accepted': True,
              'R01_source_and_worker_off_deployment_only': True, 'profile': 'review_only_v1',
              'image_id': built['image_id'], 'source_sha256': base.expected_sources(binding),
              'real_models': 0, 'worker_enabled': False, 'R02_accepted': False,
              'autonomous_quality_passed': False, 'whole_C03_complete': False, 'full_migration_complete': False,
              'operator_sha256': sha(__file__), 'base_operator_sha256': BASE_SHA, 'bindings_sha256': sha(binding['_path']),
              'verify_completed_sha256': sha(E / 'verify/completed.json'),
              'postdeploy_audit_sha256': sha(E / 'postdeploy-independent-audit.json'),
              'parent_evidence_sha256': binding['continuation']['parent_tree_sha256'],
              'inherited_before_sha256': sha(E / 'before.json'), 'inheritance_manifest_sha256': sha(E / 'inherited-inputs.json'),
              'parent_prepare_and_stage_inherited_not_reexecuted': True,
              'old189pass2fixturefail_and_original_observer_failure_preserved': True,
              'historical_PG_attempts': 41, 'new_PG_attempts': len(list((E / 'sql-events').glob('*-started.json'))),
              'before_metrics_inherited': 1, 'new_after_metrics': 1}
    save(E / 'acceptance.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=PHASES)
    parser.add_argument('--bindings', type=Path, required=True)
    args = parser.parse_args()
    binding = read(args.bindings)
    require(binding['execution_authorized'] is True and 'UNBOUND' not in json.dumps(binding), 'continuation candidate not authorized/bound')
    require(binding['operator_sha256'] == sha(__file__) and binding['continuation']['base_operator_sha256'] == BASE_SHA, 'controller source not bound')
    require(os.geteuid() == 0, 'host root required')
    os.umask(0o077)
    binding['_path'] = str(args.bindings)
    P.mkdir(mode=0o700, exist_ok=True)
    E.mkdir(mode=0o700, exist_ok=True)
    with (PARENT_P / 'phase.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        parent_guard(binding)
        review = P / 'continuation-independent-audit.json'
        require(sha(review) == binding['operator_review_sha256'] and read(review)['accepted'] is True and
                read(review)['operator_sha256'] == sha(__file__) and read(review)['base_operator_sha256'] == BASE_SHA,
                'continuation static review missing exact sources')
        base = load_base(binding)
        for phase in PHASES[:PHASES.index(args.phase)]:
            checkpoint = read(E / DIRECTORY[phase] / 'completed.json')
            require(checkpoint['operator_sha256'] == sha(__file__) and checkpoint['bindings_sha256'] == sha(args.bindings), 'earlier wrapper checkpoint changed')
        directory = E / DIRECTORY[args.phase]
        directory.mkdir(mode=0o700)
        identity = {'batch': BATCH, 'phase': args.phase, 'operator_sha256': sha(__file__), 'base_operator_sha256': BASE_SHA,
                    'bindings_sha256': sha(args.bindings), 'inherited_prepare_stage_not_reexecuted': True}
        save(directory / 'started.json', identity)
        try:
            require(base.source_map() == base.expected_sources(binding), 'application source changed')
            require(sha(S / 'services/agents/app/llm/prompts.lock.json') == binding['prompt_lock_sha256'], 'prompt lock changed')
            for path, checksum in binding['parent_compose_sha256'].items():
                require(sha(S / path) == checksum, 'parent compose changed')
            for path, checksum in binding['document_sha256'].items():
                require(sha(S / path) == checksum, 'adopted scope/document changed during continuation')
            require(sha(S / base.MANIFEST) == binding['parent_source_manifest_sha256'] and
                    sha(S / 'docs/handoff/handoff-manifest.json') == binding['parent_handoff_sha256'] and
                    sha(S / base.DOCKERFILE) == binding['dockerfile_sha256'] and sha(S / base.OVERLAY) == binding['overlay_sha256'],
                    'frozen source/index/build inputs changed')
            expected_tests = {**binding['parent_test_input_sha256'], **binding['new_test_sha256']}
            if args.phase == 'stage-test':
                expected_tests[PROFILE_TEST] = read(PARENT_E / 'execution-bindings.json')['new_test_sha256'][PROFILE_TEST]
            require(base.input_map(binding) == expected_tests, 'test cohort changed outside the unique approved file delta')
            if args.phase == 'stage-test':
                result = stage_test(binding, base)
            elif args.phase == 'finish':
                result = finish(binding, base)
            else:
                result = getattr(base, 'phase_' + args.phase)(binding)
            parent_guard(binding)
            save(directory / 'completed.json', {**identity, 'result': result})
            print(json.dumps({'phase': args.phase, 'completed': True, 'checkpoint_sha256': sha(directory / 'completed.json')}))
        except BaseException as exc:
            save(directory / 'failure.json', {**identity, 'type': type(exc).__name__,
                                             'message_sha256': hashlib.sha256(str(exc).encode()).hexdigest(), 'automatic_retry_or_rollback': False})
            raise SystemExit(1) from None


if __name__ == '__main__':
    main()
