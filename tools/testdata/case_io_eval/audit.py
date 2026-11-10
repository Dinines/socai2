"""Build a C3 offline candidate and immutable evidence; no model/DB/SSH calls."""
import argparse
import copy
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize(config):
    from tools.testdata.incident_integration.run import initialize as init

    runtime, _ = init(ROOT / config["runtime_config"])
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    return runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    args = parser.parse_args()
    config = read(args.config)
    initialize(config)
    from app.socai2 import baseline_analysis_contract as legacy
    from app.socai2.baseline_context import Context
    from app.socai2.baseline_model_view import blocked
    from app.socai2.baseline_semantics import material_projection
    from app.socai2.baseline_store import encoded
    from app.socai2.model_protocol import prepare_request
    from app.socai2.runtime_policy import active_policy
    from jsonschema import ValidationError as SchemaError

    from .fixtures import load
    from .hierarchy import render_tools
    from .input_adapter import material_entries, prepare
    from .output_adapter import canonical, convert, parse, schema, tool_catalog

    source_paths = [ROOT / config["snapshot"], *[ROOT / p for p in config["material_snapshots"]]]
    original_hashes = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    business = read(ROOT / config["business_render_config"])
    sample = load(ROOT, config)
    prepared = prepare(sample, config, business)
    bindings = sample["request"]["binding_map"]
    # Isolate identifier adaptation from additional evidence/input changes.
    original_prepared = {**prepared, "source_map": sample["request"]["source_map"], "coverage": sample["data"]["members"]}
    replay = convert(sample["answer"], prepared["member_aliases"], prepared["object_aliases"])
    restored = canonical(json.dumps(replay), original_prepared, sample["context"], bindings)
    assert restored == sample["answer"]
    validations = []
    for answer in (sample["answer"], restored):
        try:
            legacy.parse(json.dumps(answer), original_prepared["source_map"], Context.model_validate(sample["context"]),
                         original_prepared["coverage"], bindings=bindings)
            validations.append({"accepted": True})
        except legacy.AnalysisRejected as exc:
            validations.append({"accepted": False, "reason": str(exc)})
    assert validations[0] == validations[1]
    # Do not rewrite old citation arrays to make the old answer pass new input.
    old_answer_on_new_input = None
    try:
        parse(json.dumps(replay), prepared, sample["context"], bindings)
        old_answer_on_new_input = {"accepted": True}
    except (ValueError, KeyError, SchemaError) as exc:
        old_answer_on_new_input = {"accepted": False, "error_type": type(exc).__name__,
                                   "reason": "historical_citations_not_automatically_valid_in_new_input"}
    material_checks = []
    for path in source_paths[1:]:
        for material in read(path)["alert_materials"]:
            omissions = []
            items = material_entries(material["alert_id"], material, business, omissions, config)
            material_checks.append({"snapshot": str(path.relative_to(ROOT)), "material_id": material["id"],
                "original_fields": len(material_projection(material)["fields"]), "candidate_fields": len(items),
                "visible_fields_after_existing_guard": sum(not blocked(item["original_value"]) for item in items),
                "records": items, "omissions": omissions, "kind": "material_only_no_synthetic_case_created"})
    body = copy.deepcopy(sample["request"]["body"])
    instruction = body["messages"][0]["content"]
    for replacement in config["system_replacements"]:
        if instruction.count(replacement["old"]) != 1:
            raise ValueError("saved_instruction_replacement_mismatch")
        instruction = instruction.replace(replacement["old"], replacement["new"])
    catalog = tool_catalog(json.loads(body["messages"][2]["content"]), prepared)
    tools_view = render_tools(catalog, config)
    body["messages"] = [{"role": "system", "content": instruction + "\n" + config["system_suffix"]},
                        {"role": "user", "content": prepared["user"]},
                        {"role": "user", "content": tools_view["text"]}]
    body["response_format"] = {"type": "json_schema", "json_schema": {
        "name": "case_input_candidate", "strict": True, "schema": schema(prepared, sample["context"], bindings)}}
    model_policy = active_policy().model
    wire = prepare_request(SimpleNamespace(provider=model_policy.protocol, schema_profile=model_policy.schema_profile), body)
    summary = {"batch": config["batch"], "mode": "offline_candidate_only", "model_calls": 0,
        "database_connections": 0, "remote_actions": 0, "created_cases": 0, "snapshot_sha256": original_hashes,
        "input_bytes_before": len(sample["request"]["body"]["messages"][1]["content"].encode()),
        "input_bytes_after": len(prepared["user"].encode()), "request_bytes_before": len(encoded(sample["request"]["body"])),
        "request_bytes_after": len(encoded(body)), "source_count_before": len(sample["request"]["source_map"]),
        "source_count_after": len(prepared["source_map"]), "record_counts": prepared["record_counts"],
        "input_guard_omissions": [o for o in prepared["omissions"] if o["reason"] == "input_guard"],
        "a_receipts_added": len(sample["verified_queries"]), "a_receipts_were_in_original_c1": False,
        "legacy_output_roundtrip_equal": True, "old_answer_on_new_input": old_answer_on_new_input,
        "old_answer_validation_before_and_after": validations,
        "material_coverage": [{k: v for k, v in row.items() if k not in {"records", "omissions"}} for row in material_checks],
        "candidate_tokens": None, "candidate_latency_seconds": None, "model_quality_tested": False,
        "prepared_request_bytes": len(encoded(wire)), "protocol": model_policy.protocol,
        "schema_profile": model_policy.schema_profile,
        "limitations": ["new_evidence_and_rendering_changed_together_not_controlled_ab",
                        "bytes_not_tokens_or_speed", "supplemental_a_receipts_not_live_c1_integration",
                        "output_replay_is_old_answer_conversion_not_new_model_generation",
                        "no_database_or_api_contract_test", "required_request_not_tokenizer_measured_or_provider_validated"]}
    previous_path = ROOT / config["comparison_candidate"]
    previous = read(previous_path / "input-ledger.json")
    assert read(previous_path / "summary.json")["snapshot_sha256"] == original_hashes
    previous_request = read(previous_path / "candidate-request-not-sent.json")
    new_by_ref = {encoded(r["ref"]): r for r in prepared["records"]}
    kept, removed, observations = [], [], []
    for row in previous["records"]:
        new = new_by_ref.get(encoded(row["ref"]))
        if new:
            assert new["original_value"] == row["original_value"]
            kept.append(row["ref"])
        else:
            reasons = [o["reason"] for o in prepared["omissions"] if
                (o.get("material_id"), o.get("path")) == (row["ref"]["id"], row["ref"]["source_path"])
                or isinstance(o.get("origin"), dict) and
                (o["origin"].get("material_id"), o["origin"].get("path")) == (row["ref"]["id"], row["ref"]["source_path"])]
            assert reasons, "removed_record_without_structural_reason"
            removed.append({"ref": row["ref"], "value": row["value"], "reasons": sorted(set(reasons))})
        if row["ref"]["role"] == "observation":
            assert new is not None and row["value"] == new["value"]
            observations.append(row["ref"])
    assert previous["query_supplement"] == prepared["query_supplement"]
    assert previous["program_facts"] == prepared["program_facts"]
    comparison = {"previous": str(previous_path.relative_to(ROOT)), "same_material_snapshot": True,
        "same_query_supplement": True, "same_program_facts": True,
        "retained_original_records": len(kept), "unchanged_observation_sources": len(observations),
        "removed_non_observation_records": removed,
        "main_bytes_before": len(previous["user"].encode()), "main_bytes_after": len(prepared["user"].encode()),
        "tools_bytes_before": len(previous_request["messages"][2]["content"].encode()),
        "tools_bytes_after": len(tools_view["text"].encode()),
        "request_bytes_before": len(encoded(previous_request)), "request_bytes_after": len(encoded(body)),
        "full_candidate_input_guard_blocked": blocked(body["messages"]), "model_calls": 0}
    assert comparison["full_candidate_input_guard_blocked"] is False
    summary["same_material_comparison"] = comparison
    for path, h in original_hashes.items():
        assert sha(ROOT / path) == h
    tracked = [*Path(__file__).parent.glob("*.py"), args.config, ROOT / config["business_render_config"]]
    summary["source_sha256"] = {str(p.resolve().relative_to(ROOT)): sha(p) for p in tracked}
    target = ROOT / config["output"] / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True, exist_ok=False)
    outputs = {"summary.json": summary, "input-ledger.json": prepared, "material-coverage.json": material_checks,
        "candidate-request-not-sent.json": body, "config.json": config,
        "prepared-request-not-sent.json": wire,
        "hierarchy-comparison.json": comparison, "tool-presentation-ledger.json": tools_view,
        "output-replay.json": {"provenance": "offline_structure_replay_of_historical_answer", "candidate": replay,
                               "restored": restored}}
    for name, value in outputs.items():
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (target / "input-before.txt").write_text(sample["request"]["body"]["messages"][1]["content"])
    (target / "input-after.txt").write_text(prepared["user"])
    (target / "tool-catalog-after.txt").write_text(tools_view["text"])
    print(json.dumps({"output": str(target), "record_counts": summary["record_counts"],
        "comparison": {k: v for k, v in comparison.items() if k != "removed_non_observation_records"},
        "removed_non_observation_records": len(removed), "guard_omissions": len(summary["input_guard_omissions"])},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
