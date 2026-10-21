"""Authenticated existing-alert ingress for the socai2 Fusion pipeline.

An acknowledged publish is acceptance, not proof of Fusion or database success.
Tenant is bound to the authenticated principal; the caller cannot widen it.
"""
import asyncio
from datetime import datetime
import json
import os
from typing import Annotated, Literal
from uuid import UUID

from aiokafka import AIOKafkaProducer
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ConfigDict, Field

from sqlalchemy import select

from app.api.v1.deps import CurrentUser, DBSession, require_permission
from app.models.alert import Alert
from app.core.kafka_security import kafka_client_kwargs
from app.schemas.fusion_alert import RawAlert

router = APIRouter(prefix='/alert-ingress', tags=['alert-ingress'])


class ExistingAlert(RawAlert):
    model_config = ConfigDict(extra='forbid')
    tenant_id: UUID | None = None
    schema_version: Literal['v1'] = 'v1'
    source: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=512)
    source_event_ids: list[str] = Field(min_length=1, max_length=100)
    event_time: datetime


@router.post('', status_code=status.HTTP_202_ACCEPTED)
async def accept_existing_alert(
    payload: ExistingAlert,
    user: Annotated[CurrentUser, Depends(require_permission('alerts:write'))],
    db: DBSession = None,
) -> dict:
    if payload.tenant_id is not None and payload.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail='Alert tenant is outside the authenticated scope')
    if not all(item.strip() and len(item) <= 512 for item in payload.source_event_ids):
        raise HTTPException(status_code=422, detail='source_event_ids must be non-empty bounded references')
    identity_version = os.getenv('AISOC_ALERT_IDENTITY_VERSION', 'legacy-v1')
    if identity_version not in {'legacy-v1', 'source-v1'}:
        raise HTTPException(status_code=503, detail='Alert identity contract is not configured')
    if identity_version == 'source-v1' and 'id' not in payload.model_fields_set:
        raise HTTPException(status_code=422, detail='Provide a stable upstream alert UUID in id')
    wire = payload.model_dump(mode='json')
    # These fields are set by the receiver, never delegated to the caller.
    wire['identity_version'] = identity_version
    wire['source_alert_id'] = str(payload.id) if identity_version == 'source-v1' else None
    wire['tenant_id'] = str(user.tenant_id)
    if identity_version == 'source-v1':
        if db is None:
            raise HTTPException(status_code=503, detail='Identity lookup unavailable; not published')
        legacy = RawAlert.model_validate({**wire, 'identity_version': 'legacy-v1', 'source_alert_id': None})
        try:
            result = await asyncio.wait_for(db.execute(select(Alert.id).where(
                Alert.id == legacy.deterministic_id(), Alert.tenant_id == user.tenant_id,
                Alert.connector_id == payload.connector_id,
                Alert.source_event_ids.contains([str(payload.id)]),
            )), 5)
            retained_legacy_id = result.scalar_one_or_none()
        except Exception as exc:
            raise HTTPException(status_code=503, detail='Identity lookup unavailable; not published') from exc
        if retained_legacy_id is not None:
            # Exact retained pre-upgrade delivery keeps its already-issued ID.
            identity_version = wire['identity_version'] = 'legacy-v1'
            wire['source_alert_id'] = None
    content = json.dumps(wire, ensure_ascii=False, separators=(',', ':')).encode()
    if len(content) > 262144:
        raise HTTPException(status_code=413, detail='Alert exceeds 256 KiB')
    bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '').strip()
    topic = os.getenv('KAFKA_TOPIC_ALERTS_RAW', '').strip()
    if not bootstrap or not topic:
        raise HTTPException(status_code=503, detail='Alert ingress transport is not configured')
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap, client_id='socai2-api-alert-ingress',
        acks='all', enable_idempotence=True, request_timeout_ms=10000,
        **kafka_client_kwargs(),
    )
    try:
        await asyncio.wait_for(producer.start(), 12)
        metadata = await asyncio.wait_for(
            producer.send_and_wait(topic, content, key=str(user.tenant_id).encode()), 15,
        )
    except Exception as exc:
        # A timeout may happen after broker acceptance. Never automatically
        # replay here, and never return a false "not published" guarantee.
        raise HTTPException(status_code=503, detail='Publish unconfirmed; inspect before retrying') from exc
    finally:
        await producer.stop()
    # Receiver and Fusion share the explicitly versioned identity contract.
    canonical = RawAlert.model_validate(wire).deterministic_id()
    return {'status': 'accepted', 'input_id': str(payload.id), 'tenant_id': str(user.tenant_id),
            'canonical_alert_id': str(canonical), 'identity_version': identity_version, 'source_event_ids': payload.source_event_ids,
            'message': {'topic': metadata.topic, 'partition': metadata.partition, 'offset': metadata.offset},
            'result_url': f'/api/v1/alerts/{canonical}', 'processing_confirmed': False}
