"""Read an existing Case and compare documented GETs with stored rows; never write DB."""

import argparse
import asyncio
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
from processing_workbench_source import detail_query
from production_case_probe import query, save

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy/local-investigation"))
from remote_profile import load_profile  # noqa: E402 - explicit checkout module path

PREFIX = "/api/v1/socai2"
FK_SQL = """SELECT coalesce(jsonb_agg(to_jsonb(x) ORDER BY x.name),'[]') FROM (
 SELECT c.conname AS name, s.relname AS source_table, t.relname AS target_table,
 ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(n,seq)
       JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.n ORDER BY k.seq) AS source_columns,
 ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(n,seq)
       JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.n ORDER BY k.seq) AS target_columns
 FROM pg_constraint c JOIN pg_class s ON s.oid=c.conrelid JOIN pg_namespace sn ON sn.oid=s.relnamespace
 JOIN pg_class t ON t.oid=c.confrelid JOIN pg_namespace tn ON tn.oid=t.relnamespace
 WHERE c.contype='f' AND sn.nspname='socai2' AND tn.nspname='socai2'
) x;"""


def load(path):
    return json.loads(Path(path).read_text())


def equivalent(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equivalent(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equivalent(a, b) for a, b in zip(left, right))
    if isinstance(left, str) and isinstance(right, str) and re.match(r"^\d{4}-\d\d-\d\dT", left):
        try:
            return datetime.fromisoformat(left) == datetime.fromisoformat(right)
        except ValueError:
            pass
    if type(left) in (int, float) and isinstance(right, str) or type(right) in (int, float) and isinstance(left, str):
        try:
            return Decimal(str(left)) == Decimal(str(right))
        except ArithmeticError:
            return False
    return left == right


def run_path(row):
    if row["case_id"]:
        return f"/cases/{row['case_id']}/runs/{row['id']}"
    kind = "alerts" if row["alert_id"] else "incidents"
    identity = row["alert_id"] or row["incident_id"]
    return f"/{kind}/{identity}/analysis/runs/{row['id']}"


def request_plan(data, config):
    case = data["cases"][0]["id"]
    plan = []

    def add(path, kind, **extra):
        plan.append({"method": "GET", "path": PREFIX + path, "kind": kind, "expected_status": 200, **extra})

    for table in ("alerts", "incidents"):
        add(f"/{table}?limit={config['http']['subject_list_limit']}", "subject_list", table=table)
        for row in data[table]:
            base = f"/{table}/{row['id']}"
            add(base, "subject", table=table, id=row["id"])
            add(base + "/analysis", "analysis", table=table, id=row["id"])
            sections = ["objects", "sources", "assets", "cases", "comments", "activities", "related_alerts", "responses"]
            sections.append("incidents" if table == "alerts" else "members")
            for section in sections:
                add(f"{base}/records/{section}?limit={config['http']['collection_limit']}",
                    "records", table=table, id=row["id"], section=section)
    add(f"/cases?limit={config['http']['case_queue_limit']}", "case_list")
    for suffix, kind in (("", "case"), ("/page-data", "page_data"),
                         (f"/history?limit={config['http']['case_history_limit']}", "history"), ("/tasks", "tasks")):
        add(f"/cases/{case}" + suffix, kind)
    for row in data["alert_materials"]:
        add(f"/alerts/{row['alert_id']}/materials/{row['id']}", "material", id=row["id"])
    runs = {row["id"]: row for row in data["runs"]}
    for row in runs.values():
        base = run_path(row)
        add(base, "run" if row["case_id"] else "stage_run", id=row["id"])
        if not row["case_id"]:
            add(base + "/trace", "run", id=row["id"])
    for row in data["artifacts"]:
        if row["run_id"]:
            add(run_path(runs[row["run_id"]]) + f"/artifacts/{row['id']}", "artifact", id=row["id"])
    for row in data["run_members"]:
        add(run_path(runs[row["run_id"]]) + f"/materials/{row['material_id']}", "frozen_material", id=row["material_id"])
    for row in data["results"]:
        add(f"/cases/{case}/results/{row['id']}", "result", id=row["id"])
    # Deliberately wrong parent IDs, using real records, must not reveal another object's data.
    alerts = data["alerts"]
    if len(alerts) > 1:
        first, second = alerts[:2]
        add(f"/alerts/{first['id']}/materials/{second['latest_material_id']}", "wrong_parent", expected_status=404)
        other = next(row for row in runs.values() if row["alert_id"] == second["id"])
        add(f"/alerts/{first['id']}/analysis/runs/{other['id']}", "wrong_parent", expected_status=404)
        artifact = next(row for row in data["artifacts"] if row["run_id"] == other["id"])
        own = next(row for row in runs.values() if row["alert_id"] == first["id"])
        add(run_path(own) + f"/artifacts/{artifact['id']}", "wrong_parent", expected_status=404)
        add(f"/cases/{case}/runs/{other['id']}", "wrong_parent", expected_status=404)
    assert len({p["path"] for p in plan}) == len(plan)
    return plan


async def fetch(plan, profile, concurrency):
    api = profile.config["api"]
    semaphore = asyncio.Semaphore(concurrency)
    done = 0
    async with httpx.AsyncClient(base_url=f"http://{api['host']}:{api['port']}",
        timeout=api["request_timeout_seconds"], trust_env=False,
        headers={"Authorization": "Bearer " + profile.secrets["access_token"]}) as client:
        async def one(spec):
            nonlocal done
            async with semaphore:
                try:
                    response = await client.get(spec["path"])
                    try:
                        body = response.json()
                    except ValueError:
                        body = {"unparsed_body": response.text}
                    result = {**spec, "status": response.status_code, "body": body}
                except httpx.HTTPError as exc:
                    result = {**spec, "status": None, "body": {"transport_error": type(exc).__name__}}
                done += 1
                if done % 20 == 0:
                    print(json.dumps({"read_completed": done, "total": len(plan)}), flush=True)
                return result
        return await asyncio.gather(*(one(spec) for spec in plan))


def audit(data, before, foreign_keys, responses):
    checks = []
    index = {t: {r["id"]: r for r in rows} for t, rows in data.items()}
    case = data["cases"][0]

    def check(name, actual, expected):
        ok = equivalent(actual, expected)
        checks.append({"name": name, "passed": ok, **({} if ok else {"actual": actual, "expected": expected})})

    def fields(name, actual, stored):
        for key in actual.keys() & stored.keys():
            check(name + "/" + key, actual[key], stored[key])

    def rows(name, actual, stored, key="id"):
        check(name + "/ids", sorted(r[key] for r in actual), sorted(r[key] for r in stored))
        expected = {r[key]: r for r in stored}
        for r in actual:
            if r[key] in expected:
                fields(name + "/" + r[key], r, expected[r[key]])

    for table, values in data.items():
        check("unchanged/" + table, sorted(values, key=lambda r: r["id"]), sorted(before[table], key=lambda r: r["id"]))
    for fk in foreign_keys:
        targets = {tuple(r[k] for k in fk["target_columns"]) for r in data[fk["target_table"]]}
        for row in data[fk["source_table"]]:
            value = tuple(row[k] for k in fk["source_columns"])
            if all(v is not None for v in value):
                check(f"foreign_key/{fk['name']}/{row['id']}", value in targets, True)
    for row in data["run_steps"]:
        for pointer in ("input_artifact_id", "output_artifact_id", "reused_artifact_id"):
            if row[pointer]:
                art = index["artifacts"][row[pointer]]
                if pointer != "reused_artifact_id":
                    check(f"step_owner/{row['id']}/{pointer}", art["run_id"], row["run_id"])
        if row["parent_step_id"]:
            check(f"step_parent/{row['id']}", index["run_steps"][row["parent_step_id"]]["run_id"], row["run_id"])
    for row in data["artifacts"]:
        if row["content_json"] is not None:
            content = json.dumps(row["content_json"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        elif row["content_text"] is not None:
            content = row["content_text"].encode()
        else:
            continue
        check(f"artifact_sha256/{row['id']}", hashlib.sha256(content).hexdigest(), row["sha256"])
        check(f"artifact_size/{row['id']}", len(content), row["size_bytes"])
    for table, value_key in (("alert_objects", "raw_value"), ("alert_source_refs", "source_event_id")):
        for row in data[table]:
            value = index["alert_materials"][row["material_id"]]
            tokens = re.findall(r"\.([^\.\[\]]+)|\[(\d+)\]", row["source_path"])
            for key, number in tokens:
                value = value[key] if key else value[int(number)]
            check(f"source_path/{table}/{row['id']}", value, row[value_key])

    def stage(name, entry):
        fields(name + "/run", entry["run"], index["runs"][entry["run"]["id"]])
        if entry.get("result"):
            result = entry["result"]
            table = "alert_assessments" if entry["run"]["kind"] == "alert_basic" else "incident_diagnoses"
            fields(name + "/result", result, index[table][result["id"]])

    for response in responses:
        path, body, kind = response["path"], response["body"], response["kind"]
        check(path + "/status", response["status"], response["expected_status"])
        if response["status"] != 200:
            continue
        identity = response.get("id")
        if kind == "subject_list":
            found = {r["facts"]["id"] for r in body["items"]}
            check(path + "/batch_ids", set(index[response["table"]]) <= found, True)
        elif kind == "subject":
            fields(path + "/facts", body["facts"], index[response["table"]][identity])
            for key, table in (("material", "alert_materials"), ("triage", "alert_assessments"), ("feedback", "alert_assessments")):
                if body.get(key):
                    fields(path + "/" + key, body[key], index[table][body[key]["id"]])
            if response["table"] == "incidents":
                member_ids = {r["alert_id"] for r in data["incident_alerts"] if r["incident_id"] == identity}
                members = [index["alerts"][key] for key in member_ids]
                keys = {(r["namespace"], r["object_type"], r["object_key"]) for r in data["alert_objects"] if r["alert_id"] in member_ids}
                known_times = [r["event_time"] for r in members if r["event_time"] is not None]
                rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
                known_severities = [r["severity"] for r in members if r["severity"] in rank]
                automatic = max(known_severities, key=rank.get) if known_severities else None
                override = index["incidents"][identity]["severity_override"]
                for key, value in {
                    "member_count": len(members), "object_count": len(keys),
                    "first_activity_at": min(known_times) if known_times else None,
                    "last_activity_at": max(known_times) if known_times else None,
                    "unknown_event_time_count": len(members) - len(known_times),
                    "severity_auto": automatic, "severity_effective": override or automatic,
                    "severity_source": "manual_override" if override else "member_max" if automatic else None,
                }.items():
                    check(path + "/derived/" + key, body["derived"][key], value)
        elif kind == "analysis":
            for entry in body["entries"]:
                stage(path, entry)
            expected = [r for r in data["runs"] if r["alert_id" if response["table"] == "alerts" else "incident_id"] == identity]
            check(path + "/run_ids", sorted(e["run"]["id"] for e in body["entries"]), sorted(r["id"] for r in expected))
            if body["current"]:
                stage(path + "/current", body["current"])
                pointer = "latest_triage_id" if response["table"] == "alerts" else "latest_diagnosis_id"
                check(path + "/pointer", body["current"]["result"]["id"], index[response["table"]][identity][pointer])
        elif kind == "stage_run":
            stage(path, body)
        elif kind == "run":
            fields(path + "/run", body["run"], index["runs"][identity])
            for key, table in (("steps", "run_steps"), ("artifacts", "artifacts"), ("members", "run_members")):
                if key in body:
                    rows(path + "/" + key, body[key], [r for r in data[table] if r["run_id"] == identity])
            if "result_ids" in body:
                check(path + "/result_ids", sorted(body["result_ids"]), sorted(r["id"] for r in data["results"] if r["source_run_id"] == identity))
        elif kind == "artifact":
            stored = index["artifacts"][identity]
            fields(path + "/metadata", body.get("artifact", body.get("metadata", {})), stored)
            check(path + "/availability", body["availability"], "available")
            check(path + "/content_json", body["content_json"], stored["content_json"])
            check(path + "/content_text", body["content_text"], stored["content_text"])
        elif kind == "material":
            stored = index["alert_materials"][identity]
            fields(path + "/metadata", body["metadata"], stored)
            check(path + "/availability", body["availability"], "available")
            check(path + "/content_json", body["content_json"], {k: stored[k] for k in ("raw_json", "ocsf_json", "enrichment")})
            check(path + "/content_text", body["content_text"], stored["raw_text"])
        elif kind == "frozen_material":
            # The endpoint retains the frozen row and its explicit read state.
            stored = index["alert_materials"][identity]
            fields(path, body.get("material", body), stored)
        elif kind == "case_list":
            own = next((r for r in body["items"] if r["case"]["id"] == case["id"]), None)
            check(path + "/contains_case", own is not None, True)
            if own:
                fields(path + "/case", own["case"], case)
        elif kind == "case":
            fields(path + "/case", body["case"], case)
            rows(path + "/members", body["members"], data["case_alerts"], "alert_id")
            rows(path + "/linked_incidents", body["linked_incidents"], data["case_incidents"], "incident_id")
            for item in body["members"]:
                fields(path + "/member_facts/" + item["alert_id"], item, index["alerts"][item["alert_id"]])
            for item in body["linked_incidents"]:
                fields(path + "/incident_facts/" + item["incident_id"], item, index["incidents"][item["incident_id"]])
            current = body["current_assessment"]
            fields(path + "/assessment", current["value"], index["case_assessments"][case["current_assessment_id"]])
            current_id = case["current_assessment_id"]
            current_members = [r for r in data["case_assessment_members"] if r["assessment_id"] == current_id]
            rows(path + "/sources", current["sources"],
                 [r for r in data["case_assessment_sources"] if r["assessment_id"] == current_id])
            # The public coverage DTO exposes alert_id, not the link row's id.
            rows(path + "/coverage", current["members"], current_members, "alert_id")
            check(path + "/freshness", current["input_freshness"]["state"], "current")
            known = {r["alert_id"] for r in current_members}
            check(path + "/uncovered", sorted(current["uncovered_current_alert_ids"]), sorted(set(index["alerts"]) - known))
        elif kind == "history":
            check(path + "/run_ids", sorted(r["run"]["id"] for r in body["items"]), sorted(r["id"] for r in data["runs"] if r["case_id"] == case["id"]))
            for entry in body["items"]:
                fields(path + "/run", entry["run"], index["runs"][entry["run"]["id"]])
                if entry["result"]:
                    fields(path + "/result", entry["result"], index["results"][entry["result"]["id"]])
        elif kind == "result":
            fields(path + "/result", body["result"], index["results"][identity])
            fields(path + "/run", body["run"], index["runs"][body["result"]["source_run_id"]])
            rows(path + "/members", body["members"], [r for r in data["result_members"] if r["result_id"] == identity])
            if body["delivery"]:
                delivery = body["delivery"]
                check(path + "/delivery_detail", delivery["detail"], index["artifacts"][delivery["detail_artifact_id"]]["content_json"])
        elif kind == "tasks":
            check(path + "/total", body["total"], len(data["tasks"]))
        elif kind == "page_data":
            for key in ("classification", "due_at"):
                check(path + "/" + key, body[key], case[key])
            check(path + "/evidence_state", body["evidence"]["state"], "not_recorded" if case["current_evidence_artifact_id"] is None else body["evidence"]["state"])
        elif kind == "records":
            verify_records(response, data, rows, check)
    return checks


def verify_records(response, data, rows, check):
    section, identity, table = response["section"], response["id"], response["table"]
    body, path = response["body"], response["path"]
    member_ids = {identity} if table == "alerts" else {r["alert_id"] for r in data["incident_alerts"] if r["incident_id"] == identity}
    objects = [r for r in data["alert_objects"] if r["alert_id"] in member_ids]
    expected = None
    if section in {"objects", "sources"}:
        expected = objects if section == "objects" else [r for r in data["alert_source_refs"] if r["alert_id"] in member_ids]
    elif section in {"members", "incidents"}:
        key = "alert_id" if section == "incidents" else "incident_id"
        links = [r for r in data["incident_alerts"] if r[key] == identity]
        target, pointer = ("incidents", "incident_id") if section == "incidents" else ("alerts", "alert_id")
        ids = {r[pointer] for r in links}
        expected = [r for r in data[target] if r["id"] in ids]
        for item in body["items"]:
            link = next(r for r in links if r[pointer] == item["id"])
            for field in ("linked_at", "membership_source", "correlation_basis", "basis_version"):
                check(path + "/" + item["id"] + "/" + field, item[field], link[field])
    elif section == "cases":
        ids = {r["case_id"] for r in data["case_alerts"] if r["alert_id"] in member_ids}
        expected = [r for r in data["cases"] if r["id"] in ids]
        for item in body["items"]:
            explicit = table == "incidents" and any(r["case_id"] == item["id"] and r["incident_id"] == identity for r in data["case_incidents"])
            check(path + "/explicit_incident_link", item["explicit_incident_link"], explicit)
            check(path + "/via_member_alert", item["via_member_alert"], True)
    elif section in {"comments", "responses"}:
        target = "comments" if section == "comments" else "response_links"
        key = "alert_id" if table == "alerts" else "incident_id"
        expected = [r for r in data[target] if r[key] == identity]
    elif section == "activities":
        key = "alert_id" if table == "alerts" else "incident_id"
        ids = {r["activity_id"] for r in data["activity_targets"] if r[key] == identity}
        expected = [r for r in data["activities"] if r["subject_" + key] == identity or r["id"] in ids]
        for item in body["items"]:
            rows(path + "/targets", item["matching_targets"], [r for r in data["activity_targets"] if r["activity_id"] == item["id"] and r[key] == identity])
    elif section == "related_alerts":
        keys = {(r["namespace"], r["object_type"], r["object_key"]) for r in objects}
        ids = {r["alert_id"] for r in data["alert_objects"] if (r["namespace"], r["object_type"], r["object_key"]) in keys} - member_ids
        expected = [r for r in data["alerts"] if r["id"] in ids]
    if expected is not None:
        rows(path + "/items", body["items"], expected)
        check(path + "/total", body["total"], len(expected))
        check(path + "/next_offset", body["next_offset"], None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--audit-existing", type=Path, help="Offline replay only; preserves captured inputs and original audit")
    args = parser.parse_args()
    config = load(args.config)
    if args.audit_existing:
        folder = args.audit_existing
        data, foreign_keys, responses = (load(folder / name) for name in ("database.json", "foreign-keys.json", "api-responses.json"))
    else:
        runtime = load(ROOT / config["run_config"])
        case = str(UUID(load(ROOT / config["case_receipt"])["receipt"]["case_id"]))
        tenant = str(UUID(runtime["target"]["tenant_id"]))
        profile = load_profile(ROOT / config["readonly_profile"])
        assert profile.config["api"]["tenant_id"] == tenant
        sql = detail_query().replace("$3", "NULL").replace("$2", "'" + case + "'").replace("$1", "'" + tenant + "'")
        captured = query(runtime, sql + ";")
        data = captured["data"]
        assert [r["id"] for r in data["cases"]] == [case]
        assert all(r["tenant_id"] == tenant for values in data.values() for r in values)
        folder = args.config.parent / datetime.now(UTC).strftime("readback-%Y%m%dT%H%M%SZ")
        folder.mkdir()
        save(folder / "database.json", data)
        save(folder / "snapshot-metadata.json", {k: v for k, v in captured.items() if k != "data"})
        foreign_keys = query(runtime, FK_SQL)
        save(folder / "foreign-keys.json", foreign_keys)
        plan = request_plan(data, config)
        save(folder / "request-plan.json", plan)
        responses = asyncio.run(fetch(plan, profile, config["http"]["concurrency"]))
        save(folder / "api-responses.json", responses)
    checks = audit(data, load(ROOT / config["before_snapshot"]), foreign_keys, responses)
    report = {"at": datetime.now(UTC).isoformat(), "scope": config["scope"],
              "case_id": data["cases"][0]["id"], "table_counts": {k: len(v) for k, v in data.items()},
              "http_status_counts": dict(Counter(str(r["status"]) for r in responses)),
              "http_unexpected": [{k: r[k] for k in ("path", "status", "expected_status", "body")} for r in responses if r["status"] != r["expected_status"]],
              "checks": len(checks), "failed_checks": [c for c in checks if not c["passed"]],
              "db_only_artifact_ids": [r["id"] for r in data["artifacts"] if not r["run_id"]]}
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    save(folder / f"checks-{stamp}.json", checks)
    save(folder / f"summary-{stamp}.json", report)
    print(json.dumps({"folder": str(folder), **{k: report[k] for k in ("checks", "http_status_counts")},
                      "failed_checks": len(report["failed_checks"]), "http_unexpected": len(report["http_unexpected"])}, ensure_ascii=False))
    return 1 if report["failed_checks"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
