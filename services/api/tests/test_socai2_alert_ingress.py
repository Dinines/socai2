"""Scoped-ingress boundaries; broker is an explicit test double here."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.alert_ingress import ExistingAlert, accept_existing_alert

TENANT = UUID('114e173b-be2e-4b29-8cbc-48861175df51')


def payload(**changes):
    return {'source':'existing-edr', 'title':'marked finding',
            'source_event_ids':['source-1'], 'event_time':'2026-10-20T01:00:00Z', **changes}


def test_principal_tenant_and_actual_ack_are_in_receipt(monkeypatch):
    monkeypatch.setenv('KAFKA_BOOTSTRAP_SERVERS','broker:9092')
    monkeypatch.setenv('KAFKA_TOPIC_ALERTS_RAW','socai2.alerts.raw')
    p = AsyncMock()
    p.send_and_wait.return_value = SimpleNamespace(topic='socai2.alerts.raw',partition=2,offset=17)
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer',return_value=p):
        r = asyncio.run(accept_existing_alert(ExistingAlert(**payload()),SimpleNamespace(tenant_id=TENANT)))
    assert r['tenant_id']==str(TENANT) and r['message']=={'topic':'socai2.alerts.raw','partition':2,'offset':17}
    assert r['processing_confirmed'] is False
    assert b'"tenant_id":"114e173b-be2e-4b29-8cbc-48861175df51"' in p.send_and_wait.call_args.args[1]


def test_cross_tenant_is_refused_before_broker_is_constructed():
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer') as factory:
        with pytest.raises(HTTPException) as error:
            asyncio.run(accept_existing_alert(ExistingAlert(**payload(tenant_id=UUID(int=1))),SimpleNamespace(tenant_id=TENANT)))
    assert error.value.status_code==403 and not factory.called


@pytest.mark.parametrize('change',[{'schema_version':'v2'},{'source':''},{'source_event_ids':[]},{'unknown_field':True}])
def test_invalid_input_is_refused(change):
    with pytest.raises(ValidationError):ExistingAlert(**payload(**change))


def test_publish_failure_is_unconfirmed_and_not_automatically_replayed(monkeypatch):
    monkeypatch.setenv('KAFKA_BOOTSTRAP_SERVERS','broker:9092')
    monkeypatch.setenv('KAFKA_TOPIC_ALERTS_RAW','socai2.alerts.raw')
    p = AsyncMock();p.send_and_wait.side_effect=TimeoutError()
    with patch('app.api.v1.endpoints.alert_ingress.AIOKafkaProducer',return_value=p):
        with pytest.raises(HTTPException) as error:
            asyncio.run(accept_existing_alert(ExistingAlert(**payload()),SimpleNamespace(tenant_id=TENANT)))
    assert error.value.status_code==503 and 'unconfirmed' in error.value.detail
    assert p.send_and_wait.await_count==1
