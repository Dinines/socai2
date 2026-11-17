"""Read existing real Run originals and their immutable linkage, without replay."""
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from uuid import UUID

from run import application, plain, read, save

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
cfg = read(HERE / 'config.json')
os.environ.update(read(ROOT / cfg['environment_file'])); os.environ.update(cfg['runtime_overrides'])
os.environ['SOCAI2_INVESTIGATION_POLICY'] = str(ROOT / cfg['policy'])
sys.path[:0] = [str(ROOT), str(ROOT / 'services/api')]


async def main():
    from app.models import socai2 as m
    from app.socai2.baseline_store import encoded
    from app.socai2.case_service import CaseService
    from app.socai2.page_reader import PageReadService
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from tools.testdata.incident_integration.run import connect
    exports = {name: read(ROOT / name) for name in cfg['reference_exports']}
    expected_runs = {r['id']: r for data in exports.values() for r in data['runs']}
    expected_artifacts = {a['id']: a for data in exports.values() for a in data['artifacts']}
    ids = [UUID(r) for r in expected_runs]
    engine = await connect(cfg); sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = CaseService(sessions); tenant = UUID(cfg['tenant_id'])

    async def snapshot():
        result = {}
        async with service.transaction(tenant, readonly=True) as store:
            for name, model, condition in [('runs', m.Runs, m.Runs.id.in_(ids)),
                ('steps', m.RunSteps, m.RunSteps.run_id.in_(ids)), ('artifacts', m.Artifacts, m.Artifacts.run_id.in_(ids))]:
                table = model.__table__
                rows = (await store.db.execute(select(table).where(*store.where(table, condition)))).mappings().all()
                result[name] = sorted(plain([dict(r) for r in rows]), key=lambda r: r['id'])
        return result

    try:
        before = await snapshot()
        artifacts = {a['id']: a for a in before['artifacts']}
        runs = {r['id']: r for r in before['runs']}
        steps = {s['id']: s for s in before['steps']}
        assert set(runs) == set(expected_runs) and set(artifacts) == set(expected_artifacts)
        for key, run in runs.items():
            assert run['state'] == expected_runs[key]['state'] and run['input_artifact_id'] in artifacts
        for key, artifact in artifacts.items():
            original = expected_artifacts[key]
            assert artifact['sha256'] == original['sha256']
            assert artifact['content_json'] == original['content_json'] and artifact['content_text'] == original['content_text']
            raw = encoded(artifact['content_json']) if artifact['content_json'] is not None else artifact['content_text'].encode()
            assert len(raw) == artifact['size_bytes'] and hashlib.sha256(raw).hexdigest() == artifact['sha256']
            if artifact['step_id']:
                assert steps[artifact['step_id']]['run_id'] == artifact['run_id']
        for step in steps.values():
            for key in ('input_artifact_id', 'output_artifact_id'):
                if step[key]:
                    assert artifacts[step[key]]['run_id'] == step['run_id']
            if step['parent_step_id']:
                assert steps[step['parent_step_id']]['run_id'] == step['run_id']
        refs = {(r['type'], r['id']) for a in artifacts.values() for r in a['source_refs']}
        extra = {kind: [UUID(identity) for typ, identity in refs if typ == kind] for kind in ('artifact', 'alert_material')}
        async with service.transaction(tenant, readonly=True) as store:
            resolved = {}
            for kind, model in [('artifact', m.Artifacts), ('alert_material', m.AlertMaterials)]:
                table = model.__table__
                rows = (await store.db.execute(select(table.c.id).where(*store.where(table, table.c.id.in_(extra[kind]))))).scalars().all()
                resolved[kind] = set(map(str, rows))
        assert all(identity in resolved[kind] for kind, identity in refs)
        selected = {run['input_artifact_id'] for run in runs.values()}
        modules = []
        for step in sorted(steps.values(), key=lambda s: (s['run_id'], s['seq'])):
            if step['kind'] not in {'stage', 'graph'}:
                continue
            child = [s for s in steps.values() if s['parent_step_id'] == step['id']]
            input_ids = ([step['input_artifact_id']] if step['input_artifact_id'] else
                list(dict.fromkeys([runs[step['run_id']]['input_artifact_id'],
                    *(s['input_artifact_id'] for s in child if s['input_artifact_id'])])))
            output_ids = [step['output_artifact_id']] if step['output_artifact_id'] else []
            selected.update(input_ids + output_ids)
            modules.append({'run_id': step['run_id'], 'stage': step['stage_code'], 'step_id': step['id'],
                'state': step['state'], 'input_artifact_ids': input_ids, 'output_artifact_ids': output_ids,
                'input_resolution': 'direct' if step['input_artifact_id'] else 'frozen_Run_and_child_steps',
                'children': [{'step_id': s['id'], 'input_artifact_id': s['input_artifact_id'],
                              'output_artifact_id': s['output_artifact_id'], 'state': s['state']} for s in child]})
        # One representative raw/request pair per module, plus the actual C4
        # query, unknown attempt and both C3 completion originals/merge.
        seen = set()
        for a in artifacts.values():
            step = steps.get(a['step_id'], {})
            body = a['content_json'] or {}
            key = (step.get('stage_code'), a['kind'], body.get('type'))
            important = a['kind'] in {'model_request', 'model_response', 'tool_request', 'tool_response'} or body.get('type') in {
                'model_original_response', 'c3_section_merge', 'c3_section_completion'}
            if important and (key not in seen or 'section_completion' in body or 'field_origins' in body):
                selected.add(a['id']); seen.add(key)
            if 'field_origins' in body:
                selected.add(a['id'])
                for name, origin in body['field_origins'].items():
                    assert origin['original_artifact_id'] in artifacts
                    assert hashlib.sha256(encoded(body['merged_sections'][name])).hexdigest() == origin['value_sha256']
                    selected.add(origin['original_artifact_id'])
        reads = []
        app = application(service, PageReadService(sessions), tenant)
        async with AsyncClient(transport=ASGITransport(app=app), base_url=cfg['http_base_url']) as client:
            for identity in sorted(selected):
                a = artifacts[identity]; run = runs[a['run_id']]
                if run['kind'] == 'baseline':
                    path = f"/api/v1/socai2/cases/{run['case_id']}/runs/{run['id']}/artifacts/{identity}"
                else:
                    subject, key = ('alerts', 'alert_id') if run['kind'] == 'alert_basic' else ('incidents', 'incident_id')
                    path = f"/api/v1/socai2/{subject}/{run[key]}/analysis/runs/{run['id']}/artifacts/{identity}"
                response = await client.get(path)
                assert response.status_code == 200, (path, response.status_code)
                value = response.json()
                assert value['content_json'] == a['content_json'] and value['content_text'] == a['content_text']
                reads.append({'path': path, 'status': 200, 'sha256': a['sha256'], 'size_bytes': a['size_bytes']})
        assert await snapshot() == before
        summary = {'source_exports': list(exports), 'runs': len(runs), 'artifacts': len(artifacts),
            'steps': len(steps), 'source_references_resolved': len(refs), 'http_gets': len(reads),
            'module_codes': sorted({row['stage'] for row in modules}),
            'indirect_stage_inputs': sum(row['input_resolution'] != 'direct' for row in modules),
            'original_bytes_hashes_match': True, 'old_Run_states_preserved': True, 'GET_readonly': True,
            'new_model_calls': 0, 'new_source_calls': 0,
            'historical_full_policy_snapshot': 'not_saved_in_old_Runs_no_backfill',
            'unreceived_or_unknown_responses': [{'step_id': s['id'], 'stage': s['stage_code'], 'state': s['state']}
                for s in steps.values() if s['kind'] in {'tool', 'model'} and not s['output_artifact_id']],
            'model_quality': 'NOT_PASSED'}
        save('module-links.json', {'summary': summary, 'modules': modules, 'http_reads': reads})
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
