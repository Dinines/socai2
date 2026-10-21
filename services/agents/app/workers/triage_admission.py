"""Explicit human-review admission for ordinary Kafka live triage only.

No writer wrapper, I/O, model call or storage dependency. Legacy is the default.
The policy's numeric confidence sentinel is never a model estimate or Alert score.
"""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
import math
import os
import re
from typing import Any, Iterator
from uuid import UUID

ENV = 'AISOC_TRIAGE_ADMISSION_PROFILE'
LEGACY = 'legacy'
REVIEW_ONLY = 'review_only_v1'
_SCOPE: ContextVar[str | None] = ContextVar('ordinary_live_triage_admission', default=None)
_REASON = ('Human review required; effective confidence is unknown; numeric confidence 0 is a policy sentinel, '
           'not a model estimate. Model advice has not been accepted as a decision.')
_EFFECTIVE = {'verdict': 'needs_review', 'confidence': None, 'review_required': True, 'reason': _REASON}
_VERDICTS = {'true_positive', 'benign_true_positive', 'false_positive', 'benign', 'needs_review'}


class ReviewOnlyHold(RuntimeError):
    """No permission to reinterpret an old result or enter an untested path."""


def configured_profile() -> str:
    value = os.getenv(ENV, LEGACY).strip()
    if value not in {LEGACY, REVIEW_ONLY}:
        raise ReviewOnlyHold('Invalid triage admission profile')
    return value


@contextmanager
def ordinary_live_scope(profile: str) -> Iterator[None]:
    token = _SCOPE.set(profile)
    try:
        yield
    finally:
        _SCOPE.reset(token)


def agent_profile() -> str:
    profile = configured_profile()
    scope = _SCOPE.get()
    if scope is not None and scope != profile:
        raise ReviewOnlyHold('Triage admission profile changed within its live scope')
    if profile == REVIEW_ONLY and scope != REVIEW_ONLY:
        raise ReviewOnlyHold('Review-only auto-triage requires ordinary Kafka live admission')
    return profile


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def identity(state: Any) -> dict[str, str]:
    return {'run_id': str(state.run_id), 'tenant_id': str(state.tenant_id),
            'alert_id': str((state.raw_alert or {}).get('id') or '')}


def _strict_advice(response: str) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('Duplicate JSON key')
            obj[key] = value
        return obj
    def reject_constant(value: str) -> None:
        raise ValueError('Non-finite JSON number')
    try:
        value = json.loads(response, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (TypeError, ValueError) as exc:
        raise ReviewOnlyHold('Model advice must retain a strict original JSON object') from exc
    if (not isinstance(value, dict) or not isinstance(value.get('verdict'), str) or value['verdict'] not in _VERDICTS
            or type(value.get('confidence')) not in (int, float)
            or not 0 <= value['confidence'] <= 1 or not math.isfinite(value['confidence'])
            or not isinstance(value.get('rationale'), str) or not 0 < len(value['rationale']) <= 8000):
        raise ReviewOnlyHold('Original advice has an invalid schema')
    # Extra provider-visible fields stay in the original transcript; only the
    # existing three-field contract is admitted, without normalization.
    return {key: value[key] for key in ('verdict', 'confidence', 'rationale')}


def _validate_exchange(advice: dict[str, Any] | None, exchanges: Any) -> None:
    if advice is None:
        if exchanges:
            raise ReviewOnlyHold('A received model response cannot become advice-free fallback')
        return
    if (not isinstance(exchanges, list) or len(exchanges) != 1
            or not isinstance(exchanges[0], dict)
            or exchanges[0].get('response_truncated') or exchanges[0].get('prompt_truncated')):
        raise ReviewOnlyHold('A complete first model exchange is required')
    exchange = exchanges[0]
    response = exchange.get('response')
    if (not isinstance(response, str)
            or hashlib.sha256(response.encode()).hexdigest() != exchange.get('output_hash')
            or advice['raw_response_sha256'] != exchange['output_hash']
            or _strict_advice(response) != {key: advice[key] for key in ('verdict', 'confidence', 'rationale')}):
        raise ReviewOnlyHold('Advisory response differs from its first exchange')


def enforce(state: Any, *, advice: dict[str, Any] | None = None) -> dict[str, Any]:
    """Idempotently retain advice while making the effective decision inert."""
    old = state.triage_admission
    if old is not None:
        validate(old, **identity(state))
        receipt = deepcopy(old)
        if advice is not None and (receipt['model_advice'] is None or
                any(receipt['model_advice'][key] != advice.get(key) for key in ('verdict', 'confidence', 'rationale'))):
            raise ReviewOnlyHold('A first advisory receipt cannot be replaced')
    else:
        model_advice = None
        if advice is not None:
            exchanges = state.llm_exchanges
            if not isinstance(exchanges, list) or len(exchanges) != 1 or not isinstance(exchanges[0], dict):
                raise ReviewOnlyHold('A complete first model exchange is required')
            model_advice = {'verdict': advice['verdict'], 'confidence': advice['confidence'],
                            'rationale': advice['rationale'], 'raw_response_sha256': exchanges[0].get('output_hash'),
                            'stage': 'SDK_visible_egress_restored_preparse', 'review_status': 'unreviewed'}
        receipt = {'schema_version': 1, 'profile': REVIEW_ONLY, **identity(state),
            'source_raw_alert_sha256': _digest(state.raw_alert or {}),
            'review_status': 'unreviewed', 'model_advice': model_advice,
            'effective_decision': deepcopy(_EFFECTIVE),
            'confidence_scope': 'policy_sentinel_not_model_estimate',
            'canonical_Alert_update_allowed': False}
        validate(receipt, **identity(state))
    if receipt['source_raw_alert_sha256'] != _digest(state.raw_alert or {}):
        raise ReviewOnlyHold('First advisory source snapshot changed')
    _validate_exchange(receipt['model_advice'], state.llm_exchanges)
    state.triage_admission = deepcopy(receipt)
    state.verdict = 'needs_review'
    state.confidence = 0.0  # Legacy numeric plumbing only; effective confidence is null.
    state.status = type(state.status).RUNNING
    state.completed_at = None
    state.proposed_actions = []
    # Do not let old model prose stand as the effective policy rationale.
    state.confidence_basis = ['Review-only profile: model advice is unreviewed', 'Rationale: ' + _REASON]
    state.findings = ['Review-only profile: human review required; no automated disposition or actions.']
    return deepcopy(receipt)


def validate(receipt: Any, *, run_id: str, tenant_id: str, alert_id: str) -> None:
    expected = {'schema_version', 'profile', 'run_id', 'tenant_id', 'alert_id',
                'source_raw_alert_sha256', 'review_status', 'model_advice', 'effective_decision',
                'confidence_scope', 'canonical_Alert_update_allowed'}
    if (not isinstance(receipt, dict) or set(receipt) != expected
            or type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
            or receipt.get('profile') != REVIEW_ONLY or receipt.get('review_status') != 'unreviewed'
            or any(receipt.get(k) != v for k, v in {'run_id': run_id, 'tenant_id': tenant_id, 'alert_id': alert_id}.items())
            or not re.fullmatch('[0-9a-f]{64}', str(receipt.get('source_raw_alert_sha256', '')))
            or receipt.get('effective_decision') != _EFFECTIVE
            or receipt.get('confidence_scope') != 'policy_sentinel_not_model_estimate'
            or receipt.get('canonical_Alert_update_allowed') is not False):
        raise ReviewOnlyHold('Invalid first advisory receipt')
    try:
        if any(str(UUID(value)) != value for value in (run_id, tenant_id, alert_id)):
            raise ValueError('Non-canonical UUID')
    except (ValueError, TypeError, AttributeError) as exc:
        raise ReviewOnlyHold('Canonical advisory identity required') from exc
    advice = receipt['model_advice']
    if advice is not None:
        if (not isinstance(advice, dict) or set(advice) != {'verdict', 'confidence', 'rationale', 'raw_response_sha256', 'stage', 'review_status'}
                or not isinstance(advice.get('verdict'), str) or advice['verdict'] not in _VERDICTS
                or type(advice.get('confidence')) not in (float, int)
                or not 0 <= advice['confidence'] <= 1 or not math.isfinite(advice['confidence'])
                or not isinstance(advice.get('rationale'), str) or not 0 < len(advice['rationale']) <= 8000
                or not re.fullmatch('[0-9a-f]{64}', str(advice.get('raw_response_sha256', '')))
                or advice.get('stage') != 'SDK_visible_egress_restored_preparse' or advice.get('review_status') != 'unreviewed'):
            raise ReviewOnlyHold('Invalid unreviewed model advice')


def validate_projection(result: Any, *, run_id: str, tenant_id: str, alert_id: str, persisted: bool = False) -> None:
    if not isinstance(result, dict):
        raise ReviewOnlyHold('Missing first review-only projection')
    validate(result.get('triage_admission'), run_id=run_id, tenant_id=tenant_id, alert_id=alert_id)
    if (result.get('verdict') != 'needs_review' or type(result.get('confidence')) not in (int, float)
            or result['confidence'] != 0 or result.get('proposed_actions') != []
            or result.get('response_dispatched') is not False or result.get('approvals_raised') != []
            or result.get('source_writeback') is not None):
        raise ReviewOnlyHold('First result is not an inert review-only result')
    if persisted:
        # The original delivery validator already checked the first event,
        # transcript linkage, source artifacts and artifact contents. Bind this
        # profile's raw advice to its returned, actually hashed response artifact.
        artifacts = result.get('persisted_artifacts')
        if result.get('reused_persisted') is not True or not isinstance(artifacts, list):
            raise ReviewOnlyHold('Completed advisory lacks first-result artifact proof')
        responses = [item for item in artifacts if isinstance(item, dict) and item.get('kind') == 'llm_response']
        advice = result['triage_admission']['model_advice']
        if ((advice is None and responses) or (advice is not None and
                (len(responses) != 1 or responses[0].get('sha256') != advice['raw_response_sha256']))):
            raise ReviewOnlyHold('Persisted raw advice differs from its first response artifact')


def validate_persistence(receipt: Any, *, projection: Any, run_id: str, tenant_id: str,
                         alert_id: str, verdict: str, confidence: float, auto_closed: bool,
                         recommendations: Any, raw_alert: dict[str, Any], exchanges: Any) -> None:
    validate(receipt, run_id=run_id, tenant_id=tenant_id, alert_id=alert_id)
    validate_projection(projection, run_id=run_id, tenant_id=tenant_id, alert_id=alert_id)
    if (projection['triage_admission'] != receipt or verdict != 'needs_review' or confidence != 0
            or auto_closed is not False or recommendations or _digest(raw_alert) != receipt['source_raw_alert_sha256']):
        raise ReviewOnlyHold('Advisory persistence differs from its first receipt')
    _validate_exchange(receipt['model_advice'], exchanges)


def held_in_chain(error: BaseException) -> bool:
    seen = set()
    while error is not None and id(error) not in seen:
        if isinstance(error, ReviewOnlyHold):
            return True
        seen.add(id(error))
        error = error.__cause__ or error.__context__
    return False
