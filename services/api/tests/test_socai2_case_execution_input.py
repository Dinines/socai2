"""Direct Case query preparation/configuration invariants; no model or database."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits, Scope
from app.socai2.baseline_evidence_tools import VERSION, query_sql
from app.socai2.case_execution_input import CaseExecutionPolicy, binding_scope, prepare
from app.socai2.runtime_policy import active_policy


def context(times):
    ids = [str(uuid4()) for _ in times]
    scope = Scope(kind="whole_case", alert_ids=ids, object_keys=[], window_start=None, window_end=None, limitations=[])
    return Context.model_construct(scope=scope, alerts={aid: SimpleNamespace(alert={"event_time": value,
        "event_time_source": source}) for aid, (value, source) in zip(ids, times)}, questions=[], omissions=[]), ids


def limits(rows):
    return Limits(max_model_calls=6, max_tokens=131072, max_tool_calls=10, max_rows_per_query=rows,
                  deadline_at=datetime.now(UTC) + timedelta(minutes=25), policy_version="test")


def test_month_span_is_preserved_and_host_windows_use_related_alerts():
    first = datetime(2026, 10, 1, 12, tzinfo=UTC)
    last = first + timedelta(days=31)
    original, ids = context([(first.isoformat(), "source"), (last.isoformat(), "derived_source")])
    frozen = prepare(original, CaseExecutionPolicy(3600, 3600, 50), limits(200))
    assert frozen.scope.window_start == first - timedelta(hours=1)
    assert frozen.scope.window_end == last + timedelta(hours=1)
    assert binding_scope(frozen, [ids[1]])["window_start"] == (last - timedelta(hours=1)).isoformat()
    assert original.scope.window_start is None


@pytest.mark.parametrize("time,source", [(None, "unknown"), ("2026-11-15T12:00:00", "source"),
    ("2026-11-15T12:00:00+00:00", "unknown"), ("not-a-time", "source")])
def test_missing_time_records_gap_without_inventing_a_window(time, source):
    original, ids = context([(time, source)])
    frozen = prepare(original, CaseExecutionPolicy(3600, 3600, 50), limits(200))
    assert frozen.scope.window_start is None and frozen.scope.window_end is None
    assert frozen.query_preparation["missing_time_alert_ids"] == ids
    assert frozen.omissions[0].reason == "reliable_alert_time_unavailable"
    assert frozen.scope.alert_ids == original.scope.alert_ids


def test_configured_log_limit_above_50_is_capped_by_run_policy(monkeypatch):
    from pathlib import Path
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(Path(__file__).resolve().parents[3]
        / "deploy/local-investigation/investigation-policy-case-v1.toml"))
    active_policy.cache_clear()
    original, _ = context([("2026-11-15T12:00:00+00:00", "source")])
    frozen = prepare(original, CaseExecutionPolicy(3600, 3600, 80), limits(75))
    assert frozen.query_preparation["effective_max_rows_per_query"] == 75
    args = {"tool_name": "process_activity", "contract_version": VERSION,
        "scope": frozen.scope.model_dump(mode="json"), "limit": 75, "row_limit": 75,
        "parameters": {"tenant_id": str(uuid4()), "hostname": "test.invalid"}}
    _, params = query_sql(args)
    assert params["fetch_limit"] == 76
    with pytest.raises(ValueError, match="invalid_frozen_query_scope"):
        query_sql({**args, "limit": 76})
    active_policy.cache_clear()


@pytest.mark.parametrize("values", [(0, 0, 50), (-1, 3600, 50), (True, 3600, 50), (3600, 3600, 0)])
def test_invalid_preparation_config_fails(values):
    with pytest.raises(ValueError):
        CaseExecutionPolicy(*values)
