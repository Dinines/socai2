"""Post-release source-card HTTP and one read-only historical retrieval probe."""
import argparse
import json
from pathlib import Path

from tools.testdata.case_knowledge.production import remote

ROOT = Path(__file__).resolve().parents[3]

HTTP = r'''
import json,sys,urllib.request,urllib.error
p=json.load(sys.stdin); c=p['config']; receipts=[]
def request(label,method,path,body=None):
 req=urllib.request.Request(c['transport']['api_base_url']+path,method=method,
  headers={'Content-Type':'application/json','Authorization':'Bearer '+p['key']},
  data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None)
 try:
  with urllib.request.urlopen(req,timeout=c['transport']['http_timeout_seconds']) as r:
   status,value=r.status,json.loads(r.read())
 except urllib.error.HTTPError as e:
  status,value=e.code,json.loads(e.read())
 receipts.append({'label':label,'method':method,'path':path,'request':body,'status':status,'body':value})
 assert 200<=status<300,label
 return value
try:
 imported=request('import-history','POST','/api/v1/kb/alert-experiences',{'alert_ids':c['alert_ids']})
 assert all(r['state']=='stored' for r in imported['cards'])
 ids=[r['document_id'] for r in imported['cards']]
 indexed=request('index','POST','/api/v1/kb/index',{'document_ids':ids})
 assert indexed['state']=='completed'
 for ident in ids: request('card-'+ident,'GET','/api/v1/kb/alert-experiences/'+ident)
 summary={'state':'passed','document_ids':ids,'analysis_model_calls':0,'run_writes':0}
except Exception as e:
 summary={'state':'failed_inspect_before_retry','error_type':type(e).__name__,'last_request':receipts[-1]['label'] if receipts else None}
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
  assert all(r['purpose']=='historical_case_reference' for r in rows)
  print(json.dumps({'state':'passed','scope':'read-only adapter, configured probe time boundary, not a production Run',
   'analysis_model_calls':0,'run_writes':0,'checked_at':at.isoformat(),'rows':rows,'metadata':metadata},ensure_ascii=False))
 finally:await close_case_database()
asyncio.run(main())
'''


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main(path, phase):
    c = json.loads(path.read_text())
    output = ROOT / c["output"]
    if phase == "import":
        keyfile = ROOT / c["credential_file"]
        assert not keyfile.stat().st_mode & 0o077
        private = json.loads(keyfile.read_text())
        assert private["tenant_id"] == c["tenant_id"] and private["user_id"] == c["actor_id"]
        save(output / "intent.json", {"release": c["release"], "source_alert_ids": c["alert_ids"],
                                      "source_kind": "existing recorded synthetic acceptance alerts", "analysis_model_calls": 0})
        result = remote(c, HTTP, {"config": c, "key": private["api_key"]})
        save(output / "http.json", result)
        assert result["summary"]["state"] == "passed"
        print(json.dumps(result["summary"]))
    else:
        summary = json.loads((output / "http.json").read_text())["summary"]
        snapshot = json.loads((ROOT / c["local_snapshot"]).read_text())
        args = next(a["content_json"]["actual_args"] for a in snapshot["artifacts"]
                    if a["kind"] == "tool_response" and a["content_json"].get("tool_name") == "knowledge")
        keys = [k for k in args["parameters"]["selectors"] if k.get("purpose") == "historical_case_reference"]
        key = next(k for k in keys if any(p["source_path"] == "$.ocsf_json.process.cmd_line" for p in k["source_paths"]))
        key["filters"].update(c["probe_history_window"])
        args["parameters"]["selectors"] = [key]
        save(output / "retrieval-intent.json", {"args": args, "scope": "read-only adapter; probe window explicit in config"})
        result = remote(c, PROBE, {"args": args, "tenant_id": c["tenant_id"],
                                  "document_ids": summary["document_ids"]}, container=True)
        save(output / "retrieval.json", result)
        print(json.dumps({"state": result["state"], "rows": len(result["rows"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("import", "probe"))
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.phase)
