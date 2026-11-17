import json
import subprocess
import sys

v=json.load(sys.stdin); old,new=json.loads(subprocess.check_output(['docker','inspect',v['candidate']['container'],v['staged_container']],text=True))
host={k:{'old':val,'new':new['HostConfig'].get(k)} for k,val in old['HostConfig'].items() if new['HostConfig'].get(k)!=val}
print(json.dumps({'old_id':old['Id'],'new_id':new['Id'],'old_state':old['State']['Status'],'new_state':new['State']['Status'],'host_config_diff':host,'config_diff_keys':[k for k,val in old['Config'].items() if new['Config'].get(k)!=val]},indent=2))
