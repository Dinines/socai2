"""Opt-in M6.2 runtime seam: fresh Run, one query, independent ledger readback.

The private config supplies fresh exact writer/reader identities and a separately
launched loopback v2 API. Never replay a failed/unknown Run. This is not M7
publication, a model evaluation, a Case entry point or a production deployment.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import ssl
import sys
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/agents"))
from app.investigation_v2.execution_state import BudgetLimits, OpeningUsage, ExecutionRejected, stage_id_for
from app.investigation_v2.execution_store import ExecutionStore, canonical_json, content_hash
from app.investigation_v2.fixed_recon import COMPLETION_POLICY_REF
from app.investigation_v2.fixed_recon_runtime import FixedReconRuntime
from app.investigation_v2.recon_runtime_state import RUNTIME_VERSION, make_recon_plan
from app.investigation_v2.recon_runtime_store import ReconExecutionStore, HANDOFF_KIND

_spec = importlib.util.spec_from_file_location("prior_v2_scope_builder", Path(__file__).with_name("v2_query_seam.py"))
_scope = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scope)
build_context, decoded = _scope.build_context, _scope.decoded
SCENARIO = ROOT / "docs/investigation/scenarios/network-observation.v1.json"
BATCH = "investigation-fixed-runtime-20261024-01"


def run_identity(batch: str) -> UUID:
    assert isinstance(batch, str) and re.fullmatch(r"investigation-fixed-runtime-20261024-\d{2}", batch), "controlled_batch_required"
    return uuid5(NAMESPACE_URL, "socai2:" + batch + ":run")


def validate_config(config: dict) -> tuple[str, UUID]:
    batch = config["batch"]
    run_id = run_identity(batch)
    api = urlsplit(config["api_url"])
    assert api.scheme == "http" and api.hostname == "127.0.0.1" and api.port, "loopback_api_required"
    assert not api.username and not api.password and not api.query and not api.fragment and api.path in {"", "/"}, "invalid_probe_api_url"
    for key, suffix in (("writer_dsn", "w"), ("reader_dsn", "r")):
        dsn = urlsplit(config[key])
        assert (dsn.scheme, dsn.hostname, dsn.port, dsn.path) == ("postgresql", "192.168.1.21", 5432, "/aisoc"), "controlled_database_required"
        assert dsn.username == "socai2_inv_m6_20261024_" + batch[-2:] + "_" + suffix and dsn.password, "fresh_exact_role_required"
        assert not dsn.query and not dsn.fragment, "plain_private_dsn_required"
    assert isinstance(config["service_token"], str) and len(config["service_token"]) >= 32, "fresh_service_token_required"
    return batch, run_id


def evaluate_source(output: dict, expected: dict, context) -> dict:
    """Evaluation only, after execution; expected answers never enter runtime."""
    assert output["status"] == "ok" and output["caller_receipt"]["http_status"] == 200, "new_query_not_ok"
    assert [row["event_id"] for row in output["rows"]] == expected["expected_event_ids"], "matching_or_excluded_events_failed"
    row = output["rows"][0]
    assert row["raw_payload"]["sha256"] == expected["matching_raw_sha256"] and row["ocsf_json"]["sha256"] == expected["matching_ocsf_sha256"], "source_hash_changed"
    assert (row["action"], row["outcome"]) == (expected["action"], expected["outcome"]), "source_semantics_changed"
    assert UUID(row["event_id"]) in context.member_snapshot.selected[0].source_event_ids, "exact_declared_source_link_missing"
    return row


def verify_ledger(events, artifacts, *, tenant: UUID, run_id: UUID, owner: UUID) -> dict:
    """Validate every body/snapshot edge, not just each artifact's own hash."""
    kinds = [("unified_recon_started", "unified_step_input"), ("unified_recon_claimed", "fixed_recon_control"),
             ("unified_attempt_reserved", "unified_step_input"), ("unified_attempt_settled", "unified_step_output"),
             ("unified_recon_handoff_saved", HANDOFF_KIND)]
    assert [e["seq"] for e in events] == [1, 2, 3, 4, 5] and len(artifacts) == 10, "ledger_count_or_sequence_mismatch"
    assert [e["kind"] for e in events] == [k[0] for k in kinds], "ledger_event_kinds_mismatch"
    by_id = {str(a["id"]): a for a in artifacts}
    event_ids = {e["id"] for e in events}
    assert len(by_id) == 10 and len(event_ids) == 5, "duplicate_ledger_identity"
    for artifact in artifacts:
        body = artifact["content"].encode("utf-8")
        assert (artifact["tenant_id"], artifact["run_id"]) == (tenant, run_id), "artifact_owner_mismatch"
        assert artifact["event_id"] in event_ids and len(body) == artifact["size_bytes"] and hashlib.sha256(body).hexdigest() == artifact["sha256"], "artifact_integrity_or_link_failed"
    referenced = set()
    frozen_plan, frozen_scope = None, None
    for event, (_, body_kind) in zip(events, kinds):
        assert (event["tenant_id"], event["run_id"], event["agent"]) == (tenant, run_id, RUNTIME_VERSION), "event_owner_version_mismatch"
        payload = decoded(event["payload"])
        snapshot, body = by_id[payload["state_artifact_id"]], by_id[payload["body_artifact_id"]]
        assert snapshot["event_id"] == body["event_id"] == event["id"], "event_body_snapshot_link_failed"
        assert snapshot["kind"] == "unified_state_snapshot" and body["kind"] == body_kind, "event_artifact_kind_mismatch"
        assert snapshot["sha256"] == payload["state_hash"] and body["sha256"] == payload["body_hash"], "event_artifact_hash_mismatch"
        state = decoded(snapshot["content"])
        assert state["persistence"] == {k: v for k, v in payload.items() if k != "state_hash"}, "snapshot_receipt_mismatch"
        assert (state["tenant_id"], state["run_id"], state["executor_id"], state["runtime_version"]) == (str(tenant), str(run_id), str(owner), RUNTIME_VERSION), "snapshot_owner_version_mismatch"
        assert (payload["event_id"], payload["seq"], payload["tenant_id"], payload["run_id"], payload["stage_id"]) == (str(event["id"]), event["seq"], str(tenant), str(run_id), state["stage_id"]), "event_receipt_identity_mismatch"
        assert payload["stage_id"] == stage_id_for(tenant, run_id), "event_stage_identity_mismatch"
        assert payload["attempt_id"] == (state["recon"]["plan"]["attempt_id"] if event["kind"] in {"unified_attempt_reserved", "unified_attempt_settled"} else None), "event_attempt_identity_mismatch"
        assert content_hash(canonical_json(state["scope"])) == state["scope_hash"], "snapshot_scope_hash_mismatch"
        if frozen_plan is None:
            frozen_plan, frozen_scope = state["recon"]["plan"], state["scope_hash"]
        assert (state["recon"]["plan"], state["scope_hash"]) == (frozen_plan, frozen_scope), "runtime_plan_scope_changed"
        assert event["input_hash"] == (body["sha256"] if body_kind == "unified_step_input" else None), "event_input_hash_mismatch"
        assert event["output_hash"] == (body["sha256"] if body_kind == "unified_step_output" else None), "event_output_hash_mismatch"
        referenced.update((payload["state_artifact_id"], payload["body_artifact_id"]))
    assert referenced == set(by_id), "unreferenced_or_reused_artifact"
    return by_id


async def run_probe(config: dict, out: Path) -> dict:
    import asyncpg

    batch, run_id = validate_config(config)
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))
    business = scenario["business_input"]
    tenant, alert_id = UUID(business["tenant_id"]), UUID(business["canonical_alert_id"])
    owner = uuid5(NAMESPACE_URL, "socai2:" + batch + ":owner")
    tls = ssl.create_default_context(cafile=config["ssl_ca"])
    progress = {"schema": "fixed_recon_seam_progress.v1", "batch": batch, "run_id": str(run_id), "status": "intent", "model_calls": 0}
    def save_progress():
        (out / "progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
    save_progress()
    reader, pool = None, None
    try:
        reader = await asyncpg.connect(config["reader_dsn"], ssl=tls, timeout=10, command_timeout=10)
        async with reader.transaction(readonly=True):
            await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            assert await reader.fetchval("SHOW default_transaction_read_only") == "on", "reader_not_default_readonly"
            assert not await reader.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_runs WHERE id=$1 AND tenant_id=$2)", run_id, tenant), "fresh_run_required_no_replay"
            alert = await reader.fetchrow("SELECT id,tenant_id,source_event_ids,raw_event FROM alerts WHERE id=$1 AND tenant_id=$2", alert_id, tenant)
            assert alert is not None, "current_canonical_alert_missing"
        context, profile, _ = build_context(dict(alert), business, checked_ref=batch + ":live-pg-alert-read", run_id=run_id)
        plan = make_recon_plan(profile)
        pool = await asyncpg.create_pool(config["writer_dsn"], ssl=tls, min_size=1, max_size=1, timeout=10, command_timeout=10)
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
                assert not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_runs WHERE id=$1 AND tenant_id=$2)", run_id, tenant), "fresh_run_required_no_replay"
                await conn.execute("INSERT INTO investigation_runs (id,tenant_id,case_id,alert_summary,raw_alert,status,total_tokens,total_cost_usd) VALUES ($1,$2,$3,$4,$5::jsonb,'running',0,0)",
                    run_id, tenant, batch + ":synthetic-ledger-label-not-a-Case", "M6.2 fixed runtime seam; zero model calls",
                    canonical_json({"synthetic": True, "batch": batch, "alert_id": str(alert_id), "profile": "alert_recon"}))
                now = await conn.fetchval("SELECT clock_timestamp()")
                baseline = dict(await conn.fetchrow("SELECT status,completed_at,total_tokens,total_cost_usd FROM investigation_runs WHERE id=$1 AND tenant_id=$2", run_id, tenant))
        progress.update(status="new_run_created"); save_progress()
        def store():
            return ReconExecutionStore(pool, tenant_id=tenant, run_id=run_id, executor_id=owner)
        def runtime():
            return FixedReconRuntime(store(), profile, api_url=config["api_url"].rstrip("/"), service_token=config["service_token"])
        current_runtime = runtime()
        begun = await current_runtime.begin(limits=BudgetLimits(0, 1, 0, 0, 1, now + timedelta(seconds=120), batch + ":tool-only", "model0/tool1/tokens0/cost0/unsettled1; no production defaults changed"),
            opening=OpeningUsage(0, 0, 0, 0, 0, batch + ":synthetic-no-triage"), parent_deadline=now + timedelta(seconds=120))
        progress.update(status="begun", begin=begun["receipt"]); save_progress()
        first = await current_runtime.execute()
        progress.update(status=first["status"], http_attempted=first["http_attempted_by_this_invocation"]); save_progress()
        assert first["status"] == "stopped" and first["http_attempted_by_this_invocation"] is True and first["handoff"]["retention"] == "committed", "runtime_not_committed_no_replay"
        candidate = first["handoff"]["candidate"]
        analysis = candidate["result"]
        assert (analysis["scope_readiness"], analysis["nature"], analysis["authorization"]) == ("ready", "unresolved", "unknown"), "finite_result_mismatch"
        statuses = {item["question"]: item["status"] for item in analysis["questions"]}
        assert statuses == {"Q1": "supported", "Q2": "supported", "Q3a": "unassessed", "Q3b": "unassessed", "Q4": "unassessed", "Q5": "supported"}, "finite_question_boundary_changed"
        repeat = await runtime().execute()
        cold = await store().read_handoff(profile)
        assert repeat["status"] == "stopped" and repeat["http_attempted_by_this_invocation"] is False, "repeat_dispatched"
        assert candidate == repeat["handoff"]["candidate"] == cold["candidate"], "cold_handoff_changed"
        try:
            await ExecutionStore(pool, tenant_id=tenant, run_id=run_id, executor_id=owner).load()
        except ExecutionRejected:
            generic_rejected = True
        else:
            raise AssertionError("generic_store_accepted_managed_runtime")
        async with reader.transaction(readonly=True):
            await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            events = await reader.fetch("SELECT id,tenant_id,run_id,seq,kind,agent,payload,input_hash,output_hash FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq", run_id, tenant)
            artifacts = await reader.fetch("SELECT id,tenant_id,run_id,event_id,kind,content,sha256,size_bytes FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2", run_id, tenant)
            saved_run = dict(await reader.fetchrow("SELECT status,completed_at,total_tokens,total_cost_usd FROM investigation_runs WHERE id=$1 AND tenant_id=$2", run_id, tenant))
        assert saved_run == baseline, "legacy_run_columns_changed"
        by_id = verify_ledger(events, artifacts, tenant=tenant, run_id=run_id, owner=owner)
        initial = decoded(by_id[begun["receipt"]["body_artifact_id"]]["content"])
        assert initial["input"] == {"business_profile": profile.descriptor, "runtime_plan": plan}, "frozen_profile_plan_changed"
        assert candidate["runtime_version"] == RUNTIME_VERSION and candidate["completion_policy_ref"] == COMPLETION_POLICY_REF and candidate["runtime_plan_ref"] == plan["plan_ref"], "runtime_version_changed"
        state = decoded(by_id[decoded(events[-1]["payload"])["state_artifact_id"]]["content"])
        usage = state["stage_usage"]
        assert (usage["model_calls"], usage["tool_calls"], usage["unknown_attempts"], usage["unsettled_attempts"]) == (0, 1, 0, 0), "unexpected_execution_usage"
        attempt = state["attempts"][plan["attempt_id"]]
        output = decoded(by_id[attempt["completion_receipt"]["body_artifact_id"]]["content"])
        row = evaluate_source(output, scenario["evaluation_only"], context)
        handoffs = [a for a in artifacts if a["kind"] == HANDOFF_KIND]
        assert len(handoffs) == 1 and decoded(handoffs[0]["content"]) == candidate, "owned_handoff_mismatch"
        assert state["recon"]["phase"] == "stopped" and state["recon"]["handoff"]["artifact_id"] == str(handoffs[0]["id"]), "state_handoff_link_failed"
        report = {"schema": "fixed_recon_runtime_seam.v1", "status": "passed_limited_runtime_seam", "batch": batch, "tenant_id": str(tenant), "run_id": str(run_id), "canonical_alert_id": str(alert_id),
            "runtime_version": RUNTIME_VERSION, "completion_policy_ref": COMPLETION_POLICY_REF, "runtime_plan_ref": plan["plan_ref"], "handoff_ref": candidate["handoff_ref"], "result_ref": analysis["result_ref"],
            "model_calls": 0, "authenticated_activity_queries": 1, "events": len(events), "artifacts": len(artifacts), "query_receipt": output["query_receipt"], "stage_usage": usage,
            "matching_event_ids": [row["event_id"]], "excluded_event_ids": [e["event_id"] for e in scenario["evaluation_only"]["excluded_events"]],
            "scope_readiness": analysis["scope_readiness"], "nature": analysis["nature"], "authorization": analysis["authorization"], "question_statuses": statuses,
            "independent_hash_bytes_links_verified": True, "frozen_profile_plan_verified": True, "repeat_and_cold_read_same_handoff": True, "generic_store_rejected": generic_rejected, "legacy_run_columns_unchanged": True,
            "not_m7_publication_or_quality_acceptance": True, "synthetic_ledger_label_is_not_a_Case": True}
        (out / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        progress.update(status=report["status"]); save_progress()
        return report
    finally:
        if reader is not None:
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
        print(json.dumps({key: report[key] for key in ("status", "run_id", "model_calls", "authenticated_activity_queries", "events", "artifacts")}))
    except Exception as exc:
        failure = {"status": "failed_preserve_attempt_no_replay", "error_type": type(exc).__name__}
        if isinstance(exc, AssertionError):
            failure["check"] = str(exc)
        (args.out / "failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure))
        raise SystemExit(1)
