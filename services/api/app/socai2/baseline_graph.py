"""Atomic C5 snapshots on the same Run, without an external graph dispatch."""
from uuid import UUID, uuid4

from sqlalchemy import insert, select, update

from . import baseline_context as c1
from . import baseline_evidence as c4
from . import baseline_graph_projection as projection
from .baseline_context import reference
from .baseline_enrichment import S
from .baseline_reasoning import ModelSteps
from .baseline_store import F, StoreError, digest


class BaselineGraph(ModelSteps):
    def __init__(self, service):
        super().__init__(service, projection.SCHEMA)

    async def execute(self, tenant_id, case_id, run_id):
        await c4.BaselineEvidence(self.service).prepare(tenant_id, case_id, run_id)
        async with self.service.transaction(tenant_id) as store:
            run = await self.locked(store, case_id, run_id)
            context = await store.read_context(case_id, run_id)
            rows = (await store.db.execute(select(F).where(*store.where(F, F.c.run_id == run_id,
                F.c.kind == "source_snapshot", F.c.schema_version.in_([c1.SCHEMA, c4.SCHEMA]))))
                ).mappings().all()
            if any(digest(r["content_json"]) != r["sha256"] for r in rows):
                raise StoreError("evidence_receipt_invalid")
            context_id = next(r["id"] for r in rows if r["schema_version"] == c1.SCHEMA)
            bases = sorted([r for r in rows if r["content_json"].get("type") in {
                "materials", "query_projection"}], key=lambda r: str(r["id"]))
            key = digest([str(context_id), *[str(r["id"]) for r in bases]])
            prior = await store.one(select(S).where(*store.where(S, S.c.run_id == run_id,
                S.c.stage_code == "C5", S.c.kind == "graph", S.c.name == key)))
            if prior:
                summary = await self.read_artifact(store, run_id, prior["output_artifact_id"])
                graph = await self.read_artifact(store, run_id, UUID(summary["graph_artifact_id"]))
                return {"artifact_id": str(prior["output_artifact_id"]), **summary, "graph": graph}
            if run["state"] != "running":
                raise StoreError("baseline_not_running")
            await self.idle(store, run_id)
            # No source is fetched outside this transaction, so failure rolls
            # back all C5 writes and needs no uncertain-dispatch recovery state.
            graph, detail = projection.build(context, context_id, bases)
            step, now = uuid4(), await store.now()
            inputs = [str(context_id), *[str(r["id"]) for r in bases]]
            refs = [reference("artifact", i, "execution_receipt") for i in inputs]
            await store.db.execute(insert(S).values(id=step, tenant_id=tenant_id, run_id=run_id,
                seq=await self.seq(store, run_id), kind="graph", stage_code="C5", name=key,
                state="running", implementation_version=projection.SCHEMA, started_at=now,
                input_artifact_id=context_id))
            graph_id = await self.save(store, run, step, graph, "alert_graph", refs)
            summary = {"schema_version": projection.SCHEMA, "type": "graph_snapshot", "run_id": str(run_id),
                "scope": context.scope.model_dump(mode="json"), "evidence_set_key": key,
                "input_artifact_ids": inputs, "graph_artifact_id": str(graph_id),
                "state": "completed", "delivery_state": "partial", "captured_at": now.isoformat(), **detail}
            summary_id = await self.save(store, run, step, summary, "source_snapshot", refs)
            await store.db.execute(update(S).where(*store.where(S, S.c.id == step)).values(
                state="completed", ended_at=await store.now(), output_artifact_id=summary_id))
        return {"artifact_id": str(summary_id), **summary, "graph": graph}
