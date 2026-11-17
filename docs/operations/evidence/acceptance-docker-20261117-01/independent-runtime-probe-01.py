"""Limited final3d audit: reuse immutable mounted evidence; inspect and read/write files with04 only."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "independent-runtime-direct-01"
PACKAGE = ROOT / ".local/investigation-test-release/test-service-0.6.0-20261117-3d04"
PREVIOUS = ROOT / ".local/investigation-test-release/test-service-0.6.0-20261117-3d03"
IMAGE = "socai2-investigation-acceptance@sha256:6504fdad4ed0e965d16ee027302ddd0d666d2f13172ffa70108876dfd7bb5297"
IMAGE_ID = "sha256:d43e94a27e7d1e313bc9283a64a56ca6caa98a3582d43014c149133bf02e553c"
OLD01 = ROOT / "docs/operations/evidence/acceptance-append-20261117-01/prepared"


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def check_report(folder):
    for f in read(folder / "manifest.json")["files"]:
        assert sha(folder / f["path"]) == f["sha256"]
    return read(folder / "report.json")


freeze = read(HERE / "runtime-freeze-02/manifest.json")["files"]
for f in freeze:
    assert sha(ROOT / f["path"]) == sha(HERE / "runtime-freeze-02" / f["path"]) == f["sha256"]
package_manifest = read(PACKAGE / "package-manifest.json")
receipt = read(HERE / "source-package-04.json")
assert sha(PACKAGE / "package-manifest.json") == receipt["manifest_sha256"]
assert sha(pathlib.Path(receipt["archive"])) == receipt["archive_sha256"]
assert set(tree(PACKAGE)) == set(package_manifest["files"]) | {"package-manifest.json"}
assert all(sha(PACKAGE / p) == v["sha256"] for p, v in package_manifest["files"].items())
old_manifest = read(PREVIOUS / "package-manifest.json")
assert set(old_manifest["files"]) == set(package_manifest["files"])
changed = sorted(p for p in package_manifest["files"] if old_manifest["files"][p] != package_manifest["files"][p])
assert changed == read(HERE / "package03-to04-delta.json")["changed"]
assert all(not p.endswith((".py", ".yml", ".lock")) for p in changed)
assert "仍待实施" not in (PACKAGE / "tools/testdata/ACCEPTANCE.md").read_text().splitlines()[2]

# Independently bind the03 mounted proof to its saved source and output bytes.
mounted = HERE / "mounted-direct-02"
cfg = read(HERE / "mounted-config-02.json")
before = read(mounted / "sources-before.json")
assert before == read(mounted / "sources-after.json")
assert before == {name: tree(pathlib.Path(path)) for name, path in cfg["preserve"].items()}
mount_validation = read(mounted / "validation.json")
assert mount_validation["config_sha256"] == sha(HERE / "mounted-config-02.json")
for c in mount_validation["commands"]:
    value = read(mounted / "commands" / (c["label"] + ".json"))
    assert c["exit_code"] == value["exit_code"] == value["expected_exit"]
for name in ("streaming", "templates"):
    area = mounted / name
    preserved = read(area / "preserved.json")
    for section, path in (("config", "config"), ("converted", "conversion/converted"), ("prepared", "execution/prepared")):
        assert preserved[section] == tree(area / path)
    assert not (area / "execution/prepared/runs").exists()
for name in ("legacy02", "legacy01"):
    report = check_report(mounted / name / "output/report")
    reference = read(pathlib.Path(cfg["legacy"][name]["reference"]) / "report.json")
    report.pop("observed_at")
    reference.pop("observed_at")
    assert report == reference
for path in mounted.rglob("manifest.json"):
    if read(path).get("schema_version") == "socai2.acceptance-report-files.v1":
        check_report(path.parent)

OUT.mkdir()
(OUT / "commands").mkdir()
commands = []


def call(label, args, expected=0, stdin=None):
    returned = subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=60)
    item = {"command": args, "stdin": stdin, "exit_code": returned.returncode, "expected_exit": expected,
            "stdout": returned.stdout, "stderr": returned.stderr}
    save(OUT / "commands" / (label + ".json"), item)
    commands.append({"label": label, "exit_code": returned.returncode})
    assert returned.returncode == expected, label
    return returned.stdout


image = json.loads(call("inspect-final-image", ["docker", "image", "inspect", "--platform", "linux/amd64", IMAGE]))[0]
assert image["Id"] == IMAGE_ID and image["Config"]["User"] == "10001:10001"
assert image["Config"]["Entrypoint"] == ["python", "tools/testdata/acceptance.py"] and image["Config"]["Cmd"] == ["--help"]
runtime = ["docker", "run", "--rm", "--pull=never", "--platform", "linux/amd64", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,mode=1777"]
call("default-help", [*runtime, IMAGE])
script = '''import hashlib,importlib,importlib.metadata,json,os,pathlib,platform,sys
p=pathlib.Path.cwd();sys.path.insert(0,str(p/"tools/testdata"))
names=["acceptance","acceptance_run","acceptance_append","acceptance_status","acceptance_report","acceptance_console","pydantic","httpx","aiokafka","asyncpg","clickhouse_driver","dotenv"]
for n in names:importlib.import_module(n)
info=json.loads((p/"compatibility.json").read_text())["acceptance_image"]
versions={n:importlib.metadata.version(n) for n in info["runtime_dependencies"]}
assert versions==info["runtime_dependencies"]
manifest=json.loads((p/"package-manifest.json").read_text())
assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==v["sha256"] for n,v in manifest["files"].items())
print(json.dumps({"imports":names,"versions":versions,"python":platform.python_version(),"uid":os.getuid(),"files":len(manifest["files"]),"manifest_sha256":hashlib.sha256((p/"package-manifest.json").read_bytes()).hexdigest()}))'''
inside = json.loads(call("image-imports", [*runtime, "--entrypoint", "python", IMAGE, "-c", script]))
assert inside["manifest_sha256"] == receipt["manifest_sha256"] and inside["files"] == 109
assert inside["python"] == "3.11.17" and inside["uid"] == 10001
call("pip-check", [*runtime, "--entrypoint", "python", IMAGE, "-m", "pip", "check"])

materials, config, results = (OUT / name for name in ("materials", "config", "results"))
shutil.copytree(mounted / "templates/conversion/converted", materials)
config.mkdir()
results.mkdir()
profile = read(PACKAGE / "deploy/investigation-test/acceptance-config.example/profile.json")
execution = read(PACKAGE / "deploy/investigation-test/acceptance-config.example/execution.json")
execution["execution_id"] = "independent-docker-delivery-20261117-01"
save(config / "profile.json", profile)
save(config / "execution.json", execution)
input_hashes = {"materials": tree(materials), "config": tree(config), "old01": tree(OLD01)}
env = dict(cfg["environment"])
env.update(ACCEPTANCE_PROJECT="socai2-acceptance-independent-final", ACCEPTANCE_IMAGE=IMAGE,
           ACCEPTANCE_USER=f"{os.getuid()}:{os.getgid()}")
assert os.getuid() != 0


def environment(name, source, destination):
    values = {**env, "ACCEPTANCE_MATERIALS_DIR": str(source.resolve()), "ACCEPTANCE_CONFIG_DIR": str(config.resolve()),
              "ACCEPTANCE_RESULTS_DIR": str(destination.resolve())}
    path = OUT / (name + ".env")
    with path.open("x") as stream:
        stream.write("".join(f"{k}={v}\n" for k, v in values.items()))
    prefix = ["docker", "compose", "--env-file", str(path), "-f", str(PACKAGE / "deploy/investigation-test/acceptance.compose.yml")]
    resolved = json.loads(call(name + "-resolved", [*prefix, "config", "--format", "json"]))["services"]["acceptance"]
    assert resolved["network_mode"] == "none" and resolved["read_only"] and resolved["pull_policy"] == "never"
    assert {m["target"]: m.get("read_only", False) for m in resolved["volumes"]} == {"/materials": True, "/run/acceptance-config": True, "/results": False}
    return [*prefix, "run", "--rm", "-T", "acceptance"]


entry = environment("prepared", materials, results)
call("prepare", [*entry, "prepare", "--materials", "/materials", "--profile", "/run/acceptance-config/profile.json",
                 "--execution", "/run/acceptance-config/execution.json", "--output", "/results/prepared"])
prepared_hashes = tree(results / "prepared")
session = read(results / "prepared/session.json")
assert len(session["identities"]) == 2 and session["source_directory"] == "/materials"
call("visit1", [*entry, "session", "--prepared", "/results/prepared", "--output", "/results/visit1"], stdin="view\nquit\n")
call("visit2", [*entry, "session", "--prepared", "/results/prepared", "--output", "/results/visit2"], stdin="")
for visit, reason in (("visit1", "quit"), ("visit2", "eof")):
    end = read(results / visit / "end.json")
    assert end["reason"] == reason and end["execution_id"] == execution["execution_id"] and end["execution_attempts"] == 0
    assert not end["permanently_closed"] and not end["all_parts_completed"]
call("empty-report", [*entry, "report", "--prepared", "/results/prepared", "--output", "/results/report"])
report = check_report(results / "report")
assert report["state"] == "ready" and report["counts"]["runs"] == 0 and report["models"]["request_count"] == 0
assert tree(results / "prepared") == prepared_hashes and not (results / "prepared/runs").exists()

legacy_output = OUT / "legacy01"
legacy_output.mkdir()
legacy_entry = environment("legacy01", OLD01, legacy_output)
call("incomplete-report", [*legacy_entry, "report", "--prepared", "/materials", "--output", "/results/report"], expected=3)
incomplete = check_report(legacy_output / "report")
prior = read(mounted / "legacy01/output/report/report.json")
assert {k: v for k, v in incomplete.items() if k != "observed_at"} == {k: v for k, v in prior.items() if k != "observed_at"}
assert incomplete["parts"][0]["error_code"] == "http_status_503" and all(v is None for v in incomplete["counts"].values())
assert input_hashes == {"materials": tree(materials), "config": tree(config), "old01": tree(OLD01)}
remaining = call("own-containers-after", ["docker", "ps", "-a", "--filter", "label=com.docker.compose.project=" + env["ACCEPTANCE_PROJECT"], "--format", "{{.ID}}"])
assert not remaining.strip()
for f in freeze:
    assert sha(ROOT / f["path"]) == f["sha256"]
save(OUT / "source-hashes.json", input_hashes)
result = {"status": "passed", "freeze": "runtime-freeze-02/manifest.json", "image": IMAGE, "image_id": IMAGE_ID,
          "runtime": inside, "package_delta": changed, "reused_mounted03_commands": len(mount_validation["commands"]),
          "final04_commands": commands, "persistent_prepared_files_unchanged": len(prepared_hashes),
          "new_execution_prepared_only": execution["execution_id"], "prepared_records": 2,
          "reopened_same_execution": True, "incomplete_original_retained": True, "connection_files_present": False,
          "new_business_connections": 0, "new_business_executions": 0, "new_kafka_sends": 0, "new_model_calls": 0,
          "scope": "Final04 image and file-only command/persistence checks; reused03 mounted proof because runtime sources/Compose/lock are unchanged."}
save(OUT / "validation.json", result)
save(OUT / "evidence-hashes.json", tree(OUT))
print(json.dumps({k: result[k] for k in ("status", "image_id", "reused_mounted03_commands", "prepared_records", "reopened_same_execution", "new_business_executions")}, ensure_ascii=False))
