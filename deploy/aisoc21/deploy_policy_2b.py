"""Build only three changed runtime files, recreate API/Agents, keep flags."""
from pathlib import Path
import hashlib,json,subprocess,time
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2b-policy-20261020'
BASE={'api':('identity-2a-20261020','sha256:d758d6062c613a8fd0dcc9e5d061faf65d6b6974a19a99b39c82298a6595de4c'),'agents':('1g-20261020','sha256:3d92fa4e77083c4c6d9bf237634243446ca22eac8b0601ea4727cdd3a90b992c')}
PARTS=['services','embedding','gateway','investigation','correlation-2a','identity-2a','risk-2b','policy-2b']
def inspect(n):return json.loads(subprocess.check_output(['docker','inspect',n]))[0]
def command():
    cmd=['docker','compose','--project-directory',str(R)]
    for part in PARTS:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    return cmd
def main():
    assert not (E/'deployment-before.json').exists(),'Do not repeat deployment; inspect journal'
    assert '42 passed' in (E/'api-after.log').read_text() and '41 passed' in (E/'agents-after.log').read_text()
    assert json.loads((E/'before-acceptance.json').read_text())['stable_content_revision_absent']
    before={}
    for name,(tag,digest) in BASE.items():
        x=inspect('socai2-'+name+'-1');assert x['Image']==digest and inspect('socai2-'+name+':'+tag)['Id']==digest
        before[name]=x
        subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.'+name+'-policy-2b','-t','socai2-'+name+':policy-2b-20261020','.'],cwd=R/'source',check=True)
    with (E/'deployment-before.json').open('x') as f:json.dump({n:{'id':x['Id'],'image':x['Image'],'mounts':x['Mounts'],'env_sha256':hashlib.sha256(json.dumps(sorted(x['Config']['Env'])).encode()).hexdigest()} for n,x in before.items()},f,indent=2)
    cmd=command();subprocess.run(cmd+['config','--quiet'],check=True);results={}
    for name in ['api','agents']:
        subprocess.run(cmd+['up','-d','--no-deps','--pull','never',name],check=True,capture_output=True)
        for _ in range(45):
            x=inspect('socai2-'+name+'-1')
            if x['State'].get('Health',{}).get('Status')=='healthy':break
            time.sleep(1)
        else:raise RuntimeError('Unhealthy '+name)
        assert x['Mounts']==before[name]['Mounts'] and sorted(x['Config']['Env'])==sorted(before[name]['Config']['Env'])
        results[name]={'image':x['Image'],'id':x['Id'],'env_and_mounts_unchanged':True,'healthy':True}
        with (E/(name+'-deployment.json')).open('x') as f:json.dump(results[name],f,indent=2)
    with (E/'deployment.json').open('x') as f:json.dump(results,f,indent=2)
    print(json.dumps(results))
if __name__=='__main__':main()
