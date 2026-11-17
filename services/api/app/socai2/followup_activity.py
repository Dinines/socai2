"""Backend execution facts, independent of model prose and answer quality."""
import copy

VERSION = "socai2.followup-activity.v1"


def query_record(result):
    receipt = result["result"]
    state, count = receipt["state"], receipt.get("returned_rows")
    outcome = ("not_queried" if state == "skipped" else "failed" if state in {"failed", "timeout"}
               else "data" if state == "completed" and isinstance(count, int) and count > 0
               else "empty" if state == "completed" and count == 0 and not receipt.get("truncated")
               else "unknown")
    return {"query_artifact_id": result["artifact_id"], "projection_id": result["projection_id"],
        "tool_name": receipt["tool_name"], "state": state, "outcome": outcome,
        "returned_rows": count, "truncated": receipt.get("truncated"), "reused": result["reused"]}


def activity(kind, queries=(), *, disposition=None):
    records = copy.deepcopy(list(queries))
    return {"version": VERSION, "kind": kind, "disposition": disposition, "queries": records,
        "new_query_attempt_count": sum(not row["reused"] and row["state"] != "skipped" for row in records)}
