"""Direct append gates; normal transport and same-Case rounds have a local live batch."""
import asyncio
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acceptance_append import AppendRun, append_part, previous_unchanged, scope_members
from acceptance_materials import MaterialError, read_json
from test_acceptance_materials import snapshot
from test_acceptance_saved_readback import load
from test_acceptance_status import archive


@pytest.mark.parametrize("selected", [None, "part1", "part10"])
def test_append_requires_the_explicit_next_part_without_connecting(tmp_path, selected):
    root = archive(tmp_path, "02")
    before = snapshot(root)
    with pytest.raises(MaterialError, match="append_requires_explicit_next"):
        asyncio.run(append_part(root, selected, clients_factory=lambda *_: pytest.fail("must not connect")))
    assert snapshot(root) == before


@pytest.mark.parametrize("damage,code", [("running", "previous_live_execution_not_ended"),
                                       ("identity", "previous_saved_record_changed"),
                                       ("target", "append_connection_configuration_changed")])
def test_live_state_is_rechecked_before_any_send(tmp_path, damage, code):
    root = archive(tmp_path, "02")
    before = snapshot(root / "runs/part1")
    rows = read_json(root / "runs/part1/saved-records.json")
    if damage == "running":
        rows["analysis_tasks"][0].update(state="running", ended_at=None)
    elif damage == "identity":
        rows["results"] = []
        rows["alert_materials"][0]["id"] = "11111111-1111-4111-8111-111111111111"

    class Connections:
        def __init__(self, *_):
            self.pg = SimpleNamespace(snapshot=self.read)

        async def read(self, *_args, **_kwargs):
            return copy.deepcopy(rows)

        async def open(self):
            readiness = read_json(root / "runs/part1/preflight.json")
            if damage == "target":
                readiness["connection_sha256"]["kafka"] = "f" * 64
            return readiness

        async def close(self):
            pass

        async def send(self, *_):
            pytest.fail("live gate must stop before publishing")

    state = asyncio.run(append_part(root, "part2", clients_factory=Connections))
    assert state["status"] == "incomplete" and code in state["error_code"]
    assert state["sent"] == {"alerts": 0, "context": 0}
    assert state["other_parts"] == {"part1": "completed_with_issues"}
    assert state == read_json(root / "runs/part2/state.json")
    assert snapshot(root / "runs/part1") == before
    with pytest.raises(MaterialError, match="append_requires_explicit_next"):
        asyncio.run(append_part(root, "part2", clients_factory=lambda *_: pytest.fail("no replay")))


def test_old_frozen_run_change_is_rejected_and_case_scopes_are_separate(tmp_path):
    root = archive(tmp_path, "02")
    rows = read_json(root / "runs/part1/saved-records.json")
    session = read_json(root / "session.json")
    changed = copy.deepcopy(rows)
    changed["runs"][0]["state"] = "unknown"
    with pytest.raises(MaterialError, match="previous_saved_record_changed:runs"):
        previous_unchanged(rows, changed)
    case = session["plan"]["scenario"]["cases"][0]
    cid = rows["cases"][0]["id"]
    aid = rows["alerts"][0]["id"]
    extra = "11111111-1111-4111-8111-111111111111"
    changed = copy.deepcopy(rows)
    changed["incident_members"].append({"alert_id": extra, "incident_id": rows["incidents"][0]["id"]})
    changed["case_alerts"].append({"alert_id": extra, "case_id": cid})
    assert set(scope_members(session, changed, case, [cid])) == {aid, extra}
    with pytest.raises(MaterialError, match="case_current_scope_mismatch"):
        scope_members(session, changed, {**case, "scope": "alerts"}, [cid])


@pytest.mark.parametrize("missing_new_run", [False, True])
def test_expanded_case_cannot_use_only_the_first_round_result(tmp_path, missing_new_run):
    before, rows = load("first-round-snapshot.json")["rows"], load("final-pg.json")["rows"]
    for data in (before, rows):
        data["incident_members"] = copy.deepcopy(data["incident_alerts"])
    whole = next(c["id"] for c in rows["cases"] if sum(r["case_id"] == c["id"] for r in rows["runs"]) == 2)
    fixed = next(c["id"] for c in rows["cases"] if c["id"] != whole)
    anchor = next(r["alert_id"] for r in before["case_alerts"] if r["case_id"] == fixed)
    if missing_new_run:
        old_ids = {r["id"] for r in before["runs"]}
        removed = {r["id"] for r in rows["runs"] if r["case_id"] == whole and r["id"] not in old_ids}
        tasks = {a["task_id"] for a in rows["analysis_attempts"] if a["run_id"] in removed}
        for table, key, ids in (("runs", "id", removed), ("analysis_tasks", "id", tasks),
                                ("analysis_attempts", "run_id", removed), ("results", "source_run_id", removed),
                                *((t, "run_id", removed) for t in ("run_members", "run_steps", "artifacts"))):
            rows[table] = [r for r in rows[table] if r[key] not in ids]
    runner = AppendRun.__new__(AppendRun)
    runner.previous, runner.part, runner.output = {"rows": before}, {"id": "part2"}, tmp_path
    runner.state = {"cases": {"whole": [whole], "fixed": [fixed]}}
    runner.session = {"identities": {"part1/alerts/001.json": {"predicted_canonical_alert_id": anchor}},
                      "plan": {"scenario": {"cases": [
                          {"key": key, "scope": scope, "alert_refs": ["part1/alerts/001.json"],
                           "create_after_part": "part1", "check_after_parts": ["part2"]}
                          for key, scope in (("whole", "incident"), ("fixed", "alerts"))]}}}
    runner.frozen = lambda: None
    issues = runner.validate_saved(rows)
    expected = [{"case_id": whole, "reason_code": "no_new_case_run_for_current_scope"}] if missing_new_run else []
    assert issues == expected
    report = read_json(tmp_path / "append-readback.json")
    assert report["status"] == ("passed_with_issues" if missing_new_run else "passed")
    assert next(c for c in report["cases"] if c["key"] == "fixed")["scope_changed"] is False
