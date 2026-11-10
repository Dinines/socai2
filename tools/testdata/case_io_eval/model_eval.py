"""Two frozen C3 requests; one attempt each, no business DB or tool execution."""
import argparse
import json
import shlex
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from .audit import ROOT, initialize, read, sha


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def remote(config, request):
    cfg = config["transport"]
    worker = Path(__file__).with_name("model_worker.py").read_text()
    task = {**request, "transport": cfg, "hidden_message_fields": config["hidden_message_fields"]}
    argv = [cfg["ssh_binary"], "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "UpdateHostKeys=no", "-o", f"ConnectTimeout={cfg['connect_timeout_seconds']}", cfg["ssh_target"],
            shlex.join([cfg["remote_python"], "-c", worker])]
    start = time.monotonic()
    try:
        result = subprocess.run(argv, input=json.dumps(task, ensure_ascii=False), capture_output=True,
                                text=True, timeout=cfg["command_timeout_seconds"], check=False)
    except subprocess.TimeoutExpired:
        return {"state": "transport_unknown_no_retry", "error_type": "TimeoutExpired"}
    if result.returncode:
        return {"state": "transport_unknown_no_retry", "exit_code": result.returncode, "error": result.stderr[:500]}
    try:
        value = json.loads(result.stdout)
    except ValueError:
        return {"state": "transport_unknown_no_retry", "error_type": "invalid_transport_json"}
    value["transport_seconds"] = round(time.monotonic() - start, 6)
    return value


def prepare(config, config_path, output):
    from app.socai2.runtime_policy import active_policy

    from .fixtures import load
    from .output_adapter import schema

    directory = ROOT / config["candidate"]
    prior_plan = read(directory / "next-model-comparison-plan.json")
    candidate = read(directory / "config.json")
    sample = load(ROOT, candidate)
    policy = active_policy()
    assert config["variants"] == prior_plan["variants"] == ["before", "after"]
    assert config["planned_model_calls"] == prior_plan["proposed_calls"] == 2 and config["retries"] == 0
    cells, files = [], [config_path, directory / "next-model-comparison-plan.json", directory / "config.json",
                        ROOT / candidate["snapshot"], ROOT / candidate["policy"]]
    for variant in config["variants"]:
        wire = directory / "token-capacity" / f"{variant}-prepared-request-not-sent.json"
        assert sha(wire) == prior_plan["wire_files_sha256"][wire.name], "frozen_wire_changed"
        source = ROOT / candidate["comparison_candidate"] if variant == "before" else directory
        ledger_path = source / "input-ledger.json"
        ledger, body = read(ledger_path), read(wire)
        assert body["messages"][1]["content"] == ledger["user"]
        assert body["model"] == policy.model.alias and body["max_tokens"] == policy.model.output_tokens["C3"]
        cells.append({"id": variant, "body": body, "prepared": ledger,
                      "canonical_schema": schema(ledger, sample["context"], sample["request"]["binding_map"])})
        files += [wire, ledger_path]
    left, right = cells
    assert left["body"]["messages"][0] == right["body"]["messages"][0]
    assert {k: v for k, v in left["body"].items() if k != "messages"} == {
        k: v for k, v in right["body"].items() if k != "messages"}
    assert left["canonical_schema"] == right["canonical_schema"]
    keys = ("id", "ref", "alert_ids", "original_value", "value", "original_scope")
    assert [{k: r.get(k) for k in keys} for r in left["prepared"]["records"]] == [
        {k: r.get(k) for k in keys} for r in right["prepared"]["records"]]
    files += list(Path(__file__).parent.glob("*.py"))
    files += list((ROOT / "services/api/app/socai2").glob("*.py"))
    files += [ROOT / "tools/testdata/incident_integration/run.py", ROOT / candidate["runtime_config"]]
    output.mkdir(parents=True, exist_ok=False)
    for cell in cells:
        wire = directory / "token-capacity" / f"{cell['id']}-prepared-request-not-sent.json"
        (output / f"{cell['id']}-request.json").write_bytes(wire.read_bytes())
    save(output / "plan-and-packets.json", {
        "state": "prepared_no_generation", "batch": config["batch"], "config": config,
        "cells": cells, "context": sample["context"], "bindings": sample["request"]["binding_map"],
        "timeout_seconds": policy.single_model_timeout_seconds,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "request_sha256": {f"{c['id']}-request.json": sha(output / f"{c['id']}-request.json") for c in cells},
        "source_run_id": candidate["source_run_id"], "controls": prior_plan["controls"],
        "checks": prior_plan["checks"], "planned_model_calls": 2, "retries": 0,
        "scope": "frozen C3 model boundary; no business tool, DB connection, new Run/Case or deployment",
        "query_supplement_was_in_original_c1": False})
    print(json.dumps({"state": "prepared_no_generation", "planned_model_calls": 2,
                      "timeout_seconds": policy.single_model_timeout_seconds, "sources_each": len(left["prepared"]["records"])}))


def validate_plan(config, output):
    plan = read(output / "plan-and-packets.json")
    assert config == plan["config"], "config_changed"
    assert all(sha(ROOT / p) == h for p, h in plan["source_sha256"].items()), "prepared_source_changed"
    assert all(sha(output / p) == h for p, h in plan["request_sha256"].items()), "prepared_request_changed"
    assert all(read(output / f"{c['id']}-request.json") == c["body"] for c in plan["cells"])
    return plan


def check_route(config, value):
    assert value.get("state") == "ready", "preflight_not_ready"
    assert all(value.get(k) == v for k, v in config["expected_route"].items()), "unexpected_model_route"


def preflight(config, output):
    validate_plan(config, output)
    result = remote(config, {"phase": "preflight", "timeout_seconds": config["preflight_timeout_seconds"]})
    save(output / "preflight.json", result)
    print(json.dumps(result), flush=True)
    check_route(config, result)


def run(config, output):
    plan = validate_plan(config, output)
    before = read(output / "preflight.json")
    check_route(config, before)
    save(output / "batch-intent.json", {"started_at": datetime.now(UTC).isoformat(),
        "plan_sha256": sha(output / "plan-and-packets.json"), "planned_model_calls": 2, "retries": 0})
    for cell in plan["cells"]:
        save(output / "calls" / f"{cell['id']}-intent.json", {"attempt": 1,
            "request_file_sha256": plan["request_sha256"][f"{cell['id']}-request.json"]})
        result = remote(config, {"phase": "call", "cell": cell["id"], "body": cell["body"],
                                 "timeout_seconds": plan["timeout_seconds"]})
        save(output / "calls" / f"{cell['id']}-result.json", result)
        print(json.dumps({"cell": cell["id"], "state": result["state"], "seconds": result.get("http_seconds"),
                          "usage": result.get("raw", {}).get("usage")}), flush=True)
        if "unknown" in result["state"]:
            return
    after = remote(config, {"phase": "preflight", "timeout_seconds": config["preflight_timeout_seconds"]})
    save(output / "completion.json", {"finished_at": datetime.now(UTC).isoformat(), "after": after,
        "runtime_unchanged": after.get("runtime_sha256") == before["runtime_sha256"],
        "route_unchanged": all(after.get(k) == before.get(k) for k in config["expected_route"])})


def assess(result, cell, context, bindings):
    from app.socai2 import baseline_analysis_contract as contract
    from app.socai2.analysis_review import Review
    from app.socai2.baseline_analysis_model import usage
    from app.socai2.baseline_context import Context
    from jsonschema import ValidationError as SchemaError

    from .output_adapter import canonical, parse

    raw = result.get("raw", {})
    review = {"cell": cell["id"], "state": result["state"], "usage": usage(raw),
              "http_seconds": result.get("http_seconds"), "strict_accepted": False, "partial": None,
              "quality": "requires_semantic_review"}
    choices = raw.get("choices") or []
    if result["state"] != "response_received" or len(choices) != 1:
        return {**review, "error": "no_single_visible_answer"}
    choice = choices[0]
    review["finish_reason"] = choice.get("finish_reason")
    if choice.get("finish_reason") != "stop":
        return {**review, "error": "incomplete_generation"}
    content = choice.get("message", {}).get("content")
    if not isinstance(content, str):
        return {**review, "error": "missing_visible_content"}
    try:
        restored = canonical(content, cell["prepared"], context, bindings)
    except (ValueError, KeyError, TypeError, SchemaError) as exc:
        return {**review, "error": "canonical_schema_or_identity_invalid", "error_type": type(exc).__name__,
                "schema_path": list(exc.absolute_path) if isinstance(exc, SchemaError) else None}
    review["canonical_schema_valid"] = True
    try:
        parsed = parse(content, cell["prepared"], context, bindings)
        review.update(strict_accepted=True, restored=parsed.model_dump(mode="json"))
    except contract.AnalysisRejected as exc:
        review["error"] = str(exc)
        partial = Review("C3", cell["prepared"]["source_map"], Context.model_validate(context),
                         cell["prepared"]["coverage"], bindings=bindings)
        try:
            partial.partial(json.dumps(restored, ensure_ascii=False))
            review["partial"] = partial.details
        except contract.AnalysisRejected as partial_error:
            review["partial_error"] = str(partial_error)
    return review


def review(config, output):
    plan = validate_plan(config, output)
    results = [assess(read(output / "calls" / f"{cell['id']}-result.json"), cell, plan["context"], plan["bindings"])
               for cell in plan["cells"] if (output / "calls" / f"{cell['id']}-result.json").exists()]
    save(output / "structural-review.json", {"batch": config["batch"], "results": results,
        "limitations": ["schema_and_reference_validity_do_not_prove_factual_truth",
            "canonical_schema_rejection_not_silently_repaired_for_partial_review", "no_independent_verdict_ground_truth"]})
    print(json.dumps([{k: r.get(k) for k in ("cell", "state", "strict_accepted", "error", "usage", "http_seconds")} for r in results]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "preflight", "run", "review"))
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("evaluation.json"))
    args = parser.parse_args()
    config = read(args.config)
    candidate = read(ROOT / config["candidate"] / "config.json")
    runtime = initialize(candidate)
    config["transport"] = {**runtime["transport"], **config["transport_overrides"]}
    output = ROOT / config["output"]
    if args.phase == "prepare":
        prepare(config, args.config, output)
    else:
        {"preflight": preflight, "run": run, "review": review}[args.phase](config, output)


if __name__ == "__main__":
    main()
