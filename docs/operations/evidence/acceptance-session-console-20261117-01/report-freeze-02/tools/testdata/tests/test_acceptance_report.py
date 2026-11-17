"""3c.3 report: archived two-part records, no business execution."""
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance import main
from acceptance_materials import MaterialError, read_json
from acceptance_report import execution_report, report_exit_code, write_session_report
from acceptance_report_models import model_report
from alert_scenarios import json_bytes, sha256

EVIDENCE = ROOT / "docs/operations/evidence"
COMPLETE = EVIDENCE / "acceptance-append-20261117-02/prepared"
INCOMPLETE = EVIDENCE / "acceptance-append-20261117-01/prepared"


def digest(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def completed(tmp_path):
    target = tmp_path / "prepared"
    shutil.copytree(COMPLETE, target)
    return target


def offline(monkeypatch, root):
    connections = set(read_json(root / "session.json")["profile"]["connection_files"].values())
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert str(path) not in connections, "report cannot read connection files"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded)


def test_completed_real_receipts_deduplicated_exported_and_unchanged(tmp_path, monkeypatch, capsys):
    original = digest(COMPLETE)
    offline(monkeypatch, COMPLETE)
    out = tmp_path / "report"
    with patch("socket.socket", side_effect=AssertionError("must remain offline")):
        assert main(["report", "--prepared", str(COMPLETE), "--output", str(out)]) == 0
    console = json.loads(capsys.readouterr().out)
    report = read_json(out / "report.json")
    assert console["state"] == report["state"] == "all_parts_completed"
    assert report["counts"] == {"alerts": 2, "incidents": 1, "cases": 2, "analysis_tasks": 9, "analysis_attempts": 8,
                                "runs": 8, "results": 4, "run_steps": 83, "artifacts": 245, "run_members": 5}
    assert [p["newly_observed"]["runs"] for p in report["parts"]] == [4, 4]
    assert [p["observed_counts"]["runs"] for p in report["parts"]] == [4, 8]
    model = report["models"]
    assert model["saved_request_count"] == model["request_count"] == 13
    assert model["usage"] == {"prompt_tokens": 69894, "completion_tokens": 40101, "total_tokens": 109995}
    assert model["finish_reasons"] == {"stop": 13} and not model["issues"]
    assert report["quality"]["issues_by_stage"] == {"C6": 9, "C3": 6, "I": 2}
    assert len(report["step_issues"]) == 16 and report["quality"]["body_correctness"] == "not_fully_evaluated"
    case_rounds = [s["rounds"] for s in report["subjects"] if s["kind"] == "case"]
    assert sorted([[len(r["frozen_alert_ids"]) for r in rounds] for rounds in case_rounds]) == [[1, 1], [1, 2]]
    assert all(rounds[1]["previous_run_ids"] == [rounds[0]["run_id"]] for rounds in case_rounds)
    assert all(len(rounds) == 2 for rounds in case_rounds)
    for item in model["requests"]:
        source = item["source"]
        index = int(source["pointer"].split("/")[-1])
        request = read_json(COMPLETE / source["path"])["artifacts"][index]["content_json"]
        body = request.get("payload", request)["body"]
        assert json.loads((out / item["exports"]["messages"]).read_text()) == [{k: m[k] for k in ("role", "content")} for m in body["messages"]]
        assert read_json(out / item["exports"]["schema"]) == body["response_format"]
        source = item["response_source"]
        response = read_json(COMPLETE / source["path"])["artifacts"][int(source["pointer"].split("/")[-1])]["content_json"]["raw"]
        assert (out / item["exports"]["output"]).read_bytes() == response["choices"][0]["message"]["content"].encode()
    manifest = read_json(out / "manifest.json")
    assert manifest["readback"] == "passed"
    assert all(sha256((out / f["path"]).read_bytes()) == f["sha256"] for f in manifest["files"])
    assert all(sha256((COMPLETE / s["path"]).read_bytes()) == s["sha256"] for s in manifest["sources"])
    assert "109995" in (out / "report.md").read_text() and "待复核" in (out / "report.md").read_text()
    assert not any(report["this_command"].values()) and not report["live_state_verified"]
    assert digest(COMPLETE) == original


def test_failed_part_missing_snapshot_has_unknown_totals(tmp_path, monkeypatch):
    before = digest(INCOMPLETE)
    offline(monkeypatch, INCOMPLETE)
    with patch("socket.socket", side_effect=AssertionError("offline")):
        report = write_session_report(INCOMPLETE, tmp_path / "failed-report")
    assert report_exit_code(report) == 3 and report["statistics_state"] == "incomplete"
    assert all(x is None for x in report["counts"].values())
    assert report["parts"][0]["recorded_sent"] == {"context": 2, "alerts": 1}
    assert report["parts"][0]["error_code"] == "http_status_503"
    assert report["models"]["request_count"] is None and report["models"]["usage"]["total_tokens"] is None
    assert report["models"]["saved_request_count"] == 0
    assert report["parts"][1]["snapshot_state"] == "not_started"
    assert all("stopped-batch-records" not in s["path"] for s in report["sources"])
    assert digest(INCOMPLETE) == before


def test_unstarted_and_output_guards(completed, tmp_path):
    shutil.rmtree(completed / "runs")
    report = write_session_report(completed, tmp_path / "not-started")
    assert report["state"] == "ready" and report["counts"]["runs"] == report["models"]["request_count"] == 0
    assert not report["all_parts_completed"]
    assert all(p["recorded_sent"] == {"context": 0, "alerts": 0} for p in report["parts"])
    source = Path(read_json(completed / "session.json")["source_directory"])
    for out in (completed / "report", completed / "wire/report", source / "report", tmp_path / "not-started"):
        with pytest.raises((MaterialError, FileExistsError)):
            write_session_report(completed, out)
    (tmp_path / "link").symlink_to(completed, target_is_directory=True)
    with pytest.raises(MaterialError):
        write_session_report(completed, tmp_path / "link/report")


def test_unknown_usage_visible_whitespace_and_private_fields():
    requests = {"request": {"id": "request", "kind": "model_request", "content_json": {"body": {
        "messages": [{"role": "user", "content": "  useful\n", "reasoning_content": "HIDDEN_SENTINEL"}],
        "headers": {"Authorization": "AUTH_SENTINEL"}, "response_format": {"type": "json_object"}}}},
        "response": {"id": "response", "kind": "source_snapshot", "content_json": {"request_artifact_id": "request", "raw": {
            "choices": [{"finish_reason": "length", "message": {"content": " \n  ", "reasoning_content": "HIDDEN_SENTINEL"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": True, "total_tokens": None}}}}}
    origins = {k: {"path": "snapshot", "pointer": "/" + k, "sha256": "source-sha"} for k in requests}
    report, files = model_report(requests, origins, True)
    assert files["models/request/output.txt"] == b" \n  "
    assert report["usage"] == {"prompt_tokens": 12, "completion_tokens": None, "total_tokens": None}
    assert report["unknown_usage_requests"]["total_tokens"] == 1
    assert not any(b"SENTINEL" in content for content in files.values())
    requests["response"]["content_json"]["raw"]["choices"] = [None]
    report, files = model_report(requests, origins, True)
    assert report["issues"][0]["code"] == "model_choices_unreadable"
    assert "models/request/messages.json" in files and "models/request/output.txt" not in files


def test_conflicting_immutable_and_bad_row_keep_other_originals(completed):
    path = completed / "runs/part2/saved-records.json"
    data = read_json(path)
    first = read_json(completed / "runs/part1/saved-records.json")
    identity = first["artifacts"][0]["id"]
    next(a for a in data["artifacts"] if a["id"] == identity)["content_json"] = {"changed": True}
    data["artifacts"].append(None)
    path.write_bytes(json_bytes(data))
    report, _ = execution_report(completed)
    assert report["statistics_state"] == "incomplete" and report["counts"]["runs"] is None
    assert {i["code"] for i in report["report_issues"]} >= {"frozen_row_conflict", "invalid_saved_row"}
    assert report["observed_counts"]["runs"] == 8 and report["models"]["saved_request_count"] == 13
    assert report["models"]["usage"]["total_tokens"] is None


def test_unbound_state_cannot_supply_confirmed_totals(completed):
    path = completed / "runs/part1/state.json"
    state = read_json(path)
    state["session_sha256"] = "wrong"
    path.write_bytes(json_bytes(state))
    report, _ = execution_report(completed)
    assert report["counts"]["runs"] is None and report["parts"][0]["snapshot_state"] == "incomplete"
    assert report_exit_code(report) == 3


def test_malformed_link_keeps_independent_subjects_and_unknown_statistics(completed, tmp_path):
    path = completed / "runs/part2/saved-records.json"
    data = read_json(path)
    data["analysis_attempts"][0]["previous_run_id"] = {"private": "PRIVATE_SENTINEL"}
    path.write_bytes(json_bytes(data))
    report = write_session_report(completed, tmp_path / "malformed-report")
    assert report["statistics_state"] == "incomplete" and report["observed_counts"]["runs"] == 8
    assert any(i["code"] == "invalid_saved_row" for i in report["report_issues"])
    assert "PRIVATE_SENTINEL" not in (tmp_path / "malformed-report/report.json").read_text()
