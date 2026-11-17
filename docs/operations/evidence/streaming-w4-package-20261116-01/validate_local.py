"""Use only this frozen package: fixture, explicit publish, TCP read and restart."""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE/'local-runtime.json').read_text())
receipt = json.loads((HERE/'build-01.json').read_text())
with socket.socket() as check:
    check.bind((cfg['host'], cfg['port']))
assert hashlib.sha256(Path(receipt['archive']).read_bytes()).hexdigest() == receipt['archive_sha256']
temporary = Path(tempfile.mkdtemp(prefix='socai2-w4-')).resolve()
with tarfile.open(receipt['archive'], 'r:gz') as archive:
    for item in archive.getmembers():
        assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
        target = temporary/item.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(item).read())
package = temporary/receipt['release']
env = {**os.environ, 'PYTHONPATH': str(package/'services'), 'PYTHONDONTWRITEBYTECODE': '1'}


def command(*args):
    result = subprocess.run([sys.executable, *map(str, args)], cwd=temporary,
                            env=env, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout


verified = json.loads(command(package/'deploy/investigation-test/build.py', 'verify', '--directory', package))
fixture = json.loads((package/'tools/testdata/streaming-fixture.example.json').read_text())
fixture.update(batch_id='w4-package-fixture-20261116-01', base_time='2026-11-16T00:00:00+00:00')
(HERE/'local-fixture.json').write_text(json.dumps(fixture, indent=2)+'\n')
generated = json.loads(command(package/'tools/testdata/streaming_fixture.py', 'generate', '--config',
                               HERE/'local-fixture.json', '--out', HERE/'offline-materials'))
assert generated == json.loads(command(package/'tools/testdata/streaming_fixture.py', 'validate',
                                       '--input', HERE/'offline-materials'))
assert 'prepare' in command(package/'tools/testdata/streaming_send.py', '--help')
publication = json.loads(command('-m', 'investigation_test', 'publish', '--config', HERE/'publish-config.json',
                                 '--document', HERE/'inputs/document.json', '--expected-revision', '0'))
service = json.loads((HERE/'publish-config.json').read_text())
service.update(host=cfg['host'], port=cfg['port'])
(HERE/'local-service.json').write_text(json.dumps(service, indent=2)+'\n')


def ledger_hashes():
    base = Path(service['ledger_root'])
    return {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(base.rglob('*')) if p.is_file()}


before = ledger_hashes()
old = json.loads((HERE/'old-ledger-hashes.json').read_text())
assert all(before[k] == value for k, value in old.items())
requests = []
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
output = HERE/'local-responses'
output.mkdir()


def get(path):
    with opener.open(f"http://{cfg['host']}:{cfg['port']}"+path, timeout=cfg['http_timeout_seconds']) as response:
        body = response.read()
        name = f'{len(requests)+1:02}.body'
        (output/name).write_bytes(body)
        requests.append({'path': path, 'status': response.status, 'body': 'local-responses/'+name,
                         'sha256': hashlib.sha256(body).hexdigest()})
        assert response.status == 200
        return body


def start(number):
    log = (HERE/f'local-server-{number:02}.log').open('x')
    process = subprocess.Popen([sys.executable, '-m', 'investigation_test', 'serve', '--config',
        str(HERE/'local-service.json'), '--upstream-config', str(package/'config/upstream.example.json'),
        '--viewer-config', str(package/'config/viewer.example.json')], cwd=temporary, env=env,
        stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic()+cfg['startup_timeout_seconds']
    while time.monotonic() < deadline:
        if process.poll() is not None:
            log.close()
            raise RuntimeError('packaged_server_exited')
        try:
            with socket.create_connection((cfg['host'], cfg['port']), timeout=0.2):
                return process, log
        except OSError:
            time.sleep(0.1)
    process.terminate()
    process.wait(timeout=cfg['stop_timeout_seconds'])
    log.close()
    raise RuntimeError('packaged_server_start_timeout')


def stop(process, log):
    process.terminate()
    result = process.wait(timeout=cfg['stop_timeout_seconds'])
    log.close()
    return result


batch = publication['batch_id']
prefix = '/test-api/v1/batches/'+batch
exits = []
process, log = start(1)
try:
    capabilities = json.loads(get('/test-api/v1/capabilities'))
    assert capabilities['service_version'] == capabilities['viewer_version'] == '0.4.0'
    assert capabilities['investigation_http']['get_operations'] == 55
    assert json.loads(get('/openapi.json')) == json.loads((package/'test-openapi.json').read_text())
    assert json.loads(get('/viewer/config.json'))['viewer_version'] == '0.4.0'
    for url, filename in [('/viewer/', 'index.html'), ('/viewer/assets/viewer.js', 'viewer.js'),
                           ('/viewer/assets/viewer.css', 'viewer.css'), ('/viewer/assets/viewer_state.mjs', 'viewer_state.mjs')]:
        assert get(url) == (package/'services/investigation_test/web'/filename).read_bytes()
    assert json.loads(get('/test-api/v1/batches'))['total'] == 2
    detail = get(prefix)
    assert json.loads(detail)['batch']['provenance'] == 'saved_evidence'
    document = json.loads((HERE/'inputs/document.json').read_text())
    assert len(json.loads(get(prefix+'/cases'))['items']) == 3
    expected_operations = [{**row, 'occurred_at': row['occurred_at'].replace('+00:00', 'Z')}
                           for row in sorted(document['operations'], key=lambda row: row['id'])]
    assert json.loads(get(prefix+'/operations'))['items'] == expected_operations
    assert len(json.loads(get(prefix+'/quality-issues'))['items']) == 2
    evidence = get(prefix+'/evidence/quality-summary?format=content')
    assert evidence == (HERE/'inputs/quality-summary.json').read_bytes()
    get('/test-api/v1/batches/w2-live-s01-s04-20261115-01')
finally:
    exits.append(stop(process, log))
assert ledger_hashes() == before
process, log = start(2)
try:
    assert json.loads(get('/test-api/v1/capabilities')) == capabilities
    assert get(prefix) == detail
    assert get(prefix+'/evidence/quality-summary?format=content') == evidence
finally:
    exits.append(stop(process, log))
assert ledger_hashes() == before
result = {'status': 'passed', 'package': verified, 'temporary_package': str(package), 'fixture': generated,
          'publication': publication, 'http_gets': len(requests), 'requests': requests,
          'old_ledger_files_preserved': len(old), 'ledger_files_unchanged_after_reads_and_restart': len(before),
          'ledger_hashes': before, 'server_exit_codes': exits, 'new_model_calls': 0,
          'database_queries': 0, 'business_http_calls': 0, 'kafka_messages': 0}
(HERE/'local-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({key: value for key, value in result.items() if key not in {'requests', 'ledger_hashes'}}, ensure_ascii=False))
