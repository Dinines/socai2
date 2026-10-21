"""Bounded probe containers; checkpoints are owned by each operator/phase."""
import json,os,subprocess,sys
from prepare_triage_budget_3a import R,E,B,STATE,save
from deploy_triage_request_3a import inspect


def command(operator,args=(),*,state_file=STATE):
    item=inspect('socai2-agents-1')
    networks=list(item['NetworkSettings']['Networks']);assert len(networks)==1
    image=item['Image']
    cmd=['docker','run','--rm','--user','0:0','--network',networks[0],
         '--read-only','--tmpfs','/tmp:rw,nosuid,size=128m','--cap-drop','ALL','--cap-add','DAC_OVERRIDE','--security-opt','no-new-privileges:true',
         '--env-file',str(R/'private/probe-triage-budget-3a.env'),'-e','PYTHONPATH=/app','-e','PYTHONDONTWRITEBYTECODE=1',
         '-v',str(R/'source/deploy/aisoc21')+':/operators:ro','-v',str(E)+':/evidence',
         '-v',str(state_file)+':/private/state.json:ro','-v',str(R/'certificates/socai2-ca.crt')+':/run/certs/ca.crt:ro',
         '-v',str(R/'private/triage-budget-3a')+':/run/secrets/triage-budget:ro',
         image,'python','/operators/'+operator,*args]
    return cmd


def main(phase,*args):
    os.umask(0o077)
    assert (E/'deployment-final.json').exists()
    if phase=='allow-b-backlog':
        assert (E/'budget-b-live-stopped.json').exists() and not (E/'budget-allow-b-backlog.json').exists()
        state=json.loads(STATE.read_text());path=R/'private/triage-budget-3a/policy.json'
        old=json.loads(path.read_text());new=json.loads(json.dumps(old));tenant=state['identities']['b']['tenant_id']
        assert new['tenants'][tenant]['max_unsettled']==1
        new['tenants'][tenant]['max_unsettled']=2
        save('budget-policy-before-allow-b-backlog.json',old)
        replacement=path.with_suffix('.replacement')
        with replacement.open('x') as f:json.dump(new,f,indent=2)
        replacement.chmod(0o600);os.chown(replacement,10001,10001);replacement.replace(path)
        save('budget-policy-final.json',new)
        save('budget-allow-b-backlog.json',{'only_change':'B max_unsettled 1 to 2 for bounded recovery fixture','prior_unknown_refunded_or_reclaimed':False})
        print(json.dumps({'phase':phase,'prior_unknown_preserved':True}));return
    if phase=='expand-a':
        assert (E/'budget-held-a_denied.json').exists() and not (E/'budget-expand-a.json').exists()
        state=json.loads(STATE.read_text());path=R/'private/triage-budget-3a/policy.json'
        old=json.loads(path.read_text());new=json.loads(json.dumps(old));tenant=state['identities']['a']['tenant_id']
        assert new['tenants'][tenant]=={'window_seconds':86400,'max_calls':2,'max_reserved_tokens':40000,'max_unsettled':1}
        new['tenants'][tenant].update(max_calls=3,max_reserved_tokens=60000,max_unsettled=2)
        save('budget-policy-before-expand-a.json',old)
        replacement=path.with_suffix('.replacement')
        with replacement.open('x') as f:json.dump(new,f,indent=2)
        replacement.chmod(0o600);os.chown(replacement,10001,10001);replacement.replace(path)
        save('budget-policy-after-expand-a.json',new)
        save('budget-expand-a.json',{'only_change':'controlled A fixture limits 3 calls/60000 reserved/2 unsettled',
                                    'prior_unknown_refunded_or_reclaimed':False,'new_ingress_or_request':0})
        print(json.dumps({'phase':'expand-a','prior_unknown_preserved':True}));return
    if phase=='topup':
        assert (E/'budget-token-hold.json').exists() and not (E/'budget-topup.json').exists()
        state=json.loads(STATE.read_text());path=R/'private/triage-budget-3a/policy.json'
        old=json.loads(path.read_text());new=json.loads(json.dumps(old))
        tenant=state['identities']['b']['tenant_id']
        assert new['tenants'][tenant]['max_reserved_tokens']==20000
        new['tenants'][tenant]['max_reserved_tokens']=60000
        save('budget-policy-before-topup.json',old)
        replacement=path.with_suffix('.replacement')
        with replacement.open('x') as f:json.dump(new,f,indent=2)
        replacement.chmod(0o600);os.chown(replacement,10001,10001);replacement.replace(path)
        save('budget-policy-after-topup.json',new)
        save('budget-topup.json',{'only_change':'tenant_b_max_reserved_tokens_20000_to_60000',
                                  'charges_refunded_or_reset':False,'new_inputs_or_model_calls_in_topup':0})
        print(json.dumps({'phase':'topup','changed_one_policy_cap':True,'reset_charges':False}));return
    if phase=='ingress':
        assert len(args)==1 and args[0] in ['a_done','b_done','a_unknown','a_denied','b_denied','b_extra']
        state_file=STATE
        if args[0].startswith('b_'):
            alternate=R/'private/app-triage-budget-3a-b.json'
            if not alternate.exists():
                state=json.loads(STATE.read_text());a,b=state['identities']['a'],state['identities']['b']
                state['identities']['a'],state['identities']['b']=b,a
                with alternate.open('x') as f:json.dump(state,f,indent=2)
                alternate.chmod(0o600)
            state_file=alternate
        cmd=command('ingress_triage_budget_3a.py',args,state_file=state_file)
    else:
        assert phase in ['setup','setup-extra','success','concurrency','concurrency-recover','live-concurrency','b-live-concurrency','holds','stop','stop-live','stop-b','verify','pg-boundaries','resume-extra','resume'] and not args
        cmd=command('broker_triage_budget_3a.py',[phase])
    log=E/('operator-'+phase+('-'+args[0] if args else '')+'.log')
    assert not log.exists(),'Retain prior phase outcome; do not rerun mutations blindly'
    with log.open('x') as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
    log.chmod(0o600)
    print(json.dumps({'phase':phase,'args':args,'exit_code':result.returncode,'log':log.name}))
    assert result.returncode==0,'Inspect phase log/checkpoints before any continuation'


if __name__=='__main__':main(*sys.argv[1:])
