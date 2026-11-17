"""Requested 4177 static cleanup/sync; reuse archived atomic switch, no database writes."""
import argparse
import base64
import hashlib
import inspect
import json
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "docs/operations"))
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
        if retired and b'id="audit-retired-records"' not in index:
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
        receipt = {"status": "cleaned", "records_before": len(old_records), "records_after": len(request["records"]),
            "record_ids": [r["id"] for r in request["records"]], "case_ids": [r["scope_id"] for r in request["records"]],
            "files_retained": len(request["files"]) + 1, "archive": str(backup / "site-before"),
            "index_before_sha256": sha(old_index), "index_after_sha256": sha(index),
            "source_evidence_unchanged": True, "database_writes": 0, "model_calls": 0}
        (backup / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        return receipt


REMOTE = r'''
import base64,hashlib,json,subprocess,sys,urllib.request,re
request=json.load(sys.stdin); cfg=request['deployment']
before=json.loads(subprocess.check_output([cfg['docker'],'inspect',cfg['container']],text=True))[0]
assert before['Id']==cfg['expected_container_id'] and before['Image']==cfg['expected_image']
assert before['Config']['Labels']['com.docker.compose.project.config_files']==cfg['expected_compose']
assert any(m['Source']==cfg['expected_base_release'] and m['Destination']==cfg['source_mount'] for m in before['Mounts'])
exec(request['replace_source'])
receipt=replace_site(request)
paths=['index.html']
for record in request['records']:
    paths.extend([record['detail'],record['logs']['index']])
for name in dict.fromkeys(paths):
    with urllib.request.urlopen(cfg['base_url']+'/'+name,timeout=8) as response:
        raw=response.read(); assert response.status==200
        if name=='index.html':
            rows=json.loads(re.search(r'<script type="application/json" id="audit-records">(.*?)</script>',raw.decode(),re.DOTALL)[1])
            assert rows==request['records']
            assert hashlib.sha256(raw).hexdigest()==receipt['index_after_sha256']
        else: assert raw==base64.b64decode(request['files'][name])
after=json.loads(subprocess.check_output([cfg['docker'],'inspect',cfg['container']],text=True))[0]
assert before['Id']==after['Id'] and before['Mounts']==after['Mounts']
receipt.update(http_verified=len(set(paths)),container_unchanged=True,runtime_source_unchanged=True)
print(json.dumps(receipt))
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('clear', 'publish'))
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    cfg = json.loads((HERE / 'site-config.json').read_text())
    receipt_path = HERE / ('site-' + args.label + '-remote.json')
    assert not receipt_path.exists(), 'do_not_repeat_published_phase'
    output = ROOT / cfg['local_site']
    if args.phase == 'clear':
        request = {'records': [], 'files': {}, 'index': base64.b64encode(site.registry_html({}, HERE / 'empty-site', [])).decode()}
        request['target'] = {'site': str(output), 'backup': str(ROOT / cfg['local_backup'] / args.label),
            'expected_index_sha256': hashlib.sha256((output / 'index.html').read_bytes()).hexdigest()}
        local = replace_site(request)
        (HERE / ('site-' + args.label + '-local.json')).write_text(json.dumps(local, indent=2)+'\n')
    else:
        records = site.existing(output / 'index.html')
        assert records and all(r['batch'].startswith(cfg['batch']) for r in records.values())
        ordered = sorted(records.values(), key=lambda r:(site.timestamp(r['started_at']),r['batch'],r['key']),reverse=True)
        files = {}
        for p in output.rglob('*'):
            if not p.is_file() or p.relative_to(output) == Path('index.html') or p.relative_to(output).parts[0] not in {'cases','subjects','logs'}:
                continue
            raw = p.read_bytes()
            site.check_credentials(raw)
            files[str(p.relative_to(output))] = base64.b64encode(raw).decode()
        request = {'records': ordered, 'files': files, 'index': base64.b64encode((output/'index.html').read_bytes()).decode()}
    deployment = cfg['deployment']
    request.update(deployment=deployment,replace_source=inspect.getsource(replace_site),
        target={'site':deployment['site'],'backup':deployment['private']+'/'+args.label})
    intent = HERE / ('site-' + args.label + '-intent.json')
    assert not intent.exists(), 'inspect_existing_intent_before_retry'
    intent.write_text(json.dumps({'phase':args.phase,'record_ids':[r['id'] for r in request['records']],
        'target':request['target'],'database_writes':0},indent=2)+'\n')
    argv = [deployment['ssh_binary'],'-T','-o','BatchMode=yes','-o',f"ConnectTimeout={deployment['connect_timeout_seconds']}",
        deployment['ssh_target'],shlex.join([deployment['remote_python'],'-c',REMOTE])]
    result = subprocess.run(argv,input=json.dumps(request),capture_output=True,text=True,timeout=deployment['command_timeout_seconds'])
    if result.returncode:
        (HERE / ('site-' + args.label + '-failure.json')).write_text(json.dumps({'returncode':result.returncode,'stderr':result.stderr},indent=2)+'\n')
        raise RuntimeError('site_switch_failed_inspect_receipt')
    receipt = json.loads(result.stdout)
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__ == '__main__':
    main()

