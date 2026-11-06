"""Stage explicit source files in an immutable production release directory on 21."""
import argparse
import base64
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REMOTE = """
import base64, hashlib, json, os, pathlib, sys, tempfile
base = pathlib.Path('/opt/sting-aisoc-socai2/releases')
expected, label = sys.argv[1:]
body = sys.stdin.buffer.read()
assert base == base.resolve() and hashlib.sha256(body).hexdigest() == expected
target = base / ('production-' + label + '-' + expected[:16])
files = json.loads(body)
os.umask(0o022)
with tempfile.TemporaryDirectory(dir=base) as tmp:
    stage = pathlib.Path(tmp) / 'release'
    stage.mkdir()
    for name, encoded in files.items():
        relative = pathlib.PurePosixPath(name)
        assert not relative.is_absolute() and '..' not in relative.parts
        dest = stage / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(encoded, validate=True)
        dest.write_bytes(raw)
        if target.exists():
            prior = target / relative
            assert prior.resolve() == prior and prior.read_bytes() == raw
    if not target.exists():
        stage.rename(target)
print(target)
"""

WORKBENCH = [
    "serve_processing_workbench", "processing_workbench_source", "processing_workbench_retention",
    "capture_processing_case", "processing_audit_import", "update_processing_audit",
    "processing_audit_index", "processing_audit_detail", "processing_audit_flow", "processing_audit_logs",
    "processing_audit_subjects", "read_processing_audit_20261106", "export_processing_audit_batch",
    "refresh_three_case_replay_20261106",
]


def publish(label, files):
    data = {p: base64.b64encode((ROOT / p).read_text(encoding="utf-8").encode()).decode() for p in files}
    body = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(body).hexdigest()
    cmd = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8",
           "sting-infra21", shlex.join(["python3", "-c", REMOTE, digest, label])]
    subprocess.run(cmd, input=body, check=True, timeout=90)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=["workbench", "processing"])
    component = parser.parse_args().component
    if component == "workbench":
        files = [f"docs/operations/{name}.py" for name in WORKBENCH]
        files += [f"deploy/local-investigation/{name}.py"
                  for name in ("flow_export", "flow_fixture", "config", "backend_profile")]
        files.append("deploy/aisoc21/install_production_workbench.py")
    else:
        files = ["deploy/aisoc21/" + name for name in
                 ("production_processing.py", "processing_job.py", "production_ingress.py",
                  "production_projection.py", "compose.production-projection.yml", "compose.projection-activate.yml")]
    publish(component, files)
