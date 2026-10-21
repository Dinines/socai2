"""Temporarily remove only this API reader's config; prove real HTTP503 and restore it."""
from pathlib import Path
import hashlib,json,os,subprocess,urllib.error,urllib.parse,urllib.request

R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/3a-identity-read-20261020'


def save(name,value):
    with (E/name).open('x') as stream:json.dump(value,stream,indent=2)
    (E/name).chmod(0o600)


def main():
    os.umask(0o077)
    assert (E/'deployment.json').exists() and not (E/'graph-config-removed.json').exists()
    assert not (E/'model-call-started.json').exists()
    state=json.loads((R/'private/app-identity-read-3a.json').read_text());identity=state['identities']['reader_a']
    path=R/'private/identity-graph-3a/config.json';backup=path.with_name('config.temporarily-absent-3a.json')
    original=path.read_bytes();assert hashlib.sha256(original).hexdigest()==state['graph_config_sha256'] and not backup.exists()
    url='http://127.0.0.1:18000/api/v1/graph/identity-context?'+urllib.parse.urlencode({'tenant_id':identity['tenant_id'],'accounts':'svc-identity-a'})
    def get():
        request=urllib.request.Request(url,headers={'Authorization':'Bearer '+identity['key']})
        try:
            with urllib.request.urlopen(request,timeout=20) as response:return response.status,json.load(response)
        except urllib.error.HTTPError as error:return error.code,json.load(error)
    status,before=get();assert status==200 and before['source_status']=='success'
    save('graph-config-success-before.json',{'status':status,'response':before})
    save('graph-config-removed.json',{'only_dedicated_config_removed':True,'original_sha256':hashlib.sha256(original).hexdigest(),'shared_neo4j_or_other_readers_changed':False})
    os.replace(path,backup)
    try:
        status,failed=get();assert status==503 and failed['source_status']=='unavailable' and failed['source_reason']=='graph_not_configured' and not failed['identities']
        save('graph-config-failure-http.json',{'status':status,'response':failed,'actual_api_http_503':True,'shared_graph_outage':False})
        code='''import asyncio,json,pathlib,uuid
from app.context import identity
from app.agents.auto_triage_agent import _build_alert_context
from app.workers.fused_alert_consumer import FusedAlertTriageWorker,build_state,worker_enabled
E=pathlib.Path('/evidence');state=json.loads(pathlib.Path('/private/state.json').read_text())
def save(name,value):
 with (E/name).open('x') as f:json.dump(value,f,indent=2)
 (E/name).chmod(0o600)
async def main():
 assert not worker_enabled();identity.clear_cache()
 tenant=state['identities']['a']['tenant_id']
 envelope={'tenant_id':tenant,'id':str(uuid.uuid5(uuid.NAMESPACE_URL,state['batch']+'/source-failure-projection')),'alert':{'title':'Probe-only graph source failure','rule_id':state['rule_id'],'username':'svc-identity-a','severity':'critical'}}
 investigation=build_state(envelope);assert investigation is not None
 await FusedAlertTriageWorker(bootstrap_servers='')._attach_identity_context(investigation)
 read=investigation.identity_context_read;context=_build_alert_context(investigation,nonce='probe-only')
 assert read['status']=='unavailable' and read['reason']=='http_error' and read['http_status']==503
 assert read['graph_source_status']=='unavailable' and read['graph_source_reason']=='graph_not_configured'
 assert not read['identities'] and not read['prompt_block'] and 'graph_not_configured' in context
 save('actual-graph-source-failure-read.json',read)
 save('failure-prompt-projection.json',{'read':read,'context':context,'model_invoked':False,'probe_only':True,'does_not_claim_model_saw_failure':True})
 print(json.dumps({'http_status':503,'graph_reason':'graph_not_configured','adopted_count':0,'model_calls':0}))
asyncio.run(main())'''
        command=['docker','run','--rm','--user','0','--network','socai2_default','--env-file',str(R/'private/probe-identity-read-3a.env'),'-v',str(R/'private/app-identity-read-3a.json')+':/private/state.json:ro','-v',str(E)+':/evidence']
        for host,target in [('org-memory-3a','org-memory'),('tenant-skill-3a','tenant-skill'),('kb-read-3a','triage-kb'),('dispositions-3a','dispositions'),('identity-read-3a','triage-identity')]:command+=['-v',str(R/'private'/host)+':/run/secrets/'+target+':ro']
        command+=['socai2-agents:identity-read-3a-20261020','python','-c',code]
        result=subprocess.run(command,text=True,capture_output=True)
        (E/'graph-source-failure-projection.log').write_text(result.stdout+result.stderr);(E/'graph-source-failure-projection.log').chmod(0o600)
        assert result.returncode==0,'Config is restored in finally; inspect projection checkpoint before continuing'
    finally:
        assert backup.read_bytes()==original and not path.exists()
        os.replace(backup,path)
        assert path.read_bytes()==original and path.stat().st_uid==10001 and path.stat().st_mode&0o777==0o600
        save('graph-config-restored.json',{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes_and_permissions_preserved':True,'api_or_shared_graph_restarts':0})
    status,after=get();assert status==200 and after==before
    save('graph-config-success-after.json',{'status':status,'response':after,'same_as_before':True})
    print(json.dumps({'actual_http_statuses':[200,503,200],'projection_model_calls':0,'shared_service_outage':False,'config_restored':True}))


if __name__=='__main__':main()
