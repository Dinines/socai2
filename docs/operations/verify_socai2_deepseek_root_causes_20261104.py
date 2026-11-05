"""Offline attribution audit of immutable synthetic r4/r5 artifacts; no model or DB."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"services/api"))
import jsonschema
from app.socai2 import alert_basic_contract as alert
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_model_view import blocked
from app.socai2.baseline_store import StoreError, encoded


def sha(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def response_text(raw):
    return next(p["text"] for i in raw["output"] if i["type"] == "message"
                for p in i["content"] if p["type"] == "output_text")


def main():
    report = {"scope": "offline_immutable_synthetic_records", "provider_calls": 0,
        "database_calls": 0, "production_validation_changed": False, "snapshots": [], "observations": []}
    for batch, folder in (("r4", "20261104T074438-r4-export"), ("r5", "20261104T075920-r5-export")):
        base = ROOT/"docs/operations/evidence/socai2-next-acceptance-20261104"/folder
        path = max(base.glob("database-*.json"))
        db = json.loads(path.read_text("utf-8"))
        report["snapshots"].append({"batch": batch, "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        artifacts = {a["id"]: a for a in db["artifacts"]}
        for run in db["runs"]:
            records = {a["kind"]: a for a in db["artifacts"] if a["run_id"] == run["id"]
                and a["kind"] in {"model_request", "model_response"}}
            request, response = [records[k]["content_json"] for k in ("model_request", "model_response")]
            request, response = request.get("payload", request), response.get("payload", response)
            body, raw = request["body"], response["raw"]
            data = json.loads(body["input"][1]["content"])
            answer = json.loads(response_text(raw))
            schema = body["text"]["format"]["schema"]
            errors = list(jsonschema.Draft202012Validator(schema).iter_errors(answer))
            observation = {"batch": batch, "run_id": run["id"], "kind": run["kind"],
                "run_state": run["state"], "validation_error": response.get("validation_error"),
                "request_artifact_id": records["model_request"]["id"],
                "response_artifact_id": records["model_response"]["id"],
                "model": body["model"], "reasoning": body["reasoning"],
                "schema_sha256": sha(schema), "schema_echo_matches": schema == raw["text"]["format"]["schema"],
                "output_matches_sent_schema": not errors,
                "schema_errors": [{"validator": e.validator, "path": list(e.absolute_path)} for e in errors],
                "provider_usage": raw["usage"]}
            if run["kind"] in {"alert_basic", "incident_diagnosis"}:
                contract = alert if run["kind"] == "alert_basic" else incident
                # Diagnostic ablation only. No source/role/shape/ownership check is bypassed,
                # no answer is edited, and nothing is published or written to the database.
                try:
                    with patch.object(contract, "source_alias_in_prose", return_value=False):
                        contract.parse(response_text(raw), request["source_map"], data)
                    observation["all_other_parser_checks_pass_when_only_alias_rule_disabled"] = True
                except StoreError as exc:
                    observation["all_other_parser_checks_pass_when_only_alias_rule_disabled"] = False
                    observation["remaining_parser_error"] = getattr(exc, "code", type(exc).__name__)
            if run["kind"] == "baseline":
                observation["sent_conflict_finding_ids_schema"] = schema["$defs"]["Conflict"]["properties"]["finding_ids"]
                observation["actual_conflict_finding_ids"] = [c["finding_ids"] for c in answer["conflicts"]]
                observation["member_coverage_in_input"] = data["members"]
                observation["input_omission_counts"] = data["omission_counts"]
            if run["kind"] == "incident_diagnosis":
                source = artifacts[run["input_artifact_id"]]["content_json"]
                messages, _, rebuilt = incident.build(source, run["input_artifact_id"])
                assert json.loads(messages[1]["content"]) == data, "frozen input replay must match actual model view"
                observation["frozen_input_rebuild_matches"] = True
                observation["triage_members"] = []
                for index, member in enumerate(source["members"]):
                    field = f"$.members.{index}.triage"
                    paired = member["triage"]
                    if paired is None:
                        continue
                    projected = {k: paired.get(k) for k in ("verdict", "rationale", "confidence", "score_state", "assessed_at")}
                    state = {"alert_id": member["alert"]["id"], "triage_id": paired["id"],
                        "triage_source_run": paired["source_run_id"], "projected_bytes": len(encoded(projected)),
                        "guard_blocks_full_source": blocked(paired), "guard_blocks_projected_values": blocked(projected),
                        "input_flags": data["members"][index],
                        "actually_visible": any(i.get("field") == field for i in data["items"]),
                        "omission_records": [v for v in rebuilt["omission_details"] if v["source"]["source_path"] == field]}
                    if not state["actually_visible"]:
                        probe = copy.deepcopy(data)
                        probe["items"].append({"id": "S99", "alert_ids": [member["alert"]["id"]],
                            "field": field, "role": "prior_analysis", "value": projected})
                        removed = []
                        for item in list(reversed(probe["items"])):
                            if len(encoded(probe)) <= 8192 - 256:
                                break
                            if item["role"] == "source_label":
                                removed.append({"field": item["field"], "id": item["id"]})
                                probe["items"].remove(item)
                        state["priority_counterfactual"] = {"note": "illustrative size check, not a published input",
                            "original_bytes": len(encoded(data)), "reordered_bytes": len(encoded(probe)),
                            "fits_same_limit": len(encoded(probe)) <= 8192 - 256,
                            "observations_before": sum(i["role"] == "observation" for i in data["items"]),
                            "observations_after": sum(i["role"] == "observation" for i in probe["items"]),
                            "removed_lower_priority_labels": removed}
                    observation["triage_members"].append(state)
            report["observations"].append(observation)
    path = ROOT/"docs/operations/socai2-deepseek-root-cause-audit-20261104.json"
    assert not path.exists(), "audit receipt is immutable; choose a new revision"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", "utf-8")
    print(json.dumps({"receipt": str(path), "runs_reviewed": len(report["observations"]), "model_calls": 0}))


if __name__ == "__main__":
    main()
