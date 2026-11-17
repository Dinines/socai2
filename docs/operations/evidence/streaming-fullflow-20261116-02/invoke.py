"""One selected action against the explicit new batch; no service lifecycle commands."""

import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

E = Path(__file__).resolve().parent
R = E.parents[3]


def require_ready(profile):
    activation = json.loads((E / "activation.json").read_text())
    assert (
        activation["release"] == profile["release"]
        and activation["batch_id"] == profile["batch_id"]
    )
    assert activation["status"] == "actual_cleanup_and_release_verified"
    assert activation["processing_image_id"].startswith("sha256:")
    for name in ("cleanup", "release_readiness"):
        item = activation[name]
        path = R / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
    return activation


def remote(profile, argv, payload, label):
    receipt = E / (label + ".json")
    assert not receipt.exists()
    command = [
        "ssh",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=" + str(profile["timeouts"]["ssh_connect_seconds"]),
        profile["ssh_target"],
        shlex.join(argv),
    ]
    with (E / (label + "-intent.json")).open("x") as stream:
        json.dump({"state": "started_outcome_unknown", "action": label}, stream)
    try:
        process = subprocess.run(
            command,
            input=payload,
            capture_output=True,
            text=True,
            timeout=profile["timeouts"]["remote_seconds"],
            check=False,
        )
    except subprocess.TimeoutExpired:
        with receipt.open("x") as stream:
            json.dump(
                {
                    "state": "unknown",
                    "error_type": "ssh_action_timeout",
                    "action": label,
                },
                stream,
            )
        raise
    # Keep failure details private: exception output may contain database addresses
    # or credentials. The public receipt names the protected local log only.
    if process.returncode:
        private = R / ".local" / profile["batch_id"]
        private.mkdir(parents=True, exist_ok=True)
        log = private / (label + ".txt")
        with log.open("x") as stream:
            log.chmod(0o600)
            stream.write(process.stdout + "\n" + process.stderr)
        result = {
            "state": "failed_or_unknown",
            "exit": process.returncode,
            "private_log": str(log.relative_to(R)),
            "action": label,
        }
    else:
        result = {"state": "returned", "exit": 0, "value": json.loads(process.stdout)}
    with receipt.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    assert process.returncode == 0, (
        "Inspect the saved intent and protected log before any recovery."
    )
    return result["value"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("observe", "capture", "http", "send"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--phase")
    args = parser.parse_args()
    assert args.label.replace("-", "").replace("_", "").isalnum()
    profile = json.loads((E / "batch/profile.json").read_text())
    activation = require_ready(profile)
    payload = None
    if args.action == "observe":
        argv = [
            "docker",
            "exec",
            "-i",
            profile["containers"]["analysis"],
            "python",
            "-c",
            (E / "live-probe.py").read_text(),
            "observe",
        ]
        payload = json.dumps(profile)
    elif args.action == "capture":
        assert args.request
        selected = json.loads(args.request.read_text())
        assert (
            selected["batch_id"] == profile["batch_id"]
            and selected["tenant_id"] == profile["tenant_id"]
        )
        assert set(selected["alert_ids"]) <= set(profile["alert_ids"])
        selected["database"] = profile["database"]
        argv = [
            "docker",
            "exec",
            "-i",
            profile["containers"]["http"],
            "python",
            "-c",
            (E / "capture.py").read_text(),
        ]
        payload = json.dumps(selected)
    elif args.action == "http":
        assert args.request
        request = json.loads(args.request.read_text())
        argv = [
            "python3",
            "-c",
            (E / "http-action.py").read_text(),
            profile["remote_directory"],
            args.label,
        ]
        payload = json.dumps(request)
    else:
        assert args.phase in profile["counts"]
        # A bounded test producer, not a service replacement. Its image, mounts and
        # network are explicit release bindings; no restart/stop/up command exists.
        argv = [
            "docker",
            "run",
            "--rm",
            "--network",
            profile["network"],
            "--user",
            profile["user"],
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--mount",
            "type=bind,src=" + profile["remote_directory"] + ",dst=/batch,readonly",
            "--mount",
            "type=bind,src=" + profile["remote_directory"] + "/out,dst=/batch/out",
            "--mount",
            "type=bind,src="
            + profile["producer_env_source"]
            + ",dst="
            + profile["producer_env_file"]
            + ",readonly",
            "--mount",
            "type=bind,src="
            + profile["ca_source"]
            + ",dst="
            + profile["ca_target"]
            + ",readonly",
            "--entrypoint",
            "python",
            activation["processing_image_id"],
            "/batch/send-batch.py",
            args.phase,
        ]
    value = remote(profile, argv, payload, args.label)
    if args.action == "send":
        value = {
            k: value[k]
            for k in (
                "phase",
                "status",
                "requested",
                "accepted",
                "not_attempted",
                "cleanup_errors",
            )
        }
    elif args.action == "capture":
        value = {k: v for k, v in value.items() if k != "rows"}
    elif args.action == "observe":
        value = {
            "batch_id": value["batch_id"],
            "counts": {k: len(value[k]) for k in ("alerts", "incidents", "cases", "tasks", "runs", "results")},
            "tasks": [{k: t[k] for k in ("id", "subject_type", "state", "reason_code")} for t in value["tasks"]],
            "runs": [{k: r[k] for k in ("id", "kind", "state", "stop_reason")} for r in value["runs"]],
            "case_steps": [{k: s.get(k) for k in ("run_id", "stage_code", "state")} for s in value["case_steps"]],
            "global_running_tasks": value["global_running_tasks"],
        }
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
