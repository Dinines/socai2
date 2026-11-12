"""Export the three new, synthetic r3 audit cases from one read-only PG snapshot."""
import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "deploy/local-investigation"))
from flow_export import TABLES as EXPORT_TABLES
from flow_export import query_for

# Keep this deployed reader compatible with a frozen V1 flow_export module.
# Graph exploration persistence is not implemented and its empty table is retired.
TABLES = tuple(name for name in EXPORT_TABLES if name != "graph_explorations")
EXPORT_TABLE_SETS = (set(TABLES), set(TABLES) | {"graph_explorations"})

BATCH = "ie-audit-20261106-a1"
TENANT = "6aff0ef7-c670-5a84-a2ee-83d73e25b964"
DB = "socai2_processing_handoff"
ROLE = "socai2_processing_job"
MATERIAL = ("raw_text", "raw_json", "ocsf_json", "detection", "enrichment", "source_scope")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()


def save(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def validate(plan):
    require(plan["batch"] == BATCH and plan["tenant_id"] == TENANT, "unexpected scope")
    require([(r["key"], len(r["alert_ids"])) for r in plan["cases"]] == [("m01", 1), ("s02", 2), ("u03", 1)],
            "unexpected cards")
    ids = []
    for row in plan["cases"]:
        keys = row["operation_keys"]
        require(row["case_id"] == str(uuid5(UUID(TENANT), "socai2.case.create:" + keys["create"])), "case key mismatch")
        ids.extend([row["incident_id"], row["case_id"], *row["alert_ids"], *keys["alerts"], keys["incident"],
                    keys["prepare"], keys["start"], keys["create"]])
    require(len(ids) == len(set(ids)) and all(str(UUID(x)) == x for x in ids), "invalid or overlapping identities")


def sql_for(plan):
    validate(plan)
    return scoped_sql(plan, BATCH)


def scoped_sql(plan, batch, *, guards=None):
    """Build a snapshot for a caller-validated plan of ASCII keys and canonical UUIDs."""
    sql = ["BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;", f"SET LOCAL ROLE {ROLE};",
           f"SET LOCAL app.current_tenant_id='{TENANT}';", "SET LOCAL statement_timeout='25s';",
           (f"SELECT 1/(current_database()='{DB}' AND current_user='{ROLE}' AND "
            "current_setting('transaction_read_only')='on')::integer;"),
           ("SELECT json_build_array('_', 'snapshot', json_build_object('at',now(),'snapshot',txid_current_snapshot()::text,"
            "'database',current_database(),'role',current_user,'isolation',current_setting('transaction_isolation')));")]
    for row in plan["cases"]:
        key = row["key"]
        aids = "ARRAY[" + ",".join("'" + v + "'::uuid" for v in row["alert_ids"]) + "]"
        cid = "'" + row["case_id"] + "'::uuid" if row.get("case_id") else "NULL::uuid"
        iid = "'" + row["incident_id"] + "'::uuid" if row.get("incident_id") else "NULL::uuid"
        tenant = "'" + TENANT + "'::uuid"
        sql.append(f"""SELECT 1/(NOT EXISTS(SELECT 1 FROM socai2.alerts a LEFT JOIN socai2.alert_materials m
            ON m.tenant_id=a.tenant_id AND m.alert_id=a.id AND m.id=a.latest_material_id WHERE a.tenant_id={tenant}
            AND a.id=ANY({aids}) AND m.raw_json->>'source' IS DISTINCT FROM '{batch}'))::integer;""")
        if guards is not None:
            sql.append(guards(tenant, aids, iid, cid))
        stages = (f"ARRAY(SELECT id FROM socai2.runs WHERE tenant_id={tenant} AND "
                  f"(alert_id=ANY({aids}) OR incident_id={iid}))")
        for table in TABLES:
            query = query_for(table)
            for i, value in enumerate([tenant, aids, iid, cid, stages], 1):
                query = query.replace(f"${i}", value)
            sql.append(f"SELECT json_build_array('{key}','{table}',({query}));")
        sql.append(f"""SELECT json_build_array('{key}', 'input_freshness',COALESCE(jsonb_agg(jsonb_build_object(
            'run_id',r.id,'value',socai2.baseline_input_freshness(r.tenant_id,r.id)) ORDER BY r.id),'[]'))
            FROM socai2.runs r WHERE r.tenant_id={tenant} AND r.case_id={cid} AND r.kind='baseline';""")
    return "\n".join(sql + ["ROLLBACK;"])


def fetch(plan, *, build_sql=sql_for):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8",
           "sting-infra21", "docker", "exec", "-i", "spirithub-postgres-1", "psql", "-XAtq", "-v",
           "ON_ERROR_STOP=1", "-U", "spirithub", "-d", DB]
    proc = subprocess.run(cmd, input=build_sql(plan).encode(), capture_output=True, timeout=180, check=False)
    if proc.returncode:
        # This SQL contains only fixed column names, configured IDs and synthetic scope.
        raise RuntimeError("PG readback failed: " + proc.stderr.decode("utf-8", "replace")[:900])
    out = {r["key"]: {} for r in plan["cases"]}
    snapshot = None
    for line in proc.stdout.splitlines():
        if line == b"1":
            continue
        key, table, value = json.loads(line)
        if key == "_" and table == "snapshot":
            snapshot = value
        else:
            require(key in out and table not in out[key], "unrecognized table or duplicate row")
            out[key][table] = value
    require(snapshot and all(set(t) == set(TABLES) | {"input_freshness"} for t in out.values()), "incomplete readback")
    check_credentials(proc.stdout)
    return snapshot, out


def check_credentials(content):
    # Preserve all scoped evidence. Refuse to write it if transport credentials appear.
    secret = rb'(?i)(?:"(?:authorization|api[_-]?key|access_token|password)"\s*:\s*"(?!\s*")|bearer\s+[a-zA-Z0-9._-]{16,}|(?:postgresql|redis)://[^"\s/]+:[^"\s/]+@)'
    require(not re.search(secret, content), "possible credential in restricted snapshot; inspect before release")


def ids(rows, field="id"):
    return {r[field] for r in rows}


def pick(row, names):
    return {k: row.get(k) for k in names.split()}


def audit(row, data, frozen):
    issues = []
    checked = Counter()
    def check(ok, name, subject):
        checked[name] += 1
        if not ok:
            issues.append({"check": name, "record": subject})

    aids, iid, cid = set(row["alert_ids"]), row["incident_id"], row["case_id"]
    idx = {name: {r["id"]: r for r in data[name]} for name in TABLES}
    runs, files, materials = idx["runs"], idx["artifacts"], idx["alert_materials"]
    def same(table, identity, **scope):
        target = idx[table].get(identity)
        return target is not None and all(target[k] == v for k, v in scope.items())

    check(ids(data["alerts"]) == aids, "alert identities", row["key"])
    check(ids(data["incidents"]) == {iid}, "incident identity", row["key"])
    check(ids(data["incident_alerts"], "alert_id") == aids, "exact incident members", iid)
    if data["cases"]:
        check(ids(data["case_alerts"], "alert_id") == aids, "exact case members", cid)
        check(ids(data["case_incidents"], "incident_id") == {iid}, "case incident binding", cid)
    for m in materials.values():
        check(digest(encoded({k: m[k] for k in MATERIAL})) == m["sha256"], "stored material SHA256", m["id"])
    for packet in frozen:
        falert = packet["alert"]
        aid = falert["id"]
        current = idx["alerts"].get(aid, {})
        m = materials.get(current.get("latest_material_id"), {})
        check(m.get("raw_json") == falert, "entire frozen alert equals material raw_json", aid)
        check(current.get("title") == falert["title"] and current.get("source_alert_id") == falert["source_alert_id"],
              "page alert title and source identity", aid)
        refs = [r for r in data["alert_source_refs"] if r["material_id"] == m.get("id")]
        check(ids(refs, "source_event_id") == set(falert["source_event_ids"]), "source event pointers including absent", aid)
        snapshots = [f["content_json"] for f in files.values() if f["alert_id"] == aid and f["run_id"] is None
                     and f["kind"] == "source_snapshot"]
        check(any((s or {}).get("fused") == packet for s in snapshots), "complete original Fusion delivery", aid)
    for a in data["alerts"]:
        for k, t in (("latest_material_id", "alert_materials"), ("latest_triage_id", "alert_assessments"),
                     ("latest_feedback_id", "alert_assessments"), ("latest_explanation_id", "artifacts")):
            if a[k] or k == "latest_material_id":
                check(same(t, a[k], alert_id=a["id"]), k, a["id"])
    for inc in data["incidents"]:
        if inc["latest_diagnosis_id"]:
            check(same("incident_diagnoses", inc["latest_diagnosis_id"], incident_id=iid, state="completed"),
                  "latest published diagnosis", iid)
    for a in data["alert_assessments"]:
        if a["kind"] == "triage":
            check(same("runs", a["source_run_id"], alert_id=a["alert_id"], kind="alert_basic"),
                  "triage source run", a["id"])
            check(same("alert_materials", a["input_material_id"], alert_id=a["alert_id"]), "triage material", a["id"])
    for diagnosis in data["incident_diagnoses"]:
        check(same("runs", diagnosis["source_run_id"], incident_id=iid, kind="incident_diagnosis"),
              "diagnosis source run", diagnosis["id"])
    for artifact in files.values():
        blob = artifact["content_json"]
        body = encoded(blob) if blob is not None else (artifact["content_text"] or "").encode()
        if blob is not None or artifact["content_text"] is not None:
            check(digest(body) == artifact["sha256"] and len(body) == artifact["size_bytes"],
                  "stored artifact SHA256 and byte size", artifact["id"])
        if artifact["step_id"]:
            check(same("run_steps", artifact["step_id"], run_id=artifact["run_id"]), "artifact step ownership", artifact["id"])
    for m in data["run_members"]:
        check(m["alert_id"] in aids and same("runs", m["run_id"], case_id=cid), "frozen member scope", m["id"])
        for field, t in (("material_id", "alert_materials"), ("triage_id", "alert_assessments"), ("feedback_id", "alert_assessments")):
            if m[field]:
                check(same(t, m[field], alert_id=m["alert_id"]), "frozen " + field, m["id"])
    plans = {str(uuid5(UUID(TENANT), "socai2.stage:" + op)): aid for op, aid in
             zip(row["operation_keys"]["alerts"], row["alert_ids"], strict=True)}
    plans[str(uuid5(UUID(TENANT), "socai2.stage:" + row["operation_keys"]["incident"]))] = iid
    timeline = []
    for r in sorted(runs.values(), key=lambda r: (r["requested_at"], r["id"])):
        rid = r["id"]
        if r["kind"] == "baseline":
            check(r["case_id"] == cid, "baseline belongs to case", rid)
            seen = {m["alert_id"] for m in data["run_members"] if m["run_id"] == rid}
            check(seen == aids, "exact frozen baseline members", rid)
        else:
            check(plans.get(rid) == (r["alert_id"] or r["incident_id"]), "stage operation and subject", rid)
        if r["input_artifact_id"]:
            check(same("artifacts", r["input_artifact_id"], run_id=rid), "run input ownership", rid)
            snapshot = (files.get(r["input_artifact_id"]) or {}).get("content_json") or {}
            if r["kind"] == "baseline":
                check(set((snapshot.get("scope") or {}).get("alert_ids", [])) == aids, "frozen Case input scope", rid)
            else:
                members = snapshot.get("members", [])
                expected = {r["alert_id"]} if r["kind"] == "alert_basic" else aids
                check({m["alert"]["id"] for m in members} == expected, "A/I frozen member identities", rid)
                for member in members:
                    m = member.get("material") or {}
                    current = materials.get(m.get("id"), {})
                    check(bool(m) and all(m.get(k) == current.get(k) for k in MATERIAL),
                          "model preparation material payload equals saved source", rid)
                    if member.get("triage"):
                        triage = member["triage"]
                        check(same("alert_assessments", triage["id"], alert_id=member["alert"]["id"],
                                   source_run_id=triage["source_run_id"], verdict=triage["verdict"], rationale=triage["rationale"]),
                              "I member frozen triage and rationale from same A", rid)
        if r["state"] in {"completed", "failed", "cancelled"}:
            check(bool(r["ended_at"]), "terminal run timestamp", rid)
        steps = sorted([s for s in data["run_steps"] if s["run_id"] == rid], key=lambda s: s["seq"])
        for s in steps:
            for field in ("input_artifact_id", "output_artifact_id", "reused_artifact_id"):
                if s[field]:
                    check(same("artifacts", s[field], run_id=rid), "step " + field, s["id"])
            if s["parent_step_id"]:
                check(same("run_steps", s["parent_step_id"], run_id=rid), "step parent", s["id"])
        refs = [f for f in files.values() if f["run_id"] == rid]
        rows = [res for res in data["results"] if res["source_run_id"] == rid]
        deliveries = []
        for s in steps:
            if s["kind"] == "model" and s["state"] in {"completed", "failed", "unknown"}:
                check(same("artifacts", s["input_artifact_id"], kind="model_request", run_id=rid)
                      and same("artifacts", s["output_artifact_id"], kind="model_response", run_id=rid),
                      "model wire request and answer or error retained", s["id"])
            f = files.get(s["output_artifact_id"]) or {}
            receipt = f.get("content_json") or {}
            if receipt.get("type") != "delivery_receipt":
                continue
            outcome = receipt.get("outcome") or {}
            report = files.get(receipt.get("report_artifact_id")) or {}
            pub = report.get("content_json") or {}
            check(receipt.get("run_id") == rid and outcome.get("run_id") == rid, "C6 receipt run", s["id"])
            check(set(ids(rows)) == ({outcome["result_id"]} if outcome.get("result_id") else set()),
                  "C6 receipt and formal Result presence", s["id"])
            for field in ("report_artifact_id", "markdown_artifact_id", "detail_artifact_id"):
                check(same("artifacts", receipt.get(field), run_id=rid), "C6 receipt " + field, s["id"])
            check(bool(pub.get("conclusion")) and bool(pub.get("closing_note")) and ids(pub.get("members", []), "alert_id") == aids,
                  "C6 handoff conclusion, closing note and scoped members", s["id"])
            if pub.get("conclusion_origin") == "system":
                check(pub.get("validation_state") == "system_only" and not any(m["conclusion_covered"] for m in pub["members"]),
                      "C6 fallback reports zero model coverage", s["id"])
            adoption = outcome.get("adoption") or {}
            if adoption.get("assessment_id"):
                check(same("case_assessments", adoption["assessment_id"], case_id=cid),
                      "C6 adoption receipt points to saved assessment", s["id"])
            deliveries.append({"receipt_id": f["id"], "report_id": report.get("id"), "origin": pub.get("conclusion_origin"),
                               "conclusion": pub.get("conclusion"), "delivery_state": receipt.get("delivery_state"),
                               "result_id": outcome.get("result_id"), "adoption": adoption,
                               "covered_members": sum(bool(m["conclusion_covered"]) for m in pub.get("members", [])),
                               "total_members": len(pub.get("members", []))})
        timeline.append({"run": r, "steps": steps, "artifacts": [pick(f, "id step_id kind schema_version material_state") for f in refs],
                         "model_attempt_steps": sum(s["kind"] == "model" and s["state"] not in {"skipped", "planned"} for s in steps),
                         "tool_attempt_steps": sum(s["kind"] == "tool" and s["state"] not in {"skipped", "planned"} for s in steps),
                         "formal_results": sorted(ids(rows)), "delivery_receipts": deliveries})
    for res in data["results"]:
        rid = res["source_run_id"]
        check(same("runs", rid, kind="baseline", case_id=cid), "result source run", res["id"])
        rm = [m for m in data["result_members"] if m["result_id"] == res["id"]]
        check(ids(rm, "alert_id") == aids and all(m["run_id"] == rid for m in rm), "formal result members", res["id"])
        if res["conclusion_origin"] == "system":
            check(res["validation_state"] == "system_only" and not any(m["conclusion_covered"] for m in rm),
                  "system fallback separate from model coverage", res["id"])
        for field in ("graph_artifact_id", "report_artifact_id", "input_artifact_id"):
            if res[field]:
                check(same("artifacts", res[field], run_id=rid), "result " + field, res["id"])
    for c in data["cases"]:
        if c["current_assessment_id"]:
            check(same("case_assessments", c["current_assessment_id"], case_id=cid), "current assessment scope", cid)
    for source in data["case_assessment_sources"]:
        check(same("case_assessments", source["assessment_id"], case_id=cid), "assessment ownership", source["id"])
        for field, tbl in (("result_id", "results"), ("artifact_id", "artifacts"), ("task_revision_id", "task_revisions")):
            if source[field]:
                check(same(tbl, source[field], case_id=cid), "assessment " + field, source["id"])
    return {"checks": dict(checked), "issues": issues, "timeline": timeline}


def artifact_link(identity):
    return f"[{identity[:8]}](artifacts/{identity}.json)" if identity else "无主工件指针"


def describe_artifact(record):
    """Show what went in/out; keep full wire bodies in the linked original."""
    if not record:
        return "无主工件指针"
    kind = record["kind"]
    raw = record.get("content_json") or {}
    value = raw.get("payload") or raw
    detail = ""
    if kind == "model_request":
        body = value.get("body") or {}
        detail = f"{body.get('model', '')}，{len(body.get('messages', []))} 条消息"
    elif kind == "model_response":
        detail = "有原答" if value.get("raw") is not None else "无原答"
        status = (value.get("transport_error") or {}).get("http_status")
        if status:
            detail += f"，HTTP {status}"
        if value.get("validation_error"):
            detail += "，" + str(value["validation_error"])
    elif kind == "tool_request":
        detail = str(value.get("tool_name") or "")
    elif kind == "tool_response":
        count = value.get("returned_rows")
        detail = f"{count} 行" if count is not None else str(value.get("state") or "")
    elif value.get("type") == "delivery_receipt":
        detail = str(value.get("delivery_state") or "")
    else:
        detail = str(value.get("type") or "")
    return f"{artifact_link(record['id'])} {kind}" + (" · " + detail.replace("|", "\\|").replace("\n", " ") if detail else "")


def write_case(directory, row, data, frozen):
    from app.socai2.case_data import export_page_data
    directory.mkdir()
    (directory / "artifacts").mkdir()
    outcome = audit(row, data, frozen)
    save(directory / "database.json", {k: data[k] for k in TABLES})
    save(directory / "input-freshness.json", data["input_freshness"])
    for f in data["artifacts"]:
        require(str(UUID(f["id"])) == f["id"], "invalid artifact id")
        save(directory / "artifacts" / (f["id"] + ".json"), f)
    page = {"alerts": [{**a, "latest_material": next((m["id"] for m in data["alert_materials"] if m["id"] == a["latest_material_id"]), None),
                        "published_triage": next((t for t in data["alert_assessments"] if t["id"] == a["latest_triage_id"]), None)}
                       for a in data["alerts"]], "incidents": data["incidents"], "incident_members": data["incident_alerts"],
            "diagnosis_attempts": data["incident_diagnoses"], "investigations": data["runs"], "results": data["results"],
            "result_members": data["result_members"], "case_page_data": asyncio.run(export_page_data(data))}
    save(directory / "page-fields.json", page)
    save(directory / "stages.json", outcome)
    artifacts = {f["id"]: f for f in data["artifacts"]}
    lines = [f"# {row['key']} · {row['title']}", "",
             "[页面字段与当前判断](page-fields.json) · [全部 29 张表](database.json) · [逐步参数、错误与用量](stages.json)", "",
             "按库中步骤序号排列。点击工件可读完整请求、原始返回或失败回执。主指针为空时，请核对 Run 冻结输入和本步关联工件。", ""]
    for item in outcome["timeline"]:
        r = item["run"]
        lines += [f"## {r['kind']} · {r['state']} · {r['id']}", "",
                  (f"范围输入 {artifact_link(r['input_artifact_id'])}。交付 {r['delivery_state']}。"
                  f"停止原因 {r['stop_reason'] or '无记录'}。正式 Result {len(item['formal_results'])} 份。"
                  f"模型尝试 {item['model_attempt_steps']} 次，工具尝试 {item['tool_attempt_steps']} 次。"), "",
                  "| 步骤 | 操作 | 状态 | 输入 | 输出 | 其余关联工件 |", "|---|---|---|---|---|---|"]
        for s in item["steps"]:
            other = [artifact_link(f["id"]) for f in item["artifacts"] if f["step_id"] == s["id"]
                     and f["id"] not in {s["input_artifact_id"], s["output_artifact_id"]}]
            error = (s["error"] or {}).get("code", "")
            lines.append(f"| {s['seq']} · {s['stage_code']} | {s['name']} | {s['state']} {error} | "
                         f"{describe_artifact(artifacts.get(s['input_artifact_id']))} | "
                         f"{describe_artifact(artifacts.get(s['output_artifact_id']))} | {'、'.join(other)} |")
        lines.append("")
        for d in item["delivery_receipts"]:
            lines += [(f"C6 [{d['origin']}](artifacts/{d['report_id']}.json) 报告中的结论为「{d['conclusion']}」。"
                      f"本轮交接回执 {artifact_link(d['receipt_id'])} 标记 `{d['delivery_state']}`，"
                      f"覆盖 {d['covered_members']}/{d['total_members']}。"
                       f"正式 Result 为 `{d['result_id'] or '无'}`。"), ""]
    (directory / "stages.md").write_text("\n".join(lines), encoding="utf-8")
    return {"case": row["key"], "counts": {t: len(data[t]) for t in TABLES},
            "checks": sum(outcome["checks"].values()), "issues": outcome["issues"],
            "model_attempt_steps": sum(r["model_attempt_steps"] for r in outcome["timeline"]),
            "tool_attempt_steps": sum(r["tool_attempt_steps"] for r in outcome["timeline"]),
            "run_states": [pick(r["run"], "id kind state delivery_state stop_reason") for r in outcome["timeline"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "use a new output directory for each snapshot")
    body = args.manifest.read_bytes()
    plan = json.loads(body)
    inputs = (args.manifest.parent / "inputs.json").read_bytes()
    frozen = json.loads(inputs)
    for r in plan["cases"]:
        require(ids(frozen[r["key"]]) == set(r["alert_ids"]) and all(p["incident_id"] == r["incident_id"] and
                p["tenant_id"] == TENANT for p in frozen[r["key"]]), "frozen test inputs do not match scope")
    metadata, payload = fetch(plan)
    sys.path.insert(0, str(ROOT / "services/api"))
    args.output.mkdir(parents=True)
    rows = [write_case(args.output / r["key"], r, payload[r["key"]], frozen[r["key"]]) for r in plan["cases"]]
    summary = {"batch": BATCH, "snapshot": metadata, "plan_sha256": digest(body), "inputs_sha256": digest(inputs), "cases": rows,
               "note": "row and reference checks only; model semantics, dispatch coverage and UI require separate review"}
    save(args.output / "summary.json", summary)
    files = {p.relative_to(args.output).as_posix(): digest(p.read_bytes()) for p in sorted(args.output.rglob("*")) if p.is_file()}
    save(args.output / "files.sha256.json", files)
    print(json.dumps({"output": str(args.output), "files": len(files), "checks": sum(r["checks"] for r in rows),
                      "issues": sum(len(r["issues"]) for r in rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
