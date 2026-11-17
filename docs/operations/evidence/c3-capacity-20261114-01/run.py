"""One frozen C3 packet at two configured output caps; no business DB or tools."""
import argparse
import asyncio
import copy
import json
import os
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api")]
from tools.testdata.case_io_eval.model_eval import check_route, remote, save
from tools.testdata.incident_integration.run import read, sha


def initialize():
    cfg = read(HERE / "config.json")
    source = read(ROOT / cfg["source_batch"] / "config.json")
    os.environ.update(read(ROOT / source["environment_file"]))
    os.environ.update(source["runtime_overrides"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / cfg["policy"])
    runtime = {**source, "transport": {**read(ROOT / source["transport_config"])["transport"],
                                      "remote_evidence_dir": cfg["remote_evidence_dir"]}}
    return cfg, runtime


def prepare(cfg, runtime):
    from app.socai2.baseline_context import Context
    from app.socai2.baseline_execution_schema import compact_execution_wire
    from app.socai2.case_output_adapter import output_format
    from app.socai2.model_protocol import prepare_request
    from app.socai2.runtime_policy import active_policy

    source = ROOT / cfg["source_batch"] / "flow" / cfg["source_scenario"]
    db = read(source / "export/database.json")
    rid = read(source / "execution.json")["run_id"]
    steps = {row["id"]: row for row in db["run_steps"] if row["run_id"] == rid}
    artifacts = {row["id"]: row for row in db["artifacts"]}
    request = next(a["content_json"]["payload"] for a in artifacts.values()
                   if a.get("run_id") == rid and a["kind"] == "model_request"
                   and steps[a["step_id"]]["stage_code"] == "C3")
    context = next(a["content_json"] for a in artifacts.values() if a.get("run_id") == rid
                   and a["kind"] == "source_snapshot" and "alerts" in (a["content_json"] or {}))
    prepared = artifacts[request["input_view_id"]]["content_json"]
    body = read(source / "calls/call-1-intent.json")["body"]
    policy = active_policy()
    assert body == request["body"] and request["source_map"] == prepared["source_map"]
    canonical = output_format(prepared, Context.model_validate(context), request["binding_map"])
    rebuilt = compact_execution_wire(prepare_request(SimpleNamespace(provider=policy.model.protocol,
        schema_profile=policy.model.schema_profile), {**body, "response_format": canonical}))
    assert rebuilt == body, "current_schema_differs_from_frozen_request"
    assert cfg["attempts_per_cap"] == 1 and cfg["retries"] == 0
    assert len(cfg["output_caps"]) <= policy.case.max_model_calls
    files = [HERE / "config.json", Path(__file__), source / "export/database.json",
             source / "calls/call-1-intent.json", ROOT / cfg["policy"],
             ROOT / "tools/testdata/case_io_eval/model_eval.py", ROOT / "tools/testdata/case_io_eval/model_worker.py",
             ROOT / "tools/testdata/incident_integration/gateway.py", ROOT / "tools/testdata/incident_integration/remote_tokenizer.py"]
    files += sorted((ROOT / "services/api/app/socai2").glob("*.py"))
    files += sorted((ROOT / "services/api/app/socai2").glob("*.json"))
    cells = [{"id": f"C02-{cap}", "body": {**body, "max_tokens": cap}} for cap in cfg["output_caps"]]
    save(HERE / "plan.json", {"config": cfg, "prepared_at": datetime.now(UTC).isoformat(),
        "source_run_id": rid, "prepared": prepared, "context": context, "bindings": request["binding_map"],
        "cells": cells, "timeout_seconds": policy.single_model_timeout_seconds,
        "max_total_tokens": policy.case.max_total_tokens,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "scope": "frozen C3 model boundary; no business writes, new Run, correction or production configuration change"})
    save(HERE / "capacity.json", read(Path(cfg["capacity_receipt"])))
    print(json.dumps({"prepared": True, "calls": len(cells), "caps": cfg["output_caps"]}), flush=True)


def plan_for(cfg):
    plan = read(HERE / "plan.json")
    assert cfg == plan["config"]
    assert all(sha(ROOT / p) == h for p, h in plan["source_sha256"].items()), "frozen_source_changed"
    return plan


async def execute(cfg, runtime):
    from app.socai2.runtime_policy import active_policy
    from app.socai2.token_budget import BackendTokenMeter
    from tools.testdata.incident_integration.gateway import TokenizerTransport

    plan = plan_for(cfg)
    before = await asyncio.to_thread(remote, runtime, {"phase": "preflight", "timeout_seconds": runtime["preflight_timeout_seconds"]})
    save(HERE / "preflight.json", before)
    check_route(runtime, before)
    measurements = []
    for cell in plan["cells"]:
        policy = active_policy().model
        candidate = replace(policy, output_tokens={**policy.output_tokens, "C3": cell["body"]["max_tokens"]})
        meter = BackendTokenMeter(candidate, transport=TokenizerTransport(runtime, HERE / cell["id"] / "tokenizer"))
        measured = await meter.measure(cell["body"], "C3")
        save(HERE / cell["id"] / "measurement.json", measured)
        assert measured["context_fits"]
        measurements.append(measured)
    assert sum(m["reserved_total_tokens"] for m in measurements) <= plan["max_total_tokens"]
    save(HERE / "batch-intent.json", {"started_at": datetime.now(UTC).isoformat(),
        "plan_sha256": sha(HERE / "plan.json"), "generation_calls": len(plan["cells"]), "retries": 0})
    for cell in plan["cells"]:
        save(HERE / cell["id"] / "intent.json", {"body": cell["body"], "attempt": 1})
        print(cell["id"] + " dispatch", flush=True)
        result = await asyncio.to_thread(remote, runtime, {"phase": "call", "cell": cell["id"],
            "body": cell["body"], "timeout_seconds": plan["timeout_seconds"]})
        save(HERE / cell["id"] / "receipt.json", result)
        print(json.dumps({"cell": cell["id"], "state": result["state"], "seconds": result.get("http_seconds"),
            "usage": result.get("raw", {}).get("usage")}), flush=True)
        if "unknown" in result["state"]:
            return
    after = await asyncio.to_thread(remote, runtime, {"phase": "preflight", "timeout_seconds": runtime["preflight_timeout_seconds"]})
    save(HERE / "completion.json", {"finished_at": datetime.now(UTC).isoformat(), "after": after,
        "runtime_unchanged": after.get("runtime_sha256") == before["runtime_sha256"],
        "route_unchanged": all(after.get(k) == before.get(k) for k in runtime["expected_route"])})


def assess(content, plan):
    from app.socai2 import case_output_adapter as adapter
    from app.socai2.baseline_context import Context
    from app.socai2.baseline_analysis_contract import AnalysisRejected

    context = Context.model_validate(plan["context"])
    try:
        parsed = adapter.parse(content, plan["prepared"], context, plan["bindings"])
        return {"accepted": True, "assembled": parsed.model_dump(mode="json")}
    except AnalysisRejected as exc:
        out = {"accepted": False, "error": str(exc)}
    reviewer = adapter.CaseReview(plan["prepared"], context, plan["bindings"])
    try:
        out["feedback"] = reviewer.feedback(content)
        reviewer.partial(content)
        out["partial_review"] = reviewer.details
    except AnalysisRejected as exc:
        out["review_error"] = str(exc)
    return out


def review(cfg):
    from jsonschema import Draft202012Validator

    plan = plan_for(cfg)
    results = []
    for cell in plan["cells"]:
        folder = HERE / cell["id"]
        if not (folder / "receipt.json").exists():
            continue
        receipt = read(folder / "receipt.json")
        raw = receipt.get("raw", {})
        result = {"id": cell["id"], "state": receipt["state"], "usage": raw.get("usage"),
                  "http_seconds": receipt.get("http_seconds")}
        choices = raw.get("choices") or []
        if receipt["state"] != "response_received" or len(choices) != 1:
            results.append(result)
            continue
        choice = choices[0]
        content = choice["message"]["content"]
        (folder / "answer.txt").write_text(content)
        result["finish_reason"] = choice.get("finish_reason")
        try:
            value = json.loads(content)
        except ValueError:
            result.update(json_complete=False, accepted=False, error="incomplete_json")
            results.append(result)
            continue
        result.update(json_complete=True, sections=list(value), counts={k:len(v) for k,v in value.items() if isinstance(v,list)})
        errors = list(Draft202012Validator(cell["body"]["response_format"]["json_schema"]["schema"]).iter_errors(value))
        result["wire_errors"] = [{"path": list(e.absolute_path), "validator": e.validator, "message": e.message} for e in errors]
        result["original_acceptance"] = assess(content, plan)
        normalized, changes = copy.deepcopy(value), []
        def visit(node, path):
            if isinstance(node, dict):
                for key, item in node.items():
                    if key in {"support_ids", "counter_ids", "evidence_ids", "source_ids"} and isinstance(item, list):
                        unique = list(dict.fromkeys(item))
                        if unique != item:
                            changes.append({"path": path+[key], "before": item, "after": unique})
                            node[key] = unique
                    else:
                        visit(item, path+[key])
            elif isinstance(node, list):
                for index, item in enumerate(node):
                    visit(item, path+[index])
        visit(normalized, [])
        result["exact_duplicate_preview"] = {"production_implemented": False, "changes": changes,
            "acceptance": assess(json.dumps(normalized, ensure_ascii=False), plan)}
        results.append(result)
    save(HERE / "structural-review.json", {"results": results, "quality": "requires_semantic_review",
        "scope": "structure and references are not proof of factual truth; normalization is offline preview"})
    print(json.dumps([{k:v for k,v in r.items() if k not in {"original_acceptance", "exact_duplicate_preview", "wire_errors"}} for r in results]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "review"))
    args = parser.parse_args()
    config, transport = initialize()
    if args.phase == "prepare":
        prepare(config, transport)
    elif args.phase == "run":
        asyncio.run(execute(config, transport))
    else:
        review(config)
