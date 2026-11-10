"""Save offline examples and mapping checks. This runner has NO model client."""
import argparse
import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .fixtures import load
from .input_adapter import encoded, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    config = json.loads(args.config.read_text())
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(root / config["policy"])
    from app.socai2 import incident_diagnosis_contract as legacy
    from app.socai2.baseline_store import StoreError

    from .output_adapter import candidate_schema, parse, replay_candidate

    sample = load(root, config)
    prepared = prepare(sample["data"], sample["source_map"], config)
    replay = replay_candidate(sample["answer"], prepared["member_aliases"])
    replay_context = {**prepared, "source_map": sample["source_map"]}
    expected, old_members = legacy.parse(sample["raw_answer"], sample["source_map"], sample["data"])
    output, new_members = parse(encoded(replay), replay_context)
    equal = expected.model_dump(mode="json") == output.model_dump(mode="json") and old_members == new_members
    if not equal:
        raise ValueError("output_roundtrip_changed_existing_contract")
    # The old model cited metadata which is deliberately absent in the candidate.
    # Record that boundary rather than deleting its citations or rewriting its prose.
    try:
        parse(encoded(replay), prepared)
        old_answer_on_new_input = {"accepted": True, "error": None}
    except StoreError as exc:
        old_answer_on_new_input = {"accepted": False, "error": exc.code}
    original = sample["request"]["body"]["messages"][-1]["content"]
    before, after = len(original.encode()), len(prepared["user"].encode())
    used = set(sample["answer"]["evidence_ids"])
    for key in ("members", "findings", "open_questions"):
        for entry in sample["answer"][key]:
            used.update(entry["source_ids"])
    source_text = (root / config["system_prompt"]).read_text()
    body = copy.deepcopy(sample["request"]["body"])
    body["messages"] = [{"role": "system", "content": source_text}, {"role": "user", "content": prepared["user"]}]
    body["response_format"] = {"type": "json_schema", "json_schema": {
        "name": "incident_boundary_candidate", "strict": True, "schema": candidate_schema(prepared)}}
    summary = {"batch": config["batch"], "mode": "offline_only_no_model_or_database_calls",
               "snapshot": config["snapshot"], "snapshot_sha256": sample["snapshot_sha256"],
               "source_run_id": sample["run"]["id"], "output_roundtrip_equal": equal,
               "member_findings": len(new_members), "all_findings": len(output.findings),
               "open_questions": len(output.open_questions), "input_bytes_before": before,
               "input_bytes_after": after, "input_byte_reduction_percent": round(100 * (1 - after / before), 2),
               "source_count_before": len(sample["source_map"]), "source_count_after": len(prepared["source_map"]),
               "original_reported_usage": sample["response"]["usage"],
               "candidate_tokens": None, "candidate_latency_seconds": None, "model_quality_tested": False,
               "old_answer_on_new_input": old_answer_on_new_input,
               "old_answer_references_removed_from_input": sorted(used - set(prepared["source_map"])),
               "existing_a_receipts_inventoried_not_added": sum(len(q["receipts"]) for q in sample["queries"]),
               "description_present": [bool(m["alert"].get("description")) for m in sample["source"]["members"]],
               "limitations": ["output_replay_is_structural_conversion_of_old_answer_not_new_model_output",
                               "input_bytes_not_model_token_savings", "candidate_request_not_sent_or_provider_validated",
                               "no_database_persistence_or_http_page_validation", "query_handoff_not_implemented"]}
    if hashlib.sha256((root / config["snapshot"]).read_bytes()).hexdigest() != sample["snapshot_sha256"]:
        raise ValueError("source_snapshot_changed")
    target = root / config["output"] / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target.mkdir(parents=True, exist_ok=False)
    artifacts = {"summary.json": summary, "input-ledger.json": prepared,
                 "output-replay-candidate.json": {"provenance": "offline_structure_replay_of_old_answer", "answer": replay},
                 "output-replay-assembled.json": output.model_dump(mode="json"),
                 "a-query-inventory.json": sample["queries"], "candidate-request-not-sent.json": body,
                 "config.json": config}
    for name, value in artifacts.items():
        (target / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (target / "input-before.txt").write_text(original)
    (target / "input-after.txt").write_text(prepared["user"])
    print(json.dumps({"output": str(target), **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
