"""One post-release HTTP Case/H write/read; no Run starts or model calls."""
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docs/operations"))
from production_case_probe import query, save

WORKER = r'''
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
 auth=request('login','POST','/api/v1/auth/login',p['credentials'],False)
 token=auth['access_token']
 me=request('me','GET','/api/v1/auth/me',retain=False)
 assert me['id']==c['actor_id'] and me['tenant_id']==c['target']['tenant_id']
 source=request('source-case','GET','/api/v1/socai2/cases/'+c['source_case_id'])
 assert not source['members_truncated'] and sorted(m['alert_id'] for m in source['members'])==sorted(c['alert_ids'])
 created=request('create','POST','/api/v1/socai2/cases',c['create'])
 base='/api/v1/socai2/cases/'+created['case_id']
 fields={**c['human_fields'],'expected_scope_revision':created['scope_revision']}
 initial=request('human-create','POST',base+'/tasks',{**fields,**c['human_create']})
 task=initial['task']
 revised=request('human-revise','PUT',base+'/tasks/'+task['id'],{
   **fields,**c['human_revise'],'expected_row_version':task['row_version']})
 current=request('human-current','GET',base+'/tasks/'+task['id'])
 versions=request('human-revisions','GET',base+'/tasks/'+task['id']+'/revisions')
 case=request('case-final','GET',base)
 run=request('run-pending','GET',base+'/runs/'+created['pending_run_id'])
 assert current==revised['task'] and len(versions['items'])==2
 assert current['current']['result_text']==c['human_revise']['result_text']
 assert next(r for r in versions['items'] if r['id']==task['current_revision_id'])['result_text']==c['human_create']['result_text']
 assert run['run']['state']=='pending_update' and not run['result_ids']
 assert case['case']['current_assessment_id'] is None
 summary={'state':'passed','case_id':created['case_id'],'run_id':created['pending_run_id'],
   'task_id':task['id'],'initial_revision_id':task['current_revision_id'],
   'selected_revision_id':current['current_revision_id'],'http_requests':len(receipts),
   'authentication':'normal_login_existing_user','model_calls':0,'run_started':False,
   'scope':'new acceptance Case and one revised material-review task; source Case is only read'}
except Exception as exc:
 summary={'state':'failed_inspect_before_retry','error_type':type(exc).__name__,
   'last_completed_request':receipts[-1]['label'] if receipts else None}
print(json.dumps({'summary':summary,'requests':receipts},ensure_ascii=False))
'''


def run(path):
    config = json.loads(path.read_text())
    output = ROOT / config["output"]
    output.mkdir(parents=True, exist_ok=False)
    credential_file = ROOT / config["credential_file"]
    assert not credential_file.stat().st_mode & 0o077
    private = json.loads(credential_file.read_text())
    credentials = {k: private[k] for k in ("email", "password")}
    assert private["user_id"] == config["actor_id"] and private["tenant_id"] == config["target"]["tenant_id"]
    save(output / "intent.json", {"release": config["release"], "create": config["create"],
        "human_fields": config["human_fields"], "human_create": config["human_create"],
        "human_revise": config["human_revise"], "attempts": 1, "model_calls": 0})
    t = config["transport"]
    command = [t["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={t['connect_timeout_seconds']}",
               t["ssh_target"], shlex.join([t["remote_python"], "-c", WORKER])]
    result = subprocess.run(command, input=json.dumps({"config": config, "credentials": credentials}),
                            capture_output=True, text=True, timeout=config["batch_timeout_seconds"], check=False)
    if result.returncode:
        save(output / "transport.json", {"state": "unknown_inspect_before_retry", "exit_code": result.returncode})
        raise RuntimeError("production_http_transport_unknown")
    value = json.loads(result.stdout)
    save(output / "http.json", value)
    assert value["summary"]["state"] == "passed", "production_http_incomplete"
    cid = value["summary"]["case_id"]
    # Read only this acceptance Case and its one task, not a database-wide audit.
    snapshot = query(config, f"""SELECT jsonb_build_object(
      'case',(SELECT to_jsonb(c) FROM socai2.cases c WHERE c.id='{cid}'::uuid),
      'runs',(SELECT jsonb_agg(to_jsonb(r)) FROM socai2.runs r WHERE r.case_id='{cid}'::uuid),
      'tasks',(SELECT jsonb_agg(to_jsonb(t)) FROM socai2.tasks t WHERE t.case_id='{cid}'::uuid),
      'revisions',(SELECT jsonb_agg(to_jsonb(v)) FROM socai2.task_revisions v WHERE v.case_id='{cid}'::uuid));""")
    save(output / "database.json", snapshot)
    current = next(r["body"] for r in value["requests"] if r["label"] == "human-current")
    saved = next(r for r in snapshot["revisions"] if r["id"] == current["current_revision_id"])
    fields = ("id", "task_id", "case_id", "revision", "result_text", "result_scope", "source_refs", "state")
    assert all(current["current"][k] == saved[k] for k in fields)
    assert snapshot["tasks"][0]["current_revision_id"] == saved["id"]
    summary = {**value["summary"], "saved_fields_match": list(fields), "database": config["target"]["database"]}
    save(output / "verification.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    run(parser.parse_args().config)
