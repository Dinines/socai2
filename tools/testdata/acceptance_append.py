"""Append one explicit part to an ended session; preserve prior receipts and runs."""
from __future__ import annotations

import asyncio
import copy
from pathlib import Path
from uuid import UUID, uuid5

from acceptance_clients import Connections, now, require
from acceptance_materials import _safe_file, read_json, save_report
from acceptance_run import TERMINAL, PartRun, event_milliseconds, execute_part
from acceptance_session import load_execution
from acceptance_status import execution_links, session_status
from alert_scenarios import sha256

IMMUTABLE = ("alert_materials", "alert_source_refs", "analysis_tasks", "analysis_attempts",
             "runs", "results", "run_members", "run_steps", "artifacts", "alert_assessments", "incident_diagnoses")


def previous_unchanged(before, after):
    for table in IMMUTABLE:
        current = {r["id"]: r for r in after[table]}
        require(all(current.get(r["id"]) == r for r in before[table]), "previous_saved_record_changed:" + table)


def idle(rows):
    return (all(t["state"] in TERMINAL | {"merged"} and t.get("ended_at") for t in rows["analysis_tasks"])
            and all(a["local_state"] in {"ended", "interrupted"} for a in rows["analysis_attempts"])
            and all(r["state"] in {"completed", "failed", "unknown"} for r in rows["runs"]))


def connection_unchanged(before, current):
    expected = before.get("connection_sha256")
    require(isinstance(expected, dict) and set(expected) == {"http", "kafka", "postgres", "lake"},
            "previous_connection_identity_missing")
    require(current.get("connection_sha256") == expected, "append_connection_configuration_changed")


def scope_members(session, rows, case, case_ids):
    ids = session["identities"]
    selected = {ids[p]["predicted_canonical_alert_id"] for p in case["alert_refs"]}
    if case["scope"] == "incident":
        incidents = {r["incident_id"] for r in rows["incident_alerts"] if r["alert_id"] in selected}
        require(len(incidents) == 1, "incident_case_anchor_not_unique")
        expected = {r["alert_id"] for r in rows["incident_members"] if r["incident_id"] in incidents}
    else:
        expected = selected
    actual = {r["alert_id"] for r in rows["case_alerts"] if r["case_id"] in case_ids}
    require(actual == expected, "case_current_scope_mismatch:" + case["key"])
    return sorted(actual)


class AppendRun(PartRun):
    def __init__(self, *args, previous, gate):
        self.previous, self.gate = previous, gate
        super().__init__(*args)
        state = previous["state"]
        self.alerts = [a["actual_alert_id"] for a in state["alerts"]]
        self.cases = sorted({cid for values in state["cases"].values() for cid in values})
        self.state.update(mode="append", alerts=copy.deepcopy(state["alerts"]), incidents=list(state["incidents"]),
                          cases=copy.deepcopy(state["cases"]), previous_part=state["part"],
                          previous_receipts=gate["sources"],
                          other_parts={p["id"]: p["recorded_state"] for p in gate["parts"] if p["id"] != self.part["id"]})
        order = [p["id"] for p in self.session["plan"]["parts"]]
        self.prefix = set(order[:order.index(self.part["id"])])
        self.save()

    def frozen(self):
        _, current = load_execution(self.directory)
        require(current == self.session, "prepared_session_changed_before_append_effect")
        for source in self.gate["sources"]:
            require(sha256(_safe_file(self.directory, source["path"]).read_bytes()) == source["sha256"],
                    "previous_receipt_changed_before_append_effect")

    async def preflight(self):
        self.stage("append_preflight")
        self.frozen()
        readiness = await self.clients.open()
        connection_unchanged(self.previous["preflight"], readiness)
        prior = self.previous["rows"]
        live = await self.snapshot(full=True)
        require(idle(live), "previous_live_execution_not_ended")
        execution_links(live)
        previous_unchanged(prior, live)
        for table in ("alerts", "incidents", "cases", "analysis_tasks", "analysis_attempts", "runs", "results"):
            require({r["id"] for r in live[table]} == {r["id"] for r in prior[table]}, "previous_live_identity_changed:" + table)
        require(live["incident_members"] == prior["incident_members"] and live["case_alerts"] == prior["case_alerts"],
                "previous_live_membership_changed")
        ids = self.session["identities"]
        future_alerts = [v["predicted_canonical_alert_id"] for p, v in ids.items()
                         if v["kind"] == "alert" and p.split("/")[0] not in self.prefix]
        require(not (await self.clients.pg.snapshot(future_alerts))["alerts"], "append_alert_identity_already_exists")
        future_events = [v["event_id"] for p, v in ids.items()
                         if v["kind"] == "context" and p.split("/")[0] not in self.prefix]
        require(not await asyncio.to_thread(self.clients.lake.query, future_events), "append_context_identity_already_exists")
        old_events = {v["event_id"]: self.wire(p)["ocsf_event"] for p, v in ids.items()
                      if v["kind"] == "context" and p.split("/")[0] in self.prefix}
        saved_events = await asyncio.to_thread(self.clients.lake.query, list(old_events))
        require(len(saved_events) == len(old_events) and {r["event_id"] for r in saved_events} == set(old_events),
                "previous_context_missing_or_duplicate")
        for row in saved_events:
            original = old_events[row["event_id"]]
            require(row["tenant_id"] == self.profile.tenant_id and row["class_uid"] == original["class_uid"]
                    and row["event_time_ms"] == event_milliseconds(original["time"])
                    and all(row["ocsf_json"].get(k) == v for k, v in original.items()), "previous_context_changed")
        paths = self.part["files"]["alerts"]
        registration = await self.clients.pg.preflight([self.wire(p) for p in paths],
                            [ids[p]["correlation_key"] for p in paths], known_alert_ids=self.alerts)
        hosts = {self.wire(p).get("hostname") for p in paths}
        hosts |= {self.wire(p)["ocsf_event"].get("device", {}).get("name") for p in self.part["files"]["context"]}
        hosts.discard(None)
        require(await asyncio.to_thread(self.clients.lake.history_count, sorted(hosts), list(old_events)) == 0,
                "append_context_scope_contains_external_history")
        save_report(self.output / "before-records.json", live)
        save_report(self.output / "preflight.json", {**readiness, **registration, "status": "passed",
                    "previous_part": self.previous["state"]["part"], "observed_at": now(),
                    "previous_alert_ids": self.alerts, "previous_case_ids": self.cases,
                    "unsent_alert_identities": len(future_alerts), "unsent_context_identities": len(future_events)})
        self.passed("append_preflight", "same environment, ended execution, unchanged prior records and unsent identities checked")

    async def before_effect(self):
        self.frozen()
        # This session's own ingress and automatic tasks may still be finishing.
        # The production dispatcher owns capacity; no second queue or lease here.
        while True:
            live = await self.snapshot(full=True)
            previous_unchanged(self.previous["rows"], live)
            require(set(self.cases) <= {r["id"] for r in live["cases"]}, "previous_case_identity_missing_before_effect")
            pending = [t for t in live["analysis_tasks"] if t["state"] not in TERMINAL | {"merged"}]
            for task in pending:
                path = f"/api/v1/socai2/{task['subject_type']}s/{task['subject_id']}/analysis-tasks/{task['id']}"
                await self.wait_task(path)
            if idle(await self.snapshot()):
                break
            await self.pause()
        self.frozen()

    async def before_send(self, role, path):
        entry = self.session["identities"][path]
        if role == "alert":
            existing = (await self.clients.pg.snapshot([entry["predicted_canonical_alert_id"]]))["alerts"]
        else:
            existing = await asyncio.to_thread(self.clients.lake.query, [entry["event_id"]])
        require(not existing, "append_identity_already_exists_before_send")

    async def case_checks(self):
        self.stage("case_check_and_wait")
        for case in self.session["plan"]["scenario"]["cases"]:
            if self.part["id"] not in case["check_after_parts"]:
                continue
            case_ids = self.state["cases"].get(case["key"])
            require(case_ids, "previous_case_mapping_missing")
            for cid in case_ids:
                await self.before_effect()
                body = {"mode": "check", "operation_key": str(uuid5(UUID(self.session["namespace"]),
                        self.part["id"] + ":case-check:" + case["key"] + ":" + cid))}
                task = self.clients.http.request("POST", f"/api/v1/socai2/cases/{cid}/investigations", body, allowed=(202,))
                require(task["subject_type"] == "case" and task["subject_id"] == cid, "case_check_identity_mismatch")
                await self.wait_task(task["status_url"])
            self.passed("case_check_and_wait", {"case_key": case["key"], "actual_case_ids": case_ids})

    def validate_saved(self, rows):
        self.frozen()
        previous_unchanged(self.previous["rows"], rows)
        execution_links(rows)
        require(idle(rows), "append_execution_not_ended_at_readback")
        previous_runs = {r["id"] for r in self.previous["rows"]["runs"]}
        previous_results = {r["id"] for r in self.previous["rows"]["results"]}
        reports, problems = [], []
        for case in self.session["plan"]["scenario"]["cases"]:
            if self.part["id"] not in case["check_after_parts"] and case["create_after_part"] != self.part["id"]:
                continue
            cids = self.state["cases"].get(case["key"], [])
            require(cids, "case_mapping_missing_at_readback")
            members = scope_members(self.session, rows, case, cids)
            new_runs = [r for r in rows["runs"] if r["case_id"] in cids and r["id"] not in previous_runs]
            new_results = [r for r in rows["results"] if r["case_id"] in cids and r["id"] not in previous_results]
            old_members = {r["alert_id"] for r in self.previous["rows"]["case_alerts"] if r["case_id"] in cids}
            scope_changed = set(members) != old_members
            if scope_changed:
                for cid in cids:
                    current_members = {r["alert_id"] for r in rows["case_alerts"] if r["case_id"] == cid}
                    covering = [r for r in new_runs if r["case_id"] == cid and
                                {m["alert_id"] for m in rows["run_members"] if m["run_id"] == r["id"]} == current_members]
                    if not covering:
                        problems.append({"case_id": cid, "reason_code": "no_new_case_run_for_current_scope"})
            for run in new_runs:
                if not any(r["source_run_id"] == run["id"] for r in new_results):
                    problems.append({"case_id": run["case_id"], "run_id": run["id"], "reason_code": "no_new_case_result"})
            reports.append({"key": case["key"], "scope": case["scope"], "case_ids": cids,
                "current_member_ids": members, "new_run_ids": [r["id"] for r in new_runs],
                "new_result_ids": [r["id"] for r in new_results],
                "scope_changed": scope_changed,
                "execution_state": "new_run_recorded" if new_runs else "no_new_run",
                "quality": "not_fully_evaluated"})
        save_report(self.output / "append-readback.json", {"status": "passed_with_issues" if problems else "passed", "previous_records": "unchanged",
                    "cases": reports, "execution_issues": problems, "model_quality": "not_fully_evaluated"})
        return problems


async def append_part(directory: Path, selected_part, *, clients_factory=Connections):
    profile, session = load_execution(directory)
    gate = session_status(directory)
    require(selected_part and gate["state"] == "waiting_append" and gate["next_part"] == selected_part,
            "append_requires_explicit_next_unexecuted_part")
    order = [p["id"] for p in session["plan"]["parts"]]
    index = order.index(selected_part)
    prefix = directory / "runs" / order[index - 1]
    preflight_path = str((prefix / "preflight.json").relative_to(directory))
    preflight_file = _safe_file(directory, preflight_path)
    previous = {"state": read_json(prefix / "state.json"), "rows": read_json(prefix / "saved-records.json"),
                "preflight": read_json(preflight_file)}
    gate["sources"].append({"path": preflight_path, "sha256": sha256(preflight_file.read_bytes())})
    def factory(*args):
        return AppendRun(*args, previous=previous, gate=gate)
    return await execute_part(directory, profile, session, session["plan"]["parts"][index],
                              clients_factory=clients_factory, run_factory=factory)
