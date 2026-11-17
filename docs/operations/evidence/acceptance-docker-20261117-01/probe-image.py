"""Direct image proof: no host source mounts, business connections or execution."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def probe(profile_path, output):
    config = json.loads(profile_path.read_text())
    receipts = []

    def call(args):
        result = subprocess.run(args, capture_output=True, text=True, timeout=config['build_timeout_seconds'])
        receipts.append({'command': args, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            with output.open('x') as stream:
                json.dump({'status': 'failed', 'receipts': receipts}, stream, ensure_ascii=False, indent=2)
            raise RuntimeError('image verification failed; see saved receipt')
        return result.stdout

    item = json.loads(call(['docker', 'image', 'inspect', '--platform', config['platform'], config['tag']]))[0]
    image = {key: item[key] for key in ('Id', 'Architecture', 'Os', 'RepoTags', 'RepoDigests')}
    image['config'] = {key: item['Config'][key] for key in ('User', 'WorkingDir', 'Entrypoint', 'Cmd')}
    assert image['config'] == {'User': config['user'], 'WorkingDir': config['workdir'],
                               'Entrypoint': ['python', 'tools/testdata/acceptance.py'], 'Cmd': ['--help']}
    assert image['Os']+'/'+image['Architecture'] == config['platform']
    base = ['docker', 'run', '--rm', '--pull=never', '--platform', config['platform'], '--network', 'none',
            '--read-only', '--tmpfs', '/tmp:rw,mode=1777']
    help_text = call([*base, config['tag']])
    for command in ('convert', 'inspect', 'prepare', 'run', 'append', 'status', 'report', 'session'):
        assert command in help_text
    script = '''import importlib, importlib.metadata as m, json, os, platform, sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/"tools/testdata"))
modules=["acceptance", "acceptance_run", "acceptance_append", "acceptance_status", "acceptance_report", "acceptance_console",
         "pydantic", "httpx", "aiokafka", "asyncpg", "clickhouse_driver", "dotenv"]
for module in modules: importlib.import_module(module)
from alert_kafka import raw_alert_model
from acceptance_materials import _event_schema
info=json.loads(Path("compatibility.json").read_text())["acceptance_image"]
versions={name:m.version(name) for name in info["runtime_dependencies"]}
assert versions==info["runtime_dependencies"]
assert sys.version.split()[0]==info["profile"]["python_version"]
assert os.getuid()==int(info["profile"]["user"].split(":")[0])
print(json.dumps({"python":platform.python_version(),"machine":platform.machine(),"uid":os.getuid(),
 "imported":modules,"versions":versions,"identity_model":raw_alert_model().__name__,
 "ocsf_identity":_event_schema().canonical_source_event_id("packaging-proof"),"business_execution":False}))'''
    imported = json.loads(call([*base, '--entrypoint', 'python', config['tag'], '-c', script]))
    verified = json.loads(call([*base, '--entrypoint', 'python', config['tag'], 'deploy/investigation-test/build.py', 'verify', '--directory', '.']))
    call([*base, '--entrypoint', 'python', config['tag'], '-m', 'pip', 'check'])
    result = {'status': 'passed', 'profile_sha256': hashlib.sha256(profile_path.read_bytes()).hexdigest(),
              'image': image, 'imports': imported, 'package_verification': verified, 'receipts': receipts,
              'runtime_network': 'none', 'host_source_mounts': [], 'new_business_executions': 0, 'new_model_calls': 0,
              'not_verified': ['mounted command chains', 'target service connectivity', 'task4 real business flow', '21 native runtime']}
    with output.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert json.loads(output.read_text()) == result
    print(json.dumps({'status': 'passed', 'image_id': image['Id'], 'platform': config['platform'],
                      'dependencies': len(imported['versions']), 'package_files': verified['files']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    probe(args.profile, args.output)
