"""Read saved receipts only; prepare task 2 expectations, not an acceptance runner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-02/final-http-01.json"
OLD = ROOT / "docs/operations/evidence/incident-signal-d4b-20261116-01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    http = json.loads(SOURCE.read_text())["value"]["http"]
    artifacts = {}
    directories = {}
    runs = {}
    for index, response in enumerate(http):
        body = response["body"]
        if not isinstance(body, dict):
            continue
        meta = body.get("artifact") or body.get("metadata")
        if meta and "/artifacts/" in response["path"]:
            artifacts[(meta["run_id"], meta["id"])] = (index, response)
        for item in body.get("items", []):
            if isinstance(item, dict) and item.get("content_url") and item.get("id"):
                directories[(body.get("run_id"), item["id"])] = (index, item)
        if body.get("run") and "/runs/" in response["path"] and not response["path"].endswith("/trace"):
            runs.setdefault(body["run"]["id"], (index, response))

    def artifact(run_id, artifact_id):
        index, response = artifacts[(run_id, artifact_id)]
        directory_index, entry = directories[(run_id, artifact_id)]
        body = response["body"]
        meta = body.get("artifact") or body["metadata"]
        assert response["status"] == 200 and body["availability"] == "available"
        assert entry["content_url"] == response["path"]
        assert entry["sha256"] == meta["sha256"]
        return {"artifact_id": artifact_id, "source_run_id": run_id,
                "sha256": meta["sha256"], "schema_version": meta["schema_version"],
                "http_index": index, "directory_http_index": directory_index,
                "content_url": entry["content_url"]}

    contexts = []
    for (run_id, artifact_id), (index, response) in artifacts.items():
        body = response["body"]
        meta = body.get("artifact") or body["metadata"]
        if meta["schema_version"] == "socai2.baseline-context.v1":
            contexts.append((run_id, artifact_id, index, body["content_json"]))

    prepared = []
    for run_id, c1_id, index, context in contexts:
        run_index, run_response = runs[run_id]
        detail = run_response["body"]
        manifest_id = detail["run"]["input_artifact_id"]
        manifest = artifacts[(run_id, manifest_id)][1]["body"]["content_json"]
        assert c1_id in {ref["id"] for ref in manifest["source_materials"]}
        assert manifest["scope"]["alert_ids"] == context["scope"]["alert_ids"]
        assert len(context["scope"]["alert_ids"]) == detail["input_member_count"]
        alerts = []
        for alert_id, saved in context["alerts"].items():
            triage = saved["triage"]
            aid = triage["source_run_id"]
            ai, actual = runs[aid]
            assert actual["body"]["result"]["id"] == triage["id"]
            assert actual["body"]["result"]["source_run_id"] == aid
            assert actual["body"]["result"]["input_material_id"] == triage["input_material_id"]
            alerts.append({"alert_id": alert_id, "source_run_id": aid,
                           "triage_id": triage["id"], "input_material_id": triage["input_material_id"],
                           "triage_usable": saved["triage_usable"],
                           "triage_freshness_at_capture": saved["triage_freshness"],
                           "triage_run_state": saved["triage_run_state"],
                           "run_http_index": ai, "run_url": actual["path"],
                           "input_artifact": artifact(aid, actual["body"]["run"]["input_artifact_id"])})
        incidents = []
        for incident_id, saved in context["incidents"].items():
            material = saved["analysis_material"]
            iid = material["source_run_id"]
            ii, actual = runs[iid]
            scope = saved["diagnosis_scope"]
            assert iid == scope["source_run_id"] == saved["diagnosis"]["source_run_id"]
            assert actual["body"]["result"]["id"] == saved["diagnosis"]["id"]
            frozen_artifacts = {k: artifact(iid, material[k]["id"])
                                for k in ["input", "response", "receipt_source"]}
            for k, ref in frozen_artifacts.items():
                assert ref["sha256"] == material[k]["sha256"]
            assert frozen_artifacts["input"]["sha256"] == scope["source_fingerprint"]
            incidents.append({"incident_id": incident_id, "source_run_id": iid,
                              "task_id": material["task_id"], "attempt_id": material["attempt_id"],
                              "diagnosis_id": saved["diagnosis"]["id"],
                              "diagnosis_usable": saved["diagnosis_usable"],
                              "receipt_delivery": material["receipt"]["delivery"],
                              "source_member_ids": saved["member_ids"],
                              "case_member_ids": saved["case_member_ids"],
                              "diagnosis_scope": scope, "frozen_artifacts": frozen_artifacts,
                              "run_http_index": ii, "run_url": actual["path"],
                              "current_pointer_at_readback": actual["body"]["is_current_pointer"]})
        prepared.append({"case_id": context["case_id"], "run_id": run_id,
                         "run_http_index": run_index, "run_url": run_response["path"],
                         "scope_alert_ids": context["scope"]["alert_ids"],
                         "comparison_context": detail["run"]["comparison_context"],
                         "result_ids": detail["result_ids"],
                         "manifest": artifact(run_id, manifest_id), "c1": artifact(run_id, c1_id),
                         "alerts": alerts, "incidents": incidents})

    by_run = {r["run_id"]: r for r in prepared}
    for current in prepared:
        previous_id = current["comparison_context"]["previous_run_id"]
        previous = by_run.get(previous_id)
        for key, subject_key in [("alerts", "alert_id"), ("incidents", "incident_id")]:
            old = {r[subject_key]: r for r in previous[key]} if previous else {}
            for item in current[key]:
                prior = old.get(item[subject_key])
                if not previous_id:
                    relation = "initial_reference"
                elif not previous:
                    relation = "previous_source_unavailable"
                elif prior is None:
                    relation = "new_subject_reference"
                elif item["source_run_id"] == prior["source_run_id"]:
                    relation = "reused_source"
                    identity = ["triage_id", "input_material_id"] if key == "alerts" else ["diagnosis_id", "frozen_artifacts"]
                    assert all(item[k] == prior[k] for k in identity)
                else:
                    relation = "new_analysis_source"
                item["relative_to_previous_case_run"] = relation
                item["previous_source_run_id"] = prior["source_run_id"] if prior else None
    whole = sorted([r for r in prepared if len(r["alerts"]) > 1], key=lambda r: len(r["alerts"]))
    single = next(r for r in prepared if len(r["alerts"]) == 1)
    assert [len(r["alerts"]) for r in whole] == [3, 4]
    assert [a["relative_to_previous_case_run"] for a in whole[1]["alerts"]].count("reused_source") == 3
    assert [a["relative_to_previous_case_run"] for a in whole[1]["alerts"]].count("new_subject_reference") == 1
    assert whole[1]["incidents"][0]["relative_to_previous_case_run"] == "new_analysis_source"
    assert single["incidents"][0]["source_run_id"] == whole[0]["incidents"][0]["source_run_id"]
    assert len(single["incidents"][0]["diagnosis_scope"]["case_covered_alert_ids"]) == 1

    boundaries = []
    for variant in ["pg-partial-02", "pg-none-01"]:
        path = OLD / variant / "frozen-context.json"
        context = json.loads(path.read_text())
        incident_id, saved = next(iter(context["incidents"].items()))
        material = saved["analysis_material"]
        covered = sorted({aid for u in material["units"] if u["kind"] == "finding"
                          for aid in u.get("scope", {}).get("alert_ids", [])})
        boundaries.append({"variant": variant, "source_file": str(path.relative_to(ROOT)),
                           "sha256": sha(path),
                           "provenance": "Historical PG C1-only component receipt with controlled D4a-derived dependencies; not new generation or 02 live flow",
                           "case_id": context["case_id"], "case_member_count": len(context["scope"]["alert_ids"]),
                           "incident_id": incident_id, "source_run_id": material["source_run_id"],
                           "diagnosis_scope": saved["diagnosis_scope"], "diagnosis_usable": saved["diagnosis_usable"],
                           "receipt_delivery": material["receipt"]["delivery"],
                           "input_selection": material["input_selection"],
                           "retained_member_finding_alert_ids": covered,
                           "retained_unit_count": len(material["units"]),
                           "case_selected_alert_ids": material["case_selected_alert_ids"],
                           "expected": "Keep actual source and receipt visible even without diagnosis_scope/usable conclusion; do not promote selected/member counts into analyzed coverage or fall back to an older usable diagnosis"})
    assert [len(b["retained_member_finding_alert_ids"]) for b in boundaries] == [1, 0]
    return {"schema": "socai2.workbench-frozen-flow-expectations.v1",
            "status": "prepared_not_page_acceptance", "source_file": str(SOURCE.relative_to(ROOT)),
            "source_sha256": sha(SOURCE), "saved_http_count": len(http),
            "case_rounds": [*whole, single], "boundary_sources": boundaries,
            "missing_source_check": {"provenance": "Proposed controlled in-memory derivative; not yet executed",
                "basis": whole[1]["c1"],
                "changes": ["Remove one frozen alert triage source_run_id from a copy only", "Make previous Case C1 unavailable in a separate direct assertion"],
                "expected": "Unknown source/reuse classification stays unknown; no latest lookup, subject-ID-only reuse inference, fabricated coverage or rewriting of original evidence"},
            "execution_boundary": {"new_http": 0, "new_database_queries": 0, "new_model_calls": 0,
                                   "new_business_writes": 0, "page_tests_run": False, "deployed": False}}


if __name__ == "__main__":
    output = HERE / "preparation.json"
    payload = json.dumps(prepare(), ensure_ascii=False, indent=2) + "\n"
    if output.exists():
        assert output.read_text() == payload, "Preserve existing preparation; use a new evidence file for changed inputs"
    else:
        output.write_text(payload)
    print("Prepared 3 Case rounds, 8 frozen A references, 3 frozen I references; partial/none fixtures retained separately.")
