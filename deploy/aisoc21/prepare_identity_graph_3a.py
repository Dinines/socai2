"""Seed only marked synthetic graph objects; keep the shared schema and prior objects."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json, os, subprocess

R=Path('/opt/sting-aisoc-socai2'); E=R/'evidence/3a-identity-read-20261020'; B='3a-identity-read-20261020'


def save(name,value):
    with (E/name).open('x') as stream:json.dump(value,stream,indent=2)
    (E/name).chmod(0o600)


def fixtures():
    prior=json.loads((R/'private/app-dispositions-3a.json').read_text())
    tenants={alias:prior['identities'][alias]['tenant_id'] for alias in ['a','b']}
    now=datetime.now(timezone.utc); nodes=[];edges=[]
    def node(alias,tenant,label,**props):
        native=props.pop('native_stamp',False)
        nodes.append({'alias':alias,'labels':[label],'props':{'id':B+'/'+alias,'tenant_id':tenants[tenant],'batch':B,**props},'native_stamp':native})
    def edge(origin,target,kind):edges.append({'from':origin,'to':target,'type':kind,'batch':B})
    old=(now-timedelta(days=2)).isoformat()
    for tenant in ['a','b']:
        node(tenant+'-identity',tenant,'Identity',external_id='svc-identity-a',provider='synthetic-directory')
        node(tenant+'-employee',tenant,'Employee',display_name='Synthetic '+tenant.upper()+' account owner',title='Test service owner',is_active=tenant=='a',employment_type='service',start_date='2025-01-01',end_date=None if tenant=='a' else '2025-12-31',updated_at=old,native_stamp=True)
        node(tenant+'-department',tenant,'Department',name='Synthetic '+tenant.upper()+' operations')
        node(tenant+'-manager',tenant,'Employee',display_name='Synthetic '+tenant.upper()+' manager',email='manager-'+tenant+'@test.invalid',updated_at=old,native_stamp=True)
        edge(tenant+'-employee',tenant+'-identity','AUTHENTICATES_AS');edge(tenant+'-employee',tenant+'-department','BELONGS_TO');edge(tenant+'-manager',tenant+'-employee','MANAGES')
    node('a-cutoff-identity','a','Identity',external_id='svc-identity-cutoff',provider='synthetic-directory')
    # Late and unknown paths sort before the eligible old one. Filtering
    # after LIMIT 1 would incorrectly hide that old path.
    for suffix,hours in [('00-late',12),('01-late',6),('02-late',3)]:
        alias='a-cutoff-'+suffix;node(alias,'a','Employee',display_name='Synthetic later import',is_active=True,updated_at=(now-timedelta(hours=hours)).isoformat(),native_stamp=True);edge(alias,'a-cutoff-identity','AUTHENTICATES_AS')
    for suffix,value in [('30-missing',None),('31-text',old),('32-bad','not-a-date')]:
        alias='a-cutoff-'+suffix;node(alias,'a','Employee',display_name='Synthetic unverifiable import',is_active=None,updated_at=value);edge(alias,'a-cutoff-identity','AUTHENTICATES_AS')
    node('a-cutoff-90-early','a','Employee',display_name='Synthetic old import',is_active=False,updated_at=old,native_stamp=True);edge('a-cutoff-90-early','a-cutoff-identity','AUTHENTICATES_AS')
    node('a-unlinked','a','Identity',external_id='svc-identity-unlinked',provider='synthetic-directory')
    for provider in ['one','two']:
        identity='a-multi-identity-'+provider;node(identity,'a','Identity',external_id='svc-identity-multi',provider='synthetic-'+provider)
        for suffix in (['one','two'] if provider=='one' else ['three']):
            alias='a-multi-employee-'+suffix;node(alias,'a','Employee',display_name='Synthetic provider association '+suffix,is_active=None,updated_at=old,native_stamp=True);edge(alias,identity,'AUTHENTICATES_AS')
    node('a-cross-identity','a','Identity',external_id='svc-identity-cross',provider='synthetic-directory')
    for alias in ['a-cross-identity','b-employee','b-department']:
        next(item for item in nodes if item['alias']==alias)['labels'].append('Technique')
    edge('b-employee','a-cross-identity','AUTHENTICATES_AS');edge('a-employee','b-department','BELONGS_TO');edge('b-employee','a-employee','MANAGES')
    node('a-history-identity','a','Identity',external_id='svc-identity-history',provider='synthetic-directory')
    node('a-history-employee','a','Employee',display_name='Synthetic history owner',is_active=True,updated_at=old,native_stamp=True)
    node('a-history-department','a','Department',name='Synthetic history department v1')
    node('a-history-manager','a','Employee',display_name='Synthetic history manager v1',updated_at=old,native_stamp=True)
    edge('a-history-employee','a-history-identity','AUTHENTICATES_AS');edge('a-history-employee','a-history-department','BELONGS_TO');edge('a-history-manager','a-history-employee','MANAGES')
    return {'batch':B,'created_at':now.isoformat(),'split_at':(now-timedelta(days=1)).isoformat(),'tenants':tenants,
        'model_account':'svc-identity-a','cutoff_account':'svc-identity-cutoff','unlinked_account':'svc-identity-unlinked','multi_account':'svc-identity-multi','cross_account':'svc-identity-cross','history_account':'svc-identity-history',
        'nodes':nodes,'edges':edges,'node_count':len(nodes),'relationship_count':len(edges),
        'expected_frozen_cutoff':{'candidate_count':7,'eligible_count':1,'excluded_after_cutoff':3,'excluded_unverifiable_import':3,'import_timestamp_missing':1},
        'synthetic_read_fixture_not_hr_sync_or_historical_authorization':True}


def main():
    os.umask(0o077)
    assert not (E/'graph-fixtures.json').exists() and (E/'graph-inventory.json').exists()
    inventory=json.loads((E/'graph-inventory.json').read_text());assert inventory['nodes_by_labels']==inventory['relations_by_type']==[]
    credential=dict(line.split('=',1) for line in (R/'private/identity-graph-inventory-3a.env').read_text().splitlines() if '=' in line)
    directory=R/'private/identity-graph-3a';assert not directory.exists();directory.mkdir(mode=0o700)
    config={'uri':credential['NEO4J_URI'],'username':credential['NEO4J_USER'],'password':credential['NEO4J_PASSWORD'],'database':'neo4j'}
    path=directory/'config.json'
    with path.open('x') as stream:json.dump(config,stream,indent=2)
    path.chmod(0o600);os.chown(path,10001,10001);os.chown(directory,10001,10001)
    material=fixtures();save('graph-fixtures.json',material)
    code='''import asyncio,hashlib,json,os,pathlib
from datetime import datetime
from neo4j import AsyncGraphDatabase,READ_ACCESS
E=pathlib.Path('/evidence');f=json.loads((E/'graph-fixtures.json').read_text());B=f['batch']
def save(name,value):
 with (E/name).open('x') as stream:json.dump(value,stream,indent=2,default=str)
 (E/name).chmod(0o600)
async def snapshot(s):
 async def rows(query):
  r=await s.run(query);return [dict(row) async for row in r]
 return {'nodes':await rows('MATCH(n) RETURN elementId(n) AS element_id,labels(n) AS labels,properties(n) AS props ORDER BY n.id,element_id'),
         'relationships':await rows('MATCH(a)-[r]->(b) RETURN elementId(r) AS element_id,a.id AS origin,b.id AS target,type(r) AS type,properties(r) AS props ORDER BY origin,type,target,element_id'),
         'indexes':await rows('SHOW INDEXES YIELD name,type,entityType,labelsOrTypes,properties,state RETURN name,type,entityType,labelsOrTypes,properties,state ORDER BY name'),
         'constraints':await rows('SHOW CONSTRAINTS YIELD name,type,entityType,labelsOrTypes,properties RETURN name,type,entityType,labelsOrTypes,properties ORDER BY name')}
async def main():
 async with AsyncGraphDatabase.driver(os.environ['NEO4J_URI'],auth=(os.environ['NEO4J_USER'],os.environ['NEO4J_PASSWORD'])) as d:
  async with d.session(database='neo4j') as s:
   before=await snapshot(s);assert not before['nodes'] and not before['relationships'];save('graph-material-before.json',before)
   tx=await s.begin_transaction()
   try:
    for node in f['nodes']:
     props=dict(node['props'])
     if node['native_stamp']:props['updated_at']=datetime.fromisoformat(props['updated_at'])
     assert set(node['labels'])<={'Identity','Employee','Department','Technique'}
     r=await tx.run('CREATE(n:'+':'.join(node['labels'])+') SET n=$props RETURN n.id AS id',props=props);row=await r.single();assert row['id']==props['id']
    for edge in f['edges']:
     assert edge['type'] in {'AUTHENTICATES_AS','BELONGS_TO','MANAGES'}
     r=await tx.run('MATCH(a {id:$origin,batch:$batch}),(b {id:$target,batch:$batch}) CREATE(a)-[r:'+edge['type']+' {batch:$batch}]->(b) RETURN count(r) AS count',origin=B+'/'+edge['from'],target=B+'/'+edge['to'],batch=B);row=await r.single();assert row['count']==1
    await tx.commit()
   except BaseException:
    await tx.rollback();raise
   after=await snapshot(s);assert len(after['nodes'])==f['node_count'] and len(after['relationships'])==f['relationship_count']
   assert after['indexes']==before['indexes'] and after['constraints']==before['constraints'];save('graph-material-seeded.json',after)
  # This tests this driver's access mode, not a database-enforced role.
  async with d.session(database='neo4j',default_access_mode=READ_ACCESS) as s:
   tx=await s.begin_transaction();out={'database_read_only_role_claimed':False,'shared_credential_is_privileged':True,'write_committed':False}
   try:
    r=await tx.run('MATCH(e:Employee {id:$id,batch:$batch}) SET e.title=$title RETURN e.id AS id',id=B+'/a-employee',batch=B,title='probe-only value, must never persist');await r.consume()
    out['write_query_rejected']=False
   except Exception as exc:out.update(write_query_rejected=True,error_type=type(exc).__name__,code=getattr(exc,'code',None))
   finally:await tx.rollback()
   save('graph-read-access-mode.json',out)
  async with d.session(database='neo4j',default_access_mode=READ_ACCESS) as s:
   final=await snapshot(s);assert final==after
  save('graph-seed-result.json',{'nodes':len(final['nodes']),'relationships':len(final['relationships']),'schema_unchanged':True,'prior_nodes':0,'prior_relationships':0,'only_marked_synthetic_objects_added':True,'native_imports_are_not_business_effective_dates':True})
 print(json.dumps({'nodes':f['node_count'],'relationships':f['relationship_count'],'schema_changed':False,'read_access_mode':out}))
asyncio.run(main())'''
    command=['docker','run','--rm','--user','0','--network','socai2_default','--env-file',str(R/'private/identity-graph-inventory-3a.env'),'-v',str(E)+':/evidence','socai2-api:dispositions-3a-20261020','python','-c',code]
    result=subprocess.run(command,text=True,capture_output=True)
    (E/'graph-seed-operator.log').write_text(result.stdout+result.stderr);(E/'graph-seed-operator.log').chmod(0o600)
    assert result.returncode==0,'Inspect graph-seed checkpoint; never blindly recreate marked graph objects'
    print(result.stdout)


if __name__=='__main__':main()
