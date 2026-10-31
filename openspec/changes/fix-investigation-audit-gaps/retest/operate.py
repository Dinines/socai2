"""Execute only the five frozen r3 requests via the existing HTTP client.

Host21 only; --execute requires the user's recorded temporary-key authorization.
No POST retries, Case creation, overview refresh, or changes to existing keys.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parent
RELEASE = ROOT.parent
BATCH = "INVHTTP-20261031-r3-retest-01"
PRIVATE = Path("/opt/sting-aisoc-socai2/private") / (BATCH + "-tokens.json")
OUTPUT = ROOT / "results"
SCOPES = ["alerts:read", "cases:read", "investigation:run"]
TENANTS = {"f6a5c700-69b8-44fc-8238-609362fb1a9f", "53824f24-d1d4-5820-8147-f6cfda8a1247"}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pg(sql):
    c = json.loads(subprocess.check_output(["docker", "inspect", "spirithub-postgres-1"]))[0]
    env = dict(item.split("=", 1) for item in c["Config"]["Env"])
    r = subprocess.run(["docker", "exec", "-i", "spirithub-postgres-1", "psql", "-X", "-q", "-A", "-t",
                        "-v", "ON_ERROR_STOP=1", "-U", env["POSTGRES_USER"], "-d", "aisoc"],
                       input=sql, text=True, capture_output=True, timeout=30)
    if r.returncode:
        raise RuntimeError("pg_operation_failed")
    return r.stdout.strip()


def main():
    plan = json.loads((ROOT / "plan.json").read_text(encoding="utf-8"))
    steps = plan["steps"]
    assert len(steps) == 5 and {s["tenant_id"] for s in steps} == TENANTS
    for step in steps:
        UUID(step["planned_run_id"])
        assert hashlib.sha256((ROOT / step["body_file"]).read_bytes()).hexdigest() == step["body_sha256"]
    resume = sys.argv[1:] == ["--resume-preflight"]
    if sys.argv[1:] != ["--execute"] and not resume:
        print(json.dumps({"planned_runs": len(steps), "key_scopes": SCOPES, "key_ttl_minutes": 30, "executed": False}))
        return 0
    os.umask(0o077)
    assert not PRIVATE.exists() and not OUTPUT.exists(), "batch_already_started"
    OUTPUT.mkdir()
    records, keys = [], {}
    expires = (datetime.now(UTC) + timedelta(minutes=30)).isoformat()
    for tenant in sorted(TENANTS):
        keys[tenant] = "aisoc_" + secrets.token_hex(24)
        records.append({"id": str(uuid4()), "tenant_id": tenant, "name": BATCH,
                        "scopes": SCOPES, "expires_at": expires})
    if resume:
        prior = ROOT / "preflight-failure-01"
        previous = json.loads((prior / "summary.json").read_text())
        old_keys = json.loads((prior / "credential-receipt.json").read_text())
        assert not previous["runs"] and all(h["method"] == "GET" for h in previous["http"])
        assert old_keys["private_token_file_removed"] and len(old_keys["revoked"]) == 2
        assert all(not row["active"] for row in old_keys["revoked"])
        records = old_keys["keys"]  # Reuse only our two authorized identities; rotate secrets, keep original expiry.
        assert len(records) == 2 and {r["tenant_id"] for r in records} == TENANTS
        for record in records:
            UUID(record["id"])
            assert record["name"] == BATCH and record["scopes"] == SCOPES
            assert datetime.fromisoformat(record["expires_at"]) > datetime.now(UTC) + timedelta(minutes=12)
    credential = {"batch": BATCH, "keys": records, "created": False, "roles_or_users_changed": False,
                  "existing_keys_changed": False, "raw_keys_logged": False,
                  "rotated_same_owned_batch_keys_after_zero_run_preflight": resume}
    state = {"batch": BATCH, "started_at": datetime.now(UTC).isoformat(), "http": [], "runs": [], "skipped": [], "errors": []}
    serial = 0

    def request(step, method, path, label, body_file=None, require_ok=True):
        nonlocal serial
        assert path.startswith(("/api/v2/investigation/", "/api/v1/")) and "://" not in path
        serial += 1
        prefix = OUTPUT / f"{serial:03d}-{label}"
        meta = {"method": method, "path": path, "tenant_id": step["tenant_id"],
                "started_at": datetime.now(UTC).isoformat(), "attempt": 1, "authentication": "real_api_key"}
        command = [sys.executable, "-B", str(RELEASE / "scripts/investigation_client.py"), method, path, "--timeout", "150"]
        if body_file is not None:
            body = json.loads(body_file.read_text(encoding="utf-8"))
            wire = json.dumps(body, ensure_ascii=False).encode()
            prefix.with_suffix(".body.json").write_bytes(wire)
            meta["body_sha256"] = hashlib.sha256(wire).hexdigest()
            command += ["--body", str(body_file)]
        save(prefix.with_suffix(".request.json"), meta)  # Leave an attempt before dispatch; never retry it.
        r = subprocess.run(command, env={**os.environ, "AISOC_API_TOKEN": keys[step["tenant_id"]]},
                           capture_output=True, timeout=160)
        prefix.with_suffix(".response.txt").write_bytes(r.stdout)
        status = re.search(rb"HTTP (\d+)", r.stderr)
        meta.update(completed_at=datetime.now(UTC).isoformat(), exit_code=r.returncode,
                    status=int(status.group(1)) if status else None, response_sha256=hashlib.sha256(r.stdout).hexdigest(),
                    response_bytes=len(r.stdout), response_file=prefix.name + ".response.txt")
        save(prefix.with_suffix(".request.json"), meta)
        state["http"].append(meta)
        save(OUTPUT / "summary.json", state)
        if require_ok and r.returncode:
            raise RuntimeError(f"{label}:http_{meta['status']}_or_transport_error")
        try:
            parsed = json.loads(r.stdout)
        except (ValueError, UnicodeDecodeError):
            parsed = None
        return parsed, r.stdout, meta["status"]

    ids = ",".join("'" + item["id"] + "'" for item in records)
    reports, outcomes = {}, {}
    save(OUTPUT / "credential-receipt.json", credential)
    try:
        # Public preflight and execution use the actual authentication dependency.
        with PRIVATE.open("x", encoding="utf-8") as stream:
            json.dump(keys, stream)
        PRIVATE.chmod(0o600)
        statements = []
        for item in records:
            raw = keys[item["tenant_id"]]
            if resume:
                statements.append(f"UPDATE api_keys SET key_prefix='{raw[:12]}',hashed_key='{hashlib.sha256(raw.encode()).hexdigest()}',is_active=true "
                    f"WHERE id='{item['id']}' AND tenant_id='{item['tenant_id']}' AND name='{BATCH}' AND NOT is_active "
                    f"AND expires_at='{item['expires_at']}' RETURNING id;")
                continue
            statements.append("INSERT INTO api_keys(id,tenant_id,user_id,name,key_prefix,hashed_key,scopes,is_active,expires_at,created_at) "
                f"VALUES ('{item['id']}','{item['tenant_id']}',NULL,'{BATCH}','{raw[:12]}',"
                f"'{hashlib.sha256(raw.encode()).hexdigest()}','{json.dumps(SCOPES)}'::jsonb,true,'{expires}',now());")
        activated = pg("BEGIN;" + "".join(statements) + "COMMIT;")
        if resume:
            assert set(activated.splitlines()) == {r["id"] for r in records}
        credential["created"] = not resume
        credential["activated"] = True
        save(OUTPUT / "credential-receipt.json", credential)
        planned_ids = ",".join("'" + s["planned_run_id"] + "'" for s in steps)
        assert pg(f"BEGIN READ ONLY; SELECT count(*) FROM investigation_runs WHERE id IN ({planned_ids}); COMMIT;") == "0"
        for step in [s for s in steps if s["stage"] == "main"]:
            body = json.loads((ROOT / step["body_file"]).read_text(encoding="utf-8"))
            case_id = step["path"].split("/")[5]
            case, _, _ = request(step, "GET", f"/api/v1/cases/{case_id}", step["case"] + "-case-before")
            assert set(body["selected_member_ids"]).issubset(case["alert_ids"])
            for index, alert_id in enumerate(body["selected_member_ids"]):
                UUID(alert_id)
                request(step, "GET", f"/api/v1/alerts/{alert_id}", step["case"] + f"-source-{index}")
            alert_ids = ",".join("'" + a + "'" for a in body["selected_member_ids"])
            assert pg(f"BEGIN READ ONLY; SELECT count(*) FROM alerts WHERE tenant_id='{step['tenant_id']}' "
                      f"AND id IN ({alert_ids}) AND connector_id IS NOT NULL; COMMIT;") == "0", "vendor_source_outside_plan"
        for step in steps:
            name = step["case"] + "-" + step["stage"]
            if step["stage"] == "followup":
                previous = outcomes.get(step["case"])
                reusable = previous and any(e.get("kind") == "tool" and e.get("tool") == "network_connections" and e.get("available")
                                           for e in previous["result"]["evidence"])
                if not previous or previous["status"] != "completed" or (step["case"] == "network-positive-reuse" and not reusable):
                    state["skipped"].append({"step": name, "reason": "main_prerequisite_not_satisfied"})
                    continue
            print(json.dumps({"starting": name, "planned_run_id": step["planned_run_id"]}), flush=True)
            outcome, _, _ = request(step, "POST", step["path"], name, ROOT / step["body_file"], require_ok=False)
            reread, _, _ = request(step, "GET", step["readback_path"], name + "-result")
            assert reread["run_id"] == step["planned_run_id"]
            if outcome and "result" in outcome:
                assert reread["result"] == outcome["result"], "saved_result_differs"
            outcome = reread
            assert outcome["result"] is not None and outcome["status"] != "running", "run_not_stopped_no_retry"
            result = outcome["result"]
            _, report, _ = request(step, "GET", outcome["report_url"], name + "-report")
            listing, _, _ = request(step, "GET", outcome["steps_url"] + "?limit=50", name + "-steps")
            assert listing["next_after_seq"] is None, "unexpected_step_count"
            for item in listing["items"]:
                request(step, "GET", item["detail_url"], name + f"-step-{item['seq']}")
            request(step, "GET", outcome["evidence_url"], name + "-evidence-list")
            for evidence in result["evidence"]:
                request(step, "GET", outcome["evidence_url"] + "/" + evidence["evidence_id"], name + "-evidence-" + evidence["evidence_id"])
            if step["stage"] == "followup":
                history = next(e for e in result["evidence"] if e["kind"] == "prior_analysis")
                assert history["data"]["report"] == outcomes[step["case"]]["result"]["report"]
                _, original, _ = request(step, "GET", outcomes[step["case"]]["report_url"], name + "-original-report")
                assert original == reports[step["case"]], "original_report_changed"
            else:
                outcomes[step["case"]], reports[step["case"]] = outcome, report
            state["runs"].append({"step": name, "run_id": outcome["run_id"], "status": outcome["status"],
                "stop_reason": result["stop_reason"], "completion": result["completion"], "usage": result["usage"],
                "tools": [{k: e.get(k) for k in ("evidence_id", "tool", "available", "returned_count", "reused_from", "query_contract")}
                          for e in result["evidence"] if e["kind"] == "tool"]})
            save(OUTPUT / "summary.json", state)
            print(json.dumps(state["runs"][-1]), flush=True)
    except Exception as exc:
        state["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    finally:
        try:
            credential["revoked"] = json.loads(pg(f"UPDATE api_keys SET is_active=false WHERE id IN ({ids}) AND name='{BATCH}'; "
                f"SELECT COALESCE(json_agg(json_build_object('id',id,'active',is_active)),'[]'::json) FROM api_keys WHERE id IN ({ids});"))
            credential["revocation_http"] = []
            for tenant in sorted(TENANTS):
                step = next(s for s in steps if s["tenant_id"] == tenant)
                _, _, status = request(step, "GET", step["path"].rsplit("/", 1)[0] + "/investigations?limit=1",
                                       "revoked-" + tenant[:8], require_ok=False)
                credential["revocation_http"].append({"tenant_id": tenant, "status": status})
            assert all(not x["active"] for x in credential["revoked"])
            assert all(x["status"] == 401 for x in credential["revocation_http"])
        except Exception as exc:
            state["errors"].append({"cleanup": type(exc).__name__, "message": str(exc)})
        finally:
            if PRIVATE.exists():
                PRIVATE.unlink()
            credential["private_token_file_removed"] = not PRIVATE.exists()
            state["finished_at"] = datetime.now(UTC).isoformat()
            save(OUTPUT / "credential-receipt.json", credential)
            save(OUTPUT / "summary.json", state)
    print(json.dumps({"finished": True, "runs": len(state["runs"]), "skipped": state["skipped"],
                      "errors": state["errors"], "private_token_file_removed": credential["private_token_file_removed"]}), flush=True)
    return int(bool(state["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
