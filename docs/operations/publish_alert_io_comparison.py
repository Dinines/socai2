"""Publish immutable model-boundary comparisons without creating business Runs."""
import argparse
import base64
import hashlib
import html
import json
import re
import shlex
import subprocess
from pathlib import Path

import update_processing_audit as site
from read_processing_audit_20261106 import check_credentials

ROOT = Path(__file__).resolve().parents[2]


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def read(path):
    return json.loads(path.read_bytes())


def prepare(config):
    evidence = ROOT / config["evidence"]
    plan = read(evidence / "plan-and-packets.json")
    reviewed = read(evidence / "parsed-results.json")["results"]
    summary = read(evidence / "summary.json")
    intent = read(evidence / "batch-intent.json")
    if hashlib.sha256((evidence / "plan-and-packets.json").read_bytes()).hexdigest() != intent["plan_sha256"]:
        raise ValueError("frozen plan differs from dispatch intent")
    batch = plan["batch"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", batch):
        raise ValueError("invalid batch name")
    index = {row["id"]: row for row in reviewed}
    if set(index) != {cell["id"] for cell in plan["cells"]}:
        raise ValueError("comparison review is incomplete")
    files, samples = {}, []
    for subject in plan["samples"]:
        sample = {"id": subject["id"], "kind": subject["kind"], **config["samples"][subject["id"]], "cells": []}
        for cell in (c for c in plan["cells"] if c["sample"] == subject["id"]):
            packet = next(v for v in subject["variants"] if v["id"] == cell["variant"])
            raw = read(evidence / "calls" / (cell["id"] + "-result.json"))
            result = index[cell["id"]]
            body = packet["body"]
            content = raw.get("raw", {}).get("choices", [{}])[0].get("message", {}).get("content")
            if result.get("answer") is not None and json.loads(content) != result["answer"]:
                raise ValueError("parsed answer differs from original response")
            row = {**result, "content": content, "user_bytes": packet["user_bytes"],
                   "user": next(m["content"] for m in body["messages"] if m["role"] == "user"),
                   "system": "\n".join(m["content"] for m in body["messages"] if m["role"] == "system"),
                   "response_format": body["response_format"]}
            for key, value in (("request", body), ("response", raw), ("parsed", result)):
                relative = f"records/{cell['id']}-{key}.json"
                row[key + "_path"] = relative
                files[f"comparisons/{batch}/{relative}"] = encode(value)
            sample["cells"].append(row)
        samples.append(sample)
    payload = {"batch": batch, "samples": samples, "variants": config["variants"], "metrics": summary["metrics"],
               "presentation": config.get("presentation", {})}
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    page = (ROOT / config["template"]).read_text().replace("__COMPARISON_DATA__", encoded)
    files[f"comparisons/{batch}/index.html"] = page.encode()
    for data in files.values():
        check_credentials(data)
    record = {"batch": batch, "path": f"{batch}/index.html", "samples": len(samples), "calls": len(reviewed),
              "title": config.get("title", "告警三组输入输出对比"), "status": config.get("status", "质量尚未通过")}
    manifest = {"batch": batch, "source_plan_sha256": intent["plan_sha256"], "business_runs_created": 0,
                "files": {name: site.sha(value) for name, value in files.items()}}
    files[f"comparisons/{batch}/manifest.json"] = encode(manifest)
    return record, files


def listing(records):
    links = "".join(f'<li><a href="{html.escape(r["path"], quote=True)}">{html.escape(r["title"])}'
                    f' · {html.escape(r["batch"])}</a><p>{r["samples"]} 个样例 / {r["calls"]} 次调用'
                    f' · {html.escape(r["status"])}</p></li>' for r in records)
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>模型输入输出测试 · 调查工作台</title>'
            '<style>body{font:16px/1.7 system-ui,sans-serif;background:#f3f5f4;color:#1c322f;'
            'max-width:1000px;margin:40px auto;padding:20px}a{color:#176459}li{background:white;'
            'padding:20px;margin:16px 0;border:1px solid #d6dfd9;border-radius:8px}ul{list-style:none;padding:0}'
            'p{font-size:14px;color:#53695f}</style><a href="../index.html">返回调查工作台</a>'
            '<h1>模型输入输出测试</h1><p>查看各阶段实际输入、模型原答、校验和程序装配结果。'
            '这里展示已保存的测试记录，不触发模型调用。</p><ul>' + links + '</ul></html>').encode()


def archive_batches(output, archive, batches):
    """Move only explicitly named static batches outside the served site, with hashes."""
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if archive == output or output in archive.parents:
        raise ValueError("archive must be outside the public site")
    archive.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ("registry.json", "index.html"):
        source, backup = output / "comparisons" / name, archive / ("before-" + name)
        if source.exists() and not backup.exists():
            with backup.open("xb") as stream:
                stream.write(source.read_bytes())
    result = []
    for batch in batches:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", batch):
            raise ValueError("invalid retired batch name")
        source, target = output / "comparisons" / batch, archive / batch
        if source.is_symlink() or target.is_symlink():
            raise ValueError("archive paths must not be symlinks")
        existing = source if source.exists() else target
        if not existing.is_dir():
            raise ValueError("retired batch is missing: " + batch)
        hashes = {str(p.relative_to(existing)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(existing.rglob("*")) if p.is_file()}
        if source.exists():
            if target.exists():
                raise ValueError("archive target already exists: " + batch)
            source.rename(target)
        assert all(hashlib.sha256((target / n).read_bytes()).hexdigest() == h for n, h in hashes.items())
        result.append({"batch": batch, "archive": str(target), "files": len(hashes), "sha256": hashes})
    return result


def publish_local(config, record, files):
    output = ROOT / config["local_site"]
    with site.publishing(output):
        registry = output / "comparisons/registry.json"
        entries = read(registry) if registry.exists() else []
        retired = config.get("retire_batches", [])
        if record["batch"] in retired:
            raise ValueError("cannot retire the current batch")
        archived = archive_batches(output, ROOT / config["local_archive"], retired) if retired else []
        entries = [record, *(r for r in entries if r["batch"] not in {record["batch"], *retired})]
        site.publish_files(output, {**files, "comparisons/registry.json": encode(entries),
                                    "comparisons/index.html": listing(entries)})
        index = output / "index.html"
        records = site.existing(index)
        if records is None:
            raise ValueError("workbench index must be migrated first")
        site.atomic_save(index, site.registry_html(records, output, site.retired_records(index)))
    return {"archived": archived, "visible_batches": [r["batch"] for r in entries], "case_records": len(records)}


REMOTE = r'''
import base64,hashlib,json,os,pathlib,re,subprocess,sys,time,urllib.request
request=json.load(sys.stdin); cfg=request['deployment']; docker=cfg['docker']
def command(args):
 p=subprocess.run(args,text=True,capture_output=True,timeout=60)
 if p.returncode: raise RuntimeError('workbench_command_failed_'+str(p.returncode))
 return p.stdout
def inspect(): return json.loads(command([docker,'inspect',cfg['container']]))[0]
def other_containers():
 return command([docker,'ps','--format','{{.Names}} {{.ID}}']).splitlines()
def atomic(path,raw,mode=0o644,owner=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_name(path.name+'.comparison-next')
 with temp.open('wb') as f: f.write(raw)
 os.chmod(temp,mode)
 if owner: os.chown(temp,*owner)
 temp.replace(path)
def records(path):
 text=path.read_text(); m=re.search(r'<script type="application/json" id="audit-records">(.*?)</script>',text,re.S)
 assert m,'missing_workbench_registry'
 return json.loads(m[1])
before=inspect(); before_others=other_containers()
assert before['Image']==cfg['expected_image'],'unexpected_image'
assert any(m['Source']==cfg['expected_base_release'] and m['Destination']==cfg['source_mount'] for m in before['Mounts']),'unexpected_base_release'
private=pathlib.Path(cfg['private']); release=pathlib.Path(cfg['release']); output=pathlib.Path(cfg['site'])
assert all(p.resolve()==p for p in (private,release,output)),'unexpected_path'
current_compose=before['Config']['Labels']['com.docker.compose.project.config_files']
next_compose=private/'workbench-after.json'
assert current_compose in (cfg['expected_compose'],str(next_compose)),'unexpected_compose'
compose=json.loads(pathlib.Path(current_compose).read_text())
assert set(compose['services'])=={cfg['service']},'unexpected_services'
old_records=records(output/'index.html')
old_ids={r['id'] for r in old_records}
old_index_sha=hashlib.sha256((output/'index.html').read_bytes()).hexdigest()
private.mkdir(parents=True,exist_ok=True,mode=0o700)
if not (private/'workbench-before.json').exists():
 atomic(private/'workbench-before.json',pathlib.Path(current_compose).read_bytes(),0o600)
 atomic(private/'index-before.html',(output/'index.html').read_bytes(),0o600)
release.mkdir(parents=True,exist_ok=True)
for name,value in request['sources'].items():
 assert name in cfg['source_files']
 raw=base64.b64decode(value); dest=release/name
 if dest.exists(): assert dest.read_bytes()==raw,'immutable_source_mismatch'
 else: atomic(dest,raw)
for name,value in request['files'].items():
 relative=pathlib.PurePosixPath(name)
 assert relative.parts[0]=='comparisons' and '..' not in relative.parts and not relative.is_absolute()
 raw=base64.b64decode(value); dest=output/relative
 if dest.exists(): assert dest.read_bytes()==raw,'immutable_comparison_mismatch'
 else: atomic(dest,raw,owner=cfg['site_owner'])
registry=output/'comparisons/registry.json'
entries=json.loads(registry.read_text()) if registry.exists() else []
record=request['record']; retired=request.get('retire_batches',[])
assert record['batch'] not in retired,'cannot_retire_current_batch'
namespace={}; exec(request['archive_source'],namespace)
archived=namespace['archive_batches'](output,cfg['archive'],retired) if retired else []
entries=[record]+[r for r in entries if r['batch'] not in [record['batch']]+retired]
atomic(registry,(json.dumps(entries,ensure_ascii=False,indent=2)+'\n').encode(),owner=cfg['site_owner'])
# Render the registry with the publisher supplied as a frozen source string, never eval evidence.
namespace={}; exec(request['listing_source'],namespace)
atomic(output/'comparisons/index.html',namespace['listing'](entries),owner=cfg['site_owner'])
if cfg.get('static_only'):
 assert not request['sources'],'static_publish_must_not_change_runtime_sources'
 next_compose=pathlib.Path(current_compose)
else:
 service=compose['services'][cfg['service']]
 targets={cfg['source_mount']+'/'+name for name in cfg['source_files']}
 service['volumes']=[v for v in service['volumes'] if (v.get('target') if isinstance(v,dict) else v.split(':')[1]) not in targets]
 service['volumes'] += [{'type':'bind','source':str(release/name),'target':cfg['source_mount']+'/'+name,'read_only':True} for name in cfg['source_files']]
 atomic(next_compose,(json.dumps(compose,indent=2)+'\n').encode(),0o600)
 command([docker,'compose','-p',cfg['project'],'--project-directory',before['Config']['Labels']['com.docker.compose.project.working_dir'],'-f',str(next_compose),'up','-d','--no-build','--pull','never',cfg['service']])
for _ in range(15):
 try:
  with urllib.request.urlopen(cfg['base_url']+'/_workbench/status',timeout=3) as r: status=json.load(r)
  break
 except (OSError,ValueError): time.sleep(1)
else: raise RuntimeError('workbench_health_not_ready')
new_records=records(output/'index.html')
assert old_ids<={r['id'] for r in new_records},'workbench_history_lost'
assert 'comparisons/index.html' in (output/'index.html').read_text(),'navigation_missing'
for name,value in request['files'].items(): assert (output/name).read_bytes()==base64.b64decode(value)
with urllib.request.urlopen(cfg['base_url']+'/comparisons/'+record['path'],timeout=5) as r: assert r.status==200
after=inspect(); after_others=other_containers()
without=lambda rows:sorted(r for r in rows if not r.startswith(cfg['container']+' '))
receipt={'status':'published','url':cfg['base_url']+'/comparisons/'+record['path'],'files_verified':len(request['files']),'old_case_records':len(old_records),'case_records':len(new_records),'case_ids_preserved':True,'other_containers_unchanged':without(before_others)==without(after_others),'workbench_image_unchanged':before['Image']==after['Image'],'old_index_sha256':old_index_sha,'new_index_sha256':hashlib.sha256((output/'index.html').read_bytes()).hexdigest(),'base_release':cfg['expected_base_release'],'presentation_overlay':str(release),'compose':str(next_compose),'source_hashes':{n:hashlib.sha256(base64.b64decode(v)).hexdigest() for n,v in request['sources'].items()},'model_calls':0,'database_writes':0}
receipt.update(static_only=bool(cfg.get('static_only')),workbench_container_unchanged=before['Id']==after['Id'])
receipt.update(archived=archived,visible_batches=[r['batch'] for r in entries])
if cfg.get('static_only'): receipt['presentation_overlay']=None
atomic(private/'receipt.json',json.dumps(receipt,indent=2).encode(),0o600)
print(json.dumps(receipt))
'''


def deploy(config, record, files):
    import inspect
    cfg = config["deployment"]
    payload = {"deployment": cfg, "record": record,
               "files": {k: base64.b64encode(v).decode() for k, v in files.items()},
               "sources": {n: base64.b64encode((ROOT / n).read_bytes()).decode() for n in cfg["source_files"]},
               "retire_batches": config.get("retire_batches", []),
               "archive_source": "import hashlib,re\nfrom pathlib import Path\n" + inspect.getsource(archive_batches),
               "listing_source": "import html\n" + inspect.getsource(listing)}
    argv = [cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o",
            "UpdateHostKeys=no", "-o", f"ConnectTimeout={cfg['connect_timeout_seconds']}", cfg["ssh_target"],
            shlex.join([cfg["remote_python"], "-c", REMOTE])]
    result = subprocess.run(argv, input=encode(payload), capture_output=True, timeout=cfg["command_timeout_seconds"], check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1500:])
    receipt = json.loads(result.stdout)
    (ROOT / config["receipt"]).write_bytes(encode(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--deploy", action="store_true", help="publish configured static files and optional workbench source overlay")
    args = parser.parse_args()
    config = read(args.config)
    record, files = prepare(config)
    local_receipt = publish_local(config, record, files)
    if config.get("local_receipt"):
        (ROOT / config["local_receipt"]).write_bytes(encode(local_receipt))
    print(json.dumps(deploy(config, record, files) if args.deploy else record, ensure_ascii=False))


if __name__ == "__main__":
    main()
