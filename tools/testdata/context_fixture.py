"""Additional lake observations around fixed alerts; generation is offline.

Reuses the project's deterministic fixture identities, validation and JSON/hash
helpers. Expectations stay separate from event envelopes and are never sent to
Kafka or a model. No alert, Case, source_event_ids or existing Run is changed.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from alert_scenarios import _without_answers, json_bytes, sha256
from investigation_fixture import _identity, _parameters


def build(*, run_id, tenant, case):
    tenant, start = _parameters(run_id, tenant, case["window_start"])
    end = datetime.fromisoformat(case["window_end"])
    base = datetime.fromisoformat(case["alerts"][0]["event_time"])
    if not start < base < end or end - start < timedelta(seconds=100):
        raise ValueError("context fixture requires the original two-minute alert window")
    host = case["host"]
    process_event = case["alerts"][0]["raw_event"]["ocsf_event"]
    network_event = case["alerts"][1]["raw_event"]["ocsf_event"]
    user = process_event["actor"]["user"]["name"]
    src = network_event["src_endpoint"]["ip"]
    dst = network_event["dst_endpoint"]["ip"]
    specs = [
        ("network-near", 4001, base - timedelta(seconds=20), host, dst, 443, "tcp", 2400, 1200, 6, 3),
        ("network-other-destination", 4001, base - timedelta(seconds=10), host, "198.51.100.53", 53, "udp", 96, 192, 1, 2),
        ("network-volume", 4001, base + timedelta(seconds=25), host, "203.0.113.99", 8443, "tcp", 750000, 1500, 500, 3),
        ("network-zero", 4001, base + timedelta(seconds=40), host, dst, 443, "tcp", 0, 0, 0, 0),
        ("process-near", 1007, base + timedelta(seconds=5), host, None, None, None, 0, 0, 0, 0),
        ("auth-failure", 3002, base - timedelta(seconds=40), host, None, None, None, 0, 0, 0, 0),
        ("auth-success", 3002, base - timedelta(seconds=30), host, None, None, None, 0, 0, 0, 0),
        ("control-other-host", 4001, base, host + "-control", dst, 443, "tcp", 400, 200, 2, 1),
        ("control-before-window", 4001, start - timedelta(microseconds=1), host, dst, 443, "tcp", 400, 200, 2, 1),
        ("control-at-window-end", 4001, end, host, dst, 443, "tcp", 400, 200, 2, 1),
    ]
    events, expected = [], {"case_key": case["key"], "host": host,
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "included": {"network_connections": [], "process_activity": [], "authentication_activity": []},
        "excluded": [], "traffic": {}}
    kinds = {4001: "network_connections", 1007: "process_activity", 3002: "authentication_activity"}
    for ordinal, (role, kind, when, hostname, dest, port, protocol, bout, bin_, pout, pin) in enumerate(specs):
        identity = _identity(tenant, run_id, case["key"] + ":" + role)
        ocsf = {"class_uid": kind, "time": when.isoformat(), "device": {"name": hostname},
            "metadata": {"uid": identity, "product": {"name": "context-fixture", "vendor_name": "LabTelemetry"}}}
        if kind == 4001:
            ocsf.update(src_endpoint={"hostname": hostname, "ip": src, "port": 52000 + ordinal},
                dst_endpoint={"ip": dest, "port": port}, connection_info={"protocol_name": protocol},
                traffic={"bytes_out": bout, "bytes_in": bin_, "bytes": bout + bin_,
                    "packets_out": pout, "packets_in": pin, "packets": pout + pin},
                activity={"action": "network_flow_observed", "outcome": "unknown"})
            expected["traffic"][identity] = ocsf["traffic"]
        elif kind == 1007:
            ocsf.update(actor={"user": {"name": user}}, process={"name": "cmd.exe", "pid": 4243,
                "cmd_line": "cmd.exe /c hostname", "parent_process": {"pid": 4242}},
                activity={"action": "process_start", "outcome": "success"})
        else:
            ocsf.update(actor={"user": {"name": user}},
                activity={"action": "logon", "outcome": "failure" if role == "auth-failure" else "success",
                    "session": {"id": "ctx-" + identity[:8]}})
        ocsf["raw_data"] = json_bytes(ocsf).decode("utf-8")
        envelope = {"schema_version": "v1", "event_id": identity, "tenant_id": tenant,
            "connector_type": "validation", "original_vendor": "LabTelemetry", "ocsf_event": ocsf}
        _without_answers(envelope)
        events.append(envelope)
        if role.startswith("control-"):
            expected["excluded"].append({"event_id": identity, "reason": role})
        else:
            expected["included"][kinds[kind]].append(identity)
    return events, expected


def generate(plan_path, out, *, run_id):
    if out.exists():
        raise FileExistsError("fixed batch already exists; never overwrite or replay")
    plan = json.loads(plan_path.read_text("utf-8"))
    cases, expected = [], []
    for case in plan["cases"]:
        if case["scenario"] == "sparse":
            # Preserve the empty-query controls for both model cohorts.
            continue
        events, oracle = build(run_id=run_id, tenant=plan["tenant_id"], case=case)
        cases.append({"key": case["key"], "events": events, "alerts": []})
        expected.append(oracle)
    files = {"events.json": json_bytes({"tenant_id": plan["tenant_id"], "cases": cases}),
        "expected.json": json_bytes({"cases": expected, "not_an_attack_truth_label": True})}
    manifest = {"batch": run_id, "source_plan_sha256": sha256(plan_path.read_bytes()),
        "event_count": sum(len(c["events"]) for c in cases), "new_alerts": 0, "model_calls": 0,
        "files": {name: sha256(body) for name, body in files.items()},
        "reuse": ["investigation_fixture._identity/_parameters", "alert_scenarios.json_bytes/sha256/_without_answers"],
        "limitations": ["flow bytes are aggregate observations, not a packet capture or payload",
            "same-host time proximity and reported parent PID do not prove causality",
            "authentication success does not authorize an unrelated process or connection"]}
    out.mkdir(parents=True)
    for name, body in files.items():
        (out / name).write_bytes(body)
    (out / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.plan, args.out, run_id=args.run_id)))
