"""One transaction allocates members, relationships and initial tasks; no Run I/O."""
from uuid import uuid4, uuid5

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert

from app.models import socai2 as m

from .analysis_task_store import AnalysisTaskStore
from .baseline_store import CA, A, C, StoreError
from .case_allocation_contracts import (
    CaseAllocation,
    CaseAllocationReceipt,
    CaseMemberRemoval,
    InitialTaskReceipt,
)

I, IA, CI, X = (t.__table__ for t in (m.Incidents, m.IncidentAlerts, m.CaseIncidents, m.CaseAlertExclusions))


def editable(case, revision=None):
    if revision is not None and case['scope_revision'] != revision:
        raise StoreError('case_scope_revision_conflict')
    if case['handling_status'] == 'resolved':
        raise StoreError('resolved_case_scope_policy_not_enabled')


async def lock_chains(store, case_ids):
    # Root/previous identities are immutable. Lock every root before any child.
    roots = {}
    for cid in sorted(set(case_ids)):
        row = await store.case(cid, lock=False)
        if row['continuation_root_case_id'] is None:
            raise StoreError('case_continuation_unavailable')
        roots[cid] = row['continuation_root_case_id']
    for root in sorted(set(roots.values())):
        await store.case(root)
    return roots


async def incident_selection(store, ids, page_size):
    if not ids:
        return {}
    # A single statement snapshot, fetched in partitions, covers the entire event.
    query = select(I.c.id, I.c.source_namespace, IA.c.alert_id, A.c.source_namespace.label('alert_namespace')).outerjoin(
        IA, (IA.c.tenant_id == I.c.tenant_id) & (IA.c.incident_id == I.c.id)).outerjoin(
        A, (A.c.tenant_id == IA.c.tenant_id) & (A.c.id == IA.c.alert_id)).where(
        *store.where(I, I.c.id.in_(ids))).order_by(I.c.id, IA.c.alert_id)
    result = await store.db.stream(query.execution_options(yield_per=page_size))
    found = {}
    try:
        async for rows in result.mappings().partitions(page_size):
            for row in rows:
                if row['alert_id'] is None or row['alert_namespace'] is None:
                    raise StoreError('case_incident_members_unavailable')
                if row['source_namespace'] != row['alert_namespace'] or not row['source_namespace'].strip():
                    raise StoreError('case_source_namespace_mismatch')
                found.setdefault(row['id'], set()).add(row['alert_id'])
    finally:
        await result.close()
    if set(found) != set(ids):
        raise StoreError('case_incident_not_found', 404)
    return found


class Allocator:
    def __init__(self, store, policy, task_policy, actor, operation_key, root):
        self.s, self.policy, self.task_policy = store, policy, task_policy
        self.actor, self.key, self.root = actor, operation_key, root
        self.items, self.receivers = {}, {}
        self.excluded = set()

    async def item(self, cid, *, created=False):
        if cid not in self.items:
            row = await self.s.case(cid)
            self.items[cid] = CaseAllocation(case_id=cid, scope_revision=row['scope_revision'],
                created=created, changed=created, previous_case_id=row['previous_case_id'],
                added_alert_ids=[], existing_alert_ids=[], linked_incident_ids=[], initial_task=None)
        return self.items[cid]

    async def touch(self, cid, *, scope=False):
        values = {'row_version': C.c.row_version + 1, 'business_updated_at': await self.s.now()}
        if scope:
            values['scope_revision'] = C.c.scope_revision + 1
        await self.s.db.execute(update(C).where(*self.s.where(C, C.c.id == cid)).values(**values))
        item = await self.item(cid)
        self.items[cid] = item.model_copy(update={"changed": True})

    async def link(self, cid, iid):
        identity = (await self.s.db.execute(insert(CI).values(id=uuid4(), tenant_id=self.s.tenant_id,
            case_id=cid, incident_id=iid, linked_at=await self.s.now(), linked_by=self.actor.user_id,
            source_operation_id=self.key).on_conflict_do_nothing(
                constraint='case_incidents_business_key').returning(CI.c.id))).scalar_one_or_none()
        if identity is not None:
            (await self.item(cid)).linked_incident_ids.append(iid)
            await self.touch(cid)

    async def receiver(self, iid, cid):
        await self.link(cid, iid)
        row = await self.s.one(update(I).where(*self.s.where(I, I.c.id == iid,
            I.c.active_case_id.is_distinct_from(cid))).values(active_case_id=cid,
                row_version=I.c.row_version + 1, business_updated_at=await self.s.now()).returning(I.c.id))
        if row:
            self.receivers[iid] = cid
            await self.touch(cid)

    async def successor(self, current):
        prior = await self.s.case(current)
        cid = uuid4()
        await self.s.db.execute(insert(C).values(id=cid, tenant_id=self.s.tenant_id,
            continuation_root_case_id=self.root, previous_case_id=current,
            source_namespace=prior['source_namespace'], title=prior['title'], description=prior['description'],
            severity=prior['severity'], severity_source=prior['severity_source'], tags=prior['tags'],
            created_by=self.actor.user_id))
        await self.item(cid, created=True)
        await self.s.db.execute(update(C).where(*self.s.where(C, C.c.id == self.root)).values(receiving_case_id=cid))
        await self.touch(self.root)
        # Conditional update after row locking never steals another independent chain's receiver.
        events = (await self.s.db.execute(select(I.c.id).where(*self.s.where(I,
            I.c.active_case_id == current)).order_by(I.c.id).with_for_update())).scalars().all()
        for iid in events:
            await self.receiver(iid, cid)
        return cid

    async def remove(self, cid, selected):
        if selected:
            await self.s.db.execute(delete(CA).where(*self.s.where(CA, CA.c.case_id == cid, CA.c.alert_id.in_(selected))))
            for aid in sorted(selected):
                await self.s.db.execute(insert(X).values(tenant_id=self.s.tenant_id, case_id=cid, alert_id=aid,
                    excluded_at=await self.s.now(), excluded_by=self.actor.user_id, operation_key=self.key).on_conflict_do_update(
                        index_elements=[X.c.tenant_id, X.c.case_id, X.c.alert_id],
                        set_={'excluded_at': await self.s.now(), 'excluded_by': self.actor.user_id, 'operation_key': self.key}))
            await self.touch(cid, scope=True)
        row = await self.s.case(cid)
        return CaseMemberRemoval(case_id=cid, scope_revision=row['scope_revision'],
            removed_alert_ids=sorted(selected), changed=bool(selected))

    async def allocate(self, primary, explicit, incidents, *, created=False, membership_source=None):
        root = await self.s.case(self.root)
        current = root['receiving_case_id']
        editable(await self.s.case(current))
        await self.item(primary, created=created)
        await self.item(current)
        selected = set(explicit).union(*(incidents.values()))
        rows = (await self.s.db.execute(select(A.c.id, A.c.source_namespace).where(*self.s.where(A,
            A.c.id.in_(selected))).order_by(A.c.id))).mappings().all()
        if {r['id'] for r in rows} != selected:
            raise StoreError('member_alert_not_found', 404)
        namespaces = {r['source_namespace'] for r in rows}
        bound = (await self.s.case(current))['source_namespace']
        if namespaces and (len(namespaces) != 1 or not next(iter(namespaces))):
            raise StoreError('case_source_namespace_mismatch')
        if bound is None and selected:
            if not created:
                raise StoreError('case_source_scope_unverified')
            bound = next(iter(namespaces))
            await self.s.db.execute(update(C).where(*self.s.where(C, C.c.id == current)).values(source_namespace=bound))
        if namespaces - {bound}:
            raise StoreError('case_source_namespace_mismatch')
        chain = select(C.c.id).where(*self.s.where(C, C.c.continuation_root_case_id == self.root))
        restored = (await self.s.db.execute(delete(X).where(*self.s.where(X,
            X.c.case_id.in_(chain), X.c.alert_id.in_(explicit))).returning(X.c.case_id))).scalars().all()
        for cid in set(restored):
            await self.touch(cid)
        excluded = set((await self.s.db.execute(select(X.c.alert_id).where(*self.s.where(X,
            X.c.case_id.in_(chain))))).scalars())
        self.excluded = selected & excluded
        selected -= excluded
        existing = (await self.s.db.execute(select(CA.c.case_id, CA.c.alert_id).where(*self.s.where(CA,
            CA.c.case_id.in_(chain))))).mappings().all()
        owners = {r['alert_id']: r['case_id'] for r in existing}
        for aid in sorted(selected & owners.keys()):
            (await self.item(owners[aid])).existing_alert_ids.append(aid)
        todo = sorted(selected - owners.keys())
        while todo:
            members = await self.s.members(current)
            room = self.policy.max_alerts - len(members)
            if room <= 0:
                current = await self.successor(current)
                room = self.policy.max_alerts
            chunk, todo = todo[:room], todo[room:]
            await self.s.db.execute(insert(CA), [{'id': uuid4(), 'tenant_id': self.s.tenant_id,
                'case_id': current, 'alert_id': aid, 'added_by': self.actor.user_id,
                'added_at': await self.s.now(), 'source_operation_id': self.key,
                'membership_source': membership_source or ('manual' if aid in explicit else 'incident_link')} for aid in chunk])
            (await self.item(current)).added_alert_ids.extend(chunk)
            owners.update({aid: current for aid in chunk})
            await self.touch(current, scope=True)
        for iid, members in sorted(incidents.items()):
            for cid in sorted({primary, current} | {owners[aid] for aid in members & selected}):
                await self.link(cid, iid)
            await self.receiver(iid, current)
        return current

    async def receipt(self, primary, requested, receiving):
        task_store = AnalysisTaskStore(self.s.db, self.s.tenant_id, self.task_policy)
        for cid, item in self.items.items():
            row = await self.s.case(cid)
            changes = {'scope_revision': row['scope_revision'], 'linked_incident_ids': sorted(set(item.linked_incident_ids))}
            if item.created:
                task = await task_store.accept(kind='case_investigation', subject_id=cid, intent='initial',
                    source='case_create', operation_key=uuid5(cid, 'initial-investigation'), submitted_by=self.actor.user_id)
                changes['initial_task'] = InitialTaskReceipt(task_id=task['id'], subject_id=cid)
            self.items[cid] = item.model_copy(update=changes)
        # A chain has an immutable predecessor; SQL ordering alone needn't match creation clock ties.
        chain = (await self.s.db.execute(select(C.c.id, C.c.previous_case_id).where(*self.s.where(C,
            C.c.continuation_root_case_id == self.root)))).mappings().all()
        next_ids = {row['previous_case_id']: row['id'] for row in chain}
        ordered, cid = [], self.root
        while cid is not None:
            if cid in self.items:
                ordered.append(self.items[cid])
            cid = next_ids.get(cid)
        return CaseAllocationReceipt(operation_key=self.key, requested_case_id=requested,
            primary_case_id=primary, continuation_root_case_id=self.root, receiving_case_id=receiving,
            changed=any(i.changed for i in ordered) or bool(self.receivers), allocations=ordered,
            incident_receivers=[{'incident_id': iid, 'active_case_id': cid} for iid, cid in sorted(self.receivers.items())],
            excluded_alert_ids=sorted(self.excluded))
