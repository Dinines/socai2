"""Opt-in two-process v2 result GET; original Run and ledger remain unchanged."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import re
import ssl
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

_spec = importlib.util.spec_from_file_location("publication_baseline", Path(__file__).with_name("fixed_recon_publication_seam.py"))
_m7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m7)
ROOT, RUN = _m7.ROOT, _m7.RUN
BATCH = "investigation-result-http-20261025-01"


def validate_config(config: dict) -> str:
    batch = config["batch"]
    assert isinstance(batch, str) and re.fullmatch(r"investigation-result-http-20261025-\d{2}", batch), "controlled_http_read_batch_required"
    ports = []
    for key in ("api_url", "internal_url"):
        parsed = urlsplit(config[key])
        assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port, "loopback_read_apps_required"
        assert not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and parsed.path in {"", "/"}, "plain_loopback_read_url_required"
        ports.append(parsed.port)
    assert ports[0] != ports[1], "two_distinct_process_ports_required"
    for key, suffix in (("ledger_dsn", "w"), ("auth_dsn", "r")):
        parsed = urlsplit(config[key])
        assert (parsed.scheme, parsed.hostname, parsed.port, parsed.path) == ("postgresql", "192.168.1.21", 5432, "/aisoc"), "controlled_read_database_required"
        assert parsed.username == "socai2_inv_m8r_20261025_" + batch[-2:] + "_" + suffix and parsed.password and not parsed.query and not parsed.fragment, "fresh_exact_read_roles_required"
    for key in ("api_service_token", "internal_read_token"):
        token = config[key]
        assert isinstance(token, str) and 32 <= len(token.encode("ascii")) <= 256 and not any(c.isspace() for c in token), "strong_new_read_tokens_required"
    assert config["api_service_token"] != config["internal_read_token"], "separate_external_internal_credentials_required"
    assert not any(k in config for k in ("tenant_id", "run_id", "owner", "scope", "source_batch")), "fixed_approved_result_required"
    return batch


def snapshot_hash(rows) -> str:
    events, artifacts, run = rows
    return _m7.content_hash(_m7.canonical_json({"events": [dict(e) for e in events],
        "artifacts": [dict(a) for a in sorted(artifacts, key=lambda item: str(item["id"]))], "run": dict(run)}))


def raw_published_result(rows, tenant: UUID) -> dict:
    """Build a comparison value from retained rows, then verify every edge below."""
    by_id = {str(a["id"]): a for a in rows[1]}
    event = rows[0][-1]
    manifest_row = by_id[_m7._m6.decoded(event["payload"])["body_artifact_id"]]
    manifest = _m7._m6.decoded(manifest_row["content"])
    return dict(schema="owned_fixed_recon_result.v1", tenant_id=str(tenant), run_id=str(RUN), profile="alert_recon", notification=None,
        publication_state=manifest["publication_state"], target={key: manifest["target"][key] for key in ("type", "id")}, objective=manifest["objective"],
        retention=manifest["retention"]["publication_artifacts"], legacy_run_status=rows[2]["status"],
        manifest=manifest, manifest_artifact={"artifact_id": str(manifest_row["id"]), "sha256": manifest_row["sha256"]},
        markdown=by_id[manifest["report"]["artifact_id"]]["content"],
        execution_snapshot=_m7._m6.decoded(by_id[manifest["snapshots"]["execution"]["artifact_id"]]["content"]))


def verify_stable_read(payload: dict, before, after, *, tenant: UUID, prior: dict) -> dict:
    assert snapshot_hash(before) == snapshot_hash(after), "HTTP_read_changed_verified_ledger_rows"
    assert ((payload["schema"], payload["tenant_id"], payload["run_id"], payload["profile"], payload["notification"])
        == ("owned_fixed_recon_result.v1", str(tenant), str(RUN), "alert_recon", None)), "HTTP_read_identity_or_schema_mismatch"
    checked = _m7.verify_publication_ledger(after[0], after[1], tenant=tenant, run_id=RUN, owner=_m7.OWNER, expected_result=payload)
    assert payload["manifest"]["manifest_ref"] == prior["real_publish"]["manifest_ref"] and payload["manifest_artifact"] == prior["real_publish"]["manifest_artifact"], "accepted_manifest_changed"
    assert checked["report_sha256"] == prior["real_publish"]["report_sha256"] and checked["report_bytes"] == prior["real_publish"]["report_bytes"], "accepted_report_changed"
    assert payload["execution_snapshot"] == prior["real_publish"]["execution_snapshot"], "accepted_execution_changed"
    assert _m7.baseline_hash(after[0], after[1]) == prior["real_publish"]["m6_verified_baseline_sha256"], "M6_verified_baseline_changed"
    usage = checked["stage_usage"]
    assert (usage["model_calls"], usage["tool_calls"], usage["unknown_attempts"], usage["unsettled_attempts"]) == (0, 1, 0, 0), "activity_or_model_usage_changed"
    run = after[2]
    assert run["status"] == "running" and run["completed_at"] is None and run["total_tokens"] == run["total_cost_usd"] == 0, "legacy_Run_columns_changed"
    assert _m7.canonical_json(payload) == _m7.canonical_json(raw_published_result(after, tenant)), "entire_HTTP_owned_DTO_differs_from_raw_PG_publication"
    return {**checked, "whole_verified_ledger_sha256": snapshot_hash(after), "m6_verified_baseline_sha256": _m7.baseline_hash(after[0], after[1])}


async def read_rows(reader, tenant):
    async with reader.transaction(readonly=True):
        await reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant))
        assert await reader.fetchval("SHOW transaction_read_only") == "on", "observer_transaction_must_be_readonly"
        events = await reader.fetch("SELECT id,tenant_id,run_id,seq,kind,agent,payload,input_hash,output_hash FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq", RUN, tenant)
        artifacts = await reader.fetch("SELECT id,tenant_id,run_id,event_id,kind,content,sha256,size_bytes FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2", RUN, tenant)
        run = await reader.fetchrow("SELECT status,completed_at,total_tokens,total_cost_usd FROM investigation_runs WHERE id=$1 AND tenant_id=$2", RUN, tenant)
    assert run is not None, "approved_Run_missing"
    return events, artifacts, dict(run)


async def run_probe(config: dict, out: Path) -> dict:
    import asyncpg
    import httpx
    batch = validate_config(config)
    card = json.loads(_m7._m6.SCENARIO.read_text(encoding="utf-8"))
    tenant = UUID(card["business_input"]["tenant_id"])
    prior = json.loads((ROOT / "docs/operations/investigation-publication-pg-seam-20261024.json").read_text(encoding="utf-8"))
    assert prior["status"] == "ACCEPT_limited_pg_publication" and prior["real_publish"]["run_id"] == str(RUN), "accepted_M7_result_required"
    assert prior["real_publish"]["report_bytes"] == 3111, "approved_M7_report_size_required"
    progress = {"batch": batch, "run_id": str(RUN), "status": "intent", "new_runs": 0, "activity_queries": 0, "models": 0}
    def save(): (out / "progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")
    save()
    reader = await asyncpg.connect(config["ledger_dsn"], ssl=ssl.create_default_context(cafile=config["ssl_ca"]), timeout=10, command_timeout=10)
    try:
        before = await read_rows(reader, tenant)
        verify_stable_read(raw_published_result(before, tenant), before, before, tenant=tenant, prior=prior)
        api = config["api_url"].rstrip("/") + "/api/v2/investigation/runs/" + str(RUN)
        internal = config["internal_url"].rstrip("/") + "/internal/investigation-v2/runs/" + str(RUN)
        api_headers = {"Authorization": "Bearer " + config["api_service_token"], "X-AiSOC-Tenant-ID": str(tenant)}
        inner_headers = {"Authorization": "Bearer " + config["internal_read_token"], "X-AiSOC-Tenant-ID": str(tenant), "X-AiSOC-Actor-ID": str(uuid5(NAMESPACE_URL, batch + ":read-probe-actor"))}
        negatives = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            for surface, name, url, headers, expected, body in (
                ("api", "missing_bearer", api, {}, 401, None),
                ("api", "bad_bearer", api, {**api_headers, "Authorization": "Bearer invalid-test-token"}, 401, None),
                ("api", "missing_tenant", api, {"Authorization": api_headers["Authorization"]}, 403, None),
                ("api", "invalid_tenant", api, {**api_headers, "X-AiSOC-Tenant-ID": "invalid"}, 400, None),
                ("api", "unknown_tenant", api, {**api_headers, "X-AiSOC-Tenant-ID": str(uuid5(NAMESPACE_URL, batch + ":unknown-tenant"))}, 403, None),
                ("api", "query_override", api + "?owner=all", api_headers, 400, None),
                ("api", "body_override", api, api_headers, 400, {"scope": "all"}),
                ("api", "missing_Run", config["api_url"].rstrip("/") + "/api/v2/investigation/runs/" + str(uuid5(NAMESPACE_URL, batch + ":missing-run")), api_headers, 404, None),
                ("internal", "missing_token", internal, {}, 401, None),
                ("internal", "bad_token", internal, {**inner_headers, "Authorization": "Bearer wrong"}, 401, None),
                ("internal", "missing_actor", internal, {k: v for k, v in inner_headers.items() if k != "X-AiSOC-Actor-ID"}, 400, None),
                ("internal", "invalid_actor", internal, {**inner_headers, "X-AiSOC-Actor-ID": "invalid"}, 400, None),
                ("internal", "missing_tenant", internal, {k: v for k, v in inner_headers.items() if k != "X-AiSOC-Tenant-ID"}, 400, None),
                ("internal", "query_override", internal + "?scope=all", inner_headers, 400, None)):
                response = await client.request("GET", url, headers=headers, **({"json": body} if body is not None else {}))
                negatives.append({"surface": surface, "case": name, "status": response.status_code})
                assert response.status_code == expected, "read_auth_or_scope_negative_failed"
            response = await client.get(api, headers=api_headers)
            assert response.status_code == 200, "real_result_GET_failed"
            payload = response.json()
            repeated = await client.get(api, headers=api_headers)
            assert repeated.status_code == 200 and repeated.json() == payload, "repeat_GET_changed_result"
        after = await read_rows(reader, tenant)
        checked = verify_stable_read(payload, before, after, tenant=tenant, prior=prior)
        report = {"schema": "investigation_result_http_seam.v1", "status": "passed_limited_two_process_GET", "batch": batch,
            "run_id": str(RUN), "tenant_id": str(tenant), "actual_probe_GETs": len(negatives) + 2, "positive_GETs": 2, "negative_GETs": negatives,
            "manifest_ref": payload["manifest"]["manifest_ref"], "manifest_artifact": payload["manifest_artifact"], **checked,
            "new_runs": 0, "new_events": 0, "new_artifacts": 0, "activity_queries": 0, "models": 0, "notification_sends": 0,
            "legacy_Run_columns_unchanged": True, "read_permission_scope": "real shared service authentication; user RBAC revocation not exercised",
            "baseline_verified_before_HTTP": True,
            "not_start_Case_Deep_or_deployment_acceptance": True}
        (out / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "report.md").write_bytes(payload["markdown"].encode("utf-8"))
        (out / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        progress.update(status=report["status"]);save()
        return report
    finally:
        await reader.close(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args();args.out.mkdir(parents=True, exist_ok=False)
    try:
        report = asyncio.run(run_probe(json.loads(args.config.read_text(encoding="utf-8")), args.out))
        print(json.dumps({key: report[key] for key in ("status", "run_id", "actual_probe_GETs", "events", "artifacts", "manifest_ref")}))
    except Exception as exc:
        failure = {"status": "failed_preserve_read_trial", "error_type": type(exc).__name__}
        if isinstance(exc, AssertionError): failure["check"] = str(exc)
        (args.out / "failure.json").write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(failure));raise SystemExit(1)
