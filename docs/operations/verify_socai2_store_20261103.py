"""Run new Python store against the existing isolated PG database via SSH.

Ephemeral restricted login credentials remain in process memory only. No new
container, production DSN, business data, model, Tool, or service deployment.
"""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import secrets
import shlex
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]
DATABASE = "socai2_schema_review_20261103_a1"
CONTAINER = "spirithub-postgres-1"
SSH = ["ssh", "-F", "C:/Users/lychee/.ssh/config", "-i", "C:/Users/lychee/.ssh/id_ed25519_socai2",
       "-o", "UserKnownHostsFile=C:/Users/lychee/.ssh/known_hosts", "-o", "StrictHostKeyChecking=yes",
       "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
DEST = "root@192.168.1.21"
STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
EVIDENCE = ROOT / "docs/operations/evidence/socai2-store-20261103" / STAMP
OBSERVATIONS = []
SELECTED = None
SUITE = "storage"


def sql(query):
    args = ["docker", "exec", "-i", CONTAINER, "psql", "-X", "-v", "ON_ERROR_STOP=1",
            "-U", "spirithub", "-d", DATABASE, "-A", "-t", "-q"]
    result = subprocess.run(SSH + [DEST, shlex.join(args)], input=query.encode(),
                            capture_output=True, timeout=30, check=False)
    if result.returncode:
        # Never print SQL that could contain the ephemeral credential.
        raise RuntimeError("isolated database administrative statement failed")
    return result.stdout.decode().strip()


def save():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / "services/api/app/socai2" / name for name in
             ["baseline_contracts.py", "baseline_store.py", "baseline_service.py"]]
    paths += [ROOT / "services/api/tests/test_socai2_baseline_storage.py",
              ROOT / "services/api/migrations/123_socai2_page_data_model.sql", Path(__file__)]
    paths += [ROOT / "services/api/app/socai2/baseline_context.py",
              ROOT / "services/api/app/socai2/baseline_context.schema.json"]
    paths += [ROOT / "services/api/app/socai2/structured_output.py",
              ROOT / "services/api/app/socai2/model_errors.py",
              ROOT / "services/api/tests/test_socai2_model_errors.py",
              ROOT / "services/api/tests/test_socai2_structured_output.py",
              ROOT / "services/api/app/socai2/model_protocol.py",
              ROOT / "services/api/tests/test_socai2_model_protocol.py"]
    paths += [ROOT / "services/api/tests/test_socai2_deepseek_union_schema.py"]
    paths += [ROOT / "services/api/migrations/125_socai2_baseline_input_freshness.sql",
              ROOT / "services/api/tests/test_socai2_audit_fixes.py"]
    paths += [ROOT / "services/api/tests/test_socai2_followup_scope.py"]
    paths += [ROOT / "services/api/app/socai2/model_input_view.py", ROOT / "services/api/app/socai2/answer_validation.py",
              ROOT / "services/api/tests/socai2_test_model_view.py", ROOT / "services/api/tests/test_socai2_compact_model_input.py"]
    if SUITE == "c1":
        paths += [ROOT / "services/api/tests/test_socai2_baseline_context.py"]
    if SUITE == "c2":
        paths += [ROOT / "services/api/app/socai2" / name for name in
                  ["baseline_enrichment.py", "baseline_enrichment_sources.py", "baseline_model_view.py"]]
        paths += [ROOT / "services/api/tests/test_socai2_baseline_enrichment.py"]
    if SUITE == "c3":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["baseline_analysis.py",
            "baseline_analysis_contract.py", "baseline_analysis_model.py", "baseline_model_view.py",
            "baseline_analysis.schema.json", "baseline_enrichment.py"]]
        paths += [ROOT / "services/api/tests/test_socai2_baseline_analysis.py"]
    if SUITE == "c4":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["baseline_evidence.py",
            "baseline_evidence_tools.py", "baseline_semantics.py", "baseline_model_view.py", "baseline_enrichment.py"]]
        paths += [ROOT / "services/api/tests/test_socai2_baseline_evidence.py"]
    if SUITE in {"deep", "graph", "delivery", "executor", "case_http"}:
        paths += list((ROOT / "services/api/app/socai2").glob("baseline_*.py"))
        paths += [ROOT / "services/api/tests" / name for name in ["test_socai2_baseline_deep.py",
            "test_socai2_baseline_analysis.py", "test_socai2_baseline_evidence.py"]]
    if SUITE == "graph":
        paths += [ROOT / "services/api/tests/test_socai2_baseline_graph.py", ROOT / "services/api/app/socai2/contracts.schema.json"]
    if SUITE == "delivery":
        paths += [ROOT / "services/api/tests/test_socai2_baseline_delivery.py", ROOT / "services/api/app/socai2/contracts.schema.json"]
    if SUITE == "executor":
        paths += [ROOT / "services/api/tests/test_socai2_baseline_executor.py",
            ROOT / "services/api/tests/test_socai2_baseline_delivery.py", ROOT / "services/api/app/socai2/contracts.schema.json"]
    if SUITE == "case_http":
        paths += list((ROOT / "services/api/app/socai2").glob("case_*.py"))
        paths += [ROOT / p for p in ["services/api/app/api/v1/endpoints/socai2_cases.py",
            "services/api/app/api/v1/router.py", "services/api/app/core/config.py",
            "services/api/tests/test_socai2_case_api.py", "services/api/tests/test_socai2_baseline_executor.py",
            "services/api/tests/test_socai2_baseline_delivery.py", "services/api/app/socai2/contracts.schema.json"]]
    if SUITE in {"fusion_ingest", "fusion_bridge"}:
        paths += [ROOT / "services/fusion/app" / p for p in ["services/socai2_sink.py", "services/socai2_projection.py",
            "services/alert_sink.py", "services/delivery_recovery.py", "models/alert.py", "core/config.py", "main.py"]]
        paths += [ROOT / "services/fusion/tests/test_socai2_sink_postgres.py", ROOT / "services/api/app/socai2/contracts.schema.json"]
    if SUITE == "fusion_bridge":
        paths += list((ROOT / "services/api/app/socai2").glob("case_*.py"))
        paths += [ROOT / "services/api/tests/test_socai2_fusion_case_bridge.py",
            ROOT / "services/api/app/socai2/baseline_semantics.py", ROOT / "services/api/app/socai2/baseline_model_view.py"]
    if SUITE == "stage_results":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["stage_results.py", "stage_result_contracts.py", "contracts.schema.json"]]
        paths += [ROOT / "services/api/tests/test_socai2_stage_results.py"]
    if SUITE in {"stage_results", "stage_reader", "c1"}:
        paths += [ROOT / "services/api/app/socai2/stage_inputs.py"]
    if SUITE == "stage_reader":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["stage_results.py", "stage_result_contracts.py", "stage_reader.py",
            "stage_read_contracts.py", "baseline_model_view.py"]]
        paths += [ROOT / p for p in ["services/api/tests/test_socai2_stage_reader.py", "services/api/app/api/v1/endpoints/socai2_analysis.py",
            "services/api/app/api/v1/router.py", "services/api/app/core/config.py"]]
    if SUITE == "alert_basic":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["alert_basic_contract.py", "alert_basic_executor.py",
            "stage_results.py", "stage_result_contracts.py", "stage_inputs.py", "baseline_enrichment_sources.py",
            "baseline_analysis_model.py", "baseline_model_view.py"]]
        paths += [ROOT / "services/api/tests/test_socai2_alert_basic_executor.py"]
    if SUITE == "incident_diagnosis":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["incident_diagnosis_contract.py", "incident_diagnosis_executor.py",
            "stage_results.py", "stage_result_contracts.py", "stage_inputs.py", "stage_reader.py", "baseline_context.py",
            "alert_basic_contract.py", "baseline_analysis_model.py", "baseline_model_view.py"]]
        paths += [ROOT / "services/api/tests/test_socai2_incident_diagnosis_executor.py"]
    if SUITE == "page_reader":
        paths += [ROOT / "services/api/app/socai2" / name for name in ["page_reader.py", "page_contracts.py",
            "stage_reader.py", "stage_inputs.py", "case_reader.py", "stage_results.py"]]
        paths += [ROOT / p for p in ["services/api/tests/test_socai2_page_reader.py",
            "services/api/app/api/v1/endpoints/socai2_pages.py", "services/api/app/api/v1/router.py", "services/api/app/core/config.py"]]
    if SUITE == "case_relations":
        paths += list((ROOT / "services/api/app/socai2").glob("case_*.py"))
        paths += [ROOT / p for p in ["services/api/tests/test_socai2_case_relations.py",
            "services/api/app/api/v1/endpoints/socai2_cases.py", "services/api/app/models/socai2.py",
            "services/api/migrations/124_socai2_case_source_binding.sql"]]
    if SUITE == "stage_execution":
        paths += [ROOT / "services/api/app/socai2" / p for p in ["stage_results.py", "stage_inputs.py", "stage_read_contracts.py",
            "stage_reader.py", "alert_basic_executor.py", "incident_diagnosis_executor.py"]]
        paths += [ROOT / p for p in ["services/api/app/socai2_main.py", "services/api/app/api/v1/endpoints/socai2_stage_execution.py",
            "services/api/tests/test_socai2_stage_execution_api.py"]]
    if SUITE == "human_tasks":
        paths += list((ROOT / "services/api/app/socai2").glob("human_task_*.py"))
        paths += [ROOT / p for p in ["services/api/app/api/v1/endpoints/socai2_tasks.py", "services/api/tests/test_socai2_human_tasks.py",
            "services/api/app/socai2/baseline_model_view.py"]]
    if SUITE == "baseline_prepare":
        paths += list((ROOT / "services/api/app/socai2").glob("case_*.py"))
        paths += list((ROOT / "services/api/app/socai2").glob("human_task_*.py"))
        paths += [ROOT / p for p in ["services/api/tests/test_socai2_baseline_prepare.py",
            "services/api/app/api/v1/endpoints/socai2_cases.py"]]
    if SUITE == "external_sources":
        paths += [ROOT / "services/api/app/socai2" / p for p in ["baseline_optional_sources.py", "baseline_enrichment_sources.py",
            "baseline_enrichment.py", "baseline_evidence_tools.py", "baseline_evidence.py", "baseline_deep.py",
            "baseline_graph_projection.py", "baseline_model_view.py"]]
        paths += [ROOT / "services/api/tests/test_socai2_external_sources.py"]
    receipt = {"database": DATABASE, "synthetic_only": True, "started_at": STAMP,
               "observations": OBSERVATIONS,
               "hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (EVIDENCE / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")


def record(name, passed, detail=None):
    OBSERVATIONS.append({"name": name, "passed": passed, "detail": detail})
    save()
    print(json.dumps({"name": name, "passed": passed}), flush=True)


async def exercise(port, role, password):
    service = "fusion" if SUITE == "fusion_ingest" else "api"
    sys.path.insert(0, str(ROOT / "services" / service))
    sys.path.insert(0, str(ROOT / "services" / service / "tests"))
    test_name = {"c1": "test_socai2_baseline_context.py", "storage": "test_socai2_baseline_storage.py",
                 "c2": "test_socai2_baseline_enrichment.py", "c3": "test_socai2_baseline_analysis.py",
                 "c4": "test_socai2_baseline_evidence.py", "deep": "test_socai2_baseline_deep.py",
                 "graph": "test_socai2_baseline_graph.py", "delivery": "test_socai2_baseline_delivery.py",
                 "executor": "test_socai2_baseline_executor.py", "case_http": "test_socai2_case_api.py",
                 "fusion_ingest": "test_socai2_sink_postgres.py", "fusion_bridge": "test_socai2_fusion_case_bridge.py",
                 "stage_results": "test_socai2_stage_results.py", "stage_reader": "test_socai2_stage_reader.py",
                 "alert_basic": "test_socai2_alert_basic_executor.py",
                 "incident_diagnosis": "test_socai2_incident_diagnosis_executor.py",
                 "page_reader": "test_socai2_page_reader.py", "case_relations": "test_socai2_case_relations.py",
                 "stage_execution": "test_socai2_stage_execution_api.py", "human_tasks": "test_socai2_human_tasks.py",
                 "external_sources": "test_socai2_external_sources.py", "baseline_prepare": "test_socai2_baseline_prepare.py"}[SUITE]
    spec = importlib.util.spec_from_file_location("storage_checks", ROOT / "services" / service / "tests" / test_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_async_engine(URL.create("postgresql+asyncpg", username=role, password=password,
        host="127.0.0.1", port=port, database=DATABASE), pool_size=4, max_overflow=0,
        connect_args={"timeout": 10, "server_settings": {"statement_timeout": "12000"}})
    try:
        await module.run_checks(engine, record, only=SELECTED)
        executed = {r["name"] for r in OBSERVATIONS if r["name"].startswith("test_")}
        if not executed or (SELECTED and executed != set(SELECTED)):
            record("requested_checks_not_executed", False,
                {"requested": SELECTED, "executed": sorted(executed)})
    finally:
        await engine.dispose()


def main():
    role = "socai2_store_test_" + secrets.token_hex(6)
    password = secrets.token_hex(32)
    tunnel, created = None, False
    try:
        assert sql("SELECT current_database();") == DATABASE
        # No pre-existing roles or databases are modified.
        sql(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' CONNECTION LIMIT 6;"
            f"GRANT CONNECT ON DATABASE {DATABASE} TO {role}; GRANT USAGE ON SCHEMA socai2 TO {role};"
            f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA socai2 TO {role};"
            f"GRANT EXECUTE ON FUNCTION socai2.auto_adopt_baseline_result(uuid,uuid) TO {role};")
        created = True
        if SUITE in {"storage", "case_http", "fusion_bridge", "case_relations", "stage_execution", "human_tasks", "baseline_prepare"}:
            sql(f"GRANT SELECT (id,tenant_id) ON public.users TO {role};")
        if SUITE == "fusion_ingest":
            sql("INSERT INTO public.connectors(id,tenant_id) VALUES ('00000000-0000-0000-0000-000000000006',"
                "'00000000-0000-0000-0000-000000000002') ON CONFLICT DO NOTHING;"
                + f"GRANT SELECT (id,tenant_id) ON public.connectors TO {role};")
        if SUITE == "c2":
            # Minimal source fixtures only in the explicitly named synthetic DB.
            # The 29-table migration and production/public tables are unchanged.
            sql("""CREATE TABLE IF NOT EXISTS public.assets (
                id uuid PRIMARY KEY, tenant_id uuid NOT NULL, asset_type text, name text, fqdn text,
                ip_addresses text[], criticality text, tags text[], owner_email text, os text, os_version text,
                first_seen timestamptz, last_seen timestamptz, updated_at timestamptz);
                CREATE TABLE IF NOT EXISTS public.threat_intel_iocs (
                id uuid PRIMARY KEY, tenant_id uuid NOT NULL, ioc_type text, value text, confidence integer,
                severity text, tags text[], source text, source_ref text, first_seen timestamptz,
                last_seen timestamptz, expires_at timestamptz, updated_at timestamptz,
                is_active boolean, false_positive boolean);"""
                + f"GRANT SELECT,INSERT ON public.assets,public.threat_intel_iocs TO {role};")
        if SUITE == "alert_basic":
            # Reuse the source fixtures already created by C2; no new tables.
            sql(f"GRANT SELECT,INSERT ON public.assets,public.threat_intel_iocs TO {role};")
        if SUITE == "page_reader":
            sql(f"GRANT SELECT ON public.users TO {role}; GRANT SELECT,INSERT ON public.assets TO {role};")
        if SUITE == "stage_execution":
            sql(f"GRANT SELECT ON public.assets,public.threat_intel_iocs TO {role};")
        if SUITE == "external_sources":
            sql("""CREATE TABLE IF NOT EXISTS public.user_risk_profiles (
                id uuid PRIMARY KEY,tenant_id uuid,external_user_ref text,risk_score double precision,risk_tier text,
                failed_auth_24h integer,off_hours_events_7d integer,peer_anomaly_score double precision,
                last_evaluated_at timestamptz,updated_at timestamptz);
                CREATE TABLE IF NOT EXISTS public.aisoc_kb_documents (
                id uuid PRIMARY KEY,tenant_id uuid,title text,doc_kind text,source_url text,
                chunk_index integer,chunk_total integer,content text,created_at timestamptz,updated_at timestamptz);"""
                + f"GRANT SELECT,INSERT,UPDATE ON public.user_risk_profiles,public.aisoc_kb_documents TO {role};"
                + f"GRANT SELECT(id,tenant_id),INSERT(id,tenant_id) ON public.connectors TO {role};")
        inspected = subprocess.run(SSH + [DEST, 'docker inspect --format="{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}" ' + CONTAINER],
                                   capture_output=True, timeout=15, check=True)
        ip = inspected.stdout.decode().split()[0]
        import ipaddress
        assert ipaddress.ip_address(ip).is_private
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        tunnel = subprocess.Popen(SSH + ["-o", "ExitOnForwardFailure=yes", "-N", "-L",
            f"127.0.0.1:{port}:{ip}:5432", DEST], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        until = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=.2):
                    break
            except OSError:
                if time.monotonic() > until or tunnel.poll() is not None:
                    raise RuntimeError("SSH tunnel did not become ready")
                time.sleep(.1)
        asyncio.run(exercise(port, role, password))
    finally:
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if created:
            sql(f"DROP OWNED BY {role}; DROP ROLE {role};")
            record("restricted_test_role_and_tunnel_removed", True)
    print(str(EVIDENCE / "receipt.json"))
    return 1 if any(not x["passed"] for x in OBSERVATIONS) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+")
    parser.add_argument("--suite", choices=["storage", "c1", "c2", "c3", "c4", "deep", "graph", "delivery", "executor", "case_http", "fusion_ingest", "fusion_bridge", "stage_results", "stage_reader", "alert_basic", "incident_diagnosis", "page_reader", "case_relations", "stage_execution", "human_tasks", "external_sources", "baseline_prepare"], default="storage")
    args = parser.parse_args()
    SELECTED = args.only
    SUITE = args.suite
    if SUITE == "c1":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-c1-20261103" / STAMP
    if SUITE == "c2":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-c2-20261103" / STAMP
    if SUITE == "c3":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-c3-20261103" / STAMP
    if SUITE == "c4":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-c4-20261103" / STAMP
    if SUITE == "deep":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-deep-20261103" / STAMP
    if SUITE == "graph":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-graph-20261103" / STAMP
    if SUITE == "delivery":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-delivery-20261103" / STAMP
    if SUITE == "executor":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-executor-20261103" / STAMP
    if SUITE == "case_http":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-case-http-20261104" / STAMP
    if SUITE in {"fusion_ingest", "fusion_bridge"}:
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-fusion-ingest-20261104" / STAMP
    if SUITE == "stage_results":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-stage-results-20261104" / STAMP
    if SUITE == "stage_reader":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-stage-reader-20261104" / STAMP
    if SUITE == "alert_basic":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-alert-basic-20261104" / STAMP
    if SUITE == "incident_diagnosis":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-incident-diagnosis-20261104" / STAMP
    if SUITE == "page_reader":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-page-reader-20261104" / STAMP
    if SUITE == "case_relations":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-case-relations-20261104" / STAMP
    if SUITE == "stage_execution":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-stage-execution-20261104" / STAMP
    if SUITE == "human_tasks":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-human-tasks-20261104" / STAMP
    if SUITE == "external_sources":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-external-sources-20261104" / STAMP
    if SUITE == "baseline_prepare":
        EVIDENCE = ROOT / "docs/operations/evidence/socai2-baseline-prepare-20261104" / STAMP
    raise SystemExit(main())
