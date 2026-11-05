"""Run one local application from this checkout with only its own credentials."""
import argparse
import os

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
    args = parser.parse_args()
    assert PYTHON.is_file(), "prepared Python 3.12 environment missing"
    values = read_private()
    env = {**minimal_process_environment(), **runtime_environment(args.service, values)}
    paths = [str(ROOT / "services" / args.service), str(ROOT / "deploy/local-investigation")]
    env.update(PYTHONPATH=os.pathsep.join(paths), PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1")
    module = "app.socai2_main" if args.service == "api" else "fusion_app"
    if args.check_import:
        command = [str(PYTHON), "-c", "import importlib; importlib.import_module(" + repr(module) + "); print('import_passed')"]
    else:
        command = [str(PYTHON), "-m", "uvicorn", module + ":app", "--host", "127.0.0.1", "--port", str(PORTS[args.service])]
    # Neither application can discover the repository's existing .env here.
    os.chdir(PRIVATE)
    os.execve(PYTHON, command, env)


if __name__ == "__main__":
    main()
