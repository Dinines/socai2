"""Explicit, file-backed configuration for a local read-only API and SSH forward."""

import ipaddress
import json
import os
import re
import signal
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import tomllib
from config import ROOT, minimal_process_environment
from sqlalchemy import URL

SECRET_ENV_KEYS = frozenset({
    "SECRET_KEY", "JWT_SECRET", "AISOC_CREDENTIAL_KEY", "REALTIME_INTERNAL_TOKEN",
    "AISOC_REALTIME_JWT_SECRET", "METRICS_TOKEN",
})


def need(condition, code):
    if not condition:
        raise ValueError(code)


def local_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def private_json(path):
    need(path.is_file() and not path.is_symlink(), "remote_secrets_file_missing_or_symlink")
    need(path.stat().st_uid == os.getuid() and path.stat().st_mode & 0o077 == 0,
         "remote_secrets_file_requires_owner_only_access")
    need(path.parent.stat().st_mode & 0o077 == 0, "remote_secrets_directory_requires_owner_only_access")
    return json.loads(path.read_text())


@dataclass
class RemoteProfile:
    path: Path
    config: dict
    secrets: dict = field(repr=False)

    def database_url(self):
        db = self.config["database"]
        return URL.create(
            db["driver"], username=db["user"], password=self.secrets["database_password"],
            host=db["host"], port=db["port"], database=db["name"],
            query={
                "hostaddr": db["hostaddr"], "sslmode": db["sslmode"],
                "sslrootcert": str(local_path(db["sslrootcert"]).resolve()),
                "connect_timeout": str(db["connect_timeout_seconds"]),
                "application_name": db["application_name"],
                "options": "-c default_transaction_read_only=on "
                           f"-c statement_timeout={db['statement_timeout_ms']}",
            },
        ).render_as_string(hide_password=False)

    def environment(self):
        policy = tomllib.loads(local_path(self.config["investigation_policy_file"]).read_text())
        return {
            **minimal_process_environment(), **self.config["environment"],
            **self.secrets["environment"], "DATABASE_URL": self.database_url(),
            "SOCAI2_REMOTE_PROFILE": str(self.path),
            "SOCAI2_INVESTIGATION_POLICY": str(local_path(self.config["investigation_policy_file"]).resolve()),
            "AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS": str(policy["model"]["max_prepared_bytes"]),
            "PYTHONPATH": os.pathsep.join((str(ROOT / "services/api"), str(Path(__file__).parent))),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1",
        }

    def ssh_command(self):
        ssh, db = self.config["ssh"], self.config["database"]
        return [
            ssh["binary"], "-N", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", "ControlMaster=no", "-o", "ControlPath=none",
            "-o", "ExitOnForwardFailure=yes", "-o", "ConnectionAttempts=1",
            "-o", f"ConnectTimeout={ssh['connect_timeout_seconds']}",
            "-o", f"ServerAliveInterval={ssh['server_alive_interval_seconds']}",
            "-o", f"ServerAliveCountMax={ssh['server_alive_count_max']}",
            "-L", f"{db['hostaddr']}:{db['port']}:{ssh['remote_host']}:{ssh['remote_port']}",
            ssh["target"],
        ]


def load_profile(path):
    path = Path(path).resolve(strict=True)
    cfg = tomllib.loads(path.read_text())
    need(cfg["version"] == 1 and cfg["mode"] == "read_only", "unsupported_remote_profile")
    db, api, ssh = cfg["database"], cfg["api"], cfg["ssh"]
    need(db["driver"] == "postgresql+psycopg" and db["sslmode"] == "verify-full", "remote_tls_must_verify_full")
    for value in (db["name"], db["user"], db["application_name"], cfg["name"]):
        need(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", value), "invalid_remote_identity")
    for value in (db["host"], ssh["target"], ssh["remote_host"]):
        need(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value), "invalid_remote_host")
    for value in (db["hostaddr"], api["host"]):
        address = ipaddress.ip_address(value)
        need(address.version == 4 and address.is_loopback, "remote_profile_requires_loopback")
    for value in (db["port"], api["port"], ssh["remote_port"]):
        need(type(value) is int and 0 < value < 65536, "invalid_remote_port")
    for section, keys in (
        (db, ("connect_timeout_seconds", "statement_timeout_ms", "expected_tables", "expected_columns")),
        (api, ("request_timeout_seconds",)),
        (ssh, ("connect_timeout_seconds", "server_alive_interval_seconds", "server_alive_count_max",
               "startup_timeout_seconds", "poll_interval_seconds", "shutdown_timeout_seconds")),
    ):
        for key in keys:
            need(type(section[key]) in (int, float) and section[key] > 0, "invalid_remote_timeout_or_count")
    UUID(api["tenant_id"])
    UUID(api["service_id"])
    need(bool(api["service_email"]) and api["service_role"] == "viewer", "remote_service_identity_required")
    need(api["permissions"] and set(api["permissions"]) <= {"alerts:read", "cases:read"},
         "remote_service_permissions_must_be_read_only")
    env = cfg["environment"]
    sources = cfg["read_sources"]
    need(set(sources) == {"assets", "owners"}, "read_sources_configuration_incomplete")
    for name in ("assets", "owners"):
        need(isinstance(sources[name], str) and bool(re.fullmatch(r"[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*", sources[name])),
             "read_source_identifier_invalid")
    need(all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()), "environment_values_must_be_strings")
    need(not ({"DATABASE_URL", "SOCAI2_REMOTE_PROFILE", "SOCAI2_INVESTIGATION_POLICY", "PYTHONPATH"} | SECRET_ENV_KEYS) & env.keys(),
         "reserved_profile_environment_key")
    for key in ("AISOC_DEV_AUTH_BYPASS", "SOCAI2_STAGE_EXECUTION_ENABLED", "DEBUG"):
        need(env[key] == "false", "remote_profile_disallows_execution_and_auth_bypass")
    need(local_path(cfg["python"]).is_file(), "profile_python_missing")
    need(local_path(cfg["investigation_policy_file"]).is_file(), "profile_investigation_policy_missing")
    need(local_path(db["sslrootcert"]).is_file(), "profile_ca_missing")
    secret = private_json(local_path(cfg["secrets_file"]))
    need(isinstance(secret["database_password"], str) and bool(secret["database_password"]), "database_password_missing")
    need(isinstance(secret["access_token"], str) and len(secret["access_token"]) >= 32, "local_access_token_too_short")
    need(set(secret["environment"]) == SECRET_ENV_KEYS and
         all(isinstance(v, str) and len(v) >= 32 for v in secret["environment"].values()),
         "local_secret_environment_incomplete")
    return RemoteProfile(path, cfg, secret)


def run_profile(path, check_import=False):
    profile = load_profile(path)
    cfg, env = profile.config, profile.environment()
    python = str(local_path(cfg["python"]).resolve())
    cwd = local_path(cfg["secrets_file"]).parent
    if check_import:
        return subprocess.call([python, "-B", "-c", "import remote_readonly_api; print('import_passed')"], cwd=cwd, env=env)
    ssh, db, api = cfg["ssh"], cfg["database"], cfg["api"]
    # Refuse an existing listener; only this invocation's forward is owned/closed.
    with socket.socket() as probe:
        probe.bind((db["hostaddr"], db["port"]))
    processes = []

    def interrupted(_signum, _frame):
        raise KeyboardInterrupt

    previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        tunnel = subprocess.Popen(profile.ssh_command(), env=minimal_process_environment(), start_new_session=True)
        processes.append(tunnel)
        deadline = time.monotonic() + ssh["startup_timeout_seconds"]
        while True:
            need(tunnel.poll() is None, "profile_ssh_forward_exited")
            try:
                with socket.create_connection((db["hostaddr"], db["port"]), timeout=ssh["poll_interval_seconds"]):
                    break
            except OSError:
                need(time.monotonic() < deadline, "profile_ssh_forward_startup_timeout")
                time.sleep(ssh["poll_interval_seconds"])
        print(json.dumps({"profile": cfg["name"], "database": db["name"], "role": db["user"],
                          "tenant": api["tenant_id"], "api": f"http://{api['host']}:{api['port']}",
                          "read_only": True}), flush=True)
        server = subprocess.Popen(
            [python, "-B", "-m", "uvicorn", "remote_readonly_api:app", "--host", api["host"], "--port", str(api["port"])],
            cwd=cwd, env=env, start_new_session=True,
        )
        processes.append(server)
        while server.poll() is None:
            need(tunnel.poll() is None, "profile_ssh_forward_exited")
            time.sleep(ssh["poll_interval_seconds"])
        return server.returncode
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in reversed(processes):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=ssh["shutdown_timeout_seconds"])
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
