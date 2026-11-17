"""Read-only non-PG inventory; no credentials or record bodies are emitted."""
import json
import subprocess
import sys
from urllib.request import Request, urlopen
from pathlib import Path

c=json.load(sys.stdin)
def command(args,body=None):
    p=subprocess.run(args,input=body,text=True,capture_output=True,timeout=50)
    return {'ok':p.returncode==0,'output':p.stdout if p.returncode==0 else 'command_failed'}

result={}
result['kafka_topics']=command(['docker','exec',c['kafka']['container'],'kafka-topics','--bootstrap-server',c['kafka']['metadata_bootstrap'],'--list'])
result['kafka_groups']=command(['docker','exec',c['kafka']['container'],'kafka-consumer-groups','--bootstrap-server',c['kafka']['metadata_bootstrap'],'--list'])
result['clickhouse_tables']=command(['docker','exec',c['clickhouse']['container'],'clickhouse-client','--query',
    "SELECT database,name,total_rows FROM system.tables WHERE database NOT IN ('system','information_schema','INFORMATION_SCHEMA') FORMAT JSON"])
r=json.loads(Path(c['redis']['private_runtime']).read_text())
result['redis_config_keys']=list(r)
for db in (0,1):
    env={'REDISCLI_AUTH':r.get('password',r.get('REDIS_PASSWORD',''))}
    args=['docker','exec','-e','REDISCLI_AUTH='+env['REDISCLI_AUTH'],c['redis']['container'],'redis-cli','--no-auth-warning','-n',str(db)]
    result['redis_'+str(db)]=command(args+['--scan'])
result['candidate_private_files']=[p.name for p in Path(c['root'],'private').iterdir()]
print(json.dumps(result,ensure_ascii=False,indent=2))
