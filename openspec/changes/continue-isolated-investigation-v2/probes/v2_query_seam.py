"""Opt-in current v2 HTTP/PG/CH seam. No replay, models or data ingestion.

Run with the Agents environment. --config is PRIVATE JSON with writer_dsn,
reader_dsn, ssl_ca, api_url, service_token. The API must already be running in
its own process. Outputs go to a fresh directory; credentials never do.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
import hashlib
import json
import re
from pathlib import Path
import ssl
import sys
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/agents"))

from app.investigation_v2.business_profile import BusinessProfileRequest, CheckedBusinessTarget
from app.investigation_v2.evidence_view import CommittedMaterial, build_evidence_view
from app.investigation_v2.execution_models import make_analysis_messages
from app.investigation_v2.execution_state import BudgetLimits, OpeningUsage
from app.investigation_v2.execution_store import ExecutionStore, canonical_json, content_hash
from app.investigation_v2.execution_tools import DurableActivityRecords
from app.investigation_v2.request_budget import checked_model_input
from app.investigation_v2.scope import CheckedAlert, CheckedMemberSnapshot, SourceField, TenantPrincipal, UTCWindow, initialize_scope

BATCH = "investigation-v2-query-20261024-01"
SCENARIO = ROOT / "docs/investigation/scenarios/network-observation.v1.json"
RUN = uuid5(NAMESPACE_URL, "socai2:" + BATCH + ":run")


def run_identity(batch: str) -> UUID:
    assert isinstance(batch, str) and re.fullmatch(r"investigation-v2-query-20261024-\d{2}", batch), "controlled_batch_required"
    return uuid5(NAMESPACE_URL, "socai2:" + batch + ":run")


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def build_context(alert: dict, business: dict, *, checked_ref: str, run_id: UUID = RUN):
    """Only current checked Alert values and approved business input enter scope.

    Evaluation answers are not an argument to this function.
    """
    tenant, alert_id = UUID(business["tenant_id"]), UUID(business["canonical_alert_id"])
    assert (alert["tenant_id"], alert["id"]) == (tenant, alert_id), "checked_alert_identity_mismatch"
    raw = decoded(alert["raw_event"])
    assert raw.get("synthetic") is True, "controlled_synthetic_alert_required"
    network = raw["telemetry"][0]
    source_ids = tuple(UUID(str(value)) for value in decoded(alert["source_event_ids"]))
    assert UUID(str(network["tenant_id"])) == tenant and UUID(str(network["event_id"])) in source_ids, "telemetry_identity_not_bound"
    values = {"hostname": network["hostname"], "source_ip": network["source_ip"], "dest_ip": network["dest_ip"],
              "dst_port": network["dst_port"], "protocol": network["protocol"]}
    expected_parameters = business["query_parameters"]
    assert all(type(value) is type(expected_parameters[key]) and value == expected_parameters[key]
               for key, value in values.items()), "current_alert_fields_changed"
    record_ref = "checked_projection:pg.alerts:" + str(alert_id) + ":telemetry0"
    fields = tuple(SourceField(key, record_ref, business["argument_paths"][key], value) for key, value in values.items())
    fields += (SourceField("source_event_ids", record_ref, "source_event_ids", tuple(str(value) for value in source_ids)),)
    member = CheckedAlert(tenant, alert_id, record_ref, checked_ref, **values, source_event_ids=source_ids,
                          fields=fields, data_only_text="A checked synthetic source observation; verify only source records.")
    window = UTCWindow(datetime.fromisoformat(expected_parameters["start"]), datetime.fromisoformat(expected_parameters["end"]))
    context = initialize_scope(principal=TenantPrincipal(frozenset({tenant}), "controlled-v2-query-caller", True),
                               tenant_id=tenant, run_id=run_id, snapshot=CheckedMemberSnapshot(checked_ref, 1, (member,)), window=window)
    target = CheckedBusinessTarget(tenant, "alert", alert_id, record_ref, checked_ref, checked_ref, (alert_id,))
    profile = BusinessProfileRequest(context, target, business["profile"], "manual", business["objective"], business["policy_ref"])
    arguments = {**values, "start": window.start.isoformat(), "end": window.end.isoformat(), "limit": expected_parameters["limit"]}
    return context, profile, arguments


async def run_probe(config: dict, out: Path) -> dict:
    import asyncpg
    import httpx
    parsed = urlsplit(config["api_url"])
    assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port, "loopback_api_required"
    assert not parsed.username and not parsed.query and not parsed.fragment, "invalid_probe_api_url"
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    business = scenario["business_input"]
    batch = config.get("batch", BATCH)
    run_id = run_identity(batch)
    tenant, alert_id = UUID(business["tenant_id"]), UUID(business["canonical_alert_id"])
    tls = ssl.create_default_context(cafile=config["ssl_ca"])
    reader = await asyncpg.connect(config["reader_dsn"], ssl=tls, timeout=10, command_timeout=10)
    pool = None
    progress = {"batch": batch, "run_id": str(run_id), "status": "preflight", "model_calls": 0}
    def save_progress():
        (out / "progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
    save_progress()
    try:
        async with reader.transaction(readonly=True):
            await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            assert await reader.fetchval("SHOW default_transaction_read_only") == "on", "reader_not_default_readonly"
            assert not await reader.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_runs WHERE id=$1 AND tenant_id=$2)", run_id, tenant), "fresh_run_required_no_replay"
            alert = await reader.fetchrow("SELECT id,tenant_id,source_event_ids,raw_event FROM alerts WHERE id=$1 AND tenant_id=$2", alert_id, tenant)
            assert alert is not None, "current_canonical_alert_missing"
        context, profile, arguments = build_context(dict(alert), business, checked_ref=batch + ":live-pg-alert-read", run_id=run_id)
        source_projection = {"record_ref": context.member_snapshot.selected[0].record_ref, "source_record_ref": "pg.alerts:" + str(alert_id),
                             "pg_paths": business["source_projection"]["pg_paths"], "argument_paths": business["argument_paths"],
                             "raw_event_sha256": content_hash(canonical_json(decoded(alert["raw_event"]))),
                             "tenant_and_source_event_ids_checked": True}
        negatives = []
        endpoint = config["api_url"] + "/api/v2/investigation/query"
        headers = {"Authorization": "Bearer " + config["service_token"], "X-AiSOC-Tenant-ID": str(tenant)}
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            for label, candidate_headers, status in (
                ("missing_bearer", {}, 401),
                ("missing_tenant", {"Authorization": headers["Authorization"]}, 403),
                ("invalid_tenant", {**headers, "X-AiSOC-Tenant-ID": "not-a-uuid"}, 400),
                ("unknown_tenant", {**headers, "X-AiSOC-Tenant-ID": "11111111-1111-4111-8111-111111111111"}, 403)):
                response = await client.post(endpoint, headers=candidate_headers, json={"tool": "activity_records", "args": arguments})
                negatives.append({"case": label, "status": response.status_code})
                assert response.status_code == status, "authentication_negative_failed"
        pool = await asyncpg.create_pool(config["writer_dsn"], ssl=tls, min_size=1, max_size=1, timeout=10, command_timeout=10)
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
                assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_runs WHERE id=$1 AND tenant_id=$2)", run_id, tenant), "fresh_run_required_no_replay"
                await conn.execute("INSERT INTO investigation_runs (id,tenant_id,case_id,alert_summary,raw_alert,status,total_tokens,total_cost_usd) VALUES ($1,$2,$3,$4,$5::jsonb,'running',0,0)",
                                   run_id, tenant, batch + ":synthetic-ledger-label-not-a-Case", "Independent v2 query seam; zero model calls",
                                   canonical_json({"synthetic": True, "batch": batch, "alert_id": str(alert_id), "profile": "alert_recon"}))
                now = await conn.fetchval("SELECT clock_timestamp()")
                baseline = dict(await conn.fetchrow("SELECT status,completed_at,total_tokens,total_cost_usd FROM investigation_runs WHERE id=$1 AND tenant_id=$2", run_id, tenant))
        progress.update(status="new_run_created", authentication_checks=negatives)
        save_progress()
        store = ExecutionStore(pool, tenant_id=tenant, run_id=run_id, executor_id=uuid5(NAMESPACE_URL, batch + ":owner"))
        begun = await store.begin(scope=context,
                                  limits=BudgetLimits(0, 1, 0, 0, 1, now + timedelta(seconds=120), batch + ":tool-only", "model cap=0; explicit tool cap=1; no production default change"),
                                  opening=OpeningUsage(0, 0, 0, 0, 0, batch + ":synthetic-no-triage"),
                                  input_data={"purpose": "one independent v2 query; not final investigation", "business_profile": profile.descriptor,
                                              "source_projection": source_projection, "scenario_business_input_sha256": content_hash(canonical_json(business))})
        progress.update(status="begun", begin=begun["receipt"])
        save_progress()
        tool = DurableActivityRecords(store, context, "Q1", alert_id, api_url=config["api_url"], service_token=config["service_token"])
        result = await tool.execute(step_id=uuid5(NAMESPACE_URL, batch + ":step"), attempt_id=uuid5(NAMESPACE_URL, batch + ":attempt"),
                                    subtask_id="source-observation-Q1", parameters=arguments)
        progress.update(status="tool_returned", execution_status=result["execution_status"], observed_outcome=result.get("observed_outcome"), retention=result["retention"],
                        reservation=result["reservation"], completion=result["completion"])
        save_progress()
        assert result["execution_status"] == "responded" and result["retention"] == "committed", "tool_or_retention_failed_no_replay"
        output = result["tool_result"]
        (out / "tool-output.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        expected = scenario["evaluation_only"]  # Evaluator only; never passed to scope, query or model.
        assert output["status"] == "ok" and output["caller_receipt"]["http_status"] == 200, "new_query_not_ok"
        assert [row["event_id"] for row in output["rows"]] == expected["expected_event_ids"], "matching_or_excluded_events_failed"
        row = output["rows"][0]
        assert row["raw_payload"]["sha256"] == expected["matching_raw_sha256"] and row["ocsf_json"]["sha256"] == expected["matching_ocsf_sha256"], "source_hash_changed"
        assert (row["action"], row["outcome"]) == (expected["action"], expected["outcome"]), "source_semantics_changed"
        assert UUID(row["event_id"]) in context.member_snapshot.selected[0].source_event_ids, "exact_declared_source_link_missing"
        async with reader.transaction(readonly=True):
            await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            events = await reader.fetch("SELECT id,seq,kind,payload FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq", run_id, tenant)
            artifacts = await reader.fetch("SELECT id,event_id,kind,content,sha256,size_bytes FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2", run_id, tenant)
            current = dict(await reader.fetchrow("SELECT status,completed_at,total_tokens,total_cost_usd FROM investigation_runs WHERE id=$1 AND tenant_id=$2", run_id, tenant))
        assert [item["seq"] for item in events] == [1, 2, 3] and len(artifacts) == 6, "ledger_count_or_sequence_mismatch"
        assert current == baseline, "legacy_run_columns_changed"
        by_id = {str(item["id"]): item for item in artifacts}
        event_ids = {item["id"] for item in events}
        for artifact in artifacts:
            body = artifact["content"].encode("utf-8")
            assert artifact["event_id"] in event_ids and len(body) == artifact["size_bytes"] and hashlib.sha256(body).hexdigest() == artifact["sha256"], "artifact_integrity_or_link_failed"
        for event in events:
            payload = decoded(event["payload"])
            snapshot = by_id[payload["state_artifact_id"]]
            assert snapshot["event_id"] == event["id"] and snapshot["sha256"] == payload["state_hash"], "snapshot_event_link_failed"
        initial = decoded(by_id[begun["receipt"]["body_artifact_id"]]["content"])
        assert initial["input"]["business_profile"] == profile.descriptor, "profile_binding_not_retained"
        assert initial["input"]["source_projection"] == source_projection, "source_projection_not_retained"
        stored = by_id[result["completion"]["body_artifact_id"]]
        assert decoded(stored["content"]) == output, "retained_output_mismatch"
        state = decoded(by_id[result["completion"]["state_artifact_id"]]["content"])
        usage = state["stage_usage"]
        assert (usage["model_calls"], usage["tool_calls"], usage["unknown_attempts"], usage["unsettled_attempts"]) == (0, 1, 0, 0), "unexpected_execution_usage"
        evidence = build_evidence_view(context, output, CommittedMaterial(tenant, run_id, UUID(result["completion"]["body_artifact_id"]), content_hash(canonical_json(output)), stored_sha256=stored["sha256"]), 1)
        prepared = checked_model_input(make_analysis_messages(evidence, "focused_analysis"))
        report = {"schema": "investigation_v2_query_seam.v1", "status": "passed_limited_seam", "batch": batch,
                  "tenant_id": str(tenant), "run_id": str(run_id), "canonical_alert_id": str(alert_id), "profile": "alert_recon",
                  "new_query_path": "/api/v2/investigation/query", "authentication_checks": negatives,
                  "actual_http_requests": 5, "authenticated_activity_queries": 1, "model_calls": 0,
                  "events": len(events), "artifacts": len(artifacts), "begin": begun["receipt"], "completion": result["completion"],
                  "matching_event_ids": [row["event_id"]], "excluded_event_ids": [item["event_id"] for item in expected["excluded_events"]],
                  "query_receipt": output["query_receipt"], "stage_usage": usage,
                  "independent_hash_bytes_links_verified": True, "profile_input_verified": True, "source_projection": source_projection, "legacy_run_columns_unchanged": True,
                  "analysis_preparation": {"snapshot_ref": evidence.snapshot_ref, "input_bytes": prepared.input_bytes, "model_called": False},
                  "not_final_investigation": True, "legacy_case_id_is_only_a_synthetic_ledger_label": True}
        progress.update(status="passed_limited_seam")
        save_progress()
        (out / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        await reader.close(timeout=5)
        if pool is not None:
            try:
                await asyncio.wait_for(pool.close(), timeout=5)
            except TimeoutError:
                pool.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    try:
        report = asyncio.run(run_probe(config, args.out))
        print(json.dumps({"status": report["status"], "run_id": report["run_id"], "model_calls": 0, "activity_queries": 1, "events": report["events"], "artifacts": report["artifacts"]}))
    except Exception as exc:
        failure = {"status": "failed_preserve_attempt_no_replay", "run_id": str(run_identity(config.get("batch", BATCH))), "error_type": type(exc).__name__}
        if isinstance(exc, AssertionError):
            failure["check"] = str(exc)
        (args.out / "failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure))
        raise SystemExit(1)
