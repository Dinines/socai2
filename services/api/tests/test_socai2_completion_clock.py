"""A completed local handle is recorded in the DB's time domain if clocks disagree."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.socai2.analysis_dispatch_store import DispatchRepository
from app.socai2.analysis_dispatch_types import Completion, Outcome
from app.socai2.baseline_store import StoreError


@pytest.mark.parametrize("mode", ["normal", "clock_behind", "naive", "database_still_behind", "unknown_run",
                                  "running_run", "only_run_start_is_later", "database_between_starts_unknown"])
def test_completion_uses_observed_time_only_for_clock_mismatch(mode, caplog):
    start = datetime(2026, 11, 18, 4, 0, tzinfo=UTC)
    tenant, task_id, attempt_id, run_id = (uuid4() for _ in range(4))
    end = start + timedelta(seconds=1) if mode == "normal" else start - timedelta(seconds=1)
    if mode == "only_run_start_is_later":
        end = start + timedelta(milliseconds=500)
    if mode == "naive":
        end = end.replace(tzinfo=None)
    observed = start + timedelta(seconds=2) if mode != "database_still_behind" else start - timedelta(seconds=2)
    if mode == "database_between_starts_unknown":
        observed = start + timedelta(milliseconds=500)
    original = end
    outcome = "unknown" if mode in {"unknown_run", "database_between_starts_unknown"} else "failed"
    receipt = Completion({"id": task_id}, attempt_id, end, Outcome(outcome, "invalid_input", "execute", {"code": "frozen_invalid"}))
    running = mode in {"running_run", "only_run_start_is_later", "database_between_starts_unknown"}
    run = {"id": run_id, "state": "running" if running else "unknown", "ended_at": None,
        "started_at": start + timedelta(seconds=1)}
    attempt = {"id": attempt_id, "task_id": task_id, "attempt_no": 1, "local_state": "running", "started_at": start,
        "run_id": run_id if mode == "unknown_run" or running else None}

    async def validate_finish(identity, **kwargs):
        assert identity == attempt_id and kwargs["outcome"] == outcome and kwargs["error_detail"] == {"code": "frozen_invalid"}
        received = kwargs["ended_at"]
        if received.tzinfo is None or received < start:
            raise StoreError("invalid_attempt_end", 422)

    store = SimpleNamespace(attempt=AsyncMock(return_value=attempt), task=AsyncMock(return_value={"state": "failed"}),
        now=AsyncMock(return_value=observed), finish_attempt=AsyncMock(side_effect=validate_finish),
        one=AsyncMock(return_value=run), where=lambda table, *clauses: clauses,
        db=SimpleNamespace(execute=AsyncMock()))

    @asynccontextmanager
    async def transaction(*args):
        yield store

    call = DispatchRepository(SimpleNamespace(transaction=transaction), tenant).finish(receipt)
    if mode in {"naive", "database_still_behind", "database_between_starts_unknown"}:
        with pytest.raises(StoreError, match="invalid_attempt_end"):
            asyncio.run(call)
    else:
        asyncio.run(call)
    assert receipt.ended_at == original and run["ended_at"] is None
    fallback = mode not in {"normal", "naive"}
    assert store.now.await_count == int(fallback)
    records = [r for r in caplog.records if r.getMessage().startswith("analysis_completion_clock_before_start")]
    assert bool(records) is fallback
    if fallback:
        assert records[0].receipt_ended_at == original.isoformat()
        assert records[0].database_observed_ended_at == observed.isoformat()
    if mode in {"database_still_behind", "database_between_starts_unknown"}:
        store.finish_attempt.assert_not_awaited()
        store.db.execute.assert_not_awaited()
        return
    assert store.finish_attempt.call_args.kwargs["ended_at"] == (observed if fallback else original)
    if running:
        fields = store.db.execute.call_args.args[0].compile().params
        assert fields["ended_at"] == observed and fields["state"] == "failed"
    else:
        store.db.execute.assert_not_awaited()
