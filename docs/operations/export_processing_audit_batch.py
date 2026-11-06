"""Read registered synthetic cases on 21 into a new 4177 readback directory.

python docs/operations/export_processing_audit_batch.py --plan <batch>/plan.json --output <batch>/readback
If <batch>/readback already exists, publish it directly or give a NEW output
path to reuse its verified local snapshots without contacting 21.
"""
import argparse
import json
import re
import tempfile
from pathlib import Path
from uuid import UUID, uuid5

from read_processing_audit_20261106 import (
    DB,
    ROLE,
    TABLES,
    TENANT,
    check_credentials,
    digest,
    fetch,
    require,
    save,
    scoped_sql,
)

BATCH = re.compile(r"ie-audit-[a-z0-9][a-z0-9-]{0,54}")
KEY = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")


def valid_plan(plan):
    """The plan may describe subjects, never a database, a role, a query or an input path."""
    require(isinstance(plan, dict) and set(plan) <= {"batch", "cases", "source", "source_namespace",
            "source_boundary", "tenant_id"}, "unrecognized plan format")
    batch = plan.get("batch")
    require(isinstance(batch, str) and BATCH.fullmatch(batch) and plan.get("source") == batch
            and plan.get("tenant_id") == TENANT and plan.get("source_namespace") == "fusion.v1",
            "expected this processing tenant, fusion.v1 and an ie-audit-* synthetic source")
    cases = plan.get("cases")
    require(isinstance(cases, list) and 1 <= len(cases) <= 50, "expected 1 to 50 case cards")
    keys, subjects = set(), set()
    for row in cases:
        require(isinstance(row, dict) and set(row) <= {"key", "title", "alert_ids", "case_id", "incident_id",
                "operation_keys", "hostname", "lake_events", "window_start", "window_end", "baseline_run_id"},
                "unrecognized case card")
        key = row.get("key")
        require(isinstance(key, str) and KEY.fullmatch(key) and key not in keys
                and not re.fullmatch(r"(?:aux|con|nul|prn|com[1-9]|lpt[1-9])", key), "invalid or duplicate case key")
        keys.add(key)
        aids = row.get("alert_ids")
        require(isinstance(aids, list) and 1 <= len(aids) <= 100, "each card requires 1 to 100 alert IDs")
        for identity in [*aids, *(row[k] for k in ("incident_id", "case_id", "baseline_run_id") if row.get(k) is not None)]:
            require(isinstance(identity, str) and str(UUID(identity)) == identity and identity not in subjects,
                    "invalid or overlapping subject IDs")
            subjects.add(identity)
        if "operation_keys" in row:
            ops = row["operation_keys"]
            require(isinstance(ops, dict), "invalid operation keys")
            if "create" in ops and row.get("case_id"):
                create = ops["create"]
                require(isinstance(create, str) and str(UUID(create)) == create and
                        str(uuid5(UUID(TENANT), "socai2.case.create:" + create)) == row["case_id"],
                        "case ID differs from the create operation")
    return batch


def sql_for(plan):
    batch = valid_plan(plan)

    def guards(tenant, aids, iid, cid):
        def members(table, parent, value):
            return f"""(SELECT count(*)=cardinality({aids}) AND bool_and(alert_id=ANY({aids}))
                FROM socai2.{table} WHERE tenant_id={tenant} AND {parent}={value})"""

        # Membership is proved before loading any of the 29 scoped tables.
        # A candidate Case that was never created contributes zero Case rows.
        return f"""SELECT 1/(
            (SELECT count(*)=cardinality({aids}) FROM socai2.alerts a
             JOIN socai2.alert_materials m ON (m.tenant_id,m.alert_id,m.id)=(a.tenant_id,a.id,a.latest_material_id)
             WHERE a.tenant_id={tenant} AND a.id=ANY({aids}) AND a.source_namespace='fusion.v1'
               AND m.raw_json->>'source'='{batch}')
            AND NOT EXISTS (SELECT FROM socai2.alert_materials WHERE tenant_id={tenant} AND alert_id=ANY({aids})
                            AND raw_json->>'source' IS DISTINCT FROM '{batch}')
            AND NOT EXISTS (SELECT FROM socai2.incidents i WHERE i.tenant_id={tenant} AND i.id={iid}
                            AND (i.source_namespace IS DISTINCT FROM 'fusion.v1' OR
                                 NOT {members("incident_alerts", "incident_id", iid)}))
            AND NOT EXISTS (SELECT FROM socai2.cases c WHERE c.tenant_id={tenant} AND c.id={cid}
                            AND (c.source_namespace IS DISTINCT FROM 'fusion.v1' OR
                                 NOT {members("case_alerts", "case_id", cid)} OR
                                 EXISTS (SELECT FROM socai2.case_incidents ci WHERE ci.tenant_id={tenant}
                                         AND ci.case_id={cid} AND ci.incident_id IS DISTINCT FROM {iid})))
        )::integer;"""

    return scoped_sql(plan, batch, guards=guards)


def validate_data(card, data, batch):
    require(set(data) == set(TABLES) and all(isinstance(rows, list) for rows in data.values()), "incomplete database export")
    require(all(r.get("tenant_id") == TENANT for rows in data.values() for r in rows), "row outside processing tenant")
    aids = set(card["alert_ids"])
    require({a["id"] for a in data["alerts"]} == aids, "missing or unexpected alert")
    current = {a["id"]: a["latest_material_id"] for a in data["alerts"]}
    materials = {(m["alert_id"], m["id"]) for m in data["alert_materials"]}
    require(set(current.items()) <= materials and
            all(m["alert_id"] in aids and (m["raw_json"] or {}).get("source") == batch for m in data["alert_materials"]),
            "unverified synthetic alert material")
    for table in ("alerts", "incidents", "cases"):
        require(all(r.get("source_namespace") == "fusion.v1" for r in data[table]), "unexpected subject namespace")
    for table, field, members in [("incidents", "incident_id", "incident_alerts"), ("cases", "case_id", "case_alerts")]:
        ids = {s["id"] for s in data[table]}
        require(ids <= {card.get(field)} and all(m[field] in ids for m in data[members])
                and {m["alert_id"] for m in data[members]} == (aids if ids else set()), f"out-of-scope {table} or members")
    cids = {r["id"] for r in data["cases"]}
    iids = {r["id"] for r in data["incidents"]}
    require(all(r["case_id"] in cids and r["incident_id"] in iids for r in data["case_incidents"]),
            "out-of-scope case/incident link")
    require(all(r.get("case_id") in cids or r.get("alert_id") in aids or r.get("incident_id") in iids
                for r in data["runs"]), "Run outside registered subjects")
    run_ids = {r["id"] for r in data["runs"]}
    activity_ids = {r["id"] for r in data["activities"]}
    relations = {"alert_source_refs": ("alert_id", aids), "alert_objects": ("alert_id", aids),
                 "alert_assessments": ("source_run_id", run_ids), "incident_diagnoses": ("source_run_id", run_ids),
                 "run_members": ("run_id", run_ids), "run_steps": ("run_id", run_ids),
                 "activity_targets": ("activity_id", activity_ids)}
    for table in ("case_assessments", "case_assessment_sources", "case_assessment_members", "results",
                  "result_members", "tasks", "task_revisions", "conversations", "messages", "graph_explorations"):
        relations[table] = ("case_id", cids)
    for table, (field, allowed) in relations.items():
        require(all(r[field] in allowed for r in data[table]), f"{table} row outside registered subjects")
    require(all(r.get("run_id") in run_ids if r.get("run_id") is not None else
                r.get("case_id") in cids or r.get("alert_id") in aids for r in data["artifacts"]),
            "artifact outside registered subjects")
    for table, prefix in (("activities", "subject_"), ("comments", ""), ("response_links", "")):
        require(all(r.get(prefix + "case_id") in cids or r.get(prefix + "incident_id") in iids
                    or r.get(prefix + "alert_id") in aids for r in data[table]), f"{table} outside registered subjects")
    if card.get("baseline_run_id"):
        require(any(r["id"] == card["baseline_run_id"] and r["kind"] == "baseline" and r["case_id"] == card.get("case_id")
                    for r in data["runs"]), "baseline Run differs from plan")


def read_local(folder, plan, plan_hash):
    def load(name):
        path = folder / name
        require(path.resolve().is_relative_to(folder.resolve()), "snapshot path escapes its folder")
        return path.read_bytes()

    hashes = json.loads(load("files.sha256.json"))
    summary_body = load("summary.json")
    summary = json.loads(summary_body)
    require(digest(summary_body) == hashes.get("summary.json") and summary["batch"] == plan["batch"]
            and summary["plan_sha256"] == plan_hash, "existing snapshot belongs to a different or modified plan")
    snapshot = summary["snapshot"]
    require(snapshot["database"] == DB and snapshot["role"] == ROLE and snapshot["isolation"] == "repeatable read",
            "unrecognized local snapshot origin")
    output = {}
    for card in plan["cases"]:
        key = card["key"]
        records = {}
        for name in ("database.json", "input-freshness.json"):
            rel = f"{key}/{name}"
            body = load(rel)
            require(digest(body) == hashes.get(rel), "local snapshot file checksum mismatch: " + rel)
            check_credentials(body)
            records[name] = json.loads(body)
        output[key] = {**records["database.json"], "input_freshness": records["input-freshness.json"]}
    return snapshot, output


def export_batch(plan_path: Path, output: Path):
    require(not output.exists() and not output.is_symlink(), "output already exists; use the saved snapshot or a new path")
    body = plan_path.read_bytes()
    check_credentials(body)
    plan = json.loads(body)
    batch = valid_plan(plan)
    plan_hash = digest(body)
    local = plan_path.parent / "readback"
    local_source = local.exists() or local.is_symlink()
    if local_source:
        require(local.is_dir() and not local.is_symlink(), "invalid local readback directory")
        snapshot, payload = read_local(local, plan, plan_hash)
    else:
        snapshot, payload = fetch(plan, build_sql=sql_for)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage all rows and hashes first. Concurrent publishers cannot overwrite an
    # existing verified snapshot: once published, its directory is non-empty.
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "readback"
        staged.mkdir()
        cards = []
        for card in plan["cases"]:
            key = card["key"]
            rows = {k: v for k, v in payload[key].items() if k != "input_freshness"}
            validate_data(card, rows, batch)
            freshness = payload[key]["input_freshness"]
            expected_runs = {r["id"] for r in rows["runs"] if r["kind"] == "baseline" and r["case_id"] == card.get("case_id")}
            require(isinstance(freshness, list) and len(freshness) == len(expected_runs)
                    and {f["run_id"] for f in freshness} == expected_runs, "freshness rows differ from registered Case Runs")
            case_dir = staged / key
            case_dir.mkdir()
            save(case_dir / "database.json", rows)
            save(case_dir / "input-freshness.json", freshness)
            cards.append({"case": key, "counts": {k: len(v) for k, v in rows.items()}})
        save(staged / "summary.json", {"batch": batch, "plan_sha256": plan_hash, "snapshot": snapshot, "cases": cards})
        save(staged / "files.sha256.json", {p.relative_to(staged).as_posix(): digest(p.read_bytes())
                                            for p in sorted(staged.rglob("*.json"))})
        require(not output.exists() and not output.is_symlink(), "output appeared during export")
        staged.rename(output)
    return {"batch": batch, "cases": len(cards), "source": "local_readback" if local_source else "21",
            "output": str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_batch(args.plan, args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
