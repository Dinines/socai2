"""Opt-in M7c PG-only publication of the already verified M6.2c handoff.

publish requires the original unpublished 5/10 baseline. read is a separate
process phase with no publish call. No new Run, HTTP, lake query or model call.
"""
from __future__ import annotations

import argparse
import asyncio
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
from app.investigation_v2.execution_store import canonical_json, content_hash
from app.investigation_v2.recon_publication_store import (ReconPublicationStore, PUBLICATION_EVENT,
    MANIFEST_KIND, EXECUTION_KIND, REPORT_KIND, POINTER_SCHEMA)

_spec = importlib.util.spec_from_file_location("m6_baseline_verifier", Path(__file__).with_name("fixed_recon_runtime_seam.py"))
_m6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m6)
SOURCE_BATCH = "investigation-fixed-runtime-20261024-01"
RUN = _m6.run_identity(SOURCE_BATCH)
OWNER = uuid5(NAMESPACE_URL, "socai2:" + SOURCE_BATCH + ":owner")
BATCH = "investigation-publication-seam-20261024-01"


def validate_config(config: dict) -> str:
    batch = config["batch"]
    assert isinstance(batch, str) and re.fullmatch(r"investigation-publication-seam-20261024-\d{2}", batch), "controlled_publication_batch_required"
    for key, suffix in (("writer_dsn", "w"), ("reader_dsn", "r")):
        dsn = urlsplit(config[key])
        assert (dsn.scheme, dsn.hostname, dsn.port, dsn.path) == ("postgresql", "192.168.1.21", 5432, "/aisoc"), "controlled_database_required"
        assert dsn.username == "socai2_inv_m7_20261024_" + batch[-2:] + "_" + suffix and dsn.password, "fresh_publication_role_required"
        assert not dsn.query and not dsn.fragment, "plain_private_dsn_required"
    assert not any(key in config for key in ("run_id", "owner", "tenant_id", "source_batch", "api_url")), "fixed_source_identity_required"
    return batch


def baseline_hash(events, artifacts) -> str:
    first = list(events[:5])
    identities = {e["id"] for e in first}
    selected = sorted((a for a in artifacts if a["event_id"] in identities), key=lambda a: str(a["id"]))
    return content_hash(canonical_json({"events": [dict(e) for e in first], "artifacts": [dict(a) for a in selected]}))


def verify_publication_ledger(events, artifacts, *, tenant: UUID, run_id: UUID, owner: UUID, expected_result=None) -> dict:
    """Independent raw-row verification including the immutable M6 baseline."""
    assert len(events) in {5, 6}, "unexpected_event_count"
    first_ids = {e["id"] for e in events[:5]}
    _m6.verify_ledger(events[:5], [a for a in artifacts if a["event_id"] in first_ids], tenant=tenant, run_id=run_id, owner=owner)
    if len(events) == 5:
        assert len(artifacts) == 10 and expected_result is None, "unpublished_baseline_required"
        return {"events": 5, "artifacts": 10, "publication_state": "not_published"}
    assert expected_result is not None and len(artifacts) == 14, "published_result_and_fourteen_artifacts_required"
    event = events[-1]
    assert event["seq"] == 6 and event["kind"] == PUBLICATION_EVENT and event["tenant_id"] == tenant and event["run_id"] == run_id, "publication_event_identity_mismatch"
    assert event["agent"] == _m6.RUNTIME_VERSION and event["input_hash"] is None and event["output_hash"] is None, "publication_event_executor_or_io_hash_mismatch"
    by_id = {str(a["id"]): a for a in artifacts}
    assert len(by_id) == 14, "duplicate_artifact_identity"
    owned = [a for a in artifacts if a["event_id"] == event["id"]]
    assert len(owned) == 4 and {a["kind"] for a in owned} == {MANIFEST_KIND, EXECUTION_KIND, REPORT_KIND, "unified_state_snapshot"}, "publication_artifact_kinds_mismatch"
    for artifact in owned:
        assert (artifact["tenant_id"], artifact["run_id"]) == (tenant, run_id), "publication_artifact_owner_mismatch"
        assert len(artifact["content"].encode("utf-8")) == artifact["size_bytes"] and content_hash(artifact["content"]) == artifact["sha256"], "publication_artifact_bytes_hash_mismatch"
    payload = _m6.decoded(event["payload"])
    manifest_row, state_row = by_id[payload["body_artifact_id"]], by_id[payload["state_artifact_id"]]
    assert manifest_row["event_id"] == state_row["event_id"] == event["id"] and manifest_row["kind"] == MANIFEST_KIND and state_row["kind"] == "unified_state_snapshot", "publication_event_edges_mismatch"
    assert manifest_row["sha256"] == payload["body_hash"] and state_row["sha256"] == payload["state_hash"], "publication_event_hash_mismatch"
    state, manifest = _m6.decoded(state_row["content"]), _m6.decoded(manifest_row["content"])
    stopped = _m6.decoded(by_id[_m6.decoded(events[4]["payload"])["state_artifact_id"]]["content"])
    assert {k: v for k, v in state.items() if k not in {"publication", "persistence", "updated_at"}} == {k: v for k, v in stopped.items() if k not in {"persistence", "updated_at"}}, "publication_state_changed_frozen_runtime_scope_or_usage"
    assert state["persistence"] == {k: v for k, v in payload.items() if k != "state_hash"}, "publication_state_receipt_mismatch"
    assert (payload["event_id"], payload["seq"], payload["tenant_id"], payload["run_id"], payload["stage_id"], payload["attempt_id"]) == (str(event["id"]), 6, str(tenant), str(run_id), state["stage_id"], None), "publication_receipt_identity_mismatch"
    assert state["executor_id"] == str(owner) and state["publication"]["manifest_artifact"] == {"artifact_id": str(manifest_row["id"]), "sha256": manifest_row["sha256"]}, "publication_pointer_owner_mismatch"
    assert state["publication"]["schema"] == POINTER_SCHEMA and set(state["publication"]) == {"schema", "manifest_artifact", "manifest_ref"}, "publication_pointer_schema_mismatch"
    assert manifest["manifest_ref"] == "recon-manifest:" + content_hash(canonical_json({k: v for k, v in manifest.items() if k != "manifest_ref"})) == state["publication"]["manifest_ref"], "manifest_reference_mismatch"
    assert manifest == expected_result["manifest"] and expected_result["manifest_artifact"] == state["publication"]["manifest_artifact"], "raw_pg_and_store_manifest_differ"
    report, execution = by_id[manifest["report"]["artifact_id"]], by_id[manifest["snapshots"]["execution"]["artifact_id"]]
    assert report["kind"] == REPORT_KIND and execution["kind"] == EXECUTION_KIND and report["event_id"] == execution["event_id"] == event["id"], "publication_report_execution_edges_mismatch"
    assert report["sha256"] == manifest["report"]["sha256"] and execution["sha256"] == manifest["snapshots"]["execution"]["sha256"], "publication_report_execution_hash_mismatch"
    assert report["content"] == expected_result["markdown"] and _m6.decoded(execution["content"]) == expected_result["execution_snapshot"], "raw_pg_and_store_result_differ"
    for key in ("questions", "analysis", "evidence"):
        ref = manifest["snapshots"][key]
        assert ref is not None, "normal_live_scene_requires_evidence"
        handoff = by_id[ref["artifact_id"]]
        assert handoff["sha256"] == ref["sha256"], "section_artifact_hash_mismatch"
        value = _m6.decoded(handoff["content"])
        for part in ref["section"].strip("/").split("/"): value = value[part]
        assert content_hash(canonical_json(value)) == ref["section_sha256"], "section_hash_mismatch"
    return {"events": 6, "artifacts": 14, "publication_state": "published", "stage_usage": state["stage_usage"], "report_sha256": report["sha256"], "report_bytes": report["size_bytes"]}


async def read_rows(reader, tenant, run_id):
    async with reader.transaction(readonly=True):
        await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
        assert await reader.fetchval("SHOW default_transaction_read_only") == "on", "independent_reader_not_readonly"
        events = await reader.fetch("SELECT id,tenant_id,run_id,seq,kind,agent,payload,input_hash,output_hash FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq", run_id, tenant)
        artifacts = await reader.fetch("SELECT id,tenant_id,run_id,event_id,kind,content,sha256,size_bytes FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2", run_id, tenant)
        run = await reader.fetchrow("SELECT status,completed_at,total_tokens,total_cost_usd FROM investigation_runs WHERE id=$1 AND tenant_id=$2", run_id, tenant)
    assert run is not None, "verified_source_run_missing"
    return events, artifacts, dict(run)


async def resolve_phase(store_factory, request, *, phase: str, expected_handoff_ref: str):
    """The read phase can only read; no retry after an uncertain publish."""
    assert phase in {"publish", "read"}, "explicit_phase_required"
    first = await store_factory().read_result(request)
    descriptor = False
    if phase == "publish":
        assert first["publication_state"] == "not_published" and first["markdown"] is None and first["manifest"] is None, "source_already_published_do_not_replay"
        assert first["candidate"]["handoff_ref"] == expected_handoff_ref, "source_handoff_changed"
        saved = await store_factory().publish(request)
        assert saved["notification"]["delivery_status"] == "not_attempted", "descriptor_is_not_delivery"
        descriptor = True
        repeated = await store_factory().publish(request)
        assert repeated["repeated"] is True and repeated["notification"] is None and repeated["manifest"] == saved["manifest"], "repeat_changed_publication"
    else:
        saved = first
    current = await store_factory().read_result(request)
    for key in ("manifest", "manifest_artifact", "execution_snapshot", "markdown"):
        assert current[key] == saved[key], "same_process_read_changed_version"
    return current, descriptor


async def run_probe(config: dict, out: Path, *, phase: str) -> dict:
    import asyncpg
    assert phase in {"publish", "read"}, "explicit_phase_required"
    batch = validate_config(config)
    card = json.loads(_m6.SCENARIO.read_text(encoding="utf-8"))
    business = card["business_input"]
    tenant, alert_id = UUID(business["tenant_id"]), UUID(business["canonical_alert_id"])
    prior = json.loads((ROOT / "docs/operations/investigation-fixed-runtime-seam-20261024.json").read_text(encoding="utf-8"))
    assert prior["status"] == "ACCEPT_limited_runtime_seam" and prior["real_seam"]["run_id"] == str(RUN), "accepted_source_receipt_required"
    progress = {"batch": batch, "phase": phase, "run_id": str(RUN), "status": "intent", "additional_queries": 0, "models": 0}
    def save(): (out / "progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
    save()
    tls = ssl.create_default_context(cafile=config["ssl_ca"])
    reader, pool = None, None
    try:
        reader = await asyncpg.connect(config["reader_dsn"], ssl=tls, timeout=10, command_timeout=10)
        before_events, before_artifacts, baseline = await read_rows(reader, tenant, RUN)
        if phase == "publish": verify_publication_ledger(before_events, before_artifacts, tenant=tenant, run_id=RUN, owner=OWNER)
        else: assert len(before_events) == 6 and len(before_artifacts) == 14, "one_publication_required_for_cold_read"
        async with reader.transaction(readonly=True):
            await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
            alert = await reader.fetchrow("SELECT id,tenant_id,source_event_ids,raw_event FROM alerts WHERE id=$1 AND tenant_id=$2", alert_id, tenant)
        context, request, _ = _m6.build_context(dict(alert), business, checked_ref=SOURCE_BATCH + ":live-pg-alert-read", run_id=RUN)
        pool = await asyncpg.create_pool(config["writer_dsn"], ssl=tls, min_size=1, max_size=1, timeout=10, command_timeout=10)
        def store(): return ReconPublicationStore(pool, tenant_id=tenant, run_id=RUN, executor_id=OWNER)
        progress.update(status="baseline_checked", publication_attempt_intent=phase == "publish");save()
        current, descriptor = await resolve_phase(store, request, phase=phase, expected_handoff_ref=prior["real_seam"]["handoff_ref"])
        events, artifacts, now_run = await read_rows(reader, tenant, RUN)
        original_baseline_hash = baseline_hash(before_events, before_artifacts)
        assert baseline_hash(events, artifacts) == original_baseline_hash, "original_m6_verified_rows_changed"
        checked = verify_publication_ledger(events, artifacts, tenant=tenant, run_id=RUN, owner=OWNER, expected_result=current)
        assert now_run == baseline and now_run["status"] == "running" and now_run["completed_at"] is None and now_run["total_tokens"] == now_run["total_cost_usd"] == 0, "legacy_run_columns_changed"
        usage = checked["stage_usage"]
        assert (usage["model_calls"], usage["tool_calls"], usage["unknown_attempts"], usage["unsettled_attempts"]) == (0, 1, 0, 0), "source_usage_changed"
        execution = current["execution_snapshot"]
        assert (execution["run_state"], execution["investigation_completeness"], execution["continuation"]) == ("finished", "complete_for_scope", "none"), "finite_publication_mapping_changed"
        report = {"schema": "fixed_recon_publication_seam.v1", "status": "passed_limited_pg_publication", "batch": batch, "phase": phase, "tenant_id": str(tenant), "run_id": str(RUN),
            "source_batch": SOURCE_BATCH, "events_before": len(before_events), "artifacts_before": len(before_artifacts), **checked,
            "manifest_ref": current["manifest"]["manifest_ref"], "manifest_artifact": current["manifest_artifact"], "execution_snapshot": execution,
            "m6_verified_baseline_sha256": original_baseline_hash,
            "publication_notification_descriptor_generated": descriptor, "notification_delivery": "not_attempted", "extra_activity_queries": 0, "models": 0,
            "independent_raw_pg_all_artifacts_verified": True, "legacy_run_columns_unchanged": True, "not_m8_or_semantic_quality_acceptance": True}
        (out / "report.md").write_bytes(current["markdown"].encode("utf-8"))
        (out / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        progress.update(status=report["status"]);save()
        return report
    finally:
        if reader is not None: await reader.close(timeout=5)
        if pool is not None:
            try: await asyncio.wait_for(pool.close(), timeout=5)
            except TimeoutError: pool.terminate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--phase", choices=("publish", "read"), required=True)
    args = parser.parse_args();args.out.mkdir(parents=True, exist_ok=False)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        report = asyncio.run(run_probe(config, args.out, phase=args.phase))
        print(json.dumps({key: report[key] for key in ("status", "phase", "run_id", "events", "artifacts", "manifest_ref")}))
    except Exception as exc:
        failure = {"status": "failed_preserve_trial_no_republish", "phase": args.phase, "error_type": type(exc).__name__}
        if isinstance(exc, AssertionError): failure["check"] = str(exc)
        (args.out / "failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure));raise SystemExit(1)
