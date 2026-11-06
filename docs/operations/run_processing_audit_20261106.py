"""Run the frozen three-case functional audit on 21 using its installed r3 job."""
import datetime
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

BATCH = "ie-audit-20261106-a1"
HOME_DIR = Path("/opt/sting-aisoc-socai2")
ROOT = HOME_DIR / "evidence" / BATCH
LAUNCHER = HOME_DIR / "ops/processing.py"
TARGET = HOME_DIR / "releases/processing-20261106-r3/processing_host.py"
TENANT = "6aff0ef7-c670-5a84-a2ee-83d73e25b964"
RELEASE_SHA = "268df0811dce6c27cadd61f77cda97835201e24d82a6cf6e9c06c805e7541aa5"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def save(path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def stage(folder, name, args):
    # Save an exclusive intent BEFORE dispatch. An interrupted request is never
    # silently replayed. The scoped readback can still recover already committed rows.
    save(folder / (name + "-input.json"), {"at": now(), "job": args})
    p = subprocess.run(["python3", str(LAUNCHER), "job", *args], capture_output=True, text=True, check=False)
    try:
        result = json.loads(p.stdout)
    except (ValueError, TypeError):
        result = {"error": "missing_processing_receipt"}
    answer = {"at": now(), "exit": p.returncode, "receipt": result}
    save(folder / (name + "-output.json"), answer)
    print(json.dumps({"case": folder.name, "stage": name, **answer}, ensure_ascii=False), flush=True)
    return answer


def may_continue(out):
    return out["exit"] in {0, 2} and out["receipt"].get("state") in {"succeeded", "completed", "failed", "partial"}


def case(row):
    folder = ROOT / row["key"]
    folder.mkdir(mode=0o700)
    ids, op = row["alert_ids"], row["operation_keys"]
    for i, (subject, key) in enumerate(zip(ids, op["alerts"], strict=True)):
        a = stage(folder, f"A{i+1}", ["alert", "--subject", subject, "--operation-key", key])
        if not may_continue(a):
            return "stopped_after_alert"
    i = stage(folder, "I", ["incident", "--subject", row["incident_id"], "--operation-key", op["incident"]])
    if not may_continue(i):
        return "stopped_after_incident"
    created = stage(folder, "create", ["case-create", "--title", row["title"], "--incident-id", row["incident_id"],
                                       "--operation-key", op["create"]])
    c = created["receipt"]
    if created["exit"] or c.get("case_id") != row["case_id"] or set(c.get("added_alert_ids", [])) != set(ids):
        return "case_creation_unconfirmed"
    scope = ["--subject", c["case_id"], "--scope-revision", str(c["scope_revision"])]
    prepared = stage(folder, "prepare", ["case-prepare", *scope, "--operation-key", op["prepare"]])
    if prepared["exit"] or prepared["receipt"].get("pending_run_id") != c["pending_run_id"]:
        return "case_preparation_unconfirmed"
    started = stage(folder, "C", ["case-start", *scope, "--run-id", c["pending_run_id"], "--operation-key", op["start"],
                                  "--window-start", row["window_start"], "--window-end", row["window_end"]])
    return "case_" + str(started["receipt"].get("state", "unconfirmed"))


def main(plan_hash):
    require(ROOT == Path.cwd().resolve() and LAUNCHER.resolve() == TARGET, "target_mismatch")
    require(hashlib.sha256((TARGET.parent / "manifest.json").read_bytes()).hexdigest() == RELEASE_SHA, "release_changed")
    source = (ROOT / "plan.json").read_bytes()
    require(hashlib.sha256(source).hexdigest() == plan_hash, "plan_changed")
    plan = json.loads(source)
    require(plan["batch"] == BATCH and plan["tenant_id"] == TENANT, "unexpected_batch")
    require([(r["key"], len(r["alert_ids"])) for r in plan["cases"]] == [("m01", 1), ("s02", 2), ("u03", 1)],
            "unexpected_cases")
    keys = []
    for r in plan["cases"]:
        op = r["operation_keys"]
        require(len(r["alert_ids"]) == len(op["alerts"]), "operation_count_mismatch")
        keys.extend([*r["alert_ids"], r["incident_id"], r["case_id"], *op["alerts"], op["incident"], op["create"],
                     op["prepare"], op["start"]])
    require(len(set(keys)) == len(keys) and all(str(UUID(x)) == x for x in keys), "duplicate_or_invalid_identity")
    with (ROOT / "audit.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(ROOT / "dispatch.json", {"at": now(), "batch": BATCH, "plan_sha256": plan_hash,
             "limits": {"alert_model": 4, "incident_model": 3, "case_model": 12, "total_model_max": 19},
             "policy": "sequential; one dispatch per operation; stop case on unknown or unconfirmed receipt"})
        outcomes = {}
        for r in plan["cases"]:
            outcomes[r["key"]] = case(r)
        save(ROOT / "finished.json", {"at": now(), "outcomes": outcomes})
        print(json.dumps(outcomes), flush=True)


if __name__ == "__main__":
    os.umask(0o077)
    main(sys.argv[1])
