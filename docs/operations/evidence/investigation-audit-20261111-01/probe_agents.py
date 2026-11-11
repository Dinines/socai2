"""Retained Agents Hunt audit; real routes/scheduler/engine/store, external IO replaced.

Run separately from API probes with PYTHONPATH=services/agents.
These assertions document existing defects; they are not desired acceptance criteria.
"""
import asyncio
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request

from app.api import hunts
from app.hunt import lake_source, scheduler, store
from app.security.tenant_scope import TenantPrincipal, require_console_or_service_auth

# Replays must not overwrite the completed audit batch.
OUT = Path(tempfile.mkdtemp(prefix='socai2-audit-agents-'))
TENANT = '00000000-0000-0000-0000-000000000001'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def deny(*args, **kwargs):
        raise AssertionError('audit_network_not_allowed')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)


def test_lake_failure_is_recorded_as_completed_zero(monkeypatch):
    inserted = []
    class Connection:
        async def fetchrow(self, *args):
            return None  # no preexisting hypothesis; UUID tenant needs no lookup
        async def execute(self, sql, *args):
            if 'INSERT INTO hunt_runs' in sql:
                inserted.append({'tenant_id': str(args[1]), 'status': args[5],
                                 'events_scanned': args[6], 'findings_count': args[7], 'error': args[9]})
    class Acquire:
        async def __aenter__(self): return Connection()
        async def __aexit__(self, *args): pass
    async def pool(): return SimpleNamespace(acquire=lambda: Acquire())
    def failed_read(tenant_ref):
        assert tenant_ref == TENANT
        raise TimeoutError('audit injected lake timeout')
    monkeypatch.setattr(store, '_get_pool', pool)
    monkeypatch.setattr(lake_source, 'fetch_recent_events', failed_read)
    monkeypatch.setenv('HUNT_TELEMETRY_PROVIDER', 'lake')
    async def scenario():
        hunt = SimpleNamespace(id='audit-hunt')
        sched = scheduler.HuntScheduler(corpus=SimpleNamespace(get=lambda _: hunt), tenant_ref=TENANT)
        return await sched.run_one(hunt.id)
    response = asyncio.run(scenario())
    assert response['ok'] is True and response['events_scanned'] == 0
    assert inserted == [{'tenant_id': TENANT, 'status': 'completed', 'events_scanned': 0,
                         'findings_count': 0, 'error': None}]
    (OUT/'hunt-failure.json').write_text(json.dumps({'injected_source_error': 'TimeoutError',
        'response': response, 'insert_parameters': inserted,
        'components': 'real loader/scheduler/engine/store; lake raises; SQL connection spy; no DB'}, indent=2)+'\n')


def test_authenticated_tenant_is_not_propagated_to_hunt_handlers(monkeypatch):
    app = FastAPI()
    app.include_router(hunts.router)
    principals, reads, runs = [], [], []
    async def principal(request: Request):
        tid = request.headers['x-audit-tenant']
        principals.append(tid)
        return TenantPrincipal(tenant_ids=frozenset({UUID(tid)}), subject='audit-authenticated')
    app.dependency_overrides[require_console_or_service_auth] = principal
    async def list_runs(*, tenant_ref='default', limit=50):
        reads.append({'kind': 'runs', 'tenant_ref': tenant_ref})
        return [{'tenant_marker': tenant_ref}]
    async def list_findings(*, tenant_ref='default', **kwargs):
        reads.append({'kind': 'findings', 'tenant_ref': tenant_ref})
        return [{'tenant_marker': tenant_ref}]
    async def record(hunt, result, *, tenant_ref='default', **kwargs):
        runs.append(tenant_ref)
    monkeypatch.setattr(store, 'list_recent_runs', list_runs)
    monkeypatch.setattr(store, 'list_recent_findings', list_findings)
    monkeypatch.setattr(scheduler, 'record_run', record)
    monkeypatch.setattr(scheduler, '_load_telemetry', lambda tenant_ref: [])
    async def scenario():
        sched = scheduler.HuntScheduler(corpus=SimpleNamespace(get=lambda _: SimpleNamespace(id='audit-hunt')))
        monkeypatch.setattr(scheduler, 'get_scheduler', lambda: sched)
        responses = []
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://audit.invalid') as client:
            for tenant in [TENANT, '00000000-0000-0000-0000-000000000002']:
                for method, path in [('GET','runs'), ('GET','findings'), ('POST','audit-hunt/run')]:
                    r = await client.request(method, '/api/v1/hunts/'+path, headers={'x-audit-tenant': tenant})
                    assert r.status_code == 200
                    responses.append({'principal': tenant, 'path': path, 'body': r.json()})
        return responses
    responses = asyncio.run(scenario())
    assert len(principals) == 6 and {r['tenant_ref'] for r in reads} == {'default'}
    assert runs == ['default', 'default']
    (OUT/'hunt-tenant.json').write_text(json.dumps({'authenticated_principals': principals,
        'reads': reads, 'run_tenants': runs, 'responses': responses,
        'components': 'real ASGI routes/scheduler/engine; verified-principal fixture, read/persist/telemetry spies; no real JWT or database'}, indent=2)+'\n')
