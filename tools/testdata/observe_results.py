#!/usr/bin/env python3
"""Read a small test batch's persisted results; never send inputs or score answers.

Use --snapshot for an offline capture, or explicitly name a PG DSN environment
variable. PG reads run inside one read-only transaction. The output contains
selected source rows plus observations, so it can itself be read offline.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import sys
from typing import Any
from uuid import UUID


SCHEMA = "socai2-testdata-observation/v1"


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _default(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def _normalise(value: Any) -> Any:
    return json.loads(json.dumps(value, default=_default))


def load_targets(manifest: dict, receipt: dict) -> tuple[str, str, list[dict]]:
    """Use explicit mapping only; batch run_id is never an investigation Run."""
    if manifest.get("schema_version") not in {"socai2-existing-alert-fixtures/v1", "socai2-existing-alert-fixtures/v2"}:
        raise ValueError("unsupported batch manifest")
    tenant = str(UUID(manifest["tenant_id"]))
    batch = manifest["run_id"]
    if receipt.get("tenant_id") != tenant or receipt.get("run_id", receipt.get("batch_id")) != batch:
        raise ValueError("receipt tenant or batch differs")
    records = manifest.get("records")
    if not isinstance(records, list) or not 1 <= len(records) <= 20 or manifest.get("count") != len(records):
        raise ValueError("batch must contain 1..20 records")
    ids = [str(UUID(row["alert_id"])) for row in records]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate input Alert identity")
    links = {}
    for row in receipt.get("records", []):
        input_id = str(UUID(row["alert_id"]))
        if input_id not in ids or input_id in links:
            raise ValueError("receipt includes unexpected or duplicate input")
        response = row.get("response") or {}
        if response.get("tenant_id", tenant) != tenant or response.get("input_id", input_id) != input_id:
            raise ValueError("response identity differs")
        canonical = response.get("canonical_alert_id") or row.get("canonical_alert_id") or row.get("predicted_canonical_alert_id")
        links[input_id] = {
            "canonical_alert_id": str(UUID(canonical)) if canonical else None,
            "mapping_source": "HTTP response" if response.get("canonical_alert_id") else "explicit mapping or sender prediction",
            "sender_state": row.get("state", "not_recorded"),
            "broker_coordinate": row.get("message"),
        }
    targets = [{"input_alert_id": ident, **links.get(ident, {
        "canonical_alert_id": None, "mapping_source": "missing", "sender_state": "not_attempted",
    })} for ident in ids]
    canonical_ids = [row["canonical_alert_id"] for row in targets if row["canonical_alert_id"]]
    if len(canonical_ids) != len(set(canonical_ids)):
        raise ValueError("multiple batch inputs map to the same canonical Alert")
    return tenant, batch, targets


async def fetch_snapshot(dsn: str, tenant: str, canonical_ids: list[str], *, ssl_context=None, connect=None) -> dict:
    """Fetch exact identities, all seq values, and existing artifact bodies."""
    if connect is None:
        import asyncpg
        connect = asyncpg.connect
    conn = await connect(dsn=dsn, ssl=ssl_context, timeout=10, command_timeout=20)
    result = {"tenant_id": tenant, "captured_at": datetime.now(timezone.utc).isoformat()}
    try:
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", tenant)
            alert_ids = [UUID(value) for value in canonical_ids]
            result["alerts"] = [dict(row) for row in await conn.fetch(
                "SELECT id,tenant_id,title,status,disposition,ai_score,ai_summary,resolved_at,"
                "source_event_ids,external_id,case_id,enrichment_data FROM alerts "
                "WHERE tenant_id=$1 AND id=ANY($2::uuid[])", UUID(tenant), alert_ids)]
            result["runs"] = [dict(row) for row in await conn.fetch(
                "SELECT id,tenant_id,case_id,raw_alert,status,error,started_at,completed_at,total_tokens,"
                "measured_call_count,estimated_call_count,unpriced_call_count "
                "FROM investigation_runs WHERE tenant_id=$1 "
                "AND (raw_alert->>'id'=ANY($2::text[]) OR case_id=ANY($2::text[])) "
                "ORDER BY started_at,id LIMIT 101", UUID(tenant), canonical_ids)]
            if len(result["runs"]) > 100:
                raise ValueError("more than 100 related Runs; narrow the batch")
            run_ids = [row["id"] for row in result["runs"]]
            for table, columns, order, cap in (
                ("investigation_events", "id,tenant_id,run_id,seq,ts,kind,agent,summary,payload,input_hash,output_hash,duration_ms", "run_id,ts,seq", 5000),
                ("investigation_artifacts", "id,tenant_id,run_id,event_id,kind,content,blob_ref,sha256,size_bytes,created_at", "run_id,created_at,id", 1000),
                ("aisoc_run_costs", "tenant_id,run_id,model,resolved_model,call_count,total_prompt_tokens,total_completion_tokens,measured_call_count,measured_cost_usd,estimated_call_count,estimated_cost_usd,unpriced_call_count", "run_id,model", 1000),
            ):
                text_ids = table == "aisoc_run_costs"
                rows = await conn.fetch(
                    f"SELECT {columns} FROM {table} WHERE tenant_id=$1 AND run_id=ANY($2::{ 'text' if text_ids else 'uuid' }[]) ORDER BY {order} LIMIT {cap + 1}",
                    tenant if text_ids else UUID(tenant), [str(value) for value in run_ids] if text_ids else run_ids,
                )
                if len(rows) > cap:
                    raise ValueError(f"{table} exceeds bounded observation; narrow the batch")
                result[{"investigation_events": "events", "investigation_artifacts": "artifacts", "aisoc_run_costs": "costs"}[table]] = [dict(row) for row in rows]
    finally:
        await conn.close()
    return _normalise(result)


def artifact_check(row: dict) -> dict:
    content = row.get("content")
    data = content.encode("utf-8") if isinstance(content, str) else None
    return {"artifact_id": row["id"], "kind": row["kind"], "has_inline_content": data is not None,
            "bytes_match": len(data) == row.get("size_bytes") if data is not None else None,
            "sha256_match": hashlib.sha256(data).hexdigest() == row.get("sha256") if data is not None else None,
            "blob_ref_present": bool(row.get("blob_ref"))}


def _observe_run(run: dict, events: list[dict], artifacts: list[dict], costs: list[dict]) -> dict:
    checks = [artifact_check(row) for row in artifacts]
    md = [row for row in checks if row["kind"] == "report_md"]
    md_readable = bool(md) and all(md[-1][key] for key in ("has_inline_content", "bytes_match", "sha256_match"))
    graph_events = [row for row in events if row["kind"] == "graph_result"]
    triage = [_json(row.get("payload") or {}) for row in events if row["kind"] == "triage_verdict"]
    graph = _json(graph_events[-1].get("payload") or {}) if graph_events else {}
    graph_state = None
    graph_artifacts = [(row, check) for row, check in zip(artifacts, checks) if row["kind"] == "graph_result"]
    if graph_artifacts:
        row, check = graph_artifacts[-1]
        if all(check[key] for key in ("has_inline_content", "bytes_match", "sha256_match")):
            try:
                value = _json(row["content"])
                graph_state = value if isinstance(value, dict) else None
            except (ValueError, TypeError):
                pass
    depth = (graph_state or {}).get("investigation_depth") or {}
    execution = run.get("status", "unknown")
    if graph.get("completion") == "partial" or depth.get("truncated") or depth.get("error"):
        investigation = "partial"
    elif graph.get("completion") == "completed":
        investigation = "completed" if md_readable and graph_state is not None else "partial"
    elif triage and triage[-1].get("auto_closed") is True:
        investigation = "not_required_auto_closed"
    elif execution == "failed":
        investigation = "partial" if artifacts or events else "failed"
    elif execution == "running":
        investigation = "running"
    else:
        investigation = "missing"
    return {
        "run_id": run["id"], "execution_status": execution, "investigation_status": investigation,
        "error": run.get("error"), "triage": triage, "graph_result": graph,
        "graph_state_readable": graph_state is not None,
        "stop_reason": depth.get("stop_reason") or (graph_state or {}).get("budget_exhausted_reason") or (graph_state or {}).get("error"),
        "event_count": len(events), "artifact_count": len(artifacts), "artifact_integrity": checks,
        "markdown": {"state": "readable_verified" if md_readable else ("unreadable_or_unverified" if md else "missing"),
                     "artifact_ids": [row["artifact_id"] for row in md]},
        "usage": {"run_total_tokens": run.get("total_tokens"),
                  "cost_rows": len(costs), "recorded_call_count": sum(row["call_count"] for row in costs) if costs else None,
                  "recorded_tokens": sum(row["total_prompt_tokens"] + row["total_completion_tokens"] for row in costs) if costs else None,
                  "measured_call_count": sum(row.get("measured_call_count", 0) for row in costs) if costs else None,
                  "measured_cost_usd": sum(row.get("measured_cost_usd") or 0 for row in costs) if any(row.get("measured_call_count", 0) for row in costs) else None,
                  "estimated_call_count": sum(row.get("estimated_call_count", 0) for row in costs) if costs else None,
                  "estimated_cost_usd": sum(row.get("estimated_cost_usd") or 0 for row in costs) if any(row.get("estimated_call_count", 0) for row in costs) else None,
                  "unpriced_call_count": sum(row.get("unpriced_call_count", 0) for row in costs) if costs else None,
                  "meaning": "Persisted aggregates only; Run tokens and cost-row tokens are not added together. Absent or unfinished calls remain unknown."},
        "content_assessment": "not_reviewed",
    }


def observe(manifest: dict, receipt: dict, snapshot: dict) -> dict:
    tenant, batch, targets = load_targets(manifest, receipt)
    snapshot = snapshot.get("snapshot", snapshot)
    if snapshot.get("tenant_id") != tenant:
        raise ValueError("snapshot tenant differs")
    scoped = {key: [row for row in snapshot.get(key, []) if str(row.get("tenant_id")) == tenant]
              for key in ("alerts", "runs", "events", "artifacts", "costs")}
    selected = {key: [] for key in scoped}
    rows = []
    for target in targets:
        canonical = target["canonical_alert_id"]
        alert_rows = [row for row in scoped["alerts"] if row["id"] == canonical]
        if len(alert_rows) > 1:
            raise ValueError("duplicate canonical Alert in snapshot")
        alert = alert_rows[0] if alert_rows else None
        identity = _json(alert.get("enrichment_data") or {}).get("socai2_fusion", {}).get("identity", {}) if alert else {}
        source_id = identity.get("source_alert_id")
        source_matches = source_id == target["input_alert_id"] if source_id is not None else None
        runs = []
        if alert and source_matches is not False:
            selected["alerts"].append(alert)
            for run in scoped["runs"]:
                raw_id = _json(run.get("raw_alert") or {}).get("id")
                if raw_id != canonical and run.get("case_id") != canonical:
                    continue
                if raw_id is not None and raw_id != canonical:
                    raise ValueError("Run linkage conflicts with canonical Alert")
                selected["runs"].append(run)
                children = {key: [row for row in scoped[key] if str(row["run_id"]) == str(run["id"])]
                            for key in ("events", "artifacts", "costs")}
                children["events"].sort(key=lambda row: (row.get("ts") or "", row.get("seq", 0)))
                children["artifacts"].sort(key=lambda row: row.get("created_at") or "")
                for key, items in children.items():
                    selected[key].extend(items)
                runs.append(_observe_run(run, children["events"], children["artifacts"], children["costs"]))
        rows.append({**target, "alert_status": "identity_mismatch" if source_matches is False else ("present" if alert else "missing"),
                     "source_identity_matches": source_matches, "run_status": "present" if runs else "missing", "runs": runs})
    return {"schema_version": SCHEMA, "batch_id": batch, "tenant_id": tenant,
            "observed_at": datetime.now(timezone.utc).isoformat(), "source_captured_at": snapshot.get("captured_at"),
            "execution_version": manifest.get("execution_version", "not_recorded"), "records": rows,
            "investigation_status_counts": dict(Counter(run["investigation_status"] for row in rows for run in row["runs"])),
            "snapshot": {"tenant_id": tenant, "captured_at": snapshot.get("captured_at"), **selected},
            "limitations": ["Observation only; no expected answers are read and no model or business writes run.",
                            "ACK or canonical prediction does not prove processing. Missing data is not a failed or benign verdict.",
                            "Run completion, investigation completion, artifact integrity and semantic correctness are separate."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--receipt", "--canonical-map", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path)
    mode.add_argument("--dsn-env", help="explicit environment variable containing a read-only PG DSN")
    parser.add_argument("--ssl-ca", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.out.exists():
            raise FileExistsError("observation already exists")
        manifest, receipt = (json.loads(path.read_text()) for path in (args.manifest, args.receipt))
        tenant, _, targets = load_targets(manifest, receipt)
        if args.snapshot:
            snapshot = json.loads(args.snapshot.read_text())
            mode_name = "offline_snapshot"
        else:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", args.dsn_env) or not os.environ.get(args.dsn_env):
                raise ValueError("DSN environment variable is missing")
            context = ssl.create_default_context(cafile=str(args.ssl_ca)) if args.ssl_ca else None
            snapshot = asyncio.run(fetch_snapshot(os.environ[args.dsn_env], tenant,
                                   [row["canonical_alert_id"] for row in targets if row["canonical_alert_id"]], ssl_context=context))
            mode_name = "postgres_read_only"
        result = observe(manifest, receipt, snapshot)
        result["observation_source"] = mode_name
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(result, output, ensure_ascii=False, indent=2, default=_default)
            output.write("\n")
        print(f"Observed {len(result['records'])} inputs from {mode_name}; saved {args.out}")
        return 0
    except Exception as exc:
        # DSNs and database error bodies can contain credentials; never print them.
        print(f"observation refused ({type(exc).__name__}); check explicit inputs and fresh output path", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
