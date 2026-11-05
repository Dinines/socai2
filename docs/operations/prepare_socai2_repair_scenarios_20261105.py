"""Offline material for two additional scenarios per backend; no dispatch.

Reuses closed k2 recipes as source templates and existing context-fixture
identity/serialization helpers. All identities are new. Expected facts are a
separate evaluator-only file and never part of the source event envelopes.
"""
import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from alert_scenarios import _without_answers, json_bytes, sha256
from context_fixture import build as build_context
from investigation_fixture import _identity, _parameters

SOURCE = ROOT / "docs/operations/evidence/socai2-kafka-chain-20261105/k2/plan.json"


def build(batch, window_start):
    assert batch not in {"k1", "k2", "k3", "k4", "repair-k5"}, "closed or sealed batch name"
    source = json.loads(SOURCE.read_text())
    tenant, start = _parameters(batch, source["tenant_id"], window_start)
    assert start.microsecond % 1000 == 0, "use a millisecond-aligned fixture window"
    cases, expected = [], []
    for backend_index, backend in enumerate(("deepseek", "small")):
        for scenario_index, scenario in enumerate(("credential_access", "sparse")):
            ordinal = backend_index * 2 + scenario_index
            original = next(item for item in source["cases"] if item["key"] == backend + "-" + scenario)
            case = deepcopy(original)
            key, host = backend + "-card-" + str(scenario_index + 1), batch + "-endpoint-" + str(ordinal + 1)
            case_start = start + timedelta(minutes=ordinal * 20)
            old_base = datetime.fromisoformat(original["alerts"][0]["event_time"])
            new_base = case_start + timedelta(seconds=60)
            replacements = {original["host"]: host, "k2-" + backend: batch + "-" + backend}
            for value in (original["window_start"], original["window_end"], *[a["event_time"] for a in original["alerts"]]):
                replacements[value] = (new_base + (datetime.fromisoformat(value) - old_base)).isoformat()
            for index, alert in enumerate(original["alerts"]):
                replacements[alert["source_alert_id"]] = _identity(tenant, batch, key + ":alert:" + str(index))
                replacements[alert["external_id"]] = _identity(tenant, batch, key + ":vendor:" + str(index))
                replacements[alert["source_event_ids"][0]] = _identity(tenant, batch, key + ":source-event:" + str(index))
            text = json.dumps(case)
            for before, after in replacements.items():
                text = text.replace(before, after)
            case = json.loads(text)
            case.update(key=key, host=host)
            context, context_expected = build_context(run_id=batch, tenant=tenant, case=case)
            if scenario == "credential_access":
                selected = {_identity(tenant, batch, key + ":process-near"), _identity(tenant, batch, key + ":network-volume")}
                case["events"] += [event for event in context if event["event_id"] in selected]
                nature, truth_eligible = "malicious", True
                facts = ["A0 records a credential-dump command starting successfully, not confirmed memory extraction or completed dump",
                    "A1 records a successful TCP connection to its explicit endpoint, not proven exfiltration or process attribution",
                    "Lake records a nearby child-process start with reported parent PID and a separate 750000-byte outbound flow",
                    "Process ancestry and flow count are source observations; the flow has no originating process or payload proof"]
                forbidden = ["Treat process-start success as completed dump", "Claim bytes prove exfiltration",
                    "Attribute every connection to the dump process", "Invent remote execution or lateral movement"]
            else:
                selected = {item["event_id"] for item in context_expected["excluded"]}
                case["events"] = [event for event in context if event["event_id"] in selected]
                # All physical lake times align to milliseconds. The end-bound
                # control remains exactly W.end; the earlier control is W.start-1s.
                before_id = _identity(tenant, batch, key + ":control-before-window")
                for event in case["events"]:
                    if event["event_id"] == before_id:
                        ocsf = event["ocsf_event"]
                        ocsf["time"] = (case_start - timedelta(seconds=1)).isoformat()
                        raw = json.loads(ocsf["raw_data"])
                        raw["time"] = ocsf["time"]
                        ocsf["raw_data"] = json_bytes(raw).decode()
                nature, truth_eligible = "unknown", False
                facts = ["Two alert observations exist but their source events are not in this bounded lake sample",
                    "Three lake controls exist: other host, before W.start, exactly W.end",
                    "All formal tools at the declared host and [W.start,W.end) have zero matching rows",
                    "Zero matching rows do not refute alert observations or establish benign behavior or authorization"]
                forbidden = ["Read an excluded control as current Case evidence", "Equate available zero rows with unavailable or unexecuted Tool",
                    "Conclude benign because no lake match exists", "Invent authorization or scope-complete collection"]
            included = {"process_activity": [], "network_connections": [], "authentication_activity": []}
            kinds = {1007: "process_activity", 4001: "network_connections", 3002: "authentication_activity"}
            for event in case["events"]:
                _without_answers(event)
                ocsf = event["ocsf_event"]
                when = datetime.fromisoformat(ocsf["time"])
                if ocsf["device"]["name"] == host and case_start <= when < case_start + timedelta(minutes=2):
                    included[kinds[ocsf["class_uid"]]].append(event["event_id"])
            for alert in case["alerts"]:
                _without_answers(alert)
            cases.append(case)
            expected.append({"case_key": key, "scenario": scenario, "backend": backend,
                "behavior_truth": nature, "directional_verdict_denominator_eligible": truth_eligible,
                "truth_basis": "authored synthetic scenario intent, independent of any model output",
                "acceptable_abstention": "needs_review", "observed_facts": facts, "unsupported_claims": forbidden,
                "tool_expected_event_ids": included,
                "excluded_event_ids": [event["event_id"] for event in case["events"]
                    if not any(event["event_id"] in values for values in included.values())],
                "traffic": {event["event_id"]: event["ocsf_event"]["traffic"] for event in case["events"]
                    if event["event_id"] in included["network_connections"] and "traffic" in event["ocsf_event"]}})
    plan = {"batch": batch, "status": "offline_material_only_not_sealed_not_dispatched",
        "tenant_id": tenant, "source_plan_sha256": sha256(SOURCE.read_bytes()),
        "new_alerts": 8, "expected_incidents": 4, "expected_cases": 4,
        "lake_events": sum(len(case["events"]) for case in cases),
        "proposed_max_model_calls": 28, "proposed_max_runs": 16,
        "execution": "Each new card A0,A1,I,one C; no H or second C; root must explicitly select/seal new batch before dispatch",
        "baseline_limits": {"max_tokens": 48000, "max_model_calls": 4, "max_tool_calls": 4, "seconds": 120},
        "pairing": "same observations per scenario; new host/source/time/identity for each backend prevents history contamination",
        "cases": cases}
    oracle = {"audience": "evaluation_only_not_sent_to_models_or_Kafka", "batch": batch, "cases": expected,
        "quality_rule": "Only benign/malicious reversals count as directional errors; needs_review is abstention, not certain correctness. Unknown-truth card excluded from accuracy denominator."}
    return plan, oracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    plan, oracle = build(args.batch, args.window_start)
    args.out.mkdir(parents=True, exist_ok=False)
    files = {"plan.json": json_bytes(plan), "expected.json": json_bytes(oracle)}
    for name, body in files.items():
        (args.out / name).write_bytes(body)
    manifest = {"generator_sha256": sha256(Path(__file__).read_bytes()), "source_plan_sha256": sha256(SOURCE.read_bytes()),
        "files": {name: sha256(body) for name, body in files.items()}, "status": "offline_only", "model_calls": 0, "database_writes": 0}
    (args.out / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"output": str(args.out), "alerts": 8, "lake_events": plan["lake_events"], "model_calls": 0}))


if __name__ == "__main__":
    main()
