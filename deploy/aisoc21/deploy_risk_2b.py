"""Guarded one-file risk fix; recreate only Fusion after relevant checks."""
from pathlib import Path
import hashlib,json,subprocess,time
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2b-risk-20261020'
BASE='sha256:92b0f0696b5fcd5b581b7e409f6a7917d10893396596b3c619fcadc2a779534d'
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect',n]))[0]
def main():
    assert not (E/'deployment-before.json').exists(),'Review retained journal, no blind deployment'
    assert '40 passed' in (E/'tests-after-v2.log').read_text()
    assert json.loads((E/'redis-acceptance.json').read_text())['final_unique_count']==65
    assert json.loads((E/'main/before-acceptance.json').read_text())['expected_defect_reproduced']
    before=inspect('socai2-fusion-1');assert before['Image']==BASE
    assert inspect('socai2-fusion:identity-2a-20261020')['Id']==BASE
    subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.fusion-risk-2b','-t','socai2-fusion:risk-2b-20261020','.'],cwd=R/'source',check=True)
    safe={'id':before['Id'],'image':before['Image'],'env_sha256':hashlib.sha256(json.dumps(sorted(before['Config']['Env'])).encode()).hexdigest(),'mounts':before['Mounts']}
    with (E/'deployment-before.json').open('x') as f:json.dump(safe,f,indent=2)
    cmd=['docker','compose','--project-directory',str(R)]
    for part in ['services','embedding','gateway','investigation','correlation-2a','identity-2a','risk-2b']:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    subprocess.run(cmd+['config','--quiet'],check=True)
    subprocess.run(cmd+['up','-d','--no-deps','--pull','never','fusion'],check=True,capture_output=True)
    for _ in range(45):
        after=inspect('socai2-fusion-1')
        if after['State'].get('Health',{}).get('Status')=='healthy':break
        time.sleep(1)
    else:raise RuntimeError('Fusion unhealthy; inspect journal before any input')
    assert sorted(before['Config']['Env'])==sorted(after['Config']['Env']) and before['Mounts']==after['Mounts']
    result={'container_id':after['Id'],'image':after['Image'],'healthy':True,'environment_and_mounts_unchanged':True,'only_service_recreated':'fusion','schema_change':False}
    with (E/'deployment.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':main()
