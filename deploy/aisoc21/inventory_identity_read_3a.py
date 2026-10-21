"""Read-only graph capability/ownership inventory; no schema or business writes."""
from pathlib import Path
import hashlib, json, os, subprocess

R = Path('/opt/sting-aisoc-socai2')
E = R/'evidence/3a-identity-read-20261020'


def save(name, value):
    with (E/name).open('x') as stream: json.dump(value, stream, indent=2, default=str)
    (E/name).chmod(0o600)


def main():
    os.umask(0o077); E.mkdir(mode=0o700, exist_ok=True)
    assert not (E/'graph-inventory.json').exists()
    listed=json.loads(subprocess.check_output(['docker','inspect',*subprocess.check_output(['docker','ps','-aq']).decode().split()]))
    matches=[item for item in listed if 'neo4j' in item['Config']['Image'].lower()]
    assert len(matches)==1
    item=matches[0]; values=dict(value.split('=',1) for value in item['Config']['Env'] if '=' in value)
    user,password=values['NEO4J_AUTH'].split('/',1)
    assert user and password and password!='none'
    path=R/'private/identity-graph-inventory-3a.env';assert not path.exists()
    with path.open('x') as stream:
        stream.write('NEO4J_URI=bolt://192.168.1.21:7687\nNEO4J_USER='+user+'\nNEO4J_PASSWORD='+password+'\n')
    path.chmod(0o600)
    save('graph-container-before.json',{'name':item['Name'],'id':item['Id'],'image':item['Image'],
        'image_ref':item['Config']['Image'],'mounts':item['Mounts'],'state':item['State'],
        'ports':item['NetworkSettings']['Ports'],'env_sha256':hashlib.sha256(json.dumps(sorted(item['Config']['Env'])).encode()).hexdigest(),
        'credential_source':'existing container controlled NEO4J_AUTH; no value exported to public evidence'})
    code='''import asyncio,json,os,pathlib
from neo4j import AsyncGraphDatabase,READ_ACCESS
async def main():
 d=AsyncGraphDatabase.driver(os.environ['NEO4J_URI'],auth=(os.environ['NEO4J_USER'],os.environ['NEO4J_PASSWORD']))
 out={'read_only_queries':True,'source':'existing shared graph','uri':os.environ['NEO4J_URI']}
 async with d.session(database='neo4j',default_access_mode=READ_ACCESS) as s:
  queries={
   'components':'CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition',
   'database':'SHOW DATABASES YIELD name,currentStatus,default RETURN name,currentStatus,default',
   'current_user':'SHOW CURRENT USER YIELD user,roles RETURN user,roles',
   'nodes_by_labels':'MATCH (n) RETURN labels(n) AS labels,count(*) AS count ORDER BY labels',
   'relations_by_type':'MATCH ()-[r]->() RETURN type(r) AS type,count(*) AS count ORDER BY type',
   'identity_tenant_counts':'MATCH (n) WHERE n:Identity OR n:Employee OR n:Department RETURN labels(n) AS labels,n.tenant_id IS NULL AS tenant_missing,count(*) AS count ORDER BY labels,tenant_missing',
   'indexes':'SHOW INDEXES YIELD name,type,entityType,labelsOrTypes,properties,state RETURN name,type,entityType,labelsOrTypes,properties,state ORDER BY name',
   'constraints':'SHOW CONSTRAINTS YIELD name,type,entityType,labelsOrTypes,properties RETURN name,type,entityType,labelsOrTypes,properties ORDER BY name',
   'type_syntax':"RETURN valueType(datetime()) AS native_type,valueType('bad-date') AS text_type,datetime() IS :: ZONED DATETIME AS native_is_datetime",
  }
  for key,query in queries.items():
   try:
    r=await s.run(query);out[key]=[dict(row) async for row in r]
   except Exception as exc:out[key]={'error_type':type(exc).__name__,'code':getattr(exc,'code',None)}
 await d.close()
 path=pathlib.Path('/evidence/graph-inventory.json')
 with path.open('x') as f:json.dump(out,f,indent=2,default=str)
 path.chmod(0o600);print(json.dumps(out))
asyncio.run(main())'''
    command=['docker','run','--rm','--network','socai2_default','--env-file',str(path),
        '-v',str(E)+':/evidence','socai2-api:dispositions-3a-20261020','python','-c',code]
    result=subprocess.run(command,text=True,capture_output=True)
    (E/'graph-inventory-operator.log').write_text(result.stdout+result.stderr)
    (E/'graph-inventory-operator.log').chmod(0o600)
    assert result.returncode==0,'Read controlled log; do not mutate the shared graph to make inventory pass'
    print(result.stdout)


if __name__=='__main__':main()
