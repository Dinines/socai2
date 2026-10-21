"""Apply versioned identity consumer before publisher, preserving private envs."""
from pathlib import Path
import hashlib,json,subprocess,time,urllib.request
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2a-identity-20261020'
BASE={'api':'sha256:480ee56324225c3f7981abbd194eeedb25ed3b763041649fb74adbfad76edbd7','fusion':'sha256:3c1f8f281901175dc4a4439ee2c78915de5604ac89c97869b03122e9e6bbf0c6'}
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect',n]))[0]
def env(x):return dict(v.split('=',1) for v in x['Config']['Env'])
def main():
    assert not (E/'deployment-before.json').exists(),'Inspect retained deployment journal; no blind restart'
    for name,log in [('fusion','tests-fusion.log'),('api','tests-api-detail.log')]:
        text=(E/log).read_text();assert 'passed' in text and 'failed' not in text.lower()
        assert inspect('socai2-'+name+'-1')['Image']==BASE[name]
        assert json.loads(subprocess.check_output(['docker','image','inspect',f'socai2-{name}:'+('1f-20261020' if name=='api' else '2a-20261020')]))[0]['Id']==BASE[name]
        subprocess.run(['docker','build','--pull=false','-f',f'deploy/aisoc21/build/Dockerfile.{name}-identity-2a','-t',f'socai2-{name}:identity-2a-20261020','.'],cwd=R/'source',check=True)
    before={name:inspect('socai2-'+name+'-1') for name in BASE}
    (E/'deployment-before.json').write_text(json.dumps({name:{'id':x['Id'],'image':x['Image'],'env_sha256':hashlib.sha256(json.dumps(env(x),sort_keys=True).encode()).hexdigest(),'mounts':x['Mounts']} for name,x in before.items()},indent=2))
    cmd=['docker','compose','--project-directory',str(R)]
    for part in ['services','embedding','gateway','investigation','correlation-2a','identity-2a']:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    subprocess.run(cmd+['config','--quiet'],check=True);results={}
    for name in ['fusion','api']:
        subprocess.run(cmd+['up','-d','--no-deps','--pull','never',name],check=True,capture_output=True)
        for _ in range(45):
            x=inspect('socai2-'+name+'-1')
            if x['State'].get('Health',{}).get('Status')=='healthy':break
            time.sleep(1)
        else:raise RuntimeError(name+' unhealthy; inspect journal, do not replay work')
        expected=env(before[name]);expected.update({'AISOC_ALERT_IDENTITY_VERSION':'source-v1'} if name=='api' else {})
        assert expected==env(x) and before[name]['Mounts']==x['Mounts']
        result={'image':x['Image'],'container_id':x['Id'],'healthy':True,'only_expected_environment_change':name=='api','same_mounts':True}
        with (E/(name+'-deployment.json')).open('x') as f:json.dump(result,f,indent=2)
        results[name]=result
    (E/'deployment.json').write_text(json.dumps({'order':['fusion','api'],'services':results,'no_schema_change':True},indent=2));print(json.dumps(results))
if __name__=='__main__':main()
