"""One bounded, opt-in knowledge maintenance attempt after an adopted A commit."""
import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid5

from sqlalchemy import select, text

from . import knowledge_history as history
from .baseline_optional_sources import SourceUnavailable
from .baseline_store import digest
from .knowledge_config import configured, load
from .knowledge_source import index
from .knowledge_vectors import Vectors

VERSION = "socai2.history-sync.v1"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def session(service, tenant):
    # import_cards commits. Each independent operation needs a fresh RLS context.
    async with service.sessions() as db:
        await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": str(tenant)})
        yield db


async def source(service, tenant, alert_id, result_id, profile):
    async with session(service, tenant) as db:
        row = await history.source_row(db, tenant, alert_id)
        if row is None:
            raise SourceUnavailable("history_alert_not_found")
        if row["alert"]["latest_triage_id"] != str(result_id):
            raise SourceUnavailable("history_sync_source_changed")
        return history.card_from(row, profile)


async def receipt(service, tenant, run, phase, body):
    from .stage_results import F, R, artifact
    identity = uuid5(run["id"], VERSION + ":" + phase)
    async with service.transaction(tenant) as store:
        # Only the short receipt transaction locks the Run; no network I/O here.
        await store.one(select(R.c.id).where(*store.where(R, R.c.id == run["id"])).with_for_update())
        if await store.one(select(F.c.id).where(*store.where(F, F.c.id == identity))):
            return False
        refs = [{"type": "artifact", "id": str(uuid5(run["id"], "publication")), "external": None,
                 "source_path": None, "row_keys": [], "role": "execution_receipt"}]
        await artifact(store, run, identity, "source_snapshot", {"schema_version": VERSION,
            "phase": phase, **body}, await store.now(), refs, schema_version=VERSION)
    return True


async def after_triage(service, tenant, run, outcome):
    if run["kind"] != "alert_basic" or not outcome["adopted"] or not configured():
        return
    try:
        profile, fingerprint = load()
        if not profile.history or not profile.history.sync_after_adopted_triage:
            return
    except SourceUnavailable:
        logger.warning("history_sync_configuration_unavailable run=%s", run["id"])
        return
    deadline = asyncio.get_running_loop().time() + profile.history.sync_timeout_seconds
    vectors, started = Vectors(profile), False
    body = {"trigger_run_id": str(run["id"]), "alert_id": str(run["alert_id"]),
        "triage_id": outcome["result_id"], "profile_sha256": fingerprint,
        "state": "started", "storage_state": "not_attempted", "index_state": "not_attempted",
        "source_current": None, "source": None, "document_id": None, "content_sha256": None,
        "reason": None, "calls": vectors.calls}
    try:
        async with asyncio.timeout_at(deadline):
            started = await receipt(service, tenant, run, "intent", body)
            if not started:  # An old attempt, including an unknown one, is never retried here.
                return
            card = await source(service, tenant, run["alert_id"], outcome["result_id"], profile)
            body.update(source=card["source"], source_current=True)
            body["storage_state"] = "started"
            async with session(service, tenant) as db:
                imported = await history.import_cards(db, tenant, [run["alert_id"]], VERSION, profile,
                    expected_hashes={str(run["alert_id"]): digest(card)})
            saved = imported["cards"][0]
            body["storage_state"] = saved["state"]
            if saved["state"] != "stored":
                body.update(state="skipped", reason=saved["reason"], source_current=False)
            else:
                body.update(document_id=saved["document_id"], index_state="started")
                async with session(service, tenant) as db:
                    indexed = await index(db, tenant, [saved["document_id"]], vectors=vectors,
                        expected_profile_sha256=fingerprint)
                body.update(index_state="completed", content_sha256=indexed["documents"][0]["content_sha256"])
                current = await source(service, tenant, run["alert_id"], outcome["result_id"], profile)
                unchanged = digest(current) == digest(card)
                body.update(source_current=unchanged, state="completed" if unchanged else "skipped",
                    reason=None if unchanged else "history_sync_source_changed")
    except SourceUnavailable as exc:
        body.update(state="skipped" if str(exc).startswith("history_") else "failed", reason=str(exc))
        body["source_current"] = False if str(exc).startswith("history_") else None
    except (TimeoutError, asyncio.CancelledError):
        # The publication is already durable; cancellation never relaunches A.
        body.update(state="unknown", reason="history_sync_interrupted", source_current=None)
    except Exception:  # noqa: BLE001 -- preserve the published judgment and omit private DB details
        body.update(state="unknown", reason="history_sync_unconfirmed", source_current=None)
    if not started:
        logger.warning("history_sync_intent_unconfirmed run=%s", run["id"])
        return
    if body["storage_state"] == "started":
        body["storage_state"] = "unknown"
    if body["index_state"] == "started":
        body["index_state"] = ("unknown" if any(c["method"] == "PUT" and "/points" in c["path"]
            for c in vectors.calls) else "failed")
    if "unknown" in (body["storage_state"], body["index_state"]):
        body["state"] = "unknown"
    try:
        # If the total time limit is exhausted, the immutable intent remains unconfirmed.
        async with asyncio.timeout_at(deadline):
            await receipt(service, tenant, run, "result", body)
    except (Exception, asyncio.CancelledError):  # noqa: BLE001 -- a receipt failure must not undo committed triage
        logger.warning("history_sync_result_unconfirmed run=%s", run["id"])
