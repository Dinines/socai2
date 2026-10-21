"""Atomic business-rule receipts in the existing append-only investigation ledger.

No model verdict, outcome prior, alert mutation or external action is implied.
One receipt per tenant/alert/policy/mode; a changed input under that same key
is a conflict, never an overwrite of the first frozen decision.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from app.investigator import ledger

NAMESPACE = uuid.UUID('813b8f90-6f13-4e40-970d-d95142caa981')


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


async def persist_policy_suppression(*, tenant_ref: str, alert_id: str,
                                     raw_alert: dict[str, Any], policy: dict[str, Any],
                                     matched_rules: list[str], shadow: bool = False) -> dict[str, Any]:
    try:
        tenant, alert = uuid.UUID(tenant_ref), uuid.UUID(alert_id)
        if raw_alert.get("tenant_id") and uuid.UUID(str(raw_alert["tenant_id"])) != tenant:
            raise ValueError("Conflicting input tenant")
        revisions = {k: policy.get(k) for k in ('policy_revision', 'file_revision')}
        if not any(revisions.values()) or not matched_rules:
            raise ValueError('Suppression requires observed policy revision and matching rules')
        basis = {**revisions, 'matched_rules': sorted(set(matched_rules)), 'shadow': shadow}
        run_id = uuid.uuid5(NAMESPACE, f'{tenant}:{alert}:' + canonical(basis))
        input_hash = hashlib.sha256(canonical(raw_alert).encode()).hexdigest()
        payload = {'schema': 'policy-suppression-v1', 'decision': 'suppress',
                   'tenant_id': str(tenant), 'alert_id': str(alert), 'run_id': str(run_id),
                   'business_context_policy': policy, 'business_context_rules': matched_rules,
                   'shadow': shadow, 'input_hash': input_hash, 'model_called': False,
                   'response_dispatched': False}
        pool = await ledger.get_pool()
        if pool is None:
            raise ledger.LedgerPersistError('Policy receipt database unavailable')
        async with pool.acquire() as conn:
            async with conn.transaction():
                await ledger._set_rls_context(conn, tenant)
                await conn.execute("SET LOCAL statement_timeout = '5s'")
                if not await conn.fetchval('SELECT id FROM alerts WHERE id=$1 AND tenant_id=$2', alert, tenant):
                    raise ledger.LedgerPersistError('Policy receipt alert not found in tenant')
                # Run insertion serializes concurrent same-key writers. Only the
                # winning transaction inserts the event; neither branch updates.
                inserted = await conn.fetchval('''
                    INSERT INTO investigation_runs
                      (id,tenant_id,case_id,alert_summary,raw_alert,model_used,status,completed_at)
                    VALUES ($1,$2,$3,$4,$5::jsonb,'policy:business_context:suppression-v1','completed',now())
                    ON CONFLICT (id) DO NOTHING RETURNING id
                ''', run_id, tenant, str(alert), str(raw_alert.get('title') or '')[:8000], canonical(raw_alert))
                if inserted:
                    await conn.execute('''
                        INSERT INTO investigation_events
                          (id,run_id,tenant_id,seq,kind,agent,summary,payload,input_hash)
                        VALUES ($1,$2,$3,1,'policy_decision','business_context',
                                'Business rule suppression; no model verdict',$4::jsonb,$5)
                    ''', uuid.uuid4(), run_id, tenant, canonical(payload), input_hash)
                stored = await conn.fetchval('''
                    SELECT payload FROM investigation_events
                    WHERE run_id=$1 AND tenant_id=$2 AND seq=1 AND kind='policy_decision'
                ''', run_id, tenant)
                receipt = json.loads(stored) if isinstance(stored, str) else stored
                if not receipt or receipt.get('input_hash') != input_hash:
                    raise ledger.LedgerPersistError('Policy receipt input conflict or missing event')
        return {**receipt, 'persisted': True}
    except ledger.LedgerPersistError:
        raise
    except Exception as exc:
        # No SQL/connection values in retry logs or DLQ error strings.
        raise ledger.LedgerPersistError(f'Policy receipt failed ({type(exc).__name__})') from exc
