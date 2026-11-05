"""Read-only infrastructure prerequisites; emit allowlisted metadata, never env values."""
import json
import shlex
import subprocess
import sys

from verify_socai2_store_20261103 import DEST, ROOT, SSH

REMOTE = r'''
import importlib.util,json,sys
from pathlib import Path
p=Path('/opt/sting-aisoc-socai2/releases/next-20261104-n13/next_service_remote.py')
s=importlib.util.spec_from_file_location('service',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
names=m.command(['docker','ps','--format','{{.Names}}']).splitlines()
out={'containers':[n for n in names if any(x in n for x in ('kafka','redpanda','redis','fusion','next-api'))], 'protected':m.protected_model_config()}
for name in ('socai2-next-api','socai2-fusion-1'):
 code="import importlib.util,json;print(json.dumps({n:importlib.util.find_spec(n) is not None for n in ['aiokafka','asyncpg','redis','clickhouse_driver','simhash','sklearn','lightgbm']}))"
 out[name]={'dependencies':json.loads(m.command(['docker','exec',name,'python','-c',code])), 'networks':list(m.inspect(name)['NetworkSettings']['Networks'])}
env=m.environment('socai2-fusion-1')
out['fusion_connection_keys']=[k for k in env if any(s in k for s in ('KAFKA','REDIS','CLICKHOUSE'))]
out['broker']=env.get('KAFKA_BOOTSTRAP_SERVERS')
out['new_support_tables']=m.pg(m.DATABASE,"SELECT string_agg(table_name,', ' ORDER BY table_name) FROM information_schema.tables WHERE table_schema='public'")
print(json.dumps(out))
'''

if __name__ == "__main__":
    models = sys.argv[1:] == ['--models']
    if models:
        REMOTE = "import importlib.util,json; p='/opt/sting-aisoc-socai2/evidence/next-model-comparison-20261104-m1/runner.py'; s=importlib.util.spec_from_file_location('metadata_only',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(json.dumps({'small':m.child('preflight','small'),'deepseek':m.child('preflight','deepseek'),'model_calls':0,'old_batches_dispatched':False}))"
    target = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105' / ('models.json' if models else 'preflight.json')
    assert not target.exists()
    result = subprocess.run(SSH + [DEST, shlex.join(["python3", "-c", REMOTE])], capture_output=True, timeout=90, check=False)
    assert result.returncode == 0, "preflight failed; stderr withheld"
    data = json.loads(result.stdout)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data))
