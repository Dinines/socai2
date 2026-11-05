"""Transport fixed credential-free k1 package and export only its evidence."""
import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from verify_socai2_store_20261103 import DEST, ROOT, SSH

OUT = ROOT / 'docs/operations/evidence/socai2-kafka-chain-20261105/k2'
REMOTE = '/opt/sting-aisoc-socai2/evidence/next-kafka-k2-20261105'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['upload', 'ingest', 'first', 'second', 'export'])
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.phase == 'upload':
        files = {'plan.json': (OUT / 'plan.json').read_text('utf-8')}
        for name in ('kafka_chain_child.py', 'kafka_chain_remote.py'):
            files[name] = (ROOT / 'deploy/aisoc21' / name).read_text('utf-8')
            (OUT / name).write_text(files[name], 'utf-8')
        manifest = {n: hashlib.sha256(v.encode()).hexdigest() for n, v in files.items()}
        files['manifest.json'] = json.dumps(manifest)
        (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), 'utf-8')
        code = "import json,sys,pathlib; p=pathlib.Path(sys.argv[1]);p.mkdir(mode=0o700,exist_ok=False); data=json.load(sys.stdin);[(p.joinpath(k).write_text(v),p.joinpath(k).chmod(0o600)) for k,v in data.items()];print(json.dumps({'uploaded':len(data),'credentials':False}))"
        command = ['python3', '-c', code, REMOTE]
        body = json.dumps(files).encode()
    else:
        command = ['python3', REMOTE + '/kafka_chain_remote.py', args.phase]
        if args.case:
            command += ['--case', args.case]
        body = None
    stamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%S')
    target = OUT / (stamp + '-' + args.phase + ('-' + args.case if args.case else ''))
    target.mkdir(exist_ok=False)
    result = subprocess.run(SSH + [DEST, shlex.join(command)], input=body, capture_output=True, timeout=1000, check=False)
    records = []
    for line in result.stdout.decode('utf-8').splitlines():
        if not line.startswith('{'):
            continue
        record = json.loads(line)
        for name, value in record.pop('export', {}).items():
            assert Path(name).name == name and name.endswith('.json')
            (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf-8')
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    receipt = {'phase': args.phase, 'case': args.case, 'exit_code': result.returncode, 'records': records,
        'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(), 'credentials_exported': False}
    (target / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', 'utf-8')
    print(str(target / 'receipt.json'), flush=True)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
