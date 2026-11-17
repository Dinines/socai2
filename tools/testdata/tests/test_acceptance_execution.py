"""3b identity freezing and one-part ordering; live readback is verified separately."""
import asyncio
import copy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
from acceptance_contract import Profile
from acceptance_materials import MaterialError, control, convert_package, read_json
from acceptance_run import event_milliseconds, run_part
from acceptance_runtime_contract import Execution
from acceptance_session import load_execution, prepare_execution
from alert_scenarios import json_bytes
from test_acceptance_materials import EXAMPLES, STREAMING, recipe, snapshot


@pytest.fixture
def prepared(tmp_path):
    profile = control(Profile, read_json(EXAMPLES / "profile.json"), "profile")
    profile.timing.send_interval_seconds = 0
    profile.timing.poll_interval_seconds = 0.001
    materials = tmp_path / "materials"
    convert_package(STREAMING, recipe(), profile, materials)
    scenario = read_json(materials / "scenario.json")
    scenario["cases"] = scenario["cases"][:1]
    (materials / "scenario.json").write_bytes(json_bytes(scenario))
    for path in (materials / "part1/alerts").glob("*.json"):
        if path.name != "001.json":
            path.unlink()
    for path in (materials / "part1/context").glob("*.json"):
        if path.name not in {"001.json", "002.json"}:
            path.unlink()
    first = read_json(materials / "part1/context/002.json")
    first["ocsf_event"]["unknown_observation"] = {"same_text_as_source_id": first["event_id"], "zero": 0, "flag": False, "items": []}
    (materials / "part1/context/002.json").write_bytes(json_bytes(first))
    execution = Execution(schema_version="socai2.acceptance-execution.v1", execution_id="direct-one-part", time_policy="preserve")
    before = snapshot(materials)
    output = tmp_path / "prepared"
    with patch("socket.socket", side_effect=AssertionError("offline prepare")):
        session = prepare_execution(materials, profile, execution, output)
    assert before == snapshot(materials)
    return output, profile, session, materials


def test_prepare_new_identities_preserves_business_time_and_nested_sources(prepared, tmp_path):
    output, profile, session, materials = prepared
    _, reread = load_execution(output)
    assert reread == session
    assert session["execution_status"] == "prepared_not_executed"
    assert len(session["plan"]["parts"]) == 2 and not (output / "runs").exists()
    contexts = {}
    for path, entry in session["identities"].items():
        old, new = read_json(materials / path), read_json(output / "wire" / path)
        if entry["kind"] == "context":
            UUID(new["event_id"])
            assert new["event_id"] != old["event_id"]
            ocsf = new["ocsf_event"]
            assert new["event_id"] == ocsf["uid"] == ocsf["metadata"]["uid"]
            assert ocsf["time"] == old["ocsf_event"]["time"]
            import json
            assert json.loads(ocsf["raw_data"])["uid"] == new["event_id"]
            contexts[new["event_id"]] = new
            if "unknown_observation" in ocsf:
                assert ocsf["unknown_observation"] == old["ocsf_event"]["unknown_observation"]
        else:
            assert new["id"] == new["source_alert_id"] != old["id"]
            assert new["event_time"] == old["event_time"] and new["created_at"] == old["created_at"]
            assert new["tenant_id"] == old["tenant_id"] and new["connector_id"] == old["connector_id"]
    for path, entry in session["identities"].items():
        if entry["kind"] == "alert":
            wire = read_json(output / "wire" / path)
            assert set(wire["source_event_ids"]) <= set(contexts)
            assert wire["raw_event"]["ocsf_event"]["uid"] in wire["source_event_ids"]
    second = prepare_execution(materials, profile,
                               Execution(schema_version="socai2.acceptance-execution.v1", execution_id="different-execution", time_policy="preserve"),
                               tmp_path / "second")
    assert set(session["event_identity_map"].values()).isdisjoint(second["event_identity_map"].values())
    assert not {r["predicted_canonical_alert_id"] for r in session["identities"].values() if r["kind"] == "alert"} & {
        r["predicted_canonical_alert_id"] for r in second["identities"].values() if r["kind"] == "alert"}
    with pytest.raises(MaterialError, match="new directory"):
        prepare_execution(materials, profile, control(Execution, session["execution"], "execution"), output)


class FakeConnections:
    """Only orchestration doubles. No network or fabricated live-readback claims."""
    def __init__(self, profile, output, session, directory, *, unknown=False):
        self.profile, self.output, self.session, self.directory = profile, output, session, directory
        self.log, self.sent, self.polls, self.context_seen = [], [], {}, False
        self.unknown = unknown
        self.pg = SimpleNamespace(snapshot=self.snapshot, preflight=self.preflight)
        self.lake = SimpleNamespace(query=self.lake_rows, history_count=lambda hosts: 0)
        self.http = SimpleNamespace(request=self.request, pages=self.pages)
        self.iid, self.cid = "876b5dc0-91bb-46cc-b9e4-3518d784a468", "dd6ab294-879b-49b8-b53b-e506d0915606"

    async def open(self):
        return {"target": "test_double"}

    async def close(self):
        self.log.append("close")

    async def preflight(self, alerts, keys):
        return {"registered_connectors": ["fixture"]}

    async def send(self, role, path, payload):
        self.log.append("send:" + role)
        if role == "alert":
            assert self.context_seen, "alerts cannot precede actual context readback"
        if self.unknown:
            return {"status": "failed", "accepted": 0, "not_attempted": 0, "cleanup_errors": []}
        self.sent.append((role, path, payload))
        return {"status": "accepted_only", "accepted": 1, "not_attempted": 0, "cleanup_errors": []}

    def lake_rows(self, identities):
        import datetime
        self.log.append("lake")
        saved = []
        for role, _, value in self.sent:
            if role != "context":
                continue
            stamp = datetime.datetime.fromisoformat(value["ocsf_event"]["time"]).timestamp()
            saved.append({"event_id": value["event_id"], "tenant_id": value["tenant_id"],
                          "event_time_ms": round(stamp * 1000), "class_uid": value["ocsf_event"]["class_uid"],
                          "ocsf_json": copy.deepcopy(value["ocsf_event"])})
        if saved:
            self.context_seen = True
        return saved

    async def snapshot(self, alert_ids, case_ids=(), full=False):
        out = {k: [] for k in ("alerts", "alert_materials", "alert_source_refs", "incident_alerts", "incident_members",
                               "incidents", "cases", "case_alerts", "analysis_tasks", "analysis_attempts", "runs", "results")}
        for role, path, value in self.sent:
            if role != "alert":
                continue
            aid = self.session["identities"][path]["predicted_canonical_alert_id"]
            if aid not in alert_ids:
                continue
            out["alerts"].append({"id": aid, "source_alert_id": value["id"], "latest_material_id": "material"})
            out["alert_materials"].append({"id": "material", "raw_json": value})
            out["alert_source_refs"] += [{"alert_id": aid, "source_event_id": x, "relation_kind": "source_event"} for x in value["source_event_ids"]]
            out["incident_alerts"].append({"alert_id": aid, "incident_id": self.iid})
            out["incident_members"].append({"alert_id": aid, "incident_id": self.iid})
            out["incidents"] = [{"id": self.iid}]
        if case_ids:
            out["cases"] = [{"id": self.cid}]
            out["results"] = [{"id": "result", "case_id": self.cid}]
        if full:
            self.log.append("saved-full")
            out.update(run_steps=[], artifacts=[], run_members=[])
        return out

    def pages(self, path):
        kind = "alert" if "/alerts/" in path else "incident"
        self.log.append("initial:" + kind)
        return [{"intent": "initial", "source": "ingress", "status_url": path + "/initial"}]

    def request(self, method, path, body=None, allowed=(200,)):
        if method == "POST":
            if path.endswith("/diagnose"):
                self.log.append("incident-check")
                return {"subject_type": "incident", "subject_id": self.iid, "status_url": path + "/check"}
            self.log.append("case-create")
            assert "incident_ids" in body
            return {"excluded_alert_ids": [], "allocations": [{"created": True, "case_id": self.cid,
                    "initial_task": {"subject_id": self.cid, "subject_type": "case", "status_url": "/case-task"}}]}
        if "analysis-tasks" in path or path.endswith("/check") or path == "/case-task":
            n = self.polls.get(path, 0)
            self.polls[path] = n + 1
            self.log.append("task-wait" if n == 0 else "task-terminal")
            return {"task_id": path, "status": "accepted" if n == 0 else "completed", "ended_at": None if n == 0 else "now"}
        return {"id": path.rsplit("/", 1)[-1]}


@pytest.mark.parametrize("unknown", [False, True])
def test_single_part_ordering_and_no_replay(prepared, monkeypatch, unknown):
    output, _profile, session, _ = prepared
    holder = []

    def factory(p, out):
        holder.append(FakeConnections(p, out, session, output, unknown=unknown))
        return holder[-1]

    # This test checks orchestration, while the 21 run exercises the real verifier.
    monkeypatch.setattr("acceptance_run.verify_readback", lambda http, rows: {"status": "passed", "missing_originals": [], "scope": "test_double"})
    state = asyncio.run(run_part(output, clients_factory=factory))
    assert state == read_json(output / "runs/part1/state.json")
    assert state["other_parts"] == {"part2": "not_executed"}
    log = holder[0].log
    if unknown:
        assert state["status"] == "incomplete" and state["error_code"] == "send_not_confirmed_no_retry"
        assert "send:alert" not in log and "case-create" not in log
    else:
        assert state["status"] == "completed" and state["sent"] == {"context": 2, "alerts": 1}
        assert log.index("send:context") < log.index("send:alert") < log.index("task-terminal") < log.index("incident-check") < log.index("case-create") < log.index("saved-full")
        assert read_json(output / "runs/part1/context-readback.json")["status"] == "passed"
    with pytest.raises(MaterialError, match="no_replay"):
        asyncio.run(run_part(output, clients_factory=factory))
    assert len(holder) == 1
    with pytest.raises(MaterialError, match="only_first_part"):
        asyncio.run(run_part(output, "part2", clients_factory=factory))


def test_prepared_wire_changes_are_rejected_before_any_effect(prepared):
    output, _, _, _ = prepared
    path = output / "wire/part1/alerts/001.json"
    value = read_json(path)
    value["title"] += " changed"
    path.write_bytes(json_bytes(value))
    with pytest.raises(MaterialError, match="prepared material"):
        load_execution(output)
    assert not (output / "runs").exists()


def test_numeric_ocsf_times_follow_fusion_seconds_and_milliseconds():
    assert event_milliseconds(0) == 0
    assert event_milliseconds(1794884400) == event_milliseconds(1794884400000) == event_milliseconds("2026-11-17T03:00:00+00:00")


def test_object_raw_data_preserves_shared_source_identity(prepared, tmp_path):
    import json
    _, profile, _, materials = prepared
    for relative in ("part1/context/002.json", "part1/alerts/001.json"):
        path = materials / relative
        value = read_json(path)
        ocsf = value["ocsf_event"] if "/context/" in relative else value["raw_event"]["ocsf_event"]
        ocsf["raw_data"] = json.loads(ocsf["raw_data"])
        path.write_bytes(json_bytes(value))
    original = snapshot(materials)
    output = tmp_path / "object-execution"
    prepare_execution(materials, profile, Execution(schema_version="socai2.acceptance-execution.v1",
                      execution_id="object-raw-data", time_policy="preserve"), output)
    context = read_json(output / "wire/part1/context/002.json")
    alert = read_json(output / "wire/part1/alerts/001.json")
    assert context["event_id"] == context["ocsf_event"]["raw_data"]["uid"] == alert["raw_event"]["ocsf_event"]["raw_data"]["uid"]
    assert original == snapshot(materials)

