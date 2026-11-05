"""Load the user-provided token into a separate remote profile over SSH stdin."""
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
    args = parser.parse_args()
    assert re.fullmatch(r"next-20261104-[a-z0-9-]+", args.release)
    token = (ROOT/"dsapi.txt").read_text("utf-8-sig").strip()
    if not token or any(c.isspace() for c in token):
        raise ValueError("credential file must contain one token")
    target = "/opt/sting-aisoc-socai2/releases/" + args.release + "/next_service_remote.py"
    result = subprocess.run(SSH + [DEST, shlex.join(["python3", target, "configure-deepseek"])],
        input=json.dumps({"token": token}).encode(), capture_output=True, timeout=45, check=False)
    # Only explicitly structured, credential-free completion output is retained.
    records = [json.loads(line) for line in result.stdout.decode().splitlines() if line.startswith("{")]
    if token in json.dumps(records):
        raise ValueError("credential appeared in unexpected response; output suppressed")
    receipt = {"release": args.release, "exit_code": result.returncode, "records": records,
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(), "credentials_exported": False}
    directory = ROOT/"docs/operations/evidence/socai2-next-service-20261104"/(datetime.now(UTC).strftime("%Y%m%dT%H%M%S")+"-deepseek-config")
    directory.mkdir(parents=True, exist_ok=False)
    (directory/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n", "utf-8")
    print(json.dumps(receipt))
    print(str(directory/"receipt.json"))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
