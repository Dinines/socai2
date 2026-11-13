"""Case-scoped comment writes and reads, with no execution or evidence effects."""
from uuid import uuid5

from sqlalchemy import func, insert, select, update

from app.models.socai2 import Comments

from .baseline_store import C, StoreError, digest
from .case_comment_contracts import CaseCommentPage, CaseCommentView
from .case_contracts import project
from .case_service import CaseService

COMMENTS = Comments.__table__
ACTION = "case_comment_created"


class CaseCommentService(CaseService):
    async def create(self, tenant_id, case_id, request, *, actor):
        intent = digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json")})
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            case = await store.case(case_id)
            prior = await store.receipt(case_id, request.operation_key, ACTION)
            if prior:
                if prior["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return CaseCommentView.model_validate(prior["outcome"])
            now = await store.now()
            identity = uuid5(case_id, "socai2.comment:" + str(request.operation_key))
            row = (await store.db.execute(insert(COMMENTS).values(
                id=identity, tenant_id=tenant_id, case_id=case_id, body=request.body,
                author_id=actor.user_id, author_name_snapshot=actor.name, created_at=now,
            ).returning(COMMENTS))).mappings().one()
            out = project(CaseCommentView, row)
            await store.db.execute(update(C).where(*store.where(C, C.c.id == case_id)).values(
                row_version=C.c.row_version + 1, business_updated_at=now))
            await store.event(case_id, request.operation_key, actor.snapshot(), ACTION,
                {"request_hash": intent, "outcome": out.model_dump(mode="json")},
                [("case_id", case_id, {"row_version": case["row_version"]},
                  {"row_version": case["row_version"] + 1}),
                 ("comment_id", identity, None, out.model_dump(mode="json"))])
            return out

    async def list(self, tenant_id, case_id, *, limit=20, offset=0):
        if not 1 <= limit <= 100 or not 0 <= offset <= 100000:
            raise StoreError("invalid_comment_page", 422)
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            scope = store.where(COMMENTS, COMMENTS.c.case_id == case_id)
            total = (await store.db.execute(select(func.count()).select_from(COMMENTS)
                .where(*scope))).scalar_one()
            rows = (await store.db.execute(select(COMMENTS).where(*scope)
                .order_by(COMMENTS.c.created_at, COMMENTS.c.id).offset(offset).limit(limit))).mappings().all()
            return CaseCommentPage(items=[project(CaseCommentView, row) for row in rows], total=total,
                next_offset=offset + len(rows) if offset + len(rows) < total else None,
                observed_at=await store.now())
