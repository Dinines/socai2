"""Freeze the explicitly authorized r4 deployment configuration; no remote writes."""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
NEW = ROOT / 'deploy/aisoc21/streaming-release-20261116-04'
OLD = ROOT / 'deploy/aisoc21/streaming-release-20261116-03'
R2 = ROOT / 'deploy/aisoc21/streaming-release-20261116-02'
EVIDENCE = Path(__file__).resolve().parent


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write('\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


c = json.loads((OLD / 'release.json').read_text())
c.update(release=NEW.name, root='/opt/sting-aisoc-socai2/deployments/' + NEW.name,
         processing_image_tag='socai2-processing:processing-20261116-r4',
         state='prepared_not_deployed')
c['fusion']['name'] = 'socai2-production-fusion-20261116-r4'
c['analysis']['name'] = 'socai2-production-dispatch-20261116-r4'
c['database']['steps'] = ['verify']
c['swagger'].update(container='socai2-production-swagger-20261116-r4',
                    project='socai2-production-swagger-20261116-r4',
                    source_directory='deploy/api-docs/' + NEW.name + '/handoff')
c['viewer'].update(old='socai2-investigation-test-4177-r5',
                   old_id='373a0199a1570de68380dae9b7ff2513684dc8c82d6f5b7d9eb9fac89d39fe65',
                   name='socai2-investigation-test-4177-r6',
                   old_config=c['prior_runtime_root'] + '/viewer/config')
c['stop_before_cleanup'] = [
    'socai2-production-fusion-20261116-r3', 'socai2-production-http-20261116',
    'socai2-production-dispatch-20261116-r3', 'socai2-investigation-test-4177-r5',
    'socai2-production-swagger-20261116']
c['must_remain_stopped'] = sorted(set(c['must_remain_stopped'] + c['stop_before_cleanup']))
c.pop('unchanged_services', None)
c.pop('stop_after_readiness', None)
c['rollback'] = dict(before_new_business_writes='restore_previous_images_only_after_idle_check',
                     after_new_business_writes='retain_new_reader_and_data_then_fix_current_version',
                     schema_downgrade=False, restore_deleted_data=False, replay_requests=False)
save(NEW / 'release.json', c)
identity = json.loads((OLD / 'identity.json').read_text())
identity.update(candidate_id=NEW.name, state='prepared_not_deployed')
save(NEW / 'identity.json', identity)
(NEW / 'processing-build.toml').write_text((OLD / 'processing-build.toml').read_text().replace('20261116-r3', '20261116-r4'))
transport = json.loads((OLD / 'transport.json').read_text())
transport.update(local_processing=str(ROOT / '.local/processing-release/processing-20261116-r4'),
                 processing_release='processing-20261116-r4', remote_root=c['root'], evidence=str(EVIDENCE))
save(NEW / 'transport.json', transport)

h = json.loads((R2 / 'http-profile.json').read_text())
h.update(release='streaming-http-20261116-r4', root=c['root'] + '/http',
         image='socai2-http-api:streaming-http-20261116-r4',
         container='socai2-production-http-20261116-r4', project='socai2-production-http-20261116-r4')
spec = importlib.util.spec_from_file_location('http_packager', ROOT / 'deploy/http-service/manage.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)
patches = {s: t for s, t in h['patches'].items()
           if not t.startswith(('app/', 'investigation_http/')) and t != 'contract/openapi.json'}
for source, target in h['complete_packages'].items():
    for path in packager.package_sources(ROOT / source):
        patches[str(path.relative_to(ROOT))] = str(Path(target) / path.relative_to(ROOT / source))
raw = json.loads((ROOT / 'docs/operations/evidence/case-update-http-20261115-01/candidate-openapi.json').read_text())
raw['info']['version'] = h['release']
save(NEW / 'contract/openapi.json', raw)
patches[str((NEW / 'contract/openapi.json').relative_to(ROOT))] = 'contract/openapi.json'
h['patches'] = dict(sorted(patches.items()))
h['expected_source_hashes'] = {name: sha(ROOT / name) for name in h['patches']}
save(NEW / 'http-profile.json', h)

swagger = ROOT / c['swagger']['source_directory']
shutil.copytree(ROOT / 'deploy/api-docs/streaming-release-20261116-02/handoff', swagger)
contract_path = swagger / 'openapi.json'
contract = json.loads(contract_path.read_text())
contract['info']['version'] = h['release']
contract['servers'] = [{'url': c['swagger']['upstream']}]
contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + '\n')
manifest_path = swagger / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest['release'] = c['release']
manifest['version'] = h['release']
manifest['runtime_evidence'] = str(EVIDENCE.relative_to(ROOT))
manifest['source_description'] = 'Presentation template inherited from r2; runtime contract and version frozen for r4.'
manifest['openapi_sha256'] = sha(contract_path)
manifest['files'] = {str(p.relative_to(swagger)): sha(p) for p in sorted(swagger.rglob('*'))
                     if p.is_file() and p != manifest_path}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
save(EVIDENCE / 'package-preparation-01.json', {
    'status': 'prepared_not_deployed', 'source': 'current working tree',
    'http_sources': len(patches), 'raw_contract_operations': sum(
        method in {'get', 'post', 'patch', 'put', 'delete'} for item in raw['paths'].values() for method in item),
    'config_files': {str(p.relative_to(ROOT)): sha(p) for p in sorted(NEW.rglob('*')) if p.is_file()},
    'viewer_runtime_reused': 'test-service-0.6.0-20261116-01',
    'runtime_connections': c['prior_runtime_root'], 'remote_changes': False,
})
print(json.dumps({'release': c['release'], 'http_sources': len(patches), 'status': c['state']}))
