"""Compare saved Deep/C6 requests with current configured boundaries, offline."""
import argparse
import copy
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import case_followup_input as inputs
from app.socai2 import case_followup_output as outputs
from app.socai2 import (
    case_model_boundary,
    case_query_snapshot,
    runtime_policy,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_store import encoded
from app.socai2.case_followup_loader import graph_candidates

from tools.testdata.case_followup_eval.audit import (
    c6_aliases,
    origin,
    reference_ids,
    visible,
)
from tools.testdata.case_io_eval.fixtures import load


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context_for(sample, profile):
    """In-memory candidate C1 only; never rewrite the historical snapshot."""
    raw = copy.deepcopy(sample["context"])
    raw["query_receipts_version"] = case_query_snapshot.VERSION
    raw["case_input_profile"] = profile.identity
    for aid, item in raw["alerts"].items():
        item["triage_run_state"] = "completed"
        item["queries"] = copy.deepcopy(sample["query_source"]["triage_queries"].get(aid, []))
        for row in item["queries"]:
            row.update(output_artifact_id=row["id"], step_kind="tool", step_state=row["content_json"]["state"],
                       source_run_state="completed")
    for iid, item in raw["incidents"].items():
        if not item["diagnosis_usable"]:
            continue
        diagnosis, base = item["diagnosis"], f"$.incidents.{iid}.diagnosis"
        paths = [base + ".summary"]
        paths += [base + ".diagnosis." + key for key in ("conclusion", "limitations") if key in diagnosis["diagnosis"]]
        paths += [base + f".diagnosis.findings.{i}" for i in range(len(diagnosis["diagnosis"].get("findings", [])))]
        paths += [base + f".open_questions.{i}" for i in range(len(diagnosis.get("open_questions", [])))]
        raw["citation_roles"].update(dict.fromkeys(paths, "prior_analysis"))
    raw["citation_roles"].update(case_query_snapshot.roles(raw))
    return Context.model_validate(raw)


def metrics(body, sources, artifacts):
    observations = [origin(s, artifacts) for s in sources.values() if s["ref"]["role"] == "observation"]
    return {"user_bytes": len(body["messages"][1]["content"].encode()),
        "all_message_bytes": len(encoded(body["messages"])), "wire_body_bytes": len(encoded(body)),
        "schema_bytes": len(encoded(body["response_format"])), "source_count": len(sources),
        "source_roles": dict(Counter(s["ref"]["role"] for s in sources.values())),
        "observation_entries": len(observations), "observation_original_positions": len(set(observations)),
        "tokens": None, "generation_seconds": None}


def compare(config):
    os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    sample, db = load(ROOT, config), read(ROOT / config["snapshot"])
    artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == config["source_run_id"]}
    for row in artifacts.values():
        raw = encoded(row["content_json"]) if row["content_json"] is not None else row["content_text"].encode()
        assert hashlib.sha256(raw).hexdigest() == row["sha256"] and len(raw) == row["size_bytes"]
    steps = {s["id"]: s for s in db["run_steps"]}
    exchanges = {}
    for row in artifacts.values():
        if row["kind"] != "model_request":
            continue
        stage = steps[row["step_id"]]["stage_code"]
        if stage not in {"C4.deep", "C6"}:
            continue
        assert stage not in exchanges
        request = row["content_json"]["payload"]
        data, values = visible(request)
        response = artifacts[steps[row["step_id"]]["output_artifact_id"]]["content_json"]["payload"]
        exchanges[stage] = {"artifact": row, "request": request, "data": data, "values": values,
                            "raw": response["raw"]["choices"][0]["message"]["content"]}
    assert set(exchanges) == {"C4.deep", "C6"}
    context = context_for(sample, policy.case_io)
    enrichment = next(r["content_json"] for r in artifacts.values() if (r["content_json"] or {}).get("sources"))
    sources = [(s["artifact_id"], artifacts[s["artifact_id"]]["content_json"], s["citation_roles"])
               for s in enrichment["sources"]]
    base = case_model_boundary.build(context, sample["context_id"], sources, enrichment["sources"], sample["materials"],
        execution_time=sample["run"]["started_at"], run_id=sample["run"]["id"])
    assert base["ready"], base["reason"]
    material = next(r["content_json"] for r in artifacts.values() if (r["content_json"] or {}).get("type") == "materials")
    dispatch = next(r["content_json"] for r in artifacts.values() if (r["content_json"] or {}).get("type") == "followup_dispatch")
    prior_id = dispatch["initial_analysis_artifact_id"]
    prior = artifacts[prior_id]["content_json"]
    execution, lead = delivery_followups(dispatch, prior)
    bases = [r for r in artifacts.values() if (r["content_json"] or {}).get("type") in
             {"materials", "query_projection", "deep_summary", "graph_snapshot"}]
    graph_state, graphs = graph_candidates(bases, artifacts)
    results, files = {}, {"candidate-base-ledger.json": base["input_ledger"]}
    alias_config = read(ROOT / config["alias_paths"])
    for stage, exchange in exchanges.items():
        before, data = exchange["request"], exchange["data"]
        projections = [artifacts[r["artifact_id"]] for r in data["queries"]]
        # Keep exactly the tools offered in this historical call, not today's
        # clock, connectivity or remaining budget. Nothing will be dispatched.
        options = []
        for alias, bid in before["binding_map"].items():
            binding = material["catalog"]["bindings"][bid]
            options.append({"binding_id": alias, "tool_name": binding["tool_name"], "hostname": binding["hostname"],
                "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})})
        stem = "deep" if stage == "C4.deep" else "c6"
        extra = {} if stem == "deep" else {"round": "final_delivery", "comparison": data["comparison"],
                                           "followup_execution": execution, "graph_state": graph_state}
        prepared = inputs.build("Deep" if stem == "deep" else "C6", context, base, artifacts,
            previous=prior, prior_id=prior_id, question_id=data["question"]["id"] if stem == "deep" else None,
            material=material, projections=projections, options=options, binding_map=before["binding_map"],
            extra=extra, lead=() if stem == "deep" else lead, graphs=() if stem == "deep" else graphs)
        assert prepared["ready"], prepared["reason"]
        fmt = outputs.deep_format(prepared) if stem == "deep" else outputs.final_format(prepared, context, data["comparison"])
        after = {**copy.deepcopy(before["body"]), "messages": prepared["messages"], "response_format": fmt}
        dependencies = prepared["followup_boundary"]["dependencies"]
        original_answer = json.loads(exchange["raw"])
        if stem == "deep":
            replay = {k: v for k, v in original_answer.items() if k != "question_id"}
            restored = {"question_id": data["question"]["id"], **replay}
        else:
            boundary = prepared["case_boundary"]
            replay = c6_aliases(original_answer, alias_config, boundary["member_aliases"], boundary["object_aliases"])
            for row in replay["recommendations"]:
                row.pop("id")
            if outputs.fixed_comparison(data["comparison"]):
                replay.pop("comparison")
            restored = json.loads(outputs.restore_final(json.dumps(replay, ensure_ascii=False), prepared, data["comparison"]))
        assert restored == original_answer
        # This is a storage-shape roundtrip, never pretend the old source IDs
        # are legal IDs in the new request or that the model generated it.
        results[stem] = {"before": metrics(before["body"], before["source_map"], artifacts),
            "after": metrics(after, prepared["source_map"], artifacts),
            "dependency_occurrences": len(dependencies), "mapped_dependencies": sum(bool(d["visible_id"]) for d in dependencies),
            "missing_dependencies": [d for d in dependencies if not d["visible_id"]],
            "prior_blocks": {r["block"]: list(r["value"]) for r in prepared["followup_boundary"]["records"] if r["block"] in {"C3", "Deep"}},
            "prior_c3_stored_counts": {k: len(v) for k, v in prior["analysis"].items() if isinstance(v, list)},
            "old_answer_compact_bytes": len(encoded(original_answer)), "replayed_shape_bytes": len(encoded(replay)),
            "output_roundtrip_equal": True, "original_structured_references_preserved": reference_ids(replay) == reference_ids(original_answer),
            "model_response_generated": False, "request_id": exchange["artifact"]["id"]}
        for variant, body in (("before", before["body"]), ("after", after)):
            files[f"{stem}-{variant}-input.txt"] = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in body["messages"])
            files[f"{stem}-{variant}-schema.json"] = body["response_format"]
            files[f"{stem}-{variant}-request.json"] = body
        files[f"{stem}-original-output.txt"] = exchange["raw"]
        files[f"{stem}-output-shape-replay-not-generated.json"] = replay
        files[f"{stem}-mapping-ledger.json"] = prepared
    return results, files, len(artifacts), policy.case_io.identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("comparison-config.json"))
    args = parser.parse_args()
    config = read(args.config)
    assert config["version"] == "socai2.case-followup-comparison.v1"
    folder = ROOT / config["output"]
    if folder.exists():
        raise ValueError("finished_comparison_must_not_be_overwritten")
    paths = [args.config.resolve(), Path(__file__).resolve(), *[ROOT / k for k in
             [config["snapshot"], config["policy"], config["alias_paths"], *config["source_files"]]]]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    stages, files, count, profile = compare(config)
    assert hashes == {str(p.relative_to(ROOT)): sha(p) for p in paths}
    summary = {"batch": config["batch"], "at": datetime.now(UTC).isoformat(), "stages": stages,
        "mode": "same_saved_material_offline_projection_and_output_shape_roundtrip", "source_run_id": config["source_run_id"],
        "real_model_calls": 0, "database_connections": 0, "created_cases": 0, "created_runs": 0, "deployments": 0,
        "source_artifacts_verified": count, "source_sha256": hashes, "profile": profile,
        "limitations": ["candidate_C1_extends_roles_and_adds_verified_same_A_receipts_in_memory_only",
            "same_frozen_snapshot_not_identical_visible_input", "old_answers_not_validated_as_new_model_answers",
            "bytes_not_tokens_or_latency_or_semantic_quality", "not_sent_and_not_deployed"]}
    files["summary.json"] = summary
    folder.mkdir(parents=True)
    for name, value in files.items():
        (folder / name).write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(folder.relative_to(ROOT)), "stages": stages}, ensure_ascii=False))


if __name__ == "__main__":
    main()
