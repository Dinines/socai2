"""Unknown timing, retries and clock reversals retain their distinct meanings."""
import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.socai2.analysis_task_store import AnalysisTaskStore
from app.socai2.analysis_task_times import attempt_timing, task_timing


def test_attempt_observation_local_end_and_interruption_are_distinct():
    queued = datetime(2026, 11, 20, tzinfo=UTC)
    attempt = {"enqueued_at": queued, "started_at": queued + timedelta(seconds=2),
        "local_ended_at": None, "local_state": "running"}
    observed = queued + timedelta(seconds=8)
    assert attempt_timing(attempt, observed) == {
        "queue_seconds": 2, "execution_seconds": 6, "anomalies": []}
    attempt.update(local_state="ended", local_ended_at=queued + timedelta(seconds=5), outcome="unknown")
    assert attempt_timing(attempt, observed)["execution_seconds"] == 3  # local end is known, Run outcome is not
    attempt.update(local_state="interrupted", local_ended_at=None)
    assert attempt_timing(attempt, observed)["execution_seconds"] is None
    attempt.update(enqueued_at=None)
    assert attempt_timing(attempt, observed) == {
        "queue_seconds": None, "execution_seconds": None, "anomalies": []}


def test_negative_times_are_not_clamped_to_zero():
    now = datetime(2026, 11, 20, tzinfo=UTC)
    attempt = {"enqueued_at": now + timedelta(seconds=1), "started_at": now,
        "local_ended_at": None, "local_state": "running"}
    assert attempt_timing(attempt, now - timedelta(seconds=1)) == {
        "queue_seconds": None, "execution_seconds": None,
        "anomalies": ["queue_seconds_negative", "execution_seconds_negative"]}
    attempt["enqueued_at"] = now
    assert attempt_timing(attempt, now)["queue_seconds"] == 0  # true zero remains valid


def test_current_retry_wait_and_history_do_not_share_queue_start():
    submitted = datetime(2026, 11, 20, tzinfo=UTC)
    task = {"submitted_at": submitted, "state": "waiting", "ended_at": None,
        "next_attempt_enqueued_at": submitted + timedelta(seconds=7),
        "next_retry_at": submitted + timedelta(seconds=10), "merged_into_task_id": None}
    attempts = [{"local_ended_at": submitted + timedelta(seconds=5)}]
    observed = submitted + timedelta(seconds=9)
    assert task_timing(task, task, attempts, observed) == {
        "total_seconds": 9, "pending_queue_seconds": 2, "retry_wait_seconds": 4, "anomalies": []}
    task["state"] = "running"
    assert task_timing(task, task, attempts, observed)["retry_wait_seconds"] is None
    original = {**task, "merged_into_task_id": "historical-shared-execution"}
    task["state"] = "waiting"
    assert task_timing(original, task, attempts, observed)["pending_queue_seconds"] is None


def test_list_eligibility_does_not_cross_its_observation_deadline():
    created = datetime(2026, 11, 20, tzinfo=UTC)
    store = SimpleNamespace(
        subject=AsyncMock(return_value={"created_at": created, "handling_status": "new"}),
        one=AsyncMock(return_value={"last_normal_completed_at": None, "next_check_at": None,
            "automatic_stop_reason": None}),
        policy=SimpleNamespace(automatic_window_seconds=10),
        where=lambda table, *conditions: conditions,
        now=AsyncMock(return_value=created + timedelta(seconds=10)))
    observed = created + timedelta(seconds=9)
    result = asyncio.run(AnalysisTaskStore.automatic_status(store, "case", None, observed_at=observed))
    assert result["eligible"] and result["ineligible_reason"] is None
    store.now.assert_not_awaited()
    result = asyncio.run(AnalysisTaskStore.automatic_status(store, "case", None))
    assert not result["eligible"] and result["ineligible_reason"] == "expired"
