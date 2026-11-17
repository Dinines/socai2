"""One requested static-site cleanup; archive old rendered sites, retain originals."""
import base64
import inspect
import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "docs/operations"))
import processing_audit_import as importer
import update_processing_audit as site


def replace_site(request):
    import base64
    import fcntl
    import hashlib
    import json
    import os
    import re
    import tempfile
    from pathlib import Path

    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    cfg = request["target"]
    output, backup = Path(cfg["site"]).resolve(), Path(cfg["backup"]).resolve()
    assert not backup.is_relative_to(output) and not output.is_relative_to(backup)
    assert output.is_dir() and not (backup / "site-before").exists()
    stage = output.with_name(output.name + "-latest-prepared")
    assert not stage.exists()
    lock_path = Path(tempfile.gettempdir()) / ("socai2-audit-" + sha(os.path.normcase(str(output)).encode()) + ".lock")
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        old_index = (output / "index.html").read_bytes()
        if cfg.get("expected_index_sha256"):
            assert sha(old_index) == cfg["expected_index_sha256"], "site changed since preparation"
        match = re.search(r'<script type="application/json" id="audit-records">(.*?)</script>', old_index.decode(), re.DOTALL)
        assert match
        old_records = json.loads(match[1])
        index = base64.b64decode(request["index"])
        retired = re.search(r'<script type="application/json" id="audit-retired-records">(.*?)</script>', old_index.decode(), re.DOTALL)
        if retired:
            # Preserve existing historical retirement metadata without displaying old records.
            index = index.replace(b"</body>", retired[0].encode() + b"</body>", 1)
        stat = output.stat()
        stage.mkdir()
        os.chmod(stage, 0o755)
        os.chown(stage, stat.st_uid, stat.st_gid)
        for name, encoded in {**request["files"], "index.html": base64.b64encode(index).decode()}.items():
            relative = Path(name)
            assert not relative.is_absolute() and ".." not in relative.parts
            assert name == "index.html" or relative.parts[0] in {"cases", "subjects", "logs"}
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = base64.b64decode(encoded)
            path.write_bytes(raw)
            os.chmod(path, 0o644)
            os.chown(path, stat.st_uid, stat.st_gid)
            assert path.read_bytes() == raw
        for directory in (p for p in stage.rglob("*") if p.is_dir()):
            os.chmod(directory, 0o755)
            os.chown(directory, stat.st_uid, stat.st_gid)
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        assert backup.stat().st_dev == output.stat().st_dev, "archive must share the site filesystem"
        os.replace(output, backup / "site-before")
        try:
            os.replace(stage, output)
        except BaseException:
            os.replace(backup / "site-before", output)
            raise
        receipt = {"status": "cleaned", "records_before": len(old_records), "records_after": 1,
            "retained_record_id": request["record"]["id"], "retained_case_id": request["record"]["scope_id"],
            "files_retained": len(request["files"]) + 1, "archive": str(backup / "site-before"),
            "index_before_sha256": sha(old_index), "index_after_sha256": sha(index),
            "source_evidence_unchanged": True, "database_writes": 0, "model_calls": 0}
        (backup / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        return receipt


REMOTE = r'''
import base64,hashlib,json,subprocess,sys,urllib.request,re
request=json.load(sys.stdin); cfg=request['deployment']
def inspect_container():
    return json.loads(subprocess.check_output([cfg['docker'],'inspect',cfg['container']],text=True))[0]
before=inspect_container()
assert before['Id']==cfg['expected_container_id'] and before['Image']==cfg['expected_image']
assert before['Config']['Labels']['com.docker.compose.project.config_files']==cfg['expected_compose']
assert any(m['Source']==cfg['expected_base_release'] and m['Destination']==cfg['source_mount'] for m in before['Mounts'])
exec(request['replace_source'])
receipt=replace_site(request)
for name in ['index.html',request['record']['detail'],request['record']['logs']['index']]:
    with urllib.request.urlopen(cfg['base_url']+'/'+name,timeout=8) as response:
        raw=response.read(); assert response.status==200
        if name=='index.html':
            rows=json.loads(re.search(r'<script type="application/json" id="audit-records">(.*?)</script>',raw.decode(),re.DOTALL)[1])
            assert rows==[request['record']]
            assert hashlib.sha256(raw).hexdigest()==receipt['index_after_sha256']
        else: assert raw==base64.b64decode(request['files'][name])
after=inspect_container()
assert before['Id']==after['Id'] and before['Mounts']==after['Mounts']
receipt.update(http_verified=3,container_unchanged=True,runtime_source_unchanged=True)
print(json.dumps(receipt))
'''


def main():
    config = json.loads((HERE / "workbench-config.json").read_text())
    prepared = [site.prepare(*case) for case in importer.folder_cases(ROOT / config["source"])]
    assert len(prepared) == 1
    record, files = prepared[0]
    assert record["id"] == config["keep_record_id"]
    # An empty staging directory omits links to old control/comparison pages.
    empty = HERE / "empty-render-root"
    assert not empty.exists()
    index = site.registry_html({record["id"]: record}, empty, [])
    for raw in [index, *files.values()]:
        site.check_credentials(raw)
    cfg = config["deployment"]
    payload = {"record": record, "files": {n: base64.b64encode(b).decode() for n, b in files.items()},
        "index": base64.b64encode(index).decode(), "replace_source": inspect.getsource(replace_site),
        "deployment": cfg, "target": {"site": cfg["site"], "backup": cfg["private"], "expected_index_sha256": cfg["index_sha256"]}}
    assert not (HERE / "workbench-remote.json").exists(), "Remote cleanup has already been recorded; do not repeat"
    argv = [cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={cfg['connect_timeout_seconds']}", cfg["ssh_target"],
        shlex.join([cfg["remote_python"], "-c", REMOTE])]
    result = subprocess.run(argv, input=json.dumps(payload).encode(), capture_output=True,
                            timeout=cfg["command_timeout_seconds"], check=False)
    if result.returncode:
        (HERE / "workbench-remote-error.txt").write_bytes(result.stderr)
        raise RuntimeError("Remote action stopped; inspect retained error and target receipt before any retry")
    receipt = json.loads(result.stdout)
    (HERE / "workbench-remote.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    payload["target"] = {"site": str(ROOT / config["local_site"]), "backup": str(ROOT / config["local_backup"]),
                         "expected_index_sha256": config["local_index_sha256"]}
    local = replace_site(payload)
    (HERE / "workbench-local.json").write_text(json.dumps(local, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"remote": receipt, "local": local}, ensure_ascii=False))


if __name__ == "__main__":
    main()
