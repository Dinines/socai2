"""Run one local application from this checkout with only its own credentials."""
import argparse
import os
from pathlib import Path

import tomllib
from config import (
    PORTS,
    PRIVATE,
    PYTHON,
    ROOT,
    minimal_process_environment,
    read_private,
    runtime_environment,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=("api", "fusion"))
    parser.add_argument("--check-import", action="store_true", help="Import application only; do not start or connect")
    parser.add_argument("--deployed-pilot", action="store_true", help="Enable the local API's authenticated deployed-model preflight")
    parser.add_argument("--profile", help="Explicit remote read-only TOML profile (API only)")
    parser.add_argument("--investigation-policy", help="Explicit investigation policy TOML for the executing API")
    args = parser.parse_args()
    if args.profile:
        if args.service != "api" or args.deployed_pilot:
            parser.error("--profile is only supported by the read-only API")
        from remote_profile import run_profile
        raise SystemExit(run_profile(args.profile, args.check_import))
    if args.deployed_pilot and args.service != "api":
        parser.error("--deployed-pilot requires the api service")
    assert PYTHON.is_file(), "prepared Python 3.12 environment missing"
    values = read_private()
    env = {**minimal_process_environment(), **runtime_environment(args.service, values)}
    if args.service == "api":
        if not args.investigation_policy or not Path(args.investigation_policy).is_file():
            parser.error("executing API requires --investigation-policy pointing to an existing TOML file")
        env["SOCAI2_INVESTIGATION_POLICY"] = str(Path(args.investigation_policy).resolve())
        policy = tomllib.loads(Path(args.investigation_policy).read_text())
        env["AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS"] = str(policy["model"]["max_prepared_bytes"])
    paths = [str(ROOT / "services" / args.service), str(ROOT / "deploy/local-investigation")]
    env.update(PYTHONPATH=os.pathsep.join(paths), PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1")
    module = "app.socai2_main" if args.service == "api" else "fusion_app"
    if args.deployed_pilot:
        module = "pilot_api"
    if args.check_import:
        command = [str(PYTHON), "-c", "import importlib; importlib.import_module(" + repr(module) + "); print('import_passed')"]
    else:
        command = [str(PYTHON), "-m", "uvicorn", module + ":app", "--host", "127.0.0.1", "--port", str(PORTS[args.service])]
    # Neither application can discover the repository's existing .env here.
    os.chdir(PRIVATE)
    os.execve(PYTHON, command, env)


if __name__ == "__main__":
    main()
