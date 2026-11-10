"""Inspect saved Deep/C6 handoffs; no database, transport, or model client."""
import argparse
import copy
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
REFERENCE_ARRAYS = {"evidence_ids", "source_ids", "support_ids", "counter_ids"}


def read(path):
    return json.loads(path.read_text())


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def visible(request):
    data = json.loads(request["body"]["messages"][1]["content"])
    rows = [item for group in data["source_groups"] for item in group["items"]]
    assert len(rows) == len({r["id"] for r in rows})
    assert {r["id"] for r in rows} == set(request["source_map"])
    return data, {r["id"]: r["value"] for r in rows}


def origin(source, artifacts):
    """Resolve material projection provenance, never equate semantic values."""
    ref = source["ref"]
    identity = (ref["type"], ref["id"], ref["source_path"], ref["role"])
    artifact = artifacts.get(ref["id"])
    if not artifact or ref["type"] != "artifact":
        return identity
    payload = artifact["content_json"]
    parts = (ref["source_path"] or "").split(".")
    if payload.get("type") == "materials" and len(parts) == 5 and parts[:2] == ["$", "members"] and parts[3] == "fields":
        member = payload["members"][parts[2]]
        field = member["fields"][int(parts[4])]
        return "alert_material", member["material_id"], field["source_path"], ref["role"]
    return identity


def reference_ids(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in REFERENCE_ARRAYS:
                assert isinstance(child, list)
                found.extend(child)
            else:
                found.extend(reference_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(reference_ids(child))
    return found


def coverage(sources, target, artifacts):
    targets = {}
    for sid, source in target.items():
        targets.setdefault(origin(source, artifacts), []).append(sid)
    return [{"source_id": sid, "origin": origin(source, artifacts),
             "target_source_ids": targets.get(origin(source, artifacts), []),
             "original_alert_ids": source["alert_ids"]}
            for sid, source in sources.items()]


def dependencies(value, original_map, target, artifacts):
    ids = sorted(set(reference_ids(value)))
    assert set(ids) <= set(original_map)
    rows = coverage({sid: original_map[sid] for sid in ids}, target, artifacts)
    return {"structured_references": len(rows),
            "same_origin_available": sum(bool(r["target_source_ids"]) for r in rows), "rows": rows,
            "limitation": "same_origin_is_not_identical_visible_value_or_independent_corroboration"}


def replace_path(value, parts, mapping):
    if not parts:
        return [mapping[v] for v in value] if isinstance(value, list) else mapping[value]
    head, *tail = parts
    if head == "*":
        return [replace_path(v, tail, mapping) for v in value]
    result = copy.deepcopy(value)
    result[head] = replace_path(result[head], tail, mapping)
    return result


def c6_aliases(value, config, members, objects):
    for paths, mapping in ((config["c6_member_paths"], members), (config["c6_object_paths"], objects)):
        for path in paths:
            value = replace_path(value, path.split("."), mapping)
    return value


def inventory(stage, data, sources, values):
    lines = [f"# {stage} 已保存输入的材料清单", "",
        "这是历史请求的只读展开，供设计核对；不是新的模型请求。下列正文和旧编号保持原样。", ""]
    for key in ("question", "prior_analysis", "queries", "followup_execution", "comparison",
                "tool_options", "tool_capabilities", "tool_availability", "limitations"):
        if key in data:
            lines += [f"## {key}", "", "```json", json.dumps(data[key], ensure_ascii=False, indent=2), "```", ""]
    lines += ["## 已实际显示的来源", ""]
    for sid, value in values.items():
        source = sources[sid]
        lines += [f"### {sid} · {source['ref']['role']}", "",
                  "范围：" + json.dumps(source["alert_ids"], ensure_ascii=False), "",
                  "```json", json.dumps(value, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    args = parser.parse_args()
    config = read(args.config)
    assert config["version"] == "socai2.case-followup-audit.v1"
    output = ROOT / config["output"]
    if output.exists():
        raise ValueError("finished_audit_batch_must_not_be_overwritten")
    inputs = [ROOT / config["snapshot"], ROOT / config["c3_input_ledger"], args.config.resolve(),
              Path(__file__).resolve(), *[ROOT / name for name in config["source_files"]]]
    fingerprints = {str(path.relative_to(ROOT)): sha(path) for path in inputs}
    db, ledger = read(inputs[0]), read(inputs[1])
    run = next(r for r in db["runs"] if r["id"] == config["source_run_id"])
    artifacts = {a["id"]: a for a in db["artifacts"]}
    steps = {s["id"]: s for s in db["run_steps"]}
    run_artifacts = {aid: a for aid, a in artifacts.items() if a["run_id"] == run["id"]}
    for artifact in run_artifacts.values():
        assert artifact["tenant_id"] == run["tenant_id"]
        body = (encoded(artifact["content_json"]) if artifact["content_json"] is not None
                else artifact["content_text"].encode())
        assert hashlib.sha256(body).hexdigest() == artifact["sha256"]
        assert len(body) == artifact["size_bytes"]
    exchanges = {}
    for aid, artifact in run_artifacts.items():
        if artifact["kind"] != "model_request":
            continue
        step = steps[artifact["step_id"]]
        stage = step["stage_code"]
        if stage not in {"C3", "C4.deep", "C6"}:
            continue
        if stage in exchanges:
            raise ValueError("choose_snapshot_with_one_request_per_stage_or_extend_iteration_audit")
        request = artifact["content_json"]["payload"]
        response = run_artifacts[step["output_artifact_id"]]
        raw = response["content_json"]["payload"]["raw"]["choices"][0]["message"]["content"]
        data, values = visible(request)
        exchanges[stage] = {"request_id": aid, "request": request, "data": data, "values": values,
                            "answer": json.loads(raw), "step": step}
    assert set(exchanges) == {"C3", "C4.deep", "C6"}
    deep, final = exchanges["C4.deep"], exchanges["C6"]
    prior_id = final["data"]["followup_execution"]["initial_analysis_artifact_id"]
    prior = run_artifacts[prior_id]["content_json"]
    assert prior["analysis"] and prior["source_map"]
    blocks = []
    for sid, source in final["request"]["source_map"].items():
        if source["ref"]["id"] == prior_id:
            blocks.append({"source_id": sid, "path": source["ref"]["source_path"],
                           "visible_keys": sorted(final["values"][sid])})
    reports, files = {}, {}
    for stage, exchange in exchanges.items():
        request, data, answer = exchange["request"], exchange["data"], exchange["answer"]
        matched = coverage(ledger["source_map"], request["source_map"], artifacts)
        blocks_present = Counter()
        blocks_missing = Counter()
        base_rows = {r["id"]: r for r in ledger["records"]}
        for row in matched:
            target = blocks_present if row["target_source_ids"] else blocks_missing
            target[base_rows[row["source_id"]]["block"]] += 1
        reports[stage] = {"request_id": exchange["request_id"], "source_count": len(request["source_map"]),
            "source_roles": dict(Counter(s["ref"]["role"] for s in request["source_map"].values())),
            "user_bytes": len(request["body"]["messages"][1]["content"].encode()),
            "compact_output_bytes": len(encoded(answer)),
            "output_section_bytes": {k: len(encoded(v)) for k, v in answer.items()},
            "compared_c3_candidate_sources": len(matched),
            "same_origin_available": sum(bool(r["target_source_ids"]) for r in matched),
            "same_origin_by_block": dict(blocks_present), "not_explicitly_mapped_by_block": dict(blocks_missing),
            "same_origin_map": matched}
        if stage != "C3":
            stem = "deep" if stage == "C4.deep" else "c6"
            files[stem + "-input-inventory.md"] = inventory(stage, data, request["source_map"], exchange["values"])

    # Pure output-shape experiment: leave prose and every original citation alone.
    # It does not validate these old answers against the new C3 material set.
    deep_schema = copy.deepcopy(deep["request"]["body"]["response_format"]["json_schema"]["schema"])
    deep_schema["properties"].pop("question_id")
    deep_schema["required"].remove("question_id")
    deep_schema["$defs"].pop("QuestionId")
    deep_output = {k: v for k, v in deep["answer"].items() if k != "question_id"}
    restored = {"question_id": deep["data"]["question"]["id"], **deep_output}
    assert encoded(restored) == encoded(deep["answer"])
    Draft202012Validator.check_schema(deep_schema)
    Draft202012Validator(deep_schema).validate(deep_output)
    members, objects = ledger["member_aliases"], ledger["object_aliases"]
    final_output = c6_aliases(final["answer"], config, members, objects)
    restored = c6_aliases(final_output, config, {v: k for k, v in members.items()}, {v: k for k, v in objects.items()})
    assert encoded(restored) == encoded(final["answer"])
    final_schema = copy.deepcopy(final["request"]["body"]["response_format"]["json_schema"]["schema"])
    final_schema["$defs"]["AlertId"]["enum"] = sorted(members.values())
    final_schema["$defs"]["ObjectKey"]["enum"] = sorted(objects.values())
    Draft202012Validator.check_schema(final_schema)
    old_valid = Draft202012Validator(final["request"]["body"]["response_format"]["json_schema"]["schema"]).is_valid(final["answer"])
    new_valid = Draft202012Validator(final_schema).is_valid(final_output)
    assert new_valid == old_valid
    files.update({"deep-output-schema-not-active.json": deep_schema, "deep-output-replay-not-generated.json": deep_output,
                  "c6-output-schema-not-active.json": final_schema, "c6-output-replay-not-generated.json": final_output})
    deep_refs = dependencies(deep["answer"]["answer"], deep["request"]["source_map"], final["request"]["source_map"], artifacts)
    reports["C6"]["c3_prior_input_blocks"] = blocks
    reports["C6"]["c3_saved_counts"] = {key: len(value) for key, value in prior["analysis"].items() if isinstance(value, list)}
    reports["C6"]["c3_references_to_c6"] = dependencies(prior["analysis"], prior["source_map"], final["request"]["source_map"], artifacts)
    reports["C6"]["deep_references_to_c6"] = deep_refs
    reports["C6"]["analysis_output_percentage"] = round(100 * len(encoded(final["answer"]["analysis"])) / len(encoded(final["answer"])), 2)
    reports["C4.deep"]["question_scope_members"] = deep["data"]["question"]["scope"]["alert_ids"]
    reports["C4.deep"]["assigned_followups"] = deep["data"]["prior_analysis"]["followups"]
    reports["C4.deep"]["available_tools"] = deep["data"]["tool_options"]
    reports["C4.deep"]["action"] = deep["answer"]["action"]
    reports["C4.deep"]["answer_state"] = deep["answer"]["answer"]["state"]
    reports["C4.deep"]["program_facts_key_present"] = "program_facts" in deep["data"]
    files["summary.json"] = {"batch": config["batch"], "captured_at": datetime.now(UTC).isoformat(),
        "mode": "offline_saved_handoff_audit_and_output_roundtrip", "model_calls": 0,
        "database_connections": 0, "created_cases": 0, "created_runs": 0, "deployments": 0,
        "source_run_id": run["id"], "source_sha256": fingerprints, "source_artifacts_verified": len(run_artifacts),
        "c3_candidate_sources": len(ledger["source_map"]),
        "c3_ledger_query_supplement_was_in_original_c1": ledger["query_supplement_was_in_original_c1"],
        "stages": reports,
        "output_adaptation": {"deep_question_bound_by_program_roundtrip_equal": True,
            "deep_shape_valid": True, "c6_alias_roundtrip_equal": True,
            "c6_saved_wire_shape_valid_before": old_valid, "c6_saved_wire_shape_valid_after": new_valid,
            "deep_old_compact_bytes": len(encoded(deep["answer"])), "deep_candidate_compact_bytes": len(encoded(deep_output)),
            "c6_old_compact_bytes": len(encoded(final["answer"])), "c6_candidate_compact_bytes": len(encoded(final_output))},
        "limitations": ["saved_history_not_current_online_execution",
            "source_origin_match_not_full_text_coverage_or_semantic_validation",
            "c3_ledger_adds_offline_paired_A_receipts_not_present_in_historical_C1",
            "output_roundtrip_not_new_model_generation_or_full_runtime_integration",
            "bytes_are_not_tokens_latency_or_quality", "no_new_model_input_candidate_sent_or_capacity_approved"]}
    assert all(sha(ROOT / path) == value for path, value in fingerprints.items())
    output.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        with (output / name).open("x") as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2))
            stream.write("\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "artifacts_verified": len(run_artifacts),
                      "stages": {k: {f: v[f] for f in ("source_count", "same_origin_available")} for k, v in reports.items()},
                      "output_adaptation": files["summary.json"]["output_adaptation"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
