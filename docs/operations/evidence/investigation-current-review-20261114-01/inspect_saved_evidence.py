"""Summarize existing investigation evidence without calling services or models."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "docs/operations/evidence/fixed-investigation-20261114-01"
OUT = Path(__file__).with_name("saved-evidence-review.json")


def read(path):
    return json.loads(path.read_text())


def duplicate_refs(value, path="$", found=None):
    found = [] if found is None else found
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"source_ids", "evidence_ids", "support_ids", "counter_ids"} and isinstance(child, list):
                repeated = {k: n for k, n in Counter(child).items() if n > 1}
                if repeated:
                    found.append({"path": f"{path}.{key}", "count": len(child), "duplicates": repeated})
            duplicate_refs(child, f"{path}.{key}", found)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            duplicate_refs(child, f"{path}[{i}]", found)
    return found


def main():
    source_files = [SOURCE / "comparison.json", SOURCE / "flow/plan.json"]
    comparison = read(source_files[0])
    plan = read(source_files[1])
    report = {
        "review_date": "2026-11-14",
        "source_batch": comparison["batch"],
        "mode": "offline_read_only",
        "counts": comparison["counts"],
        "real_model_calls_in_source_batch": comparison["real_model_calls"],
        "new_model_calls_in_review": 0,
        "usage_in_source_batch": comparison["usage"],
        "cost": comparison["cost"],
        "quality": comparison["quality"],
        "cases": [],
        "schema_receiver_gaps": [],
    }
    # Read only the non-secret switches relevant to the unavailable query path.
    def switches(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"AISOC_DISABLE_CLICKHOUSE", "SOCAI2_SOURCE_PRODUCT_HOST_ENABLED"}:
                    report.setdefault("source_batch_switches", {})[key] = child
                switches(child)
        elif isinstance(value, list):
            for child in value:
                switches(child)
    switches(plan)
    summaries = {}
    for case in ("C01", "C02", "C03"):
        folder = SOURCE / "flow" / case
        summary_file, database_file = folder / "summary.json", folder / "export/database.json"
        source_files.extend([summary_file, database_file])
        summary, database = read(summary_file), read(database_file)
        summaries[case] = summary
        run = next(r for r in database["runs"] if r["id"] == summary["run_id"])
        steps = [s for s in database["run_steps"] if s["run_id"] == run["id"]]
        tool_receipts = []
        for artifact in database["artifacts"]:
            body = artifact.get("content_json")
            if artifact["run_id"] == run["id"] and artifact["kind"] == "tool_response" and isinstance(body, dict):
                tool_receipts.append({"tool": body.get("tool_name"), "state": body.get("state"),
                    "rows": len(body["rows"]) if isinstance(body.get("rows"), list) else None})
        deep = []
        for call in summary["calls"]:
            if call["stage"] != "C4.deep":
                continue
            answer_file, input_file = folder / call["answer_file"], folder / call["input_file"]
            request_file = folder / call["request_file"]
            source_files.extend([answer_file, input_file, request_file])
            answer = read(answer_file)
            messages = read(request_file)["body"]["messages"]
            deep.append({"call": call["number"], "action": answer["action"],
                "answer_state": answer["answer"]["state"],
                "no_query_candidates_in_input": any("无可用查询候选" in m.get("content", "") for m in messages)})
        report["cases"].append({
            "case": case, "case_id": summary["case_id"], "run_id": run["id"],
            "run_state": run["state"], "stop_reason": run["stop_reason"],
            "seconds": round((datetime.fromisoformat(run["ended_at"]) - datetime.fromisoformat(run["started_at"])).total_seconds(), 3),
            "result": {k: summary["results"][0][k] for k in ("validation_state", "conclusion_state", "delivery_state")},
            "current_assessment_present": summary["current_assessment"] is not None,
            "c4_query_steps": sum(s["stage_code"] == "C4.query" for s in steps),
            "deep": deep, "tool_receipts": sorted(tool_receipts, key=lambda r: r["tool"]),
            "calls": [{k: c.get(k) for k in ("number", "stage", "characters", "sources", "validation_error", "usage")}
                      for c in summary["calls"]],
        })
    for folder, number, answer_name in (
        ("E01/A1", 2, "call-02-answer.txt"),
        ("C02", 3, "call-03-C6-answer.txt"),
        ("C03", 5, "call-05-C6-answer.txt"),
    ):
        request_file = SOURCE / "flow" / folder / f"calls/call-{number}-intent.json"
        answer_file = SOURCE / "flow" / folder / "review" / answer_name
        source_files.extend([request_file, answer_file])
        request, answer = read(request_file)["body"], read(answer_file)
        schema = request["response_format"]["json_schema"]["schema"]
        errors = list(Draft202012Validator(schema).iter_errors(answer))
        rejection = (next(a["stop_reason"] for a in comparison["A_I"] if a["group"] == "E01" and a["stage"] == "A1")
            if folder == "E01/A1" else next(c["validation_error"] for c in summaries[folder]["calls"] if c["number"] == number))
        report["schema_receiver_gaps"].append({
            "subject": folder, "call": number, "saved_receiver_error": rejection,
            "valid_against_sent_json_schema": not errors,
            "schema_errors": [{"path": list(e.path), "validator": e.validator} for e in errors],
            "duplicate_refs": duplicate_refs(answer),
            "answered_without_evidence": [q["id"] for q in answer.get("analysis", {}).get("questions", [])
                                          if q["state"] == "answered" and not q["evidence_ids"]],
        })
    report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(set(source_files))}
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists():
        if OUT.read_text() != serialized:
            raise SystemExit("Existing review differs; preserve it and use a new review batch.")
    else:
        OUT.write_text(serialized)
    print(json.dumps({"cases": len(report["cases"]), "schema_gap_examples": len(report["schema_receiver_gaps"]),
        "all_three_original_rejected_answers_pass_sent_schema": all(r["valid_against_sent_json_schema"] for r in report["schema_receiver_gaps"]),
        "source_files": len(report["source_sha256"]), "output": str(OUT.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
