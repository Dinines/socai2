"""D4b directly consumes actual saved D4a receipts, never re-runs a receiver."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_incident_material import freeze, source_members
from app.socai2.case_update_inputs import business_view, unchanged

MOTHER = Path(__file__).resolve().parents[3] / 'docs/operations/evidence/ai-unit-continuation-d4-20261116-01/real-01/database.json'
RUNS = {'complete': '75255ae9-8159-5fa4-ae53-af5927e26523',
        'partial': '7ef7bceb-7c93-5894-bd0c-b0343334050b', 'none': '3d8b5a17-512d-563d-b34e-6250c3f1bf35'}


def candidate(kind='partial'):
    db = json.loads(MOTHER.read_text())
    rid = RUNS[kind]
    a = next(a for a in db['analysis_attempts'] if a['run_id'] == rid)
    fs = [f for f in db['artifacts'] if f['run_id'] == rid]
    receipt = next(f for f in fs if f['schema_version'] == 'socai2.stage-delivery.v1')
    return {'attempt': a, 'task': next(t for t in db['analysis_tasks'] if t['id'] == a['task_id']),
        'run': next(r for r in db['runs'] if r['id'] == rid),
        'input': next(f for f in fs if f['id'] == a['input_artifact_id']), 'receipt': receipt,
        'response': next(f for f in fs if f['kind'] == 'model_response'),
        'originals': [f for f in fs if f['id'] in {o['artifact_id'] for o in receipt['content_json']['originals']}]}


def material(c):
    return freeze(c['run']['incident_id'], c, [r['alert']['id'] for r in c['input']['content_json']['members']])


def rehash(f):
    f['sha256'], f['size_bytes'] = digest(f['content_json']), len(encoded(f['content_json']))


@pytest.mark.parametrize('kind', RUNS)
def test_saved_real_complete_partial_none_keep_actual_business(kind):
    c = candidate(kind)
    with patch('app.socai2.ai_stage_delivery.receive', side_effect=AssertionError('must not reparse old response')):
        value, reasons = material(c)
    assert value, reasons
    assert value['receipt'] == c['receipt']['content_json']
    assert value['receipt']['delivery']['state'] == kind
    assert len(value['units']) == (0 if kind == 'none' else 1 if kind == 'partial' else len(value['units']))
    assert value['business_view']['conclusion_available'] is (kind == 'complete')
    if kind == 'partial':
        assert value['units'][0]['value']['assessment'] == c['response']['content_json']['received_analysis']['members'][0]['assessment']
        assert len(value['units'][0]['scope']['alert_ids']) == 1
        assert source_members(value, '$.incidents.I.analysis_material.units.0.value', value['case_selected_alert_ids']) == value['units'][0]['scope']['alert_ids']


@pytest.mark.parametrize('bad', ['running', 'retry', 'task_end', 'input_hash', 'receipt_hash', 'response_hash', 'original_hash', 'tenant', 'input_id', 'input_digest'])
def test_unfinished_or_unverifiable_source_is_not_material(bad):
    c = candidate()
    if bad == 'running': c['attempt']['local_state'] = 'running'
    elif bad == 'retry': c['task'].update(state='waiting', ended_at=None, next_retry_at='later')
    elif bad == 'task_end': c['task']['ended_at'] = None
    elif bad.endswith('_hash'): (c['originals'][0] if bad == 'original_hash' else c[bad[:-5]])['sha256'] = '0'*64
    elif bad == 'tenant': c['response']['tenant_id'] = 'different'
    elif bad == 'input_id': c['run']['input_artifact_id'] = 'different'
    else: c['attempt']['input_digest'] = '0'*64
    value, reasons = material(c)
    assert value is None and reasons == ['incident_terminal_material_invalid']


def test_generated_identity_errors_aliases_do_not_change_business():
    c = candidate()
    old, reasons = material(c)
    assert old, reasons
    # A new task/Run/input/receipt ID with the same exact saved answer.
    new = copy.deepcopy(c)
    import uuid
    mapping = {new['run']['id']: str(uuid.uuid4()), new['task']['id']: str(uuid.uuid4()), new['attempt']['id']: str(uuid.uuid4())}
    mapping.update({f['id']: str(uuid.uuid4()) for f in [new['input'],new['receipt'],new['response'],*new['originals']]})
    text = json.dumps(new)
    for before, after in mapping.items(): text = text.replace(before, after)
    new = json.loads(text)
    for f in [new['input'],new['response'],*new['originals']]: rehash(f)
    for original in new['receipt']['content_json']['originals']:
        original['sha256'] = next(f['sha256'] for f in new['originals'] if f['id'] == original['artifact_id'])
    new['task']['reason_code'] = 'another_error'
    new['attempt']['error_code'] = 'another_error'
    rehash(new['receipt'])
    after, reasons = material(new)
    assert after, reasons
    assert after['business_view'] == old['business_view']
    assert after['source_run_id'] != old['source_run_id']


def context(m):
    return SimpleNamespace(update_context=None, alerts={}, tasks={}, incidents={'i': SimpleNamespace(
        analysis_material=m, diagnosis_usable=False, diagnosis_scope=None)})


def test_none_changes_once_for_new_input_but_not_error_metadata():
    m, _ = material(candidate('none'))
    old = context(m)
    assert unchanged(old, business_view(context(copy.deepcopy(m))), {'i'})
    new = copy.deepcopy(m)
    new['business_view']['input_digest'] = 'changed-input'
    assert not unchanged(old, business_view(context(new)), {'i'})
    assert unchanged(old, business_view(context(None)), {'i'})


def test_partial_prose_or_scope_change_detected():
    m, _ = material(candidate())
    old = context(m)
    new = copy.deepcopy(m)
    new['business_view']['content'][0]['value']['assessment'] += 'new conclusion'
    assert not unchanged(old, business_view(context(new)), {'i'})


def test_paired_triage_recommendation_reference_identity_is_not_business():
    from app.socai2.case_incident_material import semantic_ref
    source={'members':[{'alert':{'id':'a'},'triage':{'verdict':'needs_review','rationale':'reason',
        'confidence':None,'score_state':'not_scored','recommendations':[{'id':'R1','reason':'check',
        'source_refs':[{'type':'artifact','id':'old-run-input','role':'prior_analysis'}]}]}}]}
    ref={'source_id':'S1','alert_ids':['a'],'ref':{'type':'artifact','id':'input','role':'prior_analysis',
        'source_path':'$.members.0.triage','row_keys':[],'external':None}}
    before=semantic_ref(ref,source,'input',{})
    changed=copy.deepcopy(source)
    changed['members'][0]['triage']['recommendations'][0]['source_refs'][0]['id']='new-run-input'
    assert semantic_ref(ref,changed,'input',{})==before
    changed['members'][0]['triage']['recommendations'][0]['reason']='new business reason'
    assert semantic_ref(ref,changed,'input',{})!=before
