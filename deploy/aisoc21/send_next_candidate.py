"""Upload and verify a credential-free candidate; optional isolated bootstrap."""
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
sys.path.insert(0, str(ROOT/"docs/operations"))
from verify_socai2_store_20261103 import DEST, SSH

REMOTE = r"""import hashlib,io,json,pathlib,sys,tarfile
sha,destination=sys.argv[1:]
body=sys.stdin.buffer.read(64*1024*1024+1)
assert len(body)<=64*1024*1024 and hashlib.sha256(body).hexdigest()==sha
root=pathlib.Path(destination)
assert root.parent==pathlib.Path('/opt/sting-aisoc-socai2/releases') and root.name.startswith('next-20261104-')
with tarfile.open(fileobj=io.BytesIO(body)) as archive:
 members=archive.getmembers()
 assert len(members)==len({m.name for m in members})
 for m in members:
  p=pathlib.PurePosixPath(m.name)
  assert m.isfile() and not p.is_absolute() and '..' not in p.parts and '\\' not in m.name
 manifest=json.load(archive.extractfile('manifest.json'))
 assert {m.name for m in members}==set(manifest['files'])|{'manifest.json'}
 for name,entry in manifest['files'].items():
  data=archive.extractfile(name).read()
  assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
 root.mkdir(parents=True,exist_ok=False)
 for m in members:
  path=root/m.name;path.parent.mkdir(parents=True,exist_ok=True)
  path.write_bytes(archive.extractfile(m).read());path.chmod(0o644)
print(json.dumps({'uploaded':str(root),'archive_sha256':sha,'files':len(members),'credentials_exported':False}))
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("release")
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"next-20261104-[a-z0-9-]+", args.release):
        raise ValueError("invalid next-service release name")
    source = args.candidate.resolve()
    if not source.is_relative_to(ROOT/".local/releases"):
        raise ValueError("candidate outside local releases")
    data = (source/"candidate.tar").read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    dest = "/opt/sting-aisoc-socai2/releases/"+args.release
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    evidence = ROOT/"docs/operations/evidence/socai2-next-service-20261104"/stamp
    evidence.mkdir(parents=True, exist_ok=False)
    receipt = {"candidate": str(source.relative_to(ROOT)), "release": dest, "archive_sha256":sha,
        "bootstrap_requested":args.bootstrap, "old_business_data_exported":False, "steps":[]}
    try:
        commands = [("upload", ["python3","-c",REMOTE,sha,dest],data)]
        if args.bootstrap:
            commands.append(("bootstrap",["python3",dest+"/next_service_remote.py","bootstrap"],None))
        for action,command,body in commands:
            result = subprocess.run(SSH+[DEST,shlex.join(command)],input=body,capture_output=True,timeout=180,check=False)
            # stdout is restricted to non-secret structured phase/receipt output.
            records = [json.loads(line) for line in result.stdout.decode().splitlines() if line.strip().startswith("{")]
            step = {"action":action,"exit_code":result.returncode,"records":records}
            if result.returncode:
                step["failure"] = "remote step failed; raw stderr withheld because connection diagnostics may contain credentials"
                step["stderr_sha256"] = hashlib.sha256(result.stderr).hexdigest()
            receipt["steps"].append(step)
            print(json.dumps(step),flush=True)
            if result.returncode:
                return 1
    except (OSError,subprocess.TimeoutExpired):
        receipt["transport_failure"] = "remote operation did not return; inspect remote state before retrying"
        return 1
    finally:
        (evidence/"receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n","utf-8")
        print(str(evidence/"receipt.json"),flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
