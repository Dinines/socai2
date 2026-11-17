"""3c.3 independent offline console checks; execution callbacks copy saved receipts only."""
import copy
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
FROZEN = HERE / "console-freeze-01"
OUT = HERE / "independent-console-data-01"
COMPLETE = ROOT / "docs/operations/evidence/acceptance-append-20261117-02/prepared"
INCOMPLETE = ROOT / "docs/operations/evidence/acceptance-append-20261117-01/prepared"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


freeze = read(FROZEN / "manifest.json")["files"]
for f in freeze:
    assert sha(FROZEN / f["path"]) == sha(ROOT / f["path"]) == f["sha256"]
previous = {f["path"]: f["sha256"] for f in read(HERE / "report-freeze-03/manifest.json")["files"]}
for f in freeze:
    if f["path"] in {"tools/testdata/acceptance_report.py", "tools/testdata/acceptance_report_models.py", "tools/testdata/acceptance_report_render.py"}:
        assert f["sha256"] == previous[f["path"]]
OUT.mkdir()
sys.dont_write_bytecode = True
sys.path[:0] = [str(FROZEN / "tools/testdata"), str(ROOT / "tools/testdata")]
from acceptance_console import run_console
from acceptance_status import session_status

before = {"02": inventory(COMPLETE), "01": inventory(INCOMPLETE)}
assert before == read(HERE / "independent-report-data-03/source-hashes.json")
connections = {pathlib.Path(p).resolve() for root in (COMPLETE, INCOMPLETE)
               for p in read(root / "session.json")["profile"]["connection_files"].values()}
attempted_access = []
original_open = pathlib.Path.open


def open_file(path, *args, **kwargs):
    if path.resolve() in connections:
        attempted_access.append("connection_file")
        raise AssertionError("connection files forbidden")
    return original_open(path, *args, **kwargs)


def no_socket(*args, **kwargs):
    attempted_access.append("socket")
    raise AssertionError("network forbidden")


def no_execute(*args, **kwargs):
    raise AssertionError("read-only selection cannot dispatch")


def console(prepared, name, commands, execute=no_execute):
    transcript = []
    values = iter(commands)

    def next_input(_prompt):
        try:
            value = next(values)
        except StopIteration:
            raise EOFError from None
        if isinstance(value, BaseException):
            raise value
        return value

    output = OUT / name
    with patch.object(pathlib.Path, "open", open_file), patch("socket.socket", no_socket), patch("socket.create_connection", no_socket):
        code = run_console(prepared, output, read=next_input, write=transcript.append, execute=execute)
    end = read(output / "end.json")
    assert code == end["exit_code"]
    assert not end["permanently_closed"] and not end["remote_cancellation_requested"] and not end["live_state_verified"]
    with (output / "transcript.txt").open("x") as stream:
        stream.write("\n".join(transcript) + "\n")
    assert "PRIVATE_SENTINEL" not in "\n".join(transcript)
    assert all("PRIVATE_SENTINEL" not in p.read_text() for p in output.rglob("*.json"))
    return end


observations = {}
observations["complete"] = console(COMPLETE, "complete", ["", "view", "invalid PRIVATE_SENTINEL", "run part1", "report", "quit"])
observations["incomplete"] = console(INCOMPLETE, "incomplete", ["run part1", "append part2", "finish"])
observations["eof"] = console(COMPLETE, "eof", [])
observations["interrupt"] = console(COMPLETE, "interrupt", [KeyboardInterrupt()])
assert all(v["execution_attempts"] == 0 for v in observations.values())
assert observations["complete"]["all_parts_completed"] and observations["complete"]["reason"] == "quit"
assert observations["incomplete"]["exit_code"] == 3 and observations["incomplete"]["blocked_parts"] == ["part1"]
assert observations["incomplete"]["unsent_parts"] == ["part2"] and not observations["incomplete"]["all_parts_completed"]
assert observations["eof"]["report"] is None and observations["interrupt"]["report"] is None
assert observations["interrupt"]["exit_code"] == 130

controlled_actions = []
with tempfile.TemporaryDirectory(prefix="socai2-console-independent-") as temporary:
    prepared = pathlib.Path(temporary) / "prepared"
    shutil.copytree(COMPLETE, prepared, ignore=shutil.ignore_patterns("runs", "__pycache__"))
    active_output = None

    def execute(action, directory, part):
        intents = list(active_output.glob("*-intent.json"))
        assert len(intents) == 1 and not list(active_output.glob("*-result.json"))
        intent = read(intents[0])
        assert (intent["action"], intent["part"]) == (action, part)
        assert directory == prepared and session_status(prepared)["next_part"] == part
        controlled_actions.append({"action": action, "part": part, "intent_before_callback": True,
                                   "backend": "controlled_copy_of_existing_saved_receipts"})
        shutil.copytree(COMPLETE / "runs" / part, prepared / "runs" / part)
        return read(prepared / "runs" / part / "state.json")

    active_output = OUT / "controlled-first"
    first = console(prepared, "controlled-first", ["run part1", "quit"], execute)
    assert first["execution_attempts"] == 1 and first["unsent_parts"] == ["part2"]
    assert first["observed_execution_state"] == "waiting_append" and not (prepared / "runs/part2").exists()
    first_hashes = inventory(prepared / "runs/part1")
    active_output = OUT / "controlled-append"
    second = console(prepared, "controlled-append", ["view", "append part2", "quit"], execute)
    assert second["execution_attempts"] == 1 and second["all_parts_completed"]
    assert first_hashes == inventory(prepared / "runs/part1")
    reopened = console(prepared, "controlled-completed-reopen", ["run part1", "append part2", "quit"])
    assert reopened["execution_attempts"] == 0
    # A source hash change is enough to invalidate an old choice even when its part stays identical.
    empty = pathlib.Path(temporary) / "empty"
    shutil.copytree(COMPLETE, empty, ignore=shutil.ignore_patterns("runs", "__pycache__"))
    ready = session_status(empty)
    changed = copy.deepcopy(ready)
    changed["sources"][0]["sha256"] = "0" * 64
    with patch("acceptance_console.session_status", side_effect=[ready, changed, changed]):
        source_change = console(empty, "changed-source", ["run part1", "quit"])
    assert source_change["execution_attempts"] == 0 and not list((OUT / "changed-source").glob("*-intent.json"))
    assert "重新选择" in (OUT / "changed-source/transcript.txt").read_text()
    unknown_calls = []

    def uncertain(*args):
        assert len(list((OUT / "controlled-unknown").glob("*-intent.json"))) == 1
        unknown_calls.append("controlled_unknown_callback")
        raise RuntimeError("PRIVATE_SENTINEL")

    unknown = console(empty, "controlled-unknown", ["run part1", "run part1", "quit"], uncertain)
    assert len(unknown_calls) == 1 and unknown["exit_code"] == 3
    assert unknown["unconfirmed_parts"] == unknown["blocked_parts"] == ["part1"]
    assert unknown["unsent_parts"] == ["part2"]

assert controlled_actions == [
    {"action": "run", "part": "part1", "intent_before_callback": True, "backend": "controlled_copy_of_existing_saved_receipts"},
    {"action": "append", "part": "part2", "intent_before_callback": True, "backend": "controlled_copy_of_existing_saved_receipts"}]
for folder, prior in ((OUT / "complete/reports/0001", HERE / "independent-report-data-03/report-02"),
                      (OUT / "incomplete/reports/0001", HERE / "independent-report-data-03/report-01")):
    generated, previous_report = read(folder / "report.json"), read(prior / "report.json")
    generated.pop("observed_at")
    previous_report.pop("observed_at")
    assert generated == previous_report
    for f in read(folder / "manifest.json")["files"]:
        assert sha(folder / f["path"]) == f["sha256"]
assert before == {"02": inventory(COMPLETE), "01": inventory(INCOMPLETE)} and not attempted_access
for f in freeze:
    assert sha(FROZEN / f["path"]) == sha(ROOT / f["path"]) == f["sha256"]
save(OUT / "original-source-hashes.json", before)
summary = {"status": "passed", "freeze": "console-freeze-01/manifest.json", "actual_readonly_observations": observations,
    "controlled_actions": controlled_actions, "controlled_unknown_callbacks": len(unknown_calls),
    "first_part_files_unchanged": len(first_hashes), "same_candidate_source_change": "reselection_required_no_intent",
    "reopen_completed_attempts": reopened["execution_attempts"], "report_values_match_accepted_step1": True,
    "original_file_counts_unchanged": {k: len(v) for k, v in before.items()}, "forbidden_access_attempts": attempted_access,
    "new_business_executions": 0, "new_kafka_sends": 0, "new_model_calls": 0,
    "scope": "Frozen console plus accepted report. Controlled callbacks do not represent real business execution."}
save(OUT / "validation.json", summary)
save(OUT / "evidence-hashes.json", inventory(OUT))
print(json.dumps({k: v for k, v in summary.items() if k != "actual_readonly_observations"}, ensure_ascii=False, indent=2))
