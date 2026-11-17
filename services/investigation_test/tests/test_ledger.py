"""Direct W1 input -> immutable storage -> read API checks; synthetic records."""
import hashlib
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from investigation_test.api import PREFIX, create_app
from investigation_test.config import Config
from investigation_test.store import LedgerError, Store


def tree(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in path.rglob("*") if p.is_file()}


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    (source / "reply.json").write_text('{"fixture":true,"outcome":"unknown"}\n')
    mapping = {"subject_type": "case", "subject_id": str(uuid4()), "task_id": str(uuid4()), "run_id": None}
    data = {"schema_version": 1,
        "batch": {"id": "batch-1", "environment": "test", "title": "Synthetic states",
            "scenario_version": "w1.fixture.1", "execution_state": "running", "mode": "archive",
            "provenance": "synthetic_fixture", "started_at": None, "updated_at": "2026-11-15T08:00:00Z",
            "quality_status": "not_assessed"},
        "cases": [{"id": "case-1", "use_case_id": "TC-V01", "scenario_id": "synthetic",
            "status": "not_run", "expected": ["Waiting has no Run"], "actual": [],
            "operation_ids": ["operation-1"], "evidence_ids": ["reply"]},
            {"id": "case-2", "use_case_id": "TC-P01", "scenario_id": "synthetic",
            "status": "not_covered", "expected": ["Future dependency remains visible"], "actual": [],
            "operation_ids": [], "evidence_ids": []}],
        "operations": [{"id": "operation-1", "case_id": "case-1", "intent": "initial",
            "execution_state": "accepted", "occurred_at": "2026-11-15T08:00:00Z",
            "mappings": [mapping], "evidence_ids": ["reply"]}],
        "preparation": {"status": "inspected", "cleanup_mode": "no_cleanup", "summary": "Synthetic only",
            "resources": [], "observed_at": "2026-11-15T08:00:00Z", "evidence_ids": []},
        "quality_issues": [], "evidence": [{"id": "reply", "path": "reply.json", "label": "Synthetic reply",
            "mime_type": "application/json", "visibility": "public", "source_ref": "synthetic fixture"}]}
    config = Config(ledger_root=str(tmp_path / "ledger"), environment_label="component-test",
        host="127.0.0.1", port=14178, default_limit=1, max_limit=10,
        max_document_bytes=100000, max_evidence_bytes=100000, max_cursor_bytes=2048)
    document = source / "document.json"
    def write():
        document.write_text(json.dumps(data))
        return document
    return config, data, write, document


def test_publish_revision_terminal_and_original_evidence(fixture):
    config, data, write, _ = fixture
    store = Store(config)
    assert store.publish(write(), 0).revision == 1
    first, first_dir, _ = store.load("batch-1")
    old_bytes = tree(first_dir)
    with pytest.raises(LedgerError, match="revision_conflict"):
        store.publish(write(), 0)
    data["batch"].update(started_at="2026-11-15T08:00:00Z", execution_state="finished")
    assert store.publish(write(), 1).revision == 2
    assert tree(first_dir) == old_bytes
    assert first.document.batch.execution_state == "running"
    with pytest.raises(LedgerError, match="batch_terminal"):
        store.publish(write(), 2)


def test_eight_gets_pagination_and_no_writes(fixture):
    config, _data, write, document = fixture
    store = Store(config)
    store.publish(write(), 0)
    before, source = tree(store.root), tree(document.parent)
    with TestClient(create_app(config)) as client:
        assert client.get(PREFIX + "/capabilities").json()["read_only"] is True
        assert client.get(PREFIX + "/batches?environment=missing").json()["items"] == []
        batch = client.get(PREFIX + "/batches/batch-1").json()
        assert batch["batch"]["quality_status"] == "not_assessed"
        first = client.get(batch["links"]["cases"] + "?limit=1").json()
        second = client.get(batch["links"]["cases"], params={"limit": 1, "cursor": first["next_cursor"]}).json()
        assert [first["items"][0]["id"], second["items"][0]["id"]] == ["case-1", "case-2"]
        assert second["next_cursor"] is None
        operations = client.get(batch["links"]["operations"] + "?use_case_id=TC-V01").json()
        assert operations["items"][0]["mappings"][0]["run_id"] is None
        assert client.get(batch["links"]["preparation"]).json()["preparation"]["cleanup_mode"] == "no_cleanup"
        assert client.get(batch["links"]["quality-issues"]).json()["items"] == []
        evidence = client.get(batch["evidence"][0]["metadata_url"]).json()
        content = client.get(evidence["content_url"])
        assert content.content == (document.parent / "reply.json").read_bytes()
        assert content.headers["x-content-sha256"] == evidence["sha256"]
        assert "path" not in evidence
        assert client.post(PREFIX + "/batches").status_code == 405
        assert client.get(PREFIX + "/batches/batch-1/evidence/missing").status_code == 404
        assert client.get(PREFIX + "/batches?limit=11").status_code == 422
        assert client.get(PREFIX + "/batches?unknown=value").status_code == 422
        assert client.get(PREFIX + "/batches?limit=1&limit=2").status_code == 422
    with TestClient(create_app(config)) as restarted:
        assert restarted.get(PREFIX + "/batches/batch-1").json()["revision"] == 1
    assert tree(store.root) == before and tree(document.parent) == source


def test_cursor_rejects_changed_filter_and_revision_even_when_list_shrinks(fixture):
    config, data, write, _ = fixture
    store = Store(config)
    store.publish(write(), 0)
    with TestClient(create_app(config)) as client:
        url = PREFIX + "/batches/batch-1/cases"
        cursor = client.get(url).json()["next_cursor"]
        assert client.get(url, params={"cursor": cursor, "status": "not_run"}).status_code == 422
        data["cases"].pop()
        store.publish(write(), 1)
        response = client.get(url, params={"cursor": cursor})
        assert response.status_code == 409 and response.json()["detail"]["code"] == "cursor_stale"


@pytest.mark.parametrize("change", ["dangling", "unproved_pass", "quality_mismatch", "unexpected_field", "result_without_run"])
def test_invalid_documents_are_not_published(fixture, change):
    config, data, write, _ = fixture
    if change == "dangling":
        data["operations"][0]["evidence_ids"] = ["not-registered"]
    elif change == "unproved_pass":
        data["cases"][0]["status"] = "passed"
    elif change == "quality_mismatch":
        data["batch"]["quality_status"] = "issues_recorded"
    elif change == "unexpected_field":
        data["start_model"] = True
    else:
        data["operations"][0]["mappings"][0].update(result_type="case_result", result_id=str(uuid4()))
    with pytest.raises(LedgerError, match="invalid_document"):
        Store(config).publish(write(), 0)
    assert not Path(config.ledger_root).exists()


def test_quality_issue_and_multiple_runs_are_preserved(fixture):
    config, data, write, _ = fixture
    first, second = uuid4(), uuid4()
    mapping = data["operations"][0]["mappings"][0]
    mapping["run_id"] = str(first)
    data["operations"][0]["mappings"].append({**mapping, "run_id": str(second)})
    data["operations"][0]["execution_state"] = "unknown"
    data["cases"][0]["status"] = "failed"
    data["batch"]["quality_status"] = "issues_recorded"
    data["quality_issues"] = [{"id": "quality-1", "case_id": "case-1", "run_id": str(first),
        "stage": "C6", "category": "synthetic_display", "description": "Synthetic fixture, not a real defect",
        "status": "deferred", "affects_flow": False, "evidence_ids": ["reply"]}]
    Store(config).publish(write(), 0)
    with TestClient(create_app(config)) as client:
        operations = client.get(PREFIX + "/batches/batch-1/operations").json()["items"]
        assert len(operations[0]["mappings"]) == 2
        issues = client.get(PREFIX + "/batches/batch-1/quality-issues", params={"run_id": str(first)}).json()
        assert issues["total"] == 1 and issues["items"][0]["status"] == "deferred"


@pytest.mark.parametrize("path", ["../reply.json", "/etc/hosts", ".private", "link.json"])
def test_evidence_sources_are_explicit_relative_files(fixture, path):
    config, data, write, document = fixture
    (document.parent / "link.json").symlink_to(document.parent / "reply.json")
    data["evidence"][0]["path"] = path
    with pytest.raises(LedgerError):
        Store(config).publish(write(), 0)
    assert not Path(config.ledger_root).exists()


@pytest.mark.parametrize("damage", ["changed", "missing"])
def test_corrupt_evidence_is_unavailable_not_returned(fixture, damage):
    config, _data, write, _ = fixture
    store = Store(config)
    store.publish(write(), 0)
    _, directory, _ = store.load("batch-1")
    evidence = directory / "evidence/reply"
    evidence.write_bytes(b"changed") if damage == "changed" else evidence.unlink()
    with TestClient(create_app(config)) as client:
        for suffix in ("", "?format=content"):
            response = client.get(PREFIX + "/batches/batch-1/evidence/reply" + suffix)
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "evidence_unavailable"
            assert str(directory) not in response.text


def test_empty_read_service_creates_nothing_and_corrupt_ledger_fails(fixture):
    config, _data, write, _ = fixture
    with TestClient(create_app(config)) as client:
        assert client.get(PREFIX + "/batches").json()["total"] == 0
        assert client.get(PREFIX + "/batches/missing").status_code == 404
        assert not Path(config.ledger_root).exists()
    store = Store(config)
    store.publish(write(), 0)
    _, directory, _ = store.load("batch-1")
    (directory / "ledger.json").write_text("{}")
    with TestClient(create_app(config)) as client:
        assert client.get(PREFIX + "/batches").status_code == 503
        assert client.get(PREFIX + "/batches/batch-1").status_code == 503
