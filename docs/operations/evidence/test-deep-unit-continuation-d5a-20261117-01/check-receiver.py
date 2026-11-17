"""Check the handed-off receiver against already-frozen independent expectations."""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.socai2.case_deep_delivery import receive

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    assert Path(args.out).name == args.out and not (HERE / args.out).exists()
    manifest = json.loads((HERE / "preparation.json").read_text())
    source = manifest["sources"][0]
    request_path = next(p for p in source["files"] if p.endswith("/request-artifact.json"))
    prepared = json.loads((ROOT / request_path).read_text())["content_json"]["payload"]
    paths = ["case_deep_delivery.py", "closed_json_units.py", "baseline_deep_contract.py", "case_citation_quality.py", "citation_quality.py", "stage_delivery.py"]
    code = {p: sha(ROOT / "services/api/app/socai2" / p) for p in paths}
    original_hashes = {p: sha(ROOT / p) for s in manifest["sources"] for p in s["files"]}
    checks = []
    for fixture in manifest["fixtures"]:
        content = (HERE / fixture["path"]).read_text()
        assert hashlib.sha256(content.encode()).hexdigest() == fixture["received_sha256"]
        expected = fixture["expected"]
        received_id = uuid5(NAMESPACE_URL, "socai2:controlled-d5a:" + fixture["received_sha256"])
        actual = receive(content, prepared, received_id, finish_reason=fixture["controlled_finish_reason"])
        result = {"fixture": fixture["id"], "status": "passed", "received_original_id": str(received_id), "original_kind": "controlled_in_memory_fragment_not_persisted", "actual": {k: v.model_dump(mode="json") if hasattr(v, "model_dump") else v for k, v in actual.items()}}
        try:
            assert (actual["answer"] is not None) == expected["answer_retained"], "answer_presence"
            assert actual["answer"] == expected["answer_value"], "answer_original_value"
            assert (actual["decision"] is not None) == expected["non_query_decision_eligible"], "decision_eligibility"
            if actual["decision"] is not None:
                assert actual["decision"].action == "answer", "decision_action"
                assert actual["decision"].question_id == prepared["case_boundary"]["question_id"], "frozen_question"
            assert actual["use"]["dispatch_paths"] == [], "query_not_proposed"
            assert not any(actual["use"][k] for k in ["conclusion_available", "adoption_eligible", "comparison_eligible"]), "question_answer_not_final_case"
            units = {u["path"]: u for u in actual["retained_units"]}
            assert set(units) == {"$." + k for k in expected["complete_fields"]}, "closed_fields"
            for unit in units.values():
                start, end = unit["value_span"]
                assert unit["original_artifact_id"] == str(received_id), "received_identity"
                assert unit["original_content_path"] == "$.raw.choices[0].message.content", "received_path"
                assert 0 <= start < end <= len(content), "actual_fragment_span"
                assert hashlib.sha256(content[start:end].encode()).hexdigest() == unit["value_sha256"], "actual_fragment_hash"
                assert json.loads(content[start:end]) == unit["value"], "actual_fragment_value"
            if expected["answer_retained"]:
                assert units["$.answer"]["value_span"] == expected["answer_source_span"], "independent_answer_span"
                assert units["$.answer"]["value_sha256"] == expected["answer_source_sha256"], "independent_answer_hash"
            if fixture["controlled_finish_reason"] == "length":
                assert actual["parse"]["truncated"] and "provider_length" in actual["parse"]["reasons"], "finish_reason_preserved"
        except AssertionError as exc:
            result.update(status="failed", failed_check=str(exc))
        checks.append(result)
    unchanged = code == {p: sha(ROOT / "services/api/app/socai2" / p) for p in paths}
    originals_unchanged = original_hashes == {p: sha(ROOT / p) for p in original_hashes}
    assert unchanged and originals_unchanged
    report = {"status": "passed_for_receiver_only" if all(x["status"] == "passed" for x in checks) else "failed", "expectations_sha256": sha(HERE / "preparation.json"), "code_sha256": code, "sources_unchanged": originals_unchanged, "code_unchanged": unchanged, "checks": checks, "new_model_calls": 0, "database_calls": 0, "http_calls": 0, "unverified": ["Actual query dispatch effects (these mother responses propose answer)", "stage_delivery database persistence and HTTP reading", "deep_summary and C6 actual saved request", "D5b/D5c and 21/UI"]}
    with (HERE / args.out).open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"status": report["status"], "fixtures": len(checks), "failed": [{"fixture": c["fixture"], "check": c["failed_check"]} for c in checks if c["status"] != "passed"], "new_model_calls": 0}))


if __name__ == "__main__":
    main()
