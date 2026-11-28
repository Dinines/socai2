"""Direct release assembly checks; no Docker, DB, model or network operations."""
import importlib.util
import io
import json
import tarfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

SPEC = importlib.util.spec_from_file_location('http_release', Path(__file__).with_name('manage.py'))
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


def test_logging_directory_mount_matches_readonly_profile(tmp_path):
    profile_file = write(tmp_path/'logging.json', {'directory': '/app/logs'})
    directory = tmp_path/'logs'
    directory.mkdir()
    env = {'SOCAI2_LOGGING_PROFILE_FILE': '/app/config/logging.json'}
    mounts = [{'source': str(profile_file), 'target': env['SOCAI2_LOGGING_PROFILE_FILE'], 'read_only': True}]
    cfg = {'logging_directory_mount': {'source': str(directory), 'target': '/app/logs'}}
    manager.add_logging_volume(cfg, env, mounts)
    assert mounts[-1] == {'type': 'bind', 'source': str(directory), 'target': '/app/logs', 'read_only': False}
    assert mounts[0]['read_only'] is True
    with pytest.raises(AssertionError, match='duplicate_runtime_mount_target'):
        manager.add_logging_volume(cfg, env, mounts)


def test_logging_mount_cannot_fall_back_to_container_storage(tmp_path):
    profile_file = write(tmp_path/'logging.json', {'directory': '/app/logs'})
    env = {'SOCAI2_LOGGING_PROFILE_FILE': '/app/config/logging.json'}
    mounts = [{'source': str(profile_file), 'target': env['SOCAI2_LOGGING_PROFILE_FILE'], 'read_only': True}]
    with pytest.raises(AssertionError, match='explicit_logging_profile_and_mount_required'):
        manager.add_logging_volume({}, env, mounts)
    with pytest.raises(AssertionError, match='logging_directory_profile_mismatch'):
        manager.add_logging_volume({'logging_directory_mount': {'source': str(tmp_path), 'target': '/app/other'}}, env, mounts)


def profile(tmp_path):
    source = tmp_path/'source'
    for name in ('app/__init__.py', 'app/schema.json', 'investigation_http/main.py'):
        p = source/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{}' if p.suffix == '.json' else '# source\n')
    (source/'app/__pycache__').mkdir()
    (source/'app/__pycache__/ignored.pyc').write_bytes(b'cache')
    (source/'app/.env').write_text('private not a runtime source')
    patches = {str(p.relative_to(source)): str(p.relative_to(source))
               for root in ('app', 'investigation_http') for p in manager.package_sources(source/root)}
    return {'source_root': str(source), 'complete_packages': {'app': 'app', 'investigation_http': 'investigation_http'},
            'patches': patches, 'expected_source_hashes': {n: manager.sha(source/n) for n in patches},
            'base_tag': 'synthetic:base', 'base_image': 'sha256:synthetic', 'release': 'synthetic',
            'runtime_environment_file': str(tmp_path/'private.json')}


def runtime(cfg, tmp_path):
    write(Path(cfg['runtime_environment_file']), {
        'DATABASE_URL': 'postgresql+asyncpg://reader:synthetic@candidate:5432/candidate',
        'SOCAI2_CASE_DATABASE_URL': 'postgresql+asyncpg://writer:synthetic@candidate:5432/candidate'})
    cfg.update(database='candidate', database_host='candidate', database_port=5432, postgres_sslmode='require',
        environment={'SOCAI2_HTTP_CONTEXT_FILE': '/app/config/context.json'},
        runtime_mounts=[],
        reference_container='reference', container='candidate', bind='127.0.0.1', port=0,
        root=str(tmp_path/'deployment'), image='synthetic:candidate', project='candidate',
        platform='linux/amd64', entry='investigation_http.main:app', container_port=8000,
        tmpfs='/tmp:size=16m', memory='128m', network='synthetic')


def test_complete_package_roundtrip_and_old_package_replacement(tmp_path):
    cfg = profile(tmp_path)
    folder = tmp_path/'release'
    result = manager.package(cfg, folder)
    with tarfile.open(result['archive']) as archive:
        archive.extractall(tmp_path/'unpacked', filter='data')
    manager.verify_files(tmp_path/'unpacked')
    assert (folder/'app/schema.json').read_text() == '{}'
    assert not (folder/'app/.env').exists()
    assert not (folder/'app/__pycache__').exists()
    dockerfile = (folder/'Dockerfile').read_text()
    assert 'RUN rm -rf -- /app/app /app/investigation_http' in dockerfile
    assert 'COPY --chown=10001:10001 investigation_http/ /app/investigation_http/' in dockerfile
    (folder/'app/schema.json').write_text('changed')
    with pytest.raises(AssertionError, match='candidate_file_changed'):
        manager.verify_files(folder)


@pytest.mark.parametrize('change', ['omitted', 'new_source', 'changed_source', 'implicit_runtime'])
def test_incomplete_or_changed_package_refused_before_output(tmp_path, change):
    cfg = profile(tmp_path)
    source = Path(cfg['source_root'])
    if change == 'omitted':
        cfg['patches'].pop('app/schema.json')
    elif change == 'new_source':
        (source/'app/new.py').write_text('# new')
    elif change == 'changed_source':
        (source/'app/schema.json').write_text('changed')
    else:
        cfg.pop('runtime_environment_file')
    with pytest.raises(AssertionError):
        manager.package(cfg, tmp_path/'release')
    assert not (tmp_path/'release').exists()


def test_prepare_uses_only_selected_environment_and_mounts(tmp_path, monkeypatch):
    cfg = profile(tmp_path)
    runtime(cfg, tmp_path)
    folder = tmp_path/'release'
    manager.package(cfg, folder)
    monkeypatch.setattr(manager, 'inspect', lambda name: {'Image': cfg['base_image'],
        'Config': {'Env': ['OLD_ENV=must_not_inherit', 'DATABASE_URL=old']},
        'Mounts': [{'Type': 'bind', 'Source': '/old', 'Destination': '/run/old', 'RW': True}]})
    monkeypatch.setattr(manager, 'snapshot', lambda exclude: {'reference': {'id': 'unchanged'}})
    monkeypatch.setattr(manager.socket, 'socket', lambda: nullcontext(SimpleNamespace(bind=lambda address: None)))
    manager.prepare(cfg, folder)
    env = Path(cfg['root'])/'private'/cfg['release']/'runtime.env'
    assert env.stat().st_mode & 0o777 == 0o600
    assert 'OLD_ENV' not in env.read_text() and 'DATABASE_URL=old' not in env.read_text()
    assert env.read_text().count('sslmode=require') == 2
    assert 'PGSSLROOTCERT' not in env.read_text()
    service = json.loads((folder/'compose.json').read_text())['services']['api']
    assert service['volumes'] == []
    assert service['command'][3] == 'investigation_http.main:app'


def test_password_url_default_mode_preserves_encoded_credentials(tmp_path):
    cfg = profile(tmp_path)
    runtime(cfg, tmp_path)
    path = Path(cfg['runtime_environment_file'])
    value = json.loads(path.read_text())
    value['DATABASE_URL'] = 'postgresql+asyncpg://reader:p%40ss%3Aword@candidate:5432/candidate?application_name=http'
    path.write_text(json.dumps(value))
    env, mounts = manager.explicit_runtime_inputs(cfg)
    assert env['DATABASE_URL'] == value['DATABASE_URL'] + '&sslmode=require'
    assert env['SOCAI2_CASE_DATABASE_URL'].endswith('?sslmode=require')
    assert mounts == []


@pytest.mark.parametrize('change', ['missing_file', 'wrong_database', 'wrong_host', 'missing_password'])
def test_invalid_runtime_refused_before_docker_or_private_output(tmp_path, monkeypatch, change):
    cfg = profile(tmp_path)
    runtime(cfg, tmp_path)
    folder = tmp_path/'release'
    manager.package(cfg, folder)
    path = Path(cfg['runtime_environment_file'])
    if change == 'missing_file':
        path.unlink()
    else:
        env = json.loads(path.read_text())
        old, new = {'wrong_database': ('/candidate', '/other'), 'wrong_host': ('@candidate:', '@other:'),
                    'missing_password': (':synthetic@', '@')}[change]
        env['SOCAI2_CASE_DATABASE_URL'] = env['SOCAI2_CASE_DATABASE_URL'].replace(old, new)
        path.write_text(json.dumps(env))
    monkeypatch.setattr(manager, 'inspect', lambda name: pytest.fail('must reject before Docker'))
    with pytest.raises(AssertionError):
        manager.prepare(cfg, folder)
    assert not Path(cfg['root']).exists()


@pytest.mark.parametrize('changed', [False, True])
def test_verify_checks_contract_not_only_operation_count(tmp_path, monkeypatch, changed):
    cfg = {'bind': 'candidate', 'port': 18424, 'expected_operations': 1,
           'expected_openapi_file': 'openapi.json', 'release': 'current', 'database': 'candidate',
           'container': 'candidate', 'image': 'current-image'}
    doc = {'info': {'version': 'current'}, 'paths': {'/api/v1/socai2/cases': {'get': {'responses': {'200': {}}}}}}
    write(tmp_path/'openapi.json', doc)
    write(tmp_path/'manifest.json', {'files': {}})
    write(tmp_path/'before.json', {})
    if changed:
        doc['paths']['/api/v1/socai2/cases']['get']['responses']['503'] = {}
    def response(url, **kwargs):
        value = io.BytesIO(json.dumps(doc).encode())
        value.status = 200
        return value
    monkeypatch.setattr(manager.urllib.request, 'urlopen', response)
    monkeypatch.setattr(manager, 'inspect', lambda name: {'Image': 'same', 'Id': 'same'})
    monkeypatch.setattr(manager, 'snapshot', lambda exclude: {})
    if changed:
        with pytest.raises(AssertionError, match='runtime_openapi_mismatch'):
            manager.verify(cfg, tmp_path)
    else:
        assert manager.verify(cfg, tmp_path)['route_count'] == 1
