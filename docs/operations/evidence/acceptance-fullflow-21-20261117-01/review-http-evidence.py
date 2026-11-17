"""Independent offline checks of saved 21 HTTP responses and PostgreSQL snapshots."""
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
import socket
from urllib.parse import parse_qs, urlsplit

from jsonschema import Draft202012Validator, FormatChecker


BATCH = Path(__file__).resolve().parent
ROOT = BATCH.parents[3]
PREPARED = BATCH / "results/prepared"
CONTRACT = ROOT / "deploy/aisoc21/acceptance-release-20261117-01/contract/openapi.json"
OUTPUT = BATCH / "independent-http-review.json"
INPUT_HASHES = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(path):
    data = path.read_bytes()
    INPUT_HASHES[str(path.relative_to(ROOT))] = sha(data)
    return data


def load(path):
    return json.loads(raw(path))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def same_field(actual, expected):
    if isinstance(actual, str) and isinstance(expected, str):
        if re.fullmatch(r"\d{4}-\d\d-\d\dT[0-9:.]+(?:Z|[+-]\d\d:\d\d)", actual) and re.fullmatch(
                r"\d{4}-\d\d-\d\dT[0-9:.]+(?:Z|[+-]\d\d:\d\d)", expected):
            return datetime.fromisoformat(actual.replace("Z", "+00:00")) == datetime.fromisoformat(expected.replace("Z", "+00:00"))
    return actual == expected


def shared_fields(dto, row, label):
    for key in dto.keys() & row.keys():
        assert same_field(dto[key], row[key]), (label, row.get("id"), key)


def subject(run):
    for kind in ("alert", "incident", "case"):
        if run.get(kind + "_id"):
            return kind, run[kind + "_id"]
    raise AssertionError("Run has no subject")


def main():
    if OUTPUT.exists():
        raise SystemExit("Existing review must be preserved; use a new output for another review.")
    def forbidden(*args, **kwargs):
        raise RuntimeError("network_forbidden_in_offline_http_review")
    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.create_connection = forbidden
    report = {
        "status": "running", "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "saved_21_two_part_HTTP_contract_identity_originals_and_scope",
        "review_script_sha256": sha(Path(__file__).read_bytes()), "checks": [],
        "new_http_requests": 0, "new_database_requests": 0, "new_model_calls": 0,
        "source_service_or_package_changes": False,
        "initial_review": "independent-http-review-initial.json",
        "review_driver_correction": "Case Run exposes input_member_count and current_member_count; Result exposes member_count. The initial reviewer incorrectly used Result's count field for both response types. Original failed review preserved unchanged.",
        "limitations": [
            "Independent offline review of captured TCP responses and PG snapshots; no new service or database request.",
            "Only operations exercised in this two-part batch are business-validated, not every operation in the 80-operation API.",
            "Model prose quality and accuracy are not assessed or declared passed.",
            "No claim for natural 4h/6h scheduling, D5/D6 abnormal paths, 4b automatic viewer linking or browser behavior.",
        ],
    }
    def check(name, **details):
        report["checks"].append({"name": name, "status": "passed", **details})

    try:
        api = load(CONTRACT)
        session = load(PREPARED / "session.json")
        tenant = session["profile"]["tenant_id"]
        snapshots = {part: load(PREPARED / "runs" / part / "saved-records.json") for part in ("part1", "part2")}
        states = {part: load(PREPARED / "runs" / part / "state.json") for part in snapshots}
        tables = {part: {name: {row["id"]: row for row in rows}
                         for name, rows in data.items() if isinstance(rows, list) and all("id" in r for r in rows)}
                  for part, data in snapshots.items()}
        assert all(state["status"] == "completed" for state in states.values())
        assert {row["tenant_id"] for data in snapshots.values() for rows in data.values()
                if isinstance(rows, list) for row in rows} == {tenant}
        data = snapshots["part2"]
        db = tables["part2"]
        assert (len(data["alerts"]), len(data["incidents"]), len(data["cases"]), len(data["runs"]), len(data["results"])) == (2, 1, 1, 6, 2)
        case_id, incident_id = data["cases"][0]["id"], data["incidents"][0]["id"]
        case_runs = sorted((r for r in data["runs"] if r["case_id"]), key=lambda r: (r["started_at"], r["id"]))
        result_by_run = {r["source_run_id"]: r for r in data["results"]}
        attempt_by_run = {a["run_id"]: a for a in data["analysis_attempts"] if a["run_id"]}
        assert len(attempt_by_run) == len(db["runs"]) == 6
        assert all(r["state"] == "completed" for r in data["runs"])
        assert all(a["local_state"] == "ended" and a["outcome"] == "completed" for a in data["analysis_attempts"])
        for a in data["analysis_attempts"]:
            task, run = db["analysis_tasks"][a["task_id"]], db["runs"][a["run_id"]]
            assert (a["subject_type"], a["subject_id"]) == subject(run) == (task["subject_type"], task["subject_id"])
        check("saved_subject_task_attempt_run_and_backend_tenant_identity", tenant_id=tenant,
              alerts=2, incidents=1, cases=1, tasks=7, attempts=6, runs=6, results=2)

        route_patterns = [(re.compile("^" + re.sub(r"\\\{[^}]+\\\}", r"[^/]+", re.escape(path)) + "$"), path)
                          for path in api["paths"]]
        validators = {}
        def validate(schema, body, label):
            key = sha(canonical(schema))
            if key not in validators:
                validators[key] = Draft202012Validator({**schema, "components": api["components"]}, format_checker=FormatChecker())
            errors = list(validators[key].iter_errors(body))
            assert not errors, (label, str(errors[0].json_path) if errors else None, errors[0].validator if errors else None)

        receipts = defaultdict(list)
        for part in snapshots:
            folder = PREPARED / "runs" / part / "http"
            for path in sorted(folder.glob("*.json")):
                if path.name.endswith(".intent.json"):
                    continue
                r = load(path)
                body_path = folder / r["response"]["body_file"]
                assert body_path.parent == folder
                body = raw(body_path)
                assert sha(body) == r["response"]["sha256"] and json.loads(body) == r["response"]["body"]
                assert r["outcome"] == "returned"
                url = urlsplit(r["request"]["path"])
                matches = [template for regex, template in route_patterns if regex.fullmatch(url.path)]
                assert len(matches) == 1, ("route", url.path, matches)
                method, code = r["request"]["method"].lower(), str(r["response"]["status"])
                operation = api["paths"][matches[0]][method]
                assert not operation.get("security")
                validate(operation["responses"][code]["content"]["application/json"]["schema"], r["response"]["body"], path.name)
                if method == "post":
                    validate(operation["requestBody"]["content"]["application/json"]["schema"], r["request"]["body"], "request:" + path.name)
                    intent = load(path.with_name(path.stem + ".intent.json"))
                    assert intent["request"] == r["request"]
                r["evidence_path"] = str(path.relative_to(BATCH))
                receipts[part].append(r)
        counts = Counter((r["request"]["method"], r["response"]["status"]) for values in receipts.values() for r in values)
        assert counts == Counter({("GET", 200): 473, ("POST", 201): 1, ("POST", 202): 3})
        check("raw_HTTP_body_sha_and_deployed_OpenAPI_contract", responses=477, requests=4,
              counts=[{"method": m, "status": s, "count": n} for (m, s), n in sorted(counts.items())],
              authentication_in_contract=False)

        submissions = []
        for part, values in receipts.items():
            for r in values:
                if r["request"]["method"] != "POST":
                    continue
                request, response = r["request"]["body"], r["response"]["body"]
                if r["response"]["status"] == 201:
                    assert part == "part1" and request["incident_ids"] == [incident_id]
                    assert response["operation_key"] == request["operation_key"]
                    assert response["primary_case_id"] == response["receiving_case_id"] == case_id
                    assert len(response["allocations"]) == 1
                    allocation = response["allocations"][0]
                    assert allocation["created"] and allocation["case_id"] == case_id
                    assert set(allocation["added_alert_ids"]) == set(tables["part1"]["alerts"])
                    assert allocation["linked_incident_ids"] == [incident_id]
                    receipt = allocation["initial_task"]
                    task = db["analysis_tasks"][receipt["task_id"]]
                    assert task["intent"] == "initial" and task["source"] == "case_create"
                else:
                    receipt = response
                    task = db["analysis_tasks"][receipt["task_id"]]
                    assert request["mode"] == task["intent"] == "check"
                    assert request["operation_key"] == task["operation_key"]
                assert receipt["status"] == "accepted"
                assert (receipt["subject_type"], receipt["subject_id"]) == (task["subject_type"], task["subject_id"])
                assert receipt["status_url"] == f'/api/v1/socai2/{task["subject_type"]}s/{task["subject_id"]}/analysis-tasks/{task["id"]}'
                submissions.append({"part": part, "http_status": r["response"]["status"], "task_id": task["id"],
                                    "terminal_state": task["state"], "reason_code": task["reason_code"], "evidence": r["evidence_path"]})
        assert len({r["task_id"] for r in submissions}) == 4
        check("actual_creation_and_check_submission_identity", submissions=submissions)

        artifact_reads, step_reads, pagination = {}, {}, []
        all_task_details = {}
        for part, values in receipts.items():
            local = tables[part]
            details = {r["request"]["path"]: r["response"]["body"] for r in values if r["request"]["method"] == "GET"}
            pages = defaultdict(dict)
            part_artifacts = set()
            for r in values:
                if r["request"]["method"] != "GET":
                    continue
                url = urlsplit(r["request"]["path"])
                b = r["response"]["body"]
                if "availability" in b and ("artifact" in b or "metadata" in b):
                    meta = b.get("artifact", b.get("metadata"))
                    saved = local["artifacts"][meta["id"]]
                    shared_fields(meta, saved, "artifact_metadata")
                    assert b["availability"] == "available"
                    assert b["content_json"] == saved["content_json"] and b["content_text"] == saved["content_text"]
                    original = canonical(b["content_json"]) if b["content_json"] is not None else b["content_text"].encode()
                    assert sha(original) == saved["sha256"] and len(original) == saved["size_bytes"]
                    assert saved["run_id"] in url.path and saved["id"] in url.path
                    kind, sid = subject(local["runs"][saved["run_id"]])
                    assert f"/{kind}s/{sid}/" in url.path
                    part_artifacts.add(saved["id"])
                    artifact_reads[saved["id"]] = r["evidence_path"]
                if "task_id" in b and "attempts" in b:
                    all_task_details[b["task_id"]] = b
                match = re.fullmatch(r"/api/v1/socai2/analysis-runs/([^/]+)/(steps|artifacts)", url.path)
                if match:
                    run_id, kind = match.groups()
                    query = parse_qs(url.query)
                    assert set(query) <= {"limit", "cursor"}
                    cursor = query.get("cursor", [None])[0]
                    assert cursor not in pages[(run_id, kind)], (part, run_id, kind, "duplicate page")
                    pages[(run_id, kind)][cursor] = b
            assert part_artifacts == set(local["artifacts"]), (part, "missing artifact content")
            for (run_id, kind), chain in pages.items():
                cursor, seen, ids = None, set(), []
                while True:
                    assert cursor in chain and cursor not in seen
                    seen.add(cursor)
                    page = chain[cursor]
                    assert page["run_id"] == run_id
                    assert (page["subject_type"], page["subject_id"]) == subject(local["runs"][run_id])
                    for item in page["items"]:
                        table = "run_steps" if kind == "steps" else "artifacts"
                        row = local[table][item["id"]]
                        shared_fields(item, row, kind)
                        assert row["run_id"] == run_id
                        ids.append(item["id"])
                        if kind == "artifacts":
                            assert item["content_url"] in details
                            original = details[item["content_url"]]
                            assert original.get("artifact", original.get("metadata"))["id"] == item["id"]
                        else:
                            step_reads[item["id"]] = part
                    cursor = page["next_cursor"]
                    if cursor is None:
                        break
                expected = {row["id"] for row in local["run_steps" if kind == "steps" else "artifacts"].values() if row["run_id"] == run_id}
                assert len(ids) == len(set(ids)) and set(ids) == expected and len(seen) == len(chain)
                assert all(page["total"] == len(expected) for page in chain.values())
                pagination.append({"part": part, "run_id": run_id, "kind": kind, "pages": len(chain), "items": len(ids)})
            assert set(pages) == {(run_id, kind) for run_id in local["runs"] for kind in ("steps", "artifacts")}
        assert len(artifact_reads) == 142 and len(step_reads) == 48
        check("all_original_content_metadata_hash_and_size_match_PG", unique_artifacts=142,
              readbacks_including_repeated_first_round=213, availability="available", unique_steps=48)
        check("complete_step_artifact_pagination_and_content_links", directory_chains=pagination)

        assert set(all_task_details) == set(db["analysis_tasks"])
        for tid, b in all_task_details.items():
            t = db["analysis_tasks"][tid]
            shared_fields(b, t, "task")
            assert b["status"] == t["state"] and b["reason_code"] == t["reason_code"]
            attempts = sorted((a for a in data["analysis_attempts"] if a["task_id"] == tid), key=lambda a: a["attempt_no"])
            assert len(b["attempts"]) == len(attempts)
            for item, a in zip(b["attempts"], attempts):
                shared_fields(item, a, "attempt")
                assert item["run_url"].endswith("/runs/" + a["run_id"])
            assert b["latest_run_id"] == (attempts[-1]["run_id"] if attempts else None)
            run_ids = {a["run_id"] for a in attempts}
            expected = {row["id"] for table in ("alert_assessments", "incident_diagnoses", "results")
                        for row in data[table] if row["source_run_id"] in run_ids}
            assert {x["id"] for x in b["results"]} == expected
            assert all(x["source_run_id"] in run_ids for x in b["results"])
            if t["state"] == "skipped":
                assert t["reason_code"] == "no_changes" and not attempts and not b["results"]
        check("final_task_attempt_result_links_and_no_changes", terminal_tasks=7, completed=6,
              skipped_without_attempt_run_result=1)

        ai_runs, run_directories = set(), 0
        for part, values in receipts.items():
            local = tables[part]
            for r in values:
                url = urlsplit(r["request"]["path"])
                b = r["response"]["body"]
                match = re.fullmatch(r"/api/v1/socai2/(alerts|incidents)/([^/]+)/analysis/runs/([^/]+)", url.path)
                if match:
                    plural, sid, rid = match.groups()
                    run = local["runs"][rid]
                    assert subject(run) == (plural[:-1], sid)
                    shared_fields(b["run"], run, "AI_run")
                    table = "alert_assessments" if plural == "alerts" else "incident_diagnoses"
                    result = local[table][b["result"]["id"]]
                    shared_fields(b["result"], result, "AI_result")
                    assert result["source_run_id"] == rid and result[plural[:-1] + "_id"] == sid
                    if plural == "incidents":
                        selected = local["artifacts"][run["input_artifact_id"]]["content_json"]["input_selection"]
                        shared_fields(b["input_selection"], selected, "I_selection")
                    ai_runs.add(rid)
                if url.path == "/api/v1/socai2/analysis-runs":
                    query = parse_qs(url.query)
                    selected_subject = (query["subject_type"][0], query["subject_id"][0])
                    expected = {rid for rid, row in local["runs"].items() if subject(row) == selected_subject}
                    assert {x["run_id"] for x in b["items"]} == expected
                    assert b["total"] == len(expected) and b["next_cursor"] is None
                    for item in b["items"]:
                        assert (item["subject_type"], item["subject_id"]) == selected_subject
                        assert item["task_id"] == attempt_by_run[item["run_id"]]["task_id"]
                        shared_fields(item, local["runs"][item["run_id"]], "run_directory")
                    run_directories += 1
        assert ai_runs == {r["id"] for r in data["runs"] if not r["case_id"]}
        check("AI_result_fields_frozen_selection_and_subject_Run_directory", AI_runs=len(ai_runs), directory_responses=run_directories)

        scopes, comparisons, frozen_sources = {}, {}, []
        for index, run in enumerate(case_runs):
            rid = run["id"]
            result = result_by_run[rid]
            c1 = next(a["content_json"] for a in data["artifacts"]
                      if a["run_id"] == rid and a["schema_version"] == "socai2.baseline-context.v1")
            manifest = db["artifacts"][run["input_artifact_id"]]["content_json"]
            expected_scope = set(tables["part1" if index == 0 else "part2"]["alerts"])
            assert set(c1["alerts"]) == set(c1["scope"]["alert_ids"]) == expected_scope
            assert {r["alert_id"] for r in data["run_members"] if r["run_id"] == rid} == expected_scope
            assert c1["case_id"] == case_id and c1["case"]["tenant_id"] == tenant
            assert set(c1["incidents"]) == {incident_id}
            scopes[rid] = sorted(expected_scope)
            comparison = {"previous_run_id": None, "comparison_result_id": None, "state": "initial", "reason_code": None} if index == 0 else {
                "previous_run_id": case_runs[0]["id"], "comparison_result_id": result_by_run[case_runs[0]["id"]]["id"], "state": "eligible", "reason_code": None}
            assert c1["update_context"]["comparison_context"] == manifest["comparison_context"] == comparison
            assert run["comparison_result_id"] == result["comparison_result_id"] == comparison["comparison_result_id"]
            attempt = attempt_by_run[rid]
            assert attempt["previous_run_id"] == comparison["previous_run_id"] and attempt["comparison_result_id"] == comparison["comparison_result_id"]
            comparisons[rid] = comparison
            source = c1["incidents"][incident_id]["analysis_material"]
            assert source["tenant_id"] == tenant and source["incident_id"] == incident_id
            assert db["runs"][source["source_run_id"]]["incident_id"] == incident_id
            assert db["analysis_attempts"][source["attempt_id"]]["run_id"] == source["source_run_id"]
            assert db["analysis_attempts"][source["attempt_id"]]["task_id"] == source["task_id"]
            assert source["input_selection"] == db["artifacts"][source["input"]["id"]]["content_json"]["input_selection"]
            assert set(source["case_selected_alert_ids"]) == set(source["input_selection"]["selected_alert_ids"]) & expected_scope
            assert source["receipt"] == db["artifacts"][source["receipt_source"]["id"]]["content_json"]
            for identity in [source["input"], source["response"], source["receipt_source"], *source["originals"]]:
                original = db["artifacts"][identity["id"]]
                assert original["run_id"] == source["source_run_id"] and original["incident_id"] == incident_id
                shared_fields(identity, original, "frozen_I_original")
            for aid, item in c1["alerts"].items():
                triage = db["alert_assessments"][item["triage"]["id"]]
                material = db["alert_materials"][item["material"]["id"]]
                assert triage["alert_id"] == material["alert_id"] == aid
                assert triage["source_run_id"] == item["triage"]["source_run_id"]
                assert triage["input_material_id"] == material["id"]
                assert item["alert"]["tenant_id"] == tenant
            frozen_sources.append({"case_run_id": rid, "incident_run_id": source["source_run_id"],
                                   "selected_count": source["input_selection"]["selected_count"],
                                   "case_alert_ids": sorted(expected_scope)})
        assert [len(scopes[r["id"]]) for r in case_runs] == [1, 2]
        assert frozen_sources[0]["incident_run_id"] != frozen_sources[1]["incident_run_id"]
        check("two_round_frozen_scope_and_AI_source_identity", case_id=case_id, sources=frozen_sources)

        case_result_gets, case_run_gets = set(), set()
        for part, values in receipts.items():
            for r in values:
                path = urlsplit(r["request"]["path"]).path
                b = r["response"]["body"]
                if r["request"]["method"] != "GET" or not path.startswith(f"/api/v1/socai2/cases/{case_id}/"):
                    continue
                if re.fullmatch(r".*/(?:runs|results)/[^/]+", path):
                    run = db["runs"][b["run"]["id"]]
                    rid = run["id"]
                    shared_fields(b["run"], run, "case_run")
                    assert b["run"]["comparison_context"] == comparisons[rid]
                    previous = comparisons[rid]["previous_run_id"]
                    prior_result = comparisons[rid]["comparison_result_id"]
                    assert b["previous_run_url"] == (f"/api/v1/socai2/cases/{case_id}/runs/{previous}" if previous else None)
                    assert b["comparison_result_url"] == (f"/api/v1/socai2/cases/{case_id}/results/{prior_result}" if prior_result else None)
                    assert {m["alert_id"] for m in b["members"]} == set(scopes[rid])
                    count_field = "member_count" if "result" in b else "input_member_count"
                    assert b[count_field] == len(scopes[rid]) and not b["members_truncated"]
                    if "current_member_count" in b:
                        assert b["current_member_count"] == len(snapshots[part]["case_alerts"])
                    case_run_gets.add(rid)
                    if "result" in b:
                        result = result_by_run[rid]
                        shared_fields(b["result"], result, "case_result")
                        assert b["result"]["comparison_context"] == comparisons[rid]
                        assert b["result"]["source_run_id"] == rid
                        case_result_gets.add(result["id"])
        assert case_run_gets == set(comparisons) and case_result_gets == set(db["results"])
        check("Case_Run_Result_HTTP_fields_members_and_previous_urls", comparisons=comparisons,
              result_ids=sorted(case_result_gets), result_states=[{k: r[k] for k in ("id", "source_run_id", "validation_state", "conclusion_state", "delivery_state")} for r in data["results"]])

        preserved = {}
        immutable_tables = ["alert_materials", "alert_assessments", "alert_source_refs", "analysis_tasks", "analysis_attempts",
                            "artifacts", "results", "run_members", "run_steps", "runs", "incident_diagnoses"]
        for table in immutable_tables:
            for row in snapshots["part1"][table]:
                assert db[table][row["id"]] == row, ("old record changed", table, row["id"])
            preserved[table] = len(snapshots["part1"][table])
        for entry in states["part2"]["previous_receipts"]:
            assert sha(raw(PREPARED / entry["path"])) == entry["sha256"]
        check("first_round_saved_rows_and_previous_files_unchanged", rows_by_table=preserved,
              previous_files=len(states["part2"]["previous_receipts"]))

        c6 = []
        for step in data["run_steps"]:
            if step["kind"] != "model" or step["stage_code"] != "C6":
                continue
            original = db["artifacts"][step["output_artifact_id"]]
            response = original["content_json"]["payload"]["raw"]
            body = json.loads(response["choices"][0]["message"]["content"])
            result = result_by_run[step["run_id"]]
            assert body["conclusion"]["text"] == result["conclusion"]
            assert original["id"] in artifact_reads
            c6.append({"run_id": step["run_id"], "result_id": result["id"], "artifact_id": original["id"],
                       "finish_reason": response["choices"][0]["finish_reason"], "conclusion_preserved": True})
        assert len(c6) == 2
        check("C6_original_conclusion_preserved_in_saved_and_HTTP_result", runs=c6, model_quality="not_assessed")
        report["status"] = "passed_for_saved_HTTP_contract_and_readback"
    except Exception as exc:
        report["status"] = "failed"
        report["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
    finally:
        changed = [name for name, digest in INPUT_HASHES.items() if sha((ROOT / name).read_bytes()) != digest]
        report["evidence_inputs_unchanged"] = not changed
        report["evidence_files"] = INPUT_HASHES
        if changed:
            report["status"] = "failed"
            report["changed_inputs"] = changed
        with OUTPUT.open("x") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]),
                      "evidence_files": len(INPUT_HASHES), "output": str(OUTPUT.relative_to(ROOT))}))
    return 0 if report["status"].startswith("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
