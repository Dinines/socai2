"""Read the current Case scope for the information page."""
from sqlalchemy import and_, column, func, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from .baseline_store import StoreError
from .case_story_relations import (
    M,
    StoryRelations,
    array_or_empty,
    explicit_run_sources,
)


def tactic_counts(scope):
    members = scope.members
    tags = func.jsonb_array_elements(array_or_empty(M.c.detection["tactics"])).table_valued(
        column("value", JSONB),
    ).lateral()
    label = tags.c.value[()].astext
    return select(label.label("label"), func.count(func.distinct(members.c.id)).label("alert_count")).select_from(
        members.join(M, and_(M.c.alert_id == members.c.id, M.c.id == members.c.latest_material_id)).join(tags, true()),
    ).where(*scope.store.where(M), func.jsonb_typeof(tags.c.value) == "string").group_by(label).order_by(label)


async def read_info_summary(service, tenant_id, case_id):
    try:
        async with service.transaction(tenant_id, readonly=True) as store:
            case_row = await store.case(case_id, lock=False)
            scope = StoryRelations(store, case_id, await explicit_run_sources(store, case_row))
            objects, members = scope.objects, scope.members
            keys = (objects.c.namespace, objects.c.object_type, objects.c.object_key)
            groups = select(*keys).distinct().subquery()
            stats = (await store.db.execute(select(
                func.min(members.c.event_time).label("activity_time_from"),
                func.max(members.c.event_time).label("activity_time_to"),
                select(func.count()).select_from(groups).scalar_subquery().label("member_object_count"),
                scope.missing_material().scalar_subquery().label("members_without_current_material_count"),
            ).select_from(members))).mappings().one()
            preview = (await store.db.execute(select(
                objects.c.id.label("object_id"), *keys, objects.c.raw_value,
                objects.c.alert_id, objects.c.material_id, objects.c.source_path,
            ).distinct(*keys).order_by(*keys, objects.c.id).limit(4))).mappings()
            tactics = (await store.db.execute(tactic_counts(scope))).mappings()
            return {
                "case_id": case_id,
                "scope_revision": case_row["scope_revision"],
                "observed_at": await store.now(),
                **stats,
                "object_preview": [dict(row) for row in preview],
                "tactics": [dict(row) for row in tactics if row["label"].strip()],
                "investigation_count": await scope.investigation_count(),
            }
    except DBAPIError:
        raise StoreError("service_unavailable", 503) from None
