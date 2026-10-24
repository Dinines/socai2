#!/usr/bin/env python3
"""One bounded LakeWriter insertion and independent readback for a D1 fixture.

Tenant predicates are program filters, not database row-level isolation. A
failed/unknown attempt is retained and is never retried by this program.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import importlib.util
import ipaddress
import json
from pathlib import Path
import sys
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from alert_kafka import ROOT, _save_receipt
from alert_scenarios import json_bytes, sha256
from investigation_fixture import load_fixture


class CheckFailed(ValueError):
    """A fixed, non-secret check identifier suitable for receipts."""


def _require(condition: bool, check: str) -> None:
    if not condition:
        raise CheckFailed(check)


def connection_config(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(isinstance(config, dict) and set(config) == {"writer", "reader"}, "config_roles")
    result = []
    for role in ("writer", "reader"):
        entry = config[role]
        _require(isinstance(entry, dict) and set(entry) == {"host", "port", "database", "user", "password"},
                 "explicit_connection_fields")
        _require(all(isinstance(entry[k], str) and entry[k].strip() for k in ("host", "database", "user")),
                 "connection_identity")
        _require(isinstance(entry["password"], str) and bool(entry["password"]), "explicit_password")
        _require(type(entry["port"]) is int and 1 <= entry["port"] <= 65535, "connection_port")
        _require(entry["database"] == "aisoc", "fixed_database")
        result.append(dict(entry))
    writer, reader = result
    _require(all(writer[k] == reader[k] for k in ("host", "port", "database")), "same_backend")
    _require(writer["user"] != reader["user"], "separate_reader_writer")
    return writer, reader


class _SafeWriterLogger:
    def __init__(self, entries: list[dict[str, Any]]) -> None:
        self.entries = entries

    def info(self, event: str, **fields: Any) -> None:
        entry: dict[str, Any] = {"event": event}
        if type(fields.get("dropped")) is int:
            entry["dropped"] = fields["dropped"]
        self.entries.append(entry)  # Deliberately discard original exception strings.

    warning = info
    error = info


def lake_module(logs: list[dict[str, Any]]) -> Any:
    """A private import leaves the running service and its logger untouched."""
    name = "socai2_testdata_lake_probe_writer"
    spec = importlib.util.spec_from_file_location(name, ROOT / "services/fusion/app/services/lake_writer.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.logger = _SafeWriterLogger(logs)
    return module


def _error(exc: BaseException) -> dict[str, Any]:
    result: dict[str, Any] = {"class": type(exc).__name__}
    if isinstance(exc, CheckFailed):
        result["check"] = str(exc)
    code = getattr(exc, "code", None)
    if type(code) is int:
        result["code"] = code
    return result


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (UUID, ipaddress.IPv4Address, ipaddress.IPv6Address)):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _normalized(column: str, value: Any) -> Any:
    if column in ("tenant_id", "event_id"):
        return str(UUID(str(value)))
    if column in ("source_ip", "dest_ip"):
        address = ipaddress.ip_address(str(value))
        return str(address.ipv4_mapped or address) if isinstance(address, ipaddress.IPv6Address) else str(address)
    if column == "event_time":
        _require(isinstance(value, datetime), "readback_datetime_type")
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    return list(value) if isinstance(value, tuple) else value


async def run_probe(*, input_dir: Path, tenant: str, config: dict[str, Any], out: Path,
                    reader_factory=None, writer_factory=None) -> dict[str, Any]:
    """Factories exist only for direct offline tests; real operation uses original LakeWriter."""
    manifest, alerts, events = load_fixture(Path(input_dir), tenant=tenant)
    writer_config, reader_config = connection_config(config)
    _require(len(events) == 3, "exact_three_events")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    receipt_path = out / "receipt.json"
    logs: list[dict[str, Any]] = []
    lake = lake_module(logs)
    expected_rows = [lake.event_to_row(event) for event in events]
    _require(all(row is not None for row in expected_rows), "valid_writer_mapping")
    columns = list(lake._COLUMNS)
    event_ids = tuple(event["id"] for event in events)
    tenant = manifest["tenant_id"]
    control_tenant = str(uuid5(NAMESPACE_URL,
                              f"socai2:investigation-fixture:v1:{tenant}:{manifest['run_id']}:other"))
    state: dict[str, Any] = {
        "schema_version": "socai2-lake-fixture-probe/v1", "run_id": manifest["run_id"],
        "tenant_id": tenant, "control_tenant_id": control_tenant,
        "event_ids": list(event_ids), "alert_id": alerts[0]["id"],
        "alert_source_event_ids": alerts[0]["source_event_ids"], "requested": 3,
        "fixture_manifest_sha256": sha256((Path(input_dir) / "manifest.json").read_bytes()),
        "status": "preflight_started", "stage": "reader_connect", "write_attempted": False,
        "write_outcome": "not_started",
        "backend": {key: writer_config[key] for key in ("host", "port", "database")},
        "writer_user": writer_config["user"], "reader_user": reader_config["user"],
        "queries": [], "writer_logs": logs, "cleanup_errors": [],
        "tenant_isolation": "explicit query predicates; not database row-level isolation",
    }
    _save_receipt(receipt_path, state)
    reader = writer = None

    def query(stage: str, sql: str, params: dict[str, Any], *, typed: bool = False) -> Any:
        state["stage"] = stage
        item: dict[str, Any] = {"stage": stage, "sql": sql, "parameters": _json_value(params),
                                "status": "started"}
        state["queries"].append(item)
        _save_receipt(receipt_path, state)
        result = reader.execute(sql, params, with_column_types=typed)
        item.update(status="returned", result_sha256=sha256(json_bytes(_json_value(result))))
        item["row_count"] = len(result[0] if typed else result)
        _save_receipt(receipt_path, state)
        return result

    try:
        if reader_factory is None:
            from clickhouse_driver import Client
            reader_factory = Client
        reader = reader_factory(**reader_config, connect_timeout=5, send_receive_timeout=5,
                                settings={"readonly": 1, "max_execution_time": 5})
        schema = query("schema", "SELECT name, type FROM system.columns WHERE database = %(database)s "
                       "AND table = %(table)s", {"database": "aisoc", "table": "raw_events"})
        state["schema"] = _json_value(schema)
        _require(set(columns).issubset({entry[0] for entry in schema}), "missing_writer_columns")
        identity = {"tenant_id": tenant, "event_ids": event_ids}
        existing = query("existing_ids", "SELECT count() FROM aisoc.raw_events WHERE tenant_id = %(tenant_id)s "
                         "AND event_id IN %(event_ids)s", identity)
        _require(existing == [(0,)], "existing_event_ids")
        existing_tenant = query("existing_tenant", "SELECT count() FROM aisoc.raw_events "
                                "WHERE tenant_id = %(tenant_id)s", {"tenant_id": tenant})
        _require(existing_tenant == [(0,)], "tenant_not_empty")
        state.update(status="write_started_outcome_unknown", stage="writer_start")
        _save_receipt(receipt_path, state)  # Durable attempt precedes writer construction/start.
        factory = writer_factory or lake.LakeWriter
        writer = factory(**writer_config, batch_size=4, batch_max_age_seconds=3600)
        await writer.start()
        _require(writer._client is not None, "writer_client_unavailable")
        # Original start creates a lazy Client. Bound this dedicated instance's
        # native IO before its first connection, without altering the service.
        for connection in [writer._client.connection, *writer._client.connections]:
            _require(not connection.connected, "writer_connected_before_timeout_configuration")
            connection.connect_timeout = 5
            connection.send_receive_timeout = 5
            connection.disable_reconnect = True
        state["writer_io"] = {"connect_timeout": 5, "send_receive_timeout": 5, "disable_reconnect": True}
        for event in events:
            _require(await writer.write_event(event), "writer_rejected_event")
        _require(writer.metrics() == {"rows_written": 0, "flush_failures": 0, "buffered": 3},
                 "buffer_before_single_flush")
        state.update(stage="single_flush", write_attempted=True, write_outcome="unknown")
        _save_receipt(receipt_path, state)
        await writer.flush()
        state["writer_metrics"] = writer.metrics()
        _save_receipt(receipt_path, state)
        _require(state["writer_metrics"] == {"rows_written": 3, "flush_failures": 0, "buffered": 0},
                 "writer_flush_not_confirmed")
        state["write_outcome"] = "insert_acknowledged"

        sql = f"SELECT {', '.join(columns)} FROM aisoc.raw_events WHERE tenant_id = %(tenant_id)s " \
              "AND event_id IN %(event_ids)s LIMIT 4"
        values, returned_columns = query("readback", sql, identity, typed=True)
        state["readback_columns"] = _json_value(returned_columns)
        state["readback_row_count"] = len(values)
        _save_receipt(out / "readback.json", {"columns": _json_value(returned_columns),
                                             "rows": _json_value(values)})
        _save_receipt(receipt_path, state)
        _require([col[0] for col in returned_columns] == columns, "readback_columns")
        _require(len(values) == 3, "readback_row_count")
        rows = [dict(zip(columns, row, strict=True)) for row in values]
        by_id = {str(row["event_id"]): row for row in rows}
        _require(set(by_id) == set(event_ids), "readback_unique_ids")
        comparisons = []
        for expected, record in zip(expected_rows, manifest["events"], strict=True):
            actual = by_id[expected["event_id"]]
            differences = [col for col in columns if _normalized(col, actual[col]) != _normalized(col, expected[col])]
            comparison = {"event_id": expected["event_id"], "columns_checked": columns, "differences": differences,
                          "raw_payload_sha256": sha256(actual["raw_payload"].encode("utf-8")),
                          "ocsf_json_sha256": sha256(actual["ocsf_json"].encode("utf-8"))}
            comparisons.append(comparison)
            state["comparisons"] = comparisons
            _save_receipt(receipt_path, state)
            _require(not differences, "readback_field_mismatch")
            _require(all(comparison[key] == record[key] for key in ("raw_payload_sha256", "ocsf_json_sha256")),
                     "readback_hash_mismatch")
        state["write_outcome"] = "three_rows_verified"
        context = manifest["query_context"]
        params = {key: context[key] for key in ("tenant_id", "hostname", "source_ip", "dest_ip", "dst_port", "protocol")}
        for key in ("window_start", "window_end"):
            params[key] = datetime.fromisoformat(context[key]).replace(tzinfo=None)
        selected = query("bounded_match", "SELECT event_id FROM aisoc.raw_events WHERE tenant_id = %(tenant_id)s "
                         "AND src_hostname = %(hostname)s AND source_ip = toIPv6(%(source_ip)s) "
                         "AND dest_ip = toIPv6(%(dest_ip)s) AND dst_port = %(dst_port)s AND protocol = %(protocol)s "
                         "AND event_time >= toDateTime64(%(window_start)s, 3, 'UTC') "
                         "AND event_time < toDateTime64(%(window_end)s, 3, 'UTC') LIMIT 4", params)
        state["matched_event_ids"] = [str(row[0]) for row in selected]
        _require(state["matched_event_ids"] == alerts[0]["source_event_ids"], "bounded_match_not_exact")
        control = query("control_tenant", "SELECT count() FROM aisoc.raw_events WHERE tenant_id = %(tenant_id)s "
                        "AND event_id IN %(event_ids)s", {"tenant_id": control_tenant, "event_ids": event_ids})
        _require(control == [(0,)], "control_tenant_not_empty")
        state.update(status="passed", stage="completed")
    except BaseException as exc:
        state.update(status="failed_outcome_unknown" if state["write_attempted"] else "failed_before_write",
                     error=_error(exc))
        if writer is not None:
            state["writer_metrics"] = writer.metrics()
            if state["writer_metrics"]["rows_written"] == 3 and not state["writer_metrics"]["flush_failures"]:
                state["status"] = "failed_verification"
    finally:
        if writer is not None:
            # Original stop() calls flush(). Never let cleanup submit a partial buffer.
            state["discarded_buffer_on_cleanup"] = len(writer._buffer)
            writer._buffer.clear()
            try:
                await writer.stop()
            except BaseException as exc:
                state["cleanup_errors"].append({"role": "writer", **_error(exc)})
        if reader is not None:
            try:
                reader.disconnect()
            except BaseException as exc:
                state["cleanup_errors"].append({"role": "reader", **_error(exc)})
        if state["cleanup_errors"] and state["status"] == "passed":
            state["status"] = "failed_cleanup"
        _save_receipt(receipt_path, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = vars(parser.parse_args())
    config_path = args.pop("config")
    try:
        result = asyncio.run(run_probe(**args, config=json.loads(config_path.read_text(encoding="utf-8-sig"))))
    except Exception as exc:
        print(json.dumps({"status": "rejected_before_probe", "error": _error(exc)}))
        raise SystemExit(1)
    print(json.dumps({"status": result["status"], "stage": result["stage"], "requested": result["requested"]}))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
