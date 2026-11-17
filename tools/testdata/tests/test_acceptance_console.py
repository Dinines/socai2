"""Console dispatch is controlled; real archived records are only read, never rerun."""
import copy
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance import main
from acceptance_console import run_console
from acceptance_materials import MaterialError, read_json
from acceptance_status import session_status
from test_acceptance_report import COMPLETE, INCOMPLETE, digest, offline


def inputs(commands):
    iterator = iter(commands)

    def read(_prompt):
        try:
            value = next(iterator)
        except StopIteration:
            raise EOFError from None
        if isinstance(value, BaseException):
            raise value
        return value
    return read


@pytest.fixture
def empty_session(tmp_path):
    root = tmp_path / "prepared"
    shutil.copytree(COMPLETE, root, ignore=shutil.ignore_patterns("runs", "__pycache__"))
    return root


@pytest.mark.parametrize("prepared,commands,reason,code", [
    (COMPLETE, ["", "view", "unknown PRIVATE_SENTINEL", "report", "q"], "quit", 0),
    (INCOMPLETE, ["append part2", "run part1", "view"], "eof", 3),
    (COMPLETE, [KeyboardInterrupt()], "interrupt", 130),
])
def test_saved_console_is_offline_and_preserves_all_originals(tmp_path, monkeypatch, prepared, commands, reason, code):
    before = digest(prepared)
    offline(monkeypatch, prepared)
    output, transcript = tmp_path / "console", []
    with patch("socket.socket", side_effect=AssertionError("offline")), \
            patch("acceptance_console.execute_part", side_effect=AssertionError("cannot execute")):
        actual = run_console(prepared, output, read=inputs(commands), write=transcript.append)
    end = read_json(output / "end.json")
    assert actual == end["exit_code"] == code and end["reason"] == reason
    assert end["execution_attempts"] == 0 and not end["permanently_closed"]
    assert not end["remote_cancellation_requested"] and not end["live_state_verified"]
    assert before == digest(prepared)
    assert "PRIVATE_SENTINEL" not in "\n".join(transcript)
    assert all("PRIVATE_SENTINEL" not in p.read_text() for p in output.rglob("*.json"))


def test_controlled_one_part_then_explicit_append_intent_first_and_reopen(empty_session, tmp_path, monkeypatch):
    output, actions = tmp_path / "console", []
    offline(monkeypatch, empty_session)

    def execute(action, prepared, part):
        intents = sorted(output.glob("*-intent.json"))
        intent = read_json(intents[-1])
        assert intent["action"] == action and intent["part"] == part
        actions.append((action, part))
        assert session_status(prepared)["next_part"] == part
        # Controlled callback: copy previously saved receipts. No real business or model call.
        shutil.copytree(COMPLETE / "runs" / part, prepared / "runs" / part)
        return read_json(prepared / "runs" / part / "state.json")

    def command(_prompt):
        if not actions:
            return "run part1"
        if len(actions) == 1:
            assert not (empty_session / "runs/part2").exists()
            return "quit"
        return "finish"

    with patch("socket.socket", side_effect=AssertionError("controlled dispatch only")):
        code = run_console(empty_session, output, read=command, write=lambda _: None, execute=execute)
    assert code == 0 and actions == [("run", "part1")]
    waiting = read_json(output / "end.json")
    assert waiting["observed_execution_state"] == "waiting_append" and waiting["unsent_parts"] == ["part2"]
    first = digest(empty_session / "runs/part1")
    output = tmp_path / "continuation"
    with patch("socket.socket", side_effect=AssertionError("controlled dispatch only")):
        code = run_console(empty_session, output, read=inputs(["view", "append part2", "finish"]), write=lambda _: None, execute=execute)
    assert code == 0 and actions == [("run", "part1"), ("append", "part2")]
    assert digest(empty_session / "runs/part1") == first
    end = read_json(output / "end.json")
    assert end["all_parts_completed"] and end["unsent_parts"] == [] and end["operator_finished"]
    report = read_json(output / Path(end["report"]).parent / "report.json")
    assert report["models"]["saved_request_count"] == 13
    before = digest(empty_session)
    run_console(empty_session, tmp_path / "reopen", read=inputs(["run part1", "append part2", "quit"]),
                write=lambda _: None, execute=lambda *_: pytest.fail("completed cannot repeat"))
    assert digest(empty_session) == before
    assert read_json(tmp_path / "reopen/end.json")["execution_attempts"] == 0


def test_finish_unsent_session_is_not_business_completion_and_can_reopen(empty_session, tmp_path, monkeypatch):
    offline(monkeypatch, empty_session)
    before = digest(empty_session)
    with patch("socket.socket", side_effect=AssertionError("offline")):
        assert run_console(empty_session, tmp_path / "finish", read=inputs(["finish"]), write=lambda _: None) == 0
        assert run_console(empty_session, tmp_path / "eof", read=inputs([]), write=lambda _: None) == 0
    finished = read_json(tmp_path / "finish/end.json")
    assert finished["operator_finished"] and not finished["all_parts_completed"]
    assert finished["unsent_parts"] == ["part1", "part2"] and finished["report"]
    assert read_json(tmp_path / "eof/end.json")["report"] is None
    assert not (empty_session / "runs").exists() and digest(empty_session) == before


def test_fresh_candidate_change_requires_new_selection(empty_session, tmp_path, monkeypatch):
    first = session_status(empty_session)
    changed = copy.deepcopy(first)
    changed.update(state="waiting_append", next_part="part2", next_action="append_part")
    with patch("acceptance_console.session_status", side_effect=[first, changed, changed]), \
            patch("acceptance_console.execute_part", side_effect=AssertionError("stale selection")):
        assert run_console(empty_session, tmp_path / "changed", read=inputs(["run part1", "quit"]), write=lambda _: None) == 0
    assert not list((tmp_path / "changed").glob("*-intent.json"))


def test_selection_required_needs_full_explicit_command(empty_session, tmp_path):
    ready = session_status(empty_session)
    ready.update(state="selection_required", next_part=None, next_action=None, selection_required=True)
    actions = []

    def execute(action, prepared, part):
        actions.append((action, part))
        shutil.copytree(COMPLETE / "runs/part1", prepared / "runs/part1")
        return {"status": "completed"}

    with patch("acceptance_console.session_status", return_value=ready):
        run_console(empty_session, tmp_path / "selected", read=inputs(["", "run", "3", "run part2", "run part1", "q"]),
                    write=lambda _: None, execute=execute)
    assert actions == [("run", "part1")]


@pytest.mark.parametrize("failure", [RuntimeError("PRIVATE_SENTINEL"), KeyboardInterrupt()])
def test_executor_exception_is_preserved_without_retry_or_private_detail(empty_session, tmp_path, failure):
    calls = []

    def execute(*args):
        calls.append(args)
        raise failure

    output = tmp_path / "unknown"
    code = run_console(empty_session, output, read=inputs(["run part1", "run part1", "quit"]),
                       write=lambda _: None, execute=execute)
    assert len(calls) == 1 and code in {3, 130}
    end = read_json(output / "end.json")
    assert end["issues"][0]["code"] == "execution_outcome_unconfirmed"
    assert end["unconfirmed_parts"] == end["blocked_parts"] == ["part1"]
    assert end["unsent_parts"] == ["part2"]
    assert not end["all_parts_completed"] and not end["remote_cancellation_requested"]
    assert len(list(output.glob("*-intent.json"))) == len(list(output.glob("*-result.json"))) == 1
    assert all("PRIVATE_SENTINEL" not in p.read_text() for p in output.rglob("*.json"))


def test_cli_and_output_protection(empty_session, tmp_path, monkeypatch, capsys):
    with patch("builtins.input", side_effect=EOFError):
        assert main(["session", "--prepared", str(empty_session), "--output", str(tmp_path / "cli")]) == 0
    assert "空输入只重显" in capsys.readouterr().out
    for path in (tmp_path / "cli", empty_session / "console"):
        with pytest.raises((MaterialError, FileExistsError)):
            run_console(empty_session, path, read=inputs([]))


def test_interrupt_while_reporting_still_writes_end(empty_session, tmp_path):
    with patch("acceptance_console.write_session_report", side_effect=KeyboardInterrupt):
        code = run_console(empty_session, tmp_path / "interrupt", read=inputs(["report"]), write=lambda _: None)
    assert code == 130 and read_json(tmp_path / "interrupt/end.json")["reason"] == "interrupt"
