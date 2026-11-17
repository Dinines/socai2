"""Stop only the recorded batch processes, dedicated tunnel and dependency project."""
import argparse
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--config", type=Path, required=True)
args = parser.parse_args()
private = args.config.resolve().parent
config = json.loads(args.config.read_text())
out = Path(__file__).parent
validation = json.loads((out / "final-validation.json").read_text())
assert validation["active_attempts_at_end"] == 0
processes = json.loads((private / "processes-01.json").read_text())
stopped = []
for name, row in processes.items():
    command = subprocess.run(["ps", "-p", str(row["pid"]), "-o", "command="], capture_output=True, text=True).stdout
    assert " ".join(row["argv"][1:]) in command, "recorded_pid_changed:" + name
    os.kill(row["pid"], signal.SIGTERM)
    stopped.append(name)
forward = config["model_forward"]
result = subprocess.run(["ssh", "-S", forward["control_socket"], "-O", "exit", forward["ssh_alias"]], capture_output=True, text=True)
assert result.returncode == 0, "dedicated_forward_shutdown_failed"
dependency = Path(config["dependency_configuration"])
command = [config["docker"], "--context", config["docker_context"], "compose", "--env-file", str(dependency / "compose.env"),
           "-f", str(dependency / "compose.yml"), "stop"]
result = subprocess.run(command, capture_output=True, text=True, timeout=config["startup_timeout_seconds"])
assert result.returncode == 0, "batch_dependencies_stop_failed"
ports = [config[k] for k in ("http_port", "fusion_port", "kafka_port", "lake_port", "lake_http_port", "redis_port",
                            "model_gateway_port", "tokenizer_port")]
deadline = time.monotonic() + config["startup_timeout_seconds"]
while True:
    opened = []
    for port in ports:
        with socket.socket() as sock:
            sock.settimeout(config["poll_interval_seconds"])
            if sock.connect_ex((config["bind"], port)) == 0:
                opened.append(port)
    if not opened:
        break
    assert time.monotonic() < deadline, "batch_ports_not_closed"
    time.sleep(config["poll_interval_seconds"])
receipt = {"status": "passed", "stopped_processes": stopped, "dedicated_model_forward_closed": True,
           "closed_ports": ports, "dependency_action": "compose stop, no down/remove/volume deletion",
           "databases_and_evidence_retained": True, "no_deployment_to_21": True}
with (out / "cleanup.json").open("x") as file:
    json.dump(receipt, file, indent=2)
    file.write("\n")
print("Batch processes and dependencies stopped; both batches' databases and evidence retained")
