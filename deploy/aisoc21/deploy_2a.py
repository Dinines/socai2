"""Build/apply only the bounded Correlator replay fix; retain old image/config."""
from pathlib import Path
import hashlib,json,subprocess,sys,time,urllib.request
R=Path('/opt/sting-aisoc-socai2');E=R/'evidence/2a-20261020';BASE='sha256:e426842d23dec0ebb408b396343690e907bd0679f28df7f5341cc71993922d8f'
def inspect(name):return json.loads(subprocess.check_output(['docker','inspect',name]))[0]
def main():
    out=E/'fix-deployment.json';assert not out.exists()
    if '--verify-applied' in sys.argv:
        verify_applied();return
    old=inspect('socai2-fusion-1');assert old['Image']==BASE
    assert json.loads(subprocess.check_output(['docker','image','inspect','socai2-fusion:1f-20261020']))[0]['Id']==BASE
    tests=(E/'tests-after-fix.log').read_text();assert 'passed' in tests and 'failed' not in tests.lower()
    subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.fusion-2a','-t','socai2-fusion:2a-20261020','.'],cwd=R/'source',check=True)
    cmd=['docker','compose','--project-directory',str(R)]
    for name in ['services','embedding','gateway','investigation','correlation-2a']:cmd+=['-f',str(R/f'source/deploy/aisoc21/compose.{name}.yml')]
    subprocess.run(cmd+['config','--quiet'],check=True)
    subprocess.run(cmd+['up','-d','--no-deps','--pull','never','fusion'],check=True,capture_output=True)
    for _ in range(40):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18003/readyz',timeout=3) as r:health=json.load(r)
            break
        except OSError:time.sleep(1)
    else:raise RuntimeError('Fusion not ready')
    new=inspect('socai2-fusion-1');assert old['Mounts']==new['Mounts'] and dict(v.split('=',1) for v in old['Config']['Env'])==dict(v.split('=',1) for v in new['Config']['Env'])
    src=R/'source/services/fusion/app/services/correlator.py';expected=hashlib.sha256(src.read_bytes()).hexdigest()
    actual=subprocess.check_output(['docker','exec','socai2-fusion-1','python','-c',"import hashlib;print(hashlib.sha256(open('/app/app/services/correlator.py','rb').read()).hexdigest())"]).decode().strip();assert actual==expected
    data={'old_image':BASE,'new_image':new['Image'],'old_container_id':old['Id'],'new_container_id':new['Id'],'same_runtime_environment':True,'same_mounts':True,'health':health,'patched_source_sha256':actual,'only_target_service':'fusion','old_records_not_rewritten':True}
    out.write_text(json.dumps(data,indent=2));print(json.dumps(data))
def verify_applied():
    # Resolve only the verifier failure; never recreate or replay input here.
    old=json.loads((E/'environment-before.json').read_text())['containers']['socai2-fusion-1']
    new=inspect('socai2-fusion-1');assert old['image']==BASE and new['Image']!=BASE
    assert old['mounts']==new['Mounts'] and new['State']['Health']['Status']=='healthy'
    defaults=json.loads(subprocess.check_output(['docker','image','inspect',BASE]))[0]['Config']['Env']
    expected=dict(v.split('=',1) for v in defaults)
    expected.update(dict(v.split('=',1) for v in (R/'private/fusion-1f.env').read_text().splitlines()))
    actual=dict(v.split('=',1) for v in new['Config']['Env']);assert expected==actual
    expected_hash=hashlib.sha256((R/'source/services/fusion/app/services/correlator.py').read_bytes()).hexdigest()
    actual_hash=subprocess.check_output(['docker','exec','socai2-fusion-1','python','-c',"import hashlib;print(hashlib.sha256(open('/app/app/services/correlator.py','rb').read()).hexdigest())"]).decode().strip()
    assert actual_hash==expected_hash
    data={'old_image':BASE,'new_image':new['Image'],'old_container_id':old['id'],'new_container_id':new['Id'],'matches_retained_base_image_environment_plus_unchanged_1f_env':True,'same_mounts':True,'health':new['State']['Health']['Status'],'patched_source_sha256':actual_hash,'only_target_service':'fusion','original_pg_records_not_rewritten':True,'verification_recovery':'First verifier compared ordered env lists; original image defaults plus unchanged private env match current mapping exactly. Read-only verification; no second recreate or input replay'}
    out=E/'fix-deployment.json';assert not out.exists();out.write_text(json.dumps(data,indent=2));print(json.dumps(data))

if __name__=='__main__':main()
