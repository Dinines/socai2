"""Run the already checked HTTP reader on 21 against one actual saved snapshot."""

import argparse
import importlib.util
import json
from pathlib import Path

E = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("batch_invoke", E / "invoke.py")
invoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invoke)

CODE = r'''
import hashlib,json,sys,types
from pathlib import Path
x=json.load(sys.stdin);p=x['profile'];folder=Path(p['remote_directory']);snapshot=folder/'out'/(x['label']+'-snapshot.json')
with snapshot.open('x') as f:json.dump(x['snapshot'],f,ensure_ascii=False,indent=2)
module=types.ModuleType('batch_http_reader');exec(compile(x['reader'],'batch_http_reader.py','exec'),module.__dict__)
output=folder/'out'/x['label'];report=module.read(snapshot,p,output)
if x['first_gate']:
 assert len(report['case_ids'])==2 and len(report['terminal_run_ids'])==2 and report['saved_readback_complete']
 report['prepared_manifest_sha256']=hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()
 with (folder/'out/first-round-gate.json').open('x') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'report':report,'http':json.loads((output/'http.json').read_text())},ensure_ascii=False))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--first-gate", action="store_true")
    args = parser.parse_args()
    assert args.label.replace("-", "").isalnum()
    p = json.loads((E / "batch/profile.json").read_text())
    invoke.require_ready(p)
    readback = json.loads((E / "readback-config.json").read_text())
    p["timeouts"]["remote_seconds"] = readback["remote_seconds"]
    snapshot = json.loads(args.snapshot.read_text())
    if "value" in snapshot:
        assert snapshot["state"] == "returned" and snapshot["exit"] == 0
        snapshot = snapshot["value"]
    assert snapshot["source"] == "real_postgres_readonly_snapshot"
    assert snapshot["batch_id"] == p["batch_id"]
    payload = {
        "profile": p, "snapshot": snapshot, "label": args.label,
        "first_gate": args.first_gate, "reader": (E / "read-http.py").read_text(),
    }
    result = invoke.remote(p, ["python3", "-c", CODE], json.dumps(payload), args.label)
    print(json.dumps(result["report"], ensure_ascii=False))


if __name__ == "__main__":
    main()
