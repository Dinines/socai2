"""New local identities from the existing maintenance recipe; no connections."""
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from backend_profile import DEEPSEEK_DEFAULTS, ModelProfileMismatch, freeze
from config import DATABASE, LAKE, ROOT, TENANT, TOPIC

SOURCE = ROOT / "docs/operations/evidence/investigation-repair-20261105/repair-k5/plan.json"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def uid(batch, label):
    return str(uuid5(NAMESPACE_URL, "socai2-local-flow:" + batch + ":" + label))


def source_hashes():
    paths = [p for base in (ROOT / "services/api/app", ROOT / "services/fusion/app") for p in base.rglob("*.py")]
    paths += list((ROOT / "deploy/local-investigation").glob("*.py"))
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(paths)}


def prepare(batch, window_start, *, backend="deepseek", model_values=None, scenario="maintenance", additional_tests=False):
    assert re.fullmatch(r"local-[a-z0-9][a-z0-9-]{1,60}", batch), "new local batch name required"
    if backend == "deployed" and model_values is None:
        raise ModelProfileMismatch("deployed_backend_requires_explicit_local_configuration")
    model_profile = freeze(DEEPSEEK_DEFAULTS if model_values is None else model_values, backend)
    start = datetime.fromisoformat(window_start)
    assert start.tzinfo is not None and start.microsecond == 0
    source = json.loads(SOURCE.read_text())
    original = next(c for c in source["cases"] if c["backend"] == "deepseek" and c["scenario"] == "maintenance")
    old_start = datetime.fromisoformat(original["window_start"])
    replacements = {source["tenant_id"]: TENANT, original["host"]: batch + "-host",
        "repair-k5-deepseek": batch + "-source"}
    for value in (original["window_start"], original["window_end"], *[a["event_time"] for a in original["alerts"]]):
        replacements[value] = (start + (datetime.fromisoformat(value) - old_start)).isoformat()
    for i, alert in enumerate(original["alerts"]):
        replacements[alert["source_alert_id"]] = uid(batch, "alert-" + str(i))
        replacements[alert["external_id"]] = uid(batch, "vendor-" + str(i))
        replacements[alert["source_event_ids"][0]] = uid(batch, "event-" + str(i))
    raw = json.dumps(original)
    for before, after in replacements.items():
        raw = raw.replace(before, after)
    case = json.loads(raw)
    case.update(key=backend + "-maintenance", backend=backend, rounds=2, max_model_calls=11, max_runs=5)
    comparison = None
    if scenario != "maintenance":
        from comparison_fixture import apply
        comparison = apply(case, scenario)
        case["key"] = backend + "-" + scenario
    path = ROOT / "services/fusion/app/models/alert.py"
    spec = importlib.util.spec_from_file_location("local_flow_raw_alert", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    parsed = [module.RawAlert.model_validate(a) for a in case["alerts"]]
    assert len(parsed) == len(case["events"]) == 2 and len({a.correlation_key() for a in parsed}) == 1
    assert all(a["tenant_id"] == TENANT for a in [*case["alerts"], *case["events"]])
    plan = {"batch_id": batch, "tenant_id": TENANT, "database": DATABASE, "lake_database": LAKE,
        "topic_prefix": TOPIC, "case": case, "model_profile": model_profile,
        "canonical_alert_ids": [str(a.deterministic_id()) for a in parsed],
        "max_model_calls": 11, "global_local_model_call_cap": 50, "max_runs": 5, "retries": 0,
        "baseline_limits": {"max_tokens": 48000, "max_model_calls": 4, "max_tool_calls": 4, "seconds": 120},
        "source_recipe": str(SOURCE.relative_to(ROOT)), "source_recipe_sha256": sha(SOURCE.read_bytes()),
        "source_sha256": source_hashes(), "source_environment": "local-standalone", "input_kind": "synthetic",
        "phase_order": ["ingest", "first", "root_semantic_review", "second", "export"],
        "human_source": "fixed_synthetic_driver_not_real_employee"}
    oracle = {"audience": "evaluation_only_not_sent_to_models_or_page", "batch_id": batch,
        "behavior_truth": "benign", "truth_scope": "A0 authorized maintenance only; A1 authorization unknown",
        "acceptable_abstention": "needs_review", "authorization_available_after_H_only": True,
        "tool_expected_event_ids": {"process_activity": [case["events"][0]["event_id"]],
            "network_connections": [case["events"][1]["event_id"]], "authentication_activity": []},
        "unsupported_claims": ["process start proves script completion", "network connection proves exfiltration",
            "shared host proves process attribution", "A0 human authorization applies to A1"],
        "quality_rule": "Only benign/malicious reversals are directional errors; needs_review is abstention, not correctness."}
    if comparison:
        oracle.update(comparison)
        plan["phase_order"] = ["ingest", "first", "export", "root_semantic_review"]
        upstream = ROOT / "tools/testdata/upstream/generate_eval_incidents.py"
        plan["comparison_source"] = {"path": str(upstream.relative_to(ROOT)), "sha256": sha(upstream.read_bytes())}
    if additional_tests:
        # User requested a separate three-case test batch on 2026-11-06.
        # Preserve the previous 48 attempts; 21 additional attempts means an
        # absolute ceiling of 69, without recycling the old unused allowance.
        assert backend == "deepseek" and scenario in {"routine", "credential", "impact"}
        assert batch in {"local-eval-20261106-01", "local-eval-20261106-02", "local-eval-20261106-03"}
        plan.update(global_local_model_call_cap=69, max_model_calls=7, max_runs=4,
            campaign="additional-tests-20261106", previous_attempts=48, additional_attempt_cap=21)
        case.update(max_model_calls=7, max_runs=4)
    return plan, oracle
