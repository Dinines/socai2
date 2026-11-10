"""Install or inspect the V1 investigation processing services on sting-infra21."""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

HERE = Path(__file__).resolve().parent
BASE = Path("/opt/sting-aisoc-socai2")
RELEASES = BASE / "releases"
ENTRY = BASE / "ops/processing-production.py"
STATE = BASE / "state/production-projection"
IMAGE = "sha256:7218b535ca88c17616f563aa1efb6935f8eedd89e5fed4140ea6c8e4949c0be7"
PROJECTOR = "socai2-investigation-projection"
WORKBENCH = "socai2-production-workbench"
SSH = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8", "sting-infra21"]


class DeployError(Exception):
    """Operator-safe error message without subprocess logs or credentials."""


def need(test, message):
    if not test:
        raise DeployError(message)


def call(args, phase, *, cwd=None, body=None, timeout=150):
    result = subprocess.run(args, input=body, capture_output=True, check=False, cwd=cwd, timeout=timeout)
    if result.returncode:
        # Forward only our bounded error code, never Docker environment, SQL, or private arguments.
        lines = result.stdout.decode(errors="replace").splitlines()
        try:
            reason = json.loads(lines[-1]).get("error", "")
        except (ValueError, IndexError, AttributeError):
            reason = ""
        suffix = " (" + reason + ")" if re.fullmatch(r"[A-Za-z0-9_ .:-]{1,160}", str(reason)) else ""
        raise DeployError(phase + " failed" + suffix)
    return result.stdout.decode("utf-8").strip()


def release_path(value, component):
    path = Path(value)
    need(path.parent == RELEASES and re.fullmatch(r"production-" + component + r"-[0-9a-f]{16}", path.name),
         "invalid " + component + " release")
    return path


def host_release(value, component):
    path = release_path(value, component)
    need(path.is_dir() and path.resolve() == path and path.stat().st_uid == 0, "unrecognized release directory")
    return path


def inspect(name):
    args = ["docker", "inspect", "--format", "{{.Image}} {{.State.Status}} {{.State.Health.Status}}", name]
    values = call(args, "inspect " + name).split()
    need(len(values) == 3 and values[0] == IMAGE, "unexpected " + name + " image")
    return values[1:]


def mounted(name, destination):
    query = '{{range .Mounts}}{{if eq .Destination "' + destination + '"}}{{.Source}} {{.RW}}{{end}}{{end}}'
    value = call(["docker", "inspect", "--format", query, name], "inspect mounted release")
    source, _, rw = value.rpartition(" ")
    need(rw == "false" and source.startswith("/"), "expected read-only release mount")
    return Path(source)


def check_entry(*, required):
    if ENTRY.is_symlink():
        target = ENTRY.resolve(strict=True)
        path = host_release(target.parents[2], "processing")
        need(target == path / "deploy/aisoc21/production_processing.py", "unrecognized production pointer")
        return path
    need(not ENTRY.exists() and not required, "missing or foreign production pointer")
    return None


def projection_command(folder, args, *, activation=False):
    compose = ["docker", "compose", "-p", PROJECTOR, "-f", "compose.production-projection.yml"]
    if activation:
        compose.extend(("-f", "compose.projection-activate.yml"))
    return call([*compose, *args], "projection " + args[-1], cwd=folder)


def start_projection(folder):
    boundary = STATE / "activation.json"
    need(STATE.resolve() == STATE, "invalid projection state path")
    STATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.chown(STATE, 10001, 10001)
    need(not boundary.is_symlink(), "invalid activation record")
    # A fresh consumer anchors only future deliveries. On every later install
    # status checks the existing committed offsets without writing to Kafka.
    # Refuse a missing group offset after activation; never reset it on deploy.
    if boundary.is_file():
        projection_command(folder, ["run", "--rm", "--no-deps", "--pull", "never", "projection", "status"])
    else:
        need(not call(["docker", "ps", "-aq", "--filter", "name=^/" + PROJECTOR + "$"], "inspect projection"),
             "existing projection lost activation record")
        projection_command(folder, ["run", "--rm", "--no-deps", "--pull", "never", "projection", "activate"], activation=True)
    projection_command(folder, ["up", "-d", "--no-build", "--pull", "never", "projection"])


def healthy():
    deadline = time.monotonic() + 150
    for name in (PROJECTOR, WORKBENCH):
        while time.monotonic() < deadline:
            state, health = inspect(name)
            if state == "running" and health == "healthy":
                break
            need(state not in {"dead", "exited"}, name + " stopped")
            time.sleep(2)
        else:
            raise DeployError(name + " health check timed out")


def verify_services(processor, workbench):
    healthy()
    folder = processor / "deploy/aisoc21"
    for name in ("production_projection.py", "production_ingress.py"):
        need(mounted(PROJECTOR, "/opt/processor/" + name) == folder / name, "projection release mismatch")
    need(mounted(PROJECTOR, "/var/lib/socai2-projection") == STATE, "projection boundary must be read-only")
    need(mounted(WORKBENCH, "/opt/workbench") == workbench, "workbench release mismatch")
    status = call(["docker", "exec", PROJECTOR, "python", "-B", "/opt/processor/production_projection.py", "status"],
                  "verify projection position")
    data = json.loads(status.splitlines()[-1])
    need(data.get("group") == "socai2-investigation-projection-v1" and data.get("topic") == "socai2.alerts.fused"
         and data.get("database") == "aisoc" and data.get("schema") == "socai2", "projection status mismatch")
    with build_opener(ProxyHandler({})).open("http://127.0.0.1:4177/_workbench/status", timeout=8) as reply:
        panel = json.loads(reply.read(65536))
    need(panel["source"] == "aisoc" and panel["enabled"] is True, "workbench source mismatch")
    return data


def host(mode, paths, processing_profile):
    import fcntl  # Linux on 21; the orchestrator may run on Windows.

    need(os.geteuid() == 0 and ENTRY.parent == ENTRY.parent.resolve() and ENTRY.parent.is_dir(), "21 host layout required")
    # Lock the existing directory; verify mode creates no lock file or deployment state.
    lock = os.open(ENTRY.parent, os.O_RDONLY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        prior = check_entry(required=mode == "verify")
        if mode == "apply":
            processor = host_release(paths[0], "processing")
            workbench = host_release(paths[1], "workbench")
        else:
            processor = prior
            workbench = host_release(mounted(WORKBENCH, "/opt/workbench"), "workbench")
        launcher = processor / "deploy/aisoc21/production_processing.py"
        if mode == "apply":
            call(["python3", str(launcher), "--profile", processing_profile, "install"], "install processor")
        receipt = json.loads(call(["python3", str(launcher), "--profile", processing_profile, "check"], "check processor").splitlines()[-1])
        need(receipt.get("database") == "aisoc" and receipt.get("db_role") == "socai2_prod_processor"
             and receipt.get("lake_table") == "aisoc.raw_events" and receipt.get("model_calls") == 0,
             "processor target check mismatch")
        if mode == "apply":
            start_projection(launcher.parent)
            call(["python3", str(workbench / "deploy/aisoc21/install_production_workbench.py")], "install workbench")
        status = verify_services(processor, workbench)
        if mode == "apply" and prior != processor:
            staged = ENTRY.with_name("." + ENTRY.name + "." + str(os.getpid()))
            staged.symlink_to(launcher)
            try:
                staged.replace(ENTRY)
            finally:
                staged.unlink(missing_ok=True)
        need(check_entry(required=True) == processor, "production pointer mismatch")
        print(json.dumps({"mode": mode, "database": "aisoc", "schema": "socai2", "processing": processor.name,
                          "workbench": workbench.name, "job_entry": str(ENTRY), "projection_group": status["group"],
                          "partitions": status["partitions"], "model_calls": 0, "business_jobs_dispatched": 0}))
    finally:
        os.close(lock)


def local(mode, processing_profile):
    schema = HERE.parent / "database/install_aisoc21_v1.py"
    output = call([sys.executable, str(schema), mode], "schema " + mode, timeout=180)
    need("verified_socai2_v1 29_tables_462_columns" in output, "V1 schema verification missing")
    releases = []
    if mode == "apply":
        for component in ("processing", "workbench"):
            path = call([sys.executable, str(HERE / "publish_production_files.py"), component], "publish " + component)
            # Parse a POSIX remote path independently of the orchestrator OS.
            need(re.fullmatch("/opt/sting-aisoc-socai2/releases/production-" + component + "-[0-9a-f]{16}", path),
                 "unexpected published release")
            releases.append(path)
    command = shlex.join(["python3", "-I", "-", "--processing-profile", processing_profile, "--host", mode, *releases])
    result = call([*SSH, command], "21 " + mode, body=Path(__file__).read_bytes(), timeout=680)
    print(result)


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--host", action="store_true", help=argparse.SUPPRESS)
    args.add_argument("--processing-profile", required=True, help="explicit profile file already placed on 21")
    args.add_argument("mode", choices=("apply", "verify"))
    args.add_argument("releases", nargs="*", help=argparse.SUPPRESS)
    opts = args.parse_args()
    try:
        need(len(opts.releases) == (2 if opts.host and opts.mode == "apply" else 0), "unexpected release arguments")
        if opts.host:
            host(opts.mode, opts.releases, opts.processing_profile)
        else:
            local(opts.mode, opts.processing_profile)
    except Exception as exc:  # noqa: BLE001 -- never disclose subprocess environments
        print(json.dumps({"error": str(exc) if isinstance(exc, DeployError) else type(exc).__name__}))
        sys.exit(1)
