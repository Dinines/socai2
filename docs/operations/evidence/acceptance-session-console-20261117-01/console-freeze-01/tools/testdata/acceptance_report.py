"""Read-only, ID-deduplicated acceptance report from a single frozen session."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from uuid import UUID

from acceptance_materials import MaterialError, _safe_file, parse_json, save_report
from acceptance_report_models import counter, model_report, obj
from acceptance_status import inventory, load_status_execution, session_status
from alert_scenarios import sha256

TABLES = ("alerts", "incidents", "cases", "analysis_tasks", "analysis_attempts", "runs", "results",
          "run_steps", "artifacts", "run_members")
TERMINAL = {"completed", "failed", "skipped", "merged", "unknown", "cancelled", "partial"}


def token(value):
    """Diagnostic codes, not arbitrary provider errors or free-form details."""
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value) else "unavailable"


class ReportSources:
    def __init__(self, directory, sources):
        self.directory = directory
        self.hashes = {s["path"]: s["sha256"] for s in sources}

    def read(self, relative):
        data = _safe_file(self.directory, relative).read_bytes()
        digest = sha256(data)
        if self.hashes.setdefault(relative, digest) != digest:
            raise MaterialError("saved receipts changed during report")
        return parse_json(data, "saved receipt")

    def unchanged(self):
        try:
            return all(sha256(_safe_file(self.directory, p).read_bytes()) == h for p, h in self.hashes.items())
        except (OSError, ValueError):
            return False


def new_output(directory, output):
    _, session = load_status_execution(directory)
    if output.exists() or output.is_symlink() or any(output.resolve().is_relative_to(p.resolve())
            for p in (directory, Path(session["source_directory"]))):
        raise MaterialError("output must be a new directory outside prepared execution and source materials")
    return session


def valid_identity(row, tenant):
    try:
        return isinstance(row, dict) and str(UUID(row["id"])) == row["id"] and row.get("tenant_id") == tenant
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def valid_links(table, row):
    required = {"analysis_tasks": ("subject_id",), "analysis_attempts": ("task_id",),
                "run_steps": ("run_id",), "run_members": ("run_id",), "results": ("case_id", "source_run_id")}
    if any(row.get(key) is None for key in required.get(table, ())):
        return False
    try:
        return all(value is None or isinstance(value, str) and str(UUID(value)) == value
                   for key, value in row.items() if key in {"run_id", "task_id", "subject_id", "alert_id", "incident_id",
                       "case_id", "source_run_id", "previous_run_id", "comparison_result_id", "input_artifact_id"})
    except (TypeError, ValueError, AttributeError):
        return False


def frozen(table, row):
    return table in {"artifacts", "run_members", "results"} or token(row.get("state")) in TERMINAL or row.get("local_state") == "ended"


def execution_report(directory):
    status = session_status(directory)
    reader = ReportSources(directory, status["sources"])
    before = inventory(directory)
    tables = {name: {} for name in TABLES}
    origins = {name: {} for name in TABLES}
    problems, parts = [], []
    complete = True
    for part in status["parts"]:
        path = part["record_path"] + "/saved-records.json"
        summary = {k: part.get(k) for k in ("id", "planned_counts", "recorded_state", "recorded_sent", "closure_verified",
                                           "readback_state", "stage", "execution_issues", "issues")}
        summary.update(stages=[], snapshot_state="not_started", newly_observed={k: 0 for k in TABLES},
                       observed_counts={k: 0 for k in TABLES}, error_code=None)
        if not part["execution_directory_exists"]:
            summary["recorded_sent"] = {"context": 0, "alerts": 0}
        if part["execution_directory_exists"]:
            summary["snapshot_state"] = "incomplete"
            bound = False
            try:
                state = reader.read(part["record_path"] + "/state.json")
                bound = (state.get("execution_id") == status["execution_id"] and state.get("part") == part["id"]
                         and state.get("session_sha256") == reader.hashes["session.json"]
                         and state.get("schema_version") == "socai2.acceptance-part.v1")
                if not bound:
                    raise MaterialError("unbound saved state")
                summary["error_code"] = token(state["error_code"]) if state.get("error_code") else None
                steps = state.get("steps")
                if not isinstance(steps, list) or not all(isinstance(s, dict) for s in steps):
                    raise MaterialError("invalid saved stages")
                summary["stages"] = [{"stage": token(s.get("stage")), "status": token(s.get("status"))} for s in steps]
            except (OSError, ValueError, AttributeError, TypeError):
                problems.append({"code": "saved_stages_unreadable", "path": part["record_path"] + "/state.json"})
            try:
                data = reader.read(path)
                if not bound or not isinstance(data, dict):
                    raise MaterialError("invalid saved snapshot")
                summary["snapshot_state"] = "observed"
                for table in TABLES:
                    rows = data.get(table)
                    if not isinstance(rows, list):
                        problems.append({"code": "saved_table_unreadable", "path": path, "table": table})
                        summary["snapshot_state"] = "incomplete"
                        summary["newly_observed"][table] = summary["observed_counts"][table] = None
                        continue
                    seen = set()
                    for index, row in enumerate(rows):
                        source = {"path": path, "pointer": f"/{table}/{index}", "sha256": reader.hashes[path]}
                        if (not valid_identity(row, status["environment"]["tenant_id"]) or not valid_links(table, row)
                                or row["id"] in seen):
                            problems.append({"code": "invalid_saved_row", "source": source})
                            summary["snapshot_state"] = "incomplete"
                            continue
                        identity = row["id"]
                        seen.add(identity)
                        old = tables[table].get(identity)
                        if old is None:
                            summary["newly_observed"][table] += 1
                        elif old != row and frozen(table, old):
                            problems.append({"code": "frozen_row_conflict", "table": table, "id": identity,
                                             "previous_source": origins[table][identity], "source": source})
                            summary["snapshot_state"] = "incomplete"
                            continue
                        tables[table][identity], origins[table][identity] = row, source
                    summary["observed_counts"][table] = len(seen)
            except (OSError, ValueError, TypeError, AttributeError):
                problems.append({"code": "saved_snapshot_unreadable", "path": path})
                summary["newly_observed"] = summary["observed_counts"] = {k: None for k in TABLES}
            complete &= summary["snapshot_state"] == "observed"
        parts.append(summary)
    models, files = model_report(tables["artifacts"], origins["artifacts"], complete)
    quality, step_issues = quality_report(tables, origins)
    subjects = subject_report(tables, origins)
    for subject in subjects:
        for run in subject["rounds"]:
            if run["scope"]["selected_count"] is None:
                problems.append({"code": "run_scope_unavailable", "run_id": run["run_id"], "source": run["source"]})
    if not reader.unchanged() or before != inventory(directory):
        problems.append({"code": "receipts_changed_during_read", "path": "runs"})
        complete = False
        models["coverage"], models["request_count"] = "incomplete", None
        models["usage"] = {k: None for k in models["usage"]}
    value = {"schema_version": "socai2.acceptance-session-report.v1", "execution_id": status["execution_id"],
             "observed_at": status["observed_at"], "environment": status["environment"],
             "provenance": "saved_local_receipts", "live_state_verified": False,
             "state": status["state"], "all_parts_completed": status["state"] == "all_parts_completed",
             "next_part": status["next_part"], "next_action": status["next_action"], "parts": parts,
             "statistics_state": "saved_snapshots_complete" if complete else "incomplete",
             "counts": {k: len(v) if complete else None for k, v in tables.items()},
             "observed_counts": {k: len(v) for k, v in tables.items()}, "subjects": subjects,
             "tasks": [{k: t.get(k) for k in ("id", "subject_type", "subject_id", "kind", "state", "reason_code", "merged_into_task_id")}
                       for t in tables["analysis_tasks"].values()],
             "attempts": [{k: a.get(k) for k in ("id", "task_id", "run_id", "local_state", "outcome", "local_ended_at",
                           "interruption_observed_at", "previous_run_id", "comparison_result_id")}
                          for a in tables["analysis_attempts"].values()],
             "models": models, "quality": quality, "step_issues": step_issues,
             "blocking_issues": status["blocking_issues"], "report_issues": problems,
             "sources": [{"path": p, "sha256": h} for p, h in sorted(reader.hashes.items())],
             "this_command": status["this_command"]}
    return value, files


def quality_report(tables, origins):
    issues, seen = [], set()
    for artifact in tables["artifacts"].values():
        if artifact.get("kind") != "source_snapshot":
            continue
        content = obj(artifact.get("content_json"))
        schema = content.get("schema_version")
        reviews = ("citation_review", "validation_review") if schema == "socai2.baseline-delivery.v2" else (
            ("quality",) if schema == "socai2.stage-delivery.v1" else ())
        for review in reviews:
            candidates = obj(content.get(review)).get("issues", [])
            if not isinstance(candidates, list):
                candidates = [{"code": "quality_receipt_unreadable"}]
            for problem in candidates:
                problem = obj(problem)
                code = token(problem.get("code"))
                path = problem.get("path")
                path = path if isinstance(path, str) and re.fullmatch(r"[$.\[\]a-zA-Z0-9_*:-]{1,300}", path) else None
                key = (artifact.get("run_id"), schema, review, code, path)
                if key in seen:
                    continue
                seen.add(key)
                issues.append({"run_id": artifact.get("run_id"), "artifact_id": artifact["id"],
                               "stage": "C6" if schema == "socai2.baseline-delivery.v2" else token(content.get("stage")),
                               "review": review, "code": code, "path": path, "source": origins["artifacts"][artifact["id"]]})
    steps = [{"step_id": s["id"], "run_id": s.get("run_id"), "stage": token(s.get("stage_code")),
              "name": token(s.get("name")), "state": token(s.get("state")),
              "code": token(obj(s.get("error")).get("code")), "source": origins["run_steps"][s["id"]]}
             for s in tables["run_steps"].values() if s.get("error") or token(s.get("state")) in {"failed", "unknown", "skipped"}]
    return {"state": "not_fully_evaluated", "issue_count": len(issues), "issues_by_code": dict(Counter(i["code"] for i in issues)),
            "issues_by_stage": dict(Counter(i["stage"] for i in issues)),
            "issues": issues, "body_correctness": "not_fully_evaluated", "accuracy": None}, steps


def scope_report(kind, run, tables, origins):
    if kind == "alert":
        return {"source_kind": "run_alert", "alert_ids": [run["alert_id"]], "selected_count": 1,
                "total_count": 1, "source": origins["runs"][run["id"]]}
    if kind == "case":
        members = [r for r in tables["run_members"].values() if r.get("run_id") == run["id"] and r.get("alert_id")]
        ids = sorted({m["alert_id"] for m in members})
        return {"source_kind": "run_members", "alert_ids": ids, "selected_count": len(ids) if members else None,
                "total_count": len(ids) if members else None,
                "sources": [origins["run_members"][m["id"]] for m in members]}
    artifact = tables["artifacts"].get(run.get("input_artifact_id"), {})
    selection = obj(obj(artifact.get("content_json")).get("input_selection"))
    ids = selection.get("selected_alert_ids")
    try:
        valid = (artifact.get("run_id") == run["id"] and isinstance(ids, list)
                 and all(isinstance(i, str) and str(UUID(i)) == i for i in ids) and len(set(ids)) == len(ids)
                 and counter(selection.get("selected_count")) == len(ids)
                 and counter(selection.get("total_member_count")) is not None and selection["total_member_count"] >= len(ids))
    except (TypeError, ValueError):
        valid = False
    return {"source_kind": "incident_input_selection", "alert_ids": sorted(ids) if valid else [],
            "selected_count": len(ids) if valid else None, "total_count": selection["total_member_count"] if valid else None,
            "source": origins["artifacts"].get(artifact.get("id")), "state": "recorded" if valid else "unavailable"}


def subject_report(tables, origins):
    subjects = []
    for kind, table in (("case", "cases"), ("incident", "incidents"), ("alert", "alerts")):
        for subject in tables[table].values():
            runs = sorted((r for r in tables["runs"].values() if r.get(kind + "_id") == subject["id"]),
                          key=lambda r: (str(r.get("started_at") or r.get("requested_at") or ""), r["id"]))
            rounds = []
            for index, run in enumerate(runs, 1):
                attempts = [a for a in tables["analysis_attempts"].values() if a.get("run_id") == run["id"]]
                stages = [{k: s.get(k) for k in ("id", "seq", "stage_code", "name", "state", "kind")}
                          for s in sorted(tables["run_steps"].values(), key=lambda s: (counter(s.get("seq")) or 0, s["id"]))
                          if s.get("run_id") == run["id"]]
                scope = scope_report(kind, run, tables, origins)
                rounds.append({"round": index, "run_id": run["id"], "state": token(run.get("state")),
                    "delivery_state": token(run.get("delivery_state")), "started_at": run.get("started_at"),
                    "ended_at": run.get("ended_at"), "previous_run_ids": sorted({a["previous_run_id"] for a in attempts if a.get("previous_run_id")}),
                    "comparison_result_id": run.get("comparison_result_id"), "task_ids": sorted({a["task_id"] for a in attempts}),
                    "attempt_ids": [a["id"] for a in attempts], "stages": stages,
                    "frozen_alert_ids": scope["alert_ids"], "scope": scope,
                    "results": [{k: r.get(k) for k in ("id", "validation_state", "conclusion_state", "delivery_state", "adoption_state")}
                                for r in tables["results"].values() if r.get("source_run_id") == run["id"]],
                    "source": origins["runs"][run["id"]]})
            subjects.append({"kind": kind, "id": subject["id"], "rounds": rounds, "source": origins[table][subject["id"]]})
    return subjects


def report_exit_code(value):
    return 3 if (value["blocking_issues"] or value["report_issues"] or value["models"]["issues"]
                 or any(p.get("execution_issues") for p in value["parts"])) else 0


def write_session_report(directory: Path, output: Path):
    new_output(directory, output)
    value, files = execution_report(directory)
    from acceptance_report_render import render_report
    files["report.md"] = render_report(value, directory, output).encode("utf-8")
    output.mkdir(parents=True)
    for relative, content in files.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        if target.read_bytes() != content:
            raise MaterialError("report export failed readback")
    save_report(output / "report.json", value)
    manifest = {"schema_version": "socai2.acceptance-report-files.v1", "execution_id": value["execution_id"],
                "files": [{"path": str(p.relative_to(output)), "sha256": sha256(p.read_bytes())}
                          for p in sorted(output.rglob("*")) if p.is_file()],
                "sources": value["sources"], "readback": "passed"}
    save_report(output / "manifest.json", manifest)
    return value
