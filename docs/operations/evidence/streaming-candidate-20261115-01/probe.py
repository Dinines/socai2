"""Read-only candidate name/port/base probe. Never creates resources or calls a model."""
import json
import shlex
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "probe-target.json").read_text())
source = r'''
import datetime,json,pathlib,re,subprocess,sys
c=json.load(sys.stdin)
def command(argv,body=None):
 p=subprocess.run(argv,input=body,text=True,capture_output=True,timeout=c['probe_timeout_seconds'])
 if p.returncode:raise RuntimeError('probe_command_exit_'+str(p.returncode))
 return p.stdout
assert all(re.fullmatch('[a-z_][a-z0-9_]+',c[k]) for k in ['candidate_database','candidate_role'])
out={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':'read_only','model_calls':0}
out['containers']=[{'name':d['Name'].lstrip('/'),'id':d['Id'],'image':d['Image'],'tag':d['Config']['Image'],
 'running':d['State']['Running'],'started_at':d['State']['StartedAt'],'ports':d['NetworkSettings']['Ports']}
 for d in json.loads(command(['docker','inspect',*c['reference_containers']]))]
sql="SELECT json_build_object('database_exists',EXISTS(SELECT FROM pg_database WHERE datname='%s'),'role_exists',EXISTS(SELECT FROM pg_roles WHERE rolname='%s'))"%(c['candidate_database'],c['candidate_role'])
out['candidate_catalog']=json.loads(command(['docker','exec','-i',c['postgres_container'],'psql','-XwAtq','-v','ON_ERROR_STOP=1','-U',c['postgres_admin'],'-d',c['catalog_database']], 'BEGIN READ ONLY;'+sql+';ROLLBACK;'))
out['candidate_directory_exists']=pathlib.Path(c['candidate_directory']).exists()
listeners=command(['ss','-H','-ltn']).splitlines()
out['candidate_port_in_use']={str(port):any(line.split()[3].rsplit(':',1)[-1]==str(port) for line in listeners) for port in c['candidate_ports']}
out['network']=[{'name':n['Name'],'driver':n['Driver']} for n in json.loads(command(['docker','network','inspect',c['network']]))]
print(json.dumps(out,indent=2))
'''
out = HERE / "probe-01.json"
assert not out.exists()
p = subprocess.run([cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
    "-o", "ConnectTimeout=" + str(cfg["connect_timeout_seconds"]), cfg["target"],
    "python3 -c " + shlex.quote(source)], input=json.dumps(cfg), text=True, capture_output=True,
    timeout=cfg["command_timeout_seconds"])
if p.returncode:
    raise RuntimeError("readonly_probe_exit_" + str(p.returncode))
value = json.loads(p.stdout)
out.write_text(json.dumps(value, indent=2) + "\n")
print(json.dumps({"mode": value["mode"], "catalog": value["candidate_catalog"],
    "port_in_use": value["candidate_port_in_use"], "directory_exists": value["candidate_directory_exists"]}))
