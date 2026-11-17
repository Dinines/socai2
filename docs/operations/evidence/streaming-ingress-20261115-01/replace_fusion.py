"""Replace only this candidate's Fusion after its exact source fix passes tests."""
import json
import subprocess
import sys
from datetime import datetime, timezone

v = json.load(sys.stdin)
c, u = v["config"], v["upgrade"]
k = c["kafka"]


def run(args):
    return subprocess.run(args, check=True, text=True, capture_output=True,
                          timeout=c["timeout_seconds"]).stdout


def offsets():
    text = run(["docker", "exec", k["container"], "kafka-consumer-groups",
                "--bootstrap-server", k["metadata_bootstrap"], "--describe", "--group", k["group"]])
    rows = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[0] == k["group"]:
            rows[fields[1]] = {"partition": int(fields[2]), "committed": int(fields[3]),
                               "end": int(fields[4]), "lag": int(fields[5])}
    assert set(rows) == {k["topics"][role] for role in u["expected_offsets"]}
    for role, expected in u["expected_offsets"].items():
        assert rows[k["topics"][role]] == {"partition": 0, "committed": expected, "end": expected, "lag": 0}
    return rows


assert v["direct_tests_passed"] is True
before = json.loads(run(["docker", "inspect", c["fusion_container"]]))[0]
assert before["Image"] == u["previous_image"] and before["State"]["Running"]
names = set(run(["docker", "ps", "-a", "--format", "{{.Names}}"] ).splitlines())
assert u["retired_container"] not in names
baseline = offsets()
run(["docker", "stop", "--time", str(u["stop_timeout_seconds"]), c["fusion_container"]])
stopped = json.loads(run(["docker", "inspect", c["fusion_container"]]))[0]
assert not stopped["State"]["Running"]
run(["docker", "rename", c["fusion_container"], u["retired_container"]])
new_id = run(["docker", "run", "-d", "--name", c["fusion_container"], "--network", c["network"],
              "--workdir", c["fusion_workdir"], "--env-file", c["root"] + "/private/fusion.env", "--restart", "no",
              "--mount", "type=bind,src=" + k["ca_source"] + ",dst=" + k["ca_target"] + ",readonly",
              "--mount", "type=bind,src=" + c["root"] + "/initial-task-policy.json,dst=/run/config/initial-task-policy.json,readonly",
              "--entrypoint", "python", u["next_image"], "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0",
              "--port", str(c["fusion_http_port"])]).strip()
print(json.dumps({"status": "started_awaiting_readback", "candidate_id": c["candidate_id"],
                  "observed_at": datetime.now(timezone.utc).isoformat(), "release": u["release"],
                  "previous_container_id": before["Id"], "retired_container": u["retired_container"],
                  "old_exit_code": stopped["State"]["ExitCode"], "new_container_id": new_id,
                  "new_image_id": u["next_image"], "retained_offsets": baseline,
                  "materials_or_results_rewritten": False, "models_enabled": False}, indent=2))
