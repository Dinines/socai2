"""Check saved ASGI replies against the same completed Run, without any I/O service."""
import hashlib
import json

from review_saved import BATCH, HERE, ROOT, read

READBACK = ROOT / "docs/operations/evidence/quality-continuation-d2-20261116-01/real-02-readback-03"


def main():
    db, received, receipt = read(BATCH / "database.json"), read(READBACK / "http.json"), read(READBACK / "result.json")
    run, result = db["runs"][0], db["results"][0]
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    check("readback_completed_without_new_business_or_model_calls", receipt["state"] == "passed" and
          receipt["model_calls"] == receipt["business_writes"] == 0 and receipt["http_transport"] == "ASGITransport")
    check("same_original_database", db == read(READBACK / "database.json"))
    check("all_19_table_fingerprints_unchanged", receipt["before"] == receipt["after"] ==
          receipt["before_http"] == receipt["after_http"] and len(receipt["before"]) == 19)
    check("original_real02_evidence_unchanged", receipt["original_evidence_unchanged"] and all(
          hashlib.sha256((BATCH / name).read_bytes()).hexdigest() == sha
          for name, sha in receipt["original_evidence_sha256"].items()))
    check("running_slot_released_in_recorded_redis_read", receipt["running_slots"] == 0)
    check("50_unique_read_only_requests_all_200", len(received) == receipt["http_gets"] == 50 and
          len({r["path"] for r in received}) == 50 and all(r["method"] == "GET" and r["status"] == 200 for r in received))
    replies = {r["path"]: r["body"] for r in received}
    base = f"/api/v1/socai2/cases/{result['case_id']}"
    task = replies[base + "/analysis-tasks/" + receipt["task_id"]]
    detail = replies[base + "/runs/" + run["id"]]
    output = replies[base + "/results/" + result["id"]]
    check("task_points_to_same_completed_run", task["status"] == "completed" and
          task["task_id"] == receipt["task_id"] and task["latest_run_id"] == run["id"] and task["retry_count"] == 0)
    check("run_and_result_identity_matches_database", detail["run"]["id"] == output["run"]["id"] == run["id"] and
          detail["run"]["state"] == "completed" and detail["result_ids"] == [result["id"]] and
          output["result"]["source_run_id"] == run["id"] and output["result"]["id"] == result["id"])
    check("all_17_steps_returned_from_same_run", len(detail["steps"]) == 17 and
          {s["id"] for s in detail["steps"]} == {s["id"] for s in db["run_steps"]} and
          all(s["run_id"] == run["id"] for s in detail["steps"]) and not detail["steps_truncated"])
    check("all_47_artifacts_listed_without_truncation", len(detail["artifacts"]) == 47 and
          {a["id"] for a in detail["artifacts"]} == {a["id"] for a in db["artifacts"]} and not detail["artifacts_truncated"])
    for field in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "findings", "questions",
                  "delivery_state", "closing_note", "recommendations", "case_impact", "report_artifact_id"):
        check("HTTP_result_preserves_" + field, output["result"][field] == result[field])
    full = next(a for a in db["artifacts"] if (a["content_json"] or {}).get("type") == "delivery_report")
    check("HTTP_full_delivery_and_quality_exactly_saved", output["delivery"]["detail"] == full["content_json"] and
          output["delivery"]["detail_artifact_id"] == full["id"])
    for artifact in db["artifacts"]:
        body = replies[base + "/runs/" + run["id"] + "/artifacts/" + artifact["id"]]
        check("artifact_exact_content_" + artifact["id"], body["artifact"]["id"] == artifact["id"] and
              body["artifact"]["run_id"] == run["id"] and body["content_json"] == artifact["content_json"] and
              body["content_text"] == artifact["content_text"] and body["artifact"]["sha256"] == artifact["sha256"])
    review = {"status": "passed", "checks": checks, "check_count": len(checks), "http_gets": 50,
              "artifacts": 47, "steps": 17, "run_id": run["id"], "result_id": result["id"],
              "transport": "ASGITransport with real local PostgreSQL; not TCP or 21 deployment",
              "reviewer_network_calls": 0, "reviewer_database_calls": 0, "reviewer_model_calls": 0,
              "source_hashes": {str((READBACK / name).relative_to(ROOT)):
                                hashlib.sha256((READBACK / name).read_bytes()).hexdigest()
                                for name in ("result.json", "database.json", "http.json")}}
    (HERE / "http-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": review["status"], "checks": len(checks), "http_gets": 50, "artifacts": 47, "steps": 17}))


if __name__ == "__main__":
    main()
