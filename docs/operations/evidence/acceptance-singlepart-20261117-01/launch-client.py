"""Launch this batch's isolated client; leave existing business services unchanged."""
import json
import os
import subprocess
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text())
root = Path(config["remote_directory"])
observed = {}
for kind, name in config["services"].items():
    value = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
    if not value["State"]["Running"]:
        raise SystemExit("required service is not running")
    observed[kind] = {"name": name, "id": value["Id"], "image_id": value["Image"], "running": True}
    if kind == "dispatcher":
        environment = dict(v.split("=", 1) for v in value["Config"]["Env"])
image = json.loads(subprocess.check_output(["docker", "image", "inspect", config["image"]]))[0]
if image["Id"] != config["image_id"] or observed["dispatcher"]["image_id"] != config["image_id"]:
    raise SystemExit("explicit existing processing image differs")
(root / "services-before.json").write_text(json.dumps(observed, indent=2) + "\n")
private = root / "private"
private.mkdir(mode=0o700)
secret = Path(config["private_password_file"])
with secret.open("x") as handle:
    handle.write(environment[config["secret_env_key"]])
os.chmod(secret, 0o400)
os.chown(secret, 10001, 10001)
output = root / "runs"
output.mkdir(mode=0o700)
os.chown(output, 10001, 10001)
(root / "prepared" / "runs").mkdir()
command = ["docker", "run", "--detach", "--name", config["container_name"],
           "--network", config["network"], "--user", config["user"],
           "--workdir", config["workdir"], "--env", "PYTHONDONTWRITEBYTECODE=1"]
for mount in config["mounts"]:
    binding = "type=bind,source=" + mount["source"] + ",target=" + mount["target"]
    command += ["--mount", binding + (",readonly" if mount["readonly"] else "")]
command += ["--entrypoint", config["command"][0], config["image"], *config["command"][1:]]
container = subprocess.check_output(command, text=True).strip()
receipt = {"container_id": container, "container_name": config["container_name"],
           "image_id": config["image_id"], "purpose": "single-part acceptance client",
           "business_service_changes": 0, "historical_cleanup": False}
(root / "client-launch.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
