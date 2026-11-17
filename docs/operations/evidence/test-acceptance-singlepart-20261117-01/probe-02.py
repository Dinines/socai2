"""Recheck F1-F3 against freeze 02 without overwriting review 01 or calling services."""
from __future__ import annotations

import copy
import hashlib
import json
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
from acceptance_session import load_execution, prepare_execution
from acceptance_verify import verify_readback


def load(path):
    value = json.loads(path.read_bytes())
    return value.get("value", value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in root.rglob("*") if p.is_file()}


def main():
    freeze_path = ROOT / "docs/operations/evidence/acceptance-singlepart-20261117-02/source-freeze-02.json"
    frozen = load(freeze_path)
    assert all(digest(ROOT / name) == expected for name, expected in frozen.items())
    out = HERE / "probe-02"
    out.mkdir(exist_ok=False)
    materials = HERE / "probe-01/object-raw-data"
    prior = hashes(materials)
    old_receipts = {name: digest(HERE / name) for name in ("probe-results-01.json", "independent-review-01.json", "source-read-01.json")}
    profile = control(Profile, read_json(ROOT / "tools/testdata/acceptance-examples/profile.json"), "profile")
    with patch("socket.socket", side_effect=AssertionError("offline recheck")):
        session = prepare_execution(materials, profile, Execution(schema_version="socai2.acceptance-execution.v1",
            execution_id="independent-3b-object-raw", time_policy="preserve"), out / "prepared")
        assert load_execution(out / "prepared")[1] == session
    context = read_json(out / "prepared/wire/part1/context/002.json")
    alert = read_json(out / "prepared/wire/part1/alerts/001.json")
    old = read_json(materials / "part1/context/002.json")
    uid = context["event_id"]
    assert uid != old["event_id"]
    for ocsf in (context["ocsf_event"], alert["raw_event"]["ocsf_event"]):
        assert ocsf["uid"] == ocsf["metadata"]["uid"] == uid
        assert isinstance(ocsf["raw_data"], dict)
        assert ocsf["raw_data"]["uid"] == ocsf["raw_data"]["metadata"]["uid"] == uid
        assert ocsf["time"] == old["ocsf_event"]["time"]
    assert alert["source_event_ids"] == [uid]
    assert hashes(materials) == prior

    evidence = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-02"
    paths = [evidence / "final-pg.json", evidence / "final-http-01.json"]
    pg, replies = load(paths[0])["rows"], load(paths[1])["http"]
    saved = {r["path"]: r["body"] for r in replies}
    observations = []
    for kind, rid in (("alert", "83984491-9843-5221-9693-0ba45397f061"),
                      ("incident", "10535c76-6a2e-5943-8cfc-efcc31c456a9")):
        table = "alert_assessments" if kind == "alert" else "incident_diagnoses"
        run = next(r for r in pg["runs"] if r["id"] == rid)
        sid = run[kind + "_id"]
        detail_path = f"/api/v1/socai2/{kind}s/{sid}/analysis/runs/{rid}"
        attempts = [a for a in pg["analysis_attempts"] if a["run_id"] == rid]
        tasks = [t for t in pg["analysis_tasks"] if t["id"] in {a["task_id"] for a in attempts}]
        assert len(tasks) == 1
        task_path = f"/api/v1/socai2/{kind}s/{sid}/analysis-tasks/{tasks[0]['id']}"
        rows = {name: [] for name in ("alerts", "incidents", "cases", "case_alerts", "results", "alert_assessments", "incident_diagnoses")}
        rows.update(runs=[run], analysis_attempts=attempts, analysis_tasks=tasks)
        rows[kind + "s"] = [r for r in pg[kind + "s"] if r["id"] == sid]
        rows[table] = [r for r in pg[table] if r["source_run_id"] == rid]
        rows["incident_members"] = [m for m in pg["incident_alerts"] if m["incident_id"] == sid]
        for name in ("run_steps", "run_members", "artifacts"):
            rows[name] = [r for r in pg[name] if r["run_id"] == rid]

        class SavedReader:
            # Only the directory entry is assembled; all other bodies are saved actual responses.
            def __init__(self, mutation):
                self.mutation = mutation

            def request(self, method, path):
                assert method == "GET"
                value = copy.deepcopy(saved[path])
                if path == detail_path:
                    if self.mutation == "result":
                        value["result"]["rationale" if kind == "alert" else "summary"] = "CONTROLLED_REVIEW_MISMATCH"
                    elif self.mutation == "frozen_scope":
                        value["input_selection"]["total_member_count"] = 4
                if path == task_path and self.mutation == "task_refs":
                    value["results"] = []
                return value

            def pages(self, path, params=None):
                if path == "/api/v1/socai2/analysis-runs":
                    assert params == {"subject_type": kind, "subject_id": sid}
                    links = [] if self.mutation == "directory_refs" else copy.deepcopy(saved[task_path]["results"])
                    return [{"run_id": rid, "detail_url": detail_path, "results": links}]
                pages = [r["body"] for r in replies if urlsplit(r["path"]).path == path]
                assert pages, path
                items = [item for page in pages for item in page["items"]]
                assert len(items) == len({i["id"] for i in items}) == pages[-1]["total"]
                return copy.deepcopy(items)

        mutations = [None, "result", "task_refs", "directory_refs"]
        if kind == "incident":
            mutations.append("frozen_scope")
            assert saved[detail_path]["input_selection"]["total_member_count"] == 3
            assert len(rows["incident_members"]) == 4
        for mutation in mutations:
            with patch("socket.socket", side_effect=AssertionError("offline recheck")):
                try:
                    result = verify_readback(SavedReader(mutation), rows)
                    observed = {"status": result["status"], "steps": result["steps"], "artifacts": result["artifacts"]}
                except MaterialError as exc:
                    observed = {"error": str(exc)}
            if mutation is None:
                assert observed["status"] == "passed"
            elif mutation == "result":
                assert observed["error"] == "result_http_pg_mismatch:" + ("rationale" if kind == "alert" else "summary")
            elif mutation == "frozen_scope":
                assert observed["error"] == "incident_frozen_selection_mismatch"
            else:
                assert observed["error"] == "result_reference_set_mismatch"
            observations.append({"kind": kind, "run_id": rid, "mutation": mutation, **observed})
    assert all(digest(ROOT / name) == expected for name, expected in frozen.items())
    assert all(digest(HERE / name) == expected for name, expected in old_receipts.items())
    report = {"scope": "F1_F2_F3_independent_fix_recheck_only", "status": "passed",
              "source_freeze": str(freeze_path.relative_to(ROOT)), "source_freeze_sha256": digest(freeze_path),
              "source_sha256": frozen, "saved_evidence_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths},
              "F1": {"old_source_id": old["event_id"], "new_source_id": uid,
                     "context_alert_and_object_raw_identity_equal": True, "object_type_and_time_preserved": True,
                     "prepared_save_readback_equal": True, "source_materials_unchanged": True},
              "saved_response_replays": observations,
              "F3": {"frozen_member_count": 3, "current_member_count": 4, "unmodified_saved_scope_passes": True,
                     "changed_frozen_scope_is_rejected": True},
              "review_01_receipts_unchanged": old_receipts,
              "scope_limit": "saved actual A/I detail/steps/artifacts bodies, one synthesized directory entry per saved Run; no actual HTTP request",
              "network_calls": 0, "business_writes": 0, "model_calls": 0, "live_3b_status": "not_reviewed"}
    with (HERE / "probe-results-02.json").open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print("F1-F3 independent recheck passed: 9 frozen files, object identity/readback and 9 saved-response probes; 0 live calls.")


if __name__ == "__main__":
    main()
