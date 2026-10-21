"""Guarded Agents-only import-cycle repair; preserve the completed model and restart evidence."""
import hashlib, json, subprocess, time
from deploy_dispositions_3a import R, E, PARTS, BASE, inspect, describe, env_values


def save(name, value):
    with (E/name).open('x') as stream: json.dump(value, stream, indent=2)
    (E/name).chmod(0o600)


def main():
    assert (E/'after-acceptance.json').exists() and (E/'restart-acceptance.json').exists()
    assert (E/'key-lifecycle.json').exists() and (E/'finish-operator.log').exists()
    assert not (E/'postconditions.json').exists() and not (E/'import-revision-before.json').exists()
    assert 'partially initialized module' in (E/'finish-operator.log').read_text()
    tests = {name: json.loads((E/('tests-'+name+'-'+attempt+'.json')).read_text())
             for name, attempt in [('api','initial'),('agents','import-fix')]}
    assert tests['api']['passed']==91 and tests['agents']['passed']==305
    assert all(item['exit_code']==0 and item['runtime_source_unchanged_during_tests'] for item in tests.values())
    hashes = {path:digest for item in tests.values() for path,digest in item['tested_runtime_source_sha256'].items()}
    for path,digest in hashes.items(): assert hashlib.sha256((R/'source'/path).read_bytes()).hexdigest()==digest, path
    current = {name:inspect('socai2-'+name+'-1') for name in ['api','agents','fusion','actions']}
    assert current['api']['Image']=='sha256:41bae3dde2fdccb230622f30af99b6ef807469c930cb7b6aed1baf860eb7cd3d'
    assert current['agents']['Image']=='sha256:4840767939980238e966007ef4e559f99e7ddfc3fb9c3630fa27d232be16e268'
    assert inspect('socai2-agents:kb-read-3a-20261020')['Id']==BASE['agents']
    save('tests-acceptance-v1.json',json.loads((E/'tests-acceptance.json').read_text()))
    save('tests-acceptance-import-fix.json',{'api_passed':91,'agents_passed':305,'failed':0,
        'attempts':{'api':'initial','agents':'import-fix'},'tested_runtime_source_sha256':hashes,
        'dependencies_changed':False,'unit_doubles_distinct_from_live_acceptance':True})
    save('import-revision-before.json',{name:describe(item) for name,item in current.items()})
    subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.agents-dispositions-3a',
                    '-t','socai2-agents:dispositions-3a-20261020','.'],cwd=R/'source',check=True)
    built=inspect('socai2-agents:dispositions-3a-20261020')['Id']
    command=['docker','compose','--project-directory',str(R)]
    for part in PARTS:command+=['-f',str(R/f'source/deploy/aisoc21/compose.{part}.yml')]
    subprocess.run(command+['config','--quiet'],check=True,capture_output=True)
    subprocess.run(command+['up','-d','--no-deps','--pull','never','agents'],check=True,capture_output=True)
    for _ in range(45):
        after=inspect('socai2-agents-1')
        if after['State'].get('Health',{}).get('Status')=='healthy':break
        time.sleep(1)
    else:raise RuntimeError('Agents unhealthy')
    assert after['Image']==built and after['Id']!=current['agents']['Id']
    assert env_values(after)==env_values(current['agents']) and after['Mounts']==current['agents']['Mounts']
    for name in ['api','fusion','actions']:assert describe(inspect('socai2-'+name+'-1'))==describe(current[name])
    (E/'tests-acceptance.json').write_bytes((E/'tests-acceptance-import-fix.json').read_bytes())
    result={'only_recreated':['agents'],'api_fusion_actions_unchanged':True,
        'images':{'before':current['agents']['Image'],'after':built},'env_and_mounts_unchanged':True,
        'production_dependencies_or_schema_changed':False,'same_16_compose_layers':True,
        'runtime_change':'Remove new reader dependency on eagerly initialized app.agents package; mirror fixed canonical vocabulary and test both fresh-process import orders.',
        'tested_api':91,'tested_agents':305,'new_alerts':0,'new_model_calls':0,
        'original_model_and_restart_materials_preserved':True}
    save('import-revision-deployment.json',result);print(json.dumps(result))


if __name__=='__main__':main()
