"""Agents policy receipts and durable completion guard; worker remains disabled."""
from pathlib import Path
import hashlib,json,subprocess,time
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/3a-suppression-20261020'
BASE='sha256:4ac381d99e4e68e588f145e51cd2e3e98f02e6d52ce9e9822344ab43edd50b90'
PARTS=['services','embedding','gateway','investigation','correlation-2a','identity-2a','risk-2b','policy-2b','ioc-2c','context-2c','suppression-3a']
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect',n]))[0]
def main():
    assert not (E/'deployment-before.json').exists(),'No blind repeat deployment'
    assert '83 passed' in (E/'tests-suppression-3a-v2.log').read_text()
    assert json.loads((E/'before-acceptance.json').read_text())['old_tenant_ledger_runs']==0
    before=inspect('socai2-agents-1');assert before['Image']==BASE and inspect('socai2-agents:policy-2b-20261020')['Id']==BASE
    subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.agents-suppression-3a','-t','socai2-agents:suppression-3a-20261020','.'],cwd=R/'source',check=True)
    with (E/'deployment-before.json').open('x') as f:json.dump({'id':before['Id'],'image':before['Image'],'mounts':before['Mounts'],'env_sha256':hashlib.sha256(json.dumps(sorted(before['Config']['Env'])).encode()).hexdigest()},f,indent=2)
    cmd=['docker','compose','--project-directory',str(R)]
    for part in PARTS:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    subprocess.run(cmd+['config','--quiet'],check=True);subprocess.run(cmd+['up','-d','--no-deps','--pull','never','agents'],check=True,capture_output=True)
    for _ in range(45):
        x=inspect('socai2-agents-1')
        if x['State'].get('Health',{}).get('Status')=='healthy':break
        time.sleep(1)
    else:raise RuntimeError('Agents unhealthy')
    assert x['Mounts']==before['Mounts'] and sorted(x['Config']['Env'])==sorted(before['Config']['Env'])
    result={'id':x['Id'],'image':x['Image'],'healthy':True,'env_and_mounts_unchanged':True,'only_recreated_service':'agents','schema_changed':False}
    with (E/'deployment.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':main()
