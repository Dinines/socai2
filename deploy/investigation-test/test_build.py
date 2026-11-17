"""Direct release checks: independent fixture use and immutable package contents."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('investigation_test_builder', HERE/'build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture(scope='module')
def release(tmp_path_factory):
    folder = tmp_path_factory.mktemp('test-release')
    profile = json.loads((HERE/'package-build.json').read_text())
    profile['output_dir'] = str(folder/'out')
    selected = folder/'build.json'
    selected.write_text(json.dumps(profile))
    receipt = builder.build(selected)
    return Path(receipt['archive']).parent/profile['release'], receipt


def test_complete_release_generates_and_validates_outside_source_tree(release, tmp_path):
    package, receipt = release
    assert builder.verify(package)['status'] == 'passed'
    assert receipt['archive_sha256'] == builder.sha(receipt['archive'])
    cfg = json.loads((package/'tools/testdata/streaming-fixture.example.json').read_text())
    cfg['batch_id'] = 'w4-package-offline-fixture'
    config = tmp_path/'fixture.json'
    config.write_text(json.dumps(cfg))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    env.pop('PYTHONPATH', None)
    def run(*args):
        result = subprocess.run([sys.executable, *map(str, args)], cwd=tmp_path,
                                env=env, capture_output=True, text=True, timeout=30, check=True)
        return result.stdout
    script = package/'tools/testdata/streaming_fixture.py'
    generated = json.loads(run(script, 'generate', '--config', config, '--out', tmp_path/'materials'))
    checked = json.loads(run(script, 'validate', '--input', tmp_path/'materials'))
    assert generated == checked and checked['status'] == 'passed_offline'
    assert checked['business_connections'] == checked['model_calls'] == checked['kafka_sends'] == 0
    assert 'prepare' in run(package/'tools/testdata/streaming_send.py', '--help')
    entry = package/'tools/testdata/acceptance.py'
    examples = package/'tools/testdata/acceptance-examples'
    converted = json.loads(run(entry, 'convert', '--source', tmp_path/'materials',
                               '--recipe', examples/'streaming-conversion.json',
                               '--profile', examples/'profile.json', '--output', tmp_path/'parts'))
    assert converted['selected_part'] == 'part1' and converted['execution_status'] == 'not_executed'
    inspected = json.loads(run(entry, 'inspect', '--materials', tmp_path/'parts',
                               '--profile', examples/'profile.json', '--report', tmp_path/'inspection.json'))
    assert converted['parts'] == inspected['parts']
    prepared = json.loads(run(entry, 'prepare', '--materials', tmp_path/'parts',
                              '--profile', examples/'profile.json', '--execution', examples/'execution.json',
                              '--output', tmp_path/'prepared'))
    assert prepared['status'] == 'prepared_not_executed' and prepared['records'] == 17
    assert (tmp_path/'prepared'/'session.json').is_file()
    assert '已有执行不能重派' in run(entry, 'run', '--help')
    assert '显式追加' in run(entry, 'append', '--help')
    observed = json.loads(run(entry, 'status', '--prepared', tmp_path/'prepared', '--report', tmp_path/'status.json'))
    status = json.loads((tmp_path/'status.json').read_text())
    assert observed['state'] == status['state'] == 'ready' and status['next_part'] == 'part1'
    assert not (tmp_path/'prepared/runs').exists()
    assert all(p['actual'] == {'source': 'not_observed', 'alerts': [], 'incidents': [], 'cases': []}
               for p in status['parts'])
    assert not status['live_state_verified'] and not any(status['this_command'].values())
    summary = json.loads(run(entry, 'report', '--prepared', tmp_path/'prepared', '--output', tmp_path/'report'))
    assert summary['counts']['runs'] == 0 and (tmp_path/'report/report.md').is_file()
    assert json.loads((tmp_path/'report/manifest.json').read_text())['readback'] == 'passed'
    console = subprocess.run([sys.executable, str(entry), 'session', '--prepared', str(tmp_path/'prepared'),
                              '--output', str(tmp_path/'console')], cwd=tmp_path, env=env, input='',
                             capture_output=True, text=True, timeout=30, check=True)
    assert '空输入只重显' in console.stdout
    ended = json.loads((tmp_path/'console/end.json').read_text())
    assert ended['reason'] == 'eof' and ended['execution_attempts'] == 0 and not ended['all_parts_completed']
    manifest = json.loads((package/'compatibility.json').read_text())
    assert manifest['service_version'] == manifest['viewer_version'] == '0.6.1'
    assert manifest['investigation_read_operations'] == 55 and manifest['investigation_operations'] == 80
    assert not manifest['startup_executes_tests']
    assert (package/'services/investigation_test/web/viewer.js').is_file()
    assert len(json.loads((package/'test-openapi.json').read_text())['paths']) == 8


def test_dedicated_acceptance_image_uses_locked_drivers_and_separate_entry(release):
    package, _ = release
    dockerfile = (package/'Dockerfile.acceptance').read_text()
    info = json.loads((package/'compatibility.json').read_text())['acceptance_image']
    assert dockerfile.startswith('FROM '+info['profile']['base_ref']+'\n')
    assert 'ENTRYPOINT ["python", "tools/testdata/acceptance.py"]' in dockerfile
    assert 'CMD ["--help"]' in dockerfile and '--require-hashes' in dockerfile and '--only-binary=:all:' in dockerfile
    assert 'USER '+info['profile']['user'] in dockerfile
    assert info['default_command'] == ['--help'] and not info['startup_executes_tests']
    assert {'asyncpg', 'clickhouse-driver', 'aiokafka', 'python-dotenv'} <= info['runtime_dependencies'].keys()
    assert len(info['runtime_dependencies']) == 19
    assert builder.sha(package/info['profile']['requirements']) == info['requirements_sha256']
    assert '"investigation_test"' in (package/'Dockerfile').read_text()
    manifest = json.loads((package/'package-manifest.json').read_text())
    assert not any(part.startswith('.') or part in {'evidence', 'state', 'runs'} for name in manifest['files'] for part in Path(name).parts)


def test_docker_examples_keep_nested_credentials_in_readonly_config_mount(release):
    package, _ = release
    root = package/'deploy/investigation-test/acceptance-config.example'
    profile = json.loads((root/'profile.json').read_text())
    for kind, name in profile['connection_files'].items():
        assert name == '/run/acceptance-config/'+kind+'.json'
        value = json.loads((root/(kind+'.json')).read_text())
        for field in ('producer_env_file', 'database_url_file', 'password_file'):
            if field in value:
                assert value[field].startswith('/run/acceptance-config/secrets/')
    assert json.loads((root/'http.json').read_text())['tenant_id'] == profile['tenant_id']
    assert [p.name for p in (root/'secrets').iterdir()] == ['README.md']
    compose = (package/'deploy/investigation-test/acceptance.compose.yml').read_text()
    assert 'pull_policy: never' in compose and 'create_host_path: false' in compose
    assert 'ACCEPTANCE_MATERIALS_DIR:?' in compose and 'ACCEPTANCE_CONFIG_DIR:?' in compose


@pytest.mark.parametrize('mutation', ['floating_base', 'root_user', 'secret_index', 'unhashed_lock'])
def test_acceptance_image_rejects_unsafe_or_unfixed_build_values(tmp_path, mutation):
    config = json.loads((HERE/'acceptance-image.json').read_text())
    config['requirements'] = 'requirements.lock'
    lock = (HERE/'acceptance-requirements.lock').read_text()
    if mutation == 'floating_base':
        config['base_ref'] = 'python:3.11-slim'
    elif mutation == 'root_user':
        config['user'] = '0:0'
    elif mutation == 'secret_index':
        config['index_url'] = 'https://user:private@example.invalid/simple'
    else:
        lock = 'httpx>=0.28\n'
    (tmp_path/'image.json').write_text(json.dumps(config))
    (tmp_path/'requirements.lock').write_text(lock)
    with pytest.raises(ValueError):
        builder.acceptance_image(tmp_path, {'acceptance_image': 'image.json'})


@pytest.mark.parametrize('mutation', ['missing', 'changed', 'unexpected'])
def test_manifest_rejects_incomplete_or_modified_package(release, tmp_path, mutation):
    package = tmp_path/'release'
    shutil.copytree(release[0], package)
    page = package/'services/investigation_test/web/viewer.js'
    if mutation == 'missing':
        page.unlink()
    elif mutation == 'changed':
        page.write_text('changed fixture')
    else:
        (package/'unregistered.txt').write_text('unexpected fixture')
    with pytest.raises(ValueError, match='package_file_'):
        builder.verify(package)
