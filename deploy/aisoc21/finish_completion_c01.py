"""Observe C01 preservation and revoke only its two temporary operation keys.

`before-probes` must precede any real probe; `finish` only follows the final
independent audit of all scenario outputs. No old data or offsets are repaired.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from configure_triage_admission_3a import pg, save, observation, container_json, OFFSET_CODE
from deploy_fusion_delivery_c01 import protect_old_state
from shared_1b import SharedBatch
from prepare_identity_read_3a import lit

R = Path('/opt/sting-aisoc-socai2')
E = R / 'evidence/c01-fusion-delivery-20261020'
P = R / 'private/completion-c01'


def read(path):
    return json.loads(path.read_text())


def dlq():
    rows = json.loads(pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT id,row_to_json(d)::text AS material FROM aisoc_dead_letters d ORDER BY id) t;").stdout)
    return {str(row['id']): hashlib.sha256(row['material'].encode()).hexdigest() for row in rows}


def before_probes():
    assert not (E / 'probe').exists() and not (E / 'boundaries').exists()
    assert (E / 'limits-amended.json').is_file()
    save(E, 'dlq-before.json', dlq())
    offsets = container_json(OFFSET_CODE)
    assert offsets == read(R / 'evidence/3a-triage-admission-config-20261020/offsets-after.json')
    save(E, 'budget-group-offsets-before.json', offsets)
    save(E, 'before-probes.json', {'old_dlq_rows': len(dlq()), 'old_budget_groups': 6,
                                'no_broker_publication_yet': True, 'real_models': 0})
    print(json.dumps({'before_probes_frozen': True, 'old_dlq_rows': len(dlq()), 'old_budget_groups': 6}))


def finish():
    assert not (E / 'finish-started.json').exists()
    assert read(E / 'probe/acceptance.json')['accepted']
    assert read(E / 'boundaries/acceptance.json')['accepted']
    assert read(E / 'http/acceptance.json')['accepted']
    assert read(E / 'independent-audit.json')['accepted'], 'Independent final audit required'
    limits = read(E / 'limits-amended2.json')
    now = observation()
    protect_old_state(now, allow_fusion=True)
    old = read(E / 'before.json')
    assert len(now['materials']['alerts']) == len(old['materials']['alerts']) + 5
    assert len(now['materials']['alerts']) - len(old['materials']['alerts']) <= limits['new_alert_rows']
    for table in set(old['materials']) - {'alerts'}:
        assert now['materials'][table] == old['materials'][table]
    current_dlq, old_dlq = dlq(), read(E / 'dlq-before.json')
    assert all(current_dlq.get(key) == value for key, value in old_dlq.items())
    assert len(current_dlq) == len(old_dlq) + 1
    offsets = container_json(OFFSET_CODE)
    assert offsets == read(E / 'budget-group-offsets-before.json')
    # Probe events expose actual broker coordinates; count input, output and
    # failed sends without double-counting capture-only reads as publications.
    accounting = read(E / 'audited-accounting.json')
    assert accounting['all_send_attempts'] <= limits['broker_send_attempts_including_failed']
    assert accounting['raw_send_attempts'] <= limits['raw_send_attempts']
    assert accounting['fused_send_attempts'] <= limits['fused_send_attempts']
    assert accounting['worker_deliveries_and_output_reads'] <= limits['test_deliveries']
    assert accounting['new_topics'] <= limits['new_test_topics'] and accounting['new_groups'] <= limits['new_test_groups']
    state = read(P / 'state.json')
    save(E, 'finish-started.json', {'revoke_only_key_ids': [v['key_id'] for v in state['identities'].values()],
         'new_alert_rows': 5, 'new_dlq_rows': 1, 'accounting': accounting, 'old_materials_preserved': True})
    batch = SharedBatch(R)
    sql = 'SET ROLE aisoc; BEGIN; '
    for identity in state['identities'].values():
        sql += 'UPDATE api_keys SET is_active=false WHERE id=' + lit(identity['key_id']) + ' AND tenant_id=' + lit(identity['tenant_id']) + '; '
    batch.pg(sql + 'COMMIT;')
    revoked = []
    for alias, identity in state['identities'].items():
        request = urllib.request.Request('http://127.0.0.1:18000/api/v1/alerts?limit=1',
                    headers={'Authorization': 'Bearer ' + identity['key']})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        assert status == 401
        revoked.append({'alias': alias, 'key_id': identity['key_id'], 'status': status})
    save(E, 'keys-revoked.json', revoked)
    after = observation()
    assert now == after
    save(E, 'after.json', after)
    save(E, 'budget-group-offsets-after.json', offsets)
    save(E, 'acceptance.json', {'change': 'C01', 'bounded_accepted': True,
         'new_alert_rows': 5, 'new_dlq_rows': 1, 'old_material_tables_preserved': 14,
         'old_dlq_rows_preserved': len(old_dlq), 'other_containers_preserved': 35,
         'volumes_preserved': 18, 'migrations_preserved': 134, 'readers_preserved': 10,
         'budget_rows_preserved': 5, 'unknown_reservations_preserved': 3,
         'old_six_budget_groups_unchanged': True, 'temporary_operation_keys_revoked': 2,
         'accounting': accounting, 'compose_layers': 23, 'runtime_source_layers': 20,
         'real_models': 0, 'only_updated': 'fusion', 'full_migration_complete': False,
         'agents_worker_enabled': False, 'full_cache_loss_recovery_accepted': False,
         'old_snapshotless_row_recovery_accepted': False, 'real_vendor_actions': 0})
    print(json.dumps(read(E / 'acceptance.json')))


if __name__ == '__main__':
    os.umask(0o077)
    if sys.argv[1:] == ['before-probes']:
        before_probes()
    elif sys.argv[1:] == ['finish']:
        finish()
    else:
        raise SystemExit('Usage: finish_completion_c01.py before-probes | finish')
