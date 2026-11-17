"""3c.1 saved status: actual archived receipts and small, explicitly changed copies."""
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance import main
from acceptance_contract import Profile
from acceptance_materials import MaterialError, control, inspect_package, read_json
from acceptance_runtime_contract import Execution
from acceptance_session import prepare_execution
from acceptance_status import (
    ReceiptError,
    execution_links,
    session_status,
    write_status,
)
from alert_scenarios import json_bytes, sha256
from test_acceptance_execution import prepared as prepared_fixture
from test_acceptance_materials import snapshot

EVIDENCE = ROOT / "docs/operations/evidence"
prepared = prepared_fixture


def archive(tmp_path, batch):
    source = EVIDENCE / ("acceptance-singlepart-20261117-" + batch)
    target = tmp_path / ("saved-" + batch)
    shutil.copytree(source / "prepared", target)
    shutil.copytree(source / "runs", target / "runs")
    return target


def edit(root, relative, change):
    path = root / relative
    value = read_json(path)
    change(value)
    path.write_bytes(json_bytes(value))


def codes(value):
    return {i["code"] for i in value["blocking_issues"]}


def test_prepared_report_has_no_actual_ids_connections_or_mutations(prepared, tmp_path, monkeypatch):
    root, _, session, materials = prepared
    original = snapshot(root), snapshot(materials)
    blocked_paths = set(session["profile"]["connection_files"].values())
    old_open = Path.open

    def open_file(path, *args, **kwargs):
        assert str(path) not in blocked_paths, "status must not read connection files"
        return old_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)
    with patch("socket.socket", side_effect=AssertionError("status must be offline")), \
            patch("acceptance_run.run_part", side_effect=AssertionError("status cannot run")):
        result = write_status(root, tmp_path / "status.json")
    assert result == read_json(tmp_path / "status.json")
    assert result["state"] == "ready" and result["next_part"] == "part1"
    assert not result["live_state_verified"] and not result["environment"]["connections_checked"]
    assert not any(result["this_command"].values()) and result["append_execution_implemented"]
    assert all(p["actual"] == {"source": "not_observed", "alerts": [], "incidents": [], "cases": []}
               and not any(p[k] for k in ("tasks", "attempts", "runs", "results")) for p in result["parts"])
    assert (snapshot(root), snapshot(materials)) == original
    for destination in (tmp_path / "status.json", root / "report.json", root / "wire/report.json", materials / "report.json"):
        with pytest.raises((FileExistsError, MaterialError)):
            write_status(root, destination)


@pytest.mark.parametrize("batch,phase,next_part", [("01", "needs_review", None), ("02", "waiting_append", "part2")])
def test_archived_actual_receipts_preserved(tmp_path, capsys, batch, phase, next_part):
    root = archive(tmp_path, batch)
    before = snapshot(root)
    output = tmp_path / "status.json"
    with patch("socket.socket", side_effect=AssertionError("saved receipts only")):
        code = main(["status", "--prepared", str(root), "--report", str(output)])
    console, value = json.loads(capsys.readouterr().out), read_json(output)
    assert code == (3 if batch == "01" else 0)
    assert console["state"] == value["state"] == phase and value["next_part"] == next_part
    assert before == snapshot(root)
    part = value["parts"][0]
    assert part["recorded_sent"] == ({"alerts": 0, "context": 0} if batch == "01" else {"alerts": 1, "context": 2})
    if batch == "02":
        assert part["recorded_state"] == "completed_with_issues" and part["closure_verified"]
        assert [len(part["actual"][k]) for k in ("alerts", "incidents", "cases")] == [1, 1, 1]
        assert [t["state"] for t in part["tasks"] if t["subject_type"] == "case"] == ["failed"]
        assert not part["results"] and not any(r["case_id"] for r in part["runs"])
        assert part["quality"] == "not_fully_evaluated" and part["recorded_execution_issue_count"] == 2
    else:
        assert part["recorded_state"] == "incomplete" and not part["closure_verified"]


@pytest.mark.parametrize("damage,expected", [
    ("running", "state_not_closed"), ("empty", "receipt_unreadable"),
    ("bad_json", "receipt_unreadable"), ("binding", "state_binding_mismatch"),
    ("missing_snapshot", "receipt_unreadable"), ("changed_snapshot", "saved_closure_mismatch"),
])
def test_unfinished_or_unbound_receipt_never_becomes_fresh_work(tmp_path, damage, expected):
    root = archive(tmp_path, "02")
    part = root / "runs/part1"
    if damage == "empty":
        shutil.rmtree(part)
        part.mkdir()
    elif damage == "bad_json":
        (part / "state.json").write_text("broken secret-value")
    elif damage == "running":
        edit(root, "runs/part1/state.json", lambda s: s.update(status="running", ended_at=None))
    elif damage == "binding":
        edit(root, "runs/part1/state.json", lambda s: s.update(session_sha256="other-session"))
    elif damage == "missing_snapshot":
        (part / "saved-records.json").unlink()
    else:
        edit(root, "runs/part1/saved-records.json", lambda s: s.update(runs=s["runs"][:1]))
    value = session_status(root)
    assert expected in codes(value) and value["next_part"] is None
    assert value["state"] == ("recorded_in_progress" if damage == "running" else "needs_review")
    assert value["parts"][0]["execution_directory_exists"]
    assert "secret-value" not in json.dumps(value)


def test_running_task_blocks_but_ended_unknown_attempt_retains_unknown(tmp_path):
    root = archive(tmp_path, "02")
    path = "runs/part1/saved-records.json"
    data = read_json(root / path)
    edit(root, path, lambda d: d["analysis_tasks"][0].update(state="running", ended_at=None))
    assert codes(session_status(root)) == {"analysis_still_open"}
    # Explicitly controlled variation of a stored incident attempt, not a new business result.
    run = data["runs"][0]
    attempt = next(a for a in data["analysis_attempts"] if a["run_id"] == run["id"])
    task = next(t for t in data["analysis_tasks"] if t["id"] == attempt["task_id"])
    run.update(state="unknown", ended_at=None)
    attempt["outcome"], task["state"] = "unknown", "failed"
    (root / path).write_bytes(json_bytes(data))
    value = session_status(root)
    assert value["state"] == "waiting_append" and value["next_part"] == "part2"
    assert any(a["outcome"] == "unknown" for a in value["parts"][0]["attempts"])
    assert any(r["state"] == "unknown" for r in value["parts"][0]["runs"])
    attempt["run_id"] = None
    (root / path).write_bytes(json_bytes(data))
    assert codes(session_status(root)) == {"run_end_unconfirmed"}


@pytest.mark.parametrize("effect", ["send", "http"])
def test_unconfirmed_effect_blocks_even_with_terminal_snapshot(tmp_path, effect):
    root = archive(tmp_path, "02")
    if effect == "send":
        path = next((root / "runs/part1").glob("send-*"))
        edit(root, str(path.relative_to(root)), lambda s: s["records"][0].update(state="outcome_unknown"))
    else:
        intent = next((root / "runs/part1/http").glob("*.intent.json"))
        edit(root, str(intent.relative_to(root)).replace(".intent.json", ".json"),
             lambda s: s.update(outcome="unknown"))
    value = session_status(root)
    assert value["next_part"] is None
    assert codes(value) == {"send_not_confirmed" if effect == "send" else "http_write_unconfirmed"}


def test_gap_cannot_select_or_replay_a_later_directory(prepared):
    root = prepared[0]
    (root / "runs/part2").mkdir(parents=True)
    value = session_status(root)
    assert value["state"] == "needs_review" and value["next_part"] is None
    assert "part_order_conflict" in codes(value)
    assert value["parts"][0]["recorded_state"] == "not_started"


def test_first_explicit_selection_and_declaration_order(prepared, tmp_path):
    _, profile, session, materials = prepared
    scenario = read_json(materials / "scenario.json")
    scenario["parts"][0]["id"] = "part10"
    for part in scenario["parts"]:
        part["check_level"] = "incident"
    scenario["cases"] = []
    (materials / "part1").rename(materials / "part10")
    (materials / "scenario.json").write_bytes(json_bytes(scenario))
    output = tmp_path / "declared-order"
    prepare_execution(materials, profile, Execution(**session["execution"]), output)
    value = session_status(output)
    assert [p["id"] for p in value["parts"]] == ["part10", "part2"]
    assert value["state"] == "selection_required" and value["first_part"] == "part10"
    assert value["next_part"] is None


def test_all_parts_terminal_does_not_claim_business_or_quality_passed(tmp_path):
    root = archive(tmp_path, "02")
    # Controlled single-part variant: change only the future plan and its bindings.
    session = read_json(root / "session.json")
    scenario = read_json(root / "wire/scenario.json")
    scenario["parts"] = scenario["parts"][:1]
    for case in scenario["cases"]:
        case["check_after_parts"] = []
    (root / "wire/scenario.json").write_bytes(json_bytes(scenario))
    shutil.rmtree(root / "wire/part2")
    plan = inspect_package(root / "wire", control(Profile, session["profile"], "profile"))
    session.update(plan=plan, wire_sha256=plan["material_sha256"], scenario_sha256=plan["scenario_sha256"],
                   identities={k: v for k, v in session["identities"].items() if k in plan["material_sha256"]})
    (root / "session.json").write_bytes(json_bytes(session))
    edit(root, "runs/part1/state.json", lambda s: s.update(session_sha256=sha256((root / "session.json").read_bytes())))
    value = session_status(root)
    assert value["state"] == "all_parts_completed" and value["next_part"] is None
    assert all(p["recorded_state"] == "completed_with_issues" and not p["results"]
               and p["quality"] == "not_fully_evaluated" for p in value["parts"])


def test_invalid_session_is_rejected_without_report(tmp_path, capsys):
    root = tmp_path / "invalid"
    root.mkdir()
    (root / "session.json").write_bytes(json_bytes({"schema_version": "socai2.acceptance-prepared.v1"}))
    report = tmp_path / "status.json"
    assert main(["status", "--prepared", str(root), "--report", str(report)]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "invalid prepared execution"
    assert not report.exists()


@pytest.mark.parametrize("damage,expected", [("steps", "saved_closure_mismatch"), ("http_response", "http_write_unconfirmed")])
def test_invalid_nested_receipts_still_save_a_fixed_diagnostic(tmp_path, capsys, damage, expected):
    root = archive(tmp_path, "02")
    if damage == "steps":
        edit(root, "runs/part1/state.json", lambda s: s.update(steps=["invalid secret-value"]))
    else:
        intent = next((root / "runs/part1/http").glob("*.intent.json"))
        edit(root, str(intent.relative_to(root)).replace(".intent.json", ".json"), lambda s: s.update(response=[]))
    before = snapshot(root)
    report = tmp_path / "status.json"
    assert main(["status", "--prepared", str(root), "--report", str(report)]) == 3
    console, value = json.loads(capsys.readouterr().out), read_json(report)
    assert console["state"] == value["state"] == "needs_review" and value["next_part"] is None
    assert codes(value) == {expected} and not value["parts"][0]["closure_verified"]
    assert "secret-value" not in json.dumps(value) and before == snapshot(root)


def test_orphan_attempt_task_blocks_next_part(tmp_path):
    root = archive(tmp_path, "02")
    edit(root, "runs/part1/saved-records.json",
         lambda d: d["analysis_attempts"][0].update(task_id="11111111-1111-4111-8111-111111111111"))
    value = session_status(root)
    assert value["state"] == "needs_review" and value["next_part"] is None
    assert codes(value) == {"saved_execution_link_mismatch"} and not value["parts"][0]["closure_verified"]


@pytest.mark.parametrize("damage", ["subject", "run", "result"])
def test_saved_execution_links_validate_subject_and_result_without_mixing_sessions(damage):
    # Read this local continuation snapshot only to validate its own graph, never as the 21 part's closure.
    data = read_json(EVIDENCE / "acceptance-case-continuation-20261117-01/execution-03/saved-records.json")
    execution_links(data)
    attempt = next(a for a in data["analysis_attempts"] if a["subject_type"] == "case" and a["run_id"])
    incident_run = next(r["id"] for r in data["runs"] if r["incident_id"])
    if damage == "subject":
        attempt["subject_id"] = data["incidents"][0]["id"]
    elif damage == "run":
        attempt["run_id"] = incident_run
    else:
        data["results"][0]["source_run_id"] = incident_run
    with pytest.raises(ReceiptError, match="saved_execution_link_mismatch"):
        execution_links(data)
