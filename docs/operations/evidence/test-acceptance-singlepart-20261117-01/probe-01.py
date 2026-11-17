"""Bounded offline review probes; saved receipts are not new live execution."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance_contract import Profile
from acceptance_materials import MaterialError, control, read_json
from acceptance_runtime_contract import Execution
from acceptance_session import prepare_execution
from acceptance_verify import verify_readback


def load(path):
    value = json.loads(path.read_bytes())
    return value.get("value", value)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = HERE / "probe-01"
    out.mkdir(exist_ok=False)
    source = ROOT / "docs/operations/evidence/acceptance-materials-20261117-01/packages/streaming"
    source_hashes = {str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file()}
    materials = out / "object-raw-data"
    shutil.copytree(source, materials)
    for relative in ("part1/context/002.json", "part1/alerts/001.json"):
        path = materials / relative
        value = read_json(path)
        ocsf = value["ocsf_event"] if "/context/" in relative else value["raw_event"]["ocsf_event"]
        ocsf["raw_data"] = json.loads(ocsf["raw_data"])
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    profile = control(Profile, read_json(ROOT / "tools/testdata/acceptance-examples/profile.json"), "profile")
    with patch("socket.socket", side_effect=AssertionError("offline review")):
        prepare_execution(materials, profile, Execution(schema_version="socai2.acceptance-execution.v1",
            execution_id="independent-3b-object-raw", time_policy="preserve"), out / "prepared")
    wire = read_json(out / "prepared/wire/part1/context/002.json")
    old = read_json(materials / "part1/context/002.json")
    mapping = {"prepare_returned": "prepared_not_executed", "old_source_id": old["event_id"],
               "new_source_id": wire["event_id"], "nested_raw_uid": wire["ocsf_event"]["raw_data"]["uid"],
               "identity_consistent": wire["event_id"] == wire["ocsf_event"]["raw_data"]["uid"]}
    assert mapping["nested_raw_uid"] == mapping["old_source_id"] != mapping["new_source_id"]

    evidence = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-02"
    pg_path, http_path = evidence / "final-pg.json", evidence / "final-http-01.json"
    pg, responses = load(pg_path)["rows"], load(http_path)["http"]
    rid = "10535c76-6a2e-5943-8cfc-efcc31c456a9"
    run = next(r for r in pg["runs"] if r["id"] == rid)
    iid = run["incident_id"]
    detail_path = f"/api/v1/socai2/incidents/{iid}/analysis/runs/{rid}"
    saved = {r["path"]: r["body"] for r in responses}
    selection = saved[detail_path]["input_selection"]
    attempts = [a for a in pg["analysis_attempts"] if a["run_id"] == rid]
    task_ids = {a["task_id"] for a in attempts}
    subset = {"alerts": [], "cases": [], "case_alerts": [], "results": [], "alert_assessments": [],
              "incidents": [r for r in pg["incidents"] if r["id"] == iid], "runs": [run],
              "analysis_tasks": [t for t in pg["analysis_tasks"] if t["id"] in task_ids],
              "analysis_attempts": attempts,
              "incident_diagnoses": [d for d in pg["incident_diagnoses"] if d["source_run_id"] == rid]}
    for table in ("run_steps", "run_members", "artifacts"):
        subset[table] = [r for r in pg[table] if r["run_id"] == rid]
    all_members = [r for r in pg["incident_alerts"] if r["incident_id"] == iid]
    subset["incident_members"] = [r for r in all_members if r["alert_id"] in selection["selected_alert_ids"]]

    class SavedReader:
        """Replay saved bodies; directory assembled from that one saved Run."""
        def __init__(self, mutate_result=False):
            self.mutate_result = mutate_result
            self.reads = []

        def request(self, method, path):
            assert method == "GET"
            value = copy.deepcopy(saved[path])
            self.reads.append(path)
            if self.mutate_result and path == detail_path:
                value["result"]["summary"] = "CONTROLLED_REVIEW_VALUE_DIFFERENT_FROM_PG"
            return value

        def pages(self, path, params=None):
            if path == "/api/v1/socai2/analysis-runs":
                assert params == {"subject_type": "incident", "subject_id": iid}
                return [{"run_id": rid, "detail_url": detail_path}]
            pages = [r["body"] for r in responses if urlsplit(r["path"]).path == path]
            assert pages, path
            items = [item for page in pages for item in page["items"]]
            assert len(items) == len({i["id"] for i in items}) == pages[-1]["total"]
            return copy.deepcopy(items)

    reader = SavedReader()
    with patch("socket.socket", side_effect=AssertionError("offline review")):
        baseline = verify_readback(reader, subset)
        altered_result = verify_readback(SavedReader(mutate_result=True), subset)
        current_members = copy.deepcopy(subset)
        current_members["incident_members"] = all_members
        try:
            historical = {"returned": verify_readback(SavedReader(), current_members)["status"]}
        except MaterialError as exc:
            historical = {"error": str(exc)}
    assert baseline["status"] == altered_result["status"] == "passed"
    assert historical == {"error": "incident_frozen_membership_mismatch"}
    assert source_hashes == {str(p.relative_to(source)): sha(p) for p in source.rglob("*") if p.is_file()}
    report = {
        "scope": "independent_offline_boundary_probes_not_live_execution",
        "source_files": {str(p.relative_to(ROOT)): sha(p) for p in (pg_path, http_path)},
        "original_materials_unchanged": True,
        "object_raw_data_mapping": mapping,
        "saved_receipt_baseline": {"status": baseline["status"], "run_id": rid, "steps": baseline["steps"],
                                   "artifacts": baseline["artifacts"], "original_reads": len(reader.reads),
                                   "scope": "saved I1 only; current members restricted to its frozen 3 for baseline; directory assembled from saved Run; all step/artifact/HTTP bodies are saved actual responses"},
        "changed_incident_result": {"changed_path": "result.summary", "http_value_differs_from_pg": True,
                                    "verifier_status": altered_result["status"]},
        "historical_scope": {"frozen_run_member_total": selection["total_member_count"],
                             "current_member_total": len(all_members), **historical},
        "business_connections": 0, "kafka_sends": 0, "model_calls": 0,
    }
    with (HERE / "probe-results-01.json").open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({"mapping_consistent": mapping["identity_consistent"], "baseline": baseline["status"],
                      "changed_result": altered_result["status"], "historical_scope": historical}, ensure_ascii=False))


if __name__ == "__main__":
    main()
