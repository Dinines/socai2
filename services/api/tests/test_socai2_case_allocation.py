"""Focused configuration and receiving-window checks; PG writes use the evidence driver."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.socai2.baseline_store import StoreError
from app.socai2.case_allocation_policy import CaseAllocationPolicy
from app.socai2.case_relationship_reader import receiving_status


def test_capacity_requires_explicit_complete_profile(monkeypatch, tmp_path):
    monkeypatch.delenv('SOCAI2_CASE_ALLOCATION_CONFIG_FILE', raising=False)
    with pytest.raises(StoreError, match='service_unavailable'):
        CaseAllocationPolicy.load()
    path = tmp_path / 'case.json'
    path.write_text('{"case":{"max_alerts":3},"source_page_size":2,"default_limit":2,"max_limit":10}')
    monkeypatch.setenv('SOCAI2_CASE_ALLOCATION_CONFIG_FILE', str(path))
    policy = CaseAllocationPolicy.load()
    assert policy.max_alerts == 3 and policy.page_size(None) == 2
    with pytest.raises(StoreError, match='invalid_input'):
        policy.page_size(11)
    path.write_text('{"case":{"max_alerts":0},"source_page_size":2,"default_limit":2,"max_limit":10}')
    with pytest.raises(StoreError, match='service_unavailable'):
        CaseAllocationPolicy.load()


@pytest.mark.asyncio
@pytest.mark.parametrize(('closed','last_days','expected'), [(False,1,None),(False,None,'auto_window_expired'),(True,1,'closed')])
async def test_receiving_window_uses_completed_time_and_ignores_analysis_stop(closed,last_days,expected):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    now = datetime(2026,11,15,tzinfo=UTC)
    cid = uuid4()
    store = SimpleNamespace(case=AsyncMock(return_value={'id':cid,'handling_status':'resolved' if closed else 'new',
        'created_at':now-timedelta(days=8)}), now=AsyncMock(return_value=now),where=lambda *args: (),
        one=AsyncMock(return_value={'last_normal_completed_at':now-timedelta(days=last_days) if last_days else None,
            'automatic_stop_reason':'automatic_attempts_stopped'}))
    value = await receiving_status(store,{'active_case_id':cid},SimpleNamespace(automatic_window_seconds=7*24*3600))
    assert value.reason_code == expected and value.can_receive_automatically == (expected is None)


@pytest.mark.asyncio
async def test_missing_receiver_does_not_guess_a_case():
    value = await receiving_status(None,{'active_case_id':None},None)
    assert value.active_case_id is None and value.reason_code == 'no_target'
