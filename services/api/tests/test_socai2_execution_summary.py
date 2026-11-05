"""Frozen execution capability reads: no network, model or current config inference."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.socai2.baseline_store import StoreError
from app.socai2.case_reader import CaseReader


@pytest.mark.asyncio
async def test_execution_summary_preserves_frozen_limits_and_missing_historic_capability():
    reader = CaseReader(SimpleNamespace(db=None))
    cid, rid, aid = (UUID(int=n) for n in (1, 2, 3))
    steps = [{"stage_code": "C1.executor", "state": "completed", "output_artifact_id": aid}]
    body = {"type": "execution_plan", "run_id": str(rid), "schema_version": "socai2.baseline-executor.v1",
        "limits": {"max_tokens": 24000}, "limitations": ["historical_limit"]}
    reader.artifact = AsyncMock(return_value={"availability": "available", "content_json": body})
    value = await reader.execution_summary(cid, rid, steps)
    assert value.limits == {"max_tokens": 24000}
    assert value.capabilities is None and value.final_reservation is None
    reader.artifact.assert_awaited_once_with(cid, rid, aid)
    body.update(schema_version="socai2.baseline-executor.v2", limits={"max_tokens": 48000},
        capabilities={"bound_tools": [], "binding_count": 0, "unsupported": ["host_missing"]},
        final_reservation={"model_calls": 1, "seconds": 30})
    value = await reader.execution_summary(cid, rid, steps)
    assert value.capabilities == body["capabilities"]
    assert value.final_reservation == body["final_reservation"]
    assert await reader.execution_summary(cid, rid, []) is None


@pytest.mark.asyncio
async def test_execution_summary_requires_linked_verified_artifact_and_keeps_unavailable():
    reader = CaseReader(SimpleNamespace(db=None))
    cid, rid, aid = (UUID(int=n) for n in (1, 2, 3))
    steps = [{"stage_code": "C1.executor", "state": "completed", "output_artifact_id": aid}]
    reader.artifact = AsyncMock(return_value={"availability": "external_content_not_loaded", "content_json": None})
    summary = await reader.execution_summary(cid, rid, steps)
    assert summary.availability == "external_content_not_loaded" and summary.capabilities is None
    reader.artifact = AsyncMock(return_value={"availability": "available", "content_json": {
        "type": "execution_plan", "run_id": str(UUID(int=4))}})
    with pytest.raises(StoreError, match="execution_plan_link_invalid"):
        await reader.execution_summary(cid, rid, steps)
    reader.artifact = AsyncMock(side_effect=StoreError("artifact_integrity_invalid"))
    with pytest.raises(StoreError, match="artifact_integrity_invalid"):
        await reader.execution_summary(cid, rid, steps)
