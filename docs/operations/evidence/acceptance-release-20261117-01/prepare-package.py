"""Freeze this explicitly authorized release; no remote or business action."""
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main(config_path):
    p = json.loads(config_path.read_text())
    new, old, evidence = config_path.parent, ROOT / p['prior_config'], ROOT / p['evidence']
    observed = json.loads((ROOT / p['runtime_receipt']).read_text())
    delivery = json.loads((ROOT / p['test_delivery']).read_text())
    c = json.loads((old / 'release.json').read_text())
    prior_root = c['root']
    c.update(release=p['release'], root=p['remote_root'],
             processing_image_tag='socai2-processing:' + p['processing_release'],
             state='prepared_not_deployed')
    c['fusion']['name'] = 'socai2-production-fusion-' + p['processing_release'].removeprefix('processing-')
    c['analysis']['name'] = 'socai2-production-dispatch-' + p['processing_release'].removeprefix('processing-')
    c['swagger'].update(container='socai2-production-swagger-' + p['http_release'],
                        project='socai2-production-swagger-' + p['http_release'],
                        source_directory='deploy/api-docs/' + p['release'] + '/handoff')
    old_viewer = c['viewer']['name']
    c['viewer'].update(old=old_viewer, old_id=observed['services'][old_viewer]['id'],
                       name=p['viewer_name'], image=p['viewer_tag'],
                       old_config=prior_root + '/viewer/config')
    c['stop_before_cleanup'] = [n for n in observed['services'] if 'fusion' in n]
    c['stop_before_cleanup'] += [n for n in observed['services'] if 'http' in n]
    c['stop_before_cleanup'] += [n for n in observed['services'] if 'dispatch' in n]
    c['stop_before_cleanup'] += [old_viewer, next(n for n in observed['services'] if 'swagger' in n)]
    c['expected_old_container_ids'] = {n: v['id'] for n, v in observed['services'].items()}
    c['must_remain_stopped'] = sorted(set(c['must_remain_stopped'] + c['stop_before_cleanup']))
    c['acceptance'] = {'image_reference': delivery['image_reference'],
                       'platform_image_id': delivery['platform_image_id'],
                       'source_package': p['test_package'], 'platform': delivery['platform']}
    save(new / 'release.json', c)
    identity = json.loads((old / 'identity.json').read_text())
    identity.update(candidate_id=p['release'], state='prepared_not_deployed')
    save(new / 'identity.json', identity)
    (new / 'processing-build.toml').write_text((old / 'processing-build.toml').read_text().replace(
        'processing-20261116-r4', p['processing_release']))
    transport = json.loads((old / 'transport.json').read_text())
    transport.update(local_processing=str(ROOT / '.local/processing-release' / p['processing_release']),
                     processing_release=p['processing_release'], remote_root=p['remote_root'], evidence=str(evidence))
    save(new / 'transport.json', transport)

    h = json.loads((old / 'http-profile.json').read_text())
    h.update(release=p['http_release'], root=p['remote_root'] + '/http',
             image='socai2-http-api:' + p['http_release'],
             container='socai2-production-http-' + p['http_release'], project='socai2-production-http-' + p['http_release'])
    spec = importlib.util.spec_from_file_location('http_packager', ROOT / 'deploy/http-service/manage.py')
    packager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(packager)
    patches = {source: target for source, target in h['patches'].items()
               if not target.startswith(('app/', 'investigation_http/')) and target != 'contract/openapi.json'}
    for source, target in h['complete_packages'].items():
        for path in packager.package_sources(ROOT / source):
            patches[str(path.relative_to(ROOT))] = str(Path(target) / path.relative_to(ROOT / source))
    raw = json.loads((old / 'contract/openapi.json').read_text())
    raw['info']['version'] = h['release']
    save(new / 'contract/openapi.json', raw)
    patches[str((new / 'contract/openapi.json').relative_to(ROOT))] = 'contract/openapi.json'
    h['patches'] = dict(sorted(patches.items()))
    h['expected_source_hashes'] = {name: sha(ROOT / name) for name in h['patches']}
    save(new / 'http-profile.json', h)

    swagger = ROOT / c['swagger']['source_directory']
    old_release = json.loads((old / 'release.json').read_text())
    shutil.copytree(ROOT / old_release['swagger']['source_directory'], swagger)
    contract_path = swagger / 'openapi.json'
    contract = json.loads(contract_path.read_text())
    contract['info']['version'] = h['release']
    contract['servers'] = [{'url': c['swagger']['upstream']}]
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + '\n')
    manifest_path = swagger / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.update(release=c['release'], version=h['release'], runtime_evidence=p['evidence'],
                    source_description='Existing r4 documentation; same business contract and this release version.',
                    openapi_sha256=sha(contract_path))
    manifest['files'] = {str(f.relative_to(swagger)): sha(f) for f in sorted(swagger.rglob('*'))
                         if f.is_file() and f != manifest_path}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    save(evidence / 'package-preparation-01.json', {
        'status': 'prepared_not_deployed', 'http_sources': len(patches),
        'source_basis': 'Current complete backend matching accepted 3c2 normal-flow freeze; D5a abnormal-path acceptance remains incomplete.',
        'test_source_package': p['test_package'], 'test_archive_sha256': delivery['archive_sha256'],
        'runtime_connections': c['prior_runtime_root'], 'config': str(config_path.relative_to(ROOT)),
        'config_sha256': sha(config_path), 'model_calls': 0, 'remote_changes': False})
    print(json.dumps({'release': c['release'], 'http_sources': len(patches), 'status': c['state']}))


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
