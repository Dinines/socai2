"""C03-02D-02 hash-bound, single-case container operator; no automatic batch loop.

Only body/messages and selected answer/usage fields may enter evidence. No
headers, credential values, provider response object or reasoning text is
serialized. This module never reads the external grading rubric.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import asyncio
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

# All execution requires the host-frozen state/inputs/operator/source contract.
READS = ('organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read',
         'recent_dispositions_read', 'identity_context_read')
MATERIALS = ('organisation_memory', 'tenant_skill', 'knowledge_base',
             'recent_dispositions', 'identity_context')
VERDICTS = {'true_positive', 'benign_true_positive', 'false_positive', 'benign', 'needs_review'}
NONCE = re.compile(r'AISOC-[0-9a-f]{32}')
SOURCE_MARKERS = re.compile(r'synthetic|socai2|\bfixture\b', re.IGNORECASE)
SCORING_MARKERS = re.compile(r'expected[_ -]?verdict|ground[_ -]?truth|test[_ -]?label|scoring[_ -]?label|\brubric\b', re.IGNORECASE)
B_MEMORY_SHA256 = 'e1cd55995cdbd2794207c1fa40a9c14f748294226a53dfa67d145e997af61992'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(condition, reason):
    if not condition:
        # Production _llm_triage preserves this through its exception chain;
        # _process_with_retry then holds, and _handle records failure before
        # commit. A custom BaseException could escape that failure flag while
        # EntityLanes.drain gathers exceptions, so it is deliberately avoided.
        from app.workers.triage_budget import BudgetHold
        raise BudgetHold('C03 quality observation hold: ' + reason)


def json_safe_schema(content):
    require(isinstance(content, str), 'raw answer content is not text')
    def reject_non_json_constant(value):
        raise ValueError('Non-JSON numeric constant: ' + value)
    try:
        value = json.loads(content, parse_constant=reject_non_json_constant)
    except (ValueError, TypeError) as exc:
        from app.workers.triage_budget import BudgetHold
        raise BudgetHold('C03 raw reply is not strict JSON; no repair or retry') from exc
    require(isinstance(value, dict) and {'verdict', 'confidence', 'rationale'} <= set(value), 'raw answer required keys')
    require(isinstance(value['verdict'], str) and value['verdict'] in VERDICTS, 'raw answer verdict')
    confidence = value['confidence']
    require(type(confidence) in (int, float) and math.isfinite(confidence) and 0 <= confidence <= 1,
            'raw answer confidence')
    require(isinstance(value['rationale'], str) and bool(value['rationale'].strip()), 'raw answer rationale')
    return value


def schema_observation(content):
    """Observe strict raw schema without changing production response flow."""
    try:
        value = json_safe_schema(content)
    except Exception as exc:
        return {'valid': False, 'error_type': type(exc).__name__, 'repair_or_retry_allowed_for_quality': False}
    return {'valid': True, 'value': {key: value[key] for key in ('verdict', 'confidence', 'rationale')},
            'extra_field_names': sorted(set(value) - {'verdict', 'confidence', 'rationale'}),
            'extra_fields_do_not_expand_verified_schema': True, 'repair_used': False}


def nonce_normalized(value):
    """Normalize only the one observed nonce; no other content is discarded."""
    serialized = canonical(value)
    nonces = set(NONCE.findall(serialized))
    require(len(nonces) == 1, 'expected exactly one unique production run nonce')
    return serialized.replace(next(iter(nonces)), '__PRODUCTION_RUN_NONCE__')


def facts_before_prompt(state, policy):
    """Keep adopted contents, identities, source statuses and selection facts.

    Exclude only read timestamps and the measured cache age/fetch instant.
    Freshness, cache source, status/reason, received/adopted counts, content
    hashes, literal text and selection/version facts still participate.
    Called before run_auto_triage mutates KB rendering with its fresh nonce.
    """
    reads = {}
    for name in READS:
        row = deepcopy(getattr(state, name))
        row.pop('read_at', None)
        if isinstance(row.get('cache'), dict):
            row['cache'].pop('fetched_at', None)
            row['cache'].pop('age_seconds', None)
        reads[name] = row
    return {'raw_alert': deepcopy(state.raw_alert),
            'materials': {name: deepcopy(getattr(state, name)) for name in MATERIALS},
            'reads': reads, 'business_context': deepcopy(policy)}


class Evidence:
    def __init__(self, root, case, phase):
        self.root, self.case, self.phase = Path(root), case, phase
        self.directory = self.root / 'cases' / case / phase
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)

    def save(self, name, value):
        path = self.directory / name
        with path.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, default=str)
            stream.write('\n')
        path.chmod(0o600)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def stop(self, reason, error_type=None):
        path = self.root / 'recovery-stop.json'
        if not path.exists():
            with path.open('x') as stream:
                json.dump({'case': self.case, 'phase': self.phase, 'reason': reason,
                           'error_type': error_type, 'automatic_retry_allowed': False}, stream, indent=2)
                stream.write('\n')
            path.chmod(0o600)


@contextmanager
def count_http(evidence, *, mock_model_client=None, cap=240):
    """Count each new-batch HTTP send entry, including failures and polls.

    Production readers instantiate their own httpx clients. Observing send
    catches those requests as well as the supplied API/model clients. An
    event is an initiated attempt, not proof the remote accepted it. Fixture
    transport requests have a separate explicit synthetic classification.
    """
    import httpx
    original = httpx.AsyncClient.send
    events = evidence.root / 'http-events'
    events.mkdir(mode=0o700, exist_ok=True)
    lock = asyncio.Lock()

    async def send(client, request, *args, **kwargs):
        url = urlsplit(str(request.url))
        require(url.username is None and url.password is None, 'credential-bearing HTTP URL')
        mock = client is mock_model_client or getattr(client, '_c03_mock_only', False)
        async with lock:
            prior = [json.loads(path.read_text()) for path in events.glob('*-started.json')]
            number = len(prior) + 1
            require(mock or sum(not row['synthetic_model_transport'] for row in prior) < cap,
                    'new-batch actual-network HTTP attempt cap')
            require(not mock or sum(row['synthetic_model_transport'] for row in prior) < 4,
                    'batch synthetic SDK request cap')
            row = {'case': evidence.case, 'phase': evidence.phase, 'sequence': number,
                   'method': request.method, 'scheme': url.scheme, 'host': url.hostname,
                   'port': url.port, 'path': url.path,
                   'query_sha256': hashlib.sha256(url.query.encode()).hexdigest(),
                   'synthetic_model_transport': mock, 'actual_network_acceptance': 'not_observed_yet'}
            start = events / f'{number:04d}-started.json'
            with start.open('x') as stream:
                json.dump(row, stream, indent=2)
            start.chmod(0o600)
        try:
            response = await original(client, request, *args, **kwargs)
        except BaseException as exc:
            outcome = {'error_type': type(exc).__name__, 'remote_outcome': 'not_confirmed'}
            raise
        else:
            outcome = {'status': response.status_code,
                       'transport': 'MockTransport, no real network' if mock else 'real HTTP response received'}
            return response
        finally:
            end = events / f'{number:04d}-finished.json'
            with end.open('x') as stream:
                json.dump(outcome, stream, indent=2)
            end.chmod(0o600)

    httpx.AsyncClient.send = send
    try:
        yield
    finally:
        httpx.AsyncClient.send = original


class SDKObservation:
    """Observe original safe-call, original egress and the real SDK body.

    preflight uses a MockTransport outside any budget Invocation. invoke uses
    the original network transport with an actual production Invocation. No
    reader, writer, claim, budget SQL, cost flush or shadow policy is replaced.
    """
    def __init__(self, evidence, phase, *, tenant, expected=None):
        self.evidence, self.phase, self.expected = evidence, phase, expected
        self.tenant, self.memory_block = tenant, None
        self.safe_seen = self.egress_seen = self.http_seen = 0
        self.pre_messages = self.post_messages = self.request_body = None
        self.raw_answer = None
        self.sdk_settings = None

    def pin_marker_source(self, investigation):
        """Bind the sole declared B marker to its existing memory block."""
        from app.investigator.prompt_sanitizer import sanitize_text
        block = sanitize_text(str(investigation.organisation_memory_read.get('prompt_block') or ''), max_len=0)
        if self.tenant == 'b':
            require(hashlib.sha256(block.encode()).hexdigest() == B_MEMORY_SHA256,
                    'B declared global memory block changed')
            require([match.group().lower() for match in SOURCE_MARKERS.finditer(block)] == ['synthetic'],
                    'B declared memory marker identity')
            self.memory_block = block
        else:
            require(not SOURCE_MARKERS.search(block), 'A memory marker contamination')

    def scan_messages(self, messages, boundary):
        locations, scoring = [], []
        allowed_span = None
        for index, message in enumerate(messages):
            content, role = message.get('content'), message.get('role')
            require(isinstance(content, str), 'expected text-only actual messages')
            if self.tenant == 'b':
                # Preserve the current egress transformation. The pre-egress
                # block is hash-bound above; both boundaries retain the same
                # production renderer's fixed header and final advisory.
                header = 'Organisation memory for this tenant — durable facts compiled from repeated analyst disagreement, not from this alert:\n'
                trailer = 'compromise in the telemetry.'
                start = content.find(header)
                end = content.find(trailer, start) if start >= 0 else -1
                if start >= 0 and end >= 0:
                    require(allowed_span is None and role == 'user', 'unique B memory source position')
                    allowed_span = (index, start, end + len(trailer))
                    if boundary == 'pre-egress':
                        require(self.memory_block is not None and
                                content[start:end + len(trailer)] == self.memory_block,
                                'B marker not in the declared adopted memory block')
            locations.extend({'message_index': index, 'role': role, 'start': match.start(),
                              'end': match.end(), 'marker': match.group().lower()}
                             for match in SOURCE_MARKERS.finditer(content))
            scoring.extend({'message_index': index, 'role': role, 'start': match.start(), 'end': match.end()}
                           for match in SCORING_MARKERS.finditer(content))
        self.evidence.save(boundary + '-marker-scan.json', {'source_marker_locations': locations,
            'scoring_metadata_locations': scoring, 'declared_b_memory_sha256': B_MEMORY_SHA256 if self.tenant == 'b' else None,
            'marker_scan_is_not_semantic_quality_scoring': True})
        require(not scoring, 'scoring metadata in actual full messages')
        if self.tenant == 'b':
            require(len(locations) == 1 and locations[0]['marker'] == 'synthetic' and allowed_span is not None,
                    'B full prompt must contain only the one declared Synthetic marker')
            location = locations[0]
            require(location['message_index'] == allowed_span[0] and
                    allowed_span[1] <= location['start'] < location['end'] <= allowed_span[2],
                    'B marker appeared outside the declared global memory background')
        else:
            require(not locations, 'A full prompt source-marker contamination')

    async def request_hook(self, request):
        from app.workers.triage_budget import current_invocation
        from app.llm.contract_rules import LLMInputContract
        invocation = current_invocation()
        require(self.http_seen == 0, 'second SDK HTTP request forbidden')
        require((invocation is None) if self.phase == 'preflight' else
                (invocation is not None and invocation.request_marked), 'request boundary invocation identity')
        body = json.loads(request.content)
        self.request_body = body
        require(body.get('messages') == self.post_messages, 'SDK body differs from observed egress messages')
        require(len(canonical(LLMInputContract.validate(body['messages'])).encode()) <= 16000,
                'post-egress canonical input byte cap')
        caps = [body[key] for key in ('max_tokens', 'max_completion_tokens') if key in body]
        require(bool(caps) and all(value == 512 for value in caps), 'SDK output cap')
        self.evidence.save('sdk-request-body.json', body)  # Body only: never headers.
        if self.expected:
            require(nonce_normalized(body) == self.expected['sdk_request_nonce_normalized'],
                    'SDK payload changed after preflight')
        if self.phase == 'invoke':
            attempts = list(self.evidence.root.glob('cases/*/invoke/sdk-send-started.json'))
            require(len(attempts) < 4, 'batch model attempt cap')
            self.evidence.save('sdk-send-started.json', {'attempt': 1, 'batch_attempt': len(attempts) + 1,
                'request_body_sha256': digest(body), 'never_retry_unknown': True})
        self.http_seen += 1

    async def response_hook(self, response):
        # Reading in memory permits selection; only this allowlist is saved.
        # reasoning_content and all other provider-specific fields are ignored.
        await response.aread()
        try:
            body = response.json()
        except (ValueError, TypeError):
            self.evidence.save('raw-answer-selected.json', {'status': response.status_code,
                'provider_body_sha256': hashlib.sha256(response.content).hexdigest(),
                'provider_body_saved': False, 'body_json_valid': False})
            return  # The unchanged SDK decides its own exception behavior.
        if not isinstance(body, dict):
            self.evidence.save('raw-answer-selected.json', {'status': response.status_code,
                'body_json_valid': True, 'body_object_valid': False, 'provider_body_saved': False})
            return
        choices = body.get('choices')
        choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        message = choice.get('message') if isinstance(choice.get('message'), dict) else {}
        content = message.get('content')
        usage = body.get('usage') if isinstance(body.get('usage'), dict) else {}
        complete = isinstance(content, str) and len(content) <= 8000
        selected = {'content': content if complete else None, 'finish_reason': choice.get('finish_reason'),
                    'content_chars': len(content) if isinstance(content, str) else None,
                    'content_sha256': hashlib.sha256(content.encode()).hexdigest() if isinstance(content, str) else None,
                    'complete_short_content_retained': complete,
                    'choice_count': len(choices) if isinstance(choices, list) else None,
                    'usage': {key: usage.get(key) if type(usage.get(key)) is int else None
                              for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
                    'synthetic_only': self.phase == 'preflight'}
        self.evidence.save('raw-answer-selected.json', selected)
        self.raw_answer = schema_observation(content) if complete else {'valid': False, 'short_content_cap': False}
        if not isinstance(choices, list) or len(choices) != 1:
            self.raw_answer['valid'] = False
        if choice.get('finish_reason') != 'stop':
            self.raw_answer.update(valid=False, complete_finish_reason_confirmed=False)
        self.evidence.save('raw-schema-observation.json', self.raw_answer)
        # Invalid content still reaches the production parser unchanged. Its
        # repair/normalize/fallback can finish, but can never pass the external
        # quality gate or authorize the next input.

    @contextmanager
    def bind(self, http_client):
        from app.agents import auto_triage_agent as agent
        from app.llm import contract, egress_privacy
        from app.workers.triage_budget import current_invocation
        factory, safe, redact = agent.make_chat_model, agent.safe_ainvoke, egress_privacy.EgressSession.redact_messages
        old_cache = contract._RESPONSE_CACHE_ENABLED

        def observed_factory(*args, **kwargs):
            require('http_async_client' not in kwargs, 'unexpected model transport override')
            model = factory(*args, **kwargs, http_async_client=http_client)
            require(model.max_tokens == 512 and model.root_async_client.max_retries == 0 and
                    model.request_timeout == model.root_async_client.timeout == 45.0, 'production SDK limits')
            base = str(model.root_async_client.base_url)
            parts = urlsplit(base)
            require(parts.username is None and parts.password is None and not parts.query and not parts.fragment,
                    'credential-bearing model base URL')
            self.sdk_settings = {'base_url': base, 'model': model.model_name, 'max_tokens': model.max_tokens,
                'max_retries': model.root_async_client.max_retries, 'timeout': model.root_async_client.timeout}
            self.evidence.save('sdk-settings.json', self.sdk_settings)
            if self.expected:
                require(self.sdk_settings == self.expected['sdk_settings'], 'model route/settings changed')
            return model

        def observed_redact(session, messages):
            self.egress_seen += 1
            require(self.egress_seen == 1, 'second egress operation')
            result = redact(session, messages)
            self.post_messages = contract.LLMInputContract.validate(result)
            self.evidence.save('egress-post-messages.json', self.post_messages)
            self.scan_messages(self.post_messages, 'post-egress')
            return result

        async def observed_safe(llm, messages, *args, **kwargs):
            require(self.safe_seen == 0, 'second safe-call forbidden')
            require((current_invocation() is None) if self.phase == 'preflight' else
                    current_invocation() is not None, 'safe-call must match preflight/live boundary')
            self.safe_seen += 1
            self.pre_messages = contract.LLMInputContract.validate(messages)
            literal = json.dumps(self.pre_messages, sort_keys=True, default=str)
            require(len(literal) <= 8000, 'literal full prompt cap')
            self.evidence.save('egress-pre-messages.json', self.pre_messages)
            self.scan_messages(self.pre_messages, 'pre-egress')
            if self.expected:
                require(nonce_normalized(self.pre_messages) == self.expected['pre_messages_nonce_normalized'],
                        'source/status/prompt changed after preflight')
            try:
                result = await safe(llm, messages, *args, **kwargs)
            except Exception as exc:
                # Preserve the real before_request/responded state. A known
                # answer remains known; unconfirmed calls retain their slot.
                from app.workers.triage_budget import BudgetHold
                raise BudgetHold('C03 invocation stopped; no fallback/retry authorized') from exc
            usage = getattr(result, 'usage_metadata', None) or {}
            content = result.content
            self.evidence.save('safe-response-selected.json', {'content': content if isinstance(content, str) and len(content) <= 8000 else None,
                'content_sha256': digest(content),
                'usage_metadata': {key: usage.get(key) if type(usage.get(key)) is int else None
                                   for key in ('input_tokens', 'output_tokens', 'total_tokens')},
                'synthetic_only': self.phase == 'preflight'})
            return result

        agent.make_chat_model, agent.safe_ainvoke = observed_factory, observed_safe
        egress_privacy.EgressSession.redact_messages = observed_redact
        if self.phase == 'preflight':
            # Process-local fixture only. Actual live Invocation bypasses the
            # original response cache itself; invoke never changes this flag.
            contract._RESPONSE_CACHE_ENABLED = False
        try:
            yield
        finally:
            agent.make_chat_model, agent.safe_ainvoke = factory, safe
            egress_privacy.EgressSession.redact_messages = redact
            contract._RESPONSE_CACHE_ENABLED = old_cache


"""Container phase implementation; merged with observations into quality.py.

Never run this development fragment. Host owns all provision/policy/backup,
the two new topics, group0 initialization and the independent review gates.
"""

INPUT_SHA256 = 'e80c04a5e9d2bc18b526c197af9b6e9ab8cbc5966e2615dca274e12b3949e3c2'
CASES = ('case01', 'case02', 'case03', 'case04')


def read_json(path):
    return json.loads(Path(path).read_text())


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def recovery_gate(root, state, phase, case):
    """Only the independently accepted pre-Evidence failure can be waived."""
    import os
    recovery = root / 'contract-recovery-r02'
    require(file_sha(root / 'safety-stop.json') ==
            '8c32c8eaea7ed0966b2fd212104d2343fecdf3e634ba14abf0ee8298c3ab60d7', 'original stop changed')
    require(not (root / 'recovery-stop.json').exists(), 'new recovery stop forbids every phase')
    review = read_json(recovery / 'independent-review.json')
    require(file_sha(recovery / 'independent-review.json') == os.environ['C03_RECOVERY_REVIEW_SHA256'] and
            review.get('accepted') is True and review.get('change') == 'C03-02D-02-contract-recovery-r02' and
            review.get('zero_business_sends_or_models_confirmed') is True,
            'independent recovery review')
    require(review['prepared_sha256'] == file_sha(recovery / 'prepared.json') and
            review['new_inside_sha256'] == file_sha(__file__) and
            review['new_state_sha256'] == file_sha('/private/state.json') and
            review['new_runner_sha256'] == os.environ['C03_RECOVERY_RUNNER_SHA256'], 'recovery state/source binding')
    prepared = read_json(recovery / 'prepared.json')
    require(review['original_preexec_sha256'] == prepared['original_preexec_sha256'] and
            review['original_stop_sha256'] == prepared['original_stop_sha256'], 'original authorization/failure binding')
    if os.environ.get('C03_RECOVERY_CONTRACT_ONLY') == '1':
        require(phase == 'ingress' and case == 'case01' and not (root / 'cases').exists() and
                not (recovery / 'authorized.json').exists(), 'only one pre-business contract probe')
        return
    authorized = read_json(recovery / 'authorized.json')
    require(file_sha(recovery / 'authorized.json') == os.environ['C03_RECOVERY_AUTH_SHA256'] and
            authorized['independent_review_sha256'] == file_sha(recovery / 'independent-review.json') and
            authorized['new_state_sha256'] == file_sha('/private/state.json') and
            authorized['new_inside_sha256'] == file_sha(__file__) and
            authorized['new_runner_sha256'] == os.environ['C03_RECOVERY_RUNNER_SHA256'] and
            authorized['probe_accepted_sha256'] == file_sha(recovery / 'probe/accepted.json'), 'business recovery authorization')


def check_contract(phase, case):
    import os
    from app.llm.prompt_registry import default_registry, load_lock
    from app.workers import fused_alert_consumer as worker
    require(case in CASES and phase in {'ingress', 'preflight', 'invoke', 'verify'}, 'phase/case')
    require(os.geteuid() == 10001, 'probe must use resident UID10001')
    state, inputs = read_json('/private/state.json'), read_json('/private/inputs.json')
    require(state.get('execution_authorized') is True, 'frozen host authorization absent')
    require(state['batch'] == inputs['batch'], 'batch binding')
    require(file_sha('/private/inputs.json') == state['inputs_sha256'] == INPUT_SHA256, 'formal input hash')
    require(file_sha(__file__) == state['operator_sha256'], 'operator hash')
    require(os.environ['C03_PROBE_IMAGE_ID'] == state['image_id'], 'host-bound baked image')
    source = {'services/agents/app/' + str(p.relative_to('/app/app')): file_sha(p)
              for p in sorted(Path('/app/app').rglob('*.py'))}
    require(len(source) == 184 and source == state['source_sha256'], 'baked source map')
    require(file_sha('/app/app/llm/prompts.lock.json') == state['prompt_lock_sha256'], 'non-Py prompt lock')
    require(default_registry().get('triage.system').version == '5' and
            not default_registry().verify_against_lock(load_lock()), 'triage v5/lock')
    require(not worker.worker_enabled() and not worker._escalation_enabled() and
            not worker._approvals_enabled() and not worker._memory_writeback_enabled() and
            not worker.alert_trigger.deployment_enabled(), 'resident/action flags must remain off')
    require(file_sha(os.environ['AISOC_TRIAGE_BUDGET_POLICY_FILE']) == state['policy_sha256'], 'installed policy changed')
    root = Path('/evidence')
    recovery_gate(root, state, phase, case)
    if case != CASES[0] and phase != 'verify':
        previous = CASES[CASES.index(case) - 1]
        completion = root / 'cases' / previous / 'verify' / 'case-completed.json'
        gate = read_json(Path('/quality-gates') / (previous + '.json'))
        require(gate.get('accepted') is True and gate['case'] == previous and
                gate['input_sha256'] == INPUT_SHA256 and
                gate['completion_sha256'] == file_sha(completion), 'independent previous-case quality gate')
        require(read_json(completion)['gate_eligible'] is True, 'previous infrastructure/schema failed')
    return state, inputs, inputs['cases'][case]


def runtime_worker(state, cls=None):
    import os
    from app.workers import fused_alert_consumer as module
    from app.workers.business_context import BusinessContextApplier, is_enabled
    return (cls or module.FusedAlertTriageWorker)(
        bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
        topic=state['broker']['quality_topic'], group_id=state['broker']['group'],
        dlq_topic=state['broker']['dlq_topic'], max_attempts=1,
        business_context=BusinessContextApplier() if is_enabled() else None)


def book_delivery(evidence, coordinate, *, kind):
    directory = evidence.root / 'record-deliveries'
    directory.mkdir(mode=0o700, exist_ok=True)
    number = len(list(directory.glob('*.json'))) + 1
    # Reserve one resident Fusion raw delivery slot per attempted new ingress.
    # Those slots are NOT labelled physically observed by this temporary
    # consumer; host checks raw-group/log confirmation separately.
    raw_slots = len(list(evidence.root.glob('cases/*/ingress/http-sending.json')))
    over_cap = number + raw_slots > 12
    path = directory / f'{number:03d}.json'
    with path.open('x') as stream:
        json.dump({'case': evidence.case, 'kind': kind, 'coordinate': coordinate,
                   'observed_delivery_sequence': number, 'resident_raw_slots_reserved': raw_slots,
                   'over_cap': over_cap}, stream, indent=2)
    path.chmod(0o600)
    # The record has already arrived. Retain its physical coordinate even
    # when an unexpected delivery itself crosses the authorized bound.
    require(not over_cap, 'record-delivery cap including resident raw slots')


async def broker_metadata(state, *, main=False):
    import os
    from aiokafka import AIOKafkaConsumer, TopicPartition
    from app.core.kafka_security import kafka_client_kwargs
    topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED'] if main else state['broker']['quality_topic']
    group = os.environ['KAFKA_CONSUMER_GROUP'] if main else state['broker']['group']
    security = kafka_client_kwargs()
    require(security['security_protocol'] == 'SSL', 'Kafka TLS')
    observer = AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
        group_id=group, enable_auto_commit=False, **security)
    await observer.start()
    try:
        await observer._client.add_topic(topic)  # Metadata only, no assign/poll.
        parts = observer.partitions_for_topic(topic)
        require(bool(parts), 'topic metadata unavailable')
        tps = [TopicPartition(topic, p) for p in sorted(parts)]
        begins, ends = await observer.beginning_offsets(tps), await observer.end_offsets(tps)
        return {'topic': topic, 'group': group, 'partitions': [{'partition': tp.partition,
                'begin': begins[tp], 'end': ends[tp], 'committed': await observer.committed(tp)} for tp in tps]}
    finally:
        await observer.stop()


async def api(client, state, who, method, path, *, body=None, allowed=(200,)):
    headers = {'Authorization': 'Bearer ' + state['identities'][who]['key']} if who else {}
    response = await client.request(method, path, headers=headers, json=body)
    require(response.status_code in allowed, 'API status outside allowed set')
    return response.status_code, response.json() if response.content else None


async def ingress(state, item, evidence):
    import os
    import httpx
    from aiokafka import AIOKafkaConsumer, TopicPartition
    from app.core.kafka_security import kafka_client_kwargs
    from datetime import datetime
    tenant, body = state['identities'][item['tenant']]['tenant_id'], deepcopy(item['alert'])
    topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
        group_id=None, enable_auto_commit=False, **kafka_client_kwargs())
    await consumer.start()
    try:
        tps = [TopicPartition(topic, p) for p in sorted(consumer.partitions_for_topic(topic) or [])]
        require(len(tps) == 3, 'original fused partition count')
        consumer.unsubscribe()
        consumer.assign(tps)
        ends = await consumer.end_offsets(tps)
        for tp in tps:
            consumer.seek(tp, ends[tp])
        evidence.save('original-fused-read-starts.json', [{'partition': tp.partition, 'offset': ends[tp]} for tp in tps])
        evidence.save('http-sending.json', {'input': body, 'outcome': 'not_confirmed', 'never_resubmit': True})
        async with httpx.AsyncClient(base_url=os.getenv('API_SERVICE_URL', 'http://api:8000'),
                                    timeout=25, trust_env=False) as client:
            _, ack = await api(client, state, item['tenant'], 'POST', '/api/v1/alert-ingress', body=body, allowed=(202,))
            evidence.save('http-ack.json', ack)
            require(ack['input_id'] == body['id'] and ack['tenant_id'] == tenant and
                    ack['identity_version'] == 'source-v1', 'HTTP canonical identity')
            stored = None
            for _ in range(12):
                status, value = await api(client, state, item['tenant'], 'GET',
                    '/api/v1/alerts/' + ack['canonical_alert_id'], allowed=(200, 404))
                if status == 200:
                    stored = value
                    break
                await asyncio.sleep(.5)
            require(stored is not None, 'accepted ingress PG/API result not confirmed')
            evidence.save('stored-alert.json', stored)
        record = await asyncio.wait_for(consumer.getone(), 45)
        coordinate = {'topic': record.topic, 'partition': record.partition, 'offset': record.offset,
                      'sha256': hashlib.sha256(record.value).hexdigest()}
        book_delivery(evidence, coordinate, kind='original_fused_capture')
        fused = json.loads(record.value)
        require(fused.get('alert_row_id') == ack['canonical_alert_id'] and fused.get('tenant_id') == tenant,
                'unexpected original fused record; no scanning permitted')
        alert = fused['alert']
        for key in ('description', 'source', 'rule_id', 'hostname', 'username', 'raw_event'):
            require(alert.get(key) == body[key], 'Fusion changed frozen source material: ' + key)
        for key in ('event_time', 'created_at'):
            require(datetime.fromisoformat(alert[key].replace('Z', '+00:00')) ==
                    datetime.fromisoformat(body[key].replace('Z', '+00:00')), 'Fusion source instant: ' + key)
        require(set(body['source_event_ids']) <= set(alert['source_event_ids']), 'source lineage')
        require(fused.get('persist_outcome') == 'inserted', 'first Fusion delivery result')
        evidence.save('fused-envelope.json', fused)
        wire_path = evidence.directory / 'fused-wire.json'
        with wire_path.open('xb') as stream:
            stream.write(record.value)
        wire_path.chmod(0o600)
        evidence.save('fused-coordinate.json', coordinate)
        evidence.save('accepted.json', {'input_sha256': INPUT_SHA256, 'canonical_alert_id': ack['canonical_alert_id'],
            'original_fused_sha256': digest(fused), 'raw_ack_coordinate': ack['message'],
            'original_fused_coordinate': coordinate, 'source_created_at': alert['created_at'],
            'pg_created_at': stored.get('created_at'), 'pg_created_at_is_ingestion_not_source_event': True,
            'real_model_attempts': 0, 'worker_claims': 0})
    finally:
        await consumer.stop()


async def preflight(state, item, evidence):
    import httpx
    from app.core.cost_telemetry import CostTracker
    from app.llm.factory import llm_override
    from app.workers import fused_alert_consumer as module, triage_budget as budget
    from app.context import organisation_memory, tenant_skills, knowledge_base, dispositions, identity
    require(budget.current_invocation() is None, 'preflight must not hold a budget Invocation')
    fused = read_json(evidence.root / 'cases' / evidence.case / 'ingress' / 'fused-envelope.json')
    worker = runtime_worker(state)
    policy = {'enabled': worker._business_context is not None}
    if worker._business_context is not None:
        result = await worker._business_context.apply_for_tenant(fused['tenant_id'], fused['alert'])
        policy.update(provenance=result.provenance, matched_rule_ids=result.matched_rule_ids,
                      suppressed=result.suppressed, changed=result.changed)
        require(not result.suppressed, 'current BusinessContext suppresses quality input')
        if result.changed:
            fused = {**fused, 'alert': result.alert}
    investigation = module.build_state(fused)
    before_products = await empty_preflight_products(investigation)
    require(all(value == 0 for value in before_products.values()), 'preflight found an existing Run/claim/cost')
    evidence.save('pg-before.json', before_products)
    for reader in (organisation_memory, tenant_skills, knowledge_base, dispositions, identity):
        reader.clear_cache()  # Fresh temporary process only.
    investigation.organisation_memory_read = await worker._reader.fetch_organisation_memory(str(investigation.tenant_id))
    investigation.organisation_memory = list(investigation.organisation_memory_read['statements'])
    await worker._attach_tenant_skill(investigation)
    await worker._attach_runbooks(investigation)
    await worker._attach_recent_dispositions(investigation)
    await worker._attach_identity_context(investigation)
    facts = facts_before_prompt(investigation, policy)
    evidence.save('fact-projection.json', facts)
    source_text = canonical(facts)
    score_markers = re.findall(r'expected[_ -]?verdict|ground[_ -]?truth|test[_ -]?label|scoring[_ -]?label|\brubric\b',
                              source_text, re.IGNORECASE)
    evidence.save('source-marker-scan.json', {'scoring_metadata_matches': len(score_markers),
        'synthetic_marker_matches': len(re.findall(r'synthetic|\bfixture\b', source_text, re.IGNORECASE)),
        'automatic_marker_scan_is_not_a_full_contamination_review': True,
        'b_existing_global_background_not_removed': item['tenant'] == 'b'})
    require(not score_markers, 'scoring metadata in actual adopted material')
    cfg = await worker._resolve_tenant_llm(investigation.tenant_id)
    require(cfg is not None, 'current tenant route refuses LLM')
    observation = SDKObservation(evidence, 'preflight', tenant=item['tenant'])
    observation.pin_marker_source(investigation)

    async def mock_transport(_request):
        return httpx.Response(200, json={'id': 'preflight-only', 'object': 'chat.completion', 'created': 1,
            'model': 'preflight-transport-fixture', 'choices': [{'index': 0, 'finish_reason': 'stop',
             'message': {'role': 'assistant', 'content': '{"verdict":"needs_review","confidence":0.5,"rationale":"Transport fixture only. No model reasoning was evaluated."}'}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_transport),
            event_hooks={'request': [observation.request_hook], 'response': [observation.response_hook]}) as client:
        client._c03_mock_only = True
        with observation.bind(client), llm_override(
            api_key=cfg.api_key if cfg.api_key_from_tenant else None,
            base_url=cfg.base_url if cfg.base_url_from_tenant else None,
            model=cfg.model if cfg.model_from_tenant else None):
            async with CostTracker(run_id=str(investigation.run_id), tenant_id=str(investigation.tenant_id), persist=False):
                await worker._llm_triage(investigation)
    require(observation.safe_seen == observation.egress_seen == observation.http_seen == 1,
            'preflight complete SDK chain')
    after_products = await empty_preflight_products(investigation)
    evidence.save('pg-after.json', after_products)
    require(before_products == after_products, 'preflight must not create business products')
    evidence.save('accepted.json', {'fact_projection_sha256': digest(facts),
        'pre_messages_nonce_normalized': nonce_normalized(observation.pre_messages),
        'sdk_request_nonce_normalized': nonce_normalized(observation.request_body),
        'sdk_settings': observation.sdk_settings,
        'synthetic_only': True, 'budget_invocations': 0, 'pg_claims': 0,
        'real_model_attempts': 0, 'new_runs': 0, 'new_reservations': 0, 'new_cost_rows': 0})


async def invoke(state, item, evidence):
    import os
    import httpx
    import aiokafka
    from aiokafka import AIOKafkaProducer
    from app.agents import auto_triage_agent as agent
    from app.workers import fused_alert_consumer as module, triage_budget as budget
    preflight_data = read_json(evidence.root / 'cases' / evidence.case / 'preflight' / 'accepted.json')
    fused = read_json(evidence.root / 'cases' / evidence.case / 'ingress' / 'fused-envelope.json')
    expected_index = CASES.index(evidence.case)
    before = await broker_metadata(state)
    require(before['partitions'] == [{'partition': 0, 'begin': 0, 'end': expected_index,
                                     'committed': expected_index}], 'new quality group exact initial position')
    observation, policy = SDKObservation(evidence, 'invoke', tenant=item['tenant'], expected=preflight_data), {'enabled': False}

    class ObservedWorker(module.FusedAlertTriageWorker):
        async def _process_with_retry(self, message):
            require(message == fused, 'unexpected quality message')
            require(not (evidence.directory / 'worker-delivery.json').exists(), 'second worker delivery')
            evidence.save('worker-delivery.json', {'envelope_sha256': digest(message)})
            return await super()._process_with_retry(message)

        async def _llm_triage(self, investigation):
            require(budget.current_invocation() is not None, 'actual live PG budget Invocation absent')
            facts = facts_before_prompt(investigation, policy)
            evidence.save('fact-projection.json', facts)
            require(digest(facts) == preflight_data['fact_projection_sha256'], 'adopted material/status changed')
            observation.pin_marker_source(investigation)
            return await super()._llm_triage(investigation)

        async def _record(self, investigation, **kwargs):
            evidence.save('before-persist.json', {'run_id': str(investigation.run_id),
                'raw_alert': investigation.raw_alert, 'reads': {name: getattr(investigation, name) for name in READS},
                'llm_exchanges': investigation.llm_exchanges, 'verdict': investigation.verdict,
                'confidence': investigation.confidence, 'tier': kwargs.get('tier'), 'tokens': kwargs.get('tokens'),
                'writer_class': type(kwargs['writer']).__name__})
            return await super()._record(investigation, **kwargs)

        async def triage(self, message):
            require(self._uses_delivery_guard(), 'ordinary live delivery guard absent')
            result = await super().triage(message)
            evidence.save('worker-result.json', result)
            return result

    worker = runtime_worker(state, ObservedWorker)
    policy['enabled'] = worker._business_context is not None
    if worker._business_context is not None:
        original_apply = worker._business_context.apply_for_tenant
        async def observed_apply(*args, **kwargs):
            result = await original_apply(*args, **kwargs)
            policy.update(provenance=result.provenance, matched_rule_ids=result.matched_rule_ids,
                          suppressed=result.suppressed, changed=result.changed)
            return result
        worker._business_context.apply_for_tenant = observed_apply
    producer, task, stopped, failure = None, None, False, None
    original_consumer = aiokafka.AIOKafkaConsumer

    class ObservedConsumer(original_consumer):
        async def __anext__(self):
            record = await super().__anext__()
            coordinate = {'topic': record.topic, 'partition': record.partition, 'offset': record.offset}
            book_delivery(evidence, coordinate, kind='actual_quality_worker')
            evidence.save('worker-record.json', coordinate)
            require(coordinate == {'topic': state['broker']['quality_topic'], 'partition': 0,
                                   'offset': expected_index}, 'unexpected quality coordinate')
            return record

        async def commit(self, offsets=None):
            result = await super().commit(offsets)
            # Preserve the original no-argument SDK commit behavior. This
            # bounded topic has one partition and one admitted record; the
            # actual coordinator value is observed after acknowledgement.
            if (evidence.directory / 'worker-record.json').exists():
                from aiokafka import TopicPartition
                tp = TopicPartition(state['broker']['quality_topic'], 0)
                evidence.save('worker-commit-confirmed.json', {'requested_offsets': offsets,
                    'committed': await self.committed(tp), 'group': state['broker']['group']})
            return result

    aiokafka.AIOKafkaConsumer = ObservedConsumer
    try:
        async with httpx.AsyncClient(follow_redirects=True, event_hooks={
                'request': [observation.request_hook], 'response': [observation.response_hook]}) as client:
            with observation.bind(client):
                task = asyncio.create_task(worker.start())
                for _ in range(200):
                    if task.done():
                        await task
                    if worker._consumer is not None and worker._consumer.assignment():
                        break
                    await asyncio.sleep(.1)
                else:
                    require(False, 'temporary worker assignment timeout')
                from app.core.kafka_security import kafka_client_kwargs
                producer = AIOKafkaProducer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                    **kafka_client_kwargs())
                await producer.start()
                evidence.save('quality-sending.json', {'envelope_sha256': digest(fused), 'never_republish': True})
                wire = (evidence.root / 'cases' / evidence.case / 'ingress' / 'fused-wire.json').read_bytes()
                require(json.loads(wire) == fused, 'original fused wire/body binding')
                ack = await producer.send_and_wait(state['broker']['quality_topic'], wire)
                evidence.save('quality-ack.json', {'topic': ack.topic, 'partition': ack.partition, 'offset': ack.offset})
                require(ack.partition == 0 and ack.offset == expected_index, 'quality broker coordinate')
                for _ in range(800):
                    if task.done():
                        await task
                    if (evidence.directory / 'worker-result.json').exists():
                        after = await broker_metadata(state)
                        if after['partitions'][0]['committed'] == expected_index + 1:
                            break
                    await asyncio.sleep(.1)
                else:
                    require(False, 'new group commit not confirmed')
                await worker.stop()
                stopped = True
                await asyncio.wait_for(task, 15)
        require(observation.http_seen == 1, 'exactly one model request required for quality')
        evidence.save('completed.json', {'committed': expected_index + 1, 'model_attempts': 1,
            'strict_raw_schema_observed_valid': (observation.raw_answer or {}).get('valid', False),
            'model_quality_accepted': False, 'requires_independent_review': True})
        if not (observation.raw_answer or {}).get('valid', False):
            evidence.stop('raw schema quality failed after original production processing completed')
    except BaseException as exc:
        failure = exc
        raise
    finally:
        cleanup_error = None
        try:
            if producer is not None:
                try:
                    await producer.stop()
                except BaseException as exc:
                    cleanup_error = exc
            if task is not None:
                try:
                    if not stopped:
                        await worker.stop()
                except BaseException as exc:
                    cleanup_error = cleanup_error or exc
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        finally:
            aiokafka.AIOKafkaConsumer = original_consumer
        if cleanup_error is not None:
            evidence.save('cleanup-failure.json', {'error_type': type(cleanup_error).__name__})
            if failure is None:
                raise cleanup_error


async def empty_preflight_products(investigation):
    from app.investigator import ledger
    pool = await ledger.get_pool()
    require(pool is not None, 'preflight PG observation')
    async with pool.acquire() as connection:
        async with connection.transaction(readonly=True):
            await ledger._set_rls_context(connection, investigation.tenant_id)
            row = await connection.fetchrow('''
SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1::uuid AND tenant_id=$2::uuid) AS runs,
 (SELECT count(*) FROM socai2_triage_budget_reservations WHERE run_id=$1::uuid AND tenant_id=$2::uuid) AS reservations,
 (SELECT count(*) FROM aisoc_run_costs WHERE run_id=($1::uuid)::text AND tenant_id=($2::uuid)::text) AS costs
''', investigation.run_id, investigation.tenant_id)
    return dict(row)


async def verify(state, item, evidence):
    import os
    import httpx
    import uuid
    from app.investigator import ledger
    from app.workers import fused_alert_consumer as module
    fused = read_json(evidence.root / 'cases' / evidence.case / 'ingress' / 'fused-envelope.json')
    investigation = module.build_state(fused)
    tenant, run_id = investigation.tenant_id, investigation.run_id
    base = '/api/v1/investigations/' + str(run_id)
    products = {}
    async with httpx.AsyncClient(base_url=os.getenv('API_SERVICE_URL', 'http://api:8000'), timeout=25,
                                trust_env=False) as client:
        _, products['alert'] = await api(client, state, item['tenant'], 'GET', '/api/v1/alerts/' + fused['alert_row_id'])
        status, products['run'] = await api(client, state, item['tenant'], 'GET', base, allowed=(200, 404))
        if status == 404:
            evidence.save('unconfirmed.json', {'run_absent': True, 'new_model_or_publish_attempts': 0})
            require(False, 'Run not durably visible')
        _, products['events'] = await api(client, state, item['tenant'], 'GET', base + '/events')
        _, products['artifacts'] = await api(client, state, item['tenant'], 'GET', base + '/artifacts')
        products['artifact_details'] = []
        for artifact in products['artifacts']:
            _, detail = await api(client, state, item['tenant'], 'GET', base + '/artifacts/' + artifact['id'])
            products['artifact_details'].append(detail)
        other = 'b' if item['tenant'] == 'a' else 'a'
        await api(client, state, other, 'GET', base + '/events', allowed=(404,))
        await api(client, state, None, 'GET', base + '/events', allowed=(401,))
        if 'denied' in state['identities']:
            await api(client, state, 'denied', 'GET', base + '/events', allowed=(403,))
    evidence.save('api-products.json', products)
    pool = await ledger.get_pool()
    require(pool is not None, 'PG readback pool')
    async with pool.acquire() as connection:
        async with connection.transaction(readonly=True):
            await ledger._set_rls_context(connection, tenant)
            rows = {}
            for name, table, key, argument, tenant_argument in (
                ('run', 'investigation_runs', 'id', run_id, tenant),
                ('events', 'investigation_events', 'run_id', run_id, tenant),
                ('artifacts', 'investigation_artifacts', 'run_id', run_id, tenant),
                ('costs', 'aisoc_run_costs', 'run_id', str(run_id), str(tenant)),
                ('reservation', 'socai2_triage_budget_reservations', 'run_id', run_id, tenant),
                ('shadow', 'aisoc_shadow_decisions', 'alert_id', uuid.UUID(fused['alert_row_id']), tenant)):
                values = await connection.fetch('SELECT row_to_json(t)::text AS material FROM ' + table +
                    ' t WHERE ' + key + '=$1 AND tenant_id=$2 ORDER BY row_to_json(t)::text', argument, tenant_argument)
                rows[name] = [json.loads(row['material']) for row in values]
    evidence.save('pg-products.json', rows)
    require(products['run']['status'] == 'completed', 'Run not completed')
    require(len(rows['run']) == len(rows['costs']) == len(rows['reservation']) == 1, 'Run/cost/budget row identity')
    require(len(rows['events']) == 3 and len(rows['artifacts']) == 7 and len(rows['shadow']) <= 1, 'case product bounds')
    require({row['kind'] for row in products['artifacts']} == set(READS) | {'llm_prompt', 'llm_response'}, 'artifact kinds')
    require([row['seq'] for row in products['events']['items']] == [-1, 0, 1], 'started/call/verdict event sequence')
    verdicts = [row for row in products['events']['items'] if row['kind'] == 'triage_verdict']
    require(len(verdicts) == 1, 'unique verdict event')
    verdict_event = verdicts[0]
    invocation_directory = evidence.root / 'cases' / evidence.case / 'invoke'
    before_persist = read_json(invocation_directory / 'before-persist.json')
    pre_messages = read_json(invocation_directory / 'egress-pre-messages.json')
    require(len(before_persist['llm_exchanges']) == 1, 'one actual ledger model exchange')
    exchange = before_persist['llm_exchanges'][0]
    require(not exchange['prompt_truncated'] and not exchange['response_truncated'], 'complete ledger literals')
    require(json.loads(exchange['prompt']) == pre_messages and len(exchange['prompt']) <= 8000,
            'ledger prompt equals actual pre-egress input')
    for detail in products['artifact_details']:
        require(file_sha_from_text(detail['content']) == detail['sha256'], 'API artifact content hash')
        require(detail['event_id'] == verdict_event['id'], 'artifact event relation')
        if detail['kind'] in READS:
            require(json.loads(detail['content']) == before_persist['reads'][detail['kind']] ==
                    verdict_event['payload'][detail['kind']], 'adopted reader evidence relation')
        elif detail['kind'] == 'llm_prompt':
            require(detail['content'] == exchange['prompt'] and detail['sha256'] == exchange['input_hash'],
                    'prompt artifact relation')
        elif detail['kind'] == 'llm_response':
            require(detail['content'] == exchange['response'] and detail['sha256'] == exchange['output_hash'],
                    'response artifact relation')
    require(verdict_event['input_hash'] == exchange['input_hash'] and
            verdict_event['output_hash'] == exchange['output_hash'], 'verdict input/output hash relation')
    reservation = rows['reservation'][0]
    require(reservation['outcome'] == 'responded' and reservation['settled_at'] is not None and
            reservation['charged_tokens'] == 20000, 'actual settled reservation')
    require(products['run']['total_tokens'] == rows['costs'][0]['total_prompt_tokens'] +
            rows['costs'][0]['total_completion_tokens'], 'actual usage ledger equality')
    raw = read_json(invocation_directory / 'raw-answer-selected.json')
    usage = raw.get('usage') or {}
    usage_confirmed = (all(type(usage.get(key)) is int and usage[key] >= 0
                           for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')) and
                       usage['prompt_tokens'] + usage['completion_tokens'] == usage['total_tokens'] and
                       reservation['observed_tokens'] == usage['total_tokens'] == products['run']['total_tokens'])
    require(rows['costs'][0]['call_count'] == 1, 'one cost call')
    require(rows['run'][0]['tenant_id'] == str(tenant) and rows['reservation'][0]['tenant_id'] == str(tenant),
            'owner Run/reservation identity')
    require(rows['run'][0]['id'] == str(run_id) and rows['run'][0]['case_id'] == fused['alert_row_id'],
            'exact Run/canonical Alert identity')
    expected_shadow = before_persist['writer_class'] == 'ShadowModeTriageWriter'
    require(len(rows['shadow']) == (1 if expected_shadow else 0), 'original shadow policy durable receipt')
    broker = await broker_metadata(state)
    committed = CASES.index(evidence.case) + 1
    require(broker['partitions'] == [{'partition': 0, 'begin': 0, 'end': committed, 'committed': committed}],
            'new group acknowledged final position')
    commit = read_json(invocation_directory / 'worker-commit-confirmed.json')
    require(commit['committed'] == committed, 'actual worker commit confirmation')
    evidence.save('broker-final.json', broker)
    source = evidence.root / 'cases' / evidence.case
    raw_schema = read_json(source / 'invoke' / 'raw-schema-observation.json')
    completion = {'case': evidence.case, 'input_sha256': INPUT_SHA256, 'run_id': str(run_id),
        'tenant_id': str(tenant), 'infrastructure_passed': True,
        'gate_eligible': raw_schema.get('valid') is True and usage_confirmed,
        'raw_schema_valid': raw_schema.get('valid') is True,
        'actual_usage_confirmed': usage_confirmed,
        'raw_answer_sha256': file_sha(source / 'invoke' / 'raw-answer-selected.json'),
        'sdk_body_sha256': file_sha(source / 'invoke' / 'sdk-request-body.json'),
        'fact_projection_sha256': file_sha(source / 'invoke' / 'fact-projection.json'),
        'pg_products_sha256': file_sha(evidence.directory / 'pg-products.json'),
        'api_products_sha256': file_sha(evidence.directory / 'api-products.json'),
        'quality_requires_external_gate': True}
    evidence.save('case-completed.json', completion)
    if not completion['gate_eligible']:
        evidence.stop('raw schema or actual usage confirmation failed; no next case')


def file_sha_from_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


async def inside_main(phase, case):
    import logging
    import structlog
    from app.investigator import ledger
    require(__import__('os').environ.get('C03_RECOVERY_CONTRACT_ONLY') != '1', 'contract-only probe cannot execute a business phase')
    state, _, item = check_contract(phase, case)
    evidence = Evidence('/evidence', case, phase)
    evidence.save('started.json', {'phase': phase, 'case': case, 'input_sha256': INPUT_SHA256,
        'source_sha256': digest(state['source_sha256']), 'prompt_lock_sha256': state['prompt_lock_sha256'],
        'operator_sha256': state['operator_sha256'], 'resident_worker_remains_disabled': True})
    def drop(_logger, _method, _event):
        raise structlog.DropEvent
    structlog.configure(processors=[drop])
    logging.disable(logging.CRITICAL)
    failure = None
    try:
        # One watcher covers source reads, polls, owner/auth verification and
        # the SDK. Only the explicit preflight client is marked MockTransport.
        with count_http(evidence):
            await globals()[phase](state, item, evidence)
    except BaseException as exc:
        failure = exc
        evidence.save('failure.json', {'error_type': type(exc).__name__, 'automatic_retry': False,
            'original_sending_and_model_checkpoints_preserved': True})
        evidence.stop('phase_failed; inspect read-only and do not replay', type(exc).__name__)
        raise
    finally:
        try:
            await ledger.close_pool()
        except BaseException as exc:
            evidence.save('ledger-cleanup-failure.json', {'error_type': type(exc).__name__,
                'primary_phase_error_type': type(failure).__name__ if failure is not None else None})
            evidence.stop('ledger pool cleanup failed; no next case', type(exc).__name__)
            if failure is None:
                raise


if __name__ == '__main__':
    import sys
    sys.dont_write_bytecode = True
    if len(sys.argv) != 3:
        raise SystemExit('usage: quality.py {ingress|preflight|invoke|verify} case01..case04')
    try:
        asyncio.run(inside_main(*sys.argv[1:]))
    except BaseException as exc:
        # Do not expose traceback locals, provider errors or secret headers.
        print(json.dumps({'phase_failed': True, 'error_type': type(exc).__name__, 'retry_allowed': False}))
        raise SystemExit(1)
