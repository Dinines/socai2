"""Offline data/score contracts, no model or infrastructure access."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket

import pytest

spec = importlib.util.spec_from_file_location('verdict_eval', Path(__file__).parents[1] / 'verdict_eval.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(v, 'LOCAL_ROOT', tmp_path)
    path = tmp_path / 'batch'
    v.prepare(path)
    return path


def test_catalog_counts_distinguish_templates_cases_and_verdicts():
    data = v.catalog()
    assert (data['synthetic_templates'], data['synthetic_cases'], data['synthetic_telemetry']) == (55, 200, 361)
    assert (data['verdict_cases'], data['verdict_pairs']) == (72, 36)
    assert data['execution'] == 'not_started'


def test_visible_inputs_have_no_answer_fields_or_source_ids(prepared):
    manifest, inputs, answers = v.load_prepared(prepared)
    assert manifest['count'] == len(inputs) == len(answers) == 72
    assert len({row['finding_id'] for row in inputs}) == 72
    assert all(set(row) == {'finding_id', *v.VISIBLE} for row in inputs)
    text = json.dumps(inputs)
    assert all(item['corpus_id'] not in text and item['pair_id'] not in text for item in answers)
    for field in v.corpus()['held_out_from_the_model']:
        assert field not in text


def test_preparation_is_stable_private_and_refuses_overwrite(prepared):
    other = prepared.parent / 'second'
    v.prepare(other)
    for name in ('manifest.json', 'inputs.json', 'answer-key.json'):
        assert (prepared / name).read_bytes() == (other / name).read_bytes()
        assert (prepared / name).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        v.prepare(prepared)


def test_answer_tampering_is_not_accepted_even_with_rehashed_manifest(prepared):
    path = prepared / 'answer-key.json'
    rows = json.loads(path.read_text()); rows[0]['expected_disposition'] = 'false_positive'
    path.write_bytes(v.encoded(rows))
    manifest = json.loads((prepared / 'manifest.json').read_text())
    manifest['files']['answer-key.json'] = v.digest(path.read_bytes())
    (prepared / 'manifest.json').write_bytes(v.encoded(manifest))
    with pytest.raises(ValueError):
        v.load_prepared(prepared)


def test_inputs_cannot_be_silently_replaced(prepared):
    (prepared / 'inputs.json').write_text('[]')
    with pytest.raises(ValueError, match='hash mismatch'):
        v.load_prepared(prepared)


def test_output_outside_local_and_changed_corpus_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(v, 'LOCAL_ROOT', tmp_path / 'local')
    with pytest.raises(ValueError, match='.local'):
        v.prepare(tmp_path / 'public')
    p = tmp_path / 'corpus.json'; p.write_text('{}')
    monkeypatch.setattr(v, 'CORPUS', p)
    with pytest.raises(ValueError, match='pinned'):
        v.corpus()


def observations(prepared):
    _, _, answers = v.load_prepared(prepared)
    return [{'finding_id': item['finding_id'], 'verdict': 'true_positive', 'confidence': 0.95}
            for item in answers]


def test_constant_prediction_cannot_appear_accurate(prepared):
    result = v.score(prepared, observations(prepared), threshold=0.85)
    assert result['metrics']['headline_accuracy'] == 0.5
    assert result['metrics']['balanced_accuracy'] == 0.25
    assert result['metrics']['total_tokens'] is None and result['metrics']['llm_calls'] is None
    assert result['metrics']['hallucination_rate'] is None
    assert not result['model_execution_verified'] and not result['can_publish_model_performance']


def test_classification_metrics_reuse_existing_scorer(prepared):
    result = v.score(prepared, observations(prepared), threshold=0.85)
    expected = v.existing_scorer()[0].score_replay(result['decisions'], auto_close_threshold=0.85).as_dict()
    for field in ('confusion', 'per_class', 'balanced_accuracy', 'headline_accuracy', 'auto_close_precision'):
        assert result['metrics'][field] == expected[field]


def test_error_abstention_unknown_and_missing_are_distinct(prepared):
    rows = observations(prepared)
    rows[0]['error'] = 'provider_failed'
    rows[1]['verdict'] = 'needs_review'
    rows[2]['verdict'] = 'unrecognised_output'
    result = v.score(prepared, rows[:-1], threshold=0.85)
    assert (result['observed'], result['missing'], result['observed_errors']) == (71, 1, 1)
    assert result['metrics']['errored'] == 1
    assert result['metrics']['abstained'] == 1
    assert result['decisions'][2]['verdict'] == 'unrecognised_output'
    assert result['metrics']['headline_accuracy'] is None
    empty = v.score(prepared, [], threshold=0.85)
    assert empty['metrics'] is None and empty['missing'] == 72


def test_aliases_use_product_taxonomy_without_defaulting_to_tp(prepared):
    rows = observations(prepared)
    rows[0]['verdict'] = 'btp'
    rows[1]['verdict'] = 'likely_benign'
    rows[2]['verdict'] = None
    result = v.score(prepared, rows, threshold=0.85)
    assert [r['verdict'] for r in result['decisions'][:3]] == ['benign_true_positive', 'benign', '']


@pytest.mark.parametrize('mutation', ['duplicate', 'extra', 'answer', 'bad-confidence', 'bad-usage'])
def test_invalid_observations_are_rejected(prepared, mutation):
    rows = observations(prepared)
    if mutation == 'duplicate': rows.append(rows[0])
    elif mutation == 'extra': rows[0]['finding_id'] = 'unknown'
    elif mutation == 'answer': rows[0]['expected_disposition'] = 'benign'
    elif mutation == 'bad-confidence': rows[0]['confidence'] = float('nan')
    else: rows[0]['tokens'] = -1
    with pytest.raises(ValueError):
        v.score(prepared, rows, threshold=0.85)


def test_explicit_threshold_changes_only_candidate_scoring(prepared):
    rows = observations(prepared)
    rows[0].update(verdict='benign', confidence=0.87)
    low = v.score(prepared, rows, threshold=0.85)
    high = v.score(prepared, rows, threshold=0.9)
    assert low['metrics']['auto_close_considered'] == 1
    assert high['metrics']['auto_close_considered'] == 0
    assert low['metrics']['confusion'] == high['metrics']['confusion']


def test_offline_score_does_not_connect_or_change_model_configuration(prepared, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline grading attempted network access')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setenv('AISOC_MODEL_TRIAGE', 'keep-triage')
    before = dict(os.environ)
    v.score(prepared, observations(prepared), threshold=0.85)
    assert dict(os.environ) == before


def test_partial_cost_observations_cannot_be_reported_as_zero_total(prepared):
    rows = observations(prepared)
    rows[0].update(measured_usd=0, estimated_usd=0.1)
    result = v.score(prepared, rows, threshold=0.85)
    for field in ('measured_usd', 'estimated_usd'):
        assert result['unknown_telemetry_records'][field] == 71
        assert result['metrics'][field] is None
    for row in rows:
        row.update(measured_usd=0, estimated_usd=0)
    complete = v.score(prepared, rows, threshold=0.85)
    assert complete['metrics']['measured_usd'] == complete['metrics']['estimated_usd'] == 0
