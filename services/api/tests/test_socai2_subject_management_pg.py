"""One direct regression: an intervening incident update cannot move backwards."""
from datetime import timedelta
from uuid import UUID, uuid4

from app.models.socai2 import Alerts, IncidentAlerts, Incidents
from app.socai2.baseline_contracts import Actor
from app.socai2.subject_management import SubjectManagementService
from app.socai2.subject_management_contracts import FeedbackFields, SelectedSubject
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import async_sessionmaker


async def run_check(engine):
    tenant, actor_id = UUID(int=1), UUID(int=3)
    aid, iid = uuid4(), uuid4()
    service = SubjectManagementService(async_sessionmaker(engine, expire_on_commit=False))
    async with service.transaction(tenant) as store:
        newer = await store.now() + timedelta(minutes=1)
        await store.db.execute(insert(Alerts).values(id=aid, tenant_id=tenant,
            title='SYNTHETIC monotonic update regression', source_namespace='synthetic-subject-clock',
            source_identity_key=str(aid), tags=['synthetic']))
        await store.db.execute(insert(Incidents).values(id=iid, tenant_id=tenant,
            title='SYNTHETIC newer incident timestamp', source_namespace='synthetic-subject-clock',
            source_incident_id=str(iid), tags=['synthetic'], business_updated_at=newer))
        await store.db.execute(insert(IncidentAlerts).values(id=uuid4(), tenant_id=tenant,
            incident_id=iid, alert_id=aid, membership_source='manual', source_operation_id=uuid4(),
            correlation_basis={'synthetic': True}, basis_version='synthetic.v1'))
    result = await service.apply(tenant, 'alerts', [SelectedSubject(id=aid, expected_row_version=1)],
        FeedbackFields(disposition='needs_review', reason='SYNTHETIC clock regression'), uuid4(),
        Actor(user_id=actor_id, name='synthetic.clock@example.invalid'), feedback=True)
    async with service.transaction(tenant, readonly=True) as store:
        row = await store.one(select(Incidents.__table__).where(Incidents.tenant_id==tenant, Incidents.id==iid))
        assert row['business_updated_at'] == newer and row['row_version'] == 2
        assert result.items[0].facts.latest_feedback_id == result.items[0].feedback_id
    return {'state':'passed','check':'related_incident_timestamp_never_moves_backwards',
            'alert_id':str(aid),'incident_id':str(iid),'real_model_calls':0}
