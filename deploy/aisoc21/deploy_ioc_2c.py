"""Update only API/Fusion; enable local IOC evidence, no external provider."""
from pathlib import Path
import hashlib,json,subprocess,time
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2c-ioc-20261020'
BASE={'api':('policy-2b-20261020','sha256:f88bbcc9579727a8f81acf4e2fb2168485230d7889602943d46e13d711acde54'),'fusion':('risk-2b-20261020','sha256:6ff2a029253adc4301ee8e645ae9fecea218bd592078caf70c94b7de1b3fa3fd')}
PARTS=['services','embedding','gateway','investigation','correlation-2a','identity-2a','risk-2b','policy-2b','ioc-2c']
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect',n]))[0]
def main():
    assert not (E/'deployment-before.json').exists(),'No blind repeat deployment'
    assert '43 passed' in (E/'tests-fusion-v2.log').read_text() and '19 passed' in (E/'tests-api.log').read_text()
    before={}
    for n,(tag,digest) in BASE.items():
        x=inspect('socai2-'+n+'-1');assert x['Image']==digest and inspect('socai2-'+n+':'+tag)['Id']==digest;before[n]=x
        subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.'+n+'-ioc-2c','-t','socai2-'+n+':ioc-2c-20261020','.'],cwd=R/'source',check=True)
    with (E/'deployment-before.json').open('x') as f:json.dump({n:{'id':x['Id'],'image':x['Image'],'mounts':x['Mounts'],'env_sha256':hashlib.sha256(json.dumps(sorted(x['Config']['Env'])).encode()).hexdigest()} for n,x in before.items()},f,indent=2)
    cmd=['docker','compose','--project-directory',str(R)]
    for part in PARTS:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    subprocess.run(cmd+['config','--quiet'],check=True);results={}
    for n in ['api','fusion']:
        subprocess.run(cmd+['up','-d','--no-deps','--pull','never',n],check=True,capture_output=True)
        for _ in range(45):
            x=inspect('socai2-'+n+'-1')
            if x['State'].get('Health',{}).get('Status')=='healthy':break
            time.sleep(1)
        else:raise RuntimeError('Unhealthy '+n)
        expected=dict(v.split('=',1) for v in before[n]['Config']['Env'])
        if n=='fusion':expected.update(AISOC_FUSE_ENRICHMENT='true',AISOC_TENANT_IOC_MATCH='1',ENRICHMENT_SERVICE_URL='')
        assert expected==dict(v.split('=',1) for v in x['Config']['Env']) and x['Mounts']==before[n]['Mounts']
        results[n]={'id':x['Id'],'image':x['Image'],'healthy':True,'only_expected_env_change':n=='fusion','mounts_preserved':True}
        with (E/(n+'-deployment.json')).open('x') as f:json.dump(results[n],f,indent=2)
    with (E/'deployment.json').open('x') as f:json.dump(results,f,indent=2)
    print(json.dumps(results))
if __name__=='__main__':main()
