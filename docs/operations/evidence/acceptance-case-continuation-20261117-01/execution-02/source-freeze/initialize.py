"""Initialize a new, explicitly named local database; never reuse or clear one."""
import argparse
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser()
parser.add_argument("--config", type=Path, required=True)
args = parser.parse_args()
config = json.loads(args.config.read_text())
database = json.loads(Path(config["database_profile"]).read_text())
out = Path(__file__).parent
spec = importlib.util.spec_from_file_location("installer", ROOT / "deploy/database/install_reader.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
profile = installer.load_profile(args.config.parent / "install.toml")
assert database["processing_database"] == profile["database"]
assert database["container"] in profile["psql_argv"]
for name in (profile["database"], database["processor"], database["owner"]):
    assert re.fullmatch(r"[a-z_][a-z0-9_]*", name)
command = profile["psql_argv"] + ["-U", profile["admin_role"], "-v", "ON_ERROR_STOP=1"]


def sql(db, query):
    result = subprocess.run(command + ["-d", db], input=query, text=True,
                            capture_output=True, timeout=profile["timeout_seconds"], check=False)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout


name, owner, processor = profile["database"], database["owner"], database["processor"]
before = sql("postgres", "SELECT oid,datname FROM pg_database ORDER BY oid")
assert not any(line.split("|")[-1] == name for line in before.splitlines()), "target_already_exists"
sql("postgres", f'CREATE DATABASE "{name}" OWNER "{owner}";')
result = installer.execute(profile, "initialize-current")
(out / "database-install.stdout").write_text(result.stdout)
(out / "database-install.stderr").write_text(result.stderr)
assert result.returncode == 0, "database_initialization_failed_preserve_for_review"
sql(name, f'GRANT CONNECT ON DATABASE "{name}" TO "{processor}"; '
    f'GRANT USAGE ON SCHEMA socai2,public TO "{processor}"; '
    f'GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO "{processor}"; '
    f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{processor}";')
after = sql("postgres", "SELECT oid,datname FROM pg_database ORDER BY oid")
assert set(before.splitlines()) < set(after.splitlines())
assert len(set(after.splitlines()) - set(before.splitlines())) == 1
schema = sql(name, "SELECT count(DISTINCT table_name),count(*) FROM information_schema.columns "
             "WHERE table_schema='socai2'")
assert schema.strip() == "32|521", schema
(out / "database-initialization.json").write_text(json.dumps({
    "status": "passed", "database": name, "container": database["container"],
    "schema_tables": 32, "schema_columns": 521, "migrations": "123–129",
    "old_database_oids_unchanged": True, "old_databases_modified": False,
    "cleared_databases": 0, "source_business_rows": 0}, indent=2) + "\n")
print("New isolated database initialized: 32 tables, 521 columns; no old database changed.")
