"""Rebuild rejected real k2 C6 inputs from frozen exports; no external calls."""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from app.socai2 import baseline_delivery_contract as contract
from app.socai2 import baseline_reanalysis as reanalysis
from app.socai2.baseline_context import Context
from app.socai2.baseline_evidence import BaselineEvidence
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_reasoning import bounded_input
from app.socai2.baseline_store import digest, encoded

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2/20261105T001341-export'


async def one(data, run):
    rows = [r for r in data['artifacts'] if r['run_id'] == run['id'] and isinstance(r['content_json'], dict)]
    assert all(digest(r['content_json']) == r['sha256'] for r in rows)
    by_id = {r['id']: r for r in rows}
    context = Context.model_validate(next(r['content_json'] for r in rows if r['schema_version'] == 'socai2.baseline-context.v1'))
    view = next(r for r in rows if r['schema_version'] == 'socai2.baseline-model-view.v4')
    dispatch = next(r['content_json'] for r in rows if r['content_json'].get('type') == 'followup_dispatch')
    initial_id = dispatch['initial_analysis_artifact_id']
    previous = by_id[initial_id]['content_json']
    current = [r for r in rows if r['content_json'].get('type') == 'model_view'
               and r['content_json']['question_id'] == context.questions[0].id][-1]
    bases = sorted([r for r in rows if r['content_json'].get('type') in
        {'materials', 'query_projection', 'deep_summary', 'graph_snapshot'}], key=lambda r: r['id'])
    tools = [r for r in rows if r['kind'] == 'tool_response']
    report = next(r['content_json'] for r in rows if r['content_json'].get('type') == 'delivery_report')

    class Store:
        db = None
        def where(self, *_):
            return []
        async def execute(self, _):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: tools))
        async def prepare_model_view(self, *_):
            return {'artifact_id': view['id'], **view['content_json']}
    @asynccontextmanager
    async def transaction(*_):
        store = Store()
        store.db = store
        yield store
    async def model_view(*_):
        return {'artifact_id': current['id'], **current['content_json']}
    async def read_artifact(_self, _store, _run_id, identity):
        return by_id[str(identity)]['content_json']
    captured = {}
    def capture(meta, candidates, instruction):
        captured.update(data=copy.deepcopy(meta), candidates=copy.deepcopy(candidates), instruction=instruction)
        return bounded_input(meta, candidates, instruction)
    meta, planned = delivery_followups(dispatch, previous)
    # k2 comparisons are initial/unavailable, thus no prior valid conclusion candidate.
    assert report['comparison']['state'] in {'initial', 'unavailable', 'not_selected'}
    with patch.object(BaselineEvidence, 'model_view', model_view), patch.object(reanalysis.BaselineReanalysis, 'read_artifact', read_artifact), patch.object(reanalysis, 'bounded_input', capture):
        prepared = await reanalysis.BaselineReanalysis(SimpleNamespace(transaction=transaction)).input(
            UUID(run['tenant_id']), UUID(run['case_id']), UUID(run['id']), context, previous, initial_id, bases,
            instruction=contract.PROMPT,
            extra_data={'round': 'final_delivery', 'comparison': report['comparison'], 'followup_execution': meta},
            lead_candidates=planned, executed_plan_id=initial_id)
    required = [c for c in captured['candidates'] if c.get('required')]
    omitted = {encoded(o['ref']): o['reason'] for o in prepared['omissions']}
    result = {'run_id': run['id'], 'reason': prepared['reason'], 'bytes': prepared['bytes'],
        'required_count': len(required), 'required': [{'ref': c['source']['ref'],
            'value_bytes': len(encoded(c['entry']['value'])), 'entry_bytes': len(encoded(c['entry'])),
            'omitted': omitted.get(encoded(c['source']['ref']))} for c in required],
        'captured': captured, 'prepared': prepared}
    return result


async def main():
    data = json.loads(max(DIRECTORY.glob('database-*.json')).read_text('utf-8'))
    results = [await one(data, r) for r in data['runs'] if r['stop_reason'] == 'required_model_input_unavailable']
    out = DIRECTORY / 'c6-input-diagnosis.json'
    assert not out.exists()
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str) + '\n', 'utf-8')
    for r in results:
        print(json.dumps({k: v for k, v in r.items() if k not in {'captured', 'prepared'}}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
