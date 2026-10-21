"""Guarded Agents-only prompt revision after two pre-model budget stops."""
from pathlib import Path
import hashlib,json,subprocess,time
from deploy_kb_read_3a import R,E,PARTS,inspect,describe,env_values,BASE


def save(name,value):
    with (E/name).open('x') as stream:json.dump(value,stream,indent=2)
    (E/name).chmod(0o600)


def main():
    assert (E/'deployment.json').exists() and (E/'budget-preflight-resumed.json').exists()
    assert not (E/'model-call-started.json').exists() and not (E/'prompt-revision-before.json').exists()
    assert json.loads((E/'model-prompt-budget-preflight.json').read_text())['literal_chars']==8717
    assert json.loads((E/'budget-preflight-resumed.json').read_text())['literal_chars']==8105
    tests={name:json.loads((E/('tests-'+name+'-'+attempt+'.json')).read_text()) for name,attempt in [('api','initial'),('agents','prompt-v3')]}
    assert tests['api']['passed']==38 and tests['agents']['passed']==198
    hashes={path:digest for item in tests.values() for path,digest in item['tested_runtime_source_sha256'].items()}
    assert all(item['exit_code']==0 and item['runtime_source_unchanged_during_tests'] for item in tests.values())
    for path,digest in hashes.items():assert hashlib.sha256((R/'source'/path).read_bytes()).hexdigest()==digest,path
    current={name:inspect('socai2-'+name+'-1') for name in ['api','agents','fusion','actions']}
    assert current['api']['Image']=='sha256:95ed232be35add623cbee01595a623df1b0b64715f534d54814502bf57150350'
    assert current['agents']['Image']=='sha256:dd6b9ac8777b1ca2a7062261b64062a7279a270173e5273f956e015a5d46e902'
    assert inspect('socai2-agents:tenant-skill-3a-20261020')['Id']==BASE['agents']
    old=json.loads((E/'tests-acceptance.json').read_text())
    save('tests-acceptance-v1.json',old)
    save('tests-acceptance-prompt-v2.json',{'api_passed':38,'agents_passed':198,'failed':0,'attempts':{'api':'initial','agents':'prompt-v3'},'tested_runtime_source_sha256':hashes})
    save('prompt-revision-before.json',{name:describe(item) for name,item in current.items()})
    subprocess.run(['docker','build','--pull=false','-f','deploy/aisoc21/build/Dockerfile.agents-kb-read-3a','-t','socai2-agents:kb-read-3a-20261020','.'],cwd=R/'source',check=True)
    built=inspect('socai2-agents:kb-read-3a-20261020')['Id']
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
    # Keep the first accepted test material under a versioned name, then
    # publish the latest tested hashes used for this final running source.
    (E/'tests-acceptance.json').write_bytes((E/'tests-acceptance-prompt-v2.json').read_bytes())
    result={'only_recreated':['agents'],'api_fusion_actions_unchanged':True,'images':{'before':current['agents']['Image'],'after':built},'env_and_mounts_unchanged':True,'production_dependencies_or_schema_changed':False,'same_15_compose_layers':True,'runtime_change':'Only equivalent compact KB inline boundary note; all guard/nonce/standing-system controls and8000cap retained','tested_api':38,'tested_agents':198,'new_alerts':0,'new_model_calls':0}
    save('prompt-revision-deployment.json',result);print(json.dumps(result))


if __name__=='__main__':main()
