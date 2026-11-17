"""Complete read-only Run records. No HTTP, executor or scheduler dependency."""
import base64
import binascii
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.exc import DBAPIError

from app.models import socai2 as m

from .baseline_service import BaselineService
from .baseline_store import StoreError, digest

R, S, F = (x.__table__ for x in (m.Runs, m.RunSteps, m.Artifacts))
STEP_FIELDS = ("id", "run_id", "seq", "parent_step_id", "retry_of_step_id", "stage_code", "kind", "name",
               "state", "provider", "implementation_version", "question_id", "started_at", "ended_at",
               "actual_args", "returned_rows", "error", "usage", "input_artifact_id", "output_artifact_id",
               "reused_artifact_id")
ARTIFACT_FIELDS = ("id", "run_id", "step_id", "kind", "schema_version", "mime_type",
                   "file_name", "size_bytes", "sha256", "captured_at", "material_state")
SUBJECT_FIELDS = ("alert_id", "incident_id", "case_id")


@dataclass(frozen=True)
class RunRecordLimits:
    default_limit: int
    max_limit: int

    @classmethod
    def load(cls):
        try:
            path = Path(os.environ["SOCAI2_RUN_RECORDS_CONFIG_FILE"])
            if not path.is_absolute():
                raise ValueError("explicit absolute profile path required")
            values = json.loads(path.read_text())
            if set(values) != {"default_limit", "max_limit"} or any(
                type(v) is not int or v < 1 for v in values.values()
            ) or values["default_limit"] > values["max_limit"]:
                raise ValueError("invalid limits")
            return cls(**values)
        except (KeyError, OSError, ValueError, TypeError):
            raise StoreError("service_unavailable", 503) from None

    def page_size(self, requested):
        value = self.default_limit if requested is None else requested
        if type(value) is not int or not 1 <= value <= self.max_limit:
            raise StoreError("invalid_input", 422)
        return value


def subject(row):
    for field in SUBJECT_FIELDS:
        if row[field] is not None:
            return {"subject_type": field[:-3], "subject_id": row[field]}
    raise StoreError("service_unavailable", 503)


def cursor_point(cursor, fingerprint, directory):
    if cursor is None:
        return None
    try:
        if not cursor or len(cursor) > 4096:
            raise ValueError("cursor length")
        point = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if set(point) != {"filter", "at", "id"} or point["filter"] != fingerprint:
            raise ValueError("cursor scope")
        identity = UUID(point["id"])
        at = point["at"]
        if directory == "steps":
            if type(at) is not int or at < 1 or at > 9223372036854775807:
                raise ValueError("sequence")
        else:
            at = datetime.fromisoformat(at)
            if at.tzinfo is None:
                raise ValueError("timezone required")
        return at, identity
    except (ValueError, TypeError, KeyError, AttributeError, binascii.Error):
        raise StoreError("invalid_cursor", 422) from None


def make_cursor(fingerprint, row, order):
    value = row[order]
    point = {"filter": fingerprint, "at": value.isoformat() if isinstance(value, datetime) else value,
             "id": str(row["id"])}
    return base64.urlsafe_b64encode(json.dumps(point).encode()).decode()


class RunRecordService(BaselineService):
    def __init__(self, sessions, *, limits=None):
        super().__init__(sessions)
        self.limits = limits if limits is not None else RunRecordLimits.load()

    async def _run(self, store, run_id):
        row = await store.one(select(R).where(*store.where(R, R.c.id == run_id)))
        if row is None:
            raise StoreError("run_not_found", 404)
        return row

    async def _step(self, store, run_id, step_id):
        row = await store.one(select(*(S.c[k] for k in STEP_FIELDS)).where(
            *store.where(S, S.c.run_id == run_id, S.c.id == step_id)))
        if row is None:
            raise StoreError("step_not_found", 404)
        return row

    async def _steps(self, store, rows):
        roles = ("input", "output", "reused")
        ids = {row[role + "_artifact_id"] for row in rows for role in roles
               if row[role + "_artifact_id"] is not None}
        refs = {}
        if ids:
            # The source Run is authoritative, including cross-Run reuse.
            query = select(F.c.id, F.c.run_id, *(F.c[k] for k in SUBJECT_FIELDS),
                           *(R.c[k].label("run_" + k) for k in SUBJECT_FIELDS)).select_from(
                F.outerjoin(R, (R.c.id == F.c.run_id) & (R.c.tenant_id == F.c.tenant_id))
            ).where(*store.where(F, F.c.id.in_(ids)))
            for row in (await store.db.execute(query)).mappings():
                source = {k: row["run_" + k] for k in SUBJECT_FIELDS} if row["run_id"] else row
                refs[row["id"]] = {"artifact_id": row["id"], "run_id": row["run_id"], **subject(source)}
        return [{**dict(row), "artifact_refs": [
            {"role": role, **refs[row[role + "_artifact_id"]]}
            for role in roles if row[role + "_artifact_id"] in refs]} for row in rows]

    async def step(self, tenant, run_id, step_id):
        try:
            async with self.transaction(tenant, readonly=True) as store:
                await self._run(store, run_id)
                row = await self._step(store, run_id, step_id)
                return (await self._steps(store, [row]))[0]
        except DBAPIError:
            raise StoreError("service_unavailable", 503) from None

    async def page(self, tenant, run_id, directory, *, limit=None, cursor=None, kind=None, step_id=None):
        if directory not in {"steps", "artifacts"} or (directory == "steps" and step_id is not None) or (
            directory == "artifacts" and kind is not None
        ):
            raise StoreError("invalid_input", 422)
        size = self.limits.page_size(limit)
        fingerprint = digest({"tenant": str(tenant), "run": str(run_id), "directory": directory,
                              "kind": kind, "step_id": str(step_id) if step_id else None,
                              "order": "seq,id:asc" if directory == "steps" else "captured_at,id:asc"})
        point = cursor_point(cursor, fingerprint, directory)
        table, fields, order = (S, STEP_FIELDS, "seq") if directory == "steps" else (F, ARTIFACT_FIELDS, "captured_at")
        try:
            async with self.transaction(tenant, readonly=True) as store:
                run = await self._run(store, run_id)
                filters = list(store.where(table, table.c.run_id == run_id))
                if kind is not None:
                    filters.append(S.c.kind == kind)
                if step_id is not None:
                    step = await self._step(store, run_id, step_id)
                    ids = [step[k] for k in ("input_artifact_id", "output_artifact_id", "reused_artifact_id") if step[k]]
                    filters.append(or_(F.c.step_id == step_id, F.c.id.in_(ids)))
                total = (await store.db.execute(select(func.count()).select_from(table).where(*filters))).scalar_one()
                if point:
                    filters.append(tuple_(table.c[order], table.c.id) > point)
                rows = list((await store.db.execute(select(*(table.c[k] for k in fields)).where(*filters)
                    .order_by(table.c[order], table.c.id).limit(size + 1))).mappings())
                more = len(rows) > size
                rows = rows[:size]
                items = await self._steps(store, rows) if directory == "steps" else [dict(row) for row in rows]
                return {"run_id": run_id, **subject(run), "items": items, "total": total,
                        "next_cursor": make_cursor(fingerprint, rows[-1], order) if more else None,
                        "observed_at": await store.now()}
        except DBAPIError:
            raise StoreError("service_unavailable", 503) from None
