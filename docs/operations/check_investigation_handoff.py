"""Replay the November 6 Case field handoff from the committed ZIP, without service access."""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "deliverables/investigation-validation-20261106/socai2-investigation-tests-20261106.zip"
AUDIT = "docs/operations/evidence/additional-tests-20261106"
BASE = "/api/v1/socai2"


def equal(label, actual, expected):
    # Comparing JSON also distinguishes false from 0.
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError(f"{label} differs: {ascii(actual)[:160]} != {ascii(expected)[:160]}")


def one(rows, **keys):
    matches = [row for row in rows if all(row[k] == v for k, v in keys.items())]
    if len(matches) != 1:
        raise ValueError(f"expected one row for {keys}, got {len(matches)}")
    return matches[0]


def timestamp(value):
    # Python 3.9 needs 3 or 6 fractional digits; PostgreSQL emits 1 through 6.
    padded = re.sub(r"\.(\d{1,6})(?=Z|[+-])", lambda m: "." + m[1].ljust(6, "0"), value)
    parsed = datetime.fromisoformat(padded.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError(f"timestamp missing offset: {value}")
    return parsed.timestamp()


def compare_fields(view, row, keys, label):
    # Iterate the declared public fields, including explicitly nullable fields.
    for key in keys:
        actual, expected = view[key], row[key]
        if key.endswith("_at") and actual is not None and expected is not None:
            actual, expected = timestamp(actual), timestamp(expected)
        equal(f"{label}.{key}", actual, expected)


def check_page(db, case, export, schemas, counts):
    page = export["page_data"]
    ref = {"case_id": case["id"], "tenant_id": case["tenant_id"]}
    equal("case export", [export["case_id"], export["case_row_version"], export["current_assessment_id"]],
          [case["id"], case["row_version"], case["current_assessment_id"]])
    for name, value in [("CasePageData", page), ("EvidenceView", page["evidence"])]:
        equal(f"{name} missing keys", sorted(schemas[name]["properties"].keys() - value.keys()), [])
    compare_fields(page, case, ["classification", "due_at"], "page_data")
    equal("schema_version", page["schema_version"], "socai2.case-page-data.v1")
    assessment = page["assessment"]
    if case["current_assessment_id"] is None:
        equal("absent assessment", [assessment, page["determination"]], [None, None])
    else:
        current = one(db["case_assessments"], id=case["current_assessment_id"], **ref)
        fields = schemas["AssessmentPageView"]["properties"].keys() - {"sources", "alert_ids"}
        compare_fields(assessment, current, fields, "assessment")
        equal("determination", page["determination"], current["conclusion"])
        sources = [r for r in db["case_assessment_sources"] if r["assessment_id"] == current["id"]]
        equal("assessment sources", sorted(assessment["sources"], key=lambda r: r["id"]),
              sorted(sources, key=lambda r: r["id"]))
        members = [r["alert_id"] for r in db["case_assessment_members"] if r["assessment_id"] == current["id"]]
        equal("assessment members", sorted(assessment["alert_ids"]), sorted(members))
    evidence = page["evidence"]
    equal("evidence state/counts", [evidence[k] for k in ("state", "evidence_count", "threat_count")], counts)
    equal("evidence pointer", evidence["artifact_id"], case["current_evidence_artifact_id"])
    if evidence["artifact_id"] is None:
        equal("missing evidence", [evidence["index"], evidence["entries"]], [None, []])
    else:
        artifact = one(db["artifacts"], id=evidence["artifact_id"], kind="case_evidence_index", **ref)
        equal("evidence index", evidence["index"], artifact["content_json"])
        equal("evidence entries", len(evidence["entries"]), evidence["evidence_count"])


def check_model(read, batch, extended, schemas, examples):
    receipt = read(f"{AUDIT}/{batch}.json")
    db = read(receipt["export"] + "/database.json")
    case, = db["cases"]
    result, = db["results"]
    run = one(db["runs"], id=result["source_run_id"], case_id=case["id"], tenant_id=case["tenant_id"])
    frozen, = read(receipt["export"] + "/case-page-data.json")
    check_page(db, case, frozen, schemas, ["not_recorded", None, None])
    paths = {}
    for file in (receipt["live_readback"]["saved_gets"], extended["originals"]):
        for response in read(file):
            path = response["path"]
            if path in paths:
                raise ValueError(f"duplicate GET for {path}")
            equal(path, [response["method"], response["status"]], ["GET", 200])
            paths[path] = (file, response["body"])

    def get(label, path):
        source, body = paths.pop(BASE + path)
        examples[f"{batch}/{label}.json"] = (body, {"kind": "saved_http_get_body", "source": source,
                                                    "method": "GET", "path": BASE + path, "status": 200})
        return body

    prefix = "/cases/" + case["id"]
    detail = get("case", prefix)
    page = get("page-data", prefix + "/page-data")
    delivered = get("result", prefix + "/results/" + result["id"])
    compare_fields(detail["case"], case, schemas["CaseView"]["properties"], "CaseView")
    compare_fields(delivered["result"], result, schemas["ResultView"]["properties"], "ResultView")
    equal("current page", page, frozen["page_data"])
    equal("detail page", detail["page_data"], page)
    equal("Case current assessment", detail["current_assessment"]["value"]["id"], page["assessment"]["id"])
    equal("adopted result", [s["result_id"] for s in page["assessment"]["sources"]], [result["id"]])
    for view, rows in ((detail, [r for r in db["case_alerts"] if r["case_id"] == case["id"]]),
                       (delivered, [r for r in db["result_members"] if r["result_id"] == result["id"]])):
        equal("members", sorted(r["alert_id"] for r in view["members"]), sorted(r["alert_id"] for r in rows))
        equal("member_count", view["member_count"], len(rows))
    equal("result run", delivered["run"]["id"], run["id"])
    history = get("case-history", prefix + "/history")["items"]
    equal("Case history", [(r["run"]["id"], r["result"]["id"]) for r in history], [(run["id"], result["id"])])
    run_path = prefix + "/runs/" + run["id"]
    equal("baseline result", get("baseline-run", run_path)["result_ids"], [result["id"]])
    ids = {run["id"]: run["kind"]}
    for table, kind, fk in (("alerts", "alert_basic", "alert_id"), ("incidents", "incident_diagnosis", "incident_id")):
        for i, row in enumerate(db[table], start=1):
            subject = f"/{table}/{row['id']}"
            label = f"{table}-{i}"
            equal(subject, get(label, subject)["facts"]["id"], row["id"])
            stage = one(db["runs"], kind=kind, tenant_id=case["tenant_id"], **{fk: row["id"]})
            trace = get(label + "-trace", subject + "/analysis/runs/" + stage["id"] + "/trace")
            equal("subject trace", [trace["run"]["id"], trace["run"]["kind"]], [stage["id"], kind])
            ids[stage["id"]] = kind
            if table == "alerts":
                material = one(db["alert_materials"], id=row["latest_material_id"], alert_id=row["id"])
                raw = get(label + "-material", subject + "/materials/" + material["id"])
                equal("raw material", raw["content_json"]["raw_json"], material["raw_json"])
            else:
                links = get(label + "-members", subject + "/records/members")["items"]
                expected = [link["alert_id"] for link in db["incident_alerts"] if link["incident_id"] == row["id"]]
                equal("incident members", sorted(link["id"] for link in links), sorted(expected))
    equal("combined run IDs", sorted(ids), sorted(row["id"] for row in db["runs"]))
    equal("combined run kinds", dict(Counter(ids.values())), {"alert_basic": 2, "incident_diagnosis": 1, "baseline": 1})
    c6 = one(db["run_steps"], run_id=run["id"], stage_code="C6", kind="model")
    graph = one(receipt["graph"], artifact_id=result["graph_artifact_id"])
    for label, artifact_id in (("graph", result["graph_artifact_id"]), ("c6-output", c6["output_artifact_id"])):
        artifact = one(db["artifacts"], id=artifact_id, run_id=run["id"], case_id=case["id"], tenant_id=case["tenant_id"])
        body = get(label, run_path + "/artifacts/" + artifact_id)
        equal(label, [body["availability"], body["artifact"]["id"], body["content_json"]],
              ["available", artifact_id, artifact["content_json"]])
        if label == "graph":
            for key in ("nodes", "edges"):
                equal(f"graph {key}", len(body["content_json"][key]), graph[key])
    equal("unmapped GETs", sorted(paths), [])
    return {"case_id": case["id"], "case_fields": len(schemas["CaseView"]["properties"]),
            "result_fields": len(schemas["ResultView"]["properties"]), "case_history": len(history),
            "combined_history": dict(Counter(ids.values())), "adopted_result_id": result["id"],
            "graph_nodes": graph["nodes"], "graph_edges": graph["edges"]}


def replay(archive):
    def read(path):
        return json.loads(archive.read(path))

    schemas = read("docs/design/socai2-independent-api-v2.openapi.json")["components"]["schemas"]
    extended = read(f"{AUDIT}/extended-readback.json")["reports"]
    models, contracts, examples = {}, {}, {}
    for suffix in ("01", "02", "03"):
        batch = "local-eval-20261106-" + suffix
        models[batch] = check_model(read, batch, one(extended, batch=batch), schemas, examples)
    receipt = read("docs/operations/evidence/page-data-20261106/summary.json")
    export = receipt["local_readback"] + "/case-page-data.json"
    db = read(receipt["local_readback"] + "/database.json")
    pages = read(export)
    equal("contract case count", [len(pages), len(db["cases"]), len(receipt["counts"])], [4, 4, 4])
    equal("contract runs", db["runs"], [])
    for case in db["cases"]:
        cid = str(UUID(case["id"]))
        frozen = one(pages, case_id=cid)
        expected = one(receipt["counts"], case_id=cid)
        counts = [expected[k] for k in ("state", "evidence", "threats")]
        check_page(db, case, frozen, schemas, counts)
        contracts[cid] = {**expected, "classification": case["classification"], "due_at": case["due_at"]}
        examples["contracts/" + cid + ".json"] = (frozen["page_data"], {
            "kind": "database_export_field", "source": export, "case_id": cid, "field": "page_data"})
    return {"model_cases": models, "contract_cases": contracts, "saved_gets": len(examples) - len(contracts)}, examples


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def export_examples(target, summary, examples):
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as tmp:
        stage = Path(tmp) / "examples"
        for name, (body, _) in examples.items():
            dest = stage / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_json(dest, body)
        write_json(stage / "index.json", {**summary, "files": {n: meta for n, (_, meta) in examples.items()}})
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"output already exists: {target}")
        stage.rename(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples-dir", type=Path, help="Export response bodies and index to a new directory.")
    args = parser.parse_args()
    try:
        with ZipFile(ARCHIVE) as archive:
            summary, examples = replay(archive)
        if args.examples_dir:
            export_examples(args.examples_dir, summary, examples)
        print(json.dumps(summary, indent=2))
    except (OSError, BadZipFile, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Handoff check failed: {exc}\n")


if __name__ == "__main__":
    main()
