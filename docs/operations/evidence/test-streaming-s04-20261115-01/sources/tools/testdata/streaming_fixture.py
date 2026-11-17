"""Offline S01/S04 materials. No sender, database, service or model execution."""
from __future__ import annotations

import argparse
import ipaddress
import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from alert_kafka import source_wire
from alert_scenarios import RUN_ID, _event_time, _without_answers, json_bytes, sha256

ROOT = Path(__file__).resolve().parents[2]
VERSION = "socai2-streaming-s01-s04/v1"
CONTRACTS = (
    "tools/testdata/streaming_fixture.py",
    "tools/testdata/alert_kafka.py",
    "tools/testdata/alert_scenarios.py",
    "services/fusion/app/models/alert.py",
    "services/fusion/app/services/event_schema.py",
    "services/fusion/app/services/correlator.py",
    "services/fusion/app/services/lake_writer.py",
    "services/fusion/app/services/received_fields.py",
    "services/fusion/app/services/lake_material.py",
    "services/api/app/socai2/baseline_evidence_tools.py",
    "services/api/app/socai2/case_execution_input.py",
)
KEYS = {"dataset_version", "batch_id", "tenant_id", "base_time", "source_namespace",
        "host_prefix", "account_prefix", "source_ip", "destination_ip",
        "other_destination_ip", "candidate_identity"}


def parameters(config):
    c = dict(config)
    if set(c) != KEYS or c["dataset_version"] != VERSION:
        raise ValueError("explicit current fixture configuration required")
    for key in ("batch_id", "source_namespace", "host_prefix", "account_prefix"):
        if not isinstance(c[key], str) or not RUN_ID.fullmatch(c[key]):
            raise ValueError(f"invalid {key}")
    c["tenant_id"] = str(UUID(c["tenant_id"]))
    c["base_time"] = _event_time(c["base_time"])
    if not 1971 <= datetime.fromisoformat(c["base_time"]).year <= 2099:
        raise ValueError("unsupported time range")
    networks = tuple(ipaddress.ip_network(n) for n in
                     ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"))
    for key in ("source_ip", "destination_ip", "other_destination_ip"):
        if not any(ipaddress.ip_address(c[key]) in n for n in networks):
            raise ValueError("fixture requires documentation IP ranges")
    if c["destination_ip"] == c["other_destination_ip"]:
        raise ValueError("destination control must differ")
    identity = (ROOT / c["candidate_identity"]).resolve()
    identity.relative_to(ROOT / "deploy")
    if json.loads(identity.read_text())["tenant_id"] != c["tenant_id"]:
        raise ValueError("candidate and fixture tenants differ")
    c["candidate_identity"] = identity.relative_to(ROOT).as_posix()
    return c


def _id(c, logical):
    return str(uuid5(NAMESPACE_URL, ":".join((VERSION, c["tenant_id"], c["batch_id"],
                                            c["source_namespace"], logical))))


def _jsonl(values):
    return b"".join((json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n").encode()
                    for x in values)


def build(config):
    c = parameters(config)
    base = datetime.fromisoformat(c["base_time"])
    host = f"{c['host_prefix']}-{c['batch_id']}"
    user = f"{c['account_prefix']}-{c['batch_id']}"
    connector = _id(c, "connector")
    # Milliseconds avoid an out-of-window record rounding back into a lake window.
    specs = [("E01", 3002, -120000), ("E02", 3002, 0), ("E03", 1007, 300000),
             ("E04", 1007, 360000), ("E05", 4001, 600000), ("E06", 4001, 660000),
             ("E07", 4001, 720000), ("E08", 1007, 780000), ("E09", 4001, 600000),
             ("E10", 4001, -3600001), ("E11", 4001, 4200000),
             ("E12", 3002, 60000), ("E13", 4001, 1500000)]
    events = {}
    for logical, kind, offset in specs:
        eid = _id(c, logical)
        when = (base + timedelta(milliseconds=offset)).isoformat()
        hostname = host + "-control" if logical == "E09" else host
        account = user + "-control" if logical == "E12" else user
        ocsf = {"uid": eid, "tenant_uid": c["tenant_id"], "time": when,
                "class_uid": kind, "category_uid": kind // 1000, "activity_id": 0,
                "severity_id": 1, "severity": "Informational",
                "metadata": {"uid": eid, "product": {"name": c["source_namespace"],
                             "vendor_name": "Synthetic LabTelemetry"}},
                "device": {"name": hostname}, "actor": {"user": {"name": account}},
                "src_endpoint": {"ip": c["source_ip"], "hostname": hostname},
                "synthetic": True}
        if kind == 3002:
            ocsf["activity"] = {"action": "logon", "outcome": "failure" if logical == "E01" else "success",
                                "session": {"id": _id(c, logical + "-session")}}
            ocsf["logon_type"] = "network"
        elif kind == 1007:
            parent = logical == "E03"
            ocsf["process"] = {"uid": _id(c, "parent" if parent else "child"),
                "name": "sh" if parent else "curl", "pid": 4100 if parent else 4101,
                "cmd_line": "/bin/sh" if parent else f"curl --head https://{c['destination_ip']}/status"}
            if not parent:
                ocsf["process"]["parent_process"] = {"uid": _id(c, "parent"), "pid": 4100}
            ocsf["activity"] = {"action": "process_end" if logical == "E08" else "process_start",
                                "outcome": "success"}
        else:
            other = logical == "E06"
            ocsf["src_endpoint"]["port"] = 52000 + int(logical[1:])
            ocsf["dst_endpoint"] = {"ip": c["other_destination_ip"] if other else c["destination_ip"],
                                    "port": 53 if other else 443}
            ocsf["protocol"] = "UDP" if other else "TCP"
            zero = logical == "E07"
            ocsf["traffic"] = {"bytes_out": 0 if zero else 2048, "bytes_in": 0 if zero else 128,
                               "packets_out": 0 if zero else 4, "packets_in": 0 if zero else 2}
            ocsf["activity"] = {"action": "network_flow_observed", "outcome": "unknown"}
            ocsf["sensor_observation"] = {"connection_reset": False, "dns_answers": []}
        ocsf["raw_data"] = json_bytes(ocsf).decode()
        events[logical] = {"schema_version": "v1", "event_id": eid, "tenant_id": c["tenant_id"],
            "connector_id": connector, "connector_type": c["source_namespace"], "ocsf_event": ocsf}
    alerts, predictions = {}, {}
    for logical, source in (("A01", "E02"), ("A02", "E04"), ("A03", "E05"), ("A04", "E13")):
        event = events[source]
        ocsf = event["ocsf_event"]
        payload = {"schema_version": "v1", "id": _id(c, logical), "tenant_id": c["tenant_id"],
            "source": c["source_namespace"], "title": f"Synthetic {ocsf['activity']['action']} observation",
            "description": "Source observation for investigation; authorization and intent are unknown.",
            "severity": "medium", "event_time": ocsf["time"],
            "created_at": (datetime.fromisoformat(ocsf["time"]) + timedelta(seconds=1)).isoformat(),
            "hostname": host, "username": user, "src_ip": c["source_ip"],
            "connector_id": connector, "connector_type": c["source_namespace"],
            "ocsf_class_uid": ocsf["class_uid"], "source_event_ids": [event["event_id"]],
            "mitre_tactics": [], "mitre_techniques": [], "tags": ["synthetic"],
            "raw_event": {"synthetic": True, "ocsf_event": ocsf}}
        if "dst_endpoint" in ocsf:
            payload["dst_ip"] = ocsf["dst_endpoint"]["ip"]
        alerts[logical], predictions[logical] = source_wire(payload, c["tenant_id"])
    inputs = {
        "S01/alerts.jsonl": _jsonl(list(alerts.values())[:3]),
        "S01/context-events.jsonl": _jsonl(list(events.values())[:12]),
        "S04/alerts.jsonl": _jsonl([alerts["A04"]]),
        "S04/context-events.jsonl": _jsonl([events["E13"]]),
        "background.json": json_bytes({"synthetic": True, "state": "authored_not_imported",
            "asset": {"hostname": host, "local_ip": c["source_ip"], "purpose": "report application"},
            "account": {"username": user, "purpose": "scheduled reporting", "hostname": host},
            "maintenance_record": None, "authorization_status": "not_provided"}),
        "knowledge.json": json_bytes({"state": "authored_not_indexed", "synthetic": True, "items": [
            {"purpose": "technical_explanation", "text": "A successful login records that login action; it does not establish authorization for a later process."},
            {"purpose": "evidence_guidance", "text": "Compare host, account, event time and parent process identity; distinguish a connection observation from confirmed transfer."},
            {"purpose": "historical_reference", "text": "In a separate synthetic exercise an operator verified a scheduled report job. That history supplies no authorization for this batch."}]})}
    for name, data in inputs.items():
        for value in ([json.loads(line) for line in data.splitlines()] if name.endswith(".jsonl")
                      else [json.loads(data)]):
            _without_answers(value)
    def query(end, included):
        return {"window_start": (base - timedelta(hours=1)).isoformat(),
                "window_end": (base + timedelta(minutes=end)).isoformat(),
                "hostname": host, "tenant_id": c["tenant_id"],
                "available_phases": ["S01"] if end == 70 else ["S01", "S04"],
                "bounds": "start_inclusive_end_exclusive", "included": included,
                "state": "conditional_on_tool_selection_not_executed"}
    shared = {"authentication_activity": ["E01", "E02", "E12"], "process_activity": ["E03", "E04", "E08"]}
    expected = {"requirement_refs": ["S01", "S04-Q1", "F01", "F03", "F05"],
        "layer": "offline_contract", "model_verdict": "not_asserted",
        "source_links": {"A01": "E02", "A02": "E04", "A03": "E05", "A04": "E13"},
        "predicted_canonical_alert_ids": predictions, "processing_confirmed": False,
        "correlation": {"policy_version": "primary-entity-v2", "entity_type": "ip",
            "entity_value": c["source_ip"], "tactic": None, "logical_group": "I01",
            "members": list(alerts), "window_basis": "processing_time_index_ttl",
            "preconditions": ["empty candidate index", "max_alerts_per_incident >= 4",
                "S04 consumed before original index TTL expires; merge does not refresh index TTL"],
            "runtime_status": "blocked_dependency"},
        "queries": {
            "S01_full_host": query(70, {**shared, "network_connections": ["E05", "E06", "E07"]}),
            "S04_full_host": query(85, {**shared, "network_connections": ["E05", "E06", "E07", "E11", "E13"]}),
            "A01_fixed_host_after_S04": query(60, {**shared, "network_connections": ["E05", "E06", "E07", "E13"]})},
        "case_update": {"event_case": "I01 available business change precedes active Case check",
            "single_alert_case": "members remain A01; same-host context may include later events",
            "old_runs": "immutable", "no_changes": "no new Run or model request"}}
    controls = {
        "expected.json": json_bytes(expected),
        "identity-map.json": json_bytes({"state": "not_executed", "actual_mappings": []}),
        "actions.json": json_bytes({"state": "planned_not_executed", "sequence": [
            "prepare and read back S01 context/background from real sources",
            "send S01 A01-A03 via candidate Kafka after readiness gates",
            "read actual canonical/incident mappings and A/I completion via HTTP",
            "HTTP create whole-incident Case and single-A01 control; read initial results",
            "prepare/read back E13; send S04 A04 before original Fusion TTL expires",
            "read I business update, active Case update/previous-run comparison and fixed control",
            "read same batch through test HTTP and 4177; keep quality separate"]})}
    identity = json.loads((ROOT / c["candidate_identity"]).read_text())
    # Progress flags do not change fixture identity or query/correlation contracts.
    binding = {key: identity[key] for key in ("candidate_id", "tenant_id", "actor_id", "postgres", "http")}
    manifest = {"dataset_version": VERSION, "batch_id": c["batch_id"], "tenant_id": c["tenant_id"],
        "execution_status": "offline_only", "live_ready": False,
        "counts": {"S01": {"alerts": 3, "context_events": 12}, "S04": {"alerts": 1, "context_events": 1}},
        "logical_ids": {**{k: v["id"] for k, v in alerts.items()}, **{k: v["event_id"] for k, v in events.items()}},
        "source_sha256": {p: sha256((ROOT / p).read_bytes()) for p in CONTRACTS},
        "candidate_binding": {"path": c["candidate_identity"], "value": binding,
                              "sha256": sha256(json_bytes(binding))},
        "inputs": {p: sha256(v) for p, v in inputs.items()},
        "controls": {p: sha256(v) for p, v in controls.items()},
        "runtime_dependencies": ["actual candidate version and empty resource baseline",
            "Kafka topic/group/start offsets and explicit staged sender binding",
            "Fusion TTL/capacity and Redis instance/database isolation",
            "lake database/import/readback and background/knowledge source interfaces",
            "unique dispatcher, actual short-period profile and real model/tool budgets",
            "W2 HTTP identity mapping, W3 live 4177 and W4 package"]}
    return c, manifest, inputs, controls


def generate(config, out):
    c, manifest, inputs, controls = build(config)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    for name, value in {"config.json": json_bytes(c), "manifest.json": json_bytes(manifest),
                        **inputs, **controls}.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return validate(out)


def load_inputs(directory):
    """Read only generated input files; expected/control files need not exist."""
    directory = Path(directory)
    c, manifest, inputs, _ = build(json.loads((directory / "config.json").read_text()))
    if json.loads((directory / "manifest.json").read_text()) != manifest:
        raise ValueError("manifest differs from current recipe/contracts")
    for name, data in inputs.items():
        path = directory / name
        if path.is_symlink() or path.parent.is_symlink() or path.read_bytes() != data:
            raise ValueError(f"input differs from frozen recipe: {name}")
    return c, manifest, inputs


def validate(directory):
    directory = Path(directory)
    c, manifest, _ = load_inputs(directory)
    _, _, _, controls = build(c)
    for name, data in controls.items():
        if (directory / name).read_bytes() != data:
            raise ValueError(f"control differs from authored expectation: {name}")
    return {"status": "passed_offline", "batch_id": c["batch_id"], "counts": manifest["counts"],
            "files_checked": len(manifest["inputs"]) + len(controls) + 2,
            "manifest_sha256": sha256((directory / "manifest.json").read_bytes()),
            "live_ready": False, "business_connections": 0, "model_calls": 0, "kafka_sends": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--config", type=Path, required=True)
    gen.add_argument("--out", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = (generate(json.loads(args.config.read_text()), args.out) if args.command == "generate"
              else validate(args.input))
    print(json.dumps(result, ensure_ascii=False))
