#!/usr/bin/env python3
"""Small given-evidence Replay evaluation; answers are read only by prepare/scoring."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
from unittest.mock import patch
from urllib.parse import urlsplit
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verdict_eval as offline

ROOT = offline.ROOT
REQUEST_LIMIT = 4
TOKEN_STOP = 20000  # Observed-use stop between requests, not a hard token cap.
VISIBLE_INPUTS_SHA256 = 'bb7a3a56ebca03f651e9dc8bc64342b59d32c41e210d19d14b29ac94aa014795'
HELD_OUT = ('expected_disposition', 'decisive_evidence', 'pair_id', 'vendor_disposition', 'label_rationale')


def prepare(out: Path, pairs: list[str]) -> dict:
    if len(pairs) != 2 or len(set(pairs)) != 2:
        raise ValueError('Select exactly two distinct complete pairs')
    corpus = offline.corpus()
    inputs, answers = offline.materialize()
    selected = [row for row in answers if row['pair_id'] in pairs]
    if len(selected) != REQUEST_LIMIT or any(sum(r['pair_id'] == p for r in selected) != 2 for p in pairs):
        raise ValueError('Each selected pair must contain exactly two cases')
    # Each pair is adjacent for checkpointing; within a pair use opaque ordering.
    ids = [row['finding_id'] for p in pairs for row in selected if row['pair_id'] == p]
    by_id = {row['finding_id']: row for row in inputs}
    visible = [by_id[key] for key in ids]
    out = offline.private_path(out)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    offline.write_new(out / 'inputs.json', visible)
    offline.write_new(out / 'source-inputs.json', inputs)  # Visible fields only, no answer file dependency.
    offline.write_new(out / 'selection.json', selected)
    anchor = corpus.get('authored_at') or corpus.get('created_at')
    if not anchor:
        raise ValueError('Corpus must have an explicit authored anchor')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', anchor):
        anchor += 'T00:00:00+00:00'  # Explicit corpus-day anchor, never an event timestamp.
    manifest = {'schema_version': 'socai2-verdict-live/v1', 'corpus_sha256': offline.CORPUS_SHA256,
                'inputs_sha256': offline.digest(offline.encoded(visible)), 'finding_ids': ids,
                'count': len(visible), 'anchor': anchor, 'anchor_kind': 'corpus_authored_not_event_time',
                'request_limit': REQUEST_LIMIT, 'known_tokens_stop': TOKEN_STOP}
    offline.write_new(out / 'manifest.json', manifest)
    return manifest


def load_inputs(directory: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((directory / 'manifest.json').read_text())
    raw = (directory / 'inputs.json').read_bytes()
    rows = json.loads(raw)
    source = (directory / 'source-inputs.json').read_bytes()
    if offline.digest(source) != VISIBLE_INPUTS_SHA256:
        raise ValueError('Pinned visible corpus differs')
    trusted = {row['finding_id']: row for row in json.loads(source)}
    if manifest.get('corpus_sha256') != offline.CORPUS_SHA256 or offline.digest(raw) != manifest['inputs_sha256']:
        raise ValueError('Input/corpus hash mismatch')
    if len(rows) != REQUEST_LIMIT or len({r['finding_id'] for r in rows}) != REQUEST_LIMIT:
        raise ValueError('Expected exactly four distinct opaque inputs')
    if [r['finding_id'] for r in rows] != manifest['finding_ids']:
        raise ValueError('Input order/identity differs')
    for row in rows:
        UUID(row['finding_id'])
        if row != trusted.get(row['finding_id']):
            raise ValueError('Selected input differs from pinned visible corpus')
        if set(row) != {'finding_id', *offline.VISIBLE} or not isinstance(row['evidence'], dict):
            raise ValueError('Only original visible fields are allowed')
        if any(key in json.dumps(row) for key in HELD_OUT) or re.search(r'VRD-[A-Z]+-\d+(?:-[BM])?', json.dumps(row)):
            raise ValueError('Held-out data in visible inputs')
    return manifest, rows


def configure(env_file: Path, gateway: str) -> dict:
    if env_file.stat().st_mode & 0o077:
        raise ValueError('Model environment must be a private file')
    from dotenv import dotenv_values
    values = dotenv_values(env_file, interpolate=False)
    route = urlsplit(gateway)
    if route.scheme != 'http' or route.hostname != '127.0.0.1' or not route.port or route.username or route.password or route.query or route.fragment:
        raise ValueError('Use an explicit loopback SSH model gateway')
    if route.path not in ('', '/v1'):
        raise ValueError('Unexpected gateway base path')
    if values.get('AISOC_TRIAGE_ADMISSION_PROFILE', 'legacy') != 'legacy':
        raise ValueError('This Replay requires the existing legacy profile; do not bypass review-only')
    keep = {'OPENAI_API_KEY', 'LLM_GATEWAY_API_KEY', 'LLM_GATEWAY_MASTER_KEY', 'OPENAI_MODEL',
            'AISOC_AIRGAPPED', 'AISOC_AUTO_CLOSE_THRESHOLD', 'AISOC_TRIAGE_ADMISSION_PROFILE',
            'AISOC_AGENT_GROUNDEDNESS_FLOOR', 'AISOC_AGENT_GROUNDEDNESS_GATE'}
    selected = {k: v for k, v in values.items() if k in keep or k.startswith('AISOC_MODEL_PIN_')}
    if any(v is None or '${' in v for v in selected.values()):
        raise ValueError('Unresolved model settings')
    if not any(selected.get(k) for k in ('OPENAI_API_KEY', 'LLM_GATEWAY_API_KEY', 'LLM_GATEWAY_MASTER_KEY')):
        raise ValueError('Explicit model credentials required')
    essentials = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL'}}
    os.environ.clear()
    os.environ.update(essentials)
    os.environ.update(selected)
    os.environ.update(LLM_GATEWAY_URL=gateway, OPENAI_BASE_URL=gateway, AISOC_DETERMINISTIC='0',
                      AISOC_LLM_RESPONSE_CACHE='0', OTEL_SDK_DISABLED='true', PYTHONDONTWRITEBYTECODE='1')
    sys.dont_write_bytecode = True
    return {'gateway': gateway, 'model_env_sha256': offline.digest(env_file.read_bytes()),
            'role_pins': {k: v for k, v in selected.items() if k.startswith('AISOC_MODEL_PIN_')},
            'database_configured': False, 'external_context': 'excluded_not_queried',
            'response_cache': False, 'sdk_retry': 0, 'sdk_timeout_seconds': 45}


def evidence_visibility(evidence: dict, user_text: str) -> dict:
    """Conservative check against the current line-oriented production serializer."""
    expected = []
    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, f'{path}.{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f'{path}[{index}]')
        else:
            text = '(null)' if value is None else str(value).lower() if isinstance(value, bool) else str(value).replace('\r', ' ').replace('\n', ' ')
            expected.append((path, f'{path}: {text}'))
    visit(evidence, 'raw_event')
    actual_lines = set(user_text.splitlines())
    missing = [path for path, line in expected if line not in actual_lines]
    return {'expected_leaves': len(expected), 'visible_leaves': len(expected) - len(missing),
            'missing_or_changed_paths': missing, 'complete': not missing,
            'scope': 'exact current serializer leaf lines; not semantic evidence correctness'}


class Observation:
    def __init__(self, out: Path, endpoint: str, model: str, *, offline_mode=False):
        self.out, self.endpoint, self.model = out, endpoint, model
        self.offline_mode = offline_mode
        self.current = None
        self.requests, self.responses, self.blocked = [], [], []

    async def request(self, request):
        body = json.loads(await request.aread())
        row = self.current
        if row is None or request.method != 'POST' or str(request.url) != self.endpoint:
            raise RuntimeError('Unexpected model route')
        if len(self.requests) >= REQUEST_LIMIT or any(r['finding_id'] == row['finding_id'] for r in self.requests):
            raise RuntimeError('Evaluation request limit reached; no retries')
        users = '\n'.join(str(m.get('content', '')) for m in body.get('messages', []) if m.get('role') == 'user')
        if (any(k in users for k in HELD_OUT) or re.search(r'VRD-[A-Z]+-\d+(?:-[BM])?', users)
                or row['title'] not in users):
            raise RuntimeError('Actual model input failed isolation check')
        if body.get('model') != self.model or body.get('temperature') != 0 or body.get('max_tokens', body.get('max_completion_tokens')) != 512:
            raise RuntimeError('Original triage role/parameters changed')
        if body.get('response_format') != {'type': 'json_object'} or body.get('tools'):
            raise RuntimeError('Original triage JSON/no-tool contract changed')
        visibility = evidence_visibility(row['evidence'], users)
        if not visibility['complete'] and not self.offline_mode:
            blocked = {'finding_id': row['finding_id'], 'reason': 'input_evidence_incomplete',
                       'body': body, 'input_visibility': visibility, 'sent': False}
            self.blocked.append(blocked)
            offline.write_new(self.out / f'blocked-request-{len(self.blocked):02d}.json', blocked)
            raise RuntimeError('Input evidence incomplete; discuss production serialization before live evaluation')
        item = {'index': len(self.requests) + 1, 'finding_id': row['finding_id'], 'body': body,
                'body_sha256': offline.digest(offline.encoded(body)), 'phase': 'before_send',
                'input_visibility': visibility,
                'transport_mode': 'offline_http_stub' if self.offline_mode else 'real_model_gateway',
                'started_at': datetime.now(timezone.utc).isoformat()}
        self.requests.append(item)
        request.extensions['eval_index'] = item['index']
        offline.write_new(self.out / f"request-{item['index']:02d}.json", item)

    async def response(self, response):
        from agents_probe import visible_response
        await response.aread()
        try:
            body = visible_response(response.json())
        except (ValueError, TypeError, AttributeError):
            body = {'non_json_response': True}
        item = {'index': response.request.extensions['eval_index'], 'status': response.status_code, 'body': body}
        self.responses.append(item)
        offline.write_new(self.out / f"response-{item['index']:02d}.json", item)


def raw_classification(body: dict) -> dict:
    """Read the original response without the business parser's default-TP repair."""
    result = {'raw_output_verdict': None, 'raw_output_confidence': None, 'raw_output_valid': False}
    try:
        content = body['choices'][0]['message']['content']
        if not isinstance(content, str):
            return result
        start = content.find('{')
        if start < 0:
            return result
        data, _ = json.JSONDecoder().raw_decode(content[start:])
        result.update(raw_output_verdict=data.get('verdict'), raw_output_confidence=data.get('confidence'))
        _, normalize = offline.existing_scorer()
        label = normalize(data.get('verdict'), default='')
        confidence = data.get('confidence')
        valid = (label in offline.LABELS | {'needs_review'} and type(confidence) in (int, float)
                 and math.isfinite(confidence) and 0 <= confidence <= 1 and isinstance(data.get('rationale'), str))
        result.update(raw_output_valid=valid, normalized_model_verdict=label or None)
    except (KeyError, IndexError, TypeError, AttributeError, ValueError):
        pass
    return result


def classify_execution(decision: dict, requests: list[dict], responses: list[dict]) -> dict:
    matched = [r for r in responses if r['index'] in {q['index'] for q in requests}]
    good = len(requests) == len(matched) == 1 and matched[0]['status'] == 200
    usage = matched[0]['body'].get('usage') if good else None
    usage = usage if isinstance(usage, dict) else {}
    tokens = usage.get('total_tokens')
    usage_known = type(tokens) is int and tokens >= 0
    raw = raw_classification(matched[0]['body']) if good else raw_classification({})
    adopted = good and raw['raw_output_valid'] and decision.get('tier') == 'llm' and not decision.get('error')
    return {'http_requests': len(requests), 'http_responses': len(matched),
            'successful_http_response': good, 'model_result_adopted': adopted,
            **raw, 'program_verdict': decision.get('verdict'),
            'tokens': tokens if usage_known else None, 'usage_known': usage_known,
            'continue_allowed': adopted and usage_known,
            'fallback': decision.get('tier') == 'deterministic',
            'unknown_request_indices': [q['index'] for q in requests if q['index'] not in {r['index'] for r in matched}]}


async def run(directory: Path, out: Path, gateway: str, *, test_transport=None) -> dict:
    """Called in a fresh configured process; test_transport is only for offline tests."""
    import httpx
    from app.llm import factory
    from app.agents import auto_triage_agent
    from app.replay import runner as runner_module
    from app.replay.findings import HistoricalFinding
    from app.replay.shadow import ContextSnapshot
    from verdict_context import make_context_reader

    manifest, inputs = load_inputs(directory)
    anchor = datetime.fromisoformat(manifest['anchor'].replace('Z', '+00:00'))
    if anchor.tzinfo is None:
        raise ValueError('Corpus anchor must include timezone')
    # Match ChatOpenAI's supplied base exactly; the raw-HTTP helper adds /v1
    # for an unversioned base, while this SDK appends only /chat/completions.
    endpoint = gateway.rstrip('/') + '/chat/completions'
    observer = Observation(out, endpoint, factory.resolve_model_alias('triage'), offline_mode=test_transport is not None)
    original = factory.make_chat_model
    observations, execution = [], []
    reason = None
    tenant = str(uuid4())
    class Normalizer:
        connector_id = 'verdict-corpus'
        def normalize(self, raw):
            return {'raw_event': dict(raw)}
    async with httpx.AsyncClient(trust_env=False, timeout=45, follow_redirects=False, transport=test_transport,
                                  event_hooks={'request': [observer.request], 'response': [observer.response]}) as client:
        def observed_factory(role, **kwargs):
            if role != 'triage':
                raise RuntimeError('Unexpected role in given-evidence evaluation')
            return original(role, **{**kwargs, 'max_retries': 0, 'timeout': 45.0, 'http_async_client': client})
        with ExitStack() as stack:
            stack.enter_context(patch.object(factory, 'make_chat_model', observed_factory))
            stack.enter_context(patch.object(auto_triage_agent, 'make_chat_model', observed_factory))
            stack.enter_context(patch.object(runner_module, 'FrozenTriageContextReader', make_context_reader))
            replay = runner_module.ReplayRunner(normalizer=Normalizer(), tenant_id=tenant)
            for index, row in enumerate(inputs, 1):
                if sum(r['tokens'] or 0 for r in execution) >= TOKEN_STOP:
                    reason = 'observed_token_stop'
                    break
                observer.current = row
                offline.write_new(out / f'case-{index:02d}-started.json', {'finding_id': row['finding_id']})
                finding = HistoricalFinding(vendor=row['vendor'], finding_id=row['finding_id'], title=row['title'],
                    disposition='unlabeled', vendor_disposition='', closed_at=anchor, severity=row['severity'],
                    rule_id=row['rule_id'], raw=row['evidence'])
                start = len(observer.requests)
                try:
                    async with asyncio.timeout(60):
                        window = await replay.replay_window([finding], snapshot=ContextSnapshot(split_at=anchor))
                    decision = window.decisions[0].as_dict()
                    context = window.cutoff_context
                    suppressed = window.writes_attempted
                except Exception as exc:
                    decision = {'finding_id': row['finding_id'], 'verdict': None, 'confidence': 0.0,
                                'error': type(exc).__name__, 'tier': 'error'}
                    context, suppressed = {}, {}
                state = classify_execution(decision, observer.requests[start:], observer.responses)
                state.update(transport_mode='offline_http_stub' if test_transport is not None else 'real_model_gateway',
                             real_model_response_verified=test_transport is None and state['successful_http_response'])
                execution.append({'finding_id': row['finding_id'], **state})
                allowed = {'finding_id', 'verdict', 'verdict_raw', 'confidence', 'error', 'findings', 'confidence_basis',
                           'tier', 'tokens', 'llm_calls', 'resolved_models', 'measured_usd', 'estimated_usd',
                           'unpriced_calls', 'latency_ms', 'tool_calls'}
                observation = {k: v for k, v in decision.items() if k in allowed}
                observation.update(tokens=state['tokens'], llm_calls=state['http_requests'])
                if not state['model_result_adopted']:
                    observation['error'] = observation.get('error') or 'no adopted model result; see raw decision'
                observations.append(observation)
                offline.write_new(out / f'case-{index:02d}-result.json', {'decision': decision, 'execution': state,
                    'context': context, 'shadow_write_attempts_suppressed': suppressed})
                if not state['continue_allowed']:
                    reason = 'input_evidence_incomplete' if observer.blocked else 'response_usage_or_adoption_unconfirmed'
                    break
    observation_name = 'preflight-observations.json' if test_transport is not None else 'observations.json'
    offline.write_new(out / observation_name, observations)
    summary = {'schema_version': 'socai2-verdict-live-result/v1', 'planned': len(inputs), 'completed': len(execution),
               'source_mode': 'offline_http_stub' if test_transport is not None else 'given_evidence_shadow',
               'execution': execution, 'stop_reason': reason,
               'http_requests': len(observer.requests), 'http_responses': len(observer.responses),
               'known_tokens': sum(r['tokens'] or 0 for r in execution),
               'all_usage_known': all(r['usage_known'] for r in execution),
               'new_business_storage_configured': False, 'overall_accuracy_publishable': False,
               'observation_file': observation_name, 'observation_semantics': 'program_adopted_classification',
               'gateway_internal_attempts': 'not_observed', 'input_manifest': manifest}
    summary.update(new_model_requests=len(observer.requests) if test_transport is None else 0,
                   input_visibility=[{'finding_id': r['finding_id'], **r['input_visibility']} for r in observer.requests],
                   blocked_requests=[{'finding_id': r['finding_id'], 'reason': r['reason'],
                                      'input_visibility': r['input_visibility']} for r in observer.blocked],
                   ready_for_live=len(observer.requests) == REQUEST_LIMIT and not observer.blocked
                       and all(r['input_visibility']['complete'] for r in observer.requests))
    offline.write_new(out / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--pair-id', action='append', required=True)
    prep.add_argument('--out', type=Path, required=True)
    live = commands.add_parser('run')
    live.add_argument('--prepared', type=Path, required=True)
    live.add_argument('--out', type=Path, required=True)
    live.add_argument('--model-env', type=Path, required=True)
    live.add_argument('--gateway-base', required=True)
    live.add_argument('--preflight', action='store_true', help='Use marked HTTP substitutes; deny all network connections')
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == 'prepare':
        print(json.dumps(prepare(args.out, args.pair_id)))
        return
    directory = args.prepared.resolve()
    load_inputs(directory)  # Validate before importing any service or configuring egress.
    out = offline.private_path(args.out)
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    metadata = configure(args.model_env.resolve(), args.gateway_base)
    metadata['source_sha256'] = {name: offline.digest((ROOT / name).read_bytes()) for name in (
        'tools/testdata/verdict_live.py', 'tools/testdata/verdict_context.py', 'tools/testdata/verdict_eval.py',
        'services/agents/app/replay/runner.py', 'services/agents/app/agents/auto_triage_agent.py',
        'services/agents/app/prompt_serialization.py', 'services/agents/app/llm/factory.py')}
    offline.write_new(out / 'runtime.json', metadata)
    os.chdir(out)
    sys.path.insert(0, str(ROOT / 'services/agents'))
    # Last-line guard applies to all libraries, including accidental DB/API clients.
    endpoint = urlsplit(args.gateway_base)
    def network_guard(event, arguments):
        if event == 'socket.connect':
            address = arguments[1]
            if args.preflight or not isinstance(address, tuple) or address[:2] != ('127.0.0.1', endpoint.port):
                raise RuntimeError('Non-model connection blocked by evaluation harness')
    sys.addaudithook(network_guard)
    import structlog
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
                        logger_factory=structlog.PrintLoggerFactory(sys.stderr))
    transport = None
    if args.preflight:
        import httpx
        async def substitute(request):
            return httpx.Response(200, json={'id': 'preflight-substitute', 'object': 'chat.completion', 'created': 0,
                'model': json.loads(await request.aread())['model'], 'choices': [{'index': 0, 'finish_reason': 'stop',
                'message': {'role': 'assistant', 'content': json.dumps({'verdict': 'needs_review', 'confidence': 0,
                    'rationale': 'Offline input preflight substitute; no model ran.'})}}],
                'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}})
        transport = httpx.MockTransport(substitute)
    result = asyncio.run(run(directory, out, args.gateway_base, test_transport=transport))
    print(json.dumps({k: result[k] for k in ('source_mode', 'completed', 'planned', 'new_model_requests', 'ready_for_live', 'stop_reason')}))


if __name__ == '__main__':
    main()
