"""Freeze the independent test service and its existing fixture drivers; never deploy."""
import argparse
import gzip
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

import tomllib

ROOT = Path(__file__).resolve().parents[2]
CACHE_PARTS = {'__pycache__', '.pytest_cache', '.ruff_cache'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+'\n')


def source(root, name):
    path = root/name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('package_source_must_be_relative')
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError('package_source_symlink')
    path.resolve().relative_to(root.resolve())
    if not path.is_file():
        raise ValueError('package_source_missing: '+name)
    return path


def verify(folder):
    folder = Path(folder)
    manifest = json.loads((folder/'package-manifest.json').read_text())
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    expected = set(manifest['files']) | {'package-manifest.json'}
    if actual != expected:
        raise ValueError('package_file_set_changed')
    for name, value in manifest['files'].items():
        path = source(folder, name)
        if sha(path) != value['sha256'] or path.stat().st_size != value['size']:
            raise ValueError('package_file_changed: '+name)
    return {'status': 'passed', 'release': manifest['release'],
            'service_version': manifest['service_version'], 'files': len(manifest['files'])}


def acceptance_image(root, profile):
    """An optional dedicated CLI image in the same verified source package."""
    name = profile.get('acceptance_image')
    if name is None:
        return None
    config = json.loads(source(root, name).read_text())
    required = {'schema', 'base_ref', 'base_id', 'tag', 'platform', 'python_version', 'user', 'workdir',
                'requirements', 'index_url', 'build_network', 'build_timeout_seconds'}
    if set(config) != required or config['schema'] != 'socai2.acceptance-image.v1':
        raise ValueError('invalid_acceptance_image_profile')
    patterns = {'base_ref': r'[a-z0-9][a-z0-9./:_-]*@sha256:[a-f0-9]{64}',
                'base_id': r'sha256:[a-f0-9]{64}', 'tag': r'[a-z0-9][a-z0-9./:_-]*:[a-zA-Z0-9_.-]+',
                'platform': r'linux/(amd64|arm64)', 'python_version': r'3\.\d+\.\d+',
                'user': r'[1-9][0-9]*:[0-9]+', 'workdir': r'/[a-zA-Z0-9_/-]+'}
    if any(not isinstance(config[k], str) or not re.fullmatch(pattern, config[k]) for k, pattern in patterns.items()):
        raise ValueError('invalid_acceptance_image_value')
    index = urlsplit(config['index_url'])
    if (index.scheme != 'https' or not index.hostname or index.username or index.password or index.query or index.fragment
            or any(c.isspace() for c in config['index_url'])):
        raise ValueError('dependency_index_must_be_https_without_credentials')
    if (config['build_network'] not in {'default', 'none'} or type(config['build_timeout_seconds']) is not int
            or config['build_timeout_seconds'] <= 0):
        raise ValueError('invalid_acceptance_build_limits')
    requirements = source(root, config['requirements'])
    pins = {}
    for line in requirements.read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        match = re.fullmatch(r'([a-z0-9][a-z0-9._-]*)==([0-9][a-zA-Z0-9.!+_-]*) --hash=sha256:([a-f0-9]{64})', line)
        if not match or match[1] in pins:
            raise ValueError('acceptance_dependencies_must_be_pinned_and_hashed')
        pins[match[1]] = match[2]
    if not {'pydantic', 'httpx', 'aiokafka', 'asyncpg', 'clickhouse-driver', 'python-dotenv'} <= pins.keys():
        raise ValueError('acceptance_driver_dependencies_missing')
    return config, pins


def build(profile_path, *, root=ROOT):
    profile_path = Path(profile_path).resolve()
    profile = json.loads(profile_path.read_text())
    required = {'schema', 'release', 'output_dir', 'source_roots', 'source_files', 'upstream_profile', 'image'}
    if not required <= set(profile) or set(profile) - required - {'acceptance_image'} or profile['schema'] != 'socai2.test-package.v1':
        raise ValueError('invalid_test_build_profile')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}', profile['release']):
        raise ValueError('invalid_release')
    image = profile['image']
    if set(image) != {'base_tag', 'base_id', 'tag', 'platform', 'user', 'workdir', 'config_mount', 'build_timeout_seconds'}:
        raise ValueError('invalid_image_profile')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image['base_id']):
        raise ValueError('base_image_digest_required')
    if any('\n' in str(value) or '\r' in str(value) for value in image.values()):
        raise ValueError('invalid_image_value')
    folder = (profile_path.parent/profile['output_dir']/profile['release']).resolve()
    if folder.exists():
        raise ValueError('release_exists')
    names = set(profile['source_files'])
    acceptance = acceptance_image(root, profile)
    if acceptance:
        names.update((profile['acceptance_image'], acceptance[0]['requirements']))
    for name in profile['source_roots']:
        base = root/name
        base.resolve().relative_to(root.resolve())
        if not base.is_dir() or base.is_symlink():
            raise ValueError('package_source_tree_missing_or_linked')
        names.update(p.relative_to(root).as_posix() for p in base.rglob('*')
                     if p.is_file() and not CACHE_PARTS.intersection(p.parts)
                     and not any(part.startswith('.') for part in p.relative_to(base).parts)
                     and p.suffix not in {'.pyc', '.pyo'})
    sources = {name: source(root, name) for name in sorted(names)}
    project = tomllib.loads(source(root, 'services/investigation_test/pyproject.toml').read_text())['project']
    sys.path.insert(0, str(root/'services'))
    from investigation_test import __version__
    from investigation_test.api import create_app
    from investigation_test.config import Config
    from investigation_test.proxy import UpstreamConfig
    from investigation_test.viewer import ViewerConfig
    if project['version'] != __version__:
        raise ValueError('package_version_mismatch')
    upstream_file = source(root, profile['upstream_profile'])
    upstream = json.loads(upstream_file.read_text())
    contract = (upstream_file.parent/upstream['openapi_file']).resolve()
    contract.relative_to(root.resolve())
    if sha(contract) != upstream['openapi_sha256']:
        raise ValueError('investigation_contract_changed')
    folder.mkdir(parents=True)
    for name, path in sources.items():
        target = folder/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    shutil.copyfile(contract, folder/'investigation-openapi.json')
    service = json.loads(source(root, 'deploy/investigation-test/read-only.example.json').read_text())
    service['ledger_root'] = '../../state/ledger'
    service['environment_label'] = upstream['environment_label']
    save(folder/'config/service.example.json', service)
    upstream['openapi_file'] = '../investigation-openapi.json'
    save(folder/'config/upstream.example.json', upstream)
    shutil.copyfile(source(root, 'deploy/investigation-test/viewer.example.json'), folder/'config/viewer.example.json')
    app = create_app(Config.load(folder/'config/service.example.json'),
                     UpstreamConfig.load(folder/'config/upstream.example.json'),
                     viewer=ViewerConfig.load(folder/'config/viewer.example.json'))
    save(folder/'test-openapi.json', app.openapi())
    paths = json.loads(contract.read_text())['paths']
    compatibility = {'service_version': __version__, 'viewer_version': __version__,
        'test_api_schema': 'socai2.test-api.v1', 'document_schema_versions': [1],
        'python_requires': project['requires-python'], 'dependencies': project['dependencies'],
        'driver_dependencies': project['optional-dependencies']['drivers'],
        'build_dependency_versions': {name: importlib.metadata.version(name)
                                     for name in ('fastapi', 'pydantic', 'uvicorn', 'httpx', 'aiokafka')},
        'investigation_openapi_sha256': upstream['openapi_sha256'],
        'investigation_operations': sum(method in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}
                                         for item in paths.values() for method in item),
        'investigation_read_operations': sum('get' in item for name, item in paths.items()
                                             if name.startswith('/api/v1/socai2/')),
        'investigation_database_requirements': 'provided by upstream; candidate migrations 123-129; no direct DB access',
        'fixture_version': 'socai2-streaming-s01-s04/v1', 'sender_version': 'socai2.streaming-send.v1',
        'supported': ['ledger_publish_cli', 'read_api_v1', 'http_read_proxy', 'http_viewer',
                      'S01_S04_generate_validate', 'S01_S04_explicit_prepare_send'],
        'not_provided': ['web_test_execution', 'database_install_or_cleanup', 'automatic_recovery',
                         'targeted_and_synthesis_execution', 'background_knowledge_maintenance'],
        'startup_executes_tests': False, 'ledger_in_release': False}
    if acceptance:
        config, pins = acceptance
        compatibility['acceptance_image'] = {
            'profile': config, 'commands': ['convert', 'inspect', 'prepare', 'run', 'append', 'status', 'report', 'session'],
            'runtime_dependencies': pins, 'requirements_sha256': sha(source(root, config['requirements'])),
            'entrypoint': ['python', 'tools/testdata/acceptance.py'], 'default_command': ['--help'],
            'database_access': 'explicit acceptance run/append only; readonly verification; viewer remains HTTP-only',
            'startup_executes_tests': False}
    save(folder/'compatibility.json', compatibility)
    save(folder/'build-profile.json', profile)
    cmd = ['serve', '--config', image['config_mount']+'/service.json', '--upstream-config',
           image['config_mount']+'/upstream.json', '--viewer-config', image['config_mount']+'/viewer.json']
    (folder/'Dockerfile').write_text('\n'.join([
        'FROM '+image['base_tag'], 'WORKDIR '+image['workdir'], 'COPY . .',
        'ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='+image['workdir']+'/services',
        'USER '+image['user'], 'ENTRYPOINT ["python", "-m", "investigation_test"]',
        'CMD '+json.dumps(cmd), '']))
    if acceptance:
        config, _ = acceptance
        install = ['python', '-m', 'pip', 'install', '--no-cache-dir', '--disable-pip-version-check', '--only-binary=:all:',
                   '--index-url', config['index_url'], '--require-hashes', '-r', '/tmp/acceptance-requirements.lock']
        (folder/'Dockerfile.acceptance').write_text('\n'.join([
            'FROM '+config['base_ref'], 'WORKDIR '+config['workdir'],
            'COPY '+json.dumps([config['requirements'], '/tmp/acceptance-requirements.lock']),
            'RUN '+json.dumps(['python', '-c', 'import sys; assert sys.version.split()[0] == '+repr(config['python_version'])]),
            'RUN '+json.dumps(install), 'RUN ["python", "-m", "pip", "check"]', 'COPY . .',
            'ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1', 'USER '+config['user'],
            'ENTRYPOINT ["python", "tools/testdata/acceptance.py"]', 'CMD ["--help"]', '']))
    files = {p.relative_to(folder).as_posix(): {'sha256': sha(p), 'size': p.stat().st_size}
             for p in sorted(folder.rglob('*')) if p.is_file()}
    manifest = {'schema': profile['schema'], 'release': profile['release'], 'service_version': __version__,
                'viewer_version': __version__, 'image': image, 'files': files,
                'source_files': {name: sha(path) for name, path in sources.items()}}
    save(folder/'package-manifest.json', manifest)
    result = verify(folder)
    archive = folder.parent/(folder.name+'.tar.gz')
    with (archive.open('xb') as raw,
          gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as zipped,
          tarfile.open(fileobj=zipped, mode='w') as tar):
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                info = tar.gettarinfo(str(path), arcname=folder.name+'/'+path.relative_to(folder).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                info.mode = 0o644
                with path.open('rb') as stream:
                    tar.addfile(info, stream)
    result.update(archive=str(archive), archive_sha256=sha(archive),
                  manifest_sha256=sha(folder/'package-manifest.json'))
    save(folder.parent/(folder.name+'.receipt.json'), result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('build').add_argument('--profile', required=True)
    commands.add_parser('verify').add_argument('--directory', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.profile) if args.command == 'build' else verify(args.directory), ensure_ascii=False))
