"""Only the new profile contract; PG covers lifecycle behavior."""
import json
from pathlib import Path

import pytest
from app.socai2.analysis_task_policy import AnalysisTaskPolicy
from app.socai2.baseline_store import StoreError

ROOT = Path(__file__).resolve().parents[3]


def test_explicit_profile_defaults_and_override(tmp_path, monkeypatch):
    profile = json.loads((ROOT / "deploy/local-investigation/analysis-tasks.json").read_text())
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(profile))
    monkeypatch.setenv("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", str(path))
    loaded = AnalysisTaskPolicy.load()
    assert (loaded.retry_limit, loaded.retry_delay_seconds, loaded.automatic_window_seconds) == (1, 60, 604800)
    assert (loaded.incident_check_interval_seconds, loaded.case_check_interval_seconds) == (14400, 21600)
    profile.update(retry_limit=0, default_limit=7, max_limit=11)
    path.write_text(json.dumps(profile))
    assert AnalysisTaskPolicy.load().retry_limit == 0
    assert AnalysisTaskPolicy.load().page_size(None) == 7
    with pytest.raises(StoreError):
        AnalysisTaskPolicy.load().page_size(12)


@pytest.mark.parametrize("mutation", [{"retry_limit": True}, {"default_limit": 0},
    {"default_limit": 101}, {"extra": 1}, {"automatic_window_seconds": -1}])
def test_invalid_policy_never_falls_back(tmp_path, monkeypatch, mutation):
    profile = json.loads((ROOT / "deploy/local-investigation/analysis-tasks.json").read_text())
    profile.update(mutation)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(profile))
    monkeypatch.setenv("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", str(path))
    with pytest.raises(StoreError) as error:
        AnalysisTaskPolicy.load()
    assert (error.value.code, error.value.status) == ("service_unavailable", 503)


def test_missing_profile_does_not_select_another_environment(monkeypatch):
    monkeypatch.delenv("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", raising=False)
    with pytest.raises(StoreError):
        AnalysisTaskPolicy.load()
    monkeypatch.setenv("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", "relative.json")
    with pytest.raises(StoreError):
        AnalysisTaskPolicy.load()
