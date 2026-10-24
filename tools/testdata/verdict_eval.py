#!/usr/bin/env python3
"""Offline bridge for the pinned verdict corpus; never runs agents or sends data."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from typing import Any
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = ROOT / '.local'
CORPUS = ROOT / 'services/agents/tests/eval_data/verdict/verdict_corpus_v1.json'
CORPUS_SHA256 = 'ec60d7bddabcc5b28d8942cea52d770bd8a2d13b93396826a6deab1dcba6aa86'
# Same namespace as the original run_verdict_eval.py; original IDs never enter input.
OPAQUE_NS = UUID('6f1d0a1e-9c3b-4f6a-8d2e-7b5c4a3f1e20')
VISIBLE = ('title', 'severity', 'vendor', 'rule_id', 'evidence')
LABELS = {'true_positive', 'benign_true_positive', 'false_positive', 'benign'}


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def corpus() -> dict[str, Any]:
    data = CORPUS.read_bytes()
    if digest(data) != CORPUS_SHA256:
        raise ValueError('pinned verdict corpus differs; review a new corpus version first')
    return json.loads(data)


def catalog() -> dict[str, Any]:
    cases = json.loads((ROOT / 'services/agents/tests/eval_data/synthetic_incidents.json').read_text())
    items = corpus()['decisions']
    return {'synthetic_templates': len({c['template_id'] for c in cases}),
            'synthetic_cases': len(cases), 'synthetic_telemetry': sum(len(c['telemetry']) for c in cases),
            'verdict_cases': len(items), 'verdict_pairs': len({c['pair_id'] for c in items}),
            'verdict_labels': dict(Counter(c['expected_disposition'] for c in items)),
            'verdict_corpus_sha256': CORPUS_SHA256, 'provenance': 'hand-authored synthetic',
            'execution': 'not_started', 'tool_query_success': 'not_measured'}


def materialize() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inputs, answers = [], []
    for item in corpus()['decisions']:
        opaque = str(uuid5(OPAQUE_NS, item['id']))
        inputs.append({'finding_id': opaque, **{k: item[k] for k in VISIBLE}})
        answers.append({'finding_id': opaque, 'corpus_id': item['id'], 'pair_id': item['pair_id'],
                        'expected_disposition': item['expected_disposition']})
    # Do not preserve the source's alternating B/M ordering as an implicit answer key.
    return sorted(inputs, key=lambda x: x['finding_id']), sorted(answers, key=lambda x: x['finding_id'])


def private_path(path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(LOCAL_ROOT.resolve()) or path == LOCAL_ROOT.resolve():
        raise ValueError('generated material must be inside this checkout .local/')
    return path


def write_new(path: Path, value: Any) -> None:
    data = encoded(value)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def prepare(out: Path) -> dict[str, Any]:
    out = private_path(out)
    inputs, answers = materialize()
    manifest = {'schema_version': 'socai2-verdict-eval/v1', 'corpus_sha256': CORPUS_SHA256,
                'count': len(inputs), 'execution': 'not_started',
                'files': {'inputs.json': digest(encoded(inputs)), 'answer-key.json': digest(encoded(answers))}}
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_new(out / 'inputs.json', inputs)
    write_new(out / 'answer-key.json', answers)
    # Manifest last: a partial write cannot be mistaken for a completed preparation.
    write_new(out / 'manifest.json', manifest)
    return manifest


def load_prepared(directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = json.loads((directory / 'manifest.json').read_text())
    inputs, answers = materialize()
    expected_files = {'inputs.json': digest(encoded(inputs)), 'answer-key.json': digest(encoded(answers))}
    if (manifest.get('schema_version') != 'socai2-verdict-eval/v1'
            or manifest.get('corpus_sha256') != CORPUS_SHA256 or manifest.get('count') != len(inputs)
            or manifest.get('files') != expected_files):
        raise ValueError('prepared manifest does not match the pinned corpus')
    for name, sha in expected_files.items():
        if digest((directory / name).read_bytes()) != sha:
            raise ValueError(f'prepared file hash mismatch: {name}')
    return manifest, inputs, answers


def existing_scorer():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    scorer = importlib.import_module('services.api.app._vendor.aisoc_benchmark.replay')
    # The agents package __init__ imports the live runtime. Load only its pure taxonomy.
    spec = importlib.util.spec_from_file_location('socai2_eval_dispositions',
                                                ROOT / 'services/agents/app/agents/dispositions.py')
    dispositions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dispositions)
    return scorer, dispositions.normalize_disposition


def score(directory: Path, observations: list[dict[str, Any]], *, threshold: float) -> dict[str, Any]:
    """Recalculate imported results, without certifying their model provenance."""
    manifest, inputs, answers = load_prepared(directory)
    if isinstance(threshold, bool) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('auto-close threshold must be a finite value in [0,1]')
    if not isinstance(observations, list):
        raise ValueError('observations must be a JSON list')
    expected = {row['finding_id']: row for row in answers}
    visible = {row['finding_id']: row for row in inputs}
    seen, decisions = set(), []
    scorer, normalize = existing_scorer()
    allowed = {'finding_id', 'verdict', 'verdict_raw', 'confidence', 'error', 'findings',
               'confidence_basis', 'tier', 'llm_calls', 'tokens', 'resolved_models',
               'measured_usd', 'estimated_usd', 'unpriced_calls', 'latency_ms', 'tool_calls'}
    for record in observations:
        if not isinstance(record, dict) or set(record) - allowed:
            raise ValueError('unexpected observation fields; answer/evidence overrides are forbidden')
        key = record.get('finding_id')
        if key not in expected or key in seen:
            raise ValueError('unknown or duplicate observation ID')
        seen.add(key)
        raw = record.get('verdict')
        if raw is not None and not isinstance(raw, str):
            raise ValueError('verdict must be text or null')
        confidence = record.get('confidence')
        if (isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                or not math.isfinite(confidence) or not 0 <= confidence <= 1):
            raise ValueError('each observation needs an explicit confidence in [0,1]')
        for field in ('findings', 'confidence_basis', 'resolved_models'):
            if field in record and (not isinstance(record[field], list)
                                    or not all(isinstance(v, str) for v in record[field])):
                raise ValueError(f'{field} must be a list of strings')
        for field in ('error', 'tier', 'verdict_raw'):
            if record.get(field) is not None and not isinstance(record[field], str):
                raise ValueError(f'{field} must be text or null')
        for field in ('llm_calls', 'tokens', 'unpriced_calls', 'tool_calls'):
            if record.get(field) is not None and (type(record[field]) is not int or record[field] < 0):
                raise ValueError(f'{field} must be a nonnegative integer or null')
        for field in ('latency_ms', 'measured_usd', 'estimated_usd'):
            value = record.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not math.isfinite(value) or value < 0):
                raise ValueError(f'{field} must be a nonnegative finite number or null')
        item = visible[key]
        decisions.append({**record, 'verdict_raw': record.get('verdict_raw', raw),
                          # Unknown nonempty strings remain wrong/unknown predictions; never default TP.
                          'verdict': normalize(raw, default='') or (raw.strip() if raw else ''),
                          'expected_disposition': expected[key]['expected_disposition'], 'labelled': True,
                          'vendor': item['vendor'], 'rule_id': item['rule_id'], 'evidence': item['evidence']})
    counts = Counter(row['expected_disposition'] for row in decisions if not row.get('error'))
    reason = None
    if not decisions:
        reason = 'no observations; missing records are not abstentions'
    elif len(counts) < 2 or min(counts.values()) / sum(counts.values()) < 0.05:
        reason = 'observed usable labels lack at least two classes with a 5% minority'
    metrics = scorer.score_replay(decisions, auto_close_threshold=threshold).as_dict() if reason is None else None
    unknown = {field: sum(record.get(field) is None for record in observations)
               for field in ('tokens', 'llm_calls', 'latency_ms', 'unpriced_calls', 'measured_usd', 'estimated_usd')}
    # Preserve classification formulas, but do not turn absent telemetry into upstream default zero.
    if metrics is not None:
        for source, targets in {
            'tokens': ('total_tokens',), 'llm_calls': ('llm_calls',), 'unpriced_calls': ('unpriced_calls',),
            'measured_usd': ('measured_usd',), 'estimated_usd': ('estimated_usd',),
            'latency_ms': ('mean_latency_ms', 'p95_latency_ms', 'time_to_verdict_p50_ms', 'time_to_verdict_p95_ms'),
        }.items():
            if unknown[source]:
                for target in targets:
                    metrics[target] = None
        # Prepared evidence is not proof of the actual prompt; defer this axis until trace verification.
        for field in ('hallucination_rate', 'hallucinated_total', 'indicators_checked'):
            metrics[field] = None
        metrics['hallucinated_examples'] = []
        if len(seen) < len(expected):
            metrics['headline_accuracy'] = metrics['headline_accuracy_ci'] = None
            metrics['headline_withheld_reason'] = 'incomplete batch; see observed coverage and per-class support'
    return {'schema_version': 'socai2-verdict-score/v1', 'corpus_sha256': manifest['corpus_sha256'],
            'observations_sha256': digest(encoded(observations)), 'source_mode': 'offline_import',
            'model_execution_verified': False, 'can_publish_model_performance': False,
            'expected': len(expected), 'observed': len(seen), 'missing': len(expected) - len(seen),
            'missing_ids': sorted(set(expected) - seen), 'complete_batch': len(expected) == len(seen),
            'observed_errors': sum(bool(row.get('error')) for row in decisions),
            'auto_close_threshold': threshold, 'unknown_telemetry_records': unknown,
            'metrics': metrics, 'unmeasured_reason': reason,
            'scorer_sha256': digest(Path(scorer.__file__).read_bytes()),
            'decisions': decisions,
            'limitations': ['Imported results are not proof that a model ran or saw prepared inputs.',
                            'Auto-close precision is exact four-class agreement among threshold candidates, not executed closure safety.',
                            'Missing records, errors, and abstentions are distinct; no score certifies tool use.',
                            'Hallucination/semantic evidence support is unmeasured until actual input is verified.']}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('catalog')
    command = sub.add_parser('prepare')
    command.add_argument('--out', required=True, type=Path)
    command = sub.add_parser('score')
    command.add_argument('--prepared', required=True, type=Path)
    command.add_argument('--observations', required=True, type=Path)
    command.add_argument('--auto-close-threshold', required=True, type=float)
    command.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'catalog':
        result = catalog()
    elif args.command == 'prepare':
        result = prepare(args.out)
    else:
        result = score(args.prepared, json.loads(args.observations.read_text()), threshold=args.auto_close_threshold)
        out = private_path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_new(out, result)
        result = {key: result[key] for key in ('source_mode', 'expected', 'observed', 'missing', 'complete_batch')}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
