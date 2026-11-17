"""Prepare a new frozen wire bundle from explicit current-release bindings only."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

E = Path(__file__).resolve().parent
R = E.parents[3]
sys.path.insert(0, str(R / "tools/testdata"))
from alert_kafka import source_wire


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    config = json.loads((E / "preparation-config.json").read_text())
    fixture = config["fixture"]
    execution = config["execution"]
    release = json.loads((R / config["release_file"]).read_text())
    identity = json.loads((R / fixture["candidate_identity"]).read_text())
    assert identity["candidate_id"] == release["release"] == execution["release"]
    assert identity["tenant_id"] == fixture["tenant_id"]
    required = {
        "release",
        "release_root",
        "remote_directory",
        "topics",
        "expected_bootstrap_servers",
        "security_protocol",
        "producer_env_file",
        "processing_image",
        "network",
        "user",
        "http_base",
        "ssh_target",
        "containers",
        "ca_source",
        "ca_target",
        "producer_env_source",
        "dispatcher_profile",
        "database",
        "fusion_ready_url",
        "must_remain_stopped",
    }
    assert required <= execution.keys(), sorted(required - execution.keys())
    assert execution["release_root"] == release["root"]
    assert (
        execution["remote_directory"]
        == release["root"] + "/verification/" + config["batch_id"]
    )
    target = E / "batch"
    target.mkdir(exist_ok=False)
    (target / "out").mkdir()
    dependencies = [
        "tools/testdata/alert_kafka.py",
        "tools/testdata/alert_scenarios.py",
        "tools/testdata/material-source.json",
        "services/fusion/app/models/alert.py",
        "services/fusion/app/services/event_schema.py",
        "services/fusion/app/core/kafka_security.py",
    ]
    for name in dependencies:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(R / name, destination)
    shutil.copy2(E / "send-batch.py", target / "send-batch.py")
    phases, alerts, events = {}, [], []
    for phase, file, kind in [
        ("S01-context", "S01/context-events.jsonl", "context"),
        ("S01-alerts", "S01/alerts.jsonl", "alert"),
        ("S04-context", "S04/context-events.jsonl", "context"),
        ("S04-alerts", "S04/alerts.jsonl", "alert"),
    ]:
        records = []
        for index, raw in enumerate(
            (E / "input/clean-data-01" / file).read_bytes().splitlines()
        ):
            payload = json.loads(raw)
            name = f"wire/{phase}/{index}.json"
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            record = {"wire": name, "wire_sha256": sha(raw)}
            if kind == "alert":
                canonical, aid = source_wire(payload, fixture["tenant_id"])
                assert canonical == payload
                record.update(alert_id=payload["id"], predicted_canonical_alert_id=aid)
                alerts.append(aid)
            else:
                record["source_event_id"] = payload["event_id"]
                events.append(payload["event_id"])
            records.append(record)
        phases[phase] = {"kind": kind, "records": records}
    sample = json.loads(
        (target / phases["S01-alerts"]["records"][0]["wire"]).read_text()
    )
    profile = {
        **execution,
        "batch_id": config["batch_id"],
        "tenant_id": fixture["tenant_id"],
        "counts": {k: len(v["records"]) for k, v in phases.items()},
        "timeout_seconds": config["timeouts"]["send_seconds"],
        "request_timeout_ms": config["timeouts"]["send_request_timeout_ms"],
        "timeouts": config["timeouts"],
        "directory_page_size": config["directory_page_size"],
        "connector": {
            "id": sample["connector_id"],
            "name": fixture["product_name"],
            "connector_type": sample["connector_type"],
            "category": "custom",
            "is_enabled": False,
        },
        "alert_ids": alerts,
        "event_ids": events,
        "case_titles": config["case_titles"],
        "cleanup_mode": config["cleanup_mode"],
        "prerequisites": config["prerequisites"],
    }
    (target / "profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    )
    files = {
        str(p.relative_to(target)): sha(p.read_bytes())
        for p in target.rglob("*")
        if p.is_file()
    }
    manifest = {
        "batch_id": config["batch_id"],
        "tenant_id": fixture["tenant_id"],
        "phases": phases,
        "files": files,
        "expected_answers_uploaded": False,
        "source_release_sha256": sha((R / config["release_file"]).read_bytes()),
        "source_identity_sha256": sha((R / fixture["candidate_identity"]).read_bytes()),
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": "prepared_not_sent",
                "counts": profile["counts"],
                "frozen_files": len(files),
                "model_calls": 0,
                "kafka_messages": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
