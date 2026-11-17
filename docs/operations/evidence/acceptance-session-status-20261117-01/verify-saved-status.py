"""Offline 3c.1 evidence reproduction; copies historic bytes, never resumes a run."""
import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance import main
from acceptance_materials import read_json, save_report
from alert_scenarios import sha256


def snapshot(folder):
    return {str(p.relative_to(folder)): sha256(p.read_bytes()) for p in sorted(folder.rglob("*")) if p.is_file()}


def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    origins, observations = [], []
    blocked, credential_reads = [], []
    for batch in ("01", "02"):
        source = ROOT / "docs/operations/evidence" / ("acceptance-singlepart-20261117-" + batch)
        before = {name: snapshot(source / name) for name in ("prepared", "runs")}
        with tempfile.TemporaryDirectory(prefix="socai2-status-") as tmp:
            prepared = Path(tmp) / "prepared"
            shutil.copytree(source / "prepared", prepared)
            shutil.copytree(source / "runs", prepared / "runs")
            staged = snapshot(prepared)
            expected = {**before["prepared"], **{"runs/" + p: h for p, h in before["runs"].items()}}
            assert staged == expected
            connections = set(read_json(prepared / "session.json")["profile"]["connection_files"].values())
            old_open = Path.open

            def guarded_open(path, *args, connections=connections, old_open=old_open, **kwargs):
                if str(path) in connections:
                    credential_reads.append(str(path))
                    raise AssertionError("connection file read prohibited")
                return old_open(path, *args, **kwargs)

            def no_socket(*args, **kwargs):
                blocked.append("socket")
                raise AssertionError("business connections prohibited")

            report = output / ("status-" + batch + ".json")
            args = ["status", "--prepared", str(prepared), "--report", str(report)]
            console = io.StringIO()
            with contextlib.redirect_stdout(console), patch("socket.socket", side_effect=no_socket), \
                    patch.object(Path, "open", guarded_open):
                exit_code = main(args)
            value = read_json(report)
            assert exit_code == (3 if batch == "01" else 0)
            assert value["state"] == ("needs_review" if batch == "01" else "waiting_append")
            assert value["next_part"] == (None if batch == "01" else "part2")
            assert snapshot(prepared) == staged
            for entry in value["sources"]:
                assert expected[entry["path"]] == entry["sha256"]
            assert not any(value["this_command"].values()) and not value["live_state_verified"]
            part = value["parts"][0]
            if batch == "02":
                assert part["recorded_state"] == "completed_with_issues"
                assert not part["results"] and not any(r["case_id"] for r in part["runs"])
                assert [t["state"] for t in part["tasks"] if t["subject_type"] == "case"] == ["failed"]
            observed = {"batch": batch, "argv": args, "exit_code": exit_code,
                        "console": json.loads(console.getvalue()), "report_sha256": sha256(report.read_bytes()),
                        "report_readback": "passed", "copy_byte_identity": "passed",
                        "prepared_before_after": "identical", "original_before_after": "identical",
                        "temporary_copy_removed_after_read": True}
        assert before == {name: snapshot(source / name) for name in ("prepared", "runs")}
        origins.append({"batch": batch, "source_directory": str(source.relative_to(ROOT)), "files": expected,
                        "mapping": {"session/wire": "prepared/", "runs": "runs/"}})
        observations.append(observed)
    assert not blocked and not credential_reads
    assert "acceptance_run" not in sys.modules and "acceptance_clients" not in sys.modules
    save_report(output / "source-manifest.json", {"scope": "archived saved receipts, not a live environment", "origins": origins})
    save_report(output / "verification.json", {"status": "passed", "observations": observations,
                "socket_attempts": len(blocked), "connection_file_reads": len(credential_reads),
                "run_or_clients_imported": False, "new_business_connections": 0, "new_kafka_sends": 0,
                "new_model_calls": 0, "old_receipts_unchanged": True,
                "not_verified": ["live 21 state", "append execution", "interactive menu", "Docker image", "model quality"]})
    print(json.dumps({"status": "passed", "reports": str(output), "historic_batches": 2, "new_business_actions": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
