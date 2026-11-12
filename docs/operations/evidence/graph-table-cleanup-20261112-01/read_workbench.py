import json,pathlib,subprocess,shlex,sys
p=pathlib.Path('docs/operations/evidence/graph-table-cleanup-20261112-01');cfg=json.loads((p/'workbench-profile.json').read_text())['deployment'];sqlcfg=json.loads((p/'profile.json').read_text())
code="""import sys,json,urllib.request
from uuid import UUID
sys.path.insert(0,'/opt/workbench/docs/operations')
import processing_workbench_source as s
from read_processing_audit_20261106 import TABLES
assert len(TABLES)==28 and 'graph_explorations' not in TABLES
listing=s.list_cases('aisoc',s.DEFAULT_PRODUCTION_TENANT)
assert listing['cases']
cid=UUID(listing['cases'][0]['case_id'])
at,data,revision=s.read_case_if_changed('aisoc',s.DEFAULT_PRODUCTION_TENANT,cid)
assert set(data)==set(TABLES) and data['cases'] and data['runs'] and data['artifacts']
urls=['http://127.0.0.1:4177/','http://127.0.0.1:4177/_workbench/status','http://127.0.0.1:4177/_workbench/cases']
statuses=[urllib.request.urlopen(u,timeout=10).status for u in urls]
assert statuses==[200]*3
print(json.dumps({'tables':len(data),'graph_queried':False,'case_rows':len(data['cases']),'run_rows':len(data['runs']),'artifact_rows':len(data['artifacts']),'case_list_rows':len(listing['cases']),'http_statuses':statuses,'read_only':True,'model_calls':0}))
"""
argv=[cfg['ssh_binary'],'-T','-o','BatchMode=yes','-o','ConnectTimeout='+str(cfg['connect_timeout_seconds']),cfg['ssh_target'],shlex.join([cfg['docker'],'exec','-i',cfg['container'],'python','-B','-'])]
r=subprocess.run(argv,input=code,capture_output=True,text=True,timeout=sqlcfg['timeout_seconds']);assert r.returncode==0,r.stderr
obj=json.loads(r.stdout);(p/(sys.argv[1]+'.json')).write_text(json.dumps(obj,indent=2)+'\n');print(json.dumps(obj))
