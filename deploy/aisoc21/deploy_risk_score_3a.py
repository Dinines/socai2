"""Three services, same env/mounts/DDL; nullable publisher score contract only."""
from pathlib import Path
import hashlib,json,subprocess,time
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/3a-risk-20261020'
BASE={'api':('context-2c','sha256:b77da9c81bc2868cd5d3bd9f21d02e94316d949b441582324fcdd2da5207214c'),'fusion':('ioc-2c','sha256:106b290cd77ab08f8dfe84563b56e248235012c53ad38d0f639b9b4f52dbccd5'),'agents':('suppression-3a','sha256:127036ae1776f95c0bfcf820a33e9d2c151795a4e696c935bca5f42f9754ffc4')}
PARTS=['services','embedding','gateway','investigation','correlation-2a','identity-2a','risk-2b','policy-2b','ioc-2c','context-2c','suppression-3a','risk-score-3a']
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect',n]))[0]
def main():
    assert not (E/'deployment-before.json').exists(),'Inspect prior deployment; no blind replay'
    for name,count in [('agents',112),('fusion',53),('api',19)]:assert f'{count} passed' in (E/f'tests-risk-3a-{name}-final.log').read_text()
    before={}
    for name,(tag,digest) in BASE.items():
        x=inspect('socai2-'+name+'-1');assert x['Image']==digest and inspect(f'socai2-{name}:{tag}-20261020')['Id']==digest
        before[name]={'id':x['Id'],'image':x['Image'],'mounts':x['Mounts'],'env_sha256':hashlib.sha256(json.dumps(sorted(x['Config']['Env'])).encode()).hexdigest()}
        subprocess.run(['docker','build','--pull=false','-f',f'deploy/aisoc21/build/Dockerfile.{name}-risk-score-3a','-t',f'socai2-{name}:risk-score-3a-20261020','.'],cwd=R/'source',check=True)
    (E/'deployment-before.json').write_text(json.dumps(before,indent=2))
    cmd=['docker','compose','--project-directory',str(R)]
    for p in PARTS:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{p}.yml')]
    subprocess.run(cmd+['config','--quiet'],check=True);subprocess.run(cmd+['up','-d','--no-deps','--pull','never',*BASE],check=True,capture_output=True)
    after={}
    for name in BASE:
        for _ in range(45):
            x=inspect('socai2-'+name+'-1')
            if x['State'].get('Health',{}).get('Status')=='healthy':break
            time.sleep(1)
        else:raise RuntimeError('Unhealthy '+name)
        assert x['Mounts']==before[name]['mounts'] and hashlib.sha256(json.dumps(sorted(x['Config']['Env'])).encode()).hexdigest()==before[name]['env_sha256']
        after[name]={'id':x['Id'],'image':x['Image'],'healthy':True}
    (E/'deployment.json').write_text(json.dumps({'services':after,'env_and_mounts_unchanged':True,'schema_or_dependencies_changed':False},indent=2));print(json.dumps(after))
if __name__=='__main__':main()
