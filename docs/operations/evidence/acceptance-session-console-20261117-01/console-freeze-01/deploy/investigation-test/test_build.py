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
    assert manifest['service_version'] == manifest['viewer_version'] == '0.6.0'
    assert manifest['investigation_read_operations'] == 55 and manifest['investigation_operations'] == 80
    assert not manifest['startup_executes_tests']
    assert (package/'services/investigation_test/web/viewer.js').is_file()
    assert len(json.loads((package/'test-openapi.json').read_text())['paths']) == 8


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
