"""Recompute only D4b's frozen business projection from actual saved sources.

No SQL, receiver or model execution. Existing PG source rows remain immutable.
"""
import argparse
import hashlib
import json
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "services/api"))


def forbidden(*args, **kwargs):
    raise AssertionError("Current D4b saved-source review must remain offline")


def run(readback, output):
    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    from app.socai2 import ai_stage_delivery, case_incident_material

    ai_stage_delivery.receive = forbidden
    files = [readback / name for name in ("frozen-context-after-new-alert.json", "source-artifacts-readback.json", "database-readback.json")]
    files += [ROOT / "services/api/app/socai2" / name for name in (
        "case_incident_material.py", "case_update_inputs.py", "baseline_store.py", "stage_delivery.py")]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    context, originals, database = [json.loads(p.read_text()) for p in files[:3]]
    iid, item = next(iter(context["incidents"].items()))
    expected = item["analysis_material"]
    artifacts = {row["id"]: row for row in originals}
    candidate = {
        "run": next(row for row in database["runs"] if row["id"] == expected["source_run_id"]),
        "task": next(row for row in database["analysis_tasks"] if row["id"] == expected["task_id"]),
        "attempt": next(row for row in database["analysis_attempts"] if row["id"] == expected["attempt_id"]),
        "input": artifacts[expected["input"]["id"]], "response": artifacts[expected["response"]["id"]],
        "receipt": artifacts[expected["receipt_source"]["id"]],
        "originals": [artifacts[o["id"]] for o in expected["originals"]],
    }
    actual, reasons = case_incident_material.freeze(iid, candidate, list(context["alerts"]))
    assert actual, reasons
    assert actual["business_view"] == expected["business_view"], "current business signal differs from saved C1"
    assert actual == expected, "current frozen material differs from saved C1"
    assert before == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    result = {"status": "passed", "branch": readback.name, "case_run_id": candidate["run"]["id"],
              "checks": ["current_business_view_equals_saved_C1", "current_full_material_equals_saved_C1", "all_source_files_unchanged"],
              "reasons": reasons, "sources": before, "new_requests": 0, "new_model_calls": 0,
              "scope": "current freeze projection only; stored receiver output, no reparse"}
    (output / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (output / "review-source.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"branch": readback.name, "status": "passed", "checks": 3, "new_requests": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--readback", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    run(args.readback.resolve(), args.output.resolve())
