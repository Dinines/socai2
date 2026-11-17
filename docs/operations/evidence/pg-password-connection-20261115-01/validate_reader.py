"""One ordinary-reader TCP authentication check; no business writes or generation."""
import argparse
import asyncio
import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[4]


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


async def verify(config, result):
    from sqlalchemy import URL, text
    from sqlalchemy.ext.asyncio import create_async_engine

    remote = tomllib.loads(Path(config["remote_profile"]).read_text())
    db = remote["database"]
    secrets = json.loads((ROOT / remote["secrets_file"]).read_text())
    environment = json.loads(Path(config["application_environment"]).read_text())
    os.environ.update(environment)
    for key in ("PGPASSWORD", "PGPASSFILE", "PGSSLCERT", "PGSSLKEY", "PGSSLCRL", "PGSSLCRLDIR"):
        os.environ.pop(key, None)
    # This nonexistent inherited CA must not become an asyncpg require dependency.
    unused_ca = Path(config["unused_ca_path"])
    assert not unused_ca.exists()
    os.environ["PGSSLROOTCERT"] = str(unused_ca)
    url = URL.create("postgresql+asyncpg", username=db["user"], password=secrets["database_password"],
                     host=config["bind_host"], port=config["bind_port"], database=db["name"],
                     query={"sslmode": "require"})
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    sys.path.insert(0, str(ROOT / "services/api"))
    from app.db.database import _normalize_async_pg_url
    from app.db.database import engine as application_engine

    normalized, options = _normalize_async_pg_url(url.render_as_string(hide_password=False))
    context = options["ssl"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_NONE and context.check_hostname is False
    assert context.get_ca_certs() == []
    result["tls_configuration"] = {
        "mode": "require", "context_type": "SSLContext", "verify_mode": "CERT_NONE",
        "check_hostname": False, "ca_certificates_loaded": len(context.get_ca_certs()),
        "inherited_nonexistent_pgsslrootcert_ignored": True,
        "client_certificate_or_key_configured": False,
    }
    options.update(timeout=config["connect_timeout_seconds"], command_timeout=config["statement_timeout_seconds"],
                   server_settings={"default_transaction_read_only": "on", "application_name": config["application_name"]})
    engine = create_async_engine(normalized, connect_args=options, hide_parameters=True, echo=False)
    try:
        async with engine.connect() as connection:
            row = (await connection.execute(text("""SELECT current_database() AS database,
                session_user AS login_role, current_user AS effective_role,
                inet_server_addr()::text AS server_address, inet_server_port() AS server_port,
                inet_client_addr()::text AS client_address,
                current_setting('transaction_read_only') AS read_only,
                r.rolsuper, s.ssl, s.version AS tls_version
                FROM pg_roles r JOIN pg_stat_ssl s ON s.pid=pg_backend_pid()
                WHERE r.rolname=session_user"""))).mappings().one()
            result["correct_password"] = dict(row)
            assert row["database"] == db["name"] and row["login_role"] == row["effective_role"] == db["user"]
            assert not row["rolsuper"] and row["ssl"] is True and row["read_only"] == "on"
            result["correct_password"]["state"] = "passed"
    finally:
        await engine.dispose()
        await application_engine.dispose()

    # A fresh connection with a deliberately different password proves auth,
    # without reusing any previously authenticated connection or role switch.
    invalid_url = url.set(password=secrets["database_password"] + config["invalid_password_suffix"])
    invalid, invalid_options = _normalize_async_pg_url(invalid_url.render_as_string(hide_password=False))
    invalid_options.update(timeout=config["connect_timeout_seconds"], command_timeout=config["statement_timeout_seconds"])
    bad_engine = create_async_engine(invalid, connect_args=invalid_options, hide_parameters=True, echo=False)
    try:
        try:
            async with bad_engine.connect():
                raise AssertionError("wrong_password_was_accepted")
        except Exception as exc:  # noqa: BLE001 -- save only type/SQLSTATE, never a credential-bearing exception.
            code = getattr(exc, "sqlstate", None) or getattr(getattr(exc, "orig", None), "sqlstate", None)
            result["wrong_password"] = {"exception_type": type(exc).__name__, "sqlstate": code}
            assert code == "28P01", "wrong password must fail authentication"
            result["wrong_password"]["state"] = "passed"
    finally:
        await bad_engine.dispose()


def main(args):
    config = json.loads(args.config.read_text())
    remote = tomllib.loads(Path(config["remote_profile"]).read_text())
    ssh = remote["ssh"]
    result = {"state": "started", "observed_at": datetime.now(UTC).isoformat(),
              "mode": "real_ordinary_reader_tcp_require_no_ca", "model_calls": 0, "business_writes": 0,
              "kafka_messages": 0, "configuration_sha256": fingerprint(args.config),
              "target": {"ssh_target": ssh["target"], "host": ssh["remote_host"], "port": ssh["remote_port"],
                         "database": remote["database"]["name"], "user": remote["database"]["user"]},
              "source_sha256_before": fingerprint(ROOT / "services/api/app/db/database.py")}
    assert not args.output.exists(), "new receipt required"
    command = [ssh["binary"], "-N", "-L",
               f"{config['bind_host']}:{config['bind_port']}:{ssh['remote_host']}:{ssh['remote_port']}",
               "-o", "ExitOnForwardFailure=yes", "-o", "BatchMode=yes",
               "-o", f"ConnectTimeout={ssh['connect_timeout_seconds']}", ssh["target"]]
    tunnel = None
    try:
        with socket.socket() as probe:
            probe.bind((config["bind_host"], config["bind_port"]))
        tunnel = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + ssh["startup_timeout_seconds"]
        while time.monotonic() < deadline:
            assert tunnel.poll() is None, "read_only_tunnel_failed"
            try:
                with socket.create_connection((config["bind_host"], config["bind_port"]), timeout=1):
                    break
            except OSError:
                time.sleep(ssh["poll_interval_seconds"])
        else:
            raise TimeoutError("read_only_tunnel_start_timeout")
        asyncio.run(verify(config, result))
        result["source_sha256_after"] = fingerprint(ROOT / "services/api/app/db/database.py")
        assert result["source_sha256_before"] == result["source_sha256_after"]
        result["state"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- always retain a sanitized failure receipt.
        result.update(state="failed", error_type=type(exc).__name__)
    finally:
        if tunnel is not None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=ssh["shutdown_timeout_seconds"])
            except subprocess.TimeoutExpired:
                tunnel.kill()
                tunnel.wait()
        result["temporary_tunnel_stopped"] = tunnel is None or tunnel.poll() is not None
        with args.output.open("x") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
    print(json.dumps({"state": result["state"], "receipt": str(args.output)}, ensure_ascii=False))
    return 0 if result["state"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    sys.exit(main(parser.parse_args()))
