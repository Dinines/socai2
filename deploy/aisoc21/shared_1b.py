#!/usr/bin/env python3
"""Provision only socai2's objects in the existing host21 PostgreSQL/Redis services.

Run on host21 as its infrastructure operator. No container restart, shared
configuration change, database deletion, or global Redis cleanup is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import uuid

PG_CONTAINER = "spirithub-postgres-1"
REDIS_CONTAINER = "sting-infra21-redis-1"
DATABASE = "aisoc"
OWNER = "aisoc"
APP = "aisoc_app"
REDIS_USER = "socai2"
BATCH = "1b-20261020"


class SharedBatch:
    def __init__(self, root: Path):
        self.root = root
        self.source = root / "source"
        self.private = root / "private"
        self.evidence = root / "evidence" / BATCH
        self.private.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.private.chmod(0o700)
        self.evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.secrets: list[str] = []
        self.config_path = self.private / "shared-services.json"
        self.pg_admin = self.inspect_env(PG_CONTAINER)["POSTGRES_USER"]
        redis_env = self.inspect_env(REDIS_CONTAINER)
        self.redis_admin_password = redis_env.get("REDIS_PASSWORD", "")
        if not self.redis_admin_password:
            item = self.inspect(REDIS_CONTAINER)
            command = item["Config"].get("Cmd") or []
            if "--requirepass" in command:
                self.redis_admin_password = command[command.index("--requirepass") + 1]
        if not self.redis_admin_password:
            raise RuntimeError("Shared Redis credential not found in controlled configuration")
        self.secrets.append(self.redis_admin_password)
        self.config = json.loads(self.config_path.read_text()) if self.config_path.exists() else None
        if self.config:
            self.secrets.extend(self.config[k] for k in ("owner_password", "app_password", "redis_password"))

    @staticmethod
    def inspect(name: str) -> dict:
        return json.loads(subprocess.check_output(["docker", "inspect", name]))[0]

    def inspect_env(self, name: str) -> dict:
        return dict(value.split("=", 1) for value in self.inspect(name)["Config"].get("Env", []) if "=" in value)

    def redact(self, text: str) -> str:
        for value in self.secrets:
            if value:
                text = text.replace(value, "[REDACTED]")
        return text

    def run(self, command: list[str], content: str | None = None, allow_error: bool = False):
        result = subprocess.run(command, input=content, text=True, capture_output=True)
        if result.returncode and not allow_error:
            raise RuntimeError(self.redact(result.stderr or result.stdout)[:1800])
        return result

    def pg(self, sql: str, *, database: str = DATABASE, login: str | None = None,
           tcp: bool = False, allow_error: bool = False):
        user = login or self.pg_admin
        command = ["docker", "exec", "-i", "-e", "PGAPPNAME=socai2_1b"]
        if login:
            password = self.config["owner_password" if login == OWNER else "app_password"]
            command += ["-e", "PGPASSWORD=" + password]
        command += [PG_CONTAINER, "psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1"]
        if tcp:
            command += ["-h", "192.168.1.21", "-p", "5432"]
        command += ["-U", user, "-d", database]
        return self.run(command, sql, allow_error)

    def redis(self, *args: str, app: bool = False, database: int | None = None,
              content: str | None = None, allow_error: bool = False):
        password = self.config["redis_password"] if app else self.redis_admin_password
        command = ["docker", "exec", "-i", "-e", "REDISCLI_AUTH=" + password,
                   REDIS_CONTAINER, "redis-cli", "--no-auth-warning", "--raw"]
        if app:
            command += ["--user", REDIS_USER]
        if database is not None:
            command += ["-n", str(database)]
        result = self.run(command + list(args), content, allow_error)
        if not allow_error and any(line.startswith(("ERR ", "NOAUTH", "NOPERM", "WRONGPASS", "AUTH failed"))
                                   for line in (result.stdout + result.stderr).splitlines()):
            raise RuntimeError(self.redact(result.stdout + result.stderr)[:800])
        return result

    def save(self, name: str, data) -> None:
        (self.evidence / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def restore_redis_user(self) -> dict:
        if not self.config:
            raise RuntimeError("Missing project credential state")
        # This affects only this project's ACL user. Logical DBs are allocation,
        # not a Redis ACL security boundary; all application callers are trusted.
        result = self.redis("ACL", "SETUSER", REDIS_USER, "reset", "on",
                            ">" + self.config["redis_password"], "~*", "resetchannels",
                            "+@read", "+@write", "+@connection", "+@transaction", "+@scripting",
                            "-@admin", "-@dangerous", "+select", "+acl|whoami",
                            "+client|setinfo", "+client|setname", "+waitaof")
        if result.stdout.strip() != "OK":
            raise RuntimeError("Could not provision the project Redis ACL user")
        aclfile = self.redis("CONFIG", "GET", "aclfile").stdout.strip().splitlines()[1:]
        if aclfile and aclfile[0]:
            self.redis("ACL", "SAVE")
        return {"user": REDIS_USER, "restored": True,
                "aclfile": aclfile}

    def provision(self) -> dict:
        if self.config:
            raise RuntimeError("Project state already exists; use --migrate or --verify without reprovisioning")
        state = self.pg("SELECT json_build_object('databases',(SELECT json_agg(datname) FROM pg_database),"
                        "'roles',(SELECT json_agg(rolname) FROM pg_roles))::text;", database="postgres")
        present = json.loads(state.stdout)
        if DATABASE in present["databases"] or any(role in present["roles"] for role in (OWNER, APP)):
            raise RuntimeError("Target database/roles already exist without project state; retained unchanged")
        if REDIS_USER in self.redis("ACL", "USERS").stdout.splitlines():
            raise RuntimeError("Redis project user already exists without project state")
        counts = {index: int(self.redis("DBSIZE", database=index).stdout.strip()) for index in range(8, 13)}
        if any(counts.values()):
            raise RuntimeError("Planned Redis logical DBs are occupied; no keys changed")
        logging = self.pg("SELECT json_object_agg(name,setting)::text FROM pg_settings WHERE name IN "
                          "('log_statement','log_min_duration_statement','log_duration');", database="postgres")
        log_settings = json.loads(logging.stdout)
        if log_settings["log_statement"] != "none" or log_settings["log_min_duration_statement"] != "-1":
            raise RuntimeError("Review PostgreSQL statement logging before provisioning credentials")
        self.config = {"project": "socai2", "batch": BATCH, "database": DATABASE,
                       "owner": OWNER, "app_role": APP, "owner_password": secrets.token_hex(32),
                       "app_password": secrets.token_hex(32), "redis_user": REDIS_USER,
                       "redis_password": secrets.token_hex(32),
                       "redis_databases": {"api": 8, "fusion": 9, "agents": 10, "actions": 11, "threatintel": 12}}
        self.secrets.extend(self.config[k] for k in ("owner_password", "app_password", "redis_password"))
        self.config_path.write_text(json.dumps(self.config, indent=2) + "\n")
        self.config_path.chmod(0o600)
        owner_password = self.config["owner_password"]
        app_password = self.config["app_password"]
        sql = (f"CREATE ROLE {OWNER} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '{owner_password}';\n"
               f"CREATE ROLE {APP} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '{app_password}';\n"
               f"CREATE DATABASE {DATABASE} OWNER {OWNER};\n"
               f"REVOKE CONNECT ON DATABASE {DATABASE} FROM PUBLIC;\n"
               f"GRANT CONNECT ON DATABASE {DATABASE} TO {OWNER}, {APP};\n")
        self.pg(sql, database="postgres")
        self.restore_redis_user()
        (self.private / "runtime.env").write_text(
            f"DATABASE_URL=postgresql+asyncpg://{APP}:{app_password}@192.168.1.21:5432/{DATABASE}\n"
            f"DATABASE_MIGRATION_URL=postgresql+asyncpg://{OWNER}:{owner_password}@192.168.1.21:5432/{DATABASE}\n"
            f"AISOC_APP_DB_PASSWORD={app_password}\n"
            + "".join(f"SOCAI2_{service.upper()}_REDIS_URL=redis://{REDIS_USER}:{self.config['redis_password']}@192.168.1.21:6379/{index}\n"
                      for service, index in self.config["redis_databases"].items())
        )
        (self.private / "runtime.env").chmod(0o600)
        result = {"database": DATABASE, "new_roles": [OWNER, APP], "owner_superuser": False,
                  "postgres_version": self.pg("SHOW server_version;").stdout.strip(),
                  "redis_logical_db_preexisting_key_counts": counts,
                  "redis_user": REDIS_USER, "redis_db_allocation": self.config["redis_databases"],
                  "postgres_logging_checked": log_settings, "old_databases_modified": False,
                  "shared_containers_restarted": False, "credentials": "private/shared-services.json and private/runtime.env"}
        self.save("provision.json", result)
        return result

    def credential_probe(self) -> dict:
        if not self.config:
            raise RuntimeError("Provision project objects before the credential probe")
        original = (self.source / "infra/postgres/initdb/20_runtime_role_password.sh").read_text()
        patched = (self.root / "generated/initdb/20_runtime_role_password.sh").read_text()
        sentinel = "SOCAI2_1B_NON_SECRET_SENTINEL_'_quote"
        def invoke(script: str, password: str):
            command = ["docker", "exec", "-i", "-e", "POSTGRES_USER=" + self.pg_admin,
                       "-e", "POSTGRES_DB=" + DATABASE, "-e", "AISOC_APP_DB_PASSWORD=" + password,
                       PG_CONTAINER, "bash", "-s"]
            return self.run(command, script)
        first = invoke(original, sentinel)
        fixed = invoke(patched, sentinel)
        negative = invoke(original, sentinel)
        actual = invoke(patched, self.config["app_password"])
        secret_output = any(value in actual.stdout + actual.stderr for value in self.secrets)
        result = {"kind": "real PostgreSQL/psql transport with non-sensitive sentinel",
                  "original_echoes_sentinel": sentinel in first.stdout,
                  "patched_does_not_echo_sentinel": sentinel not in fixed.stdout + fixed.stderr,
                  "negative_control_original_echoes_again": sentinel in negative.stdout,
                  "real_credential_absent_from_patched_output": not secret_output}
        if not all(value for key, value in result.items() if key != "kind"):
            raise RuntimeError("Credential-output regression check failed; no secret output published")
        self.save("credential-probe.json", result)
        return result

    def migrate(self) -> dict:
        if not self.config:
            raise RuntimeError("Missing project credential state")
        manifest = json.loads((self.source / "docs/handoff/1b-import-manifest.json").read_text())
        entries = sorted((e for e in manifest["files"] if e["destination"].endswith(".sql")),
                         key=lambda e: Path(e["destination"]).name)
        if len(entries) != 134:
            raise RuntimeError("Expected the complete fixed 134-file SQL set")
        self.pg(f"SET ROLE {OWNER}; CREATE TABLE IF NOT EXISTS aisoc_schema_migrations "
                "(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());")
        applied = set(self.pg(f"SET ROLE {OWNER}; SELECT name FROM aisoc_schema_migrations;").stdout.splitlines())
        receipts_path = self.evidence / "migration-files.json"
        receipts = json.loads(receipts_path.read_text()) if receipts_path.exists() else []
        known = {item["name"]: item for item in receipts if item.get("success")}
        for entry in entries:
            path = self.source / entry["destination"]
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise RuntimeError("SQL hash mismatch: " + path.name)
            if path.name in applied:
                if path.name not in known or known[path.name]["sha256"] != entry["sha256"]:
                    raise RuntimeError("Ledger entry lacks matching project receipt: " + path.name)
                continue
            sql = data.decode()
            adaptation = None
            if path.name == "061_runtime_app_role.sql":
                start = sql.index("ALTER ROLE aisoc_app\n")
                end = sql.index("-- ─── 2. Minimum grants", start)
                # Global role attributes require the existing cluster operator;
                # table ownership/default grants remain scoped to the new owner.
                sql = sql[:start] + "RESET ROLE;\n" + sql[start:end] + f"SET ROLE {OWNER};\n" + sql[end:]
                adaptation = "Only role-attribute/comment block runs as infrastructure operator; all schema/default grants run as aisoc"
            begin = time.monotonic()
            result = self.pg(f"SET ROLE {OWNER};\n" + sql +
                             "\nINSERT INTO aisoc_schema_migrations(name) VALUES ('" + path.name + "');\n",
                             allow_error=True)
            receipt = {"name": path.name, "sha256": entry["sha256"],
                       "success": result.returncode == 0, "seconds": round(time.monotonic() - begin, 3)}
            if adaptation:
                receipt["shared_service_adaptation"] = adaptation
            if result.returncode:
                receipt["error"] = self.redact(result.stderr)[:1800]
            receipts.append(receipt)
            self.save("migration-files.json", receipts)
            if result.returncode:
                raise RuntimeError("Migration failed and retained for inspection: " + path.name + "\n" + receipt["error"])
        actual = set(self.pg(f"SET ROLE {OWNER}; SELECT name FROM aisoc_schema_migrations;").stdout.splitlines())
        expected = {Path(e["destination"]).name for e in entries}
        if actual != expected:
            raise RuntimeError("Migration ledger does not equal the complete filename set")
        result = {"expected_files": len(expected), "actual_files": len(actual), "all_file_names_match": True,
                  "numeric_prefix_deduplication": False, "owner": OWNER,
                  "sql_sources_modified": False, "existing_database_contents_touched": False}
        self.save("migration-summary.json", result)
        return result

    def verify(self) -> dict:
        if not self.config:
            raise RuntimeError("Missing project credential state")
        batch_uuid = uuid.uuid5(uuid.NAMESPACE_URL, "socai2/" + BATCH)
        tenant_a = str(uuid.uuid5(batch_uuid, "tenant-a"))
        tenant_b = str(uuid.uuid5(batch_uuid, "tenant-b"))
        alert_a = str(uuid.uuid5(batch_uuid, "alert-a"))
        alert_b = str(uuid.uuid5(batch_uuid, "alert-b"))
        self.pg(f"SET ROLE {OWNER}; INSERT INTO tenants(id,name,slug) VALUES "
                f"('{tenant_a}','socai2 1B tenant A','socai2-1b-a'),"
                f"('{tenant_b}','socai2 1B tenant B','socai2-1b-b') ON CONFLICT(id) DO NOTHING;"
                f"INSERT INTO alerts(id,tenant_id,title,severity,tags) VALUES "
                f"('{alert_a}','{tenant_a}','socai2 1B persistence A','medium','[\"{BATCH}\"]'::jsonb),"
                f"('{alert_b}','{tenant_b}','socai2 1B persistence B','medium','[\"{BATCH}\"]'::jsonb) "
                "ON CONFLICT(id) DO NOTHING;")
        role_flags = json.loads(self.pg("SELECT json_agg(json_build_object('role',rolname,'superuser',rolsuper,"
                                      "'bypass_rls',rolbypassrls,'create_db',rolcreatedb,'create_role',rolcreaterole))::text "
                                      "FROM pg_roles WHERE rolname IN ('aisoc','aisoc_app');").stdout)
        if any(flag[field] for flag in role_flags for field in ("superuser", "bypass_rls", "create_db", "create_role")):
            raise RuntimeError("Project role privilege boundary failed")
        owner_tcp = self.pg("SELECT current_user,current_database();", login=OWNER, tcp=True).stdout.strip()
        app_tcp = self.pg("SELECT current_user,current_database();", login=APP, tcp=True).stdout.strip()
        bound_a = self.pg(f"BEGIN; SET LOCAL app.current_tenant_id='{tenant_a}'; "
                          f"SELECT id FROM alerts WHERE id IN ('{alert_a}','{alert_b}') ORDER BY id; COMMIT;",
                          login=APP, tcp=True).stdout.strip()
        bound_b = self.pg(f"BEGIN; SET LOCAL app.current_tenant_id='{tenant_b}'; "
                          f"SELECT id FROM alerts WHERE id IN ('{alert_a}','{alert_b}') ORDER BY id; COMMIT;",
                          login=APP, tcp=True).stdout.strip()
        if bound_a != alert_a or bound_b != alert_b:
            raise RuntimeError("Tenant-bound runtime reads failed")
        own_write = self.pg(f"BEGIN; SET LOCAL app.current_tenant_id='{tenant_a}'; "
                           f"UPDATE alerts SET description='1B runtime write verified' WHERE id='{alert_a}'; "
                           f"SELECT description FROM alerts WHERE id='{alert_a}'; COMMIT;", login=APP, tcp=True)
        cross_write = self.pg(f"BEGIN; SET LOCAL app.current_tenant_id='{tenant_a}'; "
                             f"INSERT INTO alerts(tenant_id,title) VALUES ('{tenant_b}','forbidden cross-tenant'); COMMIT;",
                             login=APP, tcp=True, allow_error=True)
        ddl = self.pg("CREATE TABLE public.socai2_forbidden_ddl(id integer);", login=APP, tcp=True, allow_error=True)
        if cross_write.returncode == 0 or ddl.returncode == 0:
            raise RuntimeError("Runtime cross-tenant write or DDL unexpectedly allowed")
        if "row-level security" not in cross_write.stderr or "permission denied for schema public" not in ddl.stderr:
            raise RuntimeError("Rejected operations failed for an unexpected reason")
        unbound = self.pg(f"SELECT count(*) FROM alerts WHERE id IN ('{alert_a}','{alert_b}');", login=APP, tcp=True).stdout.strip()
        rows = self.pg(f"SELECT id,description FROM alerts WHERE id IN ('{alert_a}','{alert_b}') ORDER BY id;",
                       login=OWNER, tcp=True).stdout.strip().splitlines()
        if "1B runtime write verified" not in own_write.stdout or len(rows) != 2 or unbound != "2":
            raise RuntimeError("Fresh-connection persistence or unbound-session observation differs")
        wal = self.pg("SELECT json_build_object('synchronous_commit',current_setting('synchronous_commit'),"
                      "'flush_lsn',pg_current_wal_flush_lsn()::text)::text;").stdout.strip()
        redis_user = self.redis("ACL", "WHOAMI", app=True).stdout.strip()
        key = "socai2:1b:" + str(batch_uuid)
        marker = "persistence-" + str(batch_uuid)
        writes = self.redis(app=True, database=8,
                            content=f"SET {key} {marker} EX 3600\nWAITAOF 1 0 5000\nGET {key}\n")
        lines = writes.stdout.strip().splitlines()
        if lines != ["OK", "1", "0", marker]:
            raise RuntimeError("Redis write/read/WAITAOF persistence confirmation failed")
        fresh_read = self.redis("GET", key, app=True, database=8).stdout.strip()
        dangerous_denied = {}
        for command in ("FLUSHALL", "FLUSHDB", "CONFIG", "SHUTDOWN"):
            arguments = ("ACL", "DRYRUN", REDIS_USER, command)
            if command == "CONFIG":
                arguments += ("GET", "databases")
            result = self.redis(*arguments, allow_error=True)
            dangerous_denied[command] = "no permissions" in (result.stdout + result.stderr).lower()
        if redis_user != REDIS_USER or fresh_read != marker or not all(dangerous_denied.values()):
            raise RuntimeError("Redis identity, fresh read or dangerous-command ACL failed")
        redis_aclfile = self.redis("CONFIG", "GET", "aclfile").stdout.strip().splitlines()[1:]
        self.redis("DEL", key, app=True, database=8)
        if self.redis("EXISTS", key, app=True, database=8).stdout.strip() != "0":
            raise RuntimeError("Project Redis test-key cleanup failed")
        self.pg(f"SET ROLE {OWNER}; DELETE FROM alerts WHERE id IN ('{alert_a}','{alert_b}'); "
                f"DELETE FROM tenants WHERE id IN ('{tenant_a}','{tenant_b}');")
        cleaned = self.pg(f"SELECT count(*) FROM alerts WHERE id IN ('{alert_a}','{alert_b}');").stdout.strip() == "0"
        limits = ["This probe uses new PG TCP sessions and Redis AOF fsync; the separate redis-restart.json records the restart test",
                  "Redis DB 8-12 allocation is logical separation; Redis ACL cannot restrict SELECT to one database",
                  "Application-level authentication and tenant binding remain batch 1F acceptance items"]
        if not (redis_aclfile and redis_aclfile[0]):
            limits.append("Project ACL user must be restored after Redis restart until an aclfile is configured")
        result = {"postgres_endpoint": "192.168.1.21:5432/aisoc", "owner_tcp_identity": owner_tcp,
                  "runtime_tcp_identity": app_tcp, "role_flags": role_flags,
                  "input": {"tenant_a": tenant_a, "tenant_b": tenant_b, "alert_a": alert_a, "alert_b": alert_b},
                  "runtime_bound_reads": {tenant_a: bound_a, tenant_b: bound_b},
                  "runtime_own_tenant_write_persisted": True, "cross_tenant_write_rejected": True,
                  "cross_tenant_rejection": self.redact(cross_write.stderr.strip()),
                  "ddl_rejection": self.redact(ddl.stderr.strip()),
                  "runtime_public_schema_ddl_rejected": True, "fresh_tcp_connection_rows": rows,
                  "unbound_runtime_session_sees_both_test_tenants": True,
                  "unbound_session_is_not_an_external_auth_boundary": True, "postgres_wal": json.loads(wal),
                  "redis_endpoint": "192.168.1.21:6379/8", "redis_user": redis_user,
                  "redis_test_key": key, "redis_fresh_connection_value": fresh_read,
                  "redis_aof_local_fsync_acknowledgments": 1, "redis_dangerous_commands_denied_by_acl_dryrun": dangerous_denied,
                  "redis_logical_databases_are_not_acl_isolation": True,
                  "redis_aclfile_configured": bool(redis_aclfile and redis_aclfile[0]),
                  "redis_acl_restore_command": "shared_1b.py --root <project-root> --restore-redis-user",
                  "only_batch_test_rows_and_key_cleaned": cleaned, "shared_services_restarted": False,
                  "limits": limits}
        self.save("verification.json", result)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--provision", action="store_true")
    action.add_argument("--credential-probe", action="store_true")
    action.add_argument("--migrate", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--restore-redis-user", action="store_true")
    args = parser.parse_args()
    batch = None
    try:
        batch = SharedBatch(args.root.resolve())
        if args.provision:
            result = batch.provision()
        elif args.credential_probe:
            result = batch.credential_probe()
        elif args.migrate:
            result = batch.migrate()
        elif args.restore_redis_user:
            result = batch.restore_redis_user()
        else:
            result = batch.verify()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        message = batch.redact(str(exc)) if batch else type(exc).__name__
        print(json.dumps({"batch": BATCH, "success": False, "error": message}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
