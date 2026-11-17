"""Shared one-part execution; explicit first run and append retain separate gates."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5

from acceptance_clients import Connections, now, require
from acceptance_materials import MaterialError, read_json, save_report
from acceptance_session import load_execution
from acceptance_verify import verify_readback
from alert_kafka import _save_receipt
from alert_scenarios import sha256

TERMINAL = {"completed", "failed", "skipped"}


def event_milliseconds(value):
    # Same seconds/milliseconds convention as Fusion received_fields.parse_received_time.
    if isinstance(value, str):
        return round(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    return round(value if value > 1e11 else value * 1000)


class PartRun:
    def __init__(self, directory, profile, session, part, clients, output):
        self.directory, self.profile, self.session, self.part = directory, profile, session, part
        self.clients, self.output = clients, output
        self.deadline = time.monotonic() + profile.timing.part_timeout_seconds
        self.alerts, self.cases, self.tasks = [], [], []
        self.state = {"schema_version": "socai2.acceptance-part.v1", "execution_id": session["execution"]["execution_id"],
                      "part": part["id"], "status": "running", "started_at": now(), "stage": "starting",
                      "session_sha256": sha256((directory / "session.json").read_bytes()),
                      "steps": [], "sent": {"context": 0, "alerts": 0}, "alerts": [], "incidents": [], "cases": {},
                      "other_parts": {p["id"]: "not_executed" for p in session["plan"]["parts"] if p["id"] != part["id"]}}
        self.save()

    def save(self):
        self.state["observed_at"] = now()
        _save_receipt(self.output / "state.json", self.state)

    def stage(self, value):
        self.state["stage"] = value
        self.save()
        print(f"{self.part['id']}: {value}", flush=True)

    def passed(self, stage, detail):
        self.state["steps"].append({"stage": stage, "status": "passed", "detail": detail, "at": now()})
        self.save()

    async def pause(self):
        require(time.monotonic() < self.deadline, "part_deadline_reached")
        await asyncio.sleep(min(self.profile.timing.poll_interval_seconds, max(0, self.deadline - time.monotonic())))

    def wire(self, relative):
        return read_json(self.directory / "wire" / relative)

    async def snapshot(self, *, full=False):
        return await self.clients.pg.snapshot(self.alerts, self.cases, full=full)

    async def wait_task(self, path):
        while True:
            require(time.monotonic() < self.deadline, "part_deadline_reached")
            task = self.clients.http.request("GET", path)
            self.state["waiting_task"] = {k: task.get(k) for k in ("task_id", "subject_type", "subject_id", "status", "reason_code", "latest_run_id")}
            self.save()
            if task["status"] in TERMINAL:
                require(task.get("ended_at") is not None, "terminal_task_without_end")
                self.tasks.append(task)
                return task
            await self.pause()

    async def wait_initial(self, kind, identity):
        while True:
            page = self.clients.http.pages(f"/api/v1/socai2/{kind}s/{identity}/analysis-tasks")
            initial = [t for t in page if t["intent"] == "initial" and t["source"] == "ingress"]
            require(len(initial) <= 1, "ambiguous_initial_task")
            if initial:
                return await self.wait_task(initial[0]["status_url"])
            await self.pause()

    async def send(self, role, path):
        require(time.monotonic() < self.deadline, "part_deadline_reached")
        await self.before_effect()
        await self.before_send(role, path)
        receipt = await self.clients.send(role, path, self.wire(path))
        require(receipt["status"] == "accepted_only" and receipt["accepted"] == 1
                and receipt["not_attempted"] == 0 and not receipt["cleanup_errors"], "send_not_confirmed_no_retry")
        self.state["sent"]["context" if role == "context" else "alerts"] += 1
        self.save()
        await asyncio.sleep(self.profile.timing.send_interval_seconds)

    async def preflight(self):
        self.stage("preflight")
        readiness = await self.clients.open()
        alert_paths, context_paths = self.part["files"]["alerts"], self.part["files"]["context"]
        ids = self.session["identities"]
        all_ids = [r["predicted_canonical_alert_id"] for r in ids.values() if r["kind"] == "alert"]
        existing = await self.clients.pg.snapshot(all_ids)
        require(not existing["alerts"], "execution_alert_identity_already_exists")
        all_events = [r["event_id"] for r in ids.values() if r["kind"] == "context"]
        require(not await asyncio.to_thread(self.clients.lake.query, all_events), "execution_context_identity_already_exists")
        registered = await self.clients.pg.preflight([self.wire(p) for p in alert_paths],
                                                     [ids[p]["correlation_key"] for p in alert_paths])
        hosts = {self.wire(p).get("hostname") for p in alert_paths}
        hosts |= {self.wire(p)["ocsf_event"].get("device", {}).get("name") for p in context_paths}
        hosts.discard(None)
        require(await asyncio.to_thread(self.clients.lake.history_count, sorted(hosts)) == 0,
                "historical_context_scope_choose_new_materials")
        save_report(self.output / "preflight.json", {**readiness, **registered, "new_alerts": 0, "new_context": 0})
        self.passed("preflight", "explicit targets, source registration and new identities/scopes checked")

    async def before_effect(self):
        """Append overrides this to recheck prior receipts and wait for known tasks."""

    async def before_send(self, role, path):
        """Append checks the next identity again immediately before publishing."""

    async def case_checks(self):
        """First-part execution has no preceding cases to check."""

    def validate_saved(self, rows):
        return []

    async def execute(self):
        await self.preflight()
        alert_paths, context_paths = self.part["files"]["alerts"], self.part["files"]["context"]
        ids = self.session["identities"]
        self.stage("context_publish_and_readback")
        for path in context_paths:
            await self.send("context", path)
        expected = {ids[p]["event_id"]: self.wire(p)["ocsf_event"] for p in context_paths}
        while expected:
            saved = await asyncio.to_thread(self.clients.lake.query, list(expected))
            require(len({r["event_id"] for r in saved}) == len(saved), "duplicate_lake_records")
            if set(expected) == {r["event_id"] for r in saved}:
                for row in saved:
                    value = expected[row["event_id"]]
                    stamp = value["time"]
                    milliseconds = event_milliseconds(stamp)
                    require(row["tenant_id"] == self.profile.tenant_id and row["class_uid"] == value["class_uid"]
                            and row["event_time_ms"] == milliseconds, "context_identity_time_type_mismatch")
                    require(all(row["ocsf_json"].get(k) == v for k, v in value.items()), "context_original_value_mismatch")
                save_report(self.output / "context-readback.json", {"status": "passed", "rows": saved, "observed_at": now()})
                break
            await self.pause()
        self.passed("context_publish_and_readback", {"records": len(expected), "query_coverage": self.part["context_query_verification"]})

        self.stage("alerts_publish_and_triage")
        for path in alert_paths:
            await self.send("alert", path)
            aid = ids[path]["predicted_canonical_alert_id"]
            self.alerts.append(aid)
            while True:
                current = await self.snapshot()
                if aid in {a["id"] for a in current["alerts"]}:
                    break
                await self.pause()
            wire = self.wire(path)
            saved = next(a for a in current["alerts"] if a["id"] == aid)
            material = next((m for m in current["alert_materials"] if m["id"] == saved["latest_material_id"]), None)
            require(saved["source_alert_id"] == wire["id"] and material is not None, "alert_identity_or_material_mismatch")
            require(material["raw_json"]["raw_event"] == wire["raw_event"]
                    and material["raw_json"]["source_event_ids"] == wire["source_event_ids"], "alert_business_material_mismatch")
            refs = {r["source_event_id"] for r in current["alert_source_refs"]
                    if r["alert_id"] == aid and r["relation_kind"] == "source_event"}
            require(refs == set(wire["source_event_ids"]), "alert_source_relation_mismatch")
            self.clients.http.request("GET", f"/api/v1/socai2/alerts/{aid}")
            await self.wait_initial("alert", aid)
            self.state["alerts"].append({"material": path, "actual_alert_id": aid, "material_id": material["id"]})
            self.save()
        self.passed("alerts_publish_and_triage", {"actual_alert_ids": self.alerts})

        current = await self.snapshot()
        self.state["incidents"] = [r["id"] for r in current["incidents"]]
        require({r["alert_id"] for r in current["incident_members"]} == set(self.alerts), "unexpected_incident_membership")
        require(len({m["alert_id"] for m in current["incident_alerts"]}) == len(self.alerts), "missing_incident_membership")
        if self.part["check_level"] in {"incident", "case"}:
            self.stage("incident_diagnosis")
            affected = {ids[p]["predicted_canonical_alert_id"] for p in alert_paths}
            incident_ids = {r["incident_id"] for r in current["incident_alerts"] if r["alert_id"] in affected}
            for iid in sorted(incident_ids):
                await self.wait_initial("incident", iid)
                body = {"mode": "check", "operation_key": str(uuid5(UUID(self.session["namespace"]), self.part["id"] + ":incident-check:" + iid))}
                await self.before_effect()
                task = self.clients.http.request("POST", f"/api/v1/socai2/incidents/{iid}/diagnose", body, allowed=(202,))
                require(task["subject_type"] == "incident" and task["subject_id"] == iid, "incident_task_identity_mismatch")
                await self.wait_task(task["status_url"])
            self.passed("incident_diagnosis", {"actual_incident_ids": self.state["incidents"]})

        self.stage("case_creation_and_wait")
        for case in self.session["plan"]["scenario"]["cases"]:
            if case["create_after_part"] != self.part["id"]:
                continue
            selected = [ids[p]["predicted_canonical_alert_id"] for p in case["alert_refs"]]
            body = {"operation_key": str(uuid5(UUID(self.session["namespace"]), "case-create:" + case["key"])), "title": case["title"]}
            if case["scope"] == "incident":
                incident_ids = {r["incident_id"] for r in current["incident_alerts"] if r["alert_id"] in selected}
                require(len(incident_ids) == 1, "incident_case_anchor_not_unique")
                body["incident_ids"] = list(incident_ids)
            else:
                body["alert_ids"] = selected
            await self.before_effect()
            created = self.clients.http.request("POST", "/api/v1/socai2/cases", body, allowed=(201,))
            require(created.get("allocations") and not created.get("excluded_alert_ids"), "case_allocation_incomplete")
            allocated = []
            for allocation in created["allocations"]:
                cid, task = allocation["case_id"], allocation["initial_task"]
                require(allocation["created"] and task and task["subject_id"] == cid and task["subject_type"] == "case",
                        "case_initial_admission_missing")
                self.cases.append(cid)
                allocated.append(cid)
                self.state["cases"][case["key"]] = allocated.copy()
                self.save()
                await self.wait_task(task["status_url"])
            self.passed("case_creation_and_wait", {"case_key": case["key"], "actual_case_ids": allocated})

        await self.case_checks()
        await self.before_effect()
        self.stage("saved_http_readback")
        rows = await self.snapshot(full=True)
        save_report(self.output / "saved-records.json", rows)
        append_issues = self.validate_saved(rows)
        validation = verify_readback(self.clients.http, rows)
        save_report(self.output / "readback.json", validation)
        self.passed("saved_http_readback", validation)
        problems = [{"task_id": t["task_id"], "status": t["status"], "reason_code": t.get("reason_code")}
                    for t in self.tasks if t["status"] == "failed" or (t["status"] == "skipped" and t.get("reason_code") != "no_changes")]
        problems.extend(append_issues)
        problems.extend({"run_id": r["id"], "state": r["state"]} for r in rows["runs"] if r["state"] not in {"completed"})
        for cid in self.cases:
            if not any(r["case_id"] == cid for r in rows["results"]):
                problems.append({"case_id": cid, "reason_code": "no_saved_case_result"})
        self.state.update(status="completed_with_issues" if problems or validation["missing_originals"] else "completed",
                          ended_at=now(), execution_issues=problems, readback=validation,
                          quality="not_fully_evaluated; retained diagnostics do not stop legal downstream processing")
        self.save()
        return self.state


async def run_part(directory: Path, selected_part=None, *, clients_factory=Connections):
    profile, session = load_execution(directory)
    selected_part = selected_part or session["plan"]["selected_part"]
    require(selected_part is not None, "part_selection_required")
    parts = session["plan"]["parts"]
    require(selected_part == parts[0]["id"], "run_supports_only_first_part_use_append_for_later_parts")
    return await execute_part(directory, profile, session, parts[0], clients_factory=clients_factory)


async def execute_part(directory, profile, session, part, *, clients_factory=Connections, run_factory=PartRun):
    selected_part = part["id"]
    output = directory / "runs" / selected_part
    require(not output.exists(), "part_execution_already_exists_read_saved_state_no_replay")
    output.mkdir(parents=True, exist_ok=False)
    clients, run = None, None
    try:
        run = run_factory(directory, profile, session, part, None, output)
        clients = clients_factory(profile, output)
        run.clients = clients
        return await run.execute()
    except BaseException as exc:
        state = run.state if run else {"execution_id": session["execution"]["execution_id"], "part": selected_part, "steps": []}
        state.update(status="incomplete", ended_at=now(), error_type=type(exc).__name__,
                     error_code=str(exc) if isinstance(exc, MaterialError) else "execution_error_see_saved_step",
                     retry_policy="no_automatic_replay")
        _save_receipt(output / "state.json", state)
        if not isinstance(exc, Exception):
            raise
        return state
    finally:
        if clients:
            try:
                await clients.close()
            except Exception as exc:  # noqa: BLE001 - retain the recorded operation outcome on client cleanup failure
                state = run.state if run else read_json(output / "state.json")
                state.setdefault("cleanup_errors", []).append(type(exc).__name__)
                state["status"] = "incomplete"
                _save_receipt(output / "state.json", state)

