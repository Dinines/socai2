"""Install/verify V1.2 reader dependencies using one explicit deployment profile."""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import tomllib

HERE = Path(__file__).resolve().parent
ENTRIES = {"initialize": "init_socai2_v1_2_reader.sql",
           "upgrade": "upgrade_socai2_v1_2_reader.sql", "verify": "verify_socai2_v1_2_reader.sql",
           "enable-api": "api_read_access_20261108.sql",
           "initialize-current": "init_socai2_current_reader.sql",
           "remove-unused-graph": "remove_unused_graph_table.sql"}
GRAPH_MIGRATION = "../../services/api/migrations/127_socai2_remove_unused_graph_table.sql"


def render(name, parents=()):
    """Inline repository-owned includes so local/SSH/container psql sees identical SQL."""
    if (not re.fullmatch(r"[a-z0-9_]+\.sql", name) and name != GRAPH_MIGRATION) or name in parents:
        raise ValueError("invalid_sql_include")
    lines = []
    for line in (HERE / name).read_text(encoding="utf-8").splitlines():
        if line.startswith("\\ir "):
            lines.append(render(line.removeprefix("\\ir ").strip(), (*parents, name)))
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def load_profile(path):
    with Path(path).open("rb") as f:
        cfg = tomllib.load(f)
    if set(cfg) - {"cleanup"} != {"database", "admin_role", "function_owner", "reader_role", "timeout_seconds", "psql_argv", "environment", "transport"}:
        raise ValueError("reader_install_configuration_incomplete")
    if "cleanup" in cfg:
        cleanup = cfg["cleanup"]
        if (not isinstance(cleanup, dict) or set(cleanup) != {"lock_timeout_seconds", "statement_timeout_seconds"}
                or any(type(v) is not int or v <= 0 for v in cleanup.values())):
            raise ValueError("reader_cleanup_limits_invalid")
    for key in ("database", "admin_role", "function_owner", "reader_role"):
        if not isinstance(cfg[key], str) or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", cfg[key]):
            raise ValueError("reader_install_identifier_invalid")
    if type(cfg["timeout_seconds"]) is not int or cfg["timeout_seconds"] <= 0:
        raise ValueError("reader_install_timeout_invalid")
    if not isinstance(cfg["psql_argv"], list) or not cfg["psql_argv"] or not all(isinstance(x, str) and x for x in cfg["psql_argv"]):
        raise ValueError("reader_install_command_invalid")
    allowed = {"PGHOST", "PGHOSTADDR", "PGPORT", "PGSSLMODE", "PGSSLROOTCERT", "PGPASSFILE"}
    if not isinstance(cfg["environment"], dict) or set(cfg["environment"]) - allowed:
        raise ValueError("reader_install_environment_invalid")
    if not all(isinstance(x, str) for x in cfg["environment"].values()):
        raise ValueError("reader_install_environment_invalid")
    command, env = cfg["psql_argv"], cfg["environment"]
    if cfg["transport"] == "docker_socket":
        # Explicit container and its local socket; no inherited Docker context/host.
        if len(command) != 8 or command[1] != "--context" or command[3:5] != ["exec", "-i"] or command[6:] != ["psql", "-XwAtq"] or env:
            raise ValueError("reader_install_container_target_incomplete")
    elif cfg["transport"] == "libpq":
        if not {"PGHOST", "PGPORT", "PGSSLMODE", "PGPASSFILE"} <= set(env) or not all(env.values()):
            raise ValueError("reader_install_libpq_target_incomplete")
        if len(command) != 3 or command[1:] != ["-X", "-w"] or not env["PGPORT"].isdigit():
            raise ValueError("reader_install_libpq_target_invalid")
        if env["PGSSLMODE"] not in {"verify-full", "disable"} or (env["PGSSLMODE"] == "verify-full" and not env.get("PGSSLROOTCERT")):
            raise ValueError("reader_install_tls_configuration_invalid")
    else:
        raise ValueError("reader_install_transport_invalid")
    return cfg


def execute(cfg, mode):
    if mode in {"initialize-current", "remove-unused-graph"} and "cleanup" not in cfg:
        raise ValueError("reader_cleanup_limits_required")
    command = [*cfg["psql_argv"], "-U", cfg["admin_role"], "-d", cfg["database"],
               "-v", "ON_ERROR_STOP=1", "-v", "expected_database=" + cfg["database"],
               "-v", "reader_role=" + cfg["reader_role"], "-v", "function_owner=" + cfg["function_owner"]]
    if "cleanup" in cfg:
        command += ["-v", "cleanup_lock_timeout=" + str(cfg["cleanup"]["lock_timeout_seconds"]) + "s",
                    "-v", "cleanup_statement_timeout=" + str(cfg["cleanup"]["statement_timeout_seconds"]) + "s"]
    # Never inherit a different PG target/password from the parent environment.
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("PG", "DOCKER_"))}
    environment.update(cfg["environment"])
    return subprocess.run(command, input=render(ENTRIES[mode]), text=True, env=environment,
                          check=False, timeout=cfg["timeout_seconds"], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=ENTRIES)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--print-sql", action="store_true")
    args = parser.parse_args()
    cfg = load_profile(args.profile)
    if args.print_sql:
        sys.stdout.write(render(ENTRIES[args.mode]))
        return 0
    result = execute(cfg, args.mode)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
