"""Direct 3c.3 console proof. Actual originals read-only; execution callback explicitly controlled."""
import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance_console import run_console
from acceptance_materials import read_json, save_report
from alert_scenarios import json_bytes, sha256


def digest(directory):
    files = {str(p.relative_to(directory)): sha256(p.read_bytes()) for p in sorted(directory.rglob("*")) if p.is_file()}
    return {"file_count": len(files), "inventory_sha256": sha256(json_bytes(files))}


def inputs(commands):
    source = iter(commands)

    def read(_prompt):
        try:
            value = next(source)
        except StopIteration:
            raise EOFError from None
        if isinstance(value, BaseException):
            raise value
        return value
    return read


def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    evidence = ROOT / "docs/operations/evidence"
    actual = {batch: evidence / ("acceptance-append-20261117-" + batch) / "prepared" for batch in ("01", "02")}
    original = {batch: digest(path) for batch, path in actual.items()}
    blocked = {path for root in actual.values() for path in read_json(root / "session.json")["profile"]["connection_files"].values()}
    real_open = Path.open

    def guarded(path, *args, **kwargs):
        assert str(path) not in blocked, "connection file read attempted"
        return real_open(path, *args, **kwargs)

    observations, actions = [], []
    with patch("socket.socket", side_effect=AssertionError("network attempted")), patch.object(Path, "open", guarded):
        for batch, commands, reason, expected in (("02", ["", "view", "report", "quit"], "quit", 0),
                ("01", ["view", "append part2", "finish"], "finish", 3), ("02", [], "eof", 0),
                ("02", [KeyboardInterrupt()], "interrupt", 130)):
            target, transcript = output / (batch + "-" + reason), []
            code = run_console(actual[batch], target, read=inputs(commands), write=transcript.append,
                               execute=lambda *_: (_ for _ in ()).throw(AssertionError("actual batch must not execute")))
            end = read_json(target / "end.json")
            assert code == expected and end["reason"] == reason and end["execution_attempts"] == 0
            (target / "transcript.txt").write_text("\n".join(transcript) + "\n")
            observations.append({"batch": batch, "output": str(target.relative_to(output)), "end": end})
        with tempfile.TemporaryDirectory(prefix="socai2-console-controlled-") as temporary:
            root = Path(temporary) / "prepared"
            shutil.copytree(actual["02"], root, ignore=shutil.ignore_patterns("runs", "__pycache__"))
            target = output / "controlled-start"

            def execute(action, prepared, part):
                intent = read_json(sorted(target.glob("*-intent.json"))[-1])
                assert (intent["action"], intent["part"]) == (action, part)
                actions.append({"action": action, "part": part, "backend": "controlled_copy_of_saved_receipts"})
                shutil.copytree(actual["02"] / "runs" / part, prepared / "runs" / part)
                return read_json(prepared / "runs" / part / "state.json")

            transcript = []
            assert run_console(root, target, read=inputs(["run part1", "quit"]), write=transcript.append, execute=execute) == 0
            assert not (root / "runs/part2").exists()
            assert read_json(target / "end.json")["observed_execution_state"] == "waiting_append"
            (target / "transcript.txt").write_text("\n".join(transcript) + "\n")
            first = digest(root / "runs/part1")
            target, transcript = output / "controlled-append", []
            assert run_console(root, target, read=inputs(["view", "append part2", "quit"]), write=transcript.append, execute=execute) == 0
            assert read_json(target / "end.json")["all_parts_completed"]
            (target / "transcript.txt").write_text("\n".join(transcript) + "\n")
            assert digest(root / "runs/part1") == first
            assert [(a["action"], a["part"]) for a in actions] == [("run", "part1"), ("append", "part2")]
    after = {batch: digest(path) for batch, path in actual.items()}
    assert original == after
    files = [{"path": str(p.relative_to(output)), "sha256": sha256(p.read_bytes())} for p in sorted(output.rglob("*")) if p.is_file()]
    value = {"status": "passed", "scope": "actual originals read-only; controlled executor copies explicitly labelled",
             "before": original, "after": after, "observations": observations, "controlled_actions": actions,
             "first_part_unchanged": first, "socket_and_connection_file_guard": "passed",
             "new_business_executions": 0, "new_model_calls": 0, "new_kafka_sends": 0, "files": files}
    save_report(output / "validation.json", value)
    print(json.dumps({"status": "passed", "actual_observations": len(observations), "controlled_actions": len(actions),
                      "new_model_calls": 0, "validation": str(output / "validation.json")}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
