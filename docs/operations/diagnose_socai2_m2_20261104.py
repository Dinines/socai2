"""Fixed-answer diagnostics only; counterfactual copies never become results."""
import copy
import json

import jsonschema
from app.socai2 import alert_basic_contract
from app.socai2.model_input_view import items
from evaluate_socai2_models_20261104 import ROOT, sha, write

OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m2"


def read(path):
    return json.loads(path.read_text("utf-8"))


def without_unique(value):
    if isinstance(value, dict):
        return {k: without_unique(v) for k, v in value.items() if k != "uniqueItems"}
    if isinstance(value, list):
        return [without_unique(v) for v in value]
    return value


def check_refs(schema):
    paths = []
    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                ref = value["$ref"]
                assert ref.startswith("#/")
                target = schema
                for name in ref[2:].split("/"):
                    target = target[name.replace("~1", "/").replace("~0", "~")]
                paths.append(ref)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(schema)
    return len(paths)


def main():
    bundle = read(OUT / "plan-and-packets.json")
    packets = {p["id"]: p for p in bundle["packets"]}
    cells = {p["id"]: p for p in bundle["cells"]}
    rows = {r["cell"]: r for r in read(OUT / "parsed-results.json")["cells"]}
    m1 = read(OUT.parent / "m1/plan-and-packets.json")
    old_packets = {p["id"]: p for p in m1["packets"]}
    schema_checks = {}
    for pid, packet in packets.items():
        small, deep = [cells[pid + "-" + backend]["body"] for backend in ("small", "deepseek")]
        standard = {k: v for k, v in deep["text"]["format"].items() if k != "type"}
        assert without_unique(standard) == small["response_format"]["json_schema"]
        assert small["messages"] == deep["input"] == packet["messages"]
        assert small["temperature"] == deep["temperature"] == 0
        assert small["max_tokens"] == deep["max_output_tokens"] == 3000
        assert packet["source_sha256"] == old_packets[pid]["source_sha256"]
        schema = packet["response_format"]["json_schema"]["schema"]
        jsonschema.Draft202012Validator.check_schema(schema)
        schema_checks[pid] = {"canonical_schema_valid": True, "local_refs_resolved": check_refs(schema),
            "same_frozen_source_as_m1": True, "paired_messages_equal": True,
            "wire_schema_diff_only_uniqueItems": True}

    visible = {}
    for pid, packet in packets.items():
        if pid == "C3-current":
            continue
        def by_field(packet):
            return {(tuple(i.get("alert_ids", [])), i["field"], i["role"]): i["value"] for i in items(packet["data"])}
        old, new = by_field(old_packets[pid]), by_field(packet)
        changed = [key for key in old.keys() & new.keys() if old[key] != new[key]]
        visible[pid] = {"old_count": len(old), "new_count": len(new), "changed_shared_field_values": changed,
            "added_fields": sorted(new.keys() - old.keys()),
            "omitted_old_fields": sorted(old.keys() - new.keys())}
        assert not changed

    original = rows["A0-current-small"]["answer"]
    counterfactual = copy.deepcopy(original)
    mapping = packets["A0-current"]["source_map"]
    counterfactual["decision_basis"]["source_ids"] = [s for s in counterfactual["decision_basis"]["source_ids"]
        if mapping[s]["ref"]["role"] == "observation"]
    assert len(counterfactual["decision_basis"]["source_ids"]) == 2
    # Demonstrates the limit of role-only checks; never modify the received answer.
    accepted = alert_basic_contract.parse(json.dumps(counterfactual, ensure_ascii=False), mapping, packets["A0-current"]["data"])
    assert accepted.verdict == "benign" and original == rows["A0-current-small"]["answer"]
    counterexample = {"kind": "offline_counterfactual_not_a_model_answer_or_adoption",
        "only_change": "remove source_label from decision_basis.source_ids; leave unsupported claim unchanged",
        "remaining_paths": [mapping[s]["ref"]["source_path"] for s in counterfactual["decision_basis"]["source_ids"]],
        "parser_accepts": True, "meaning": "host/user observations alone still do not prove authorization; role gate is insufficient for truth"}

    member = rows["I-current-small"]["answer"]["members"][1]
    duplicates = sorted({s for s in member["source_ids"] if member["source_ids"].count(s) > 1})
    assert duplicates == ["N1_S14"]
    old_summary = read(ROOT / "docs/operations/socai2-model-evaluation-m1-20261104.json")
    assert all(sha((ROOT / p).read_bytes()) == h for p, h in old_summary["evidence_sha256"].items())
    result = {"schema_checks": schema_checks, "visible_field_comparison_to_m1": visible,
        "small_A0_main_refs_have_observation_but_new_decision_basis_gate_rejects": True,
        "small_A1_both_main_direct_source_and_new_basis_gates_reject": True,
        "small_I_duplicate_source_ids": duplicates, "basis_gate_counterexample": counterexample,
        "deepseek_A_400": {"both_rejected_before_answer": True, "error_response_body_saved": False,
            "exact_provider_rejection_reason": "unknown", "hypothesis_only": "new A output-contract compatibility; nullable DecisionBasis is one changed shape, not proven cause",
            "I_and_C3_same_endpoint_succeeded": True},
        "original_m1_evidence_hashes_verified": len(old_summary["evidence_sha256"]),
        "m2_original_result_hashes_verified": all(sha((OUT / "remote" / (r["cell"] + "-result.json")).read_bytes()) == r["result_sha256"] for r in rows.values()),
        "new_model_calls": 0, "business_adoptions": 0,
        "official_reference": "https://api-docs.deepseek.com/api/create-response/",
        "official_reference_limit": "documents json_schema support, does not establish the exact cause of these two HTTP400 responses"}
    write(OUT / "offline-diagnostics.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
