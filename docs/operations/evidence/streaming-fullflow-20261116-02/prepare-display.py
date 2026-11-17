"""Supplement the finished execution with saved HTTP exchanges, never re-execute it."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from investigation_test.config import Config
from investigation_test.models import Document
from investigation_test.store import LedgerError, Store

E = Path(__file__).resolve().parent
R = E.parents[3]


def read(name):
    return json.loads((E / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old = E / "viewer-input"
    original = read("viewer-input/document.json")
    assert original["batch"]["execution_state"] == "finished"
    frozen = {p.name: sha(p) for p in old.iterdir()}
    rows = read("final-pg.json")["rows"]
    exchanges = []
    names = ["create-whole-01.json", "create-single-01.json", "S04-I-check-01.json", "S04-case-check-01.json", "no-changes-01.json"]
    for name in names:
        receipt = read(name)
        assert receipt["state"] == "returned" and receipt["exit"] == 0
        value = receipt["value"]
        assert set(value) == {"request", "response", "observed_at"}
        assert value["request"]["method"] == "POST"
        response = value["response"]
        if name.startswith("create-"):
            assert response["status"] == 201 and len(response["body"]["allocations"]) == 1
            accepted = response["body"]["allocations"][0]["initial_task"]
        else:
            assert response["status"] == 202
            accepted = response["body"]
        task = next(t for t in rows["analysis_tasks"] if t["id"] == accepted["task_id"])
        assert task["subject_type"] == accepted["subject_type"] and task["subject_id"] == accepted["subject_id"]
        attempts = [a for a in rows["analysis_attempts"] if a["task_id"] == task["id"]]
        assert len(attempts) == (0 if name == "no-changes-01.json" else 1)
        rid = attempts[0]["run_id"] if attempts else None
        if rid:
            run = next(r for r in rows["runs"] if r["id"] == rid)
            assert run[task["subject_type"] + "_id"] == task["subject_id"]
        else:
            assert task["state"] == "skipped"
        exchanges.append({"subject_type": task["subject_type"], "subject_id": task["subject_id"], "task_id": task["id"], "run_id": rid, **value, "sources": [{"path": str((E / name).relative_to(R)), "sha256": sha(E / name)}, {"path": str((E / "final-pg.json").relative_to(R)), "sha256": sha(E / "final-pg.json")}]})

    doc = json.loads(json.dumps(original))
    doc["batch"].update(id=original["batch"]["id"] + "-viewer-02", title="完整调查流程02 · 补齐HTTP接入展示（同一执行）", provenance="saved_evidence", updated_at=datetime.now(timezone.utc).isoformat())
    doc["preparation"]["summary"] += " 本观察记录由原02已保存证据派生，仅补齐HTTP接入展示，未重新投放、清理、调用模型或执行调查。"
    task_ids = {x["task_id"] for x in exchanges}
    affected = set()
    for operation in doc["operations"]:
        if any(m.get("task_id") in task_ids for m in operation["mappings"]):
            operation["evidence_ids"].append("http-exchanges")
            affected.add(operation["case_id"])
    for case in doc["cases"]:
        if case["id"] in affected:
            case["evidence_ids"].append("http-exchanges")
    doc["evidence"].append({"id": "http-exchanges", "path": "http-exchanges.json", "label": "真实HTTP请求及201/202回执（原02已保存证据）", "mime_type": "application/json", "visibility": "public", "source_ref": str((E / "create-whole-01.json").relative_to(R))})
    encoded = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    Document.model_validate_json(encoded)
    # Use the shipped page's actual matcher; no duplicate matching implementation.
    script = """
import {matchingExchange} from './services/investigation_test/web/execution_flow.mjs';
import assert from 'node:assert/strict';
let raw='';for await(const chunk of process.stdin)raw+=chunk;
const {exchanges,document}=JSON.parse(raw);
let matched=0;
for(const op of document.operations)for(const m of op.mappings){
 const actual=matchingExchange(exchanges,m,m.run_id,m.task_id);
 if(exchanges.some(e=>e.task_id===m.task_id)){assert(actual);matched++;}
 else assert.equal(actual,null);
 for(const e of exchanges)if(e.task_id!==m.task_id)assert.equal(matchingExchange([e],m,m.run_id,m.task_id),null);
}
assert.equal(matched,5);assert.equal(exchanges.filter(e=>e.run_id===null).length,1);
console.log(JSON.stringify({status:'passed',matched_exchanges:matched,cross_task_and_round_isolated:true}));
"""
    checked = subprocess.run(["node", "--input-type=module", "-e", script], input=json.dumps({"exchanges": exchanges, "document": doc}), text=True, capture_output=True, cwd=R, check=True)
    out = E / "viewer-display-input"
    out.mkdir(exist_ok=False)
    for evidence in original["evidence"]:
        shutil.copyfile(old / evidence["path"], out / evidence["path"])
        assert sha(old / evidence["path"]) == sha(out / evidence["path"])
    (out / "document.json").write_text(encoded)
    (out / "http-exchanges.json").write_text(json.dumps({"schema": "socai2.test-http-exchanges.v1", "source_execution_batch_id": original["batch"]["id"], "supplement_only": True, "new_business_calls": 0, "new_model_calls": 0, "exchanges": exchanges}, ensure_ascii=False, indent=2) + "\n")
    service = json.loads((R / "deploy/aisoc21" / doc["batch"]["environment"] / "viewer/service.json").read_text())
    assert (out / "document.json").stat().st_size <= service["max_document_bytes"]
    assert all((out / e["path"]).stat().st_size <= service["max_evidence_bytes"] for e in doc["evidence"])
    assert frozen == {p.name: sha(p) for p in old.iterdir()}
    with tempfile.TemporaryDirectory(prefix="socai2-display-check-") as tmp:
        config = Config.model_validate(service).model_copy(update={"ledger_root": tmp})
        store = Store(config)
        store.publish(old / "document.json", 0)
        before = {str(p.relative_to(Path(tmp))): sha(p) for p in Path(tmp).rglob("*") if p.is_file()}
        try:
            store.publish(old / "document.json", 1)
        except LedgerError as exc:
            assert exc.code == "batch_terminal" and exc.status == 409
            terminal_check = {"code": exc.code, "status": exc.status, "scope": "local_temporary_store_using_current_source"}
        else:
            raise AssertionError("finished batch unexpectedly mutable")
        assert before == {str(p.relative_to(Path(tmp))): sha(p) for p in Path(tmp).rglob("*") if p.is_file()}
        assert store.publish(out / "document.json", 0).revision == 1
        assert json.loads(store.evidence(doc["batch"]["id"], "http-exchanges")[1])["exchanges"] == exchanges
    report = {"status": "prepared_current_contract_validated", "batch_id": doc["batch"]["id"], "input_directory": out.name, "preserve_batch_ids": [original["batch"]["id"]], "cases": len(doc["cases"]), "operations": len(doc["operations"]), "quality_issues": len(doc["quality_issues"]), "http_exchange_checks": json.loads(checked.stdout), "terminal_protection": terminal_check, "local_publish_readback": "passed", "original_input_unchanged": frozen, "files": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in out.iterdir()}, "published": False}
    with (E / "display-preparation.json").open("x") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k not in {"files", "original_input_unchanged"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
