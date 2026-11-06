"""Run one frozen 21 matrix phase using the original pilot's verified dependencies."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

EVIDENCE = Path("/opt/sting-aisoc-socai2/evidence")
ORIGINAL = EVIDENCE / "deployed-pilot-20261106-01"
PLAN = {
    "02": "f48aff612dd3c398d972054eeb794de5feedfd6b19e8aba7e981676d4a8526fe",
    "03": "1995c5afdf8617f8eed793c9f3004681326f3d4f560e541301ab18ae9a521130",
    "04": "16c40d5dad07856ec86bd88e08a2a0e22888a03c9d5a9ff98731995bf80c1e42",
}
HELPERS = {
    "deployed_pilot_case.py": "b7c1a1b230b8f572fd46e5b84ff711f8f4b4435da67e1128643ddb8073632588",
    "deployed_pilot_host.py": "c089c58f38b01e382d5ec51059e4b027cd82ebb48c4c91133c6cf2675f251664",
    "flow_export.py": "320e6d19dd384ee66b013629e80fc875fb6ea8fdb48c796d7b997c0519b65e0e",
    "validate_flow.py": "1b54bd804239fea6eb234cada9d5c7e723a65923e9e3dfcb20f779dd06b1f847",
    "history-index.json": "dca4db844c946b23e469eaf4c5e6cb9670966aa26776884d9a6e8df61c91c9c5",
    "analysis/first-outcome.json": "55f8fc8e7c0992df65aeb99a98b6ce1a1cd2dab7b35209df581847d57fa0d073",
}
HISTORY = "423d20d4c60b45ad9387fce4fa5523cfc7f3cd95a6c497541f2f813964fa6d11"
TENANT = "fbe17036-51e4-5d28-a3de-8c93d1f8d634"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def pg(database, sql):
    args = ["docker", "exec", "-i", "spirithub-postgres-1", "psql", "-XAtq", "-v", "ON_ERROR_STOP=1",
            "-U", "spirithub", "-d", database]
    return subprocess.run(args, input=sql.encode(), capture_output=True, check=True).stdout.decode().strip()


def other_attempts(card):
    counts = {}
    for other in PLAN:
        if other == card:
            continue
        database = "socai2_pilot_20261106_" + other
        if pg("postgres", f"SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname='{database}')") == "f":
            counts[other] = 0
            continue
        if pg(database, "SELECT coalesce(to_regclass('socai2.run_steps')::text,'absent')") == "absent":
            counts[other] = 0
            continue
        sql = f"""SELECT count(*) FROM socai2.run_steps WHERE tenant_id='{TENANT}' AND kind='model'
            AND state NOT IN ('planned','skipped')"""
        counts[other] = int(pg(database, sql))
        require(counts[other] <= (11 if other == "04" else 7), "sibling_database_exceeds_cap")
    return counts


def run(card, phase, lock):
    root = EVIDENCE / ("deployed-pilot-20261106-" + card)
    require(Path(__file__).resolve().parent == root and __debug__, "wrong_matrix_entry")
    for name, sha in HELPERS.items():
        require(digest((ORIGINAL / name).read_bytes()) == sha, "pilot_dependency_changed:" + name)
    sys.path.insert(0, str(ORIGINAL))
    import deployed_pilot_host as pilot

    fcntl.flock(lock, fcntl.LOCK_EX)
    require(digest((root / "plan.json").read_bytes()) == PLAN[card], "plan_changed")
    require(digest((root / "history-index.json").read_bytes()) == HISTORY, "prior_ledger_changed")
    # Reuse the original credential and URL checks in a process dedicated to this database.
    pilot.ROOT, pilot.OUTPUT = root, root / "analysis"
    pilot.DB, pilot.ROLE = "socai2_pilot_20261106_" + card, "socai2_pilot_api_20261106_" + card
    inventory = json.loads((ORIGINAL / "source-manifest.json").read_bytes())
    canonical = json.dumps(inventory, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    require(digest(canonical) == json.loads((root / "plan.json").read_bytes())["transferred_source_manifest_sha256"],
            "wrong_source_manifest")
    source = ORIGINAL / "source"
    for name, expected in inventory.items():
        f = source / name
        require(f.resolve().is_relative_to(source) and digest(f.read_bytes()) == expected, "source_changed")
    pilot.stage_files(phase)
    info = json.loads(subprocess.run(["docker","inspect",pilot.API], capture_output=True,check=True).stdout)[0]
    require(info["State"]["Running"] and info["Image"] == "sha256:c78b01862896f966cf8f6901ad21baa941f35ebe6ec83a5894d17c97575a5795"
            and "socai2_default" in info["NetworkSettings"]["Networks"] and
            all(m["Destination"] == "/run/certs/ca.crt" and not m["RW"] for m in info["Mounts"]), "carrier_changed")
    env = pilot.environment(info)
    others = other_attempts(card)
    env.update(MATRIX_CARD=card, MATRIX_PLAN_SHA=PLAN[card], MATRIX_OTHER_COUNTS=json.dumps(others))
    args = ["docker","run","--rm","--pull=never","--network","socai2_default","--volumes-from",pilot.API+":ro",
            "--user","0:0","--cap-drop","ALL","--security-opt","no-new-privileges","--read-only","--tmpfs","/tmp",
            "-v",str(pilot.OUTPUT)+":/pilot:rw", "-v",str(source)+":/pilot/source:ro",
            "-v",str(root/"deployed_matrix_case.py")+":/matrix-case.py:ro",
            "-w","/pilot/source/services/api","--entrypoint","python"]
    for name in ("deployed_pilot_case.py","flow_export.py","validate_flow.py"):
        args += ["-v",str(ORIGINAL/name)+":/pilotlib/"+name+":ro"]
    for key in env:
        args += ["-e",key]
    p = subprocess.run(args+[info["Image"],"-B","/matrix-case.py",phase], env={**os.environ,**env}, capture_output=True)
    matches = [s for s in p.stdout.decode(errors="replace").splitlines() if s.startswith("MATRIX_RESULT=")]
    require(len(matches)==1,"container_missing_receipt")
    print(matches[0],flush=True)
    return p.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("card",choices=PLAN)
    parser.add_argument("phase",choices=["identity","preflight","first","second","export"])
    parser.add_argument("--dispatch-once",action="store_true")
    args = parser.parse_args()
    if (args.phase in {"first","second"}) != args.dispatch_once or (args.phase=="second" and args.card!="04"):
        parser.error("only the fixed model phases can dispatch")
    try:
        with contextlib.ExitStack() as stack:
            lock = stack.enter_context((EVIDENCE / "deployed-matrix-20261106.lock").open("a"))
            sys.exit(run(args.card,args.phase,lock))
    except Exception as exc:
        print(json.dumps({"error":str(exc) if type(exc) is RuntimeError else type(exc).__name__}))
        sys.exit(1)
