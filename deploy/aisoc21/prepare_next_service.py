"""Build a credential-free candidate only; no network, database or deployment."""
import argparse
import hashlib
import io
import json
import re
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_IMAGE = "socai2-investigation-api:20261101-r13"
BASE_IMAGE_ID = "sha256:7ca0572275260ee96a677665e20d513b0ced6a58fcfdba1b13ca2c6922ac5093"
SUPPORT_TABLES = {"tenants", "users", "api_keys", "connectors", "tenant_llm_credentials",
    "assets", "threat_intel_iocs", "user_risk_profiles", "insider_indicators", "roles", "permissions",
    "role_permissions", "user_roles", "privilege_grants", "permission_conditions"}


def support_schema():
    sys.path.insert(0, str(ROOT / "services/api"))
    import app.models.enterprise_iam
    import app.models.rbac  # noqa: F401 -- populate metadata
    from app.models import Base
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.schema import CreateIndex, CreateTable, sort_tables

    tables = [Base.metadata.tables[name] for name in sorted(SUPPORT_TABLES)]
    for tab in tables:
        assert all(fk.column.table.name in SUPPORT_TABLES for fk in tab.foreign_keys)
    ddl = ["BEGIN;", "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
        "CREATE TABLE IF NOT EXISTS public.aisoc_schema_migrations(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());",
        "CREATE OR REPLACE FUNCTION public.current_tenant_id() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('app.current_tenant_id',true),'')::uuid $$;"]
    for table in sort_tables(tables):
        ddl.append(str(CreateTable(table, if_not_exists=True).compile(dialect=dialect()))+";")
        for index in sorted(table.indexes, key=lambda i: i.name):
            ddl.append(str(CreateIndex(index, if_not_exists=True).compile(dialect=dialect()))+";")
    ddl.append((ROOT / "services/api/migrations/016_knowledge_base.sql").read_text("utf-8"))
    ddl.append("COMMIT;")
    return "\n".join(ddl).encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="socai2-next-api:20261104-n1")
    args = parser.parse_args()
    if not re.fullmatch(r"socai2-next-api:20261104-n[1-9][0-9]*", args.image):
        raise ValueError("invalid independent-service image tag")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / ".local"):
        raise ValueError("candidate output must be inside repository .local")
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for path in sorted((ROOT / "services/api/app").rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc" or not path.is_file():
            continue
        if path.is_symlink() or any(part.startswith(".") for part in path.relative_to(ROOT/"services/api/app").parts):
            raise ValueError("unexpected application entry")
        files["app/"+path.relative_to(ROOT/"services/api/app").as_posix()] = path.read_bytes()
    if "app/socai2_main.py" not in files:
        raise ValueError("isolated application entry point is missing")
    for name in ["123_socai2_page_data_model.sql", "124_socai2_case_source_binding.sql", "125_socai2_baseline_input_freshness.sql"]:
        files["migrations/"+name] = (ROOT/"services/api/migrations"/name).read_bytes()
    files["support-schema.sql"] = support_schema()
    source = (ROOT/"services/api/clickhouse/001_init.sql").read_text("utf-8")
    start = source.index("CREATE TABLE IF NOT EXISTS aisoc.raw_events")
    end = source.index("SETTINGS index_granularity = 8192;", start)+len("SETTINGS index_granularity = 8192;")
    files["lake-schema.sql"] = ("CREATE DATABASE IF NOT EXISTS socai2_next_validation;\n"+
        source[start:end].replace("aisoc.raw_events", "socai2_next_validation.raw_events")+"\n").encode()
    for name in ["compose.next-service.yml", "compose.next-deepseek.yml", "next_service_remote.py", "next_acceptance_remote.py", "next_acceptance_seed.py"]:
        files[name] = (ROOT/"deploy/aisoc21"/name).read_bytes()
    assert files["compose.next-service.yml"].count(b"image: socai2-next-api:20261104-n1") == 1
    files["compose.next-service.yml"] = files["compose.next-service.yml"].replace(
        b"image: socai2-next-api:20261104-n1", ("image: " + args.image).encode())
    assert ("image: " + args.image).encode() in files["compose.next-service.yml"]
    for path in sorted((ROOT/"services/fusion/app").rglob("*.py")):
        if "__pycache__" not in path.parts:
            files["fusion/app/"+path.relative_to(ROOT/"services/fusion/app").as_posix()] = path.read_bytes()
    files["Dockerfile"] = (f"FROM {BASE_IMAGE}\nUSER root\nWORKDIR /app\nENV PYTHONPATH=/app\nRUN rm -rf /app/app\n"
        "COPY --chown=10001:10001 app /app/app\nUSER 10001:10001\n"
        'CMD ["python","-m","uvicorn","app.socai2_main:app","--host","0.0.0.0","--port","8000","--workers","1"]\n').encode()
    manifest = {"created_at": datetime.now(UTC).isoformat(), "base_image": BASE_IMAGE,
        "base_image_id": BASE_IMAGE_ID, "image": args.image,
        "public_support_tables": sorted(SUPPORT_TABLES | {"aisoc_kb_documents", "aisoc_schema_migrations"}),
        "database": "socai2_next_20261104", "lake_database": "socai2_next_validation",
        "files": {name: {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "mode": "0644"}
            for name, body in sorted(files.items())}}
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode()
    archive = output/"candidate.tar"
    with tarfile.open(archive, "w") as tar:
        for name, body in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(body), 0o644, 0
            tar.addfile(info, io.BytesIO(body))
    (output/"manifest.json").write_bytes(files["manifest.json"])
    result = {"archive": str(archive), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(files["manifest.json"]).hexdigest(), "files": len(manifest["files"]),
        "application_files": len([k for k in files if k.startswith("app/")]), "deployed": False}
    (output/"preparation.json").write_text(json.dumps(result, indent=2)+"\n", "utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
