"""Transport/dispatch only the sealed repair-k5 packet; no deployment operation.

Model phases require review receipts on 21. Closed prior batches are unreachable.
Credentials and credential-derived hashes are never returned by this wrapper.
"""
import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/operations/evidence/investigation-repair-20261105/repair-k5"
REMOTE = "/opt/sting-aisoc-socai2/evidence/next-repair-k5-20261105"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8", "sting-infra21"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["upload", "upload-review", "preflight", "backup-125", "apply-125",
        "ingest", "first", "second", "export"])
    parser.add_argument("--backend", choices=["deepseek", "small"])
    parser.add_argument("--review", type=Path)
    parser.add_argument("--review-kind", choices=["core", "semantic", "page-human"])
    parser.add_argument("--human-source", choices=["page", "driver"], default="page")
    args = parser.parse_args()
    if args.phase in {"first", "second", "export", "preflight"} and not args.backend:
        parser.error("this phase requires an explicit --backend")
    manifest = json.loads((PACKET / "manifest.json").read_text())
    for name, digest in manifest.items():
        assert Path(name).name == name and hashlib.sha256((PACKET / name).read_bytes()).hexdigest() == digest
    body = None
    if args.phase == "upload":
        files = {name: (PACKET / name).read_text() for name in [*manifest, "manifest.json"]}
        code = """import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); data=json.load(sys.stdin)
m=json.loads(data['manifest.json'])
assert set(data)==set(m)|{'manifest.json'}
assert all(pathlib.Path(n).name==n and hashlib.sha256(data[n].encode()).hexdigest()==v for n,v in m.items())
p.mkdir(mode=0o700,exist_ok=False)
for n,v in data.items():
 f=p/n; f.write_text(v); f.chmod(0o600)
print(json.dumps({'uploaded':len(data),'credentials_exported':False}))"""
        command, body = ["python3", "-c", code, REMOTE], json.dumps(files).encode()
    elif args.phase == "upload-review":
        if args.review is None:
            parser.error("upload-review requires --review")
        approval = json.loads(args.review.read_text())
        assert approval.get("approved") is True and approval.get("reviewer") == "root"
        assert approval.get("plan_sha256") == hashlib.sha256((PACKET / "plan.json").read_bytes()).hexdigest()
        review_kind = args.review_kind or ("semantic" if args.backend else "core")
        if review_kind != "core" and not args.backend:
            parser.error("a card review requires --backend")
        target = args.backend + "/" + review_kind + "-review.json" if review_kind != "core" else "core-review.json"
        code = """import json,pathlib,sys
p=pathlib.Path(sys.argv[1])/sys.argv[2]; assert p.parent.is_dir()
with p.open('x') as f: json.dump(json.load(sys.stdin),f,indent=2)
p.chmod(0o600); print(json.dumps({'review_uploaded':sys.argv[2]}))"""
        command, body = ["python3", "-c", code, REMOTE, target], json.dumps(approval).encode()
    elif args.phase in {"backup-125", "apply-125"}:
        command = ["python3", REMOTE + "/repair_migration_remote_20261105.py", args.phase.removesuffix("-125")]
    else:
        command = ["python3", REMOTE + "/repair_acceptance_remote_20261105.py", args.phase]
        if args.backend:
            command += ["--backend", args.backend]
        if args.phase == "second":
            command += ["--human-source", args.human_source]
    destination = PACKET / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ-") + args.phase + ("-" + args.backend if args.backend else ""))
    destination.mkdir(exist_ok=False)
    receipt = {"phase": args.phase, "backend": args.backend, "credentials_exported": False,
        "dispatched_at": datetime.now(UTC).isoformat(), "records": []}
    try:
        result = subprocess.run(SSH + [shlex.join(command)], input=body, capture_output=True, timeout=800, check=False)
        receipt["exit_code"] = result.returncode
        for line in result.stdout.decode().splitlines():
            if not line.startswith("{"):
                continue
            record = json.loads(line)
            for name, value in record.pop("export", {}).items():
                assert Path(name).name == name and name.endswith(".json") and "private" not in name
                (destination / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
            receipt["records"].append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
        if result.returncode:
            receipt["failure"] = "Remote phase failed. Raw stderr withheld; inspect immutable phase intent before any further action."
        return result.returncode
    except (OSError, subprocess.TimeoutExpired):
        receipt["failure"] = "Transport failed or timed out; remote state unknown. Do not retry a dispatched model phase."
        return 1
    finally:
        (destination / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        print(destination / "receipt.json", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
