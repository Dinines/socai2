"""Inspect only the handed-off image; run isolated import/entry checks, no business."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import importlib.util

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
FROZEN = HERE / "image-freeze-01"
OUTPUT = HERE / "independent-image-probe-02.json"
PACKAGE = ROOT / ".local/investigation-test-release/test-service-0.6.0-20261117-3d01"
EXPECTED_IMAGE = "sha256:b08c83c504308d7b426d26063a39fc5cab6f7c0fbc8059976cdbe7bd2c350df2"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not OUTPUT.exists()
freeze = read(FROZEN / "manifest.json")["files"]
for f in freeze:
    assert sha(ROOT / f["path"]) == sha(FROZEN / f["path"]) == f["sha256"]
config = read(ROOT / "deploy/investigation-test/acceptance-image.json")
manifest = read(PACKAGE / "package-manifest.json")
receipt = read(HERE / "source-package-01.json")
assert sha(PACKAGE / "package-manifest.json") == receipt["manifest_sha256"]
assert sha(pathlib.Path(receipt["archive"])) == receipt["archive_sha256"]
assert {str(p.relative_to(PACKAGE)) for p in PACKAGE.rglob("*") if p.is_file()} == set(manifest["files"]) | {"package-manifest.json"}
assert all(sha(PACKAGE / name) == v["sha256"] for name, v in manifest["files"].items())
assert manifest == read(HERE / "image-package-package-manifest.json")
for f in freeze:
    if f["path"] in manifest["files"]:
        assert manifest["files"][f["path"]]["sha256"] == f["sha256"]

lock_path = ROOT / config["requirements"]
pins = {}
for line in lock_path.read_text().splitlines():
    if not line or line.startswith("#"):
        continue
    name, version, digest = re.fullmatch(r"([^=]+)==([^ ]+) --hash=sha256:([a-f0-9]{64})", line).groups()
    pins[name] = {"version": version, "sha256": digest}
downloaded = read(HERE / "dependency-lock-01.json")["wheels"]
assert len(pins) == len(downloaded) == 19
for wheel in downloaded:
    assert pins[wheel["name"]] == {"version": wheel["version"], "sha256": wheel["sha256"]}
    assert sha(ROOT / ".local/acceptance-docker-20261117-01/wheels" / wheel["wheel"]) == wheel["sha256"]

# Optional acceptance image must not change the existing serve Dockerfile.
spec = importlib.util.spec_from_file_location("independent_builder", FROZEN / "deploy/investigation-test/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory(prefix="socai2-legacy-package-check-") as temporary:
    profile = read(ROOT / "deploy/investigation-test/package-build.json")
    profile.pop("acceptance_image")
    profile["output_dir"] = temporary
    selected = pathlib.Path(temporary) / "build.json"
    selected.write_text(json.dumps(profile))
    old = builder.build(selected, root=ROOT)
    legacy = pathlib.Path(old["archive"]).parent / profile["release"]
    assert (legacy / "Dockerfile").read_bytes() == (PACKAGE / "Dockerfile").read_bytes()
    assert not (legacy / "Dockerfile.acceptance").exists()
    assert "acceptance_image" not in read(legacy / "compatibility.json")
    legacy_receipt = {"status": old["status"], "old_serve_dockerfile_unchanged": True,
                      "optional_image_omitted": True}

commands = []


def call(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    commands.append({"command": args, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    if result.returncode:
        with OUTPUT.open("x") as stream:
            json.dump({"status": "check_failed", "receipts": commands}, stream, ensure_ascii=False, indent=2)
        raise RuntimeError("image check failed; original receipts preserved")
    return result.stdout


base = json.loads(call(["docker", "image", "inspect", "--platform", config["platform"], config["base_ref"]]))[0]
assert base["Id"] == config["base_id"]
actual = json.loads(call(["docker", "image", "inspect", "--platform", config["platform"], config["tag"]]))[0]
assert actual["Id"] == EXPECTED_IMAGE
assert actual["Os"] + "/" + actual["Architecture"] == config["platform"]
assert actual["Config"]["User"] == config["user"]
assert actual["Config"]["WorkingDir"] == config["workdir"]
assert actual["Config"]["Entrypoint"] == ["python", "tools/testdata/acceptance.py"]
assert actual["Config"]["Cmd"] == ["--help"]
runtime_image = actual["RepoDigests"][0]
assert json.loads(call(["docker", "image", "inspect", "--platform", config["platform"], runtime_image]))[0]["Id"] == EXPECTED_IMAGE
runtime = ["docker", "run", "--rm", "--pull=never", "--platform", config["platform"], "--network", "none",
           "--read-only", "--tmpfs", "/tmp:rw,mode=1777"]
help_text = call([*runtime, runtime_image])
for command in ("convert", "inspect", "prepare", "run", "append", "status", "report", "session"):
    assert command in help_text

script = '''import contextlib, hashlib, importlib, importlib.metadata, io, json, os, pathlib, platform, socket, sys
root=pathlib.Path.cwd()
sys.path.insert(0,str(root/"tools/testdata"))
attempts=[]
def forbidden(*a,**k):
    attempts.append("socket")
    raise AssertionError("business network forbidden")
socket.socket.connect=forbidden
socket.socket.connect_ex=forbidden
socket.create_connection=forbidden
modules=["acceptance", "acceptance_run", "acceptance_append", "acceptance_status", "acceptance_report", "acceptance_console", "pydantic", "httpx", "aiokafka", "asyncpg", "clickhouse_driver", "dotenv"]
for name in modules: importlib.import_module(name)
info=json.loads((root/"compatibility.json").read_text())["acceptance_image"]
versions={n:importlib.metadata.version(n) for n in info["runtime_dependencies"]}
assert versions==info["runtime_dependencies"]
assert platform.python_version()==info["profile"]["python_version"]
assert os.getuid()==int(info["profile"]["user"].split(":")[0])
m=json.loads((root/"package-manifest.json").read_text())
files={str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
assert files==set(m["files"])|{"package-manifest.json"}
assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v["sha256"] for n,v in m["files"].items())
from alert_kafka import raw_alert_model
from acceptance_materials import _event_schema
assert raw_alert_model().__name__=="RawAlert"
assert _event_schema().canonical_source_event_id("container-review")=="container-review"
from acceptance import main
parsed=[]
for command in info["commands"]:
    with contextlib.redirect_stdout(io.StringIO()):
        try: main([command,"--help"])
        except SystemExit as exc: assert exc.code==0
    parsed.append(command)
assert not attempts
print(json.dumps({"python":platform.python_version(),"machine":platform.machine(),"uid":os.getuid(),"gid":os.getgid(),"versions":versions,"imports":modules,"parsed_commands":parsed,"network_attempts":attempts,"package_files":len(m["files"]),"manifest_sha256":hashlib.sha256((root/"package-manifest.json").read_bytes()).hexdigest(),"identity_and_ocsf_load":"passed"}))'''
inside = json.loads(call([*runtime, "--entrypoint", "python", runtime_image, "-c", script]))
assert inside["manifest_sha256"] == receipt["manifest_sha256"]
assert inside["package_files"] == 99
call([*runtime, "--entrypoint", "python", runtime_image, "-m", "pip", "check"])
for f in freeze:
    assert sha(ROOT / f["path"]) == f["sha256"]
result = {"status": "passed", "scope": "3d step1 DK01/necessary DK02 only", "freeze": "image-freeze-01/manifest.json",
          "image_id": actual["Id"], "runtime_reference": runtime_image, "base_ref": config["base_ref"], "base_id": base["Id"], "platform": config["platform"],
          "host_machine": subprocess.check_output(["uname", "-m"], text=True).strip(),
          "package_archive_sha256": receipt["archive_sha256"], "package_manifest_sha256": receipt["manifest_sha256"],
          "locked_wheels_checked": len(downloaded), "legacy_serve_compatibility": legacy_receipt,
          "runtime": inside, "receipts": commands, "host_mounts": [], "runtime_network": "none", "root_filesystem": "read_only",
          "new_business_connections": 0, "new_business_executions": 0, "new_model_calls": 0,
          "not_verified": ["step2 mounted command chains", "persistence after container removal", "real service connections", "task4", "21 native execution"]}
with OUTPUT.open("x") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({k: result[k] for k in ("status", "scope", "image_id", "platform", "host_machine", "locked_wheels_checked", "new_business_executions")}, ensure_ascii=False))
