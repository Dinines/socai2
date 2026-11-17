"""Read saved acceptance receipts and derive the next-part gate, without connections."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from acceptance_materials import MaterialError, _safe_file, parse_json, save_report
from acceptance_session import load_execution
from alert_scenarios import sha256

FINISHED = {"completed", "completed_with_issues"}
TASK_END = {"completed", "failed", "skipped", "merged"}
REASONS = {
    "receipt_unreadable": "回执缺失、损坏或路径不可读，请先核对原件",
    "state_binding_mismatch": "段回执与本执行、段或冻结材料不匹配",
    "state_not_closed": "本地记录尚未完成保存和读回",
    "invalid_saved_identity": "保存的主体或执行身份不完整，不能推定实际落库",
    "saved_closure_mismatch": "完成声明与保存快照、读回回执不一致",
    "saved_execution_link_mismatch": "保存的主体、任务、执行尝试、Run或Result关联不一致",
    "analysis_still_open": "保存记录中仍有未结束的分析执行",
    "run_end_unconfirmed": "未知Run缺少已结束的执行尝试，需先核对",
    "send_not_confirmed": "投递回执尚未确认或与本段材料不符，不能重发",
    "http_write_unconfirmed": "HTTP写入意图缺少相同请求的确定回执",
    "part_order_conflict": "后段已有记录，但前段尚未确认完成",
    "undeclared_part_record": "发现未在本执行声明的段目录",
    "receipts_changed_during_read": "读取期间回执发生变化，请重新查看",
}


class ReceiptError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise ReceiptError(code)


def issue(code, path):
    return {"code": code, "reason": REASONS[code], "path": path}


def identities(rows):
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), "invalid_saved_identity")
    values = [r["id"] for r in rows]
    require(all(isinstance(v, str) and str(UUID(v)) == v for v in values)
            and len(values) == len(set(values)), "invalid_saved_identity")
    return values


def projected(rows, fields):
    identities(rows)
    return [{k: row.get(k) for k in fields} for row in rows]


class SavedReceipts:
    def __init__(self, directory):
        self.directory, self.sources = directory, {}

    def read(self, relative):
        try:
            data = _safe_file(self.directory, relative).read_bytes()
            self.sources[relative] = sha256(data)
            return parse_json(data, "saved receipt")
        except (OSError, ValueError):
            raise ReceiptError("receipt_unreadable") from None

    def unchanged(self):
        try:
            return all(sha256(_safe_file(self.directory, p).read_bytes()) == h for p, h in self.sources.items())
        except (OSError, ValueError):
            return False


def inventory(directory):
    root = directory / "runs"
    return sorted(str(p.relative_to(directory)) for p in root.rglob("*")) if root.is_dir() and not root.is_symlink() else []


def saved_analysis(part, data, tenant):
    subjects = {name: sorted(identities(data[name])) for name in ("alerts", "incidents", "cases")}
    for name in (*subjects, "analysis_tasks", "analysis_attempts", "runs", "results"):
        identities(data[name])
        require(all(r.get("tenant_id") == tenant for r in data[name]), "invalid_saved_identity")
    part.update(actual={"source": "saved-records.json", **subjects},
        tasks=projected(data["analysis_tasks"], ("id", "subject_type", "subject_id", "kind", "state", "reason_code")),
        attempts=projected(data["analysis_attempts"], ("id", "task_id", "run_id", "local_state", "outcome")),
        runs=projected(data["runs"], ("id", "alert_id", "incident_id", "case_id", "state", "delivery_state")),
        results=projected(data["results"], ("id", "case_id", "source_run_id", "validation_state", "conclusion_state", "delivery_state")))


def execution_links(data):
    """Only the saved execution graph used by this gate, not a database audit."""
    code = "saved_execution_link_mismatch"
    subjects = {kind: set(identities(data[table])) for kind, table in (
        ("alert", "alerts"), ("incident", "incidents"), ("case", "cases"))}
    tasks = {t["id"]: (t["subject_type"], t["subject_id"]) for t in data["analysis_tasks"]}
    require(all(kind in subjects and identity in subjects[kind] for kind, identity in tasks.values()), code)
    runs = {}
    for run in data["runs"]:
        links = [(kind, run.get(kind + "_id")) for kind in subjects if run.get(kind + "_id") is not None]
        require(len(links) == 1 and links[0][1] in subjects[links[0][0]], code)
        runs[run["id"]] = links[0]
    linked_runs = set()
    for attempt in data["analysis_attempts"]:
        subject = (attempt["subject_type"], attempt["subject_id"])
        require(attempt["task_id"] in tasks and tasks[attempt["task_id"]] == subject, code)
        if attempt["run_id"] is not None:
            require(attempt["run_id"] in runs and runs[attempt["run_id"]] == subject, code)
            linked_runs.add(attempt["run_id"])
    require(linked_runs == set(runs), code)
    for result in data["results"]:
        require(result["case_id"] in subjects["case"] and result["source_run_id"] in runs
                and runs[result["source_run_id"]] == ("case", result["case_id"]), code)


def closed_analysis(state, data, readback):
    steps = state.get("steps", [])
    require(isinstance(steps, list) and all(isinstance(s, dict) for s in steps), "saved_closure_mismatch")
    require(state.get("ended_at") and state.get("stage") == "saved_http_readback"
        and state.get("readback") == readback and readback.get("status") in {"passed", "incomplete_originals"}
        and any(s.get("stage") == "saved_http_readback" and s.get("status") == "passed"
                and s.get("detail") == readback for s in steps), "saved_closure_mismatch")
    for key, table in (("task_ids", "analysis_tasks"), ("run_ids", "runs"), ("result_ids", "results")):
        require(sorted(readback[key]) == sorted(identities(data[table])), "saved_closure_mismatch")
    require(readback["steps"] == len(data["run_steps"]) and readback["artifacts"] == len(data["artifacts"]),
            "saved_closure_mismatch")
    require({r["actual_alert_id"] for r in state["alerts"]} == set(identities(data["alerts"]))
        and set(state["incidents"]) == set(identities(data["incidents"]))
        and {cid for values in state["cases"].values() for cid in values} == set(identities(data["cases"])),
        "saved_closure_mismatch")
    tasks, attempts, runs = data["analysis_tasks"], data["analysis_attempts"], data["runs"]
    require(all(t["state"] in TASK_END and t.get("ended_at") for t in tasks), "analysis_still_open")
    require(all(a["local_state"] in {"ended", "interrupted"}
                and (a.get("local_ended_at") or a.get("interruption_observed_at")) for a in attempts), "analysis_still_open")
    require(all(r["state"] == "unknown" or (r["state"] in {"completed", "failed"} and r.get("ended_at"))
                for r in runs), "analysis_still_open")
    require(all(r["state"] != "unknown" or any(a["run_id"] == r["id"] for a in attempts) for r in runs),
            "run_end_unconfirmed")
    execution_links(data)


def confirmed_effects(reader, prefix, plan, session, state):
    expected = plan["files"]["alerts"] + plan["files"]["context"]
    expected_names = {"send-" + path.replace("/", "-") for path in expected}
    actual_names = {p.name for p in (reader.directory / prefix).glob("send-*")}
    require(actual_names == expected_names and state["sent"] == {
        "alerts": len(plan["files"]["alerts"]), "context": len(plan["files"]["context"])}, "send_not_confirmed")
    for material in expected:
        receipt = reader.read(prefix + "/send-" + material.replace("/", "-"))
        require(receipt.get("schema_version") == "socai2.acceptance-send.v1"
            and receipt.get("material") == material and receipt.get("tenant_id") == session["profile"]["tenant_id"]
            and receipt.get("status") == "accepted_only" and receipt.get("requested") == receipt.get("accepted") == 1
            and receipt.get("not_attempted") == 0 and receipt.get("cleanup_errors") == []
            and len(receipt.get("records", [])) == 1, "send_not_confirmed")
        sent = receipt["records"][0]
        message = sent.get("message", {})
        require(sent.get("material") == material and sent.get("wire_sha256") == session["wire_sha256"][material]
            and sent.get("state") == "accepted_not_processed" and message.get("topic") == receipt.get("topic")
            and all(type(message.get(k)) is int and message[k] >= 0 for k in ("partition", "offset")),
            "send_not_confirmed")
    for path in sorted((reader.directory / prefix / "http").glob("*.intent.json")):
        name = str(path.relative_to(reader.directory))
        intent, returned = reader.read(name), reader.read(name.replace(".intent.json", ".json"))
        require(isinstance(intent.get("request"), dict) and isinstance(returned.get("response"), dict),
                "http_write_unconfirmed")
        require(intent.get("request", {}).get("method") == "POST" and intent.get("request") == returned.get("request")
            and returned.get("outcome") == "returned" and returned.get("response", {}).get("status") in {201, 202},
            "http_write_unconfirmed")


def observe_part(reader, plan, session, session_hash):
    prefix = "runs/" + plan["id"]
    folder = reader.directory / prefix
    part = {"id": plan["id"], "check_level": plan["check_level"], "planned_counts": plan["counts"],
        "recorded_state": "not_started", "closure_verified": False, "issues": [],
        "actual": {"source": "not_observed", "alerts": [], "incidents": [], "cases": []},
        "tasks": [], "attempts": [], "runs": [], "results": [], "quality": "not_evaluated_by_status",
        "record_path": prefix, "execution_directory_exists": folder.exists() or folder.is_symlink()}
    if not part["execution_directory_exists"]:
        return part
    part["recorded_state"] = "unreadable"
    path = prefix + "/state.json"
    try:
        state = reader.read(path)
        require(state.get("schema_version") == "socai2.acceptance-part.v1" and state.get("part") == plan["id"]
            and state.get("execution_id") == session["execution"]["execution_id"]
            and state.get("session_sha256") == session_hash, "state_binding_mismatch")
        require(state.get("status") in FINISHED | {"running", "incomplete"}, "state_binding_mismatch")
        part.update(recorded_state=state["status"], recorded_at=state.get("observed_at"),
            stage=state.get("stage"), ended_at=state.get("ended_at"),
            recorded_sent=state.get("sent"),
            recorded_execution_issue_count=len(state.get("execution_issues", [])), quality="not_fully_evaluated",
            execution_issues=[{k: problem[k] for k in ("reason_code", "status", "task_id", "run_id", "case_id") if k in problem}
                              for problem in state.get("execution_issues", [])])
        if (reader.directory / prefix / "saved-records.json").exists():
            path = prefix + "/saved-records.json"
            data = reader.read(path)
            saved_analysis(part, data, session["profile"]["tenant_id"])
        require(state["status"] in FINISHED, "state_not_closed")
        # A terminal assertion alone never substitutes for the saved closure.
        path = prefix + "/saved-records.json"
        data = reader.read(path)
        saved_analysis(part, data, session["profile"]["tenant_id"])
        path = prefix + "/readback.json"
        readback = reader.read(path)
        closed_analysis(state, data, readback)
        path = prefix
        confirmed_effects(reader, prefix, plan, session, state)
        part.update(closure_verified=True, readback_state=readback["status"])
    except ReceiptError as exc:
        part["issues"].append(issue(str(exc), path))
    except AttributeError:
        # Malformed nested objects must not escape as a traceback or echo their values.
        part["issues"].append(issue("receipt_unreadable", path))
    except (KeyError, TypeError, ValueError, OSError):
        part["issues"].append(issue("invalid_saved_identity", path))
    return part


def load_status_execution(directory):
    try:
        return load_execution(directory)
    except (KeyError, TypeError):
        raise MaterialError("invalid prepared execution") from None


def session_status(directory: Path):
    profile, session = load_status_execution(directory)
    reader = SavedReceipts(directory)
    reader.read("session.json")
    session_hash = reader.sources["session.json"]
    before = inventory(directory)
    parts = [observe_part(reader, p, session, session_hash) for p in session["plan"]["parts"]]
    issues, open_prefix = [], False
    for part in parts:
        if open_prefix and part["execution_directory_exists"]:
            issues.append(issue("part_order_conflict", part["record_path"]))
        open_prefix |= not part["closure_verified"]
    declared = {p["id"] for p in parts}
    run_root = directory / "runs"
    if run_root.is_symlink() or (run_root.exists() and not run_root.is_dir()):
        issues.append(issue("receipt_unreadable", "runs"))
    elif run_root.is_dir():
        for child in run_root.iterdir():
            if child.name not in declared:
                issues.append(issue("undeclared_part_record", "runs"))
    if not reader.unchanged() or before != inventory(directory):
        issues.append(issue("receipts_changed_during_read", "runs"))
    issues += [problem for part in parts for problem in part["issues"]]
    candidate, action = None, None
    selection_required = False
    if issues:
        recorded_running = (all(p["code"] == "state_not_closed" for p in issues)
                            and any(p["recorded_state"] == "running" for p in parts))
        state = "recorded_in_progress" if recorded_running else "needs_review"
    elif all(p["closure_verified"] for p in parts):
        state = "all_parts_completed"
    elif not any(p["execution_directory_exists"] for p in parts):
        selection_required = session["plan"]["selected_part"] != parts[0]["id"]
        state = "selection_required" if selection_required else "ready"
        candidate, action = (None, None) if selection_required else (parts[0]["id"], "run_first_part")
    else:
        state = "waiting_append"
        candidate, action = next(p["id"] for p in parts if not p["execution_directory_exists"]), "append_part"
    return {"schema_version": "socai2.acceptance-session-status.v1", "execution_id": session["execution"]["execution_id"],
        "observed_at": datetime.now(timezone.utc).isoformat(), "provenance": "saved_local_receipts",
        "environment": {"profile_id": profile.profile_id, "label": profile.environment_label, "tenant_id": profile.tenant_id,
                        "connections_checked": False}, "state": state, "parts": parts,
        "next_part": candidate, "next_action": action, "selection_required": selection_required,
        "first_part": parts[0]["id"], "blocking_issues": issues,
        "append_execution_implemented": True, "live_state_verified": False,
        "sources": [{"path": p, "sha256": h} for p, h in sorted(reader.sources.items())],
        "this_command": {"business_connections": 0, "business_writes": 0, "kafka_sends": 0, "model_calls": 0}}


def write_status(directory: Path, report: Path):
    _, session = load_status_execution(directory)
    if any(report.resolve().is_relative_to(p.resolve()) for p in (directory, Path(session["source_directory"]))):
        raise MaterialError("status report must be outside prepared execution and source materials")
    value = session_status(directory)
    save_report(report, value)
    return value
