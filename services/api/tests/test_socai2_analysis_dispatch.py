"""Direct dispatcher policy/error boundary checks; no service or model calls."""
import asyncio
import json
import socket
import ssl
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from app.socai2.analysis_dispatch_config import DispatchPolicy
from app.socai2.analysis_dispatch_runtime import exclusive_process, load_profile, run
from app.socai2.analysis_dispatch_types import (
    ExecutionFailure,
    Outcome,
    classify_failure,
)

ROOT = Path(__file__).resolve().parents[3]


def test_error_facts_and_retry_after():
    for error in (httpx.ConnectTimeout("x"), httpx.PoolTimeout("x"), ConnectionRefusedError(), socket.gaierror(socket.EAI_AGAIN, "x")):
        result = classify_failure(error, stage="execute")
        assert result.outcome == "failed" and result.retryable
    for error in (httpx.ReadTimeout("x"), httpx.ReadError("x"), httpx.WriteTimeout("x"), asyncio.CancelledError()):
        result = classify_failure(error, stage="execute")
        assert result.outcome == "unknown" and not result.retryable
    for error in (ValueError("x"), ssl.SSLError("x"), httpx.InvalidURL("x")):
        assert not classify_failure(error, stage="execute").retryable
    for code in (400, 401, 403, 404, 422):
        assert not classify_failure(ExecutionFailure("rejected", stage="execute", not_executed=True,
            temporary=True, status_code=code), stage="execute").retryable
    at = datetime.now(UTC) + timedelta(seconds=120)
    result = classify_failure(ExecutionFailure("rate_limited", stage="execute", not_executed=True,
        temporary=True, status_code=429, retry_after=at), stage="execute")
    assert result.retryable and result.retry_after == at
    unknown = classify_failure(ExecutionFailure("upstream", stage="execute", temporary=True, status_code=503), stage="execute")
    assert unknown.outcome == "unknown" and not unknown.retryable
    known = classify_failure(ExecutionFailure("unavailable", stage="input", not_executed=True,
        temporary=True, status_code=503), stage="input")
    assert known.outcome == "failed" and known.retryable
    with pytest.raises(ValueError):
        Outcome("failed")
    with pytest.raises(ValueError):
        Outcome("failed", "execution_failed", error_detail={"raw_body": "not permitted"})


def test_profile_disabled_capacity_and_single_instance(tmp_path):
    path = ROOT / "deploy/local-investigation/analysis-dispatch.example.json"
    profile = load_profile(str(path))
    assert profile["enabled"] is False
    asyncio.run(run(profile))  # must not read secrets, contact Redis/PG, or create a dispatcher
    policy = DispatchPolicy(**profile["dispatch"])
    for size in (1, 3, 5):
        assert replace(policy, max_running_tasks=size).max_running_tasks == size
    for size in (0, -1, True):
        with pytest.raises(ValueError):
            replace(policy, max_running_tasks=size)
    with pytest.raises(ValueError):
        replace(policy, poll_interval_seconds=0)
    with pytest.raises(ValueError):
        replace(policy, priorities=("case_investigation",))
    invalid = tmp_path / "profile.json"
    invalid.write_text(json.dumps({**profile, "enabled": True}))
    with pytest.raises(ValueError, match="executor factory"):
        load_profile(str(invalid))
    with exclusive_process(tmp_path / "process.lock"), pytest.raises(RuntimeError, match="already active"), exclusive_process(tmp_path / "process.lock"):
        pass
    with exclusive_process(tmp_path / "process.lock"):
        pass


def test_release_sources_present_without_automatic_activation():
    config = json.loads((ROOT / "deploy/local-investigation/analysis-dispatch-release-fragment.json").read_text())
    assert config["instances"] == 1
    assert all((ROOT / path).is_file() for path in config["patches"])
    assert config["requires"] == "analysis-lifecycle-release-fragment.json"
