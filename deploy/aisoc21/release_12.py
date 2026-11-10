"""Freeze, build and deploy the investigation services from one explicit release file.

No migrations, offset resets, tenant creation or model jobs. Runtime credentials
stay in existing host configuration and private rollback snapshots.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import tomllib


def digest(data):
    return hashlib.sha256(data).hexdigest()


def need(value, code):
    if not value:
        raise ValueError(code)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value, *, private=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(data)
        os.chmod(temporary, 0o600 if private else 0o644)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def command(args, *, timeout=60, env=None, body=None):
    result = subprocess.run(args, text=True, capture_output=True, input=body, timeout=timeout, env=env, check=False)
    if result.returncode:
        # Full stderr can contain connection settings. It stays private.
        error = Path(tempfile.gettempdir()) / ("socai2-release-error-" + str(os.getpid()) + ".log")
        error.write_text(result.stdout + result.stderr)
        error.chmod(0o600)
        raise ValueError("command_failed_exit_" + str(result.returncode) + "_private_log_" + str(error))
    return result.stdout.strip()


def inspect(name):
    return json.loads(command(["docker", "inspect", name]))[0]


def freeze(config_path, output):
    cfg = read(config_path)
    need(cfg["version"] == "socai2.release.v1.2", "unsupported_release")
    root = Path(__file__).resolve().parents[2]
    output = Path(output).resolve()
    need(not output.exists(), "release_exists_use_new_id")
    files = {}
    for item in cfg["build"].values():
        folder = root / item["source"]
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            need(path.resolve() == path and not any(p.startswith(".") for p in path.relative_to(root).parts), "unsafe_source")
            files[str(path.relative_to(root))] = path.read_bytes()
    for name in cfg["files"]:
        path = root / name
        need(path.resolve() == path and path.is_file(), "missing_release_file")
        files[name] = path.read_bytes()
    for name in ("deploy/aisoc21/release_12.py",):
        files[name] = (root / name).read_bytes()
    files["release.json"] = (json.dumps(cfg, indent=2) + "\n").encode()
    output.mkdir(parents=True)
    for name, data in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o644)
    manifest = {"release": cfg["release"], "version": cfg["version"],
        "source_basis": "working tree; complete source file hashes include uncommitted changes",
        "source_commit": command(["git", "-C", str(root), "rev-parse", "HEAD"]),
        "files": {name: digest(data) for name, data in sorted(files.items())}}
    write(output / "manifest.json", manifest)
    return {"release": cfg["release"], "files": len(files), "manifest_sha256": digest((output / "manifest.json").read_bytes())}


def verify_files(folder):
    cfg, manifest = read(folder / "release.json"), read(folder / "manifest.json")
    need(cfg["release"] == manifest["release"] and cfg["version"] == manifest["version"], "release_identity_mismatch")
    for name, expected in manifest["files"].items():
        path = folder / name
        need(path.is_relative_to(folder) and path.resolve() == path and digest(path.read_bytes()) == expected,
             "source_changed_" + name)
    return cfg, manifest, digest((folder / "manifest.json").read_bytes())


HASH_APP = """import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);r={}
for f in p.rglob('*'):
 if f.is_file() and '__pycache__' not in f.parts:
  b=f.read_bytes();r[str(f.relative_to(p))]=hashlib.sha256(b).hexdigest()
  if f.suffix=='.py':compile(b,str(f),'exec')
print(json.dumps(r))
"""


def build(folder):
    cfg, manifest, sha = verify_files(folder)
    images = {}
    for name, item in cfg["build"].items():
        base = json.loads(command(["docker", "image", "inspect", item["base_id"]]))[0]
        need(base["Id"] == item["base_id"] and base["Architecture"] == cfg["architecture"], "base_image_mismatch")
        existing = command(["docker", "image", "ls", "--quiet", item["tag"]])
        if not existing:
            with tempfile.TemporaryDirectory() as temporary:
                context = Path(temporary)
                shutil.copytree(folder / item["source"], context / "app")
                (context / "Dockerfile").write_text(
                    "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nUSER 0:0\n"
                    "RUN rm -rf /app/app\nCOPY --chown=" + item["user"] + " app /app/app\n"
                    "ENV PYTHONDONTWRITEBYTECODE=1\nUSER " + item["user"] + "\n")
                command(["docker", "build", "--network=none", "--pull=false", "--build-arg", "BASE_IMAGE=" + base["Id"],
                    "--label", "socai2.release=" + sha, "--tag", item["tag"], str(context)],
                    timeout=cfg["build_timeout_seconds"], env={**os.environ, "DOCKER_BUILDKIT": "0"})
        image = json.loads(command(["docker", "image", "inspect", item["tag"]]))[0]
        need(image["Config"].get("Labels", {}).get("socai2.release") == sha and image["Config"]["User"] == item["user"],
             "candidate_image_collision")
        actual = json.loads(command(["docker", "run", "--rm", "--network=none", "--read-only", "--entrypoint", "python",
            image["Id"], "-B", "-c", HASH_APP, "/app/app"]))
        expected = {path.removeprefix(item["source"] + "/"): value for path, value in manifest["files"].items()
                    if path.startswith(item["source"] + "/")}
        need(actual == expected, "image_source_mismatch_" + name)
        images[name] = {"id": image["Id"], "tag": item["tag"], "files": len(actual)}
    write(folder / "images.json", {"manifest_sha256": sha, "images": images})
    return {"release": cfg["release"], "manifest_sha256": sha, "images": images, "network": "none", "services_changed": False}


def compose(project, files):
    args = ["docker", "compose", "--project-directory", project["directory"], "-p", project["name"]]
    for path in files:
        args += ["-f", path]
    return args


def service_environment(service):
    image = json.loads(command(["docker", "image", "inspect", service["image"]]))[0]
    return {**dict(v.split("=", 1) for v in image["Config"].get("Env", [])),
            **{k: str(v) for k, v in service.get("environment", {}).items()}}


def runtime_matches(project, rendered, name, current):
    """Prove the saved rollback describes the running instance before accepting it."""
    service = rendered["services"][name]
    image = json.loads(command(["docker", "image", "inspect", current["Image"]]))[0]["Config"]
    config, host = current["Config"], current["HostConfig"]
    need(service_environment(service) == dict(v.split("=", 1) for v in config["Env"]), "runtime_environment_drift_" + name)
    for key, actual in (("command", config.get("Cmd")), ("entrypoint", config.get("Entrypoint")),
                        ("user", config.get("User")), ("working_dir", config.get("WorkingDir"))):
        fallback = image.get({"command": "Cmd", "entrypoint": "Entrypoint", "user": "User", "working_dir": "WorkingDir"}[key])
        configured = service.get(key)
        need((fallback if configured is None else configured) == actual, "runtime_" + key + "_drift_" + name)
    mounts = {(v["source"], v["target"], not v.get("read_only", False), v["type"]) for v in service.get("volumes", [])}
    actual_mounts = {(m["Source"], m["Destination"], m["RW"], m["Type"]) for m in current["Mounts"] if m["Type"] != "tmpfs"}
    need(mounts == actual_mounts, "runtime_mount_drift_" + name)
    ports = {(str(v["target"]) + "/" + v.get("protocol", "tcp"), v.get("host_ip", ""), str(v["published"]))
             for v in service.get("ports", [])}
    actual_ports = {(p, v.get("HostIp", ""), v["HostPort"]) for p, values in (host.get("PortBindings") or {}).items() for v in values or []}
    need(ports == actual_ports and service.get("read_only", False) == host["ReadonlyRootfs"], "runtime_ports_or_rootfs_drift_" + name)
    need(set(service.get("cap_drop", [])) == {v.removeprefix("CAP_") for v in host.get("CapDrop") or []}
         and set(service.get("security_opt", [])) == set(host.get("SecurityOpt") or []), "runtime_security_drift_" + name)
    if "network_mode" in service:
        need(service["network_mode"] == host["NetworkMode"], "runtime_network_drift_" + name)
    else:
        networks = {rendered["networks"][n]["name"] for n in service.get("networks", {})}
        need(networks == set(current["NetworkSettings"]["Networks"]), "runtime_network_drift_" + name)
    need(int(service.get("mem_limit", 0)) == host["Memory"], "runtime_memory_drift_" + name)
    if "pids_limit" in service:
        need(int(service["pids_limit"]) == host["PidsLimit"], "runtime_pids_drift_" + name)
    need(service.get("restart", "no").split(":")[0] == host["RestartPolicy"]["Name"], "runtime_restart_drift_" + name)


def require_runtime_flags(cfg):
    for container, expected in cfg.get("required_environment", {}).items():
        env = dict(v.split("=", 1) for v in inspect(container)["Config"]["Env"])
        need(all(env.get(k) == v for k, v in expected.items()), "background_configuration_drift_" + container)


def processing_environment_overlay(change, cfg):
    desired = dict(change.get("override", {}))
    if change.get("use_processing_environment"):
        values = dict(line.split("=", 1) for line in Path(cfg["processing"]["api_model_env"]).read_text().splitlines() if "=" in line)
        need(set(values) == set(cfg["processing"]["api_model_keys"]), "processing_environment_keys_changed")
        need(set(values) <= set(change.get("allowed_env_changes", [])), "processing_environment_not_authorized")
        explicit = desired.get("environment", {})
        need(all(explicit.get(k, v) == v for k, v in values.items()), "processing_environment_override_conflict")
        # An existing rendered Compose file already contains environment values.
        # They override env_file, so explicitly replace only the configured keys.
        desired["environment"] = {**explicit, **values}
    return desired


def verify_processing_policy(cfg):
    check = cfg.get("processing_policy_check")
    if not check:
        return None
    selected = tomllib.loads(Path(cfg["processing"]["profile"]).read_text())
    code = """import json,os,sys
from app.core.config import settings
from app.socai2.runtime_policy import active_policy
p=active_policy()
print(json.dumps({'path':os.environ.get('SOCAI2_INVESTIGATION_POLICY'),
 'sha256':p.sha256,'configured_sha256':os.environ.get('SOCAI2_INVESTIGATION_POLICY_SHA256'),
 'profiles':{name:getattr(getattr(p,name,None),'version',None) for name in json.loads(sys.argv[1])},
 'read_flags':{name:getattr(settings,name) for name in ('SOCAI2_PAGE_READ_ENABLED','SOCAI2_ANALYSIS_READ_ENABLED')}}))
"""
    actual = json.loads(command(["docker", "exec", check["container"], "python", "-B", "-c", code,
                                 json.dumps(list(check["profiles"]))]))
    expected = digest(Path(selected["paths"]["policy_file"]).read_bytes())
    need(actual["path"] == selected["paths"]["policy_mount"]
         and actual["sha256"] == actual["configured_sha256"] == expected
         and actual["profiles"] == check["profiles"]
         and ("read_flags" not in check or actual["read_flags"] == check["read_flags"]), "runtime_processing_policy_mismatch")
    return actual


def verify_api_reader(folder, cfg):
    selected = cfg.get("api_reader_check")
    if not selected:
        return None
    output = command(["python3", "-B", str(folder / "deploy/database/install_reader.py"),
                      "verify", "--profile", selected["profile"]], timeout=120)
    need("verified_socai2_v1_2_reader" in output.splitlines(), "api_reader_permissions_not_ready")
    return {"profile": selected["profile"], "verified": True, "writes": 0}


def configure_processing(folder, cfg, state):
    selected = tomllib.loads(Path(cfg["processing"]["profile"]).read_text())
    private = Path(selected["paths"]["private_dir"])
    # This is an upgrade of existing identities; never invoke first installation.
    for name in cfg["processing"]["required_existing_secrets"]:
        need((private / name).is_file(), "existing_processing_identity_required")
    backup = {str(private / name): base64.b64encode((private / name).read_bytes()).decode()
              for name in ("runtime.env", "ingress.env")}
    write(state / "processing-before.json", backup, private=True)
    write(state / "pointers-before.json", {key: str(Path(cfg[key]).resolve()) if Path(cfg[key]).is_symlink() else None
          for key in ("current_pointer",)}, private=True)
    write(state / "entry-before.json", {"target": str(Path(cfg["processing"]["entry"]).resolve())}, private=True)
    launcher = folder / "deploy/aisoc21/production_processing.py"
    command(["python3", "-B", str(launcher), "--profile", cfg["processing"]["profile"], "install"], timeout=120)
    check = json.loads(command(["python3", "-B", str(launcher), "--profile", cfg["processing"]["profile"], "check"], timeout=120).splitlines()[-1])
    need(check.get("model_calls") == 0 and check.get("check") == "schema_identity_and_source_readback", "processing_check_failed")
    values = dict(line.split("=", 1) for line in (private / "runtime.env").read_text().splitlines() if "=" in line)
    api_env = Path(cfg["processing"]["api_model_env"])
    need(not api_env.exists(), "api_model_environment_already_exists")
    api_env.write_text("".join(k + "=" + values[k] + "\n" for k in cfg["processing"]["api_model_keys"]))
    api_env.chmod(0o600)
    write(state / "processing-check.json", check)


def prepare_host(folder):
    cfg, _, sha = verify_files(folder)
    require_runtime_flags(cfg)
    built = read(folder / "images.json")
    need(built["manifest_sha256"] == sha, "images_not_from_release")
    state = Path(cfg["state_dir"])
    need(not state.exists(), "release_already_prepared")
    state.mkdir(mode=0o700, parents=True)
    targets, before = {}, {}
    # First prove all existing runtime definitions, before any configuration write.
    for name, project in cfg["projects"].items():
        original = json.loads(command(compose(project, project["files"]) + ["config", "--format", "json"]))
        for service, change in project["services"].items():
            current = inspect(change["container"])
            need(current["Image"] == change["expected_image"], "runtime_image_drift_" + service)
            runtime_matches(project, original, service, current)
            original["services"][service]["image"] = current["Image"]
        before[name] = original
        write(state / (name + "-before.json"), original, private=True)
    configure_processing(folder, cfg, state)
    hashes = {str(folder / "images.json"): digest((folder / "images.json").read_bytes())}
    selected = tomllib.loads(Path(cfg["processing"]["profile"]).read_text())
    private = Path(selected["paths"]["private_dir"])
    for path in (private / "runtime.env", private / "ingress.env", Path(cfg["processing"]["api_model_env"])):
        hashes[str(path)] = digest(path.read_bytes())
    for name, project in cfg["projects"].items():
        original = before[name]
        overlay = {"services": {}}
        for service, change in project["services"].items():
            current = inspect(change["container"])
            need(current["Image"] == change["expected_image"], "runtime_image_drift_" + service)
            desired = processing_environment_overlay(change, cfg)
            desired["image"] = built["images"][change["build"]]["id"] if "build" in change else change["image"]
            image = json.loads(command(["docker", "image", "inspect", desired["image"]]))[0]
            need(image["Id"] == desired["image"], "immutable_target_required")
            overlay["services"][service] = desired
            original["services"][service]["image"] = current["Image"]
        overlay_file = state / (name + "-overlay.json")
        write(overlay_file, overlay, private=True)
        rendered = json.loads(command(compose(project, project["files"] + [str(overlay_file)]) + ["config", "--format", "json"]))
        for service, change in project["services"].items():
            current = inspect(change["container"])
            oldenv = dict(v.split("=", 1) for v in current["Config"]["Env"])
            newenv = service_environment(rendered["services"][service])
            allowed = set(change.get("override", {}).get("environment", {})) | set(change.get("allowed_env_changes", []))
            need(not {k for k in oldenv.keys() | newenv.keys() if oldenv.get(k) != newenv.get(k)} - allowed,
                 "unexpected_environment_change_" + service)
            old, new = original["services"][service], rendered["services"][service]
            mutable = {"image", "environment", "volumes", "env_file"}
            need(all(old.get(k) == new.get(k) for k in old.keys() | new.keys() if k not in mutable),
                 "unexpected_service_definition_change_" + service)
            replaced = {v.split(":")[1] for v in change.get("override", {}).get("volumes", [])}
            oldmounts = {v["target"]: v for v in old.get("volumes", [])}
            newmounts = {v["target"]: v for v in new.get("volumes", [])}
            need(all(newmounts.get(k) == v for k, v in oldmounts.items() if k not in replaced), "unexpected_mount_change_" + service)
            targets[change["container"]] = {"project": name, "service": service,
                "before_id": current["Id"], "before_image": current["Image"], "target_image": overlay["services"][service]["image"]}
        # Subsequent rollout uses only this effective configuration, not old layers.
        effective = state / (name + "-after.json")
        write(effective, rendered, private=True)
        hashes[str(effective)] = digest(effective.read_bytes())
    need(inspect(cfg["agents_container"])["State"]["Status"] == "running", "agents_not_running")
    env = dict(v.split("=", 1) for v in inspect(cfg["agents_container"])["Config"]["Env"])
    need(env.get("AISOC_AGENT_KAFKA_DISABLE") == "1" and not env.get("AISOC_TRIAGE_BUDGET_POLICY_FILE"), "consumer_must_stay_paused_and_unlimited")
    write(state / "targets.json", targets, private=True)
    hashes[str(state / "targets.json")] = digest((state / "targets.json").read_bytes())
    write(state / "prepared.json", {"manifest_sha256": sha, "hashes": hashes}, private=True)
    return {"release": cfg["release"], "targets": targets, "consumer_enabled": False, "model_calls": 0}


def preflight(folder):
    cfg, _, sha = verify_files(folder)
    require_runtime_flags(cfg)
    checked = []
    for project in cfg["projects"].values():
        rendered = json.loads(command(compose(project, project["files"]) + ["config", "--format", "json"]))
        for service, change in project["services"].items():
            current = inspect(change["container"])
            need(current["Image"] == change["expected_image"], "runtime_image_drift_" + service)
            runtime_matches(project, rendered, service, current)
            checked.append(change["container"])
    return {"release": cfg["release"], "manifest_sha256": sha, "runtime_definitions_verified": checked,
            "api_reader": verify_api_reader(folder, cfg), "runtime_changes": False}


def rollout(folder, project_name, service):
    cfg, _, sha = verify_files(folder)
    require_runtime_flags(cfg)
    state = Path(cfg["state_dir"])
    prepared = read(state / "prepared.json")
    need(prepared["manifest_sha256"] == sha and all(digest(Path(p).read_bytes()) == h for p, h in prepared["hashes"].items()),
         "prepared_release_drift")
    project = cfg["projects"][project_name]
    target = read(Path(cfg["state_dir"]) / "targets.json")[project["services"][service]["container"]]
    current = inspect(project["services"][service]["container"])
    need(current["Image"] in {target["before_image"], target["target_image"]}, "runtime_image_drift")
    # Configuration-only releases can keep the same image (e.g. gateway).
    stage = "before" if current["Id"] == target["before_id"] else "after"
    runtime_matches(project, read(state / (project_name + "-" + stage + ".json")), service, current)
    command(compose(project, [str(state / (project_name + "-after.json"))])
        + ["up", "-d", "--no-deps", "--no-build", "--pull", "never", service], timeout=cfg["deploy_timeout_seconds"])
    return {"service": service, "container": project["services"][service]["container"], "target_image": target["target_image"]}


def verify(folder, *, check_pointer=True):
    cfg, manifest, sha = verify_files(folder)
    require_runtime_flags(cfg)
    prepared_state = read(Path(cfg["state_dir"]) / "prepared.json")
    need(prepared_state["manifest_sha256"] == sha and all(digest(Path(p).read_bytes()) == h for p,h in prepared_state["hashes"].items()),
         "prepared_release_drift")
    expected = read(folder / "images.json")["images"]
    result = {}
    for project in cfg["projects"].values():
        for service, change in project["services"].items():
            current = inspect(change["container"])
            target = expected[change["build"]]["id"] if "build" in change else change["image"]
            need(current["Image"] == target and current["State"]["Status"] == "running"
                 and current["State"].get("Health", {}).get("Status") == "healthy", "service_not_ready_" + service)
            prepared = read(Path(cfg["state_dir"]) / (next(k for k,v in cfg["projects"].items() if v is project) + "-after.json"))
            runtime_matches(project, prepared, service, current)
            if "build" in change:
                source = cfg["build"][change["build"]]["source"]
                actual = json.loads(command(["docker", "exec", change["container"], "python", "-B", "-c", HASH_APP, "/app/app"]))
                need(actual == {p.removeprefix(source + "/"): value for p, value in manifest["files"].items()
                                if p.startswith(source + "/")}, "runtime_source_mismatch_" + service)
            result[service] = {"container": change["container"], "image": current["Image"], "health": "healthy"}
            # Bind sources are part of this same release; verify inside the process namespace.
            bound = {}
            for mount in current["Mounts"]:
                source = Path(mount["Source"])
                if not source.is_relative_to(folder):
                    continue
                need(not mount["RW"], "release_source_mount_not_readonly")
                for name, expected_sha in manifest["files"].items():
                    path = folder / name
                    if path == source or source.is_dir() and path.is_relative_to(source):
                        destination = mount["Destination"] if path == source else str(Path(mount["Destination"]) / path.relative_to(source))
                        bound[destination] = expected_sha
            if bound:
                code = "import hashlib,json,pathlib,sys; d=json.loads(sys.stdin.read()); print(json.dumps({p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in d}))"
                actual = json.loads(command(["docker", "exec", "-i", change["container"], "python", "-B", "-c", code], body=json.dumps(bound)))
                need(actual == bound, "runtime_bound_source_mismatch_" + service)
                result[service]["verified_bound_files"] = len(bound)
    env = dict(v.split("=", 1) for v in inspect(cfg["agents_container"])["Config"]["Env"])
    need(env.get("AISOC_AGENT_KAFKA_DISABLE") == "1" and not env.get("AISOC_TRIAGE_BUDGET_POLICY_FILE"), "agents_flags_changed")
    check = json.loads(command(["python3", "-B", str(folder / "deploy/aisoc21/production_processing.py"),
        "--profile", cfg["processing"]["profile"], "check"], timeout=120).splitlines()[-1])
    need(check.get("model_calls") == 0 and check.get("check") == "schema_identity_and_source_readback", "processing_check_failed")
    if check_pointer:
        need(Path(cfg["current_pointer"]).resolve() == folder and Path(cfg["processing"]["entry"]).resolve()
             == folder / "deploy/aisoc21/production_entry.py", "current_release_pointer_mismatch")
    policy = verify_processing_policy(cfg)
    return {"release": cfg["release"], "manifest_sha256": sha, "services": result,
            "processing_policy": policy, "api_reader": verify_api_reader(folder, cfg),
            "consumer_enabled": False, "tenant_quota_unlimited": True}


def activate(folder):
    result = verify(folder, check_pointer=False)
    cfg = read(folder / "release.json")
    for path, target in ((Path(cfg["processing"]["entry"]), folder / "deploy/aisoc21/production_entry.py"),
                         (Path(cfg["current_pointer"]), folder)):
        need(not path.exists() or path.is_symlink(), "foreign_current_pointer")
        temporary = path.with_name("." + path.name + ".next")
        temporary.symlink_to(target)
        temporary.replace(path)
    return {**result, "current_release": cfg["current_pointer"], "processing_entry": cfg["processing"]["entry"]}


def rollback(folder):
    cfg, _, _ = verify_files(folder)
    state = Path(cfg["state_dir"])
    for path, data in read(state / "processing-before.json").items():
        target = Path(path)
        target.write_bytes(base64.b64decode(data, validate=True))
        target.chmod(0o600)
    restored = []
    for name, project in cfg["projects"].items():
        for service in project["services"]:
            command(compose(project, [str(state / (name + "-before.json"))])
                + ["up", "-d", "--no-deps", "--no-build", "--pull", "never", service], timeout=cfg["deploy_timeout_seconds"])
            restored.append(service)
    entries = {cfg["processing"]["entry"]: read(state / "entry-before.json")["target"],
               cfg["current_pointer"]: read(state / "pointers-before.json")["current_pointer"]}
    for filename, target in entries.items():
        path = Path(filename)
        need(not path.exists() or path.is_symlink(), "foreign_current_pointer")
        if target is None:
            path.unlink(missing_ok=True)
        else:
            temporary = path.with_name("." + path.name + ".rollback")
            temporary.symlink_to(target)
            temporary.replace(path)
    return {"release": cfg["release"], "rollback_services": restored, "health_verification_required": True}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["freeze", "build", "preflight", "prepare", "rollout", "activate", "rollback", "verify"])
    ap.add_argument("--config")
    ap.add_argument("--directory", required=True)
    ap.add_argument("--project")
    ap.add_argument("--service")
    args = ap.parse_args()
    folder = Path(args.directory).resolve()
    if args.mode == "freeze":
        result = freeze(args.config, folder)
    elif args.mode == "build":
        result = build(folder)
    elif args.mode == "prepare":
        result = prepare_host(folder)
    elif args.mode == "preflight":
        result = preflight(folder)
    elif args.mode == "rollout":
        result = rollout(folder, args.project, args.service)
    elif args.mode == "activate":
        result = activate(folder)
    elif args.mode == "rollback":
        result = rollback(folder)
    else:
        result = verify(folder)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- bounded operator errors; private logs retain subprocess details
        print(json.dumps({"error": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}))
        sys.exit(1)
