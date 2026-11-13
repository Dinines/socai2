"""Direct Case comment HTTP acceptance; only creates its own synthetic records."""
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--read-existing", type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.profile.read_text())
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    secret = json.loads((ROOT / cfg["credential"]["file"]).read_text())
    if cfg["credential"]["kind"] == "existing_login":
        req = urllib.request.Request(cfg["credential"]["login_url"],
            data=json.dumps({k: secret[k] for k in ("email", "password")}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=cfg["timeout_seconds"]) as r:
            token = json.load(r)["access_token"]
    else:
        token = secret["api_key"]
    receipts = []

    def request(method, path, body=None, code=200):
        save(out / f"{len(receipts)+1:02}-intent.json", {"method": method, "path": path, "input": body})
        req = urllib.request.Request(cfg["base_url"] + path, method=method,
            data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=cfg["timeout_seconds"]) as r:
                status, data = r.status, json.load(r)
        except urllib.error.HTTPError as e:
            status, data = e.code, json.load(e)
        receipts.append({"method": method, "path": path, "input": body, "status": status, "body": data})
        save(out / "responses.json", receipts)
        assert status == code, (status, data)
        return data

    contract = request("GET", "/openapi.json")
    assert contract["info"]["version"] == cfg["release"]
    assert sum(len(v) for p, v in contract["paths"].items() if p.startswith("/api/v1/socai2")) == 59
    base = "/api/v1/socai2/cases"
    if args.read_existing:
        fixture = json.loads(args.read_existing.read_text())
        path = base + "/" + fixture["case_id"]
        current = request("GET", path + "/comments")
        assert current["items"] == fixture["comments"] and current["total"] == 2
        assert request("GET", base + "/" + fixture["other_case_id"] + "/comments")["total"] == 0
        assert request("GET", path + "/tasks/" + fixture["task"]["id"]) == fixture["task"]
        assert request("GET", path + "/runs/" + fixture["run"]["id"])["run"] == fixture["run"]
        assert request("GET", path)["case"] == fixture["case_after"]
        save(out / "verification.json", {"passed": True, "mode": "read_only", "http_requests": len(receipts), "fixture": str(args.read_existing)})
        print("Readback passed", len(receipts), "GETs")
        return

    alert = cfg.get("source_alert_id")
    if not alert:
        alert = request("GET", base + "/" + cfg["source_case_id"])["members"][0]["alert_id"]
    case = request("POST", base, {"operation_key": str(uuid4()), "title": cfg["title"], "alert_ids": [alert]})
    other = request("POST", base, {"operation_key": str(uuid4()), "title": cfg["title"] + "-其他案件", "alert_ids": [alert]})
    path = base + "/" + case["case_id"]
    task = request("POST", path + "/tasks", {"operation_key": str(uuid4()),
        "expected_scope_revision": case["scope_revision"], "title": "评论不完成这项人工任务"})["task"]
    before = request("GET", path)["case"]
    run = request("GET", path + "/runs/" + case["pending_run_id"])["run"]
    assert request("GET", path + "/comments")["total"] == 0
    first_input = {"operation_key": str(uuid4()), "body": "  本批为评论存取验收。\n仍待运维核实；此评论不是已核实事实。<tag>保留原文</tag>  "}
    first = request("POST", path + "/comments", first_input)
    assert first["body"] == first_input["body"] and first["author_id"] == before["created_by"]
    assert first["author_name_snapshot"] and first["created_at"] and first["row_version"] == 1
    assert first["edited_at"] is None and first["edited_by"] is None
    assert request("POST", path + "/comments", first_input) == first
    assert request("POST", path + "/comments", dict(first_input, body="相同key改变内容"), 409)["detail"] == "operation_key_conflict"
    request("POST", path + "/comments", {"operation_key": str(uuid4()), "body": " \n "}, 422)
    second = request("POST", path + "/comments", {"operation_key": str(uuid4()), "body": "第二条普通协作说明，任务继续保留。"})
    page = request("GET", path + "/comments?limit=1")
    assert page["items"] == [first] and page["total"] == 2 and page["next_offset"] == 1
    page2 = request("GET", path + "/comments?limit=1&offset=1")
    assert page2["items"] == [second] and page2["next_offset"] is None
    request("GET", path + "/comments?q=unsupported", code=422)
    assert request("GET", base + "/" + other["case_id"] + "/comments")["total"] == 0
    request("GET", base + "/" + str(uuid4()) + "/comments", code=404)
    assert request("GET", path + "/tasks/" + task["id"]) == task
    assert request("GET", path + "/runs/" + run["id"])["run"] == run
    after = request("GET", path)["case"]
    assert after["row_version"] == before["row_version"] + 2
    assert after["business_updated_at"] >= before["business_updated_at"]
    assert {k:v for k,v in after.items() if k not in {"row_version", "business_updated_at"}} == {
        k:v for k,v in before.items() if k not in {"row_version", "business_updated_at"}}
    activities = request("GET", path + "/activities")
    notes = [r for r in activities["items"] if r["action"] == "case_comment_created"]
    assert len(notes) == 2
    saved = [t["after_value"]["operation_receipt"]["outcome"] for r in notes for t in r["matching_targets"] if t.get("case_id") == case["case_id"]]
    assert sorted(saved, key=lambda r:r["id"]) == sorted([first, second], key=lambda r:r["id"])
    fixture = {"case_id": case["case_id"], "other_case_id": other["case_id"], "comments": [first, second],
        "task": task, "run": run, "case_before": before, "case_after": after}
    save(out / "fixture.json", fixture)
    result = {"passed": True, "mode": "new_synthetic_case_only", "database_expected": cfg["database"],
        "http_requests": len(receipts), "case_id": case["case_id"], "comments": 2, "models": 0,
        "task_run_and_case_semantics_unchanged": True, "sql_verification": "separate_snapshot_required"}
    save(out / "verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
