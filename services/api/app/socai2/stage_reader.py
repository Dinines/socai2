"""Read-only A/I result history, repeatable-read service transactions."""
from uuid import uuid5

from sqlalchemy import and_, or_, select, text

from .baseline_service import BaselineService
from .baseline_store import StoreError, digest, encoded
from .stage_inputs import freshness_sql
from .stage_read_contracts import StageEntry, StagePage, StageRunView
from .stage_results import AS, D, F, R, parent

MAX_CONTENT_BYTES = 131072


class StageReader:
    def __init__(self, store, kind, identity):
        self.store, self.kind, self.identity = store, kind, identity
        self.table, self.key = parent(kind)
        self.result_table = AS if kind == "alert_basic" else D
        self.pointer = "latest_triage_id" if kind == "alert_basic" else "latest_diagnosis_id"

    async def subject(self):
        row = await self.store.one(select(self.table).where(*self.store.where(self.table, self.table.c.id == self.identity)))
        if row is None:
            raise StoreError("stage_subject_not_found", 404)
        return row

    async def run(self, identity):
        row = await self.store.one(select(R).where(*self.store.where(R, R.c.id == identity,
            R.c.kind == self.kind, R.c[self.key] == self.identity)))
        if row is None:
            raise StoreError("stage_run_not_found", 404)
        return row

    async def entry(self, row, subject):
        freshness = (await self.store.db.execute(text("SELECT " + freshness_sql(self.kind, ":subject", ":run")),
            {"tenant": self.store.tenant_id, "subject": self.identity, "run": row["id"]})).scalar_one()
        result = await self.store.one(select(self.result_table).where(*self.store.where(self.result_table,
            self.result_table.c.source_run_id == row["id"], self.result_table.c[self.key] == self.identity)))
        selected = bool(result and result["id"] == subject[self.pointer])
        accepted = bool(result and (self.kind == "alert_basic" or
            (result["diagnosis"] or {}).get("validation_state") == "accepted"))
        explanation = None
        if result and self.kind == "alert_basic":
            art = await self.store.one(select(F).where(*self.store.where(F, F.c.id == uuid5(row["id"], "explanation"),
                F.c.run_id == row["id"], F.c.alert_id == self.identity, F.c.kind == "alert_explanation")))
            if art:
                available, reason = False, "external_or_missing_content"
                body = art["content_json"]
                if body is not None and art["blob_ref"] is None:
                    if art["material_state"] != "complete":
                        reason = "material_" + art["material_state"]
                    elif len(encoded(body)) > MAX_CONTENT_BYTES:
                        reason = "content_exceeds_read_limit"
                    elif digest(body) != art["sha256"] or len(encoded(body)) != art["size_bytes"]:
                        reason = "content_integrity_mismatch"
                    else:
                        available, reason = True, None
                explanation = {"artifact_id": art["id"], "available": available, "reason": reason,
                    "content": body if available else None}
        public_result = None
        if result:
            fields = ("id", "input_material_id", "source_run_id", "verdict", "rationale", "confidence", "score_state",
                      "recommendations", "producer", "actor", "assessed_at") if self.kind == "alert_basic" else (
                      "id", "source_run_id", "revision", "state", "summary", "diagnosis", "open_questions",
                      "input_artifact_id", "source_fingerprint", "producer", "requested_at", "generated_at")
            public_result = {k: result[k] for k in fields}
            if self.kind == "incident_diagnosis":
                public_result["error_code"] = (result["error"] or {}).get("code")
        return StageEntry(run=StageRunView.model_validate({k: row[k] for k in StageRunView.model_fields}),
            freshness=freshness, is_current_pointer=selected,
            valid_for_current_input=selected and accepted and freshness == "current" and row["state"] == "completed",
            result=public_result, explanation=explanation)

    async def page(self, *, limit=20, before_run_id=None):
        if not 1 <= limit <= 50:
            raise StoreError("invalid_stage_history_limit", 422)
        subject = await self.subject()
        current, reason = None, None
        if subject[self.pointer]:
            result = await self.store.one(select(self.result_table).where(*self.store.where(self.result_table,
                self.result_table.c.id == subject[self.pointer], self.result_table.c[self.key] == self.identity)))
            if result and result["source_run_id"]:
                current = await self.entry(await self.run(result["source_run_id"]), subject)
            else:
                reason = "current_pointer_without_verifiable_run"
        q = select(R).where(*self.store.where(R, R.c.kind == self.kind, R.c[self.key] == self.identity))
        if before_run_id:
            before = await self.run(before_run_id)
            q = q.where(or_(R.c.requested_at < before["requested_at"],
                and_(R.c.requested_at == before["requested_at"], R.c.id < before["id"])))
        rows = (await self.store.db.execute(q.order_by(R.c.requested_at.desc(), R.c.id.desc()).limit(limit + 1))).mappings().all()
        entries = [await self.entry(row, subject) for row in rows[:limit]]
        return StagePage(subject_id=self.identity, kind=self.kind, current_pointer_id=subject[self.pointer],
            current=current, current_unavailable_reason=reason, entries=entries,
            next_before_run_id=rows[limit - 1]["id"] if len(rows) > limit else None)


class StageReadService(BaselineService):
    async def read_page(self, tenant, kind, identity, **kwargs):
        async with self.transaction(tenant, readonly=True) as store:
            return await StageReader(store, kind, identity).page(**kwargs)

    async def read_entry(self, tenant, kind, identity, run_id):
        async with self.transaction(tenant, readonly=True) as store:
            reader = StageReader(store, kind, identity)
            subject = await reader.subject()
            return await reader.entry(await reader.run(run_id), subject)
