"""Observer contracts use in-memory rows and a read-only connection double."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest


spec = importlib.util.spec_from_file_location("testdata_observer", Path(__file__).parents[1] / "observe_results.py")
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)

TENANT, OTHER, INPUT, CANONICAL, RUN = [str(UUID(int=value)) for value in range(1, 6)]


def materials():
    manifest = {"schema_version": "socai2-existing-alert-fixtures/v1", "run_id": "batch-is-not-run",
                "tenant_id": TENANT, "count": 1,
                "records": [{"alert_id": INPUT, "expected": "DO-NOT-READ.json"}]}
    receipt = {"run_id": manifest["run_id"], "tenant_id": TENANT,
               "records": [{"alert_id": INPUT, "predicted_canonical_alert_id": CANONICAL,
                            "state": "outcome_unknown", "message": {"topic": "test.raw", "partition": 1, "offset": 4}}]}
    snapshot = {"tenant_id": TENANT, "captured_at": "2026-10-23T01:00:00Z",
                "alerts": [{"id": CANONICAL, "tenant_id": TENANT, "status": "triaged",
                            "enrichment_data": {"socai2_fusion": {"identity": {"source_alert_id": INPUT}}}}],
                "runs": [{"id": RUN, "tenant_id": TENANT, "case_id": CANONICAL,
                          "raw_alert": {"id": CANONICAL}, "status": "completed", "total_tokens": 123}],
                "events": [], "artifacts": [], "costs": []}
    return manifest, receipt, snapshot


def artifact(kind, content, number):
    encoded = content.encode("utf-8")
    return {"id": str(UUID(int=number)), "tenant_id": TENANT, "run_id": RUN, "kind": kind,
            "content": content, "sha256": hashlib.sha256(encoded).hexdigest(), "size_bytes": len(encoded),
            "created_at": f"2026-10-23T01:00:{number:02d}Z"}


def graph(snapshot, completion="completed"):
    snapshot["events"] = [
        {"id": "started", "tenant_id": TENANT, "run_id": RUN, "seq": -1, "kind": "triage_started", "payload": {}},
        {"id": "tool", "tenant_id": TENANT, "run_id": RUN, "seq": 10000, "kind": "tool_call", "payload": {}},
        {"id": "graph", "tenant_id": TENANT, "run_id": RUN, "seq": 5, "kind": "graph_result", "payload": {"completion": completion}},
    ]
    snapshot["artifacts"] = [artifact("report_md", "# 中文调查报告\n待人工复核", 10),
                             artifact("graph_result", json.dumps({"status": "completed", "investigation_depth": {}}), 11)]


def result(snapshot, manifest=None, receipt=None):
    default_manifest, default_receipt, _ = materials()
    return observer.observe(manifest or default_manifest, receipt or default_receipt, snapshot)


def test_exact_identity_filters_other_tenants_and_old_runs_and_preserves_seq():
    manifest, receipt, snapshot = materials()
    graph(snapshot, "partial")
    snapshot["runs"] += [{"id": "old", "tenant_id": TENANT, "case_id": str(UUID(int=100)), "raw_alert": {}},
                         {"id": "other-tenant", "tenant_id": OTHER, "case_id": CANONICAL, "raw_alert": {"id": CANONICAL}}]
    snapshot["events"].append({"tenant_id": OTHER, "run_id": RUN, "seq": 9, "kind": "secret"})
    snapshot["costs"] = [{"tenant_id": TENANT, "run_id": RUN, "model": "test", "call_count": 2,
                          "total_prompt_tokens": 100, "total_completion_tokens": 23, "unpriced_call_count": 2,
                          "measured_call_count": 0, "measured_cost_usd": 0}]
    observed = observer.observe(manifest, receipt, snapshot)
    row = observed["records"][0]
    run = row["runs"][0]
    assert observed["batch_id"] == "batch-is-not-run"
    assert row["input_alert_id"] == INPUT and row["canonical_alert_id"] == CANONICAL and run["run_id"] == RUN
    assert row["sender_state"] == "outcome_unknown"  # A later PG match does not rewrite the send receipt.
    assert row["source_identity_matches"] is True
    assert run["execution_status"] == "completed" and run["investigation_status"] == "partial"
    assert run["markdown"]["state"] == "readable_verified"
    assert run["usage"]["recorded_tokens"] == 123 and run["usage"]["run_total_tokens"] == 123
    assert run["usage"]["measured_cost_usd"] is None
    assert len(observed["snapshot"]["runs"]) == 1
    assert {e["seq"] for e in observed["snapshot"]["events"]} == {-1, 5, 10000}
    assert "DO-NOT-READ" not in json.dumps(observed)


@pytest.mark.parametrize("state", ["missing", "running", "partial", "completed"])
def test_completion_and_report_states_are_independent(state):
    _, _, snapshot = materials()
    if state == "running":
        snapshot["runs"][0]["status"] = "running"
    elif state in {"partial", "completed"}:
        graph(snapshot, state)
    run = result(snapshot)["records"][0]["runs"][0]
    assert run["investigation_status"] == state
    assert run["usage"]["recorded_tokens"] is None
    assert run["usage"]["recorded_call_count"] is None


def test_auto_closed_does_not_require_report_and_missing_run_is_not_failure():
    _, _, snapshot = materials()
    snapshot["events"] = [{"tenant_id": TENANT, "run_id": RUN, "kind": "triage_verdict", "seq": 1,
                           "payload": {"verdict": "benign_true_positive", "auto_closed": True}}]
    run = result(snapshot)["records"][0]["runs"][0]
    assert run["investigation_status"] == "not_required_auto_closed"
    assert run["markdown"]["state"] == "missing"
    snapshot["runs"] = []
    assert result(snapshot)["records"][0]["run_status"] == "missing"
    snapshot["alerts"] = []
    assert result(snapshot)["records"][0]["alert_status"] == "missing"


def test_newest_bad_markdown_and_graph_truncation_cannot_pass_as_completed():
    _, _, snapshot = materials()
    graph(snapshot)
    bad = artifact("report_md", "Changed report", 12)
    bad["sha256"] = "wrong"
    snapshot["artifacts"].append(bad)
    run = result(snapshot)["records"][0]["runs"][0]
    assert run["investigation_status"] == "partial"
    assert run["markdown"]["state"] == "unreadable_or_unverified"
    snapshot["artifacts"] = [artifact("report_md", "Report", 10), artifact("graph_result", json.dumps({
        "investigation_depth": {"truncated": True, "stop_reason": "iteration_limit"}}), 11)]
    run = result(snapshot)["records"][0]["runs"][0]
    assert run["investigation_status"] == "partial" and run["stop_reason"] == "iteration_limit"


def test_receipt_and_snapshot_mismatches_refuse_or_quarantine():
    manifest, receipt, snapshot = materials()
    receipt["tenant_id"] = OTHER
    with pytest.raises(ValueError):
        observer.observe(manifest, receipt, snapshot)
    receipt["tenant_id"] = TENANT
    snapshot["alerts"][0]["enrichment_data"]["socai2_fusion"]["identity"]["source_alert_id"] = OTHER
    row = observer.observe(manifest, receipt, snapshot)["records"][0]
    assert row["alert_status"] == "identity_mismatch" and row["runs"] == []
    snapshot["tenant_id"] = OTHER
    with pytest.raises(ValueError):
        observer.observe(manifest, receipt, snapshot)


def test_http_receipt_compatibility_and_unattempted_inputs():
    manifest, receipt, _ = materials()
    receipt["records"] = [{"alert_id": INPUT, "state": "accepted_not_processed",
                           "response": {"canonical_alert_id": CANONICAL, "tenant_id": TENANT, "input_id": INPUT}}]
    assert observer.load_targets(manifest, receipt)[2][0]["mapping_source"] == "HTTP response"
    receipt["records"] = []
    assert observer.load_targets(manifest, receipt)[2][0]["canonical_alert_id"] is None


@pytest.mark.asyncio
async def test_pg_capture_uses_one_read_only_transaction_and_scoped_selects():
    _, _, snapshot = materials()
    graph(snapshot)

    class Transaction:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_args):
            pass

    class Connection:
        def __init__(self):
            self.queries = []
            self.close = AsyncMock()
        def transaction(self, **kwargs):
            assert kwargs == {"isolation": "repeatable_read", "readonly": True}
            return Transaction()
        async def execute(self, query, tenant):
            assert query.startswith("SELECT set_config") and tenant == TENANT
        async def fetch(self, query, tenant, ids):
            assert query.startswith("SELECT ") and "tenant_id=$1" in query
            assert str(tenant) == TENANT
            self.queries.append(query)
            for table, key in (("investigation_runs", "runs"), ("investigation_events", "events"),
                               ("investigation_artifacts", "artifacts"), ("aisoc_run_costs", "costs"), ("alerts", "alerts")):
                if f"FROM {table} " in query:
                    return snapshot[key]
            raise AssertionError(query)

    conn = Connection()
    connect = AsyncMock(return_value=conn)
    captured = await observer.fetch_snapshot("postgresql://unused", TENANT, [CANONICAL], connect=connect)
    assert len(conn.queries) == 5 and captured["tenant_id"] == TENANT
    assert not any("seq >" in query for query in conn.queries)
    conn.close.assert_awaited_once()


def test_offline_cli_saves_private_capture_rereads_it_and_refuses_overwrite(tmp_path, monkeypatch):
    manifest, receipt, snapshot = materials()
    graph(snapshot, "partial")
    for name, value in (("manifest", manifest), ("receipt", receipt), ("snapshot", snapshot)):
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    (tmp_path / "DO-NOT-READ.json").write_text("not JSON; the observer must not read expected answers")
    args = ["--manifest", str(tmp_path / "manifest.json"), "--receipt", str(tmp_path / "receipt.json"),
            "--snapshot", str(tmp_path / "snapshot.json"), "--out", str(tmp_path / "observed.json")]
    assert observer.main(args) == 0
    observed_path = tmp_path / "observed.json"
    assert observed_path.stat().st_mode & 0o777 == 0o600
    saved = observed_path.read_bytes()
    assert observer.main(args) == 1 and observed_path.read_bytes() == saved
    reread = observer.observe(manifest, receipt, json.loads(saved))
    assert reread["records"][0]["runs"][0]["investigation_status"] == "partial"


def test_bad_pg_dsn_error_does_not_leak_secret(tmp_path, monkeypatch, capsys):
    manifest, receipt, _ = materials()
    for name, value in (("manifest", manifest), ("receipt", receipt)):
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    async def failed(*_args, **_kwargs):
        raise ValueError("private-password-do-not-print")
    monkeypatch.setattr(observer, "fetch_snapshot", failed)
    monkeypatch.setenv("TESTDATA_READ_DSN", "postgresql://private-password-do-not-print")
    assert observer.main(["--manifest", str(tmp_path / "manifest.json"), "--receipt", str(tmp_path / "receipt.json"),
                          "--dsn-env", "TESTDATA_READ_DSN", "--out", str(tmp_path / "observed.json")]) == 1
    assert "private-password" not in capsys.readouterr().err
    assert not (tmp_path / "observed.json").exists()
