"""Build on the exact cached parent and add only the budget policy mount/env."""
import hashlib,json,subprocess,sys
from prepare_triage_budget_3a import R,E,STATE,save,sha
from deploy_triage_request_3a import PARTS as PREVIOUS,healthy,inspect,describe,verify_runtime_source
from test_triage_budget_3a import sources

PARTS=PREVIOUS+['triage-budget-3a']


def compose():
    result=['docker','compose','--project-directory',str(R)]
    for part in PARTS:result+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    return result


def main():
    assert (E/'prepared.json').is_file() and not (E/'deployment-before.json').exists()
    state=json.loads(STATE.read_text());test=json.loads((E/'tests-agents-second.json').read_text())
    assert test['exit_code']==0 and test['failed']==test['errors']==0
    assert sources('agents')==test['tested_runtime_source_sha256']
    assert all(sha(R/'source'/p)==h for p,h in test['test_input_sha256'].items())
    parent='socai2-agents:triage-request-3a-20261020';image='socai2-agents:triage-budget-3a-20261020'
    before={n:inspect('socai2-'+n+'-1') for n in ['api','agents','fusion','actions']}
    assert all(before[n]['Image']==h for n,h in state['images'].items())
    assert before['agents']['Image']==inspect(parent)['Id']=='sha256:d6b9c7bb7eec6591e152b94a7372ce08289ee7d12b813711ab9c43ddef00c66d'
    assert len(PARTS)==21
    subprocess.run(compose()+['config','--quiet'],check=True,capture_output=True)
    save('deployment-before.json',{n:describe(v) for n,v in before.items()})
    with (E/'build-agents.log').open('x') as f:
        result=subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.agents-triage-budget-3a','-t',image,'.'],cwd=R/'source',stdout=f,stderr=subprocess.STDOUT)
    (E/'build-agents.log').chmod(0o600);assert result.returncode==0
    built=inspect(image)['Id'];save('built-image.json',{'agents':built,'parent':before['agents']['Image']})
    subprocess.run(compose()+['up','-d','--no-deps','--pull','never','agents'],check=True,capture_output=True)
    after=healthy('agents')
    oldenv=dict(e.split('=',1) for e in before['agents']['Config']['Env']);newenv=dict(e.split('=',1) for e in after['Config']['Env'])
    assert newenv.pop('AISOC_TRIAGE_BUDGET_POLICY_FILE')=='/run/secrets/triage-budget/policy.json' and oldenv==newenv
    oldmounts={m['Destination']:m for m in before['agents']['Mounts']};newmounts={m['Destination']:m for m in after['Mounts']}
    policy=newmounts.pop('/run/secrets/triage-budget');assert not policy['RW'] and oldmounts==newmounts
    assert after['Image']==built and after['Id']!=before['agents']['Id'] and after['HostConfig']['ReadonlyRootfs']
    for n in ['api','fusion','actions']:assert describe(inspect('socai2-'+n+'-1'))==describe(before[n])
    count=verify_runtime_source('agents')
    code="import json,os;from app.workers.triage_budget import policy_for;from app.workers.fused_alert_consumer import worker_enabled;from uuid import UUID;assert not worker_enabled();print(json.dumps({'uid':os.getuid(),'worker_enabled':False,'policies':[policy_for(UUID(t)).__dict__ for t in json.loads(__import__('sys').argv[1])]}))"
    resident=json.loads(subprocess.check_output(['docker','exec','socai2-agents-1','python','-c',code,json.dumps([state['identities'][n]['tenant_id'] for n in ['a','b']])]))
    result={'images':{'agents':built},'parent':before['agents']['Image'],'only_updated':['agents'],'compose_layers':21,
            'original_env_and_mounts_preserved':True,'added_env':'AISOC_TRIAGE_BUDGET_POLICY_FILE','added_readonly_mount':'/run/secrets/triage-budget',
            'runtime_source_files':count,'source_matches_tests':True,'dependencies_changed':False,'resident':resident}
    save('deployment.json',result);print(json.dumps(result))


def refresh():
    """One explicitly checked correction before probes; preserve first deployment."""
    initial=json.loads((E/'deployment.json').read_text())
    assert not (E/'deployment-final-before.json').exists() and not (E/'inputs.json').exists()
    test=json.loads((E/'tests-agents-final.json').read_text())
    assert test['exit_code']==0 and test['failed']==test['errors']==0
    assert sources('agents')==test['tested_runtime_source_sha256']
    before=inspect('socai2-agents-1')
    assert before['Image']==initial['images']['agents']
    save('deployment-final-before.json',{'agents':describe(before),'reason':'Budget claim SQL/unavailable failures need BudgetHold so offsets are retained'})
    with (E/'build-agents-final.log').open('x') as f:
        result=subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.agents-triage-budget-3a','-t','socai2-agents:triage-budget-3a-20261020','.'],cwd=R/'source',stdout=f,stderr=subprocess.STDOUT)
    (E/'build-agents-final.log').chmod(0o600);assert result.returncode==0
    built=inspect('socai2-agents:triage-budget-3a-20261020')['Id']
    save('built-image-final.json',{'agents':built,'prior_candidate':before['Image'],'parent':initial['parent']})
    subprocess.run(compose()+['up','-d','--no-deps','--pull','never','agents'],check=True,capture_output=True)
    after=healthy('agents')
    assert after['Image']==built and describe(after)['env_sha256']==describe(before)['env_sha256']
    assert after['Mounts']==before['Mounts']
    count=verify_runtime_source('agents')
    result={**initial,'images':{'agents':built},'prior_candidate':before['Image'],'tests_attempt':'final',
            'runtime_source_files':count,'second_controlled_agents_update_before_input':True,'env_or_mount_change_in_refresh':False}
    save('deployment-final.json',result);print(json.dumps(result))


if __name__=='__main__':
    refresh() if sys.argv[1:]==['refresh'] else main()
