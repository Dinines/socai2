import json
import subprocess
import sys
from pathlib import Path

v=json.load(sys.stdin); c=v['config']; row=json.loads(subprocess.check_output(['docker','inspect',c['container']],text=True))[0]
keys=['AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS','SOCAI2_INVESTIGATION_POLICY_SHA256','SOCAI2_INVESTIGATION_POLICY']
env=dict(s.split('=',1) for s in row['Config']['Env'] if '=' in s)
private=dict(s.split('=',1) for s in Path(c['private_runtime_path']).read_text().splitlines() if '=' in s and not s.startswith('#'))
print(json.dumps({'container_id':row['Id'],'state':row['State']['Status'],'container_values':{k:env.get(k) for k in keys},'file_values':{k:private.get(k) for k in keys}},indent=2))
