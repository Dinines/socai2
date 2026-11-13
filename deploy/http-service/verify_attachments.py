"""Direct Case attachment-reference HTTP acceptance; only creates its own synthetic records."""
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
            status = e.code
            raw = e.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"non_json_response": raw}
        if path == "/openapi.json" and status == 200:
            save(out / "openapi.json", data)
            receipt_data = {"saved_as": "openapi.json", "release": data["info"]["version"]}
        else:
            receipt_data = data
        receipts.append({"method": method, "path": path, "input": body, "status": status, "body": receipt_data})
        save(out / "responses.json", receipts)
        assert status == code, (status, data)
        return data

    contract = request("GET", "/openapi.json")
    assert contract["info"]["version"] == cfg["release"]
    assert sum(len(v) for p, v in contract["paths"].items() if p.startswith("/api/v1/socai2")) == 62
    base = "/api/v1/socai2/cases"
    if args.read_existing:
        fixture = json.loads(args.read_existing.read_text())
        path = base + "/" + fixture["case_id"]
        current = request("GET", path + "/attachments")
        assert current["items"] == fixture["attachments"] and current["total"] == 2
        for item in fixture["attachments"]:
            assert request("GET", path + "/attachments/" + item["id"]) == item
        assert request("GET", base + "/" + fixture["other_case_id"] + "/attachments")["total"] == 0
        assert request("GET", path)["case"] == fixture["case_after"]
        assert request("GET", path + "/tasks/" + fixture["task"]["id"]) == fixture["task"]
        assert request("GET", path + "/runs/" + fixture["run"]["id"])["run"] == fixture["run"]
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
        "expected_scope_revision": case["scope_revision"], "title": "附件登记不完成这项人工任务"})["task"]
    before = request("GET", path)["case"]
    run = request("GET", path + "/runs/" + case["pending_run_id"])["run"]
    assert request("GET", path + "/attachments")["total"] == 0
    # Explicit synthetic reference IDs: no real upload, download or byte check is claimed.
    first_input = {"operation_key": str(uuid4()), "file_id": "SYNTHETIC-file-" + str(uuid4()),
        "file_name": "运维工单（引用验收样例）.pdf", "mime_type": "application/pdf", "size_bytes": 1234,
        "sha256": "a" * 64}
    first = request("POST", path + "/attachments", first_input)
    for key, value in first_input.items():
        if key != "operation_key":
            assert first[key] == value
    assert first["case_id"] == case["case_id"] and first["created_by"] == before["created_by"] and first["created_at"]
    assert first["file_owner"] == "business_backend" and first["availability"] == "managed_by_backend"
    assert request("POST", path + "/attachments", first_input) == first
    assert request("POST", path + "/attachments", dict(first_input, file_name="更改元数据"), 409)["detail"] == "operation_key_conflict"
    assert request("POST", path + "/attachments", dict(first_input, operation_key=str(uuid4())), 409)["detail"] == "attachment_already_linked"
    request("POST", path + "/attachments", dict(first_input, operation_key=str(uuid4()), size_bytes=-1), 422)
    request("POST", path + "/attachments", dict(first_input, operation_key=str(uuid4()), file_id=" "), 422)
    second = request("POST", path + "/attachments", {"operation_key": str(uuid4()),
        "file_id": "SYNTHETIC-empty-file-" + str(uuid4()), "file_name": "空文件引用.txt", "mime_type": "text/plain", "size_bytes": 0})
    assert second["sha256"] is None and second["size_bytes"] == 0
    page = request("GET", path + "/attachments?limit=1")
    assert page["items"] == [first] and page["total"] == 2 and page["next_offset"] == 1
    page2 = request("GET", path + "/attachments?limit=1&offset=1")
    assert page2["items"] == [second] and page2["next_offset"] is None
    assert request("GET", path + "/attachments/" + first["id"]) == first
    request("GET", path + "/attachments?q=unsupported", code=422)
    assert request("GET", base + "/" + other["case_id"] + "/attachments")["total"] == 0
    request("GET", base + "/" + other["case_id"] + "/attachments/" + first["id"], code=404)
    request("GET", base + "/" + str(uuid4()) + "/attachments", code=404)
    assert request("GET", path + "/tasks/" + task["id"]) == task
    assert request("GET", path + "/runs/" + run["id"])["run"] == run
    after = request("GET", path)["case"]
    assert after["row_version"] == before["row_version"] + 2
    assert after["business_updated_at"] >= before["business_updated_at"]
    assert {k:v for k,v in after.items() if k not in {"row_version", "business_updated_at"}} == {
        k:v for k,v in before.items() if k not in {"row_version", "business_updated_at"}}
    activities = request("GET", path + "/activities")
    links = [r for r in activities["items"] if r["action"] == "case_attachment_linked"]
    assert len(links) == 2
    saved = [t["after_value"]["operation_receipt"]["outcome"] for r in links for t in r["matching_targets"] if t.get("case_id") == case["case_id"]]
    assert sorted(saved, key=lambda r:r["id"]) == sorted([first, second], key=lambda r:r["id"])
    fixture = {"case_id": case["case_id"], "other_case_id": other["case_id"], "attachments": [first, second],
        "task": task, "run": run, "case_before": before, "case_after": after}
    save(out / "fixture.json", fixture)
    result = {"passed": True, "mode": "new_synthetic_case_and_reference_only", "database_expected": cfg["database"],
        "http_requests": len(receipts), "case_id": case["case_id"], "attachments": 2, "models": 0,
        "task_run_and_case_semantics_unchanged": True, "sql_verification": "separate_snapshot_required",
        "backend_file_upload_download_verified": False}
    save(out / "verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
