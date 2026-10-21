import asyncio,json
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from uuid import UUID
import pytest
from fastapi import HTTPException
from app.api.v1.endpoints.alert_ingress import ExistingAlert,accept_existing_alert
TENANT=UUID(int=1);SOURCE_ID=UUID(int=20)

class NoLegacy:
    async def execute(self,query):return SimpleNamespace(scalar_one_or_none=lambda:None)

def payload(**changes):return {'id':str(SOURCE_ID),'source':'test-edr','title':'finding','event_time':'2026-10-20T01:00:00Z','source_event_ids':['event-1'],**changes}

@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setenv('AISOC_ALERT_IDENTITY_VERSION','source-v1')
    monkeypatch.setenv('KAFKA_BOOTSTRAP_SERVERS','broker:9092')
    monkeypatch.setenv('KAFKA_TOPIC_ALERTS_RAW','socai2.alerts.raw')

def test_receiver_binds_identity_to_supplied_uuid_and_its_config():
    producer=AsyncMock();producer.send_and_wait.return_value=SimpleNamespace(topic='socai2.alerts.raw',partition=0,offset=1)
    value=ExistingAlert(**payload(identity_version='legacy-v1',source_alert_id=str(UUID(int=999))))
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer',return_value=producer):
        receipt=asyncio.run(accept_existing_alert(value,SimpleNamespace(tenant_id=TENANT),NoLegacy()))
    wire=json.loads(producer.send_and_wait.call_args.args[1]);assert wire['source_alert_id']==str(SOURCE_ID)
    assert wire['identity_version']==receipt['identity_version']=='source-v1'
    from app.schemas.fusion_alert import RawAlert
    assert receipt['canonical_alert_id']==str(RawAlert.model_validate(wire).deterministic_id())

def test_missing_explicit_uuid_rejected_before_broker():
    body=payload();body.pop('id')
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer') as factory:
        with pytest.raises(HTTPException) as e:asyncio.run(accept_existing_alert(ExistingAlert(**body),SimpleNamespace(tenant_id=TENANT)))
    assert e.value.status_code==422;factory.assert_not_called()

def test_bad_server_identity_mode_is_unavailable(monkeypatch):
    monkeypatch.setenv('AISOC_ALERT_IDENTITY_VERSION','typo')
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer') as factory:
        with pytest.raises(HTTPException) as e:asyncio.run(accept_existing_alert(ExistingAlert(**payload()),SimpleNamespace(tenant_id=TENANT)))
    assert e.value.status_code==503;factory.assert_not_called()


def test_source_identity_requires_available_legacy_lookup():
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer') as factory:
        with pytest.raises(HTTPException) as e:asyncio.run(accept_existing_alert(ExistingAlert(**payload()),SimpleNamespace(tenant_id=TENANT)))
    assert e.value.status_code==503;factory.assert_not_called()

def test_exact_retained_legacy_delivery_keeps_legacy_version():
    class Retained:
        async def execute(self,query):return SimpleNamespace(scalar_one_or_none=lambda:UUID(int=30))
    producer=AsyncMock();producer.send_and_wait.return_value=SimpleNamespace(topic='socai2.alerts.raw',partition=0,offset=1)
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer',return_value=producer):
        receipt=asyncio.run(accept_existing_alert(ExistingAlert(**payload()),SimpleNamespace(tenant_id=TENANT),Retained()))
    assert receipt['identity_version']=='legacy-v1'
    wire=json.loads(producer.send_and_wait.call_args.args[1]);assert wire['source_alert_id'] is None
