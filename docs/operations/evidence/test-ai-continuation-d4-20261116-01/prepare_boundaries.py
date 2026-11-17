"""Explicit D4 structural counterexamples; no product receiver imports."""
import argparse
import copy
import json
from pathlib import Path

from prepare import HERE, catalog, save, sha


def prepare(out):
    out.mkdir(exist_ok=False)
    mothers = {stage: json.loads((HERE / "fixtures-02" / stage / "mother.txt").read_text()) for stage in ("A", "I")}
    variants = []

    def add(stage, name, value, expected, *, raw=None):
        text = raw if raw is not None else json.dumps(value, ensure_ascii=False)
        (out / (name + ".txt")).write_text(text)
        body = {"stage": stage, "name": name, "finish_reason": "stop", "fragment_sha256": sha(text),
            "source": "explicit controlled derivative of fixtures-02 real mother; no new generation",
            "source_mother_sha256": sha((HERE / "fixtures-02" / stage / "mother.txt").read_bytes()),
            "expectation_basis": "stage11 design section 11.1; fixed functional conditions, not receiver output",
            "expected_dispatch_paths": [], "expected_quality": "not_checked", **expected}
        if raw is None:
            body["complete_value_catalog"] = catalog(text)
        save(out / (name + ".expected.json"), body)
        variants.append({k: body[k] for k in ("stage", "name", "fragment_sha256")})

    add("A", "a-rationale-only", {"rationale": mothers["A"]["rationale"]}, {
        "must_retain_paths": ["$.rationale"], "must_not_create_fields": ["verdict", "confidence", "evidence_ids"],
        "expected_usable_result": False, "expected_delivery": "partial"})
    a = mothers["A"]
    duplicate = '{"verdict":"needs_review",' + json.dumps(a, ensure_ascii=False)[1:]
    add("A", "a-duplicate-verdict", None, {
        "must_retain_paths": [], "must_reject_paths": ["$.verdict"], "expected_usable_result": False,
        "expected_delivery": "none", "reason": "duplicate key stops parsing; later fields were not read"}, raw=duplicate)
    late_duplicate = json.dumps(a, ensure_ascii=False)[:-1] + ',"verdict":"needs_review"}'
    add("A", "a-late-duplicate-verdict", None, {
        "must_retain_paths": ["$.rationale", "$.recommendations[0]", "$.recommendations[1]"],
        "must_reject_paths": ["$.verdict"], "expected_usable_result": False, "expected_delivery": "partial",
        "reason": "previous independent units survive a later duplicate; no reading past the error"}, raw=late_duplicate)
    empty = copy.deepcopy(a)
    empty["recommendations"] = []
    add("A", "a-explicit-empty-recommendations", empty, {"must_retain_paths": ["$.recommendations"],
        "explicit_empty_path": "$.recommendations", "expected_usable_result": True, "expected_delivery": "complete"})
    i = copy.deepcopy(mothers["I"])
    aliases = [m["alert_ref"] for m in i["members"]]
    i["members"][0]["alert_ref"] = "foreign-member"
    add("I", "i-unknown-member", i, {"must_reject_paths": ["$.members[0]"],
        "must_retain_paths": ["$.members[1]", "$.members[2]"], "expected_original_member_aliases": aliases[1:],
        "expected_usable_result": False, "expected_delivery": "partial"})
    i = copy.deepcopy(mothers["I"])
    i["members"][1]["alert_ref"] = aliases[0]
    add("I", "i-duplicate-member", i, {"must_reject_paths": ["$.members[0]", "$.members[1]"],
        "must_retain_paths": ["$.members[2]"], "expected_original_member_aliases": aliases[2:],
        "expected_usable_result": False, "expected_delivery": "partial"})
    i = copy.deepcopy(mothers["I"])
    i["open_questions"][0]["alert_refs"] = ["foreign-member"]
    add("I", "i-question-original-index", i, {"must_reject_paths": ["$.open_questions[0]"],
        "must_retain_paths": ["$.open_questions[1]"], "retained_question_original_indices": [1],
        "expected_question_ids": ["Q2"], "expected_usable_result": True, "expected_delivery": "partial"})
    save(out / "manifest.json", {"status": "prepared_not_product_tested", "variants": variants,
        "model_calls": 0, "database_calls": 0, "product_parser_calls": 0})
    print(json.dumps({"variants": len(variants), "status": "prepared_not_product_tested"}))


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--output", type=Path, required=True)
    prepare(cli.parse_args().output)
