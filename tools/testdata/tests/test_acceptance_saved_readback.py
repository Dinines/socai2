"""Replay saved real A/I receipts to verify result values and frozen scopes."""
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from acceptance_materials import MaterialError
from acceptance_verify import verify_readback

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/operations/evidence/streaming-fullflow-20261116-02"


def load(name):
    value = json.loads((EVIDENCE / name).read_text())
    return value.get("value", value)


@pytest.mark.parametrize("kind", ["alert", "incident"])
@pytest.mark.parametrize("mutation", [None, "result", "missing_reference"])
def test_saved_stage_results_and_historical_scope(kind, mutation):
    pg, replies = load("final-pg.json")["rows"], load("final-http-01.json")["http"]
    table = "alert_assessments" if kind == "alert" else "incident_diagnoses"
    stored_result = pg[table][0]
    rid = stored_result["source_run_id"]
    run = next(r for r in pg["runs"] if r["id"] == rid)
    sid = run[kind + "_id"]
    detail_path = f"/api/v1/socai2/{kind}s/{sid}/analysis/runs/{rid}"
    saved = {r["path"]: r["body"] for r in replies}
    attempts = [r for r in pg["analysis_attempts"] if r["run_id"] == rid]
    tasks = [r for r in pg["analysis_tasks"] if r["id"] in {a["task_id"] for a in attempts}]
    rows = {key: [] for key in ("alerts", "incidents", "cases", "case_alerts", "results", "alert_assessments", "incident_diagnoses")}
    rows.update(runs=[run], analysis_attempts=attempts, analysis_tasks=tasks)
    rows[kind + "s"] = [r for r in pg[kind + "s"] if r["id"] == sid]
    rows[table] = [stored_result]
    for name in ("run_steps", "run_members", "artifacts"):
        rows[name] = [r for r in pg[name] if r["run_id"] == rid]
    # Current I has four members while this historical I1 froze three: both are valid.
    rows["incident_members"] = [r for r in pg["incident_alerts"] if r["incident_id"] == sid]
    task_path = f"/api/v1/socai2/{kind}s/{sid}/analysis-tasks/{tasks[0]['id']}"
    links = saved[task_path]["results"]

    class SavedReader:
        def request(self, method, path):
            assert method == "GET"
            value = copy.deepcopy(saved[path])
            if path == detail_path and mutation == "result":
                value["result"]["rationale" if kind == "alert" else "summary"] = "CONTROLLED_DIFFERENT_VALUE"
            if path == task_path and mutation == "missing_reference":
                value["results"] = []
            return value

        def pages(self, path, params=None):
            if path == "/api/v1/socai2/analysis-runs":
                assert params == {"subject_type": kind, "subject_id": sid}
                return [{"run_id": rid, "detail_url": detail_path, "results": copy.deepcopy(links)}]
            pages = [r["body"] for r in replies if urlsplit(r["path"]).path == path]
            items = [item for page in pages for item in page["items"]]
            assert len(items) == len({r["id"] for r in items}) == pages[-1]["total"]
            return copy.deepcopy(items)

    if mutation:
        message = "result_http_pg_mismatch" if mutation == "result" else "result_reference_set_mismatch"
        with pytest.raises(MaterialError, match=message):
            verify_readback(SavedReader(), rows)
    else:
        assert verify_readback(SavedReader(), rows)["status"] == "passed"
        if kind == "incident":
            assert len(rows["incident_members"]) == 4
            assert saved[detail_path]["input_selection"]["total_member_count"] == 3


def test_two_case_rounds_use_their_own_frozen_members_and_comparison():
    pg, replies = load("final-pg.json")["rows"], load("final-http-01.json")["http"]
    saved = {r["path"]: r["body"] for r in replies}
    cid = next(c["id"] for c in pg["cases"] if sum(r["case_id"] == c["id"] for r in pg["runs"]) == 2)
    runs = [r for r in pg["runs"] if r["case_id"] == cid]
    run_ids = {r["id"] for r in runs}
    attempts = [a for a in pg["analysis_attempts"] if a["run_id"] in run_ids]
    rows = {key: [] for key in ("alerts", "incidents", "alert_assessments", "incident_diagnoses")}
    rows.update(cases=[c for c in pg["cases"] if c["id"] == cid], runs=runs, analysis_attempts=attempts,
                analysis_tasks=[t for t in pg["analysis_tasks"] if t["id"] in {a["task_id"] for a in attempts}],
                case_alerts=[r for r in pg["case_alerts"] if r["case_id"] == cid],
                results=[r for r in pg["results"] if r["case_id"] == cid])
    for name in ("run_steps", "run_members", "artifacts"):
        rows[name] = [r for r in pg[name] if r["run_id"] in run_ids]

    class Reader:
        def request(self, method, path):
            assert method == "GET"
            return copy.deepcopy(saved[path])

        def pages(self, path, params=None):
            if path == "/api/v1/socai2/analysis-runs":
                assert params == {"subject_type": "case", "subject_id": cid}
                return [{"run_id": r["id"], "detail_url": f"/api/v1/socai2/cases/{cid}/runs/{r['id']}",
                         "results": [{"result_type": "case_result", "id": v["id"], "source_run_id": r["id"]}
                                     for v in rows["results"] if v["source_run_id"] == r["id"]]} for r in runs]
            pages = [r["body"] for r in replies if urlsplit(r["path"]).path == path]
            return copy.deepcopy([item for page in pages for item in page["items"]])

    assert verify_readback(Reader(), rows)["status"] == "passed"
    assert sorted(sum(m["run_id"] == r["id"] for m in rows["run_members"]) for r in runs) == [3, 4]
    assert len(rows["case_alerts"]) == 4
