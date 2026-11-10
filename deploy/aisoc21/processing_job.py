"""On-demand internal investigation processing. No HTTP listener or background dispatch.

Run with services/api on PYTHONPATH and the processing image's dependencies.
Writes require the tenant user's scoped API key through the configured stream. Keep the
same subject, scope revision, run and operation key when checking a previous attempt.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote, urlsplit
from uuid import UUID


class Refused(Exception):
    """Only fixed diagnostic codes may cross the job boundary."""


def require(condition, code):
    if not condition:
        raise Refused(code)


def self_test():
    """Project an unavailable model result through the very same C6 renderer."""
    from app.socai2.baseline_contracts import Scope
    from app.socai2.baseline_delivery_projection import make_publication

    alerts = [UUID(int=1), UUID(int=2)]
    scope = Scope(kind="whole_case", alert_ids=alerts, object_keys=[], limitations=[],
                  window_start=None, window_end=None)
    members = {aid: {"read_state": "read", "analysis_state": "not_analyzed"} for aid in alerts}
    publication, reasons = make_publication(
        None, SimpleNamespace(scope=scope, questions=[], omissions=[]), members, {},
        {"state": "initial"}, {"graph_artifact_id": None, "delivery_state": "partial"},
        UUID(int=3), "self_test_model_unavailable",
    )
    require(publication.conclusion_origin == "system" and publication.conclusion_state == "uncertain"
            and publication.validation_state == "system_only" and publication.delivery_state == "partial"
            and publication.terminal_state == "failed" and publication.conclusion and publication.closing_note
            and {m.alert_id for m in publication.members} == set(alerts)
            and not any(m.conclusion_covered for m in publication.members)
            and "no_accepted_final_model_conclusion" in reasons, "c6_publication_mismatch")
    return {"test": "c6_unavailable_model_projection", "input_members": len(alerts),
            "delivery_state": publication.delivery_state, "origin": publication.conclusion_origin,
            "conclusion": publication.conclusion, "result_members": len(publication.members),
            "verified_model_coverage": 0, "database_writes": 0, "model_calls": 0}


def production_profile():
    return os.environ.get("SOCAI2_PROCESSING_PROFILE") == "production21"


async def verify_target():
    from app.core.config import enforce_secure_defaults, settings
    from app.db.database import AsyncSessionLocal
    from app.socai2.baseline_service import BaselineService
    from sqlalchemy import text

    db_name = os.environ["SOCAI2_SERVICE_DATABASE_NAME"]
    role = os.environ["SOCAI2_PROCESSING_DB_ROLE"]
    tenant = UUID(os.environ["SOCAI2_PROCESSING_TENANT_ID"])
    actor_value = os.getenv("SOCAI2_PROCESSING_ACTOR_ID")
    actor = UUID(actor_value) if actor_value else None
    dsn = urlsplit(str(settings.DATABASE_URL))
    if production_profile():
        require(dsn.hostname == os.environ["SOCAI2_PROCESSING_DB_HOST"]
                and dsn.port == int(os.environ["SOCAI2_PROCESSING_DB_PORT"]),
                "production_target_required")
    else:
        require(db_name.startswith("socai2_") and actor is not None, "isolated_target_required")
    require(dsn.path == "/" + db_name and role
            and unquote(dsn.username or "") == role and tenant != actor, "isolated_target_required")
    require(settings.ENVIRONMENT == "production" and
            os.getenv("AISOC_DEV_AUTH_BYPASS", "").lower() not in {"1", "true", "yes"},
            "production_auth_required")
    enforce_secure_defaults()
    async with BaselineService(AsyncSessionLocal).transaction(tenant, readonly=True) as store:
        identity = (await store.db.execute(text("""
            SELECT current_database(), current_user,
                NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
            FROM pg_catalog.pg_roles WHERE rolname=current_user
        """))).one()
        require(tuple(identity) == (db_name, role, True), "database_identity_mismatch")
        if actor is not None:
            user = (await store.db.execute(text("""
                SELECT u.id FROM public.users u JOIN public.tenants t ON t.id=u.tenant_id
                WHERE u.id=:actor AND t.id=:tenant AND u.is_active AND t.is_active
            """), {"tenant": tenant, "actor": actor})).scalar_one_or_none()
            require(user == actor, "inactive_or_unknown_tenant_actor")
        else:
            active = await store.db.scalar(text("SELECT is_active FROM public.tenants WHERE id=:tenant"),
                                           {"tenant": tenant})
            require(active is True, "inactive_or_unknown_tenant")
        await store.db.execute(text("SELECT classification, due_at, current_evidence_artifact_id FROM socai2.cases LIMIT 0"))
        ready = (await store.db.execute(text("""
            SELECT to_regprocedure('socai2.baseline_input_freshness(uuid,uuid)') IS NOT NULL
                AND to_regclass('socai2.runs') IS NOT NULL AND to_regclass('socai2.results') IS NOT NULL
        """))).scalar_one()
        require(ready, "processing_schema_unavailable")
    return db_name, role, tenant, actor


async def principal(tenant, actor, permission):
    from app.api.v1.deps import get_current_user
    from app.db.database import AsyncSessionLocal
    from fastapi.security import HTTPAuthorizationCredentials
    from sqlalchemy import text
    from starlette.requests import Request

    key = Path(os.environ["SOCAI2_PROCESSING_API_KEY_FILE"]).read_text(encoding="utf-8").strip()
    require(key.startswith("aisoc_") and not key.startswith("aisoc_wl_"), "user_api_key_required")
    # Use the installed API-key verifier and permission check in process. This
    # supplies no forwarded address, excludes shared service/dev credentials
    # and commits last_used_at only after the scoped user's checks pass.
    request = Request({"type": "http", "headers": []})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=key)
    async with AsyncSessionLocal() as db, db.begin():
        if production_profile():
            require(actor is not None, "production_actor_required")
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": str(tenant)})
        user = await get_current_user(request, credentials, db)
        require(user.api_key_prefix and not user.workload_service and user.tenant_id == tenant
                and user.user_id == actor, "api_key_principal_mismatch")
        user.require_permission(permission)
    return user


async def verify_sources(tenant):
    from app.db.database import AsyncSessionLocal
    from app.services.llm_resolver import resolve_llm_config
    from app.socai2.baseline_optional_sources import lake_database
    from app.socai2.baseline_service import BaselineService
    from app.socai2.runtime_policy import active_policy
    from sqlalchemy import text
    policy = active_policy()
    if production_profile():
        require(policy.sha256 == os.environ["SOCAI2_INVESTIGATION_POLICY_SHA256"], "investigation_policy_changed")
    require(os.environ.get("SOCAI2_MODEL_PROTOCOL") == policy.model.protocol
            and os.environ.get("SOCAI2_MODEL_SCHEMA_PROFILE") == policy.model.schema_profile
            and os.environ.get("AISOC_AIRGAPPED", "").lower() in {"1", "true"}
            and lake_database() == os.environ["CLICKHOUSE_DATABASE"],
            "processing_sources_required")
    async with BaselineService(AsyncSessionLocal).transaction(tenant, readonly=True) as store:
        if production_profile():
            override = await store.db.scalar(text("SELECT EXISTS(SELECT FROM public.tenant_llm_credentials "
                                                  "WHERE tenant_id=:tenant AND enabled)"), {"tenant": tenant})
            require(not override, "production_tenant_model_override_requires_review")
        config = await resolve_llm_config(store.db, tenant)
    require(config.base_url.rstrip("/") == os.environ["OPENAI_BASE_URL"].rstrip("/") and config.model == policy.model.alias,
            "local_model_target_mismatch")
    allowlist = json.loads(os.environ["AISOC_AIRGAP_ALLOWLIST"])
    require({urlsplit(config.base_url).hostname, urlsplit(policy.model.tokenizer["endpoint"]).hostname} <= set(allowlist),
            "processing_source_endpoint_not_allowed")
    return config


async def check_dependencies(config):
    import hashlib

    import httpx
    from app.core.config import settings
    from app.db.clickhouse import close_clickhouse, execute_lake_query
    from app.models.socai2 import Cases
    from app.socai2 import runtime_policy
    from app.socai2.baseline_optional_sources import lake_database
    from app.socai2.runtime_policy import active_policy

    page_columns = ["classification", "due_at", "current_evidence_artifact_id"]
    require(all(name in Cases.__table__.c for name in page_columns), "processing_orm_missing_page_fields")
    require(config.allowed and config.api_key, "gateway_credentials_unavailable")
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=10) as client:
        catalog = await client.get(config.base_url.rstrip("/") + "/models",
                                   headers={"Authorization": "Bearer " + config.api_key})
    require(catalog.status_code == 200 and
            any(row.get("id") == config.model for row in catalog.json().get("data", []) if isinstance(row, dict)),
            "gateway_alias_unverified")
    lake = lake_database()  # validates the SQL identifier
    require(settings.CLICKHOUSE_DATABASE == lake and not settings.AISOC_DISABLE_CLICKHOUSE,
            "lake_configuration_mismatch")
    try:
        identity = await execute_lake_query("SELECT currentDatabase(), currentUser()", timeout_seconds=8)
        require(identity.rows == [[lake, settings.CLICKHOUSE_USER]], "lake_identity_mismatch")
        # Verify SELECT on the original table/columns without reading event rows.
        empty = await execute_lake_query(f"SELECT event_id, tenant_id FROM {lake}.raw_events LIMIT 0", timeout_seconds=8)
        require(not empty.rows and empty.columns == ["event_id", "tenant_id"], "lake_projection_unavailable")
    finally:
        await close_clickhouse()
    policy = active_policy()
    code = Path(runtime_policy.__file__).parent
    return {"orm_page_fields": page_columns, "catalog_alias": config.model,
            "lake_table": lake + ".raw_events", "lake_log_rows_read": 0,
            "processing_profile_sha256": os.environ.get("SOCAI2_PROCESSING_PROFILE_SHA256"),
            "investigation_policy_sha256": policy.sha256, "investigation_policy_version": policy.version,
            "single_model_timeout_seconds": policy.single_model_timeout_seconds,
            "case_deadline_seconds": policy.case.deadline_seconds, "final_reserve_seconds": policy.final_reserve_seconds,
            "implementation_sha256": {name: hashlib.sha256((code / name).read_bytes()).hexdigest() for name in (
                "runtime_policy.py", "token_budget.py", "stage_answer_review.py", "program_facts.py", "baseline_reasoning.py",
                "baseline_delivery.py", "baseline_evidence_index.py")}}


def case_start_receipt(record):
    from app.socai2.case_contracts import RunDetail

    detail = RunDetail.model_validate(record)
    return {"run_id": detail.run.id, "state": detail.run.state, "delivery_state": detail.run.delivery_state,
            "stop_reason": detail.run.stop_reason, "result_ids": detail.result_ids}


async def prepare_production_subjects(args, tenant):
    if args.command not in {"alert", "incident", "case-create"}:
        return
    params = ["--tenant", str(tenant)]
    for subject in ("alert", "incident"):
        ids = [args.subject] if args.command == subject else getattr(args, subject + "_id", [])
        for uid in ids:
            params.extend(("--" + subject + "-id", str(uid)))
    env = {"DATABASE_URL": os.environ["SOCAI2_INGRESS_URL"], "PYTHONPATH": os.environ["SOCAI2_PROCESSING_FUSION_PYTHONPATH"],
           "PYTHONDONTWRITEBYTECODE": "1", "PGSSLROOTCERT": os.environ["PGSSLROOTCERT"],
           "PGSSLMODE": os.environ["PGSSLMODE"], "SSL_CERT_FILE": os.environ["SSL_CERT_FILE"]}
    for key in ("SOCAI2_SERVICE_DATABASE_NAME", "SOCAI2_PROCESSING_INGRESS_ROLE", "SOCAI2_PROCESSING_DB_HOST", "SOCAI2_PROCESSING_DB_PORT"):
        env[key] = os.environ[key]
    proc = await asyncio.create_subprocess_exec(sys.executable, "-B", "/opt/processor/production_ingress.py",
        *params, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    stdout, _ = await proc.communicate()
    if proc.returncode:
        try:
            error = json.loads(stdout.decode().strip().splitlines()[-1])["error"]
        except (ValueError, IndexError, KeyError, UnicodeError):
            error = None
        require(False, error if error in {"source_alert_snapshot_unavailable", "source_snapshot_invalid",
                "source_subject_absent", "source_identity_mismatch"} else "ingress_unavailable")


async def process(args):
    from app.db.database import AsyncSessionLocal, engine
    from app.socai2.baseline_contracts import Actor, Start
    from app.socai2.case_contracts import CaseCreate, PrepareBaseline
    from app.socai2.case_service import CaseService
    from app.socai2.stage_results import StageResultService

    try:
        database, role, tenant, actor = await verify_target()
        config = await verify_sources(tenant)
        if args.command == "check":
            return {"database": database, "db_role": role, "tenant_id": tenant, "actor_id": actor,
                    "check": "schema_identity_and_source_readback", "database_writes": 0, "model_calls": 0,
                    **await check_dependencies(config)}
        stage = args.command in {"alert", "incident"}
        user = await principal(tenant, actor, "alerts:write" if stage else "cases:write")
        if production_profile():
            await prepare_production_subjects(args, tenant)
        if stage:
            service = StageResultService(AsyncSessionLocal)
            execute = service.execute_alert if args.command == "alert" else service.execute_incident
            return await execute(tenant, args.subject, args.operation_key, requested_by=user.user_id)
        service = CaseService(AsyncSessionLocal)
        identity = Actor(user_id=user.user_id, name=user.email)
        if args.command == "case-create":
            request = CaseCreate(operation_key=args.operation_key, title=args.title, alert_ids=args.alert_id,
                                 incident_ids=args.incident_id)
            receipt = await service.create_case(tenant, request, actor=identity)
            return receipt.model_dump(mode="json")
        fields = {"expected_scope_revision": args.scope_revision, "operation_key": args.operation_key}
        if args.command == "case-prepare":
            receipt = await service.prepare_baseline(tenant, args.subject, PrepareBaseline(**fields), actor=identity)
            return receipt.model_dump(mode="json")
        start = Start(**fields, window_start=args.window_start, window_end=args.window_end,
                      comparison_result_id=args.comparison_result_id)
        return case_start_receipt(await service.start_case(tenant, args.subject, args.run_id, start, actor=identity))
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check target identity, schema and model configuration without dispatch")
    commands.add_parser("self-test", help="compute a two-alert C6 fallback entirely in memory")
    for name in ("alert", "incident", "case-create", "case-prepare", "case-start"):
        command = commands.add_parser(name)
        command.add_argument("--operation-key", type=UUID, required=True, help="stable caller-supplied operation UUID")
        if name == "case-create":
            command.add_argument("--title", required=True)
            command.add_argument("--alert-id", type=UUID, action="append", default=[])
            command.add_argument("--incident-id", type=UUID, action="append", default=[])
        else:
            command.add_argument("--subject", type=UUID, required=True, help="alert, incident or case ID")
        if name in {"case-prepare", "case-start"}:
            command.add_argument("--scope-revision", type=int, required=True)
        if name == "case-start":
            command.add_argument("--run-id", type=UUID, required=True)
            command.add_argument("--window-start", help="optional ISO 8601 timestamp including offset")
            command.add_argument("--window-end", help="optional ISO 8601 timestamp including offset")
            command.add_argument("--comparison-result-id", type=UUID)
    args = parser.parse_args()
    if getattr(args, "scope_revision", 0) < 0:
        parser.error("scope revision must be non-negative")
    if args.command == "case-create" and not (args.alert_id or args.incident_id):
        parser.error("case-create requires at least one --alert-id or --incident-id")
    try:
        result = self_test() if args.command == "self-test" else asyncio.run(process(args))
    except Exception as exc:  # noqa: BLE001 -- no provider/connection details in job output
        reason = type(exc).__name__
        if isinstance(exc, Refused):
            reason = str(exc)
        elif exc.__class__.__module__ == "app.socai2.baseline_store" and reason == "StoreError":
            reason = exc.code
        result = {"error": reason, "command": args.command}
        if hasattr(args, "operation_key"):
            result["operation_key"] = args.operation_key
        if hasattr(args, "subject"):
            result["subject"] = args.subject
        if args.command == "case-start":
            result["requested_run_id"] = args.run_id
        print(json.dumps(result, default=str))
        return 1
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 2 if result.get("state") in {"unknown", "failed", "cancelled", "running", "pending_update"} else 0


if __name__ == "__main__":
    sys.exit(main())
