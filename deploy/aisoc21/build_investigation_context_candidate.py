#!/usr/bin/env python3
"""Plan or build the reviewed 19-file candidate; never deploy or start it.

The default only validates local files and prints JSON. --check-parents reads
local Docker metadata; --execute additionally builds two new local images.
The classic daemon builder is the default. An explicit --local-buildkit-builder
may select an existing docker-driver builder after its single endpoint is
verified against the same local socket. No automatic builder fallback occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
# Bind the exact reviewed batch, not merely a self-consistent source manifest.
EXPECTED_MANIFEST_SHA256 = "827f54b729925a9110bc21d9b0254ab3eb09aa68eea430891d0f4fe68b24f193"
PARENTS = {
    "api": ("socai2-api:integrity-20261021",
            "sha256:1be37c3893f782b84ea5bfe3d1af20f20700f7e88fa9c79fee1202f3a15a3b1d"),
    "agents": ("socai2-agents:full-ueba-context-20261021",
               "sha256:aec3c54f6f07c219f55922b0209e2a8edf3303e084441bb7651a27f7845a2c82"),
}
FILES = {
    "api": (
        "app/api/v1/endpoints/attack_chain.py", "app/api/v1/endpoints/cases.py",
        "app/api/v1/endpoints/graph.py", "app/api/v1/router.py",
        "app/services/graph_service.py", "app/services/investigation_attack_context.py",
        "app/services/investigation_tools.py",
    ),
    "agents": (
        "app/agents/attack_path_agent.py", "app/context/attack_context.py",
        "app/context/bundle.py", "app/investigator/bundle_prompt.py",
        "app/investigator/deep_investigation.py", "app/investigator/ledger.py",
        "app/investigator/orchestrator.py", "app/investigator/tools.py",
        "app/orchestrator/report.py", "app/orchestrator/router.py",
        "app/tools/graph.py", "app/workers/fused_alert_consumer.py",
    ),
}
TARGETS = {service: f"socai2-{service}:investigation-context-candidate-20261022"
           for service in FILES}


def verify_context(candidate: Path) -> Path:
    context = candidate / "build-context"
    if context.is_symlink() or not context.is_dir():
        raise ValueError("build-context must be a real directory")
    paths = list(context.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in paths):
        raise ValueError("build-context must contain only regular files/directories")
    expected = {f"services/{service}/{name}" for service, names in FILES.items() for name in names}
    actual = {p.relative_to(context).as_posix() for p in paths if p.is_file()}
    if actual != expected | {"manifest.json"}:
        raise ValueError("build-context must contain exactly the 19 reviewed files and manifest.json")
    manifest_bytes = (context / "manifest.json").read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != EXPECTED_MANIFEST_SHA256:
        raise ValueError("manifest bytes differ from the reviewed 19-file batch")
    manifest = json.loads(manifest_bytes)
    rows = manifest.get("files", [])
    if manifest.get("schema_version") != 1 or not isinstance(rows, list):
        raise ValueError("manifest must use schema_version 1 and a files list")
    if len(rows) != 19 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("manifest must contain exactly 19 file records")
    listed = [row.get("path") for row in rows]
    if any(not isinstance(p, str) for p in listed) or set(listed) != expected or len(set(listed)) != 19:
        raise ValueError("manifest paths must match the exact reviewed file set without duplicates")
    for row in rows:
        digest = row.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid sha256 for {row['path']}")
        if hashlib.sha256((context / row["path"]).read_bytes()).hexdigest() != digest:
            raise ValueError(f"sha256 mismatch: {row['path']}")
    for service, names in FILES.items():
        dockerfile = HERE / f"Dockerfile.investigation-context-{service}"
        instructions = [line.strip() for line in dockerfile.read_text().splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
        expected_recipe = [f"FROM {PARENTS[service][0]}"] + [
            f"COPY --chown=10001:10001 {name} /app/{name}" for name in names]
        if instructions != expected_recipe:
            raise ValueError(f"Dockerfile differs from the explicit reviewed recipe: {dockerfile.name}")
    return context


def capture(command: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(f"Docker metadata command failed (exit {result.returncode}); check the local daemon")
    return result.stdout.strip()


def local_docker() -> tuple[list[str], dict[str, str]]:
    # DOCKER_CONTEXT overrides DOCKER_HOST in the Docker CLI.
    context_name = os.environ.get("DOCKER_CONTEXT")
    endpoint = os.environ.get("DOCKER_HOST") if not context_name else None
    if not endpoint:
        command = ["docker", "context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"]
        if context_name:
            command.append(context_name)
        endpoint = json.loads(capture(command))
    parsed = urlsplit(endpoint)
    if (parsed.scheme != "unix" or parsed.netloc or not parsed.path.startswith("/")
            or parsed.query or parsed.fragment):
        raise ValueError("Only a local Unix Docker socket is allowed; remote endpoints are refused")
    env = dict(os.environ)
    for key in ("DOCKER_CONTEXT", "DOCKER_HOST", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH",
                "BUILDX_BUILDER", "BUILDKIT_HOST"):
        env.pop(key, None)
    env["DOCKER_BUILDKIT"] = "0"
    return ["docker", "--host", endpoint], env


def image_info(docker: list[str], env: dict[str, str], tag: str) -> dict:
    # Select fields explicitly: no credentials or environment values are emitted.
    template = ('{"id":{{json .Id}},"os":{{json .Os}},"architecture":{{json .Architecture}},'
                '"layers":{{json .RootFS.Layers}},"cmd":{{json (index .Config "Cmd")}},'
                '"entrypoint":{{json (index .Config "Entrypoint")}},"user":{{json (index .Config "User")}},'
                '"working_dir":{{json (index .Config "WorkingDir")}}}')
    return json.loads(capture(docker + ["image", "inspect", "--format", template, tag], env=env))


def check_parents(docker: list[str], env: dict[str, str]) -> dict:
    observed = {}
    for service, (tag, expected_id) in PARENTS.items():
        value = image_info(docker, env, tag)
        if value["id"] != expected_id or value["os"] != "linux" or value["architecture"] != "amd64":
            raise ValueError(f"{service} parent image ID/platform differs from the recorded full baseline")
        observed[service] = {"tag": tag, **value}
    return observed


def verify_inheritance(service: str, parent: dict, child: dict) -> None:
    parent_layers, child_layers = parent["layers"], child["layers"]
    if (not isinstance(parent_layers, list) or not parent_layers
            or not isinstance(child_layers, list)
            or child_layers[:len(parent_layers)] != parent_layers):
        raise ValueError(f"{service} built image does not retain the parent RootFS layer prefix")
    for field in ("os", "architecture", "cmd", "entrypoint", "user", "working_dir"):
        if child[field] != parent[field]:
            raise ValueError(f"{service} built image changed inherited {field}")


def check_local_builder(docker: list[str], env: dict[str, str], name: str) -> dict:
    # Older installed buildx has no inspect --format; retain only these fields.
    output = capture(docker + ["buildx", "inspect", name], env=env)
    fields = {}
    for line in output.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key in ("Driver", "Endpoint", "Status"):
            fields.setdefault(key, []).append(value.strip())
    if fields.get("Driver") != ["docker"] or len(fields.get("Endpoint", [])) != 1:
        raise ValueError("BuildKit must use one existing docker-driver endpoint")
    endpoint = fields["Endpoint"][0]
    if "://" in endpoint:
        raise ValueError("BuildKit must name a Docker context mapped to the local socket")
    host = json.loads(capture(
        ["docker", "context", "inspect", endpoint, "--format", "{{json .Endpoints.docker.Host}}"], env=env))
    if host != docker[2] or fields.get("Status") != ["running"]:
        raise ValueError("BuildKit endpoint must be the same running local Docker daemon")
    return {"name": name, "driver": "docker", "endpoint": endpoint, "host": host}


def build_command(service: str, context: Path, builder: str | None = None) -> list[str]:
    command = (["buildx", "build", "--builder", builder, "--load", "--progress", "plain"]
               if builder else ["build"])
    return command + [ "--platform", "linux/amd64", "--network", "none", "--pull=false",
            "--file", str(HERE / f"Dockerfile.investigation-context-{service}"),
            "--tag", TARGETS[service], str(context / "services" / service)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, required=True,
                        help="directory containing build-context/manifest.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-parents", action="store_true", help="read local parent image metadata only")
    mode.add_argument("--execute", action="store_true", help="build two local images; never run or deploy them")
    parser.add_argument("--local-buildkit-builder", help="explicit existing local docker-driver builder; no fallback")
    args = parser.parse_args()
    try:
        candidate = args.candidate_dir.resolve()
        context = verify_context(candidate)
        report = {"mode": "execute" if args.execute else "check-parents" if args.check_parents else "plan",
                  "candidate_dir": str(candidate), "verified_source_files": 19,
                  "verified_manifest_sha256": EXPECTED_MANIFEST_SHA256,
                  "platform": "linux/amd64", "network": "none", "pull": False,
                  "builder": ({"explicit_local_buildkit": args.local_buildkit_builder}
                              if args.local_buildkit_builder else "local classic daemon builder (DOCKER_BUILDKIT=0)"),
                  "parents": {s: {"tag": tag, "expected_image_id": ident}
                              for s, (tag, ident) in PARENTS.items()},
                  "commands": {s: ["docker", *build_command(s, context, args.local_buildkit_builder)] for s in FILES},
                  "images_built": False, "deployment_performed": False}
        if args.check_parents or args.execute:
            docker, env = local_docker()
            build_docker = docker
            report["observed_parents"] = check_parents(docker, env)
            if args.local_buildkit_builder:
                env["DOCKER_BUILDKIT"] = "1"
                report["observed_local_builder"] = check_local_builder(docker, env, args.local_buildkit_builder)
                # Buildx's context-bound docker driver requires --context, not --host.
                build_docker = ["docker", "--context", report["observed_local_builder"]["endpoint"]]
                report["commands"] = {s: build_docker + build_command(s, context, args.local_buildkit_builder)
                                      for s in FILES}
        if args.execute:
            # Fail before the first build if either candidate tag already exists.
            for tag in TARGETS.values():
                if capture(docker + ["image", "ls", "--quiet", "--no-trunc", "--filter", f"reference={tag}"], env=env):
                    raise ValueError(f"candidate tag already exists; refusing to overwrite: {tag}")
            built = {}
            for service in FILES:
                verify_context(candidate)
                parents = check_parents(docker, env)
                if args.local_buildkit_builder:
                    check_local_builder(docker, env, args.local_buildkit_builder)
                # Build logs go to stderr so stdout remains a single JSON result.
                subprocess.run(build_docker + build_command(service, context, args.local_buildkit_builder), env=env,
                               stdout=sys.stderr, check=True)
                child = image_info(docker, env, TARGETS[service])
                verify_inheritance(service, parents[service], child)
                built[service] = {"tag": TARGETS[service], **child,
                                  "parent_layers_prefix": True, "inherited_configuration": True}
            report.update(images_built=True, built_images=built)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Candidate preparation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
