"""Run explicitly configured existing ingress/jobs and retain unmodified receipts.

No investigation implementation, input enrichment, schema migration or retries.
"""

import argparse
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

WORKER = r'''
import json,subprocess,sys,urllib.request,urllib.error
p=json.load(sys.stdin)
t=p['transport']
if p['mode']=='http':
    request=urllib.request.Request(t['api_base_url']+p['path'],method=p['method'],
        data=json.dumps(p['body']).encode() if p['body'] is not None else None,
        headers={'Authorization':'Bearer '+p['key'],'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=t['http_timeout_seconds']) as response:
            result={'status':response.status,'body':json.loads(response.read())}
    except urllib.error.HTTPError as error:
        raw=error.read().decode('utf-8',errors='replace')
        try:body=json.loads(raw)
        except ValueError:body={'unparsed_body':raw}
        result={'status':error.code,'body':body}
elif p['mode']=='job':
    args=[t['remote_python'],t['processing_entry']]
    if t.get('processing_profile_mode','explicit')=='explicit':
        args+=['--profile',t['processing_profile_file']]
    args+=['job','--tenant',p['tenant'],'--actor',p['actor'],*p['arguments']]
    result=subprocess.run(args,input=p['key'],text=True,capture_output=True,check=False)
    bodies=[]
    for line in result.stdout.splitlines():
        try:bodies.append(json.loads(line))
        except ValueError:pass
    result={'exit_code':result.returncode,'receipt':bodies[-1] if bodies else {'error':'missing_job_receipt'}}
elif p['mode']=='sql':
    args=[t['remote_docker'],'exec','-i',t['pg_container'],t['pg_client'],'-wXAtq','-v','ON_ERROR_STOP=1',
          '-U',t['pg_reader_role'],'-d',p['database']]
    completed=subprocess.run(args,input=p['sql'],text=True,capture_output=True,check=False)
    if completed.returncode:
        result={'error':'readonly_query_failed','exit_code':completed.returncode,
                'detail':completed.stderr.splitlines()[0] if completed.stderr else None}
    else:
        result={'body':json.loads(completed.stdout.strip())}
else:
    raise ValueError('unknown mode')
print(json.dumps(result,ensure_ascii=False))
'''


def save(path, value):
    with path.open("x") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")


def remote(config, request, *, job=False):
    transport = config["transport"]
    if request["mode"] == "job":
        profile_mode = transport.get("processing_profile_mode", "explicit")
        if profile_mode not in {"explicit", "current_release"}:
            raise ValueError("unsupported_processing_profile_mode")
        if profile_mode == "explicit" and not transport.get("processing_profile_file"):
            raise ValueError("processing_profile_file_required_for_new_jobs")
    request["transport"] = transport
    if request["mode"] in {"http", "job"}:
        path = Path(config["target"]["user_api_key_file"])
        if path.stat().st_mode & 0o077:
            raise ValueError("credential file must be private")
        request["key"] = json.loads(path.read_text())[config["target"]["user_api_key_json_path"]]
    argv = [transport["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={transport['connect_timeout_seconds']}",
            transport["ssh_target"], shlex.join([transport["remote_python"], "-c", WORKER])]
    result = subprocess.run(argv, input=json.dumps(request), text=True, capture_output=True, check=False,
                            timeout=transport["job_timeout_seconds"] if job else transport["command_timeout_seconds"])
    if result.returncode:
        raise RuntimeError(f"remote_transport_failed_exit_{result.returncode}; inspect before retry")
    return json.loads(result.stdout)


def query(config, sql):
    tenant = str(UUID(config["target"]["tenant_id"]))
    script = ("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
              f"SET LOCAL statement_timeout='{config['transport']['command_timeout_seconds']}s';\n"
              f"SET LOCAL app.current_tenant_id='{tenant}';\n" + sql + "\nROLLBACK;\n")
    result = remote(config, {"mode": "sql", "database": config["target"]["database"], "sql": script})
    if "error" in result:
        raise RuntimeError(result["error"] + ": " + str(result.get("detail")))
    return result["body"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("mode", choices=("auth", "send", "subjects", "job"))
    parser.add_argument("--name")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    root = args.config.parent
    def now():
        return datetime.now(UTC).isoformat()
    if args.mode == "auth":
        result = remote(config, {"mode": "http", "method": "GET", "path": "/api/v1/auth/me", "body": None})
        if result["status"] != 200:
            save(root / "account-auth-failure.json", result)
            raise RuntimeError("normal_api_authentication_failed")
        body = result["body"]
        if (body["id"], body["tenant_id"], body["username"]) != (
            config["target"]["actor_id"], config["target"]["tenant_id"], config["account"]["username"],
        ):
            raise RuntimeError("api_principal_mismatch")
        result = {"status": result["status"], "id": body["id"], "tenant_id": body["tenant_id"], "username": body["username"]}
        save(root / "account-authenticated.json", result)
    elif args.mode == "send":
        payloads = json.loads((root / "inputs.json").read_text())
        receipts = []
        for index, payload in enumerate(payloads, 1):
            save(root / f"ingress-{index}-intent.json", {"at": now(), "input_id": payload["id"]})
            result = remote(config, {"mode": "http", "method": "POST", "path": config["transport"]["ingress_path"], "body": payload})
            save(root / f"ingress-{index}-receipt.json", {"at": now(), **result})
            receipts.append(result)
            if result["status"] != 202:
                raise RuntimeError("ingress_not_confirmed; no automatic replay")
        result = {"accepted": len(receipts), "canonical_alert_ids": [r["body"]["canonical_alert_id"] for r in receipts]}
    elif args.mode == "subjects":
        ids = [str(UUID(json.loads((root / f"ingress-{i}-receipt.json").read_text())["body"]["canonical_alert_id"]))
               for i in range(1, config["execution_bounds"]["alert_attempts"] + 1)]
        literals = ",".join("'" + identity + "'::uuid" for identity in ids)
        result = query(config, f"""SELECT jsonb_build_object(
          'alerts',(SELECT coalesce(jsonb_agg(jsonb_build_object('id',id,'title',title)),'[]'::jsonb) FROM socai2.alerts WHERE id IN ({literals})),
          'members',(SELECT coalesce(jsonb_agg(to_jsonb(m)),'[]'::jsonb) FROM socai2.incident_alerts m WHERE alert_id IN ({literals})),
          'incidents',(SELECT coalesce(jsonb_agg(to_jsonb(i)),'[]'::jsonb) FROM socai2.incidents i WHERE id IN (SELECT incident_id FROM socai2.incident_alerts WHERE alert_id IN ({literals}))))""" + ";")
        save(root / ("subjects-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json"), result)
        result = {"alerts": len(result["alerts"]), "incidents": [r["id"] for r in result["incidents"]],
                  "members": len(result["members"])}
    else:
        if not args.name or not args.arguments:
            parser.error("job requires --name before the positional arguments and job arguments")
        save(root / (args.name + "-intent.json"), {"at": now(), "arguments": args.arguments})
        result = remote(config, {"mode": "job", "tenant": config["target"]["tenant_id"],
                                "actor": config["target"]["actor_id"], "arguments": args.arguments}, job=True)
        save(root / (args.name + "-receipt.json"), {"at": now(), **result})
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
