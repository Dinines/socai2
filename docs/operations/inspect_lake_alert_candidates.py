"""Read a selected lake scope and retain 4a decisions locally. Never dispatch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from app.services.lake_alert_selection import (
    CANDIDATES,
    SelectionPolicy,
    delivery_effect,
    reconcile_immutable_versions,
    select_alert,
)

FIELDS = ("tenant_id", "source_namespace", "mapping_version", "event_id", "source_version", "event_time", "class_uid",
          "parse_status", "source_event_id", "ocsf_json")
STATUS_VERSION = "socai2.lake-alert-selection-execution.v1"


def query_sql(policy):
    fields = ", ".join(FIELDS)
    return f"""SELECT {fields} FROM (
 SELECT {fields},row_number() OVER (PARTITION BY tenant_id,event_time,class_uid,event_id
 ORDER BY ingest_time DESC,kafka_topic DESC,kafka_partition DESC,kafka_offset DESC) AS source_rank
 FROM {policy.body['database']}.raw_events WHERE tenant_id=%(tenant_id)s
 AND source_namespace=%(source_namespace)s AND mapping_version=%(mapping_version)s
) WHERE source_rank=1 ORDER BY event_time,class_uid,event_id LIMIT %(fetch_limit)s"""


def scan(client, policy):
    limits = policy.body["read_limits"]
    settings = {"readonly": 2, "max_execution_time": limits["query_timeout_seconds"],
        "max_result_rows": limits["max_records"]+1, "max_result_bytes": limits["max_result_bytes"],
        "result_overflow_mode": "throw"}
    expected = client.execute(f"""SELECT uniqExact(tuple(event_time,class_uid,event_id))
 FROM {policy.body['database']}.raw_events WHERE tenant_id=%(tenant_id)s
 AND source_namespace=%(source_namespace)s AND mapping_version=%(mapping_version)s""", policy.scope(), settings=settings)[0][0]
    if not 0 < expected <= limits["max_records"]:
        raise ValueError("selected_batch_empty_or_exceeds_limit")
    stream = iter(client.execute_iter(query_sql(policy), {**policy.scope(), "fetch_limit": limits["max_records"]+1},
                                      with_column_types=True, settings=settings))
    names = [name for name, _ in next(stream)]
    if tuple(names) != FIELDS:
        raise ValueError("lake_column_contract_mismatch")
    decisions, identities = [], set()
    for index, values in enumerate(stream):
        if index >= limits["max_records"]:
            raise ValueError("selected_batch_limit_exceeded")
        decision = select_alert(dict(zip(names, values, strict=True)), policy)
        if decision["delivery_key"] in identities:
            raise ValueError("duplicate_lake_version_after_dedup")
        identities.add(decision["delivery_key"])
        decisions.append(decision)
    if len(decisions) != expected:
        raise ValueError("fixed_scope_read_incomplete_or_changed")
    reconcile_immutable_versions(decisions)
    outcomes, blockers, coverage = Counter(), Counter(), Counter()
    for decision in decisions:
        outcomes[decision["action"]] += 1
        if decision["action"] in CANDIDATES:
            blockers.update((decision["identity"] or {}).get("blockers", []))
        coverage[json.dumps([decision["reported_class_uid"], decision["target_class_uid"], decision["is_alert"], decision["quality"]])] += 1
        decision["prospective_effect_without_existing_subject"] = delivery_effect(decision, subject_exists=False, delivered_keys=set())
    return {"schema_version": "socai2.lake-alert-selection-report.v1", "mode": "read_only_no_dispatch",
        "database": policy.body["database"], "scope": policy.scope(), "policy_digest": policy.digest,
        "validation": {"scope_count_matches": True, "versions_unique": True, "all_not_dispatched": True},
        "counts": {"logical_versions": len(decisions), "actions": dict(outcomes), "identity_blockers": dict(blockers)},
        "coverage": dict(coverage), "decisions": decisions,
        "limitations": ["not_business_ground_truth", "no_pg_subject_lookup", "no_actual_delivery",
            "global_identity_only_checked_in_selected_scope" if policy.immutable else "unobserved_lifecycle_not_verified"]}


def save_and_readback(report, directory):
    raw = json.dumps(report, ensure_ascii=False, indent=2).encode()
    path = directory / "report.json"
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o600)
    received = path.read_bytes()
    if hashlib.sha256(received).digest() != hashlib.sha256(raw).digest() or json.loads(received) != report:
        raise ValueError("private_report_readback_mismatch")


def run(args):
    from clickhouse_driver import Client
    os.umask(0o077)
    directory = Path(args.private_results)
    directory.mkdir(mode=0o700, exist_ok=False)
    passed, client = False, None
    try:
        policy = SelectionPolicy.load(args.policy)
        connection = json.loads(Path(args.connection).read_text())
        if connection["database"] != policy.body["database"]:
            raise ValueError("connection_policy_database_mismatch")
        limits = policy.body["read_limits"]
        client = Client(host=connection["host"], port=connection["port"], database=connection["database"],
            user=connection["user"], password=connection["password"], disable_reconnect=True,
            connect_timeout=limits["connect_timeout_seconds"], send_receive_timeout=limits["send_receive_timeout_seconds"])
        report = scan(client, policy)
        save_and_readback(report, directory)
        passed = True
    except Exception as exc:  # noqa: BLE001 -- diagnostics stay private; public output is fixed status only.
        import traceback
        (directory / "error.json").write_text(json.dumps({"error_type": type(exc).__name__, "traceback": traceback.format_exc()}))
    finally:
        if client is not None:
            client.disconnect()
    status = {"schema_version": STATUS_VERSION, "execution": "completed" if passed else "incomplete",
        "validation": "passed" if passed else "not_passed", "private_report_saved": (directory / "report.json").exists()}
    with Path(args.execution_status).open("x") as stream:
        json.dump(status, stream, indent=2)
    print(json.dumps(status))
    return 0 if passed else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("policy", "connection", "private-results", "execution-status"):
        parser.add_argument("--"+name, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
