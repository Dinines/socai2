"""Create new private local credentials and reviewable schemas; never connect."""
import argparse
import base64
import hashlib
import json
import os
import secrets
from datetime import UTC, datetime

from config import DATABASE, ENV_FILE, LAKE, PORTS, PRIVATE, ROOT, STATE, TENANT, USER
from schema import (
    MIGRATIONS,
    SUPPORT_TABLES,
    grants_schema,
    lake_schema,
    support_schema,
)


def write_private(path, body):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
        stream.write(body)


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    assert not ENV_FILE.exists(), "private environment already exists; do not regenerate credentials"
    PRIVATE.mkdir(parents=True, mode=0o700, exist_ok=True)
    PRIVATE.chmod(0o700)
    # Only generated credentials, never a local/remote credential import.
    values = {k: secrets.token_hex(32) for k in ("PG_ADMIN_PASSWORD", "CH_ADMIN_PASSWORD", "API_DB_PASSWORD",
        "FUSION_DB_PASSWORD", "CH_READER_PASSWORD", "CH_WRITER_PASSWORD", "SECRET_KEY", "JWT_SECRET",
        "REALTIME_INTERNAL_TOKEN", "AISOC_REALTIME_JWT_SECRET", "METRICS_TOKEN")}
    values.update({"API_KEY": "aisoc_" + secrets.token_hex(32), "READ_API_KEY": "aisoc_" + secrets.token_hex(32),
        "AISOC_CREDENTIAL_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
        "OPENAI_API_KEY": "", "OPENAI_BASE_URL": "https://api.deepseek.com", "OPENAI_MODEL": "deepseek-flash",
        "SOCAI2_MODEL_PROTOCOL": "deepseek_responses", "SOCAI2_MODEL_SCHEMA_PROFILE": "standard"})
    # Importing ORM metadata must not search the repository's .env.
    previous = os.getcwd()
    try:
        os.chdir(PRIVATE)
        files = {"support.sql": support_schema(), "grants.sql": grants_schema(), "lake.sql": lake_schema()}
    finally:
        os.chdir(previous)
    files.update({n: (ROOT / "services/api/migrations" / n).read_text() for n in MIGRATIONS})
    schema_dir = STATE / "schema"
    schema_dir.mkdir(exist_ok=False)
    for name, body in files.items():
        (schema_dir / name).write_text(body)
    manifest = {"created_at": datetime.now(UTC).isoformat(), "database": DATABASE, "lake_database": LAKE,
        "tenant_id": TENANT, "user_id": USER, "ports": PORTS,
        "public_support_tables": sorted(SUPPORT_TABLES | {"aisoc_kb_documents", "aisoc_schema_migrations"}),
        "schema_files": {n: hashlib.sha256(b.encode()).hexdigest() for n, b in files.items()},
        "expected_socai2_tables": 29, "expected_socai2_columns": 459, "model_key_configured": False,
        "source": "current_local_checkout", "old_data_copied": False, "services_started": False}
    (STATE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_private(ENV_FILE, "".join(k + "=" + v + "\n" for k, v in sorted(values.items())))
    print(json.dumps({"prepared": True, "private_env_path": str(ENV_FILE), "schema_directory": str(schema_dir),
                      "database": DATABASE, "lake_database": LAKE, "services_started": False}))


if __name__ == "__main__":
    main()
