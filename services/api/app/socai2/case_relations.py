"""Case writes share capacity allocation and immutable operation receipts."""
from uuid import uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .baseline_store import C, StoreError, digest
from .case_allocation import Allocator, I, editable, incident_selection, lock_chains
from .case_allocation_contracts import (
    CaseAllocationReceipt,
    CaseMoveReceipt,
    CaseReplacementReceipt,
)


def intent(request, actor):
    return digest({'actor': str(actor.user_id), 'request': request.model_dump(mode='json')})


async def replay(store, case_id, request, actor, action, model):
    previous = await store.receipt(case_id, request.operation_key, action)
    if previous is None:
        return None
    if previous['request_hash'] != intent(request, actor):
        raise StoreError('operation_key_conflict')
    return model.model_validate(previous['outcome'])


async def record(store, case_id, request, actor, action, out):
    await store.event(case_id, request.operation_key, actor.snapshot(), action,
        {'request_hash': intent(request, actor), 'outcome': out.model_dump(mode='json')}, [])
    return out


async def create(store, request, actor, policy, task_policy):
    cid = uuid5(store.tenant_id, 'socai2.case.create:' + str(request.operation_key))
    inserted = (await store.db.execute(insert(C).values(id=cid, tenant_id=store.tenant_id,
        continuation_root_case_id=cid, receiving_case_id=cid,
        title=request.title, description=request.description, severity=request.severity,
        severity_source='manual' if request.severity else None, tags=request.tags,
        created_by=actor.user_id).on_conflict_do_nothing(index_elements=[C.c.id]).returning(C.c.id))).scalar_one_or_none()
    await store.case(cid)
    if inserted is None:
        prior = await replay(store, cid, request, actor, 'case_created', CaseAllocationReceipt)
        if prior is None:
            raise StoreError('operation_key_conflict')
        return prior
    allocator = Allocator(store, policy, task_policy, actor, request.operation_key, cid)
    incidents = await incident_selection(store, request.incident_ids, policy.source_page_size)
    current = await allocator.allocate(cid, set(request.alert_ids), incidents, created=True)
    return await record(store, cid, request, actor, 'case_created', await allocator.receipt(cid, None, current))


async def associate(store, case_id, request, actor, policy, task_policy):
    # Check the original receipt even when current receiver is closed/has moved.
    await store.case(case_id, lock=False)
    prior = await replay(store, case_id, request, actor, 'case_associated', CaseAllocationReceipt)
    if prior is not None:
        return prior
    roots = await lock_chains(store, [case_id])
    prior = await replay(store, case_id, request, actor, 'case_associated', CaseAllocationReceipt)
    if prior is not None:
        return prior
    editable(await store.case(case_id), request.expected_scope_revision)
    allocator = Allocator(store, policy, task_policy, actor, request.operation_key, roots[case_id])
    incidents = await incident_selection(store, request.incident_ids, policy.source_page_size)
    current = await allocator.allocate(case_id, set(request.alert_ids), incidents)
    return await record(store, case_id, request, actor, 'case_associated', await allocator.receipt(case_id, case_id, current))


async def replace(store, case_id, request, actor, policy, task_policy):
    prior = await replay(store, case_id, request, actor, 'case_members_replaced', CaseReplacementReceipt)
    if prior is not None:
        return prior
    roots = await lock_chains(store, [case_id])
    prior = await replay(store, case_id, request, actor, 'case_members_replaced', CaseReplacementReceipt)
    if prior is not None:
        return prior
    editable(await store.case(case_id), request.expected_scope_revision)
    allocator = Allocator(store, policy, task_policy, actor, request.operation_key, roots[case_id])
    before = await store.members(case_id)
    source = await allocator.remove(case_id, before - set(request.alert_ids))
    current = await allocator.allocate(case_id, set(request.alert_ids), {})
    allocation = await allocator.receipt(case_id, case_id, current)
    source = source.model_copy(update={'scope_revision': (await store.case(case_id))['scope_revision'],
        'changed': source.changed or any(item.case_id == case_id and item.changed for item in allocation.allocations)})
    out = CaseReplacementReceipt(source=source, allocation=allocation)
    return await record(store, case_id, request, actor, 'case_members_replaced', out)


async def move(store, case_id, request, actor, policy, task_policy):
    if case_id == request.target_case_id:
        raise StoreError('case_move_requires_different_target', 422)
    prior = await replay(store, case_id, request, actor, 'case_members_moved_out', CaseMoveReceipt)
    if prior is not None:
        return prior
    roots = await lock_chains(store, [case_id, request.target_case_id])
    cases = {cid: await store.case(cid) for cid in sorted([case_id, request.target_case_id])}
    prior = await replay(store, case_id, request, actor, 'case_members_moved_out', CaseMoveReceipt)
    if prior is not None:
        return prior
    source, target = cases[case_id], cases[request.target_case_id]
    editable(source, request.expected_source_scope_revision)
    editable(target, request.expected_target_scope_revision)
    if source['source_namespace'] is None or target['source_namespace'] is None:
        raise StoreError('case_source_scope_unverified')
    if source['source_namespace'] != target['source_namespace']:
        raise StoreError('case_source_namespace_mismatch')
    selected = set(request.alert_ids)
    if not selected <= await store.members(case_id):
        raise StoreError('case_move_member_not_in_source')
    allocator = Allocator(store, policy, task_policy, actor, request.operation_key, roots[request.target_case_id])
    removed = await allocator.remove(case_id, selected)
    current = await allocator.allocate(request.target_case_id, selected, {}, membership_source='move')
    allocation = await allocator.receipt(request.target_case_id, request.target_case_id, current)
    removed = removed.model_copy(update={'scope_revision': (await store.case(case_id))['scope_revision']})
    out = CaseMoveReceipt(source=removed, allocation=allocation, moved_alert_ids=sorted(selected))
    await record(store, request.target_case_id, request, actor, 'case_members_moved_in', out)
    return await record(store, case_id, request, actor, 'case_members_moved_out', out)


async def follow(store, case_id, incident_id, request, actor, policy, task_policy):
    """Called by future periodic preparation, never schedules itself."""
    prior = await replay(store, case_id, request, actor, 'case_event_followed', CaseAllocationReceipt)
    if prior is not None:
        return prior
    roots = await lock_chains(store, [case_id])
    prior = await replay(store, case_id, request, actor, 'case_event_followed', CaseAllocationReceipt)
    if prior is not None:
        return prior
    event = await store.one(select(I).where(*store.where(I, I.c.id == incident_id)))
    if event is None:
        raise StoreError('case_incident_not_found', 404)
    from .case_relationship_reader import receiving_status
    status = await receiving_status(store, event, task_policy)
    if event['active_case_id'] != case_id or not status.can_receive_automatically:
        return None
    allocator = Allocator(store, policy, task_policy, actor, request.operation_key, roots[case_id])
    incidents = await incident_selection(store, [incident_id], policy.source_page_size)
    # Lock the event after loading its members, then recheck a concurrent explicit switch.
    event = await store.one(select(I).where(*store.where(I, I.c.id == incident_id)).with_for_update())
    if event['active_case_id'] != case_id:
        return None
    current = await allocator.allocate(case_id, set(), incidents)
    return await record(store, case_id, request, actor, 'case_event_followed', await allocator.receipt(case_id, case_id, current))
