"""Own only these temporary processes; always stop without touching 21 services."""
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
profile=json.loads((ROOT/'runtime-profile.json').read_text())
ledger=Path(json.loads((ROOT/'service-config.json').read_text())['ledger_root'])
def hashes():
    return {str(p.relative_to(ledger)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ledger.rglob('*')) if p.is_file()}
def listening(port):
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(('127.0.0.1',port))==0
before=hashes()
(ROOT/'ledger-before.json').write_text(json.dumps(before,indent=2)+'\n')
(ROOT/'responses').mkdir(exist_ok=True)
stop=False
processes=[]
def request_stop(*_args):
    global stop
    stop=True
signal.signal(signal.SIGTERM,request_stop)
signal.signal(signal.SIGINT,request_stop)
try:
    sshlog=(ROOT/'ssh.log').open('w')
    tunnel=subprocess.Popen(['ssh','-N','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=30','-L',f"127.0.0.1:{profile['forward_port']}:{profile['forward_target']}",profile['ssh_alias']],stdout=sshlog,stderr=sshlog)
    processes.append(tunnel)
    env=dict(os.environ,PYTHONPATH=str(REPO/'services'))
    servicelog=(ROOT/'service.log').open('w')
    service=subprocess.Popen([str(REPO/'.local/conda-envs/socai2/bin/python'),str(ROOT/'record_server.py')],env=env,stdout=servicelog,stderr=servicelog)
    processes.append(service)
    until=time.monotonic()+30
    while not all(listening(profile[k]) for k in ['service_port','forward_port']):
        if any(p.poll() is not None for p in processes): raise RuntimeError('temporary process exited before startup')
        if time.monotonic()>until: raise RuntimeError('temporary startup timeout')
        time.sleep(.1)
    print(json.dumps({'state':'ready','service_port':profile['service_port'],'forward_port':profile['forward_port'],'pids':[p.pid for p in processes]}),flush=True)
    while not stop and not (ROOT/'stop-request').exists():
        if any(p.poll() is not None for p in processes): raise RuntimeError('temporary process exited unexpectedly')
        time.sleep(.2)
finally:
    for p in reversed(processes):
        if p.poll() is None:p.terminate()
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.kill();p.wait()
    after=hashes()
    (ROOT/'ledger-after.json').write_text(json.dumps(after,indent=2)+'\n')
    result={'ledger_unchanged':before==after,'exit_codes':[p.returncode for p in processes],
            'ports_closed':{str(profile[k]):not listening(profile[k]) for k in ['service_port','forward_port']}}
    (ROOT/'shutdown.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
