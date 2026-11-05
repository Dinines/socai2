"""Run one fixed independent-service phase and retain sanitized output."""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs/operations"))
from verify_socai2_store_20261103 import DEST, SSH


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("release")
    parser.add_argument("kind", choices=["service", "acceptance"])
    parser.add_argument("phase", choices=["inspect", "build", "start", "verify", "seed", "reuse", "auth", "stages", "first", "second", "export"])
    parser.add_argument("--batch", choices=["r1", "r2", "r3", "r4", "r5", "r6", "r7"], default="r1")
    parser.add_argument("--model-profile", choices=["original", "deepseek"], default="original")
    args = parser.parse_args()
    assert re.fullmatch(r"next-20261104-[a-z0-9-]+", args.release)
    assert args.phase in ({"inspect", "build", "start", "verify"} if args.kind == "service" else {"seed", "reuse", "auth", "stages", "first", "second", "export"})
    script = "next_service_remote.py" if args.kind == "service" else "next_acceptance_remote.py"
    target = "/opt/sting-aisoc-socai2/releases/" + args.release + "/" + script
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    suffix = ("-" + args.batch) if args.kind == "acceptance" else ""
    directory = ROOT / "docs/operations/evidence" / ("socai2-next-" + args.kind + "-20261104") / (stamp + suffix + "-" + args.phase)
    directory.mkdir(parents=True, exist_ok=False)
    command = ["python3", target, args.phase]
    if args.kind == "acceptance":
        command += ["--batch", args.batch]
    elif args.model_profile != "original":
        command += ["--model-profile", args.model_profile]
    result = subprocess.run(SSH + [DEST, shlex.join(command)], capture_output=True, timeout=450, check=False)
    records = []
    for line in result.stdout.decode("utf-8").splitlines():
        if line.startswith("{"):
            item = json.loads(line)
            if "export" in item:
                for name, content in item.pop("export").items():
                    assert Path(name).name == name and name.endswith(".json")
                    (directory / name).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", "utf-8")
                item["export_saved"] = True
            records.append(item)
            print(json.dumps(item, ensure_ascii=False), flush=True)
    receipt = {"release": args.release, "kind": args.kind, "phase": args.phase, "exit_code": result.returncode,
        "batch": args.batch if args.kind == "acceptance" else None,
        "records": records, "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(), "credentials_exported": False}
    (directory / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(str(directory / "receipt.json"), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
