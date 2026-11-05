"""One-off model evaluation on 21. Existing container, no DB or service writes."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIVATE = Path("/opt/sting-aisoc-socai2/private/next-20261104")
HELPER = Path("/opt/sting-aisoc-socai2/releases/next-20261104-n9/next_service_remote.py")

# Executed in an ephemeral Python process inside the existing container. Only
# sanitized metadata and provider responses leave it; secrets arrive over stdin.
CHILD = r'''
import asyncio,json,os,sys,time
from types import SimpleNamespace
from urllib.parse import urlsplit
import httpx
x=json.load(sys.stdin)
error_ns={}
exec(x['error_helper'],error_ns)
for k in ('OPENAI_MODEL','OPENAI_BASE_URL','OPENAI_API_KEY','LLM_MODEL','LLM_BASE_URL','LLM_API_KEY','LLM_GATEWAY_URL','LLM_GATEWAY_API_KEY','LITELLM_MASTER_KEY','AISOC_LLM_MODEL'):
    os.environ.pop(k,None)
os.environ.update(x['env'])
from app.services.model_aliases import resolve_base_url,resolve_api_key
from app.services.llm_safety import LLMInputContract
from app.socai2.baseline_analysis_model import TenantChatGateway,usage
from app.socai2.model_protocol import DEEPSEEK_BASE
model=x['model']; base=resolve_base_url(model); key=resolve_api_key(model)
assert base and key
async def main():
    if x['phase']=='preflight':
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as c:
            h={'Authorization':'Bearer '+key}
            r=await c.get(base.rstrip('/')+'/models',headers=h); r.raise_for_status()
            ids=[v['id'] for v in r.json()['data']]
            assert model in ids
            out={'model':model,'models_http_status':r.status_code,'selected_model_present':True}
            if x['backend']=='small':
                route=await c.get(base.rstrip('/').removesuffix('/v1')+'/model/info',headers=h)
                route.raise_for_status()
                rows=[v for v in route.json()['data'] if v['model_name']==model]
                assert len(rows)==1
                params=rows[0]['litellm_params']; upstream=params['api_base']
                host=urlsplit(upstream).hostname
                assert host and (host.startswith(('10.','172.','192.168.')) or host in ('host.docker.internal','localhost') or '.' not in host)
                uh={'Authorization':'Bearer '+params['api_key']} if params.get('api_key') else {}
                ur=await c.get(upstream.rstrip('/')+'/models',headers=uh); ur.raise_for_status()
                out['route_model']=params['model']
                out['upstream_models']=[{'id':v['id'],'owned_by':v.get('owned_by'),'max_model_len':v.get('max_model_len'),'root_basename':str(v.get('root','')).rstrip('/').split('/')[-1]} for v in ur.json()['data']]
            else:
                assert base.rstrip('/')==DEEPSEEK_BASE and model=='deepseek-flash'
        return out
    body=x['body']; assert body['model']==model
    messages=body.get('messages',body.get('input'))
    assert LLMInputContract.validate(messages)==messages
    gateway=TenantChatGateway(); gateway.provider='chat_completions' if x['backend']=='small' else 'deepseek_responses'
    gateway.model=model; gateway.config=SimpleNamespace(base_url=base,api_key=key,model=model)
    start=time.monotonic()
    try:
        raw=await gateway.complete(body,120)
        result={'state':'response_received','raw':raw,'usage':usage(raw)}
    except Exception as exc:
        result={'state':'failed_or_unknown_no_retry','error_type':type(exc).__name__,'transport_error':error_ns['provider_error'](exc,key)}
        response=getattr(exc,'response',None)
        if response is not None:
            result['http_status']=response.status_code
    result['elapsed_seconds']=round(time.monotonic()-start,3)
    return result
try:
    result=asyncio.run(main())
except Exception as exc:
    result={'state':'pre_dispatch_or_metadata_failed','error_type':type(exc).__name__}
output=json.dumps(result,ensure_ascii=False)
assert key not in output
print(output)
'''


def save(name, value):
    with (HERE / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.chmod(HERE / name, 0o600)


def env(backend):
    path = PRIVATE / ("api.env" if backend == "small" else "model.deepseek.env")
    source = dict(line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    allowed = {"OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY",
        "LLM_GATEWAY_URL", "LLM_GATEWAY_API_KEY", "LITELLM_MASTER_KEY", "AISOC_LLM_MODEL"}
    return {k: v for k, v in source.items() if k in allowed}


def child(phase, backend, body=None):
    payload = {"phase": phase, "backend": backend, "env": env(backend), "body": body,
        "model": "aisoc-investigation" if backend == "small" else "deepseek-flash", "error_helper": json.loads((HERE / "plan-and-packets.json").read_text())["error_helper"]}
    try:
        result = subprocess.run(["docker", "exec", "-i", "socai2-next-api", "python", "-c", CHILD],
            input=json.dumps(payload).encode(), capture_output=True, timeout=140, check=False)
        if result.returncode:
            return {"state": "child_failed_unknown_no_retry", "returncode": result.returncode}
        output = result.stdout.decode().strip()
        for k, v in payload["env"].items():
            if ("KEY" in k or "TOKEN" in k) and v and v in output:
                raise ValueError("credential_in_result_refused")
        return json.loads(output)
    except subprocess.TimeoutExpired:
        return {"state": "child_timeout_unknown_no_retry"}


def fingerprint(helper):
    value = helper.protected_model_config()
    value["new_container"] = {k: v for k, v in helper.inspect("socai2-next-api").items() if k in {"Id", "Image"}}
    value["deepseek_profile_sha256"] = hashlib.sha256((PRIVATE / "model.deepseek.env").read_bytes()).hexdigest()
    return value


def main():
    spec = importlib.util.spec_from_file_location("existing_service_helper", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    phase = sys.argv[1]
    if phase == "preflight":
        before = fingerprint(helper)
        results = {backend: child("preflight", backend) for backend in ("deepseek",)}
        after = fingerprint(helper)
        save("preflight.json", {"before": before, "after": after, "unchanged": before == after,
            "models": results, "model_calls": 0})
        print(json.dumps({"unchanged": before == after, "models": results}, ensure_ascii=False), flush=True)
        return
    assert phase == "run"
    packet_file = HERE / "plan-and-packets.json"
    bundle = json.loads(packet_file.read_text())
    assert len(bundle["cells"]) == 2 and bundle["plan"]["retries"] == 0
    preflight = json.loads((HERE / "preflight.json").read_text())
    assert preflight["unchanged"] and all(r.get("selected_model_present") for r in preflight["models"].values())
    assert fingerprint(helper) == preflight["after"]
    save("batch-intent.json", {"started_at": datetime.now(UTC).isoformat(),
        "packets_sha256": hashlib.sha256(packet_file.read_bytes()).hexdigest(), "max_calls": 2})
    for cell in bundle["cells"]:
        save(cell["id"] + "-intent.json", {"body_sha256": cell["body_sha256"],
            "dispatch_intent_at": datetime.now(UTC).isoformat(), "attempt": 1})
        result = child("call", cell["backend"], cell["body"])
        save(cell["id"] + "-result.json", result)
        print(json.dumps({"cell": cell["id"], "state": result["state"],
            "seconds": result.get("elapsed_seconds"), "usage": result.get("usage")}), flush=True)
    after = fingerprint(helper)
    save("completion.json", {"finished_at": datetime.now(UTC).isoformat(), "protected_after": after,
        "protected_unchanged": after == preflight["after"], "cells": 2, "business_writes": 0, "tools": 0})


if __name__ == "__main__":
    main()
