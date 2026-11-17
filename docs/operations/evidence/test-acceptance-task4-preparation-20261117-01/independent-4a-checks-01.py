"""Independent offline recomputation of the frozen task4a package; no execution."""
import copy
import hashlib
import json
import re
import socket
import sys
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "docs/operations/evidence/acceptance-fullflow-20261117-01"
OUT = Path(__file__).with_suffix(".json")
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools/testdata"))
CHECKS = []
NETWORK = []


def no_network(*args, **kwargs):
    NETWORK.append("attempt")
    raise AssertionError("independent task4a review is offline")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network
socket.getaddrinfo = no_network


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def verify(name, condition, detail=None):
    CHECKS.append({"check": name, "passed": bool(condition), "detail": detail})
    assert condition, name


def freeze_check(root, items):
    return all(
        (root / r["path"]).is_file()
        and not (root / r["path"]).is_symlink()
        and digest(root / r["path"]) == r["sha256"]
        and ("size" not in r or (root / r["path"]).stat().st_size == r["size"])
        for r in items
    )


def without_observed(value):
    if isinstance(value, dict):
        return {k: without_observed(v) for k, v in value.items() if k != "observed_at"}
    if isinstance(value, list):
        return [without_observed(v) for v in value]
    return value


def main():
    frozen = read(BASE / "preparation-freeze-01.json")
    runtime_path = ROOT / "docs/operations/evidence/acceptance-docker-20261117-01/runtime-freeze-02/manifest.json"
    runtime = read(runtime_path)
    verify("44 frozen files size and SHA", len(frozen["files"]) == 44 and freeze_check(BASE, frozen["files"]))
    verify("32 prior Docker delivery files unchanged", len(runtime["files"]) == 32 and freeze_check(ROOT, runtime["files"]))
    author = read(BASE / "config/authoring.json")
    authored = read(BASE / "authoring-receipt.json")
    profile = read(BASE / "config/profile.json")
    execution = read(BASE / "config/execution.json")
    prepared = BASE / "results/prepared"
    session = read(prepared / "session.json")
    scenario = read(BASE / "materials/scenario.json")
    relative = [r["target"] for r in author["selection"]]
    materials = {p: read(BASE / "materials" / p) for p in relative}
    wires = {p: read(prepared / "wire" / p) for p in relative}
    verify("one incident Case and two explicit material parts",
           scenario == author["scenario"] == read(prepared / "wire/scenario.json")
           and scenario["parts"] == [{"id": p, "check_level": "case", "context_required": True} for p in ("part1", "part2")]
           and len(scenario["cases"]) == 1
           and {k: scenario["cases"][0][k] for k in ("scope", "create_after_part", "check_after_parts", "alert_refs")}
           == {"scope": "incident", "create_after_part": "part1", "check_after_parts": ["part2"], "alert_refs": ["part1/alerts/001.json"]}
           and len(relative) == len(set(relative)) == 5)
    # Recreate only the author's source observations in memory, not its output script.
    from streaming_fixture import build
    _, _, generated, _ = build(author["generator_config"])
    for selection, receipt in zip(author["selection"], authored["records"], strict=True):
        source = json.loads(generated[selection["source"]].splitlines()[selection["line"] - 1])
        assert hashlib.sha256(encoded(source)).hexdigest() == receipt["generator_record_sha256"]
        expected = copy.deepcopy(source)
        expected["connector_id"] = author["registered_connector_id"]
        assert encoded(expected) == (BASE / "materials" / selection["target"]).read_bytes()
        assert digest(BASE / "materials" / selection["target"]) == receipt["material_sha256"]
        assert receipt["source_binding"]["from"] == source["connector_id"]
    verify("five author selections reproduce original business values",
           digest(ROOT / "tools/testdata/streaming_fixture.py") == authored["generator_sha256"]
           and digest(BASE / "config/authoring.json") == authored["authoring_config_sha256"],
           "Only the declared connector binding changes; no old result or model output is used.")
    namespace = uuid5(NAMESPACE_URL, f"socai2.acceptance:{profile['tenant_id']}:{execution['execution_id']}")
    event_map = {v["event_id"]: str(uuid5(namespace, "event:" + v["event_id"]))
                 for p, v in materials.items() if "/context/" in p}
    assert len(event_map) == 3 and session["event_identity_map"] == event_map
    assert session["namespace"] == str(namespace)
    assert session["profile"] == profile and session["execution"] == execution
    assert session["source_directory"] == "/materials" and session["execution_status"] == "prepared_not_executed"
    assert execution["time_policy"] == "preserve"
    canonical_ids, correlation_keys = [], []

    def remap_event(event):
        result = copy.deepcopy(event)
        for target in (result, result["metadata"]):
            target["uid"] = event_map[target["uid"]]
        if "raw_data" in result:
            nested = json.loads(event["raw_data"])
            assert "raw_data" not in nested
            for target in (nested, nested["metadata"]):
                target["uid"] = event_map[target["uid"]]
            result["raw_data"] = encoded(nested).decode()
        return result

    for path, material in materials.items():
        expected = copy.deepcopy(material)
        entry = session["identities"][path]
        if "/alerts/" in path:
            new_id = str(uuid5(namespace, "alert:" + material["id"]))
            expected.update(id=new_id, source_alert_id=new_id,
                            source_event_ids=[event_map[v] for v in material["source_event_ids"]])
            expected["raw_event"]["ocsf_event"] = remap_event(material["raw_event"]["ocsf_event"])
            fields = {k: expected[k] for k in ("identity_version", "tenant_id", "source", "connector_id", "source_alert_id")}
            fingerprint = hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()
            canonical_id = str(uuid5(UUID("a15c0c00-0000-5568-a150-c000000a1e77"), f"{profile['tenant_id']}:{fingerprint}"))
            key = profile["tenant_id"] + ":entity-v2:" + json.dumps(["ip", expected["src_ip"], None], separators=(",", ":"))
            assert entry == {"kind": "alert", "source_id": material["id"], "source_alert_id": new_id,
                             "predicted_canonical_alert_id": canonical_id, "correlation_key": key}
            canonical_ids.append(canonical_id)
            correlation_keys.append(key)
        else:
            expected["event_id"] = event_map[material["event_id"]]
            expected["ocsf_event"] = remap_event(material["ocsf_event"])
            assert entry == {"kind": "context", "source_id": material["event_id"], "event_id": expected["event_id"]}
        assert encoded(expected) == (prepared / "wire" / path).read_bytes(), path
        assert digest(BASE / "materials" / path) == session["source_material_sha256"][path]
        assert digest(prepared / "wire" / path) == session["wire_sha256"][path]
    verify("independent UUID, canonical ID and exact wire reconstruction",
           len(set(canonical_ids)) == 2 and len(set(correlation_keys)) == 1,
           "All five wire files equal the independently rebuilt bytes; business fields, times and process identities remain.")
    for label, records in (("original", materials), ("wire", wires)):
        contexts = {v["event_id"]: (p, v["ocsf_event"]) for p, v in records.items() if "/context/" in p}
        for path, v in records.items():
            if "/alerts/" in path:
                for source in v["source_event_ids"]:
                    source_path, source_event = contexts[source]
                    assert int(source_path.split("/")[0][4:]) <= int(path.split("/")[0][4:])
                    assert v["raw_event"]["ocsf_event"] == source_event
        parent = records["part1/context/001.json"]["ocsf_event"]
        child = records["part1/context/002.json"]["ocsf_event"]
        network = records["part2/context/001.json"]["ocsf_event"]
        assert parent["process"]["uid"] == child["process"]["parent_process"]["uid"]
        assert parent["process"]["pid"] == child["process"]["parent_process"]["pid"]
        assert parent["activity"]["action"] == child["activity"]["action"] == "process_start"
        assert network["activity"]["action"] == "network_flow_observed"
        assert parent["time"] < child["time"] < network["time"]
        assert network["sensor_observation"]["connection_reset"] is False
        assert network["sensor_observation"]["dns_answers"] == []
        assert type(network["activity_id"]) is int and network["activity_id"] == 0
        hosts = set()
        for path, value in records.items():
            event = value.get("ocsf_event") or value["raw_event"]["ocsf_event"]
            assert value["tenant_id"] == event["tenant_uid"] == profile["tenant_id"]
            assert value["connector_id"] == author["registered_connector_id"]
            hosts.add(event["device"]["name"])
            content = encoded(value).decode().lower()
            assert not any(marker.lower() in content for marker in
                           (execution["execution_id"], "expected_verdict", "is_test", "synthetic", "fixture", "测试"))
        assert len(hosts) == 1
    verify("original and wire relationships, neutral controls and significant false/zero/empty values", True,
           "Parent/child process relationship and same-host later network observation; no unsupported causal claim.")
    from acceptance_materials import inspect_package
    from acceptance_session import load_execution
    from acceptance_status import session_status
    from acceptance_report import execution_report
    from acceptance_report_render import render_report
    checked_profile, loaded = load_execution(prepared)
    assert loaded == session
    assert inspect_package(BASE / "materials", checked_profile) == read(BASE / "results/inspection.json")
    assert inspect_package(prepared / "wire", checked_profile) == session["plan"]
    status = session_status(prepared)
    report, exports = execution_report(prepared)
    saved_status = read(BASE / "results/status.json")
    saved_report = read(BASE / "results/report01/report.json")
    assert without_observed(status) == without_observed(saved_status)
    assert without_observed(report) == without_observed(saved_report) and not exports
    assert render_report(saved_report, prepared, BASE / "results/report01").encode() == (BASE / "results/report01/report.md").read_bytes()
    start, end = read(BASE / "results/console01/start.json"), read(BASE / "results/console01/end.json")
    assert without_observed(start["observation"]) == without_observed(saved_status)
    assert {r["planned_counts"]["alerts"] for r in report["parts"]} == {1}
    assert [r["planned_counts"]["context"] for r in report["parts"]] == [2, 1]
    assert all(r["recorded_state"] == "not_started" and not r["closure_verified"] and
               r["recorded_sent"] == {"alerts": 0, "context": 0} for r in report["parts"])
    assert report["state"] == "ready" and not report["all_parts_completed"] and not report["live_state_verified"]
    assert not report["environment"]["connections_checked"] and all(v == 0 for v in report["counts"].values())
    assert not report["subjects"] and report["models"]["request_count"] == 0 and report["models"]["cost"] is None
    assert end["execution_attempts"] == 0 and end["reason"] == "eof" and not end["permanently_closed"]
    assert end["unsent_parts"] == ["part1", "part2"] and not (prepared / "runs").exists()
    verify("same execution status, EOF and report independently recomputed", True,
           "ready is saved-file state only; no business records, attempts or model calls, no completion claim.")
    manifest = read(BASE / "results/report01/manifest.json")
    verify("report export manifest and prepared source hashes",
           freeze_check(BASE / "results/report01", manifest["files"])
           and all(digest(prepared / x["path"]) == x["sha256"] for x in manifest["sources"]))
    config = read(BASE / "config/offline-docker.json")
    env = dict(line.split("=", 1) for line in (BASE / "config/offline.env").read_text().splitlines() if line and not line.startswith("#"))
    image_review = read(ROOT / "docs/operations/evidence/acceptance-docker-20261117-01/independent-runtime-review-01.json")
    assert env["ACCEPTANCE_IMAGE"] == config["image_reference"] == image_review["delivery"]["repo_digest"]
    assert config["network"] == env["ACCEPTANCE_NETWORK"] == "none"
    assert env["ACCEPTANCE_USER"] == "501:20" and env["ACCEPTANCE_PLATFORM"] == "linux/amd64"
    assert Path(config["compose"]).read_bytes() == (ROOT / "deploy/investigation-test/acceptance.compose.yml").read_bytes()
    for name, folder in (("MATERIALS", "materials"), ("CONFIG", "config"), ("RESULTS", "results")):
        assert Path(env[f"ACCEPTANCE_{name}_DIR"]).resolve() == (BASE / folder).resolve()
    assert not any((BASE / "config" / (key + ".json")).exists() for key in ("http", "kafka", "postgres", "lake"))
    containers = []
    for n, command in enumerate(("inspect", "prepare", "status", "session", "report"), 1):
        receipt = read(BASE / f"offline-command-{n:02d}.json")
        args = receipt["command"]
        assert receipt["exit_code"] == 0 and args[args.index("acceptance") + 1] == command
        assert args[args.index("--env-file") + 1] == str(BASE / "config/offline.env")
        assert args[args.index("-f") + 1] == config["compose"]
        assert "--rm" in args and "-T" in args
        found = re.findall(r"Container (\S+) Creating", receipt["stderr"])
        assert len(found) == 1
        containers.extend(found)
    verify("five existing actual Docker receipts bound to 3d04 and offline mounts",
           len(set(containers)) == 5,
           "Independent receipt/config readback; no additional Docker invocation in this review.")
    observed = read(BASE / "current-environment-03.json")
    observed_config = read(BASE / "config/current-environment.json")
    result = observed["processing"]["result"]
    assert set(observed_config["alert_ids"]) == set(canonical_ids)
    assert set(observed_config["source_event_ids"]) == set(event_map.values())
    assert observed_config["correlation_keys"] == sorted(set(correlation_keys))
    assert result["target"] == {"database": observed_config["expected_database"], "role": observed_config["expected_database_user"]}
    assert result["tenant_id"] == profile["tenant_id"] == observed_config["tenant_id"]
    connector = result["connector"]
    assert connector["id"] == author["registered_connector_id"] == observed_config["connector_id"]
    assert connector["tenant_id"] == profile["tenant_id"]
    assert connector["connector_type"] == author["generator_config"]["source_namespace"] == observed_config["connector_type"]
    assert connector["is_enabled"] is False and result["checks"]["registered_connector_matches_config"] is False
    assert result["transaction_read_only"] and not result["in_flight_at_observation"]
    assert result["new_scope_collision_counts"] == {"new_alert_ids_present": 0, "new_source_ids_present": 0, "historical_correlation_members": 0}
    assert all(v["status_code"] == 200 for v in observed["health"].values())
    assert observed["services_before"] == observed["services_after"] and observed["service_lifecycle_unchanged"]
    assert result["dispatch_max_running_tasks"] == 1
    limits = result["policy_numeric_token_limits"]
    assert limits["model.context_tokens"] == 65536 and limits["case.max_total_tokens"] == 393216
    assert limits["alert_basic.max_total_tokens"] == limits["incident_diagnosis.max_total_tokens"] == 131072
    assert [limits[f"model.output_tokens.{k}"] for k in ("A", "I", "Deep", "C3", "C6")] == [8192,8192,8192,16384,16384]
    assert observed["source_matches_local_candidate"] == {"case_incident_material": False, "viewer.js": False}
    assert not observed["ready_to_execute"]
    assessment = read(BASE / "preparation-assessment.json")
    assert assessment["observation_sha256"] == digest(BASE / assessment["actual_environment_observation"])
    assert assessment["registered_source_id_tenant_type_match"] and not assessment["collector_is_enabled_observed"]
    assert not assessment["ready_to_execute"] and not frozen["ready_to_execute"]
    assert all(digest(ROOT / row["path"]) == row["sha256"] for row in assessment["source_registration_rule"]["sources"])
    assert assessment["existing_runtime_freeze"]["sha256"] == digest(runtime_path)
    verify("21 read-only observation matches this prepared identity and preserves target differences", True,
           "Rechecks receipt only. Collision queries cover PG alerts/source_refs/incident members; lake/Redis/final Docker connectivity are not verified.")
    first = read(BASE / "current-environment-01.json")["processing"]["result"]
    second = read(BASE / "current-environment-02.json")["processing"]["result"]
    verify("prior readonly probe failures retained", first["error_type"] == "UndefinedColumnError" and second["error_type"] == "AssertionError")
    verify("freeze and prior runtime still unchanged after recomputation",
           freeze_check(BASE, frozen["files"]) and freeze_check(ROOT, runtime["files"]) and not NETWORK)
    return {"status": "passed", "scope": "task4a frozen files and current-target receipt review only",
            "reviewed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "checks": CHECKS, "preparation_freeze_sha256": digest(BASE / "preparation-freeze-01.json"),
            "review_driver_sha256": digest(Path(__file__)), "frozen_files": 44, "prior_runtime_files": 32,
            "material_records": 5, "reviewed_docker_receipts": 5, "new_docker_commands": 0,
            "independent_connections_to_21": 0, "network_attempts": len(NETWORK),
            "new_business_writes": 0, "kafka_sends": 0, "new_model_calls": 0,
            "ready_to_execute": False}


if __name__ == "__main__":
    assert not OUT.exists(), "use a new independent output; never overwrite"
    try:
        value = main()
    except Exception as exc:
        value = {"status": "failed", "checks": CHECKS, "error_type": type(exc).__name__, "error": str(exc),
                 "network_attempts": len(NETWORK), "ready_to_execute": False}
        OUT.write_bytes(encoded(value))
        raise
    OUT.write_bytes(encoded(value))
    print(json.dumps({k: value[k] for k in ("status", "frozen_files", "material_records", "reviewed_docker_receipts", "ready_to_execute")}))
