"""Post-release KB HTTP import/index/read and read-only C2 adapter probe; no Case/model run."""
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docs/operations"))
from production_case_probe import save

HTTP = r'''
import json,sys,urllib.request,urllib.error
p=json.load(sys.stdin);c=p['config'];receipts=[];token=None
def request(label,method,path,body=None,retain=True):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(c['transport']['api_base_url']+path,method=method,headers=headers,
  data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None)
 try:
  with urllib.request.urlopen(req,timeout=c['transport']['http_timeout_seconds']) as response:
   status,value=response.status,json.loads(response.read())
 except urllib.error.HTTPError as error:
  status=error.code
  try:value=json.loads(error.read())
  except ValueError:value={'error':'non_json_http_error'}
 if retain:receipts.append({'label':label,'method':method,'path':path,'request':body,'status':status,'body':value})
 if not 200<=status<300:raise RuntimeError(label+'_http_'+str(status))
 return value
try:
 token=(p['api_key'] if c['authentication']=='api_key' else
  request('login','POST','/api/v1/auth/login',p['credentials'],False)['access_token'])
 me=request('me','GET','/api/v1/auth/me',retain=False)
 assert me['id']==c['actor_id'] and me['tenant_id']==c['tenant_id']
 ids=[]
 for i,doc in enumerate(p['documents']):
  ids.extend(r['id'] for r in request('ingest-'+str(i+1),'POST','/api/v1/kb/ingest',doc['request']))
 indexed=request('index','POST','/api/v1/kb/index',{'document_ids':ids})
 assert indexed['state']=='completed' and {d['doc_id'] for d in indexed['documents']}==set(ids)
 for ident in ids:
  assert request('read-'+ident,'GET','/api/v1/kb/documents/'+ident)['id']==ident
 summary={'state':'passed','document_ids':ids,'http_requests':len(receipts),'analysis_model_calls':0,
  'authentication':c['authentication'],'scope':'two public source documents, explicit native-vector index and chunk metadata readback'}
except Exception as exc:
 summary={'state':'failed_inspect_before_retry','error_type':type(exc).__name__,
  'last_completed_request':receipts[-1]['label'] if receipts else None}
print(json.dumps({'summary':summary,'requests':receipts},ensure_ascii=False))
'''

PROBE = r'''
import asyncio,json,sys
from uuid import UUID
from app.db.case_database import get_case_write_sessions,close_case_database
from app.socai2.baseline_service import BaselineService
from app.socai2.knowledge_config import load
from app.socai2.knowledge_source import query
p=json.load(sys.stdin)
async def main():
 profile,fingerprint=load()
 for key in p['args']['parameters']['selectors']:key['profile_sha256']=fingerprint
 try:
  rows,at,metadata=await query(BaselineService(get_case_write_sessions()),UUID(p['tenant_id']),p['args'])
  assert rows and all(r['record_id'] in p['document_ids'] for r in rows)
  assert {r['purpose'] for r in rows}=={'technical_explanation','investigation_guidance'}
  print(json.dumps({'state':'passed','scope':'read-only C2 adapter probe with saved local query text; not a production Run',
   'analysis_model_calls':0,'database_writes':0,'checked_at':at.isoformat(),'rows':rows,'metadata':metadata},ensure_ascii=False))
 finally:await close_case_database()
asyncio.run(main())
'''


def remote(config, program, payload, *, container=False):
    t = config["transport"]
    command = ([t["docker"], "exec", "-i", config["api_container"], "python", "-B", "-c", program]
               if container else [t["remote_python"], "-c", program])
    argv = [t["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={t['connect_timeout_seconds']}",
            t["ssh_target"], shlex.join(command)]
    result = subprocess.run(argv, input=json.dumps(payload), text=True, capture_output=True,
                            timeout=config["batch_timeout_seconds"], check=False)
    if result.returncode:
        raise RuntimeError("transport_or_probe_failed_inspect_before_retry")
    return json.loads(result.stdout)


def main(path, phase):
    config = json.loads(path.read_text())
    output = ROOT / config["output"]
    if phase == "import":
        output.mkdir(parents=True, exist_ok=False)
        private_file = ROOT / config["credential_file"]
        assert not private_file.stat().st_mode & 0o077
        private = json.loads(private_file.read_text())
        assert private["user_id"] == config["actor_id"] and private["tenant_id"] == config["tenant_id"]
        documents = json.loads((ROOT / config["corpus"]).read_text())
        save(output / "intent.json", {"release": config["release"], "documents": documents,
                                     "analysis_model_calls": 0, "attempts": 1})
        auth = ({"api_key": private["api_key"]} if config["authentication"] == "api_key" else
                {"credentials": {k: private[k] for k in ("email", "password")}})
        value = remote(config, HTTP, {"config": config, "documents": documents, **auth})
        save(output / "http.json", value)
        assert value["summary"]["state"] == "passed", "production_kb_http_incomplete"
        print(json.dumps(value["summary"]))
    else:
        imported = json.loads((output / "http.json").read_text())["summary"]
        assert imported["state"] == "passed" and not (output / "retrieval.json").exists()
        data = json.loads((ROOT / config["local_snapshot"]).read_text())
        args = next(a["content_json"]["actual_args"] for a in data["artifacts"]
                    if a["kind"] == "tool_response" and a["content_json"].get("tool_name") == "knowledge")
        args["parameters"]["selectors"] = args["parameters"]["selectors"][:2]
        save(output / "retrieval-intent.json", {"scope": "read-only adapter, no Run created", "args": args})
        value = remote(config, PROBE, {"tenant_id": config["tenant_id"], "args": args,
                                      "document_ids": imported["document_ids"]}, container=True)
        save(output / "retrieval.json", value)
        print(json.dumps({"state": value["state"], "rows": len(value["rows"]), "analysis_model_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("import", "probe"))
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    main(args.config, args.phase)
