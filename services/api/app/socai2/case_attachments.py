"""Append/read external file references, without fetching or analyzing bytes."""
from uuid import uuid5

from sqlalchemy import func, insert, select, update

from .baseline_store import C, F, StoreError, digest
from .case_attachment_contracts import CaseAttachmentPage, CaseAttachmentView
from .case_service import CaseService

SCHEMA = "socai2.case-attachment-reference.v1"
PREFIX = "business-backend-file:"
ACTION = "case_attachment_linked"


def view(row):
    return CaseAttachmentView(id=row["id"], case_id=row["case_id"],
        file_id=row["blob_ref"][len(PREFIX):], file_name=row["file_name"],
        mime_type=row["mime_type"], size_bytes=row["size_bytes"], sha256=row["sha256"],
        created_by=row["created_by"], created_at=row["captured_at"],
        file_owner="business_backend", availability="managed_by_backend")


class CaseAttachmentService(CaseService):
    @staticmethod
    def scope(store, case_id):
        return store.where(F, F.c.case_id == case_id, F.c.kind == "attachment",
            F.c.schema_version == SCHEMA, F.c.run_id.is_(None))

    async def create(self, tenant_id, case_id, request, *, actor):
        intent = digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json")})
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            case = await store.case(case_id)
            prior = await store.receipt(case_id, request.operation_key, ACTION)
            if prior:
                if prior["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return CaseAttachmentView.model_validate(prior["outcome"])
            reference = PREFIX + request.file_id
            if await store.one(select(F.c.id).where(*self.scope(store, case_id), F.c.blob_ref == reference)):
                raise StoreError("attachment_already_linked")
            now = await store.now()
            identity = uuid5(case_id, "socai2.attachment:" + str(request.operation_key))
            row = (await store.db.execute(insert(F).values(
                id=identity, tenant_id=tenant_id, case_id=case_id, kind="attachment", schema_version=SCHEMA,
                blob_ref=reference, file_name=request.file_name, mime_type=request.mime_type,
                size_bytes=request.size_bytes, sha256=request.sha256, captured_at=now,
                material_state="complete", source_refs=[], created_by=actor.user_id,
                retention={"original_size_bytes": request.size_bytes, "original_sha256": request.sha256,
                    "retained_size_bytes": None, "retained_sha256": None, "truncated": False,
                    "reason": "business_backend_reference_only", "omitted_paths": []},
            ).returning(F))).mappings().one()
            out = view(row)
            await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id)).values(
                row_version=C.c.row_version + 1, business_updated_at=now))
            await store.event(case_id, request.operation_key, actor.snapshot(), ACTION,
                {"request_hash": intent, "outcome": out.model_dump(mode="json")},
                [("case_id", case_id, {"row_version": case["row_version"]},
                  {"row_version": case["row_version"] + 1})])
            return out

    async def list(self, tenant_id, case_id, *, limit=20, offset=0):
        if not 1 <= limit <= 100 or not 0 <= offset <= 100000:
            raise StoreError("invalid_attachment_page", 422)
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            scope = self.scope(store, case_id)
            total = (await store.db.execute(select(func.count()).select_from(F).where(*scope))).scalar_one()
            rows = (await store.db.execute(select(F).where(*scope)
                .order_by(F.c.captured_at, F.c.id).offset(offset).limit(limit))).mappings().all()
            return CaseAttachmentPage(items=[view(row) for row in rows], total=total,
                next_offset=offset + len(rows) if offset + len(rows) < total else None,
                observed_at=await store.now())

    async def read(self, tenant_id, case_id, attachment_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            row = await store.one(select(F).where(*self.scope(store, case_id), F.c.id == attachment_id))
            if row is None:
                raise StoreError("case_attachment_not_found", 404)
            return view(row)
