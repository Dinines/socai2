"""Freeze repair-k6 six synthetic cards locally; no network or execution."""
import argparse
import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from prepare_socai2_repair_scenarios_20261105 import ROOT, build, sha256

BATCH = "repair-k6"
OUT = ROOT / "docs/operations/evidence/investigation-repair-20261105" / BATCH


def uid(label):
    return str(uuid5(NAMESPACE_URL, "socai2-repair-k6-20261105:" + label))


def prepare(candidate, window_start):
    candidate = candidate.resolve()
    assert candidate.is_relative_to(ROOT / ".local/releases") and candidate.name.startswith("next-")
    manifest = json.loads((candidate / "manifest.json").read_text())
    for name, value in manifest["files"].items():
        p = candidate / name
        assert p.resolve().is_relative_to(candidate) and not p.is_symlink()
        assert sha256(p.read_bytes()) == value["sha256"] and p.stat().st_size == value["bytes"]
    assert '"socai2.baseline-executor.v2"' in (candidate / "app/socai2/baseline_contracts.py").read_text()
    assert "max_tokens=48000" in (candidate / "app/socai2/case_service.py").read_text()
    start = datetime.fromisoformat(window_start)
    assert start.tzinfo is not None and start.microsecond == 0
    extra, oracle = build(BATCH, (start + timedelta(minutes=20)).isoformat())
    old_path = ROOT / "docs/operations/evidence/investigation-repair-20261105/repair-k5/plan.json"
    old = json.loads(old_path.read_text())
    cases, expectations = [], []
    for n, backend in enumerate(("deepseek", "small")):
        original = next(c for c in old["cases"] if c["backend"] == backend)
        key, host = backend + "-card-1", BATCH + "-endpoint-maint-" + str(n)
        target = start + timedelta(minutes=100 * n)
        source = datetime.fromisoformat(original["window_start"])
        replacements = {original["host"]: host, "repair-k5-" + backend: BATCH + "-" + backend}
        for t in [original["window_start"], original["window_end"], *[a["event_time"] for a in original["alerts"]]]:
            replacements[t] = (target + (datetime.fromisoformat(t) - source)).isoformat()
        for i, alert in enumerate(original["alerts"]):
            for field, kind in [("source_alert_id", "alert"), ("external_id", "vendor")]:
                replacements[alert[field]] = uid(key + ":" + kind + ":" + str(i))
            replacements[alert["source_event_ids"][0]] = uid(key + ":event:" + str(i))
        body = json.dumps(original)
        for before, after in replacements.items():
            body = body.replace(before, after)
        case = json.loads(body)
        case.update(key=key, host=host, max_model_calls=11, max_runs=5, rounds=2)
        cases.append(case)
        expectations.append({"case_key": key, "backend": backend, "scenario": "maintenance",
            "behavior_truth": "benign", "truth_scope": "A0 authorized maintenance only; A1 authorization unknown",
            "initial_evidence": "Authorization withheld until narrowly scoped H after root review",
            "tool_expected_event_ids": {"process_activity": [case["events"][0]["event_id"]],
                "network_connections": [case["events"][1]["event_id"]], "authentication_activity": []},
            "excluded_event_ids": [], "unsupported_claims": ["process start proves script completion",
                "network connection proves process attribution or exfiltration", "A0 H authorizes A1"]})
        for index, item in enumerate([c for c in extra["cases"] if c["backend"] == backend], start=2):
            entry = deepcopy(item)
            prior_key = entry["key"]
            entry.update(key=backend + "-card-" + str(index), max_model_calls=7, max_runs=4, rounds=1)
            cases.append(entry)
            expected = deepcopy(next(e for e in oracle["cases"] if e["case_key"] == prior_key))
            expected["case_key"] = entry["key"]
            expectations.append(expected)
    assert len(cases) == 6 and sum(len(c["events"]) for c in cases) == 18
    # Canonical correlation keys are checked without touching Redis or a service.
    spec = importlib.util.spec_from_file_location("repair_alert_model", candidate / "fusion/app/models/alert.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    keys = [{module.RawAlert.model_validate(a).correlation_key() for a in c["alerts"]} for c in cases]
    assert all(len(k) == 1 for k in keys) and len(set.union(*keys)) == 6
    plan = {"batch": BATCH, "tenant_id": old["tenant_id"], "release": candidate.name, "image": manifest["image"],
        "candidate_manifest_sha256": sha256((candidate / "manifest.json").read_bytes()),
        "candidate_files": {n: v["sha256"] for n, v in manifest["files"].items()},
        "source_k5_plan_sha256": sha256(old_path.read_bytes()), "source_k2_plan_sha256": extra["source_plan_sha256"],
        "new_alerts": 12, "new_incidents": 6, "new_cases": 6, "lake_events": 18,
        "max_model_calls": 50, "max_runs": 26, "retries": 0,
        "baseline_limits": old["baseline_limits"], "ai_limits": old["ai_limits"],
        "initial_analysis_schema": old["initial_analysis_schema"],
        "final_reanalysis_proposal_schema": old["final_reanalysis_proposal_schema"],
        "topic_prefix": "socai2.validation.repair-k6.20261105", "group": "socai2-validation-repair-k6-20261105",
        "lake_access": "server-only CH management connection, frozen worker exact validation.raw_events INSERT and event IDs; no grants changed",
        "gate": "Core review binds candidate and plan. Readback must pass before models. Only maintenance may run H/second C after root semantic review.",
        "quality_rule": oracle["quality_rule"], "cases": cases}
    return plan, {"audience": "evaluation_only_not_sent_to_models_or_Kafka", "batch": BATCH,
                  "cases": expectations, "quality_rule": oracle["quality_rule"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    plan, oracle = prepare(args.candidate, args.window_start)
    args.out.mkdir(parents=True, exist_ok=False)
    files = {"plan.json": json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
             "expected.json": json.dumps(oracle, ensure_ascii=False, indent=2) + "\n"}
    for name in ["repair_k6_remote_20261105.py", "repair_k6_child_20261105.py"]:
        files[name] = (ROOT / "deploy/aisoc21" / name).read_text()
    for name, body in files.items():
        (args.out / name).write_text(body)
    (args.out / "manifest.json").write_text(json.dumps({n: sha256(b.encode()) for n, b in files.items()}, indent=2) + "\n")
    print(json.dumps({"packet": str(args.out), "cards": 6, "alerts": 12, "lake_events": 18,
                      "max_model_calls": 50, "executed_models": 0, "uploaded": False}))


if __name__ == "__main__":
    main()
