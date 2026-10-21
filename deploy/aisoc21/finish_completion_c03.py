"""Seal C03-01 after independent runtime audit; all shared operations are read-only."""
from datetime import datetime, timezone
import hashlib
import json
import os

from configure_triage_admission_3a import observation, save, container_json, FLAGS_CODE, OFFSET_CODE, inspect
from deploy_triage_reasoning_c03 import protected
from prepare_completion_c03 import R, E, P


def read(path):
    return json.loads(path.read_text())


def main():
    os.umask(0o077)
    assert not (E / 'acceptance.json').exists()
    built = read(E / 'built-image.json')
    tests = read(E / f"tests-agents-{built['test_attempt']}.json")
    audit = read(E / 'independent-audit.json')
    assert audit['accepted'] and audit['image_id'] == built['agents']
    assert tests['exit_code'] == tests['failed'] == tests['errors'] == 0 and tests['passed'] > 0
    assert read(E / 'probe/acceptance.json')['accepted'] and read(E / 'deployment.json')['image_id'] == built['agents']
    after = observation()
    protected(after, changed_agents=True)
    state = read(R / 'private/app-triage-budget-3a.json')
    tenants = [state['identities'][a]['tenant_id'] for a in ['a', 'b']]
    flags = container_json(FLAGS_CODE, payload=tenants)
    assert flags['uid'] == 10001 and flags['reader_maps_resolve']
    assert all(flags[k] is False for k in ['worker', 'escalation', 'memory_writeback', 'approvals', 'alert_graph'])
    assert flags['source'] == built['source_sha256']
    prompt = container_json("from app.llm.prompt_registry import default_registry,load_lock;from pathlib import Path;import hashlib,json;r=default_registry();assert not r.verify_against_lock(load_lock());p=r.get('triage.system');print(json.dumps({'version':p.version,'sha256':p.sha256,'lock_sha256':hashlib.sha256(Path('/app/app/llm/prompts.lock.json').read_bytes()).hexdigest()}))")
    assert prompt['version'] == '3' and prompt['lock_sha256'] == built['lock_sha256']
    save(E, 'prompt-after.json', prompt)
    offsets = container_json(OFFSET_CODE)
    assert offsets == read(E / 'budget-group-offsets-before.json')
    ready = container_json("import urllib.request,json;print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8084/readyz',timeout=5))))")
    assert ready['status'] == 'ready' and not ready.get('subscriptions')
    resident = inspect('socai2-agents-1')
    assert resident['Image'] == built['agents'] and resident['Config']['StopTimeout'] == 60
    assert resident['State']['Health']['Status'] == 'healthy'
    save(E, 'resident-after.json', flags)
    save(E, 'readiness-after.json', ready)
    save(E, 'budget-group-offsets-after.json', offsets)
    save(E, 'after.json', after)
    save(E, 'acceptance.json', {'batch': E.name, 'change': 'C03-01',
         'finished_at': datetime.now(timezone.utc).isoformat(), 'bounded_accepted': True,
         'source_count': 184, 'runtime_source_layers': 22, 'compose_layers': 25,
         'image_id': built['agents'], 'lock_sha256': built['lock_sha256'], 'triage_prompt': prompt, 'parent_image': built['parent'], 'test_attempt': built['test_attempt'],
         'direct_tests_passed': tests['passed'], 'baked_mock_http_requests': 1,
         'synthetic_model_usage_is_not_provider_usage': True,
         'only_recreated': 'agents', 'stop_grace_seconds': 60, 'original_env_mounts_dependencies_preserved': True,
         'old_material_tables_preserved': 14, 'budget_rows_preserved': 5,
         'unknown_reservations_preserved': 3, 'reader_keys_preserved': 10,
         'other_containers_preserved': 35, 'volumes_preserved': 18, 'upstream_migrations_preserved': 134,
         'old_six_group_offsets_unchanged': True, 'real_models': 0, 'new_business_pg_writes': 0,
         'new_business_rows': 0, 'new_tenants': 0, 'new_keys': 0, 'new_readers': 0,
         'new_broker_publications': 0, 'new_broker_record_deliveries': 0, 'broker_offset_commits': 0,
         'worker_enabled': False, 'full_migration_complete': False, 'model_quality_retested': False,
         'direct_replay_pattern_cache_repaired': False, 'real_inflight_docker_stop_tested': False,
         'prior_infrastructure_contract_evidence_reused': True,
         'independent_audit_sha256': hashlib.sha256((E / 'independent-audit.json').read_bytes()).hexdigest(),
         'next_change': 'C03-02 bounded blind model quality; worker still OFF'})
    print(json.dumps({'change': 'C03-01', 'bounded_accepted': True, 'direct_tests_passed': tests['passed'],
                      'real_models': 0, 'new_business_rows': 0, 'worker_enabled': False,
                      'source_layers': 22, 'compose_layers': 25}))


if __name__ == '__main__':
    main()
