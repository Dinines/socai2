"""Build this actual batch's ledger with the current investigation_test contract."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from investigation_test.models import Document

E = Path(__file__).resolve().parent
R = E.parents[3]


def read(name):
    return json.loads((E / name).read_text())


def main():
    p = read("batch/profile.json")
    snapshot = read("final-pg.json")
    rows = snapshot["rows"]
    validation = read("final-validation.json")
    assert validation["status"] == "passed_for_business_flow" and validation["tables_unchanged"]
    quality = read("quality-register.json")
    mapping = read("case-mapping.json")
    first = read("first-round-snapshot.json")["rows"]
    first_runs = {r["id"] for r in first["runs"]}
    output = E / "viewer-input"
    output.mkdir(exist_ok=False)
    evidence = []

    def save(eid, label, value, source):
        name = eid + ".json"
        raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
        (output / name).write_bytes(raw)
        evidence.append({"id": eid, "path": name, "label": label, "mime_type": "application/json", "visibility": "public", "source_ref": str((E / source).relative_to(R))})

    save("preparation", "当前发布、空态与来源核对", {name: read(name) for name in ("activation.json", "preflight-02.json", "connector-01.json", "release-receipts-comparison.json", "send-S01-context-recovery-02.json")}, "preflight-02.json")
    manifest = read("batch/manifest.json")
    wires = {record["wire"]: read("batch/" + record["wire"]) for phase in manifest["phases"].values() for record in phase["records"]}
    save("inputs", "冻结告警和上下文原件", {"manifest": manifest, "wire": wires}, "batch/manifest.json")
    save("transports", "四阶段Kafka ACK与实际通道失败", {name: read(name) for name in ("send-S01-context-01.json", "send-S01-context-02.json", "send-S01-alerts-01.json", "send-S04-context-01.json", "send-S04-alerts-01.json", "transport-block-01.json")}, "send-S04-alerts-01.json")
    save("checks", "各阶段程序判据及上下文查询核对", {name: read(name) for name in ("P2-validation.json", "P3-validation.json", "P4-validation.json", "no-changes-validation.json", "context-query-verification.json")}, "final-validation.json")
    save("execution", "实际任务、Run、步骤及Result索引", {"snapshot_sha256": hashlib.sha256((E / "final-pg.json").read_bytes()).hexdigest(), "counts": snapshot["counts"], "tasks": rows["analysis_tasks"], "attempts": rows["analysis_attempts"], "runs": rows["runs"], "steps": rows["run_steps"], "results": rows["results"], "case_alerts": rows["case_alerts"]}, "final-pg.json")
    save("models", "14次真实模型请求与原答索引", read("model-io/index.json"), "model-io/index.json")
    save("quality", "质量问题原始诊断，后置处理", quality, "quality-register.json")
    save("http", "完整HTTP读回及前后数据库一致", {"http": read("final-http-01.json")["value"]["report"], "unchanged_tables": validation["read_before_after_tables"], "tables_unchanged": validation["tables_unchanged"]}, "final-http-01.json")
    if (E / "static-verification.json").exists():
        save("static", "本机静态查阅更新，旧记录保持", read("static-verification.json"), "static-verification.json")

    definitions = [
        ("setup", "P1", "当前环境和材料就绪，失败意图与恢复事实保留", "r4身份/profile/空态通过；通道恢复后证实首次发送未执行", ["preparation", "transports"]),
        ("ingress", "P2", "上下文先入湖，3告警形成事件并完成真实A/I", "12上下文/3告警ACK与读回、3A/1I完成，76次HTTP一致", ["inputs", "transports", "checks", "models"]),
        ("whole-initial", "P3", "整事件Case首轮覆盖3成员，来源与结果可读", "HTTP201；整案首轮3成员，accepted/uncertain/partial", ["checks", "execution", "models"]),
        ("single-initial", "P3", "单告警Case首轮固定A01，质量不扩大程序范围", "HTTP201；单案1成员，accepted/uncertain/partial；质量单列", ["checks", "execution", "models", "quality"]),
        ("append-update", "P4", "追加E13/A04后事件4成员，整案R2比较最近R1，单案不扩展", "增量ACK与入湖通过；I完整4成员；整案R2 expanded，单案保持1轮/1成员", ["inputs", "transports", "checks", "execution", "quality"]),
        ("unchanged", "P5", "无新材料的新key检查不得增加Run或模型调用", "skipped/no_changes；0attempt/Run/model增量", ["checks", "execution"]),
        ("readback", "P5", "所有步骤、原答与Result通过正式HTTP追溯", "318 GET；9Run/77step/224个Run工件、3Result一致，前后23表不变", ["http", "execution", "models", "quality"]),
    ]
    cases = {cid: {"id": cid, "use_case_id": phase, "scenario_id": "streaming-normal-flow-v2", "status": "passed", "expected": [expected], "actual": [actual], "operation_ids": [], "evidence_ids": refs} for cid, phase, expected, actual, refs in definitions}
    operations, run_case = [], {}

    def operation(oid, cid, intent, state, refs, mappings=None, occurred=None):
        operations.append({"id": oid, "case_id": cid, "intent": intent, "execution_state": state, "occurred_at": occurred, "mappings": mappings or [], "evidence_ids": refs})
        cases[cid]["operation_ids"].append(oid)

    operation("transport-not-executed", "setup", "首发SSH握手失败，恢复核实没有远端发送", "failed", ["preparation", "transports"])
    for label, phase, cid in [("send-S01-context-02.json", "S01-context", "ingress"), ("send-S01-alerts-01.json", "S01-alerts", "ingress"), ("send-S04-context-01.json", "S04-context", "append-update"), ("send-S04-alerts-01.json", "S04-alerts", "append-update")]:
        ack = read(label)["value"]
        assert ack["status"] == "accepted_only" and ack["accepted"] == ack["requested"]
        operation("send-" + phase, cid, phase + "逐条发送并核ACK", "completed", ["transports"])
    nochange = read("no-changes-validation.json")["task_id"]
    result_tables = {"alert": ("alert_assessments", "alert_assessment"), "incident": ("incident_diagnoses", "incident_diagnosis"), "case": ("results", "case_result")}
    for task in sorted(rows["analysis_tasks"], key=lambda t: (t["submitted_at"], t["id"])):
        attempts = [a for a in rows["analysis_attempts"] if a["task_id"] == task["id"]]
        runs = [a["run_id"] for a in attempts if a["run_id"]]
        if task["id"] == nochange:
            cid = "unchanged"
        elif task["id"] == mapping["whole"]["task_id"]:
            cid = "whole-initial"
        elif task["id"] == mapping["single"]["task_id"]:
            cid = "single-initial"
        else:
            cid = "ingress" if runs and all(r in first_runs for r in runs) else "append-update"
        links = []
        for rid in runs or [None]:
            link = {"subject_type": task["subject_type"], "subject_id": task["subject_id"], "task_id": task["id"], "run_id": rid}
            table, kind = result_tables[task["subject_type"]]
            result = next((r for r in rows[table] if r["source_run_id"] == rid), None) if rid else None
            if result:
                link.update(result_type=kind, result_id=result["id"])
            links.append(link)
            if rid:
                run_case[rid] = cid
        operation("task-" + task["id"], cid, task["subject_type"] + " " + task["intent"] + "（" + task["source"] + "）", task["state"], ["execution", "models"], links, task["submitted_at"])
    operation("http-final", "readback", "只读遍历所有任务和目录并核对原件", "completed", ["http"])
    issues = [{"id": q["id"], "case_id": run_case[q["run_id"]], "run_id": q["run_id"], "stage": q["stage"], "category": q["diagnostic"]["code"], "description": q["diagnostic"]["code"] + "：" + q["diagnostic"].get("path", "") + "。程序诊断保留；原答不改，质量后置处理。", "status": "deferred", "affects_flow": False, "evidence_ids": ["quality", "models"]} for q in quality["program_diagnostics"]]
    doc = {"schema_version": 1, "batch": {"id": p["batch_id"], "environment": p["release"], "title": "完整调查流程02：首轮、告警追加与后轮", "scenario_version": "socai2-streaming-s01-s04/v2", "execution_state": "finished", "mode": "live", "provenance": "live_execution", "started_at": read("activation.json")["observed_at"], "updated_at": datetime.now(timezone.utc).isoformat(), "quality_status": "issues_recorded"}, "cases": list(cases.values()), "operations": operations, "preparation": {"status": "prepared", "cleanup_mode": "executed", "summary": "协调方完成本轮范围内清理和r4发布；测试核空态、材料/版本/来源。首次通道失败已核实未发送，原失败保留。", "resources": ["21 aisoc PostgreSQL", "Kafka", "Redis", "raw_events lake", "r4 HTTP", "真实配置模型"], "observed_at": read("preflight-02.json")["value"]["observed_at"], "evidence_ids": ["preparation", "inputs", "transports"]}, "quality_issues": issues, "evidence": evidence}
    raw = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    Document.model_validate_json(raw)
    (output / "document.json").write_text(raw)
    service = json.loads((R / "deploy/aisoc21" / p["release"] / "viewer/service.json").read_text())
    assert len(raw.encode()) <= service["max_document_bytes"]
    assert all((output / e["path"]).stat().st_size <= service["max_evidence_bytes"] for e in evidence)
    report = {"status": "prepared_current_contract_validated", "batch_id": p["batch_id"], "cases": len(cases), "operations": len(operations), "quality_issues": len(issues), "files": {f.name: {"sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "bytes": f.stat().st_size} for f in output.iterdir()}, "published": False}
    with (E / "ledger-preparation.json").open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "files"}))


if __name__ == "__main__":
    main()
