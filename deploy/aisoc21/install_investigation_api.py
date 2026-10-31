"""Prepare the dedicated investigation service; --execute builds and starts it on 21."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
BASE_IMAGE = "sha256:5a1e1fd8cf08349438e7d1346a25c9599bff7937df5d22ea94426e77b33f2aa9"
IMAGE = "socai2-investigation-api:20261031-r7"
CONTAINER = "socai2-investigation-api"
PROFILE = Path("/opt/sting-aisoc-socai2/private/investigation-v2.env")
COMPOSE = ROOT / "deploy/aisoc21/compose.investigation-v2-api.yml"


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name]))[0]


def environment(container):
    return dict(value.split("=", 1) for value in container["Config"]["Env"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--upgrade-from", help="Expected current investigation image ID; preserves its existing environment file")
    args = parser.parse_args()
    files = sorted((ROOT / "services/api/app").rglob("*.py"))
    out = {"image": IMAGE, "base_image": BASE_IMAGE, "container": CONTAINER,
           "listen": "127.0.0.1:18010", "source_files": len(files), "executed": args.execute}
    if not args.execute:
        print(json.dumps(out))
        return
    os.umask(0o077)
    log = ROOT / "install.log"
    def run(command):
        with log.open("ab") as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"{command[0]} command failed; see restricted install.log")
    try:
        core, agents = inspect("socai2-api-1"), inspect("socai2-agents-1")
        assert core["Image"] == BASE_IMAGE, "core_dependency_image_changed"
        base_reference = core["Config"]["Image"]
        assert inspect(base_reference)["Id"] == BASE_IMAGE, "base_image_tag_changed"
        assert core["State"]["Running"] and agents["State"]["Running"]
        exists = subprocess.run(["docker", "inspect", CONTAINER], capture_output=True).returncode == 0
        if args.upgrade_from:
            assert exists and PROFILE.exists(), "missing_upgrade_target"
            previous = inspect(CONTAINER)
            assert previous["Image"] == args.upgrade_from, "investigation_image_changed"
            out["previous_image_id"] = previous["Image"]
            source_env = environment(previous)
        else:
            assert not exists and not PROFILE.exists(), "service_or_environment_already_exists"
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 18010))
            source_env, agent_env = environment(core), environment(agents)
            for key in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "LLM_GATEWAY_URL", "LLM_GATEWAY_API_KEY"):
                if key in agent_env:
                    source_env[key] = agent_env[key]
            source_env["OPENAI_MODEL"] = "aisoc-investigation"
        assert source_env.get("DATABASE_URL") and source_env.get("SECRET_KEY")
        assert source_env.get("OPENAI_BASE_URL") or source_env.get("LLM_GATEWAY_URL")
        assert source_env.get("OPENAI_API_KEY") or source_env.get("LLM_GATEWAY_API_KEY")
        assert all("\n" not in value and "\r" not in value for value in source_env.values()), "multiline_environment_value"
        run(["docker", "build", "--pull=false", "--network=none", "--build-arg", f"BASE_API_IMAGE={base_reference}",
             "-f", str(ROOT / "deploy/aisoc21/Dockerfile.investigation-v2-api"), "-t", IMAGE, "."])
        if not args.upgrade_from:
            with PROFILE.open("x", encoding="utf-8") as stream:
                stream.write("".join(f"{key}={value}\n" for key, value in sorted(source_env.items())))
            PROFILE.chmod(0o600)
        compose = ["docker", "compose", "-f", str(COMPOSE)]
        run(compose + ["config", "--quiet"])
        run(compose + ["up", "-d", "--no-deps", "--pull", "never", "investigation-api"])
        for attempt in range(15):
            try:
                with urlopen("http://127.0.0.1:18010/livez", timeout=2) as response:
                    out["liveness"] = json.load(response)
                break
            except OSError:
                if attempt == 14:
                    raise
                time.sleep(1)
        with urlopen("http://127.0.0.1:18010/api/v2/investigation/openapi.json", timeout=5) as response:
            schema = json.load(response)
        required = ["/api/v2/investigation/case-links", "/api/v2/investigation/incidents/{incident_id}",
                    "/api/v2/investigation/cases/{case_id}/investigate"]
        assert all(path in schema["paths"] for path in required)
        out["openapi_paths"] = len(schema["paths"])
        try:
            urlopen("http://127.0.0.1:18010/api/v2/investigation/cases/467dc2a9-fa33-4aba-bb87-19595ecd176e/investigations", timeout=5)
        except HTTPError as exc:
            out["without_credentials_status"] = exc.code
            assert exc.code in {401, 403}
        else:
            raise AssertionError("missing_existing_auth_rejection")
        current_core, current_agents, deployed = inspect("socai2-api-1"), inspect("socai2-agents-1"), inspect(CONTAINER)
        if args.upgrade_from:
            assert environment(deployed) == source_env, "investigation_environment_changed"
        assert all(before["Id"] == after["Id"] and before["State"]["StartedAt"] == after["State"]["StartedAt"]
                   for before, after in [(core, current_core), (agents, current_agents)])
        out.update(passed=True, image_id=deployed["Image"], core_and_agents_unchanged=True,
                   profile_mode=oct(PROFILE.stat().st_mode & 0o777), model_role=source_env["OPENAI_MODEL"],
                   source_sha256={str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files})
    except Exception as exc:
        out.update(passed=False, error={"type": type(exc).__name__, "message": str(exc)})
    finally:
        (ROOT / "install-result.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in out.items() if key != "source_sha256"}))
    if not out["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
