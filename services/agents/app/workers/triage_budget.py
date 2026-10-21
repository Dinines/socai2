"""Conservative, durable admission for configured ordinary live Kafka triage.

Charges are reservations, never claims about provider usage or dollars. Unknown
calls retain their concurrency slot until explicitly resolved outside this path.
"""
from __future__ import annotations

import contextlib
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterator
from uuid import UUID

from app.investigator import ledger

POLICY_FILE_ENV = 'AISOC_TRIAGE_BUDGET_POLICY_FILE'
PROMPT_BYTE_CAP = 16000
RESERVED_TOKENS = 20000


class BudgetHold(ledger.LedgerPersistError):
    """No durable authority for further work: retain the Kafka offset, no DLQ."""


@dataclass(frozen=True)
class Policy:
    window_seconds: int
    max_calls: int
    max_reserved_tokens: int
    max_unsettled: int

    @property
    def sha256(self) -> str:
        fields = {**self.__dict__, 'schema_version': 1, 'per_request_reserved_tokens': RESERVED_TOKENS,
                  'prompt_byte_cap': PROMPT_BYTE_CAP, 'output_token_cap': 512}
        return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def policy_for(tenant_id: UUID) -> Policy | None:
    filename = os.getenv(POLICY_FILE_ENV, '').strip()
    if not filename:
        return None  # Preserve callers/deployments which have not opted in.
    try:
        raw = Path(filename).read_bytes()
        if len(raw) > 65536:
            raise ValueError('oversized policy')
        data = json.loads(raw)
        if set(data) != {'schema_version', 'tenants'} or type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('policy version')
        if not isinstance(data['tenants'], dict) or len(data['tenants']) > 100:
            raise ValueError('tenant mapping')
        if any(str(UUID(k)) != k for k in data['tenants']):
            raise ValueError('canonical tenant mapping')
        row = data['tenants'][str(tenant_id)]
        bounds = {'window_seconds': (60, 86400), 'max_calls': (1, 1000),
                  'max_reserved_tokens': (1, 20000000), 'max_unsettled': (1, 8)}
        if not isinstance(row, dict) or set(row) != set(bounds):
            raise ValueError('policy fields')
        if any(type(row[k]) is not int or not low <= row[k] <= high for k, (low, high) in bounds.items()):
            raise ValueError('policy bounds')
        return Policy(**row)
    except Exception as exc:
        raise BudgetHold('Triage budget policy unavailable or invalid') from exc


async def check_locked(conn: Any, tenant_id: UUID, policy: Policy) -> None:
    key = int.from_bytes(hashlib.sha256(('socai2:triage-budget:' + str(tenant_id)).encode()).digest()[:8],
                         'big', signed=True)
    await conn.execute('SELECT pg_advisory_xact_lock($1::bigint)', key)
    # Lock first, then use a fresh READ COMMITTED snapshot shared by every
    # policy version. Changing a file cannot reset prior charges/unknown calls.
    row = await conn.fetchrow('''
SELECT count(*) FILTER (WHERE reserved_at > clock_timestamp() - $2 * interval '1 second') AS calls,
       COALESCE(sum(charged_tokens) FILTER (WHERE reserved_at > clock_timestamp() - $2 * interval '1 second'), 0) AS tokens,
       count(*) FILTER (WHERE settled_at IS NULL) AS unsettled
  FROM socai2_triage_budget_reservations WHERE tenant_id = $1
''', tenant_id, policy.window_seconds)
    if (row['calls'] + 1 > policy.max_calls or row['tokens'] + RESERVED_TOKENS > policy.max_reserved_tokens
            or row['unsettled'] + 1 > policy.max_unsettled):
        raise BudgetHold('Triage budget exhausted or prior invocation unconfirmed')


async def reserve(conn: Any, *, run_id: UUID, tenant_id: UUID, policy: Policy) -> None:
    await conn.execute('''
INSERT INTO socai2_triage_budget_reservations(run_id,tenant_id,policy_sha256,charged_tokens)
VALUES ($1,$2,$3,$4)
''', run_id, tenant_id, policy.sha256, RESERVED_TOKENS)


async def _update(run_id: UUID, tenant_id: UUID, statement: str, *args: Any) -> None:
    try:
        pool = await ledger.get_pool()
        if pool is None:
            raise BudgetHold('Triage budget database unavailable')
        async with pool.acquire() as conn:
            async with conn.transaction():
                await ledger._set_rls_context(conn, tenant_id)
                row = await conn.fetchrow(statement, run_id, tenant_id, *args)
                if row is None:
                    raise BudgetHold('Triage budget reservation identity or state mismatch')
    except BudgetHold:
        raise
    except Exception as exc:
        raise BudgetHold('Triage budget confirmation failed; invocation remains unconfirmed') from exc


@dataclass
class Invocation:
    run_id: UUID
    tenant_id: UUID
    stopping: Callable[[], bool]
    request_marked: bool = False
    response_seen: bool = False

    async def before_request(self, llm: Any, outbound: Any, kwargs: dict[str, Any]) -> None:
        from app.llm.contract_rules import LLMInputContract

        if self.stopping():
            raise BudgetHold('Triage worker is stopping')
        body = LLMInputContract.validate(outbound)
        size = len(json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        root = getattr(llm, 'root_async_client', None)
        if (self.request_marked or kwargs or size > PROMPT_BYTE_CAP
                or getattr(llm, 'max_tokens', None) != 512
                or getattr(llm, 'request_timeout', None) != 45.0
                or getattr(root, 'max_retries', None) != 0 or getattr(root, 'timeout', None) != 45.0
                or (getattr(llm, 'extra_body', None) or {}).get('max_tokens', 512) != 512):
            raise BudgetHold('Triage invocation exceeds its reserved request contract')
        await _update(self.run_id, self.tenant_id, '''
UPDATE socai2_triage_budget_reservations SET request_started_at=clock_timestamp()
 WHERE run_id=$1 AND tenant_id=$2 AND outcome='reserved' AND request_started_at IS NULL
 RETURNING run_id
''')
        self.request_marked = True
        # A stop could have arrived while the transaction awaited its commit.
        if self.stopping():
            raise BudgetHold('Triage worker stopped after request intent; outcome unconfirmed')

    async def responded(self, response: Any) -> None:
        self.response_seen = True
        usage = getattr(response, 'usage_metadata', None)
        tokens = usage.get('total_tokens') if isinstance(usage, dict) else None
        if tokens is not None and (type(tokens) is not int or not 0 <= tokens <= RESERVED_TOKENS):
            raise BudgetHold('Triage response usage exceeds or invalidates its reservation')
        await _update(self.run_id, self.tenant_id, '''
UPDATE socai2_triage_budget_reservations
 SET outcome='responded',settled_at=clock_timestamp(),observed_tokens=$3
 WHERE run_id=$1 AND tenant_id=$2 AND outcome='reserved' AND request_started_at IS NOT NULL
 RETURNING run_id
''', tokens)

    async def no_request(self) -> None:
        await _update(self.run_id, self.tenant_id, '''
UPDATE socai2_triage_budget_reservations SET outcome='no_request',settled_at=clock_timestamp()
 WHERE run_id=$1 AND tenant_id=$2 AND outcome='reserved' AND request_started_at IS NULL
 RETURNING run_id
''')


_INVOCATION: ContextVar[Invocation | None] = ContextVar('socai2_triage_budget', default=None)


def current_invocation() -> Invocation | None:
    return _INVOCATION.get()


@contextlib.contextmanager
def invocation_scope(invocation: Invocation | None) -> Iterator[None]:
    token = _INVOCATION.set(invocation)
    try:
        yield
    finally:
        _INVOCATION.reset(token)


def hold_in_chain(error: BaseException) -> BudgetHold | None:
    seen = set()
    while error is not None and id(error) not in seen:
        if isinstance(error, BudgetHold):
            return error
        seen.add(id(error))
        error = error.__cause__
    return None
