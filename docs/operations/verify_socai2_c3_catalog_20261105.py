"""Offline replay of closed local a: no database, lake or model dispatch."""
import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
os.environ["DATABASE_URL"] = "postgresql+asyncpg://offline:offline@127.0.0.1:1/offline"
sys.path.insert(0, str(ROOT / "services/api"))

from app.services.llm_safety import LLMInputContract
from app.socai2 import baseline_analysis_contract as contract
from app.socai2.baseline_analysis import budget_reason, messages
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_dispatch import offered_bindings
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format

DEFAULT = ROOT / ".local/local-investigation/validation/local-maintenance-20261105a/exports/20261105T102314778605Z/database.json"
OUTPUT = ROOT / "docs/operations/evidence/investigation-repair-20261105/local-a-c3-catalog-replay.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    db = json.loads(path.read_text())
    steps = {row["id"]: row for row in db["run_steps"]}
    request = next(row for row in db["artifacts"] if row["kind"] == "model_request"
                   and steps.get(row["step_id"], {}).get("stage_code") == "C3")
    run = next(row for row in db["runs"] if row["id"] == request["run_id"])
    rows = [row for row in db["artifacts"] if row["run_id"] == run["id"] and isinstance(row["content_json"], dict)]
    assert all(digest(row["content_json"]) == row["sha256"] for row in rows)
    context = Context.model_validate(next(row["content_json"] for row in rows if row["schema_version"] == "socai2.baseline-context.v1"))
    prepared = next(row["content_json"] for row in rows if row["schema_version"] == "socai2.baseline-model-view.v4")
    material = next(row["content_json"] for row in rows if row["content_json"].get("type") == "materials")
    tools = {row["id"]: row["content_json"] for row in rows if row["kind"] == "tool_response"}
    step = steps[request["step_id"]]
    previous = [row for row in steps.values() if row["run_id"] == run["id"] and row["seq"] < step["seq"]]
    now, limits = datetime.fromisoformat(step["started_at"]), Limits.model_validate(run["limits"])
    options, bindings, excluded = offered_bindings(material["catalog"], limits, now, previous, SimpleNamespace(configured=lambda: True))
    return {"db": db, "run": run, "request": request["content_json"]["payload"], "request_id": request["id"],
            "context": context, "prepared": prepared, "tools": tools, "options": options, "bindings": bindings,
            "excluded": excluded, "now": now, "limits": limits, "previous": previous, "rows": rows}


def replay(path):
    before = sha(path)
    sample = load(path)
    original = sample["request"]
    facts_before = json.loads(original["body"]["input"][1]["content"])
    assert facts_before.pop("tool_options") == [] and original["binding_map"] == {}
    prepared_before, options_before = copy.deepcopy(sample["prepared"]), copy.deepcopy(sample["options"])
    prompt, sources = messages(sample["prepared"], sample["context"], sample["tools"], sample["options"])
    assert sample["prepared"] == prepared_before and sample["options"] == options_before
    assert json.loads(prompt[1]["content"]) == facts_before and sources == original["source_map"]
    grouped = json.loads(prompt[2]["content"])
    expanded = [{**{key: group[key] for key in ("hostname", "alert_ids", "object_keys")}, **option}
                for group in grouped["tool_option_groups"] for option in group["options"]]
    assert expanded == options_before and len(expanded) == 3 and not sample["excluded"]
    assert {row["tool_name"] for row in expanded} == {"authentication_activity", "network_connections", "process_activity"}
    assert len(prompt[1]["content"].encode()) <= 8192 and len(encoded(prompt)) <= 12288
    assert LLMInputContract.validate(prompt) == prompt
    trials = []
    context = sample["context"]
    for protocol, profile in (("deepseek_responses", "standard"), ("chat_completions", "vllm_grammar_v1")):
        gateway = SimpleNamespace(provider=protocol, schema_profile=profile, model=original["body"]["model"])
        canonical = {"model": gateway.model, "messages": prompt, "max_tokens": 3000, "temperature": 0,
            "response_format": response_format(contract.ExecutionAnalysis, sources, members=context.alerts,
                questions=[q.id for q in context.questions], objects=context.scope.object_keys, bindings=sample["bindings"])}
        body = prepare_request(gateway, canonical)
        wire_messages = body["input"] if protocol == "deepseek_responses" else body["messages"]
        assert wire_messages == prompt and LLMInputContract.validate(wire_messages) == wire_messages
        reason = budget_reason(sample["previous"], sample["limits"], len(encoded(body)), sample["now"],
                               reserve_calls=1, reservation=original["final_reservation"])
        assert reason is None
        trials.append({"protocol": protocol, "schema_profile": profile, "wire_bytes": len(encoded(body)),
            "reserved_call_units": len(encoded(body)) + 3000 + 256,
            "wire_sha256": digest(body), "unchanged_saved_reservation_admission": reason,
            "llm_input_contract": "passed_without_rewrite"})
    # This constructed parser probe is not a model answer or a replacement of a.
    response = next(row["content_json"]["payload"]["raw"] for row in sample["rows"]
                    if row["kind"] == "model_response" and row["schema_version"] == "socai2.baseline-analysis.v2")
    answer = json.loads(response["output"][0]["content"][0]["text"])
    for option in options_before:
        probe = copy.deepcopy(answer)
        probe["followups"] = [{**answer["followups"][0], "mode": "query", "binding_id": option["binding_id"],
                              "alert_ids": option["alert_ids"], "object_keys": option["object_keys"], "source_ids": []}]
        contract.parse(json.dumps(probe), sources, context, sample["prepared"]["coverage"], bindings=sample["bindings"])
    assert sha(path) == before
    files = [Path(__file__), *[ROOT / "services/api/app/socai2" / name for name in
        ("baseline_analysis.py", "baseline_analysis_contract.py", "baseline_tool_catalog.py", "baseline_dispatch.py",
         "model_input_view.py", "model_protocol.py", "baseline_capacity.py")],
        ROOT / "services/api/tests/test_socai2_c3_tool_catalog.py"]
    return {"kind": "offline_original_input_replay_not_acceptance", "at": datetime.now(UTC).isoformat(),
        "database": {"path": str(path.relative_to(ROOT)), "sha256_before": before, "sha256_after": sha(path)},
        "run_id": sample["run"]["id"], "original_state": sample["run"]["state"], "request_id": sample["request_id"],
        "facts": {"bytes": len(prompt[1]["content"].encode()), "cap": 8192, "values_and_members_unchanged": True,
            "source_map_and_original_paths_unchanged": True, "coverage_and_omissions_unchanged": True,
            "visible_source_count": len(sources), "source_map_sha256": digest(sources)},
        "catalog": {"original_offered": 0, "candidate_offered": len(expanded), "groups": len(grouped["tool_option_groups"]),
            "flat_bytes": len(encoded(options_before)), "grouped_bytes": len(prompt[2]["content"].encode()),
            "options": expanded, "binding_map_sha256": digest(sample["bindings"]), "lossless_roundtrip": True,
            "constructed_query_parser_probes": 3, "catalog_guard": "entire_catalog_before_trimming_and_all_sent_messages"},
        "messages": {"count": len(prompt), "bytes": len(encoded(prompt)), "cap": 12288},
        "wire_trials": trials, "limits_unchanged": sample["run"]["limits"],
        "original_deep_skip_reason_unchanged": "final_model_tokens_reserved", "model_calls": 0, "lake_calls": 0,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "limitations": ["closed a unchanged and not replayed against any service", "no response edited or adopted",
            "query options being visible does not prove model selection, actual lake access or semantic quality",
            "larger facts or different host scopes can still explicitly exclude whole options at the same total cap",
            "Deep token reservation and C6 output quality are separate from this C3 catalog fix"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = replay(args.database)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"receipt": str(args.output), "facts_bytes": result["facts"]["bytes"],
        "messages_bytes": result["messages"]["bytes"], "bindings": result["catalog"]["candidate_offered"], "model_calls": 0}))


if __name__ == "__main__":
    main()
