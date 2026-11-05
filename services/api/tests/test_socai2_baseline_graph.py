"""C5 graph provenance, atomicity and reanalysis on the isolated synthetic PG."""
import asyncio
import copy
import importlib.util
import json
import traceback
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from app.models import socai2 as m
from app.socai2 import baseline_graph_projection as graph
from app.socai2.baseline_context import reference
from app.socai2.baseline_contracts import Actor, Limits, Start
from app.socai2.baseline_graph import BaselineGraph
from app.socai2.baseline_service import BaselineService
from app.socai2.baseline_store import RM, A, C, F, R, StoreError, digest, encoded
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker


def helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lake = helper("test_socai2_baseline_evidence")
analysis = helper("test_socai2_baseline_analysis")
T, OTHER, USER = UUID(int=1), UUID(int=2), UUID(int=3)
ACTOR = Actor(user_id=USER, name="synthetic C5 reviewer")
CONTRACTS = json.loads((Path(__file__).parents[1] / "app/socai2/contracts.schema.json").read_text("utf-8"))
S = m.RunSteps.__table__


async def run_checks(engine, record, only=None):
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))

    async def rows(query):
        async with service.transaction(T) as store:
            return (await store.db.execute(query)).mappings().all()

    async def fixture(count=1, *, raw=None, different_namespace=False):
        cid, host, aids = uuid4(), "synthetic-" + uuid4().hex, []
        async with service.transaction(T) as store:
            now = await store.now()
            await store.db.execute(insert(C).values(id=cid, tenant_id=T, title="synthetic C5 Case", created_by=USER))
            for i in range(count):
                aid, mid = uuid4(), uuid4()
                aids.append(aid)
                await store.db.execute(insert(A).values(id=aid, tenant_id=T, title="synthetic C5 alert",
                    event_time=now, event_time_source="source", source_namespace="graph-fixture", source_identity_key=str(aid)))
                await store.db.execute(insert(m.AlertMaterials.__table__).values(id=mid, tenant_id=T, alert_id=aid,
                    revision=1, ocsf_json=raw if raw is not None else lake.original(host), detection={}, source_scope={},
                    material_state="complete", retention={}))
                await store.db.execute(update(A).where(A.c.id == aid).values(latest_material_id=mid))
                await store.db.execute(insert(m.AlertObjects.__table__).values(id=uuid4(), tenant_id=T, alert_id=aid,
                    material_id=mid, object_type="host", object_role="entity", object_key="host:" + host,
                    namespace="other" if different_namespace and i == count - 1 else "fixture",
                    raw_value=host, normalized_value=host, source_path="$.ocsf_json.device.name", attributes={}))
            out = await store.replace_members(cid, set(aids), expected_revision=0, actor=ACTOR, operation_id=uuid4())
        rid = UUID(out["pending_run_id"])
        async def idle(claim):
            pass
        await service.start(T, cid, rid, Start(expected_scope_revision=1, operation_key=uuid4(),
            window_start=now - timedelta(minutes=5), window_end=now + timedelta(minutes=5)), actor=ACTOR,
            executor=idle, executor_version="synthetic-C5", limits=Limits(max_model_calls=4, max_tool_calls=4,
                max_tokens=24000, max_rows_per_query=5, deadline_at=now + timedelta(seconds=120), policy_version="synthetic-C5"))
        return cid, rid, aids

    async def reject(code, task):
        try:
            await task
        except StoreError as exc:
            assert exc.code == code, (exc.code, code)
        else:
            raise AssertionError("expected " + code)

    async def inputs(cid, rid):
        context = await service.read_context(T, cid, rid)
        sources = await rows(select(F).where(F.c.run_id == rid, F.c.kind == "source_snapshot"))
        context_id = next(r["id"] for r in sources if r["schema_version"] == context.schema_version)
        bases = [r for r in sources if r["content_json"].get("type") in {"materials", "query_projection"}]
        return context, context_id, bases

    async def query(cid, rid, gateway, tool="network_connections"):
        prepared = await service.prepare_evidence(T, cid, rid)
        binding = next(k for k, v in prepared["catalog"]["bindings"].items() if v["tool_name"] == tool)
        return await service.query_evidence(T, cid, rid, binding, "member_relationships", gateway=gateway)

    async def test_c5_persisted_graph_contract_sources_and_replay():
        cid, rid, aids = await fixture()
        result = await service.build_graph(T, cid, rid)
        assert result == await service.build_graph(T, cid, rid)
        Draft202012Validator({**CONTRACTS, "$ref": "#/$defs/graph"}, format_checker=FormatChecker()).validate(result["graph"])
        assert result["delivery_state"] == "partial" and set(result["coverage"]) == set(map(str, aids))
        edges = result["graph"]["edges"]
        assert {e["relation"] for e in edges} == {"source_reports_object", "reported_parent_process"}
        for e in edges:
            expected = "source_label" if e["strength"] == "candidate" else "observation"
            assert e["source_refs"] and all(r["role"] == expected for r in e["source_refs"])
        assert len(await rows(select(S).where(S.c.run_id == rid, S.c.stage_code == "C5"))) == 1
        artifacts = await rows(select(F).where(F.c.run_id == rid, F.c.schema_version == graph.SCHEMA))
        assert len(artifacts) == 2 and all(digest(r["content_json"]) == r["sha256"] for r in artifacts)
        assert not await rows(select(m.Results.__table__).where(m.Results.source_run_id == rid))
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "running"
        return {"nodes": len(result["graph"]["nodes"]), "edges": len(edges), "graph_id": result["graph_artifact_id"]}

    async def test_c5_namespaces_types_and_record_local_pids_sessions():
        cid, rid, aids = await fixture(3, different_namespace=True)
        out = await service.build_graph(T, cid, rid)
        hosts = [n for n in out["graph"]["nodes"] if n["type"] == "host"]
        assert len(hosts) == 2 and sorted(len(n["alert_ids"]) for n in hosts) == [1, 2]
        processes = [n for n in out["graph"]["nodes"] if n["type"] == "process"]
        assert len(processes) == 6 and all(len(n["alert_ids"]) == 1 for n in processes)
        assert len({n["id"] for n in processes if n["label"] == "4209"}) == 3
        sessions = [r for r in out["records"] if r["kind"] == "record_session"]
        assert len(sessions) == 9 and len({r["node_ids"][0] for r in sessions}) == 9
        ctx, context_id, bases = await inputs(cid, rid)
        obj = copy.deepcopy(ctx.alerts[str(aids[0])].objects[0])
        obj.update(id=str(uuid4()), object_type="user")
        ctx.alerts[str(aids[0])].objects.append(obj)
        changed, _ = graph.build(ctx, context_id, bases)
        assert len([n for n in changed["nodes"] if n["type"] == "user"]) == 1

    async def test_c5_network_direction_outcome_and_field_conflicts():
        raw = lake.original()
        raw["class_uid"], raw["activity"]["outcome"] = 4001, "failure"
        cid, rid, _ = await fixture(raw=raw)
        out = await service.build_graph(T, cid, rid)
        edge = next(e for e in out["graph"]["edges"] if e["relation"] == "reported_network_activity")
        nodes = {n["id"]: n for n in out["graph"]["nodes"]}
        assert nodes[edge["from"]]["label"] == "192.0.2.1" and nodes[edge["to"]]["label"] == "198.51.100.2"
        fields = next(r["fields"] for r in out["records"] if r["kind"] == "endpoints")
        assert any(f["name"] == "src_port" and f["value"] == 0 for f in fields)
        assert any(f["name"] == "outcome" and f["value"] == "failure" for f in fields)
        ctx, context_id, bases = await inputs(cid, rid)
        bases = [dict(r, content_json=copy.deepcopy(r["content_json"])) for r in bases]
        for data in bases[0]["content_json"]["members"].values():
            for f in data["fields"]:
                if f["name"] in {"source_ip", "src_hostname", "parent_pid"}:
                    f["conflict"] = True
        projected, detail = graph.build(ctx, context_id, bases)
        assert all(e["strength"] == "candidate" for e in projected["edges"])
        assert detail["omissions"]["conflicting_or_guarded_field_not_used"] == 3

    async def test_c5_query_rows_are_related_not_members_and_empty_is_unknown():
        cid, rid, _ = await fixture()
        first = await service.build_graph(T, cid, rid)
        await query(cid, rid, lake.SyntheticLake(0), "process_activity")
        empty = await service.build_graph(T, cid, rid)
        assert empty["queries"][0]["observed_rows_in_bounded_fetch"] == 0
        assert empty["queries"][0]["tool_name"] == "process_activity"
        assert empty["queries"][0]["scope"]["window_start"] == first["scope"]["window_start"]
        assert empty["graph"] == first["graph"] and empty["graph_artifact_id"] != first["graph_artifact_id"]
        await query(cid, rid, lake.SyntheticLake())
        current = await service.build_graph(T, cid, rid)
        query_records = [r for r in current["records"] if r.get("membership_basis") == "query_binding_only"]
        node_ids = {n for r in query_records for n in r["node_ids"]}
        assert node_ids and all(not n["alert_ids"] for n in current["graph"]["nodes"] if n["id"] in node_ids)
        assert all(r["time_basis"]["origin"] == "query_row_event_time" for r in query_records)
        assert all(r["time_basis"]["event_id"] for r in query_records)
        assert len(await rows(select(S).where(S.c.run_id == rid, S.c.kind == "tool"))) == 2
        assert not await rows(select(S).where(S.c.run_id == rid, S.c.kind == "model"))
        assert (await rows(select(F).where(F.c.id == UUID(first["graph_artifact_id"]))))[0]["content_json"] == first["graph"]

    async def test_c5_concurrent_graph_and_query_preserve_scope():
        cid, rid, aids = await fixture(2)
        a, b = await asyncio.gather(service.build_graph(T, cid, rid), service.build_graph(T, cid, rid))
        assert a == b
        async def while_query():
            # An unchanged snapshot may be read during a query; it cannot be
            # mistaken for a graph of the unfinished query.
            assert await service.build_graph(T, cid, rid) == a
            changed = await service.replace_members(T, cid, {aids[0]}, expected_revision=1,
                actor=ACTOR, operation_id=uuid4())
            assert changed["pending_run_id"] != str(rid)
        await query(cid, rid, lake.SyntheticLake(hook=while_query))
        new = await service.build_graph(T, cid, rid)
        assert new["scope"]["alert_ids"] == a["scope"]["alert_ids"] and len(new["coverage"]) == 2

    async def test_c5_active_step_without_snapshot_and_tenant_denied():
        cid, rid, _ = await fixture()
        async def while_query():
            await reject("baseline_step_in_progress", service.build_graph(T, cid, rid))
        await query(cid, rid, lake.SyntheticLake(hook=while_query))
        await reject("case_not_found", service.build_graph(OTHER, cid, rid))
        assert not await rows(select(S).where(S.c.run_id == rid, S.c.stage_code == "C5"))

    async def test_c5_failed_persist_rolls_back_graph_and_step():
        cid, rid, _ = await fixture()
        original_save = BaselineGraph.save
        async def broken(self, store, run, step, payload, kind, refs=()):
            value = await original_save(self, store, run, step, payload, kind, refs)
            if kind == "source_snapshot":
                raise RuntimeError("synthetic graph failure after both writes")
            return value
        with patch.object(BaselineGraph, "save", broken):
            try:
                await service.build_graph(T, cid, rid)
            except RuntimeError:
                pass
            else:
                raise AssertionError("expected injected rollback")
        assert not await rows(select(F).where(F.c.run_id == rid, F.c.schema_version == graph.SCHEMA))
        assert not await rows(select(S).where(S.c.run_id == rid, S.c.stage_code == "C5"))
        assert (await rows(select(R).where(R.c.id == rid)))[0]["state"] == "running"
        assert (await service.build_graph(T, cid, rid))["state"] == "completed"

    async def test_c5_bounds_no_dangling_edges_and_original_guard():
        cid, rid, aids = await fixture(2)
        await service.prepare_evidence(T, cid, rid)
        ctx, context_id, bases = await inputs(cid, rid)
        ctx.alerts[str(aids[0])].alert["title"] = 'password="abcdefghijklmnopqrstuv"'
        with patch.object(graph, "MAX_NODES", 3):
            result, detail = graph.build(ctx, context_id, bases)
        ids = {n["id"] for n in result["nodes"]}
        assert len(ids) <= 3 and all(e["from"] in ids and e["to"] in ids for e in result["edges"])
        assert detail["omissions"]["whole_relation_bundle_exceeds_graph_limit"] > 0
        assert 'abcdefghijklmnopqrstuv' not in encoded(result).decode()
        assert len(detail["coverage"]) == 2
        with patch.object(graph, "MAX_NODES", 1):
            try:
                graph.build(ctx, context_id, bases)
            except StoreError as exc:
                assert exc.code == "graph_member_anchors_exceed_retention_limit"
            else:
                raise AssertionError("mandatory members must not silently disappear")

    async def test_c5_graph_reanalysis_and_publication_roles():
        cid, rid, _ = await fixture()
        with patch("app.socai2.baseline_enrichment.sources.CONNECTED", frozenset()):
            await service.enrich(T, cid, rid)
        assert (await service.analyze(T, cid, rid, gateway=analysis.SyntheticGateway()))["state"] == "completed"
        graph_result = await service.build_graph(T, cid, rid)
        gateway = analysis.SyntheticGateway()
        result = await service.reanalyze(T, cid, rid, gateway=gateway)
        assert result["state"] == "completed", result
        assert await service.reanalyze(T, cid, rid, gateway=gateway) == result
        refs = [s["ref"] for s in result["source_map"].values() if s["ref"]["id"] == graph_result["graph_artifact_id"]]
        assert refs and all(r["role"] == "prior_analysis" for r in refs)
        assert not await rows(select(m.Results.__table__).where(m.Results.source_run_id == rid))
        async with service.transaction(T) as store:
            run = await store.run(cid, rid)
            members = (await store.db.execute(select(RM).where(RM.c.run_id == rid))).mappings().all()
            good = reference("artifact", graph_result["graph_artifact_id"], "prior_analysis", "$.edges.0")
            publication = SimpleNamespace(model_dump=lambda **_: {"evidence": [good]},
                graph_artifact_id=UUID(graph_result["graph_artifact_id"]), report_artifact_id=None)
            await store.validate_result_refs(run, members, publication)
            good["role"] = "observation"
            await reject("context_citation_path_or_role_invalid", store.validate_result_refs(run, members, publication))

    async def test_c5_stale_graph_excluded_and_only_latest_snapshot_consumed():
        cid, rid, _ = await fixture()
        with patch("app.socai2.baseline_enrichment.sources.CONNECTED", frozenset()):
            await service.enrich(T, cid, rid)
        await service.analyze(T, cid, rid, gateway=analysis.SyntheticGateway())
        old = await service.build_graph(T, cid, rid)
        await query(cid, rid, lake.SyntheticLake(0))
        gateway = analysis.SyntheticGateway()
        stale = await service.reanalyze(T, cid, rid, gateway=gateway)
        assert stale["state"] == "completed", stale
        assert all(s["ref"]["id"] != old["graph_artifact_id"] for s in stale["source_map"].values())
        requests = await rows(select(F).where(F.c.run_id == rid, F.c.kind == "model_request").order_by(F.c.captured_at))
        assert "stale" in encoded(requests[-1]["content_json"]).decode()
        current = await service.build_graph(T, cid, rid)
        new = await service.reanalyze(T, cid, rid, gateway=gateway)
        assert new["state"] == "completed", new
        source_ids = {s["ref"]["id"] for s in new["source_map"].values()}
        assert current["graph_artifact_id"] in source_ids and old["graph_artifact_id"] not in source_ids
        assert new["basis"]["comparison_analysis_artifact_id"] != old["artifact_id"]

    checks = [test_c5_persisted_graph_contract_sources_and_replay, test_c5_namespaces_types_and_record_local_pids_sessions,
        test_c5_network_direction_outcome_and_field_conflicts, test_c5_query_rows_are_related_not_members_and_empty_is_unknown,
        test_c5_concurrent_graph_and_query_preserve_scope, test_c5_active_step_without_snapshot_and_tenant_denied,
        test_c5_failed_persist_rolls_back_graph_and_step, test_c5_bounds_no_dangling_edges_and_original_guard,
        test_c5_graph_reanalysis_and_publication_roles, test_c5_stale_graph_excluded_and_only_latest_snapshot_consumed]
    for check in checks:
        if only is not None and check.__name__ not in only:
            continue
        try:
            detail = await asyncio.wait_for(check(), 180)
            record(check.__name__, True, detail)
        except Exception:  # noqa: BLE001 -- retain original failures
            record(check.__name__, False, traceback.format_exc())
