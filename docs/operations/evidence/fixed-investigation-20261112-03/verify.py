"""Saved model/stage/Case readback, no model calls or state writes."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import connect, read, save

config, folder = initialize(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('config.json'))


async def main():
    from app.api.v1.endpoints import socai2_analysis as api
    from app.socai2.stage_reader import StageReadService
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker
    data, execution = read(folder / 'export/database.json'), read(folder / 'execution.json')
    artifacts = {a['id']: a for a in data['artifacts']}
    runs = {r['id']: r for r in data['runs']}
    result = next(r for r in data['results'] if r['source_run_id'] == execution['run_id'])
    result_http = read(folder / 'http' / ('result-' + result['id'] + '.json'))['body']
    case_http = read(folder / 'http/case.json')['body']
    for key in ('id','source_run_id','conclusion','validation_state','delivery_state','conclusion_origin',
                'conclusion_state','recommendations','questions','findings','case_impact','report_artifact_id'):
        assert result_http['result'][key] == result[key], key
    assert result['id'] in read(folder / 'http/run.json')['body']['result_ids']
    assert len(result_http['members']) == len(data['result_members']) == 3
    assert artifacts[result['report_artifact_id']]['run_id'] == result['source_run_id']
    current = case_http['current_assessment']
    if current:
        stored = next(a for a in data['case_assessments'] if a['id'] == current['value']['id'])
        for key in ('conclusion','origin','validity'):
            assert stored[key] == current['value'][key]
        assert any(s['result_id'] == result['id'] for s in current['sources'])
    engine = await connect(config)
    reader = StageReadService(async_sessionmaker(engine, expire_on_commit=False))
    app = FastAPI()
    app.include_router(api.router, prefix='/api/v1')
    app.dependency_overrides[api.get_service] = lambda: reader
    app.dependency_overrides[api.User.__metadata__[0].dependency] = lambda: SimpleNamespace(tenant_id=UUID(config['tenant_id']))
    stage_readback = []
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=config['http_base_url']) as client:
            for stage in execution['stages']:
                run = runs[stage['run_id']]
                kind = 'alerts' if run['kind'] == 'alert_basic' else 'incidents'
                subject = run['alert_id'] if kind == 'alerts' else run['incident_id']
                path = f'/api/v1/socai2/{kind}/{subject}/analysis/runs/{run["id"]}'
                response = await client.get(path)
                assert response.status_code == 200, path
                body = response.json()
                assert body['run']['state'] == run['state']
                saved = next((r for r in data['alert_assessments' if kind == 'alerts' else 'incident_diagnoses']
                              if r['source_run_id'] == run['id']), None)
                if saved:
                    fields = ('verdict','rationale','recommendations') if kind == 'alerts' else ('summary','diagnosis','open_questions')
                    assert all(body['result'][key] == saved[key] for key in fields)
                else:
                    assert body['result'] is None
                save(folder / 'readback' / (run['id'] + '.json'), {'path': path, 'status': response.status_code, 'body': body})
                stage_readback.append({'run_id': run['id'], 'kind': run['kind'], 'state': run['state'],
                    'stop_reason': run['stop_reason'], 'adopted_current': body['is_current_pointer'],
                    'valid_for_current_input': body['valid_for_current_input'], 'database_http_match': True})
    finally:
        await engine.dispose()
    new_runs = {execution['run_id']}
    if (folder / 'I-execution.json').exists():
        new_runs.add(read(folder / 'I-execution.json')['run_id'])
    new_runs.update(read(path)['run_id'] for path in folder.glob('A*-execution.json'))
    models = []
    for step in sorted(data['run_steps'], key=lambda s: (s['run_id'], s['seq'])):
        if step['kind'] != 'model' or step['run_id'] not in new_runs:
            continue
        req = artifacts[step['input_artifact_id']]['content_json']; req = req.get('payload',req)
        res = artifacts[step['output_artifact_id']]['content_json']; res = res.get('payload',res)
        knowledge = {sid:s for sid,s in req.get('source_map',{}).items() if s.get('knowledge')}
        citations = []
        def scan(value, path):
            if isinstance(value, dict):
                for key, child in value.items(): scan(child, path+[key])
            elif isinstance(value, list):
                for i, child in enumerate(value): scan(child, path+[i])
            elif isinstance(value, str) and value in knowledge:
                citations.append({'path':path,'id':value,'ref':knowledge[value]['ref']})
        content = res.get('raw',{}).get('choices',[{}])[0].get('message',{}).get('content')
        if content:
            scan(json.loads(content), [])
        models.append({'run_id':step['run_id'],'stage':step['stage_code'],'seq':step['seq'],'state':step['state'],
            'validation_error':res.get('validation_error'),'usage':step['usage'],
            'is_correction':bool(req.get('correction')), 'knowledge_sources':len(knowledge),'knowledge_citations':citations})
    assert len(models) == sum(execution['model_calls'].values())
    summary = {'batch':config['batch'], 'stage_readback':stage_readback, 'real_model_calls':len(models),
        'tokens':sum(m['usage']['total_tokens'] for m in models),'models':models,
        'case': {'run_id':execution['run_id'],'run_state':runs[execution['run_id']]['state'],
            'stop_reason':runs[execution['run_id']]['stop_reason'],'result_id':result['id'],
            'validation_state':result['validation_state'],'delivery_state':result['delivery_state'],
            'conclusion':result['conclusion'],'conclusion_state':result['conclusion_state'],
            'conclusion_origin':result['conclusion_origin'],'current_assessment':current,
            'database_http_match':True},
        'quality':'NOT_PASSED', 'cost':'unknown', 'all_A_I_valid':all(s['valid_for_current_input'] for s in stage_readback)}
    save(folder / 'readback-verification.json', summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['models','case','stage_readback']},ensure_ascii=False))
    print(json.dumps({k:v for k,v in summary['case'].items() if k not in ['conclusion','current_assessment']},ensure_ascii=False))


asyncio.run(main())
