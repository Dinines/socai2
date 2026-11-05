"""Real isolated PG for C4 transactions; ClickHouse responses are substitutes."""
import asyncio
import copy
import json
import traceback
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_evidence as c4
from app.socai2 import baseline_evidence_tools as tools
from app.socai2 import baseline_semantics as semantics
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import RM, A, C, F, R, StoreError
from jsonschema import Draft202012Validator, FormatChecker
from socai2_test_model_view import model_data
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic C4 reviewer")
CONTRACTS = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))


def original(host="fixture-host"):
    return {"class_uid": 1007, "device": {"name": host}, "process": {"pid": 4209,
        "name": "worker", "cmd_line": "worker --synthetic", "session_uid": "process-session",
        "parent_process": {"pid": 20, "name": "launcher", "cmd_line": "launcher --test"}},
        "src_endpoint": {"ip": "192.0.2.1", "port": 0, "hostname": host},
        "dst_endpoint": {"ip": "198.51.100.2", "port": 443, "hostname": "test.invalid"},
        "protocol": "TCP", "activity": {"action": "connect", "outcome": "success",
            "session": {"id": "session-a", "key": "vendor-session", "key_kind": "vendor_session"}}}


class SyntheticLake:
    def __init__(self, count=1, hook=None, enabled=True, mutate=None):
        self.count, self.hook, self.enabled, self.mutate = count, hook, enabled, mutate
        self.calls, self.arguments, self.query_ids = 0, [], []

    def configured(self):
        return self.enabled

    async def query(self, args, query_id, timeout):
        assert timeout > 0
        self.calls += 1
        self.arguments.append(copy.deepcopy(args))
        self.query_ids.append(query_id)
        if self.hook:
            await self.hook()
        out = []
        for i in range(self.count):
            host = args["parameters"]["hostname"]
            raw = original(host)
            raw["class_uid"] = tools.TOOLS[args["tool_name"]]
            row = dict.fromkeys(tools.FIELDS, "")
            row.update(event_id=str(uuid4()), event_time=args["scope"]["window_start"],
                class_uid=raw["class_uid"], src_hostname=host, src_port=0, dst_port=443,
                source_ip="::", dest_ip="198.51.100.2", ocsf_json=json.dumps(raw))
            if self.mutate:
                self.mutate(row)
            out.append(row)
        return out


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(query):
        async with service.transaction(T) as store:
            return (await store.db.execute(query)).mappings().all()

    async def alert(store, host, raw=None):
        aid, mid = uuid4(), uuid4()
        await store.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic C4 alert",
            source_namespace="c4-fixture", source_identity_key=str(aid)))
        await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T,
            alert_id=aid, revision=1, ocsf_json=raw or original(host), detection={}, source_scope={},
            material_state="complete", retention={}))
        await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
        await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=T,
            alert_id=aid, material_id=mid, object_key="host:" + host, namespace="fixture",
            object_type="host", object_role="entity", raw_value=host, normalized_value=host,
            source_path="$.ocsf_json.device.name", attributes={}))
        return aid, mid

    async def fixture(calls=4, limit=20, deadline=120, window=True, raw=None):
        cid, host = uuid4(), "synthetic-" + uuid4().hex
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic C4 Case", created_by=USER))
            aid, mid = await alert(store, host, raw)
            out = await store.replace_members(cid, {aid}, expected_revision=0, actor=ACTOR, operation_id=uuid4())
        rid = UUID(out["pending_run_id"])
        async def idle(claim):
            pass
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4(),
            window_start=now - timedelta(minutes=5) if window else None,
            window_end=now + timedelta(minutes=5) if window else None), actor=ACTOR, executor=idle,
            executor_version="synthetic-c4", limits=Limits(max_model_calls=4, max_tool_calls=calls,
                max_tokens=24000, max_rows_per_query=limit, deadline_at=now + timedelta(seconds=deadline),
                policy_version="synthetic-c4"))
        context = await service.read_context(T, cid, rid)
        return cid, rid, aid, mid, host, context.questions[0].id

    async def prepare(cid, rid, tool="process_activity"):
        prepared = await service.prepare_evidence(T, cid, rid)
        binding = next(k for k, b in prepared["catalog"]["bindings"].items() if b["tool_name"] == tool)
        return prepared, binding

    async def reject(code, task):
        try:
            await task
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def test_c4_material_projection_paths_guard_and_conflicts():
        raw = original()
        raw["_socai2_storage"] = {"activity_source": "activity", "envelope_activity": {
            "action": "envelope-action", "session": {"id": "envelope-session"}}}
        raw["process"]["cmd_line"] = 'password="abcdefghijklmnopqrstuv"'
        raw["process"]["parent_process"]["cmd_line"] = "x" * 3000
        raw["actor"] = {"process": {"pid": 70}, "session_uid": "actor-session"}
        projected = semantics.project(raw)
        names = {f["name"] for f in projected["fields"]}
        assert {"process_pid", "parent_pid", "actor_process_pid", "process_session_uid_alt",
                "actor_session_uid_alt", "src_port", "dst_hostname", "action", "session_id"} <= names
        assert "process_command_line" not in names and "parent_command_line" not in names
        assert {o["reason"] for o in projected["omissions"]} >= {"source_guard_blocked", "whole_field_exceeds_budget"}
        actions = [f for f in projected["fields"] if f["name"] == "action"]
        assert len(actions) == 2 and all(f["conflict"] for f in actions)
        assert any(f["value"] == 0 and f["name"] == "src_port" for f in projected["fields"])
        assert semantics.project({"_socai2_storage": {"truncated": True}, "preview": json.dumps(raw)})["state"] == "unavailable"
        assert semantics.project('{"process":{"pid":1,"pid":2}}')["state"] == "unavailable"
        assert semantics.project("raw text") ["state"] == "unavailable"
        assert semantics.scalar_reason("source_ip", 0) == "invalid_ip"
        cid, rid, aid, mid, _, _ = await fixture(raw=raw)
        saved, _ = await prepare(cid, rid)
        assert saved["members"][str(aid)]["material_id"] == str(mid)
        assert saved["members"][str(aid)]["fields"] == projected["fields"]

    async def test_c4_freezes_material_and_scope_and_replays():
        cid, rid, aid, mid, host, _ = await fixture()
        async with service.transaction(T) as store:
            new_mid = uuid4()
            await store.db.execute(insert(m.AlertMaterials.__table__).values(id=new_mid, tenant_id=T,
                alert_id=aid, revision=2, ocsf_json={"process": {"pid": 999}}, detection={},
                source_scope={}, material_state="complete", retention={}))
            await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=new_mid))
            second, _ = await alert(store, "later-host")
        await service.replace_members(T, cid, {aid, second}, expected_revision=1, actor=ACTOR, operation_id=uuid4())
        out, _ = await prepare(cid, rid)
        assert out["members"][str(aid)]["material_id"] == str(mid) and str(second) not in out["members"]
        assert {b["hostname"] for b in out["catalog"]["bindings"].values()} == {host}
        assert out == await service.prepare_evidence(T, cid, rid)
        assert (await rows(select(RM).where(RM.c.run_id == rid)))[0]["read_state"] == "read"
        assert (await rows(select(RM).where(RM.c.run_id == rid)))[0]["analysis_state"] == "not_analyzed"
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "running"

    async def test_c4_real_ledger_query_contract_view_and_no_adoption():
        cid, rid, aid, _, _, q = await fixture()
        prepared, bid = await prepare(cid, rid)
        gateway = SyntheticLake()
        out = await service.query_evidence(T, cid, rid, bid, q, gateway=gateway)
        assert out["result"]["returned_rows"] == 1 and gateway.calls == 1
        assert out["result"]["actual_args"]["parameters"]["query_id"] == gateway.query_ids[0]
        for schema, data in [("tool_exchange", out["result"]), ("tool_args", out["result"]["actual_args"])]:
            Draft202012Validator({**CONTRACTS, "$ref": "#/$defs/" + schema}, format_checker=FormatChecker()).validate(data)
        assert out == await service.query_evidence(T, cid, rid, bid, q, gateway=gateway)
        assert gateway.calls == 1
        view = await service.prepare_evidence_view(T, cid, rid, q)
        assert view["ready"] and view["bytes"] <= 8192
        content = model_data(view["messages"][1]["content"])
        assert any(i["name"] == "process_pid" and i["value"] == 4209 for i in content["items"])
        assert {s["ref"]["id"] for s in view["source_map"].values()} >= {
            prepared["artifact_id"], out["projection_id"]}
        assert str(aid) in content["coverage"] and view["source_map"]
        assert view == await service.prepare_evidence_view(T, cid, rid, q)
        assert (await rows(select(C).where(C.c.id == cid)))[0]["current_assessment_id"] is None
        assert not await rows(select(m.Results.__table__).where(m.Results.source_run_id == rid))
        artifacts = await rows(select(F).where(F.c.run_id == rid, F.c.schema_version == c4.SCHEMA))
        for a in artifacts:
            assert a["sha256"] == c4.digest(a["content_json"])
        assert c4.citation_roles(out["result"]) == {} and c4.citation_roles(prepared)

    async def test_c4_concurrent_claim_is_committed_before_dispatch():
        cid, rid, _, _, _, q = await fixture()
        _, bid = await prepare(cid, rid)
        entered, release = asyncio.Event(), asyncio.Event()
        async def hold():
            active = await rows(select(c4.S).where(c4.S.c.run_id == rid, c4.S.c.stage_code == "C4.query"))
            assert len(active) == 1 and active[0]["state"] == "running" and active[0]["input_artifact_id"]
            entered.set()
            await release.wait()
        gateway = SyntheticLake(hook=hold)
        task = asyncio.create_task(service.query_evidence(T, cid, rid, bid, q, gateway=gateway))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            await reject("evidence_query_already_claimed", service.query_evidence(T, cid, rid, bid, q, gateway=gateway))
            _, other = await prepare(cid, rid, "network_connections")
            await reject("baseline_step_in_progress", service.query_evidence(T, cid, rid, other, q, gateway=gateway))
        finally:
            release.set()
            await task
        assert gateway.calls == 1

    async def test_c4_budget_missing_window_and_source_skip():
        for params, enabled, why in [({"calls": 0}, True, "tool_budget_exhausted"),
            ({"window": False}, True, "query_window_not_defined"),
            ({"deadline": 0}, True, "insufficient_query_time"), ({}, False, "lake_not_configured")]:
            cid, rid, _, _, _, q = await fixture(**params)
            _, bid = await prepare(cid, rid)
            gateway = SyntheticLake(enabled=enabled)
            result = await service.query_evidence(T, cid, rid, bid, q, gateway=gateway)
            assert result["result"]["state"] == "skipped" and result["result"]["rows"] is None
            assert result["result"]["returned_rows"] is None and result["result"]["error"]["code"] == why
            assert gateway.calls == 0
        cid, rid, _, _, _, q = await fixture(calls=1)
        _, bid = await prepare(cid, rid)
        async with service.transaction(T) as store:
            await store.db.execute(insert(c4.S).values(id=uuid4(), tenant_id=T, run_id=rid,
                seq=2, kind="tool", stage_code="C2", name="synthetic previous budget usage", state="failed"))
        gateway = SyntheticLake()
        result = await service.query_evidence(T, cid, rid, bid, q, gateway=gateway)
        assert result["result"]["error"]["code"] == "tool_budget_exhausted" and gateway.calls == 0

    async def test_c4_empty_truncated_and_storage_omission_are_distinct():
        for count, mutate, expected, truncated in [(0, None, 0, False), (2, None, 1, True),
            (1, lambda row: row.update(ocsf_json=json.dumps({"large": "x" * 70000})), 0, True)]:
            cid, rid, _, _, _, q = await fixture(limit=1)
            _, bid = await prepare(cid, rid)
            result = await service.query_evidence(T, cid, rid, bid, q, gateway=SyntheticLake(count, mutate=mutate))
            assert result["result"]["returned_rows"] == expected and result["result"]["truncated"] == truncated
            assert result["projection"]["observed_rows_in_bounded_fetch"] == count
            assert "empty_query_is_not_counterevidence" in result["projection"]["limitations"]
            if count and not expected:
                assert "retained_row_bytes_limit" in result["projection"]["omissions"]

    async def test_c4_cancel_and_bad_scope_hold_unknown_slot():
        for mode in ("cancel", "bad_scope", "timeout"):
            cid, rid, _, _, _, q = await fixture()
            _, bid = await prepare(cid, rid)
            async def fail(mode=mode):
                if mode == "cancel":
                    raise asyncio.CancelledError()
                if mode == "timeout":
                    raise TimeoutError("synthetic unknown CH completion")
            gateway = SyntheticLake(hook=fail, mutate=(lambda row: row.update(src_hostname="outside")) if mode == "bad_scope" else None)
            try:
                await service.query_evidence(T, cid, rid, bid, q, gateway=gateway)
            except (asyncio.CancelledError, TimeoutError, ValueError):
                pass
            else:
                raise AssertionError("expected uncertain execution")
            assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "unknown"
            assert (await rows(select(c4.S).where(c4.S.c.run_id == rid, c4.S.c.kind == "tool")))[0]["state"] == "unknown"
            await reject("evidence_query_already_claimed", service.query_evidence(T, cid, rid, bid, q, gateway=gateway))
            assert gateway.calls == 1

    async def test_c4_binding_question_tenant_and_reference_guards():
        cid, rid, _, _, _, q = await fixture()
        _, bid = await prepare(cid, rid)
        gateway = SyntheticLake()
        await reject("tool_binding_outside_frozen_scope", service.query_evidence(T, cid, rid, "fake", q, gateway=gateway))
        await reject("question_outside_frozen_scope", service.query_evidence(T, cid, rid, bid, "fake", gateway=gateway))
        await reject("case_not_found", service.prepare_evidence(OTHER, cid, rid))
        assert not gateway.calls
        view = await service.prepare_evidence_view(T, cid, rid, q)
        assert c4.citation_roles(view) == {}

    async def test_c4_lake_adapter_fixed_sql_and_new_columns():
        cid, rid, _, _, _, _ = await fixture()
        prepared, bid = await prepare(cid, rid)
        binding = prepared["catalog"]["bindings"][bid]
        args = {"tool_name": binding["tool_name"], "contract_version": tools.VERSION,
            "scope": binding["scope"], "limit": 2,
            "parameters": {"tenant_id": str(T), "hostname": "x' OR 1=1 --"}}
        sql, params = tools.query_sql(args)
        assert "x'" not in sql and params["hostname"] == "x' OR 1=1 --"
        assert params["fetch_limit"] == 3 and "PARTITION BY tenant_id,event_time,class_uid,event_id" in sql
        assert sql.index("source_rank=1") < sql.index("LIMIT")
        assert {"ocsf_json", "src_port", "dst_hostname", "action", "outcome", "session_id"} <= set(tools.FIELDS)
        from app.db.clickhouse import LakeQueryResult
        captured = []
        async def substitute(statement, **kwargs):
            captured.append((statement, kwargs))
            return LakeQueryResult(columns=list(tools.FIELDS), rows=[], row_count=0, elapsed_ms=1)
        with patch("app.db.clickhouse.execute_lake_query", substitute):
            assert await tools.LakeGateway().query(args, "synthetic-query", 2) == []
        assert captured[0][1]["query_id"] == "synthetic-query" and captured[0][1]["timeout_seconds"] == 2
        try:
            await tools.LakeGateway().query(args, "not-dispatched", 0.1)
        except ValueError:
            pass
        else:
            raise AssertionError("subsecond server timeout must not become unlimited")

    async def test_c4_request_commit_failure_does_not_dispatch():
        cid, rid, _, _, _, q = await fixture()
        _, bid = await prepare(cid, rid)
        gateway, inserted = SyntheticLake(), []
        original_artifact = c4.BaselineEvidence.artifact
        async def fail_commit(self, store, run, payload, **kwargs):
            identity = await original_artifact(self, store, run, payload, **kwargs)
            if kwargs.get("kind") == "tool_request":
                await store.db.execute(insert(c4.S).values(id=uuid4(), tenant_id=T, run_id=rid,
                    seq=10000000, parent_step_id=uuid4(), kind="tool", stage_code="C4.query",
                    state="planned", name="synthetic_deferred_fk_failure"))
                inserted.append(True)
            return identity
        with patch.object(c4.BaselineEvidence, "artifact", fail_commit):
            try:
                await service.query_evidence(T, cid, rid, bid, q, gateway=gateway)
            except IntegrityError as exc:
                assert getattr(exc.orig.__cause__, "constraint_name", None) in {
                    "run_steps_parent_step_id_fk", "run_steps_parent_step_id_scope_fk"}
            else:
                raise AssertionError("expected deferred FK failure on commit")
        assert inserted == [True] and gateway.calls == 0
        assert not await rows(select(c4.S).where(c4.S.c.run_id == rid, c4.S.c.kind == "tool"))
        assert not await rows(select(F).where(F.c.run_id == rid, F.c.kind == "tool_request"))
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "running"

    async def test_c4_view_budget_defaults_and_publication_citation_paths():
        raw = original()
        raw["process"]["cmd_line"] = "synthetic " + "x" * 1800
        raw["process"]["parent_process"]["cmd_line"] = "synthetic " + "y" * 1800
        cid, rid, aid, _, _, q = await fixture(raw=raw)
        prepared, bid = await prepare(cid, rid)
        def defaults(row):
            row.update(ocsf_json="{}", src_port=0, dst_port=0, source_ip="::", dest_ip="::",
                       action="observed-action", session_id="explicit-session")
        query = await service.query_evidence(T, cid, rid, bid, q, gateway=SyntheticLake(mutate=defaults))
        fields = query["projection"]["rows"][0]["semantics"]["fields"]
        assert not {f["name"] for f in fields} & {"src_port", "dst_port", "source_ip", "dest_ip"}
        assert {"action", "session_id"} <= {f["name"] for f in fields}
        view = await service.prepare_evidence_view(T, cid, rid, q)
        assert view["ready"] and view["bytes"] <= 8192 and view["omissions"]
        async with service.transaction(T) as store:
            run = await store.run(cid, rid)
            members = (await store.db.execute(select(RM).where(RM.c.run_id == rid))).mappings().all()
            path = next(iter(c4.citation_roles(prepared)))
            good = c4.reference("artifact", UUID(prepared["artifact_id"]), "observation", path)
            publication = SimpleNamespace(model_dump=lambda **_: {"evidence": [good]},
                                          graph_artifact_id=None, report_artifact_id=None)
            await store.validate_result_refs(run, members, publication)
            for identity, wrong_path, role in [(query["artifact_id"], "$.rows.0", "observation"),
                (view["artifact_id"], None, "observation"), (prepared["artifact_id"], f"$.members.{aid}", "observation"),
                (prepared["artifact_id"], path, "prior_analysis")]:
                ref = c4.reference("artifact", UUID(identity), role, wrong_path)
                publication.model_dump = lambda ref=ref, **_: {"evidence": [ref]}
                await reject("context_citation_path_or_role_invalid", store.validate_result_refs(run, members, publication))

    checks = [test_c4_material_projection_paths_guard_and_conflicts,
        test_c4_freezes_material_and_scope_and_replays, test_c4_real_ledger_query_contract_view_and_no_adoption,
        test_c4_concurrent_claim_is_committed_before_dispatch, test_c4_budget_missing_window_and_source_skip,
        test_c4_empty_truncated_and_storage_omission_are_distinct, test_c4_cancel_and_bad_scope_hold_unknown_slot,
        test_c4_binding_question_tenant_and_reference_guards, test_c4_lake_adapter_fixed_sql_and_new_columns,
        test_c4_request_commit_failure_does_not_dispatch, test_c4_view_budget_defaults_and_publication_citation_paths]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 100)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain each original failure
            record(check.__name__, False, traceback.format_exc())
