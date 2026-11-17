"""Small helpers for this one saved-material Case continuation, not a test framework."""
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT), str(ROOT / "services/api"), str(ROOT / "tools/testdata")]
TABLES = ("alerts", "alert_materials", "alert_objects", "alert_source_refs", "alert_assessments",
    "incidents", "incident_alerts", "incident_diagnoses", "cases", "case_alerts", "case_incidents",
    "case_alert_exclusions", "analysis_tasks", "analysis_attempts", "analysis_subject_state",
    "runs", "run_members", "run_steps", "artifacts", "results", "result_members", "case_assessments",
    "case_assessment_sources", "case_assessment_members", "activities", "activity_targets")


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=lambda v:
        v.isoformat() if isinstance(v, datetime) else str(v)) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def environment(config):
    for key in ("environment_file", "model_environment_file", "lake_environment_file"):
        path = Path(config[key])
        if path.exists():
            os.environ.update(json.loads(path.read_text()))
    os.environ.update(config["runtime_overrides"])
    for name, key in (("SOCAI2_INVESTIGATION_POLICY", "investigation_policy_file"),
                     ("SOCAI2_ANALYSIS_TASKS_CONFIG_FILE", "lifecycle_policy_file"),
                     ("SOCAI2_CASE_ALLOCATION_CONFIG_FILE", "allocation_policy_file"),
                     ("SOCAI2_RUN_RECORDS_CONFIG_FILE", "run_records_config_file")):
        os.environ[name] = config[key]
    os.environ.pop("SOCAI2_KNOWLEDGE_PROFILE", None)


def engine(config, *, admin=False):
    from sqlalchemy.engine import URL
    from sqlalchemy.ext.asyncio import create_async_engine
    db = json.loads(Path(config["database_profile"]).read_text())
    url = URL.create("postgresql+psycopg", username=db["admin"],
        password=Path(db["password_file"]).read_text().strip(), host=db["host"], port=db["port"],
        database=db["processing_database"])
    options = {} if admin else {"options": "-c role=" + db["processor"]}
    return create_async_engine(url, hide_parameters=True, pool_size=config["database_pool_size"], max_overflow=0,
                               connect_args={"sslmode": config["sslmode"], **options})


async def snapshot(db_engine, tenant):
    from sqlalchemy import text
    rows = {}
    async with db_engine.connect() as db, db.begin():
        await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": tenant})
        for table in TABLES:
            rows[table] = (await db.execute(text(f"SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') "
                f"FROM socai2.{table} t WHERE tenant_id=:tenant"), {"tenant": UUID(tenant)})).scalar_one()
        assert (await db.execute(text("SHOW transaction_read_only"))).scalar_one() == "on"
    return rows, {t: {"count": len(v), "sha256": digest(v)} for t, v in rows.items()}


def same(left, right):
    if isinstance(left, str) and isinstance(right, str):
        try:
            return datetime.fromisoformat(left.replace("Z", "+00:00")) == datetime.fromisoformat(right.replace("Z", "+00:00"))
        except ValueError:
            return left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right
