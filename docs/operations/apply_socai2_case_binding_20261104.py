"""Apply incremental 124 only to the existing, named synthetic review database."""
import hashlib
import json
from datetime import UTC, datetime

from verify_socai2_store_20261103 import DATABASE, ROOT, sql

path = ROOT / "services/api/migrations/124_socai2_case_source_binding.sql"
assert DATABASE == "socai2_schema_review_20261103_a1"
assert sql("SELECT current_database();") == DATABASE
query = """SELECT json_build_object('tables',count(DISTINCT table_name),'columns',count(*))
 FROM information_schema.columns WHERE table_schema='socai2';"""
before = json.loads(sql(query))
assert before["tables"] == 29 and before["columns"] in {458, 459}
sql(path.read_text("utf-8"))
after = json.loads(sql(query))
assert after == {"tables": 29, "columns": 459}
stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
out = ROOT / "docs/operations/evidence/socai2-case-relations-20261104" / stamp / "migration.json"
out.parent.mkdir(parents=True, exist_ok=False)
receipt = {"database": DATABASE, "synthetic_only": True, "before": before, "after": after,
    "migration": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "unverified_case_count": int(sql("SELECT count(*) FROM socai2.cases WHERE source_namespace IS NULL;")),
    "old_database_or_frozen_run_changes": False}
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps(receipt), flush=True)
