"""Build/verify the frozen candidate locally on its target architecture, without a service switch."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_release(directory):
    directory = Path(directory).resolve(strict=True)
    raw = (directory / "manifest.json").read_bytes()
    manifest = json.loads(raw)
    if manifest["format"] != "socai2.processing-release.v1.2" or manifest["release"] != directory.name:
        raise ValueError("Release identity mismatch")
    actual = {str(path.relative_to(directory)) for path in directory.rglob("*") if path.is_file()}
    if actual != {"manifest.json", *manifest["files"]}:
        raise ValueError("Release contains missing or unexpected files")
    for name, description in manifest["files"].items():
        path = directory / name
        if (path.resolve(strict=True) != path or not path.is_relative_to(directory)
                or sha256(path.read_bytes()) != description["sha256"] or path.stat().st_size != description["bytes"]):
            raise ValueError("Release source mismatch: " + name)
    return directory, manifest, sha256(raw)


def command(args, timeout=60, env=None):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=timeout, env=env).stdout.strip()


def inspect(tag):
    return json.loads(command(["docker", "image", "inspect", tag]))[0]


IMAGE_CHECK = r'''
import hashlib, importlib.util, json, os, pathlib, runpy, sys
root=pathlib.Path('/opt/processor')
raw=(root/'manifest.json').read_bytes()
manifest=json.loads(raw)
assert hashlib.sha256(raw).hexdigest() == sys.argv[1]
verified=[]
for prefix, directory in [('app', pathlib.Path('/app/app')), ('smoke-fusion/app', root/'smoke-fusion/app')]:
    actual={prefix+'/'+str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
    expected={name for name in manifest['files'] if name.startswith(prefix+'/')}
    assert actual==expected, 'unexpected or missing application files'
for name, record in manifest['files'].items():
    if name in {'Dockerfile', 'build_processing_image.py'}:
        continue
    path=pathlib.Path('/app')/name if name.startswith('app/') else root/name
    data=path.read_bytes()
    assert hashlib.sha256(data).hexdigest()==record['sha256'] and len(data)==record['bytes'],name
    if name.endswith('.py'):
        compile(data, str(path), 'exec')
    verified.append(name)
os.environ['SOCAI2_INVESTIGATION_POLICY']=str(root/'investigation-policy.toml')
spec=importlib.util.spec_from_file_location('candidate_policy', '/app/app/socai2/runtime_policy.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
policy=module.load_policy(root/'investigation-policy.toml')
assert policy.sha256 == manifest['policy_sha256']
result=runpy.run_path(str(root/'processing_job.py'))['self_test']()
assert result['database_writes']==result['model_calls']==0
print(json.dumps({'verified_source_count':len(verified), 'policy_sha256':policy.sha256,
    'database_tls_source_sha256':manifest['files']['app/db/database.py']['sha256'],
    'self_test':result, 'network':'none'}))
'''


def build(directory, *, verify_only=False):
    directory, manifest, digest = verify_release(directory)
    configured = manifest["image"]
    base = inspect(configured["base_tag"])
    if (base["Id"] != configured["base_id"]
            or base["Os"] + "/" + base["Architecture"] != configured["platform"]):
        raise ValueError("Configured base image or architecture changed")
    existing = command(["docker", "image", "ls", "--quiet", configured["tag"]])
    if not existing:
        if verify_only:
            raise ValueError("Candidate image missing")
        command(["docker", "build", "--network=none", "--pull=false", "--platform", configured["platform"],
            "--build-arg", "BASE_IMAGE=" + base["Id"], "--build-arg", "RUNTIME_USER=" + configured["user"],
            "--label", "socai2.processing.release=" + digest, "--tag", configured["tag"], str(directory)],
            timeout=configured["build_timeout_seconds"], env={**os.environ, "DOCKER_BUILDKIT": str(int(configured["buildkit"]))})
    image = inspect(configured["tag"])
    if (image["Config"].get("Labels", {}).get("socai2.processing.release") != digest
            or image["Config"]["User"] != configured["user"]
            or image["Os"] + "/" + image["Architecture"] != configured["platform"]
            or image["Config"]["Entrypoint"] != ["python", "-B", "/opt/processor/processing_job.py"]
            or image["RootFS"]["Layers"][:len(base["RootFS"]["Layers"])] != base["RootFS"]["Layers"]):
        raise ValueError("Candidate tag already points to another image or base")
    checked = command(["docker", "run", "--rm", "--network=none", "--read-only", "--entrypoint", "python",
        image["Id"], "-B", "-c", IMAGE_CHECK, digest])
    return {"release": manifest["release"], "manifest_sha256": digest, "image_id": image["Id"],
        "image_tag": configured["tag"], "platform": configured["platform"], "base_image_id": base["Id"],
        "services_changed": False, **json.loads(checked.splitlines()[-1])}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-directory", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.release_directory, verify_only=args.verify_only)))
