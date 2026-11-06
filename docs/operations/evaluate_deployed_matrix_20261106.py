"""Read each 21 model case from its frozen export. Preserve partial and missing results."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from check_investigation_handoff import BASE, compare_fields, equal, one, timestamp

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / ".local"


def read(path):
    return json.loads(path.read_bytes())


def require(test, reason):
    if not test:
        raise ValueError(reason)


def check_handoff(db, reads):
    """Compare saved GETs to the same subjects, materials and explicitly published pointers."""
    def get(path):
        response = reads[BASE + path]
        equal(path, response["status"], 200)
        return response["body"]

    for kind in ("alerts", "incidents"):
        queue = get("/" + kind)
        equal(kind + " total", queue["total"], len(db[kind]))
        for row in db[kind]:
            path = "/" + kind + "/" + row["id"]
            subject = get(path)
            listed = one([x["facts"] for x in queue["items"]], id=row["id"])
            for facts in (listed, subject["facts"]):
                compare_fields(facts, row, ["id","title","description","handling_status","owner_id"], path)
            analysis = get(path + "/analysis")
            if kind == "alerts":
                for facts in (listed, subject["facts"]):
                    compare_fields(facts, row, ["severity","original_vendor","source_alert_id","latest_material_id"], path)
                    equal("event time", timestamp(facts["event_time"]), timestamp(row["event_time"]))
                material = one(db["alert_materials"], id=row["latest_material_id"], alert_id=row["id"])
                raw = get(path + "/materials/" + material["id"])
                equal("material content", [raw["availability"],raw["content_json"]["raw_json"]], ["available",material["raw_json"]])
                pointer = row["latest_triage_id"]
                triage = subject["triage"]
                if pointer:
                    saved = one(db["alert_assessments"], id=pointer)
                    compare_fields(triage, saved, ["id","verdict","rationale","source_run_id"], "triage")
                    equal("confidence percent", triage["confidence_percent"], float(saved["confidence"])*100)
                else:
                    equal("no current triage", triage, None)
            else:
                linked = [r["alert_id"] for r in db["incident_alerts"] if r["incident_id"] == row["id"]]
                equal("incident member count", subject["derived"]["member_count"],len(linked))
                equal("incident members", sorted(r["id"] for r in get(path + "/records/members")["items"]), sorted(linked))
                pointer = row["latest_diagnosis_id"]
                if pointer:
                    diagnosis = one(db["incident_diagnoses"], id=pointer)
                    compare_fields(analysis["current"]["result"], diagnosis, ["id","state","summary","source_run_id"], "diagnosis")
            equal("current pointer", analysis["current_pointer_id"],pointer)
            if pointer is None:
                equal("no published analysis", analysis["current"],None)
            for entry in analysis["entries"]:
                rid = entry["run"]["id"]
                saved_run = one(db["runs"], id=rid)
                trace = get(path + "/analysis/runs/" + rid + "/trace")
                compare_fields(trace["run"], saved_run, ["id","state","stop_reason","delivery_state"], "trace")
    case_queue = get("/cases")
    equal("Case queue", sorted(i["case"]["id"] for i in case_queue["items"]), sorted(c["id"] for c in db["cases"]))
    for case in db["cases"]:
        path = "/cases/" + case["id"]
        detail, page = get(path), get(path+"/page-data")
        equal("case page data", detail["page_data"],page)
        require(sorted(m["alert_id"] for m in detail["members"]) == sorted(r["alert_id"] for r in db["case_alerts"]
                if r["case_id"] == case["id"]), "Case members")
        current = case["current_assessment_id"]
        assessment = one(db["case_assessments"],id=current) if current else None
        equal("adopted conclusion", page["determination"], assessment["conclusion"] if current else None)
        if current:
            compare_fields(page["assessment"], assessment, ["id","origin","validity"], "current assessment")
        for run in [r for r in db["runs"] if r["case_id"] == case["id"]]:
            compare_fields(get(path+"/runs/"+run["id"])["run"], run, ["id","state","stop_reason"],"Case Run")
        for result in [r for r in db["results"] if r["case_id"] == case["id"]]:
            rid = result["source_run_id"]
            detail_result = get(path+"/results/"+result["id"])
            compare_fields(detail_result["result"], result, ["id","conclusion","conclusion_origin","validation_state",
                           "delivery_state","source_run_id"], "Case result")
            if result["graph_artifact_id"]:
                aid = result["graph_artifact_id"]
                graph = get(path+"/runs/"+rid+"/artifacts/"+aid)
                equal("graph body", graph["content_json"], one(db["artifacts"],id=aid,run_id=rid)["content_json"])
    return {"alert_facts_and_originals":len(db["alerts"]), "incident_members_and_diagnosis_pointers":len(db["incidents"]),
            "case_queue_count":len(db["cases"]), "case_results":len(db["results"])}


def case_summary(card):
    folder = STATE / ("deployed-pilot-20261106-" + card)
    plan = read(folder / "plan.json")
    exports = sorted((folder / "exports").glob("*/manifest.json"))
    require(exports, "missing export for " + card)
    record = exports[-1].parent
    manifest = read(record / "manifest.json")
    for src in manifest["sources"]:
        require(Path(src["file"]).name == src["file"], "invalid export path")
        require(hashlib.sha256((record / src["file"]).read_bytes()).hexdigest() == src["sha256"], src["file"])
    db = read(record / "database.json")
    require(len(db) == 29 and manifest["table_counts"] == {k:len(v) for k,v in db.items()}, "table readback mismatch")
    require(manifest["batch_id"] == plan["batch_id"] and manifest["database"] == plan["database"], "scope mismatch")
    alerts = sorted(db["alerts"], key=lambda row:row["event_time"])
    require([r["id"] for r in alerts] == plan["canonical_alert_ids"], "wrong alerts")
    require(len(db["incidents"]) == 1 and {r["alert_id"] for r in db["incident_alerts"]} ==
            set(plan["canonical_alert_ids"]), "wrong members")
    runs = sorted(db["runs"], key=lambda row:row.get("requested_at") or "")
    receipts = {r["id"]:r for r in read(record / "model-receipts.json")}
    attempts = [s for s in db["run_steps"] if s["kind"] == "model" and s["state"] not in {"skipped","planned"}]
    require(set(receipts) == {s["id"] for s in attempts}, "model receipt identities differ")
    require(len(attempts) <= plan["max_model_calls"], "attempt cap exceeded")
    reads = {}
    for name in ("api-responses.json", "three-page-gets.json"):
        for call in read(record / name):
            require(call["method"] == "GET", name)
            reads[call["path"]] = call
    handoff = check_handoff(db, reads)
    used = [s.get("usage") or {} for s in attempts]
    incident = db["incidents"][0]
    triages = {a["id"]:a for a in db["alert_assessments"]}
    diagnoses = {i["id"]:i for i in db["incident_diagnoses"]}
    results = []
    for result in sorted(db["results"], key=lambda r:r.get("created_at") or ""):
        rid = result["source_run_id"]
        run = next(r for r in runs if r["id"] == rid)
        details = [a["content_json"] for a in db["artifacts"] if a["run_id"] == rid and
                   a["schema_version"] == "socai2.baseline-delivery.v1" and "delivery" in (a["content_json"] or {})]
        require(len(details) == 1, "no unique stored publication detail")
        members = [m for m in db["result_members"] if m["result_id"] == result["id"]]
        q = Counter(v["state"] for v in result["questions"])
        selected = ("id","source_run_id","conclusion","conclusion_state","conclusion_origin","validation_state",
                    "delivery_state","comparison_result_id","graph_artifact_id","report_artifact_id")
        results.append({**{k:result[k] for k in selected}, "run_state":run["state"],"stop_reason":run["stop_reason"],
                        "covered": sum(bool(m["conclusion_covered"]) for m in members), "members":len(members),
                        "question_states":dict(q), "limitations":details[0]["limitations"]})
    def stage(s):
        raw = receipts.get(s["id"], {}).get("raw") or {}
        artifact = next((a for a in db["artifacts"] if a["id"] == s["output_artifact_id"]), {})
        content = artifact.get("content_json") or {}
        transport = (content.get("payload") or content).get("transport_error") or {}
        return {"id":s["id"], "stage":s["stage_code"], "kind":s["kind"], "state":s["state"],
                "error":(s.get("error") or {}).get("code"), "raw_response_id":raw.get("id"),
                "provider_http_status":transport.get("http_status")}
    execution = []
    for r in runs:
        ss = sorted((s for s in db["run_steps"] if s["run_id"] == r["id"]), key=lambda s:s["seq"])
        execution.append({**{k:r[k] for k in ("id","kind","state","delivery_state","stop_reason","alert_id")},
                          "stages":[stage(s) for s in ss if s["kind"] in {"stage","model"}]})
    cases = []
    for c in db["cases"]:
        current = next((a for a in db["case_assessments"] if a["id"] == c["current_assessment_id"]), {})
        refs = [{"result_id":s["result_id"],"artifact_id":s["artifact_id"],"task_revision_id":s["task_revision_id"]}
                for s in db["case_assessment_sources"] if s["assessment_id"] == current.get("id")]
        cases.append({"id":c["id"],"title":c["title"], "assessment_id":c["current_assessment_id"],
                      "conclusion":current.get("conclusion"),"origin":current.get("origin"),
                      "validity":current.get("validity"),"sources":refs})
    return {"batch_id":plan["batch_id"], "database":plan["database"], "scenario":plan["case"]["scenario"],
            "reference_batch":plan["comparison_batch_id"], "export":str(record.relative_to(REPO).as_posix()),
            "alerts":[{"id":a["id"],"title":a["title"],"triage":{k:triages[a["latest_triage_id"]][k]
                      for k in ("verdict","confidence","rationale")} if a["latest_triage_id"] else None} for a in alerts],
            "incident":{"id":incident["id"],"published_summary":diagnoses[incident["latest_diagnosis_id"]]["summary"]
                        if incident["latest_diagnosis_id"] else None},
            "cases":cases,"runs":execution, "results":results, "task_revisions":len(db["task_revisions"]),
            "attempts":len(attempts),"reported_tokens":sum(s.get("total_tokens") or 0 for s in used),
            "unknown_usage":sum(s.get("total_tokens") is None for s in used),
            "steps":len(db["run_steps"]),"artifacts":len(db["artifacts"]), "handoff_checked":handoff,
            "http_status_by_unique_path":dict(Counter(r["status"] for r in reads.values()))}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--cards", nargs="+", choices=("01","02","03","04"), default=("01","02","03","04"))
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    data = [case_summary(n) for n in args.cards]
    encoded = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    else:
        print(encoded)
