"""Bounded evaluation runner contracts; all model replies here are HTTP substitutes."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('verdict_live', ROOT / 'tools/testdata/verdict_live.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


@pytest.fixture
def batch(tmp_path, monkeypatch):
    monkeypatch.setattr(v.offline, 'LOCAL_ROOT', tmp_path)
    out = tmp_path / 'prepared'
    v.prepare(out, ['VRD-AWS-01', 'VRD-AWS-03'])
    return out


def test_two_complete_pairs_and_runtime_does_not_need_answers(batch):
    (batch / 'selection.json').unlink()
    manifest, rows = v.load_inputs(batch)
    assert len(rows) == 4
    assert manifest['anchor'] == '2026-10-07T00:00:00+00:00'
    assert all(set(row) == {'finding_id', *v.offline.VISIBLE} for row in rows)
    assert 'VRD-' not in (batch / 'inputs.json').read_text()


def test_bad_pair_or_modified_inputs_stop_before_execution(batch, tmp_path):
    with pytest.raises(ValueError):
        v.prepare(tmp_path / 'bad', ['VRD-AWS-01'])
    (batch / 'inputs.json').write_text('[]')
    with pytest.raises(ValueError, match='hash'):
        v.load_inputs(batch)


def test_unknown_usage_and_fallback_are_not_valid_model_scores():
    request = [{'index': 1}]
    reply = [{'index': 1, 'status': 200, 'body': {'usage': {'total_tokens': 17}, 'choices': [{'message': {
        'content': json.dumps({'verdict':'true_positive','confidence':0.9,'rationale':'supplied evidence'})}}]}}]
    assert v.classify_execution({'tier': 'llm'}, request, reply)['continue_allowed']
    assert not v.classify_execution({'tier': 'deterministic'}, request, reply)['continue_allowed']
    assert not v.classify_execution({'tier': 'llm'}, request, [])['continue_allowed']
    reply[0]['body']['usage'] = {}
    assert v.classify_execution({'tier': 'llm'}, request, reply)['tokens'] is None


def test_request_guard_checks_real_body_and_single_request(batch, tmp_path):
    _, rows = v.load_inputs(batch)
    observer = v.Observation(tmp_path, 'http://127.0.0.1:24951/v1/chat/completions', 'aisoc-triage', offline_mode=True)
    observer.current = rows[0]
    body = {'model': 'aisoc-triage', 'temperature': 0, 'max_tokens': 512,
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'user', 'content': rows[0]['title']}]}
    asyncio.run(observer.request(httpx.Request('POST', observer.endpoint, json=body)))
    with pytest.raises(RuntimeError, match='limit'):
        asyncio.run(observer.request(httpx.Request('POST', observer.endpoint, json=body)))
    observer.current = rows[1]
    body['messages'][0]['content'] = rows[1]['title'] + ' expected_disposition'
    with pytest.raises(RuntimeError, match='isolation'):
        asyncio.run(observer.request(httpx.Request('POST', observer.endpoint, json=body)))


def test_explicit_environment_drops_business_connections(tmp_path, monkeypatch):
    # configure intentionally replaces the process environment; restore it afterward.
    original = dict(os.environ)
    try:
        env = tmp_path / 'model.env'
        env.write_text('OPENAI_API_KEY=test-not-a-real-key\nDATABASE_URL=postgres://forbidden\nAISOC_TRIAGE_ADMISSION_PROFILE=legacy\n')
        env.chmod(0o600)
        result = v.configure(env, 'http://127.0.0.1:24951')
        assert not result['database_configured']
        assert 'DATABASE_URL' not in os.environ and 'KAFKA_BOOTSTRAP_SERVERS' not in os.environ
        assert os.environ['AISOC_LLM_RESPONSE_CACHE'] == '0'
        with pytest.raises(ValueError):
            v.configure(env, 'http://192.0.2.1:4000')
    finally:
        os.environ.clear()
        os.environ.update(original)


def test_incomplete_evidence_stops_before_real_transport(batch, tmp_path):
    _, rows = v.load_inputs(batch)
    observer = v.Observation(tmp_path, 'http://127.0.0.1:24951/chat/completions', 'aisoc-triage')
    observer.current = rows[0]
    body = {'model': 'aisoc-triage', 'temperature': 0, 'max_tokens': 512,
            'response_format': {'type': 'json_object'}, 'messages': [{'role': 'user', 'content': rows[0]['title']}]}
    with pytest.raises(RuntimeError, match='evidence incomplete'):
        asyncio.run(observer.request(httpx.Request('POST', observer.endpoint, json=body)))
    assert not observer.requests and len(observer.blocked) == 1
    assert not json.loads((tmp_path / 'blocked-request-01.json').read_text())['sent']


def test_complete_leaf_lines_are_recognized_and_truncation_is_not():
    evidence = {'flag': True, 'missing': None, 'items': ['a', 'b'], 'num': 9}
    text = 'raw_event.flag: true\nraw_event.missing: (null)\nraw_event.items[0]: a\nraw_event.items[1]: b\nraw_event.num: 9'
    assert v.evidence_visibility(evidence, text)['complete']
    assert v.evidence_visibility(evidence, text[:-1])['missing_or_changed_paths'] == ['raw_event.num']


def test_rehashing_changed_evidence_cannot_relabel_it_as_the_fixed_corpus(batch):
    path = batch / 'inputs.json'
    rows = json.loads(path.read_text())
    rows[0]['evidence']['injected'] = 'new unsupported input'
    path.write_bytes(v.offline.encoded(rows))
    manifest = json.loads((batch / 'manifest.json').read_text())
    manifest['inputs_sha256'] = v.offline.digest(path.read_bytes())
    (batch / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='pinned visible'):
        v.load_inputs(batch)


@pytest.mark.parametrize('response_mode', ['valid', 'malformed', 'unavailable', 'unknown_usage', 'null_usage', 'unknown_verdict'])
def test_original_replay_through_observed_http_without_business_writes(batch, tmp_path, response_mode):
    code = r'''
import asyncio, json, os, socket, sys
from pathlib import Path
root, batch, out = map(Path, sys.argv[1:4])
mode = sys.argv[4]
sys.path.insert(0, str(root/'tools/testdata'))
import verdict_live as v
env = out.parent/'model.env'
env.write_text('OPENAI_API_KEY=offline-test-key\nAISOC_TRIAGE_ADMISSION_PROFILE=legacy\n')
env.chmod(0o600)
v.configure(env, 'http://127.0.0.1:24951')
os.chdir(out)
sys.path.insert(0, str(root/'services/agents'))
import httpx
from app.investigator import ledger, siem_writeback
from app.memory import outcomes
class Wrote(BaseException): pass
async def forbidden(*args, **kwargs): raise Wrote('business write or DB pool')
for module, names in [(ledger, ['persist_auto_triage','raise_approval','record_suppression']),
                      (outcomes,['record_outcome']), (siem_writeback,['write_back_disposition'])]:
    for name in names:setattr(module,name,forbidden)
def denied(*args, **kwargs):raise Wrote('network outside mock model')
socket.socket.connect = denied
async def handler(request):
    if mode == 'unavailable':return httpx.Response(503,json={'error':{'message':'offline simulated unavailable'}})
    content = 'not json' if mode == 'malformed' else json.dumps({'verdict':'true_positive','confidence':0.9,'rationale':'The supplied actions indicate malicious activity.'})
    if mode == 'unknown_verdict':content=json.dumps({'verdict':'nonsense','confidence':0.9,'rationale':'Invalid original classification'})
    reply = {'id':'offline-reply','object':'chat.completion','created':1,'model':'aisoc-triage',
             'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':content}}]}
    if mode != 'unknown_usage':reply['usage']={'prompt_tokens':2000,'completion_tokens':50,'total_tokens':2050}
    if mode == 'null_usage':reply['usage']=None
    return httpx.Response(200,json=reply)
summary = asyncio.run(v.run(batch,out,'http://127.0.0.1:24951',test_transport=httpx.MockTransport(handler)))
assert len(list(out.glob('request-*.json'))) == summary['http_requests']
print('RESULT='+json.dumps(summary))
'''
    out = tmp_path / response_mode
    out.mkdir()
    result = subprocess.run([sys.executable, '-c', code, str(ROOT), str(batch), str(out), response_mode],
                            capture_output=True, text=True, timeout=60,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode == 0, result.stderr[-4000:]
    summary = json.loads(next(line[7:] for line in result.stdout.splitlines() if line.startswith('RESULT=')))
    if response_mode == 'valid':
        assert summary['completed'] == summary['http_requests'] == summary['http_responses'] == 4
        assert summary['known_tokens'] == 8200 and summary['stop_reason'] is None
        assert all(item['model_result_adopted'] for item in summary['execution'])
    else:
        assert summary['completed'] == summary['http_requests'] == 1
        assert summary['stop_reason'] == 'response_usage_or_adoption_unconfirmed'
    assert summary['overall_accuracy_publishable'] is False
    assert summary['source_mode'] == 'offline_http_stub' and summary['new_model_requests'] == 0
    assert not summary['ready_for_live']
    if response_mode == 'unknown_verdict':
        assert summary['execution'][0]['raw_output_verdict'] == 'nonsense'
        assert summary['execution'][0]['program_verdict'] == 'true_positive'
        assert summary['execution'][0]['raw_output_valid'] is False
