"""Replay immutable r4/r5 inputs/answers under the new local contracts; no I/O services."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))

from app.socai2 import alert_basic_contract as alert
from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import StoreError, encoded
from app.socai2.model_input_view import items


def response_text(raw):
    return next(part["text"] for output in raw["output"] if output["type"] == "message"
        for part in output["content"] if part["type"] == "output_text")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report = {"scope": "local_contract_replay_of_immutable_synthetic_originals",
        "model_calls": 0, "database_calls": 0, "published_results": 0,
        "semantic_quality_accepted": False, "snapshots": [], "answers": [], "incident_inputs": []}
    for batch, directory in (("r4", "20261104T074438-r4-export"), ("r5", "20261104T075920-r5-export")):
        path = max((ROOT / "docs/operations/evidence/socai2-next-acceptance-20261104" / directory).glob("database-*.json"))
        before = sha(path)
        db = json.loads(path.read_text("utf-8"))
        artifacts = {a["id"]: a for a in db["artifacts"]}
        for run in db["runs"]:
            records = {a["kind"]: a for a in artifacts.values() if a["run_id"] == run["id"]
                and a["kind"] in {"model_request", "model_response"}}
            request, response = [records[k]["content_json"] for k in ("model_request", "model_response")]
            request, response = request.get("payload", request), response.get("payload", response)
            data = json.loads(request["body"]["input"][1]["content"])
            text = response_text(response["raw"])
            diagnostics, rejected = [], None
            try:
                if run["kind"] == "baseline":
                    context = next(a["content_json"] for a in artifacts.values() if a["run_id"] == run["id"]
                        and a["schema_version"] == "socai2.baseline-context.v1")
                    analysis.parse(text, request["source_map"], Context.model_validate(context), data["members"])
                else:
                    contract = alert if run["kind"] == "alert_basic" else incident
                    contract.parse(text, request["source_map"], data, diagnostics=diagnostics)
            except (StoreError, analysis.AnalysisRejected) as exc:
                rejected = getattr(exc, "code", str(exc))
            report["answers"].append({"batch": batch, "run_id": run["id"], "kind": run["kind"],
                "response_artifact_id": records["model_response"]["id"],
                "original_validation_error": response.get("validation_error"),
                "local_contract_accepted": rejected is None, "local_error": rejected,
                "diagnostics": diagnostics, "original_usage": response["raw"]["usage"]})
            if run["kind"] == "incident_diagnosis":
                original = artifacts[run["input_artifact_id"]]["content_json"]
                messages, mapping, rebuilt = incident.build(original, run["input_artifact_id"])
                wire = json.loads(messages[1]["content"])
                by_source = {(tuple(i["alert_ids"]), i["field"]): i for i in items(wire)}
                preserved = all(by_source[(tuple(i["alert_ids"]), i["field"])]["value"] == i["value"]
                    and by_source[(tuple(i["alert_ids"]), i["field"])]["role"] == i["role"] for i in data["items"])
                assert preserved and len(encoded(wire)) <= 8192
                report["incident_inputs"].append({"batch": batch, "original_bytes": len(encoded(data)),
                    "new_bytes": len(encoded(wire)), "original_fields_preserved": preserved,
                    "old_item_count": len(data["items"]), "new_item_count": len(mapping),
                    "coverage": rebuilt["members"], "omissions": rebuilt["omissions"],
                    "note": "byte size only; new model quality and token usage not measured"})
        assert sha(path) == before
        report["snapshots"].append({"path": path.relative_to(ROOT).as_posix(), "sha256": before, "unchanged": True})
    report["source_sha256"] = {p.relative_to(ROOT).as_posix(): sha(p)
        for p in sorted((ROOT / "services/api/app/socai2").glob("*.py"))}
    target = ROOT / "docs/operations/socai2-compact-input-replay-20261104.json"
    assert not target.exists(), "immutable receipt; choose a new revision"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"receipt": str(target), "answers": len(report["answers"]),
        "contract_accepted": sum(r["local_contract_accepted"] for r in report["answers"]),
        "incident_bytes": [(r["original_bytes"], r["new_bytes"]) for r in report["incident_inputs"]]}))


if __name__ == "__main__":
    main()
