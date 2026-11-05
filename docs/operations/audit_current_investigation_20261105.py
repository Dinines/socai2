"""Current-code audit with frozen exports and synthetic projections; no I/O to services."""
import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path
from uuid import UUID

from app.socai2.baseline_evidence_tools import FIELDS, row_projection
from diagnose_socai2_kafka_inputs_20261105 import one

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2/20261105T001341-export/database-20261105T001344.json'
OUT = ROOT / 'docs/operations/evidence/current-investigation-audit-20261105/offline-checks-v2.json'


async def main():
    assert not OUT.exists(), 'Keep audit evidence immutable; choose a new file for another audit.'
    data = json.loads(SOURCE.read_text('utf-8'))
    original = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    c6 = []
    for run in data['runs']:
        if run['stop_reason'] != 'required_model_input_unavailable':
            continue
        result = await one(data, run)
        c6.append({k: v for k, v in result.items() if k not in {'captured', 'prepared'}})
        c6[-1]['ready'] = result['prepared']['ready']
        c6[-1]['c6_model_step_count_in_export'] = sum(s['run_id'] == run['id'] and s['kind'] == 'model'
            and s['stage_code'] == 'C6' for s in data['run_steps'])

    c2 = []
    for step in data['run_steps']:
        if step['kind'] == 'tool' and step['stage_code'] == 'C2':
            c2.append({'run_id': step['run_id'], 'name': step['name'], 'state': step['state'],
                'selector_count': len(step['actual_args']['parameters']['selectors']),
                'returned_rows': step['returned_rows'], 'error': step['error']})
    errors = []
    for artifact in data['artifacts']:
        if artifact['kind'] != 'model_response':
            continue
        content = artifact['content_json']
        error = content.get('transport_error') or (content.get('payload') or {}).get('transport_error')
        if error is not None:
            run = next(r for r in data['runs'] if r['id'] == artifact['run_id'])
            step = next(s for s in data['run_steps'] if s['id'] == artifact['step_id'])
            req = next(a for a in data['artifacts'] if a['id'] == step['input_artifact_id'])['content_json']
            errors.append({'run_id': run['id'], 'kind': run['kind'], 'run_state': run['state'],
                'step_state': step['state'], 'ended_at': run['ended_at'], 'error': error,
                'provider': req.get('provider'), 'schema_profile': req.get('schema_profile'),
                'response_artifact_id': artifact['id']})

    hash_checks = []
    for mode in ('flat_only', 'flat_and_explicit_ocsf_algorithm'):
        row = dict.fromkeys(FIELDS)
        row.update(event_id=str(UUID(int=301)), event_time='2026-11-05T00:00:00+00:00',
            class_uid=1007, src_hostname='synthetic-hash-audit', hash_sha256='ab' * 32,
            ocsf_json={'class_uid': 1007, 'process': {'name': 'sample.exe', 'pid': 4242}})
        if mode == 'flat_and_explicit_ocsf_algorithm':
            row['ocsf_json']['file'] = {'path': 'C:/fixture/sample.exe',
                'hashes': [{'algorithm': 'SHA-256', 'value': row['hash_sha256']}]}
        projection = row_projection(row)
        hash_checks.append({'mode': mode, 'query_selects_hash_sha256': 'hash_sha256' in FIELDS,
            'input_hash': row['hash_sha256'], 'projected_fields': projection['fields'],
            'hash_in_projected_fields': any(f['value'] == row['hash_sha256'] for f in projection['fields']),
            'hash_omission_recorded': any('hash' in o['source_path'] for o in projection['omissions'])})

    catalog = json.loads((ROOT / 'docs/investigation/current-database-write-catalog.json').read_text('utf-8'))
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in catalog['source_sha256']}
    source_mismatch = [name for name in hashes if hashes[name] != catalog['source_sha256'][name]]
    members = {(r['run_id'], r['alert_id']) for r in data['run_members']}
    artifacts = {r['id']: r for r in data['artifacts']}
    linkage_errors = []
    for step in data['run_steps']:
        for key in ('input_artifact_id', 'output_artifact_id'):
            if step[key] and (step[key] not in artifacts or artifacts[step[key]]['run_id'] != step['run_id']):
                linkage_errors.append({'step_id': step['id'], 'field': key})
    for member in data['result_members']:
        if (member['run_id'], member['alert_id']) not in members:
            linkage_errors.append({'result_member_id': member['id'], 'reason': 'not_in_frozen_members'})
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == original
    result = {'scope': 'source review + current-code offline replay, not live PG/model acceptance',
        'source': SOURCE.relative_to(ROOT).as_posix(), 'evidence_source_sha256': original,
        'real_model_calls': 0, 'remote_queries': 0, 'database_mutations': 0,
        'c6_current_code_replay': c6, 'c2_actual_steps': c2, 'explicit_model_errors': errors,
        'hash_field_projection': hash_checks, 'code_source_sha256': hashes,
        'catalog_source_mismatch': source_mismatch, 'record_linkage_errors': linkage_errors,
        'record_counts': {k: len(v) for k, v in data.items()}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + '\n', 'utf-8')
    print(json.dumps({'c6': [{'run_id': r['run_id'], 'reason': r['reason'], 'bytes': r['bytes'],
        'required_count': r['required_count'], 'omitted_required': sum(bool(x['omitted']) for x in r['required'])} for r in c6],
        'c2_ti': dict(Counter((s['error'] or {}).get('code') or s['state'] for s in c2 if s['name'] == 'threat_intel')),
        'explicit_errors': len(errors), 'hash_checks': [{k: v for k, v in r.items() if k != 'projected_fields'} for r in hash_checks],
        'catalog_source_mismatch': source_mismatch, 'record_linkage_errors': linkage_errors}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
