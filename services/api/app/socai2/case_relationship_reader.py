"""Read persisted continuation and derived event intersections without mutations."""
import base64
import binascii
import json
from datetime import timedelta

from sqlalchemy import select, text

from app.models import socai2 as m

from .baseline_store import StoreError, digest
from .case_allocation_contracts import CaseContinuation, RelatedCasePage
from .page_contracts import CaseReceiving


async def continuation(store, case):
    root_id = case['continuation_root_case_id']
    if root_id is None:
        return None
    root = case if root_id == case['id'] else await store.case(root_id, lock=False)
    return CaseContinuation(root_case_id=root_id, previous_case_id=case['previous_case_id'],
        receiving_case_id=root['receiving_case_id'])


async def case_view(store, case):
    from .case_contracts import CaseView, project
    return project(CaseView, case).model_copy(update={'continuation': await continuation(store, case)})


async def receiving_status(store, incident, policy):
    cid = incident['active_case_id']
    if cid is None:
        return CaseReceiving(active_case_id=None, can_receive_automatically=False, reason_code='no_target')
    case = await store.case(cid, lock=False)
    state = m.AnalysisSubjectState.__table__
    last = await store.one(select(state.c.last_normal_completed_at).where(*store.where(state,
        state.c.subject_type == 'case', state.c.subject_id == cid)))
    anchor = (last['last_normal_completed_at'] if last else None) or case['created_at']
    reason = ('closed' if case['handling_status'] == 'resolved' else 'auto_window_expired'
        if await store.now() >= anchor + timedelta(seconds=policy.automatic_window_seconds) else None)
    return CaseReceiving(active_case_id=cid, can_receive_automatically=reason is None, reason_code=reason)


# UNION removes duplicate paths before intersections, grouping and pagination.
RELATED = """WITH sources AS (
 SELECT ci.case_id,ci.incident_id,'explicit'::text AS source FROM socai2.case_incidents ci WHERE ci.tenant_id=:tenant
 UNION
 SELECT ca.case_id,ia.incident_id,'member_alert'::text FROM socai2.case_alerts ca
 JOIN socai2.incident_alerts ia ON ia.tenant_id=ca.tenant_id AND ia.alert_id=ca.alert_id WHERE ca.tenant_id=:tenant
), labels AS (
 SELECT case_id,incident_id,array_agg(source ORDER BY source) AS sources FROM sources GROUP BY case_id,incident_id
), shared AS (
 SELECT other.case_id,jsonb_agg(jsonb_build_object('incident_id',i.id,'title',i.title,
 'current_case_sources',mine.sources,'related_case_sources',other.sources) ORDER BY i.id) AS incidents
 FROM labels mine JOIN labels other ON other.incident_id=mine.incident_id AND other.case_id<>mine.case_id
 JOIN socai2.incidents i ON i.tenant_id=:tenant AND i.id=mine.incident_id
 WHERE mine.case_id=:case GROUP BY other.case_id
), candidates AS (
 SELECT c.id AS case_id,c.title,c.handling_status,c.severity,c.created_at,
 c.continuation_root_case_id,c.previous_case_id,root.receiving_case_id,
 (c.continuation_root_case_id=:root) IS TRUE AS same_chain,coalesce(s.incidents,'[]'::jsonb) AS shared_incidents
 FROM socai2.cases c LEFT JOIN shared s ON s.case_id=c.id
 LEFT JOIN socai2.cases root ON root.tenant_id=c.tenant_id AND root.id=c.continuation_root_case_id
 WHERE c.tenant_id=:tenant AND c.id<>:case AND (c.continuation_root_case_id=:root OR s.case_id IS NOT NULL)
) """
ORDER = ' ORDER BY same_chain DESC,created_at ASC,case_id ASC'


async def related_cases(store, case_id, *, limit, cursor):
    case = await store.case(case_id, lock=False)
    params = {'tenant': store.tenant_id, 'case': case_id, 'root': case['continuation_root_case_id']}
    rows = (await store.db.execute(text(RELATED + 'SELECT * FROM candidates' + ORDER), params)).mappings().all()
    signature = [{'id': str(r['case_id']), 'at': r['created_at'].isoformat(), 'same_chain': r['same_chain'],
        'shared': [{k: v for k, v in shared.items() if k != 'title'} for shared in r['shared_incidents']]} for r in rows]
    revision = digest({'tenant': str(store.tenant_id), 'case': str(case_id), 'relations': signature})
    offset = 0
    if cursor:
        try:
            value = json.loads(base64.b64decode(cursor, altchars=b'-_', validate=True))
            if (set(value) != {'case', 'revision', 'offset'} or value['case'] != str(case_id)
                    or type(value['offset']) is not int or value['offset'] < 0):
                raise ValueError('invalid cursor')
        except (ValueError, TypeError, binascii.Error, KeyError):
            raise StoreError('invalid_cursor', 422) from None
        if value['revision'] != revision:
            raise StoreError('cursor_stale')
        offset = value['offset']
    selected = (await store.db.execute(text(RELATED + 'SELECT * FROM candidates' + ORDER + ' LIMIT :limit OFFSET :offset'),
        {**params, 'limit': limit, 'offset': offset})).mappings().all()
    items = []
    for row in selected:
        types = (['continuation'] if row['same_chain'] else []) + (['shared_incident'] if row['shared_incidents'] else [])
        chain = None if not row['same_chain'] else CaseContinuation(
            root_case_id=row['continuation_root_case_id'], previous_case_id=row['previous_case_id'],
            receiving_case_id=row['receiving_case_id'])
        items.append({k: row[k] for k in ('case_id', 'title', 'handling_status', 'severity', 'shared_incidents')} |
            {'relation_types': types, 'primary_relation': types[0], 'continuation': chain})
    following = offset + len(items)
    next_cursor = base64.urlsafe_b64encode(json.dumps({'case': str(case_id), 'revision': revision,
        'offset': following}).encode()).decode() if following < len(rows) else None
    return RelatedCasePage(case_id=case_id, relation_revision=revision, items=items, total=len(rows),
        next_cursor=next_cursor, observed_at=await store.now())
