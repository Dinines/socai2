"""Opt-in v2 job: generate one initial summary per newly persisted incident.

Run separately with --tenant-id; the legacy Fusion worker is unchanged.
By default only incidents formed after this process starts are selected.
"""
import argparse
import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import String, cast, func, select

from app.db.database import AsyncSessionLocal, engine
from app.db.rls import set_rls_context
from app.models.alert import Alert
from .incident_reader import read_incident
from .incident_summary import IncidentSummaryRecord, generate_summary

logger = logging.getLogger(__name__)


async def pending_incidents(db, tenant_id: UUID, since: datetime) -> list[UUID]:
    incident = Alert.enrichment_data["socai2_fusion"]["incident_id"].astext
    query = (
        select(incident)
        .outerjoin(IncidentSummaryRecord, (IncidentSummaryRecord.tenant_id == Alert.tenant_id)
                   & (cast(IncidentSummaryRecord.incident_id, String) == incident))
        .where(Alert.tenant_id == tenant_id, incident.is_not(None), IncidentSummaryRecord.incident_id.is_(None))
        .group_by(incident).having(func.min(Alert.created_at) >= since)
        .order_by(func.min(Alert.created_at), incident).limit(20)
    )
    candidates = []
    for value in (await db.execute(query)).scalars().all():
        try:
            candidates.append(UUID(value))
        except (ValueError, TypeError, AttributeError):
            logger.warning("incident_summary.invalid_incident_reference")
    return candidates


async def run_once(tenant_id: UUID, since: datetime) -> int:
    async with AsyncSessionLocal() as db:
        await set_rls_context(db, tenant_id)
        candidates = await pending_incidents(db, tenant_id, since)
    processed = 0
    for incident_id in candidates:
        async with AsyncSessionLocal() as db:
            await set_rls_context(db, tenant_id)
            overview = await read_incident(db, tenant_id=tenant_id, incident_id=incident_id)
            if overview is None:
                continue
            await generate_summary(db, overview, initial=True)
            await db.commit()
            processed += 1
    return processed


async def run(tenant_id: UUID, since: datetime, interval: int, once: bool):
    try:
        while True:
            count = await run_once(tenant_id, since)
            logger.info("incident_summary.initial_batch processed=%s", count)
            if once:
                return
            await asyncio.sleep(interval)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", required=True, type=UUID)
    parser.add_argument("--since", help="Optional UTC/offset timestamp; defaults to process start")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--once", action="store_true", help="Process at most 20 pending incidents, then exit")
    args = parser.parse_args()
    since = datetime.fromisoformat(args.since.replace("Z", "+00:00")) if args.since else datetime.now(UTC)
    if since.tzinfo is None or args.interval < 1:
        parser.error("--since needs a timezone and --interval must be positive")
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(args.tenant_id, since, args.interval, args.once))
