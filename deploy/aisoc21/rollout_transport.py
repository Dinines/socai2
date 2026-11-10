"""Transfer and execute a frozen release using explicit host configuration.

Only release source archives and sanitized tool receipts cross this transport.
Credentials remain in the existing private host files.
"""
import argparse
import hashlib
import io
import json
import shlex
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path

UNPACK = r'''
import hashlib,io,json,pathlib,sys,tarfile,tempfile
dest=pathlib.Path(sys.argv[1]);expected=sys.argv[2];limits=json.loads(sys.argv[3])
raw=sys.stdin.buffer.read(limits['compressed_bytes']+1)
assert len(raw)<=limits['compressed_bytes'] and hashlib.sha256(raw).hexdigest()==expected
assert not dest.exists() and dest.parent.resolve()==dest.parent
with tempfile.TemporaryDirectory(dir=dest.parent) as temporary:
 stage=pathlib.Path(temporary)/'release';stage.mkdir()
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  members=archive.getmembers();names=[m.name for m in members]
  assert len(members)<=limits['files'] and len(names)==len(set(names))
  assert sum(m.size for m in members)<=limits['uncompressed_bytes']
  for member in members:
   path=pathlib.PurePosixPath(member.name)
   assert member.isfile() and not path.is_absolute() and '..' not in path.parts
   assert path.as_posix()==member.name and member.mode==0o644
   target=stage/path;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(archive.extractfile(member).read());target.chmod(0o644)
 manifest=json.loads((stage/'manifest.json').read_text())
 assert set(names)==set(manifest['files'])|{'manifest.json'}
 for name,record in manifest['files'].items():
  sha=record['sha256'] if isinstance(record,dict) else record
  assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==sha
 stage.rename(dest)
print(json.dumps({'uploaded':str(dest),'archive_sha256':expected,'files':len(names)}))
'''


def run(config_path, kind, mode, project=None, service=None):
    cfg = json.loads(Path(config_path).read_text())
    transport = cfg['transport']
    local = Path(cfg['local_processing' if kind == 'processing' else 'local_release'])
    release = cfg['processing_release' if kind == 'processing' else 'release']
    remote = cfg['remote_root'] + '/releases/' + release
    body = None
    if mode == 'upload':
        if kind == 'processing':
            body = (local / 'release.tar.gz').read_bytes()
        else:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
                for path in sorted(local.rglob('*')):
                    if path.is_file():
                        archive.add(path, arcname=str(path.relative_to(local)), recursive=False)
            body = buffer.getvalue()
        command = [transport['remote_python'], '-B', '-c', UNPACK, remote,
                   hashlib.sha256(body).hexdigest(), json.dumps(cfg['archive_limits'])]
    elif kind == 'processing':
        if mode != 'build':
            raise ValueError('Processing release only supports upload/build')
        command = [transport['remote_python'], '-B', remote + '/build_processing_image.py',
                   '--release-directory', remote]
    else:
        command = [transport['remote_python'], '-B', remote + '/deploy/aisoc21/release_12.py',
                   mode, '--directory', remote]
        if mode == 'rollout':
            if not project or not service:
                raise ValueError('rollout requires project and service')
            command += ['--project', project, '--service', service]
    argv = [transport['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UpdateHostKeys=no', '-o', f"ConnectTimeout={transport['connect_timeout_seconds']}",
            transport['ssh_target'], shlex.join(command)]
    result = subprocess.run(argv, input=body, capture_output=True, check=False,
                            timeout=cfg['command_timeout_seconds'])
    receipt = {'kind': kind, 'mode': mode, 'project': project, 'service': service,
               'exit': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()}
    destination = Path(cfg['evidence']) / (kind + '-' + mode + '-' + datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with destination.open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps({'receipt': str(destination), **receipt}))
    if result.returncode:
        raise RuntimeError('Remote step failed; inspect receipt before taking further action')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('kind', choices=('processing', 'unified'))
    parser.add_argument('mode', choices=('upload', 'build', 'preflight', 'prepare', 'rollout', 'activate', 'verify', 'rollback'))
    parser.add_argument('--project')
    parser.add_argument('--service')
    args = parser.parse_args()
    run(args.config, args.kind, args.mode, args.project, args.service)
