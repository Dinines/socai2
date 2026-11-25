"""Apply the reviewed alert Run read overlay to the existing SpiritHub API."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit


FILES = ("api/routes/socai2.py", "soc/bridge_contract.json")
FINGERPRINT = """
from hashlib import sha256
import json
from pathlib import Path
import sys

package = Path(sys.argv[1])
print(json.dumps({name: sha256((package / name).read_bytes()).hexdigest()
                  for name in sys.argv[2:]}))
"""


def run(args, *, env=None, cwd=None, timeout=20):
    result = subprocess.run(
        args, env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        raise RuntimeError(f"{args[0]} {args[1]} exited with {result.returncode}")
    return result.stdout


def inspect(container):
    return json.loads(run(["docker", "inspect", container]))[0]


def image_id(image):
    return run(["docker", "image", "inspect", "--format", "{{.Id}}", image]).strip()


def fingerprints(command, package, names):
    return json.loads(run([*command, "-B", "-c", FINGERPRINT, package, *names]))


def other_project_services(project, api):
    lines = run(
        [
            "docker", "ps", "-a", "--no-trunc",
            "--filter", f"label=com.docker.compose.project={project}",
            "--format", "{{.Names}} {{.ID}}",
        ]
    )
    return {name: identity for name, identity in (line.split() for line in lines.splitlines())
            if name != api}


def compose_environment(project):
    scanners = run(
        [
            "docker", "ps", "-a",
            "--filter", f"label=com.docker.compose.project={project}",
            "--filter", "label=com.docker.compose.service=scanner-worker",
            "--format", "{{.Names}}",
        ]
    ).splitlines()
    images = {inspect(name)["Config"]["Image"] for name in scanners}
    if len(images) != 1:
        raise RuntimeError("existing scanner image could not be resolved")
    return {**os.environ, "SPIRITHUB_GO_SCANNER_IMAGE": images.pop()}


def active_is_healthy(container, expected_image, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = inspect(container)
        health = data["State"].get("Health", {}).get("Status")
        if data["Image"] == expected_image and data["State"]["Running"] and health == "healthy":
            return True
        time.sleep(2)
    return False


def declared_routes(scope):
    origin = urlsplit(scope["release"]["platform_origin"])
    connection = HTTPConnection(origin.hostname, origin.port, timeout=8)
    try:
        connection.request("GET", "/openapi.json")
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"platform OpenAPI returned {response.status}")
        openapi = json.loads(response.read(5_000_000))
    finally:
        connection.close()
    paths = openapi["paths"]
    return {
        operation: paths[item["path"]]["get"]["operationId"] == f"socai2_{operation}"
        for operation, item in scope["added_operations"].items()
    }


def check_baseline(scope):
    runtime = scope["runtime"]
    container = inspect(runtime["container"])
    labels = container["Config"]["Labels"]
    if (
        container["Image"] != runtime["image_id"]
        or container["Config"]["Image"] != runtime["image"]
        or image_id(runtime["image"]) != runtime["image_id"]
        or not container["State"]["Running"]
        or container["State"].get("Health", {}).get("Status") != "healthy"
        or labels["com.docker.compose.project"] != runtime["compose_project"]
        or labels["com.docker.compose.service"] != "api"
        or labels["com.docker.compose.project.working_dir"] != runtime["compose_workdir"]
        or labels["com.docker.compose.project.config_files"].split(",") != runtime["compose_files"]
    ):
        raise RuntimeError("running API image or Compose chain differs from the reviewed baseline")
    change = scope["runtime_source_assessment"]
    source = fingerprints(["docker", "exec", runtime["container"], "python"],
                          change["api_package_root"], change["source_sha256"])
    if source != change["source_sha256"]:
        raise RuntimeError("running API source differs from the reviewed baseline")


def verify_candidate_source(scope, directory):
    package = Path(scope["runtime_source_assessment"]["api_package_root"])
    expected = scope["runtime_patch_after_sha256"]
    for name in FILES:
        relative = str(Path("backend/src/spirithub") / name)
        actual = sha256((directory / "source" / relative).read_bytes()).hexdigest()
        if actual != expected[relative]:
            raise RuntimeError("candidate payload source fingerprint mismatch")
    target = scope["release"]["image"]
    dockerfile = directory / "Dockerfile"
    instructions = [f"FROM {scope['runtime']['image']}"]
    instructions.extend(
        f"COPY source/backend/src/spirithub/{name} {package / name}" for name in FILES
    )
    with dockerfile.open("x") as stream:
        stream.write("\n".join(instructions) + "\n")
    run(["docker", "build", "--pull=false", "--network=none", "-t", target, str(directory)],
        timeout=180)
    fixed = image_id(target)
    base, built = json.loads(run(["docker", "image", "inspect", scope["runtime"]["image_id"], fixed]))
    layers = base["RootFS"]["Layers"]
    if built["RootFS"]["Layers"][:len(layers)] != layers:
        raise RuntimeError("candidate image does not extend the reviewed base layers")
    source = fingerprints(
        ["docker", "run", "--rm", "--network=none", "--entrypoint", "python", fixed],
        str(package), scope["runtime_source_assessment"]["source_sha256"],
    )
    wanted = dict(scope["runtime_source_assessment"]["source_sha256"])
    for name in FILES:
        wanted[name] = expected[str(Path("backend/src/spirithub") / name)]
    if source != wanted:
        raise RuntimeError("candidate image contains unexpected source fingerprints")
    return fixed, source


def compare_compose(scope, base, overlay, env, working):
    old = json.loads(run([*base, "config", "--format", "json"], env=env, cwd=working))
    new = json.loads(run([*base, "-f", str(overlay), "config", "--format", "json"],
                         env=env, cwd=working))
    expected = deepcopy(old)
    if expected["services"]["api"]["image"] != scope["runtime"]["image"]:
        raise RuntimeError("Compose base image differs from the running API")
    expected["services"]["api"]["image"] = scope["release"]["image"]
    if new != expected:
        raise RuntimeError("rendered Compose differs outside api.image")


def receipt(directory, phase, data):
    data["utc"] = datetime.now(timezone.utc).isoformat()
    with (directory / f"{phase}.json").open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    print(json.dumps(data), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "activate"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    scope = json.loads((directory / "release-scope.json").read_bytes())
    runtime = scope["runtime"]
    working = runtime["compose_workdir"]
    base = ["docker", "compose", "--project-directory", working, "-p", runtime["compose_project"]]
    for file in runtime["compose_files"]:
        base.extend(("-f", file))
    env = compose_environment(runtime["compose_project"])
    overlay = directory / "compose.alert-a-run.json"
    data = {"phase": args.phase, "ok": False}
    api = runtime["container"]
    started = False
    try:
        check_baseline(scope)
        data["baseline_source_match"] = True
        if args.phase == "prepare":
            image, source = verify_candidate_source(scope, directory)
            with overlay.open("x") as stream:
                json.dump({"services": {"api": {"image": scope["release"]["image"]}}}, stream)
                stream.write("\n")
            compare_compose(scope, base, overlay, env, working)
            data.update(ok=True, compose_diff=["services.api.image"], image_id=image,
                        image=scope["release"]["image"], source_sha256=source)
        else:
            prepared = json.loads((directory / "prepare.json").read_bytes())
            if not prepared["ok"] or image_id(prepared["image"]) != prepared["image_id"]:
                raise RuntimeError("prepared image is absent or differs from the verified image")
            compare_compose(scope, base, overlay, env, working)
            data["compose_diff"] = ["services.api.image"]
            services = other_project_services(runtime["compose_project"], api)
            started = True
            run([*base, "-f", str(overlay), "up", "-d", "--no-deps", "--no-build", "api"],
                env=env, cwd=working, timeout=60)
            if not active_is_healthy(api, prepared["image_id"], scope["release"]["health_wait_seconds"]):
                raise RuntimeError("updated API did not become healthy")
            source = fingerprints(["docker", "exec", api, "python"],
                                  scope["runtime_source_assessment"]["api_package_root"],
                                  prepared["source_sha256"])
            if source != prepared["source_sha256"]:
                raise RuntimeError("actual API source differs from the prepared package")
            routes = declared_routes(scope)
            if not all(routes.values()):
                raise RuntimeError("one or more approved GET operations were not declared")
            current = inspect(api)
            actual_chain = current["Config"]["Labels"]["com.docker.compose.project.config_files"].split(",")
            if actual_chain != [*runtime["compose_files"], str(overlay)]:
                raise RuntimeError("actual API Compose chain differs from the approved chain")
            data.update(
                ok=True, container=api, health="healthy", image=prepared["image"],
                image_id=current["Image"], source_sha256=source, declared_routes=routes,
                compose_chain=actual_chain,
                original_image_retained=image_id(runtime["image"]) == runtime["image_id"],
                other_service_ids_unchanged=services == other_project_services(runtime["compose_project"], api),
            )
    except (RuntimeError, OSError, TimeoutError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
        data["failure"] = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        if started:
            try:
                current = inspect(api)
                if current["Config"]["Image"] == scope["release"]["image"]:
                    run([*base, "up", "-d", "--no-deps", "--no-build", "api"],
                        env=env, cwd=working, timeout=60)
                    data["original_api_healthy_after_rollback"] = active_is_healthy(
                        api, runtime["image_id"], scope["release"]["health_wait_seconds"]
                    )
            except (RuntimeError, OSError, subprocess.TimeoutExpired):
                data["rollback_state"] = "unverified"
    receipt(directory, args.phase, data)
    raise SystemExit(0 if data["ok"] else 1)


if __name__ == "__main__":
    main()
