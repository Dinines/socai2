"""Host 21, one bounded replay of the registered three synthetic cards. No shared service changes."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

BASE = Path("/opt/sting-aisoc-socai2")
ROOT = BASE / "evidence/ie-audit-20261106-r300"
RELEASE = BASE / "releases/processing-20261106-r3"
JOB = "three_case_timed_job_20261106.py"
PLAN_SHA = "6eac8f08e7f858f5f18dc4639fadb57364a354e350ec81b12e96ae154e1d2a61"
RELEASE_SHA = "268df0811dce6c27cadd61f77cda97835201e24d82a6cf6e9c06c805e7541aa5"


def now():
    return datetime.now(timezone.utc).isoformat()


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def save(path, value):
    with path.open("x", encoding="utf8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())


def source_key():
    # Read only the provider credential on 21. The value travels on job stdin, never in argv/receipts.
    check = ("import os,sys;from urllib.parse import urlsplit;"
             "u=urlsplit(os.environ['AISOC_LLM_API_BASE']);"
             "assert (u.scheme,u.hostname,u.port,u.path.rstrip('/'))==('http','192.168.1.43',8000,'/v1');"
             "k=os.environ['OPENAI_API_KEY'];assert k and not any(c in k for c in '\\r\\n');sys.stdout.write(k)")
    proc = subprocess.run(["docker", "exec", "socai2-litellm-1", "python", "-c", check],
                          capture_output=True, timeout=15, check=False)
    require(proc.returncode == 0 and 0 < len(proc.stdout) <= 4096, "provider_credential_unavailable")
    return proc.stdout + b"\n"


def timed(image, argv):
    private = BASE / "private/processing-handoff"
    args = ["docker", "run", "--rm", "-i", "--pull=never", "--network", "socai2_default", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--memory=2g", "--pids-limit=128",
            "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m,mode=1777", "--env-file", str(private / "runtime.env"),
            "-e", "AISOC_AIRGAP_ALLOWLIST=litellm,192.168.1.43", "--entrypoint", "python"]
    for src, dst in [(private / "job-key", "/run/processor/key"), (BASE / "certificates/socai2-ca.crt", "/run/certs/ca.crt"),
                     (ROOT / JOB, "/opt/processor/" + JOB), (ROOT / "plan.json", "/opt/r300/plan.json")]:
        args.extend(["--mount", f"type=bind,src={src},dst={dst},readonly"])
    args += [image, "-B", "/opt/processor/" + JOB, *argv]
    return subprocess.run(args, input=source_key(), capture_output=True, timeout=1360, check=False)


def command(job, image, card, name, argv, *, use_timed):
    folder = ROOT / "receipts" / card
    folder.mkdir(parents=True, exist_ok=True)
    save(folder / (name + "-input.json"), {"at": now(), "job": argv, "timed": use_timed})
    if use_timed:
        proc = timed(image, argv)
    else:
        proc = subprocess.run(["python3", str(job), "job", *argv], capture_output=True, timeout=150, check=False)
    for line in reversed(proc.stdout.decode("utf8", "replace").splitlines()):
        try:
            reply = json.loads(line)
        except ValueError:
            continue
        if isinstance(reply, dict):
            break
    else:
        reply = {"error": "missing_job_receipt"}
    receipt = {"at": now(), "exit": proc.returncode, "receipt": reply}
    save(folder / (name + "-output.json"), receipt)
    print(json.dumps({"card": card, "stage": name, "exit": proc.returncode,
                      "state": reply.get("state"), "error": reply.get("error")}), flush=True)
    return receipt


def run_card(launcher, image, row):
    key, ops = row["key"], row["operation_keys"]
    def run(name, argv, *, timed_route=True):
        return command(launcher, image, key, name, argv, use_timed=timed_route)

    for i, (aid, op) in enumerate(zip(row["alert_ids"], ops["alerts"], strict=True), 1):
        a = run("A" + str(i), ["alert", "--card", key, "--subject", aid, "--operation-key", op])
        if a["receipt"].get("state") not in {"completed", "failed"}:
            return "unconfirmed_alert"
    inc = run("I", ["incident", "--card", key, "--subject", row["incident_id"], "--operation-key", ops["incident"]])
    if inc["receipt"].get("state") not in {"completed", "failed"}:
        return "unconfirmed_incident"
    out = run("create", ["case-create", "--title", row["title"], "--incident-id", row["incident_id"],
                         "--operation-key", ops["create"]], timed_route=False)
    c = out["receipt"]
    if out["exit"] or c.get("case_id") != row["case_id"] or set(c.get("added_alert_ids", [])) != set(row["alert_ids"]):
        return "unconfirmed_create"
    scope = ["--subject", c["case_id"], "--scope-revision", str(c["scope_revision"])]
    prepared = run("prepare", ["case-prepare", *scope, "--operation-key", ops["prepare"]], timed_route=False)
    rid = prepared["receipt"].get("pending_run_id")
    if prepared["exit"] or not rid or str(UUID(rid)) != c["pending_run_id"]:
        return "unconfirmed_prepare"
    result = run("C", ["case-start", "--card", key, *scope, "--run-id", rid, "--operation-key", ops["start"]])
    return result["receipt"].get("state") or result["receipt"].get("error", "unconfirmed_case")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["preflight", "run"])
    args = parser.parse_args()
    require(Path(__file__).resolve().parent == ROOT and not ROOT.is_symlink(), "unexpected_job_location")
    data = (ROOT / "plan.json").read_bytes()
    require(hashlib.sha256(data).hexdigest() == PLAN_SHA, "plan_changed")
    plan = json.loads(data)
    launcher = BASE / "ops/processing.py"
    require(launcher.resolve() == RELEASE / "processing_host.py", "release_link_changed")
    spec = importlib.util.spec_from_file_location("installed_processing", launcher.resolve())
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    require(host.verified_release() == RELEASE_SHA, "release_changed")
    image = host.image(RELEASE_SHA)
    if args.action == "preflight":
        result = command(launcher, image, "_preflight-r2", "target", ["preflight", "--card", "m01"], use_timed=True)
        return result["exit"]
    require(json.loads((ROOT / "receipts/_preflight-r2/target-output.json").read_bytes())["exit"] == 0, "preflight_required")
    require((ROOT / "reset-authorized-receipt.json").is_file(), "reset_commit_required")
    with (ROOT / "dispatch.lock").open("a") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_NB | fcntl.LOCK_EX)
        save(ROOT / "dispatch.json", {"at": now(), "plan_sha256": PLAN_SHA, "max_model_calls": 19, "retry": 0,
                                      "per_call_timeout_seconds": 300, "cards": ["m01", "s02", "u03"]})
        results = {row["key"]: run_card(launcher, image, row) for row in plan["cases"]}
        save(ROOT / "finished.json", {"at": now(), "outcomes": results})
        print(json.dumps(results), flush=True)
    return 0


if __name__ == "__main__":
    os.umask(0o077)
    raise SystemExit(main())
