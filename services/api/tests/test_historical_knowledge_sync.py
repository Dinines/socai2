"""Direct synchronization boundaries; the real publication path is checked separately."""
import copy
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.socai2 import knowledge_sync as sync
from app.socai2.baseline_optional_sources import SourceUnavailable
from app.socai2.knowledge_config import History
from pydantic import ValidationError
from test_historical_alert_knowledge import profile, source

RUN = {"kind": "alert_basic", "id": UUID(int=40), "alert_id": UUID(int=2)}
OUTCOME = {"result_id": str(UUID(int=4)), "adopted": True, "reason": "current"}


class Configuration(TestCase):
    def test_sync_is_opt_in_and_requires_its_own_time_limit(self):
        value = profile().history.model_dump()
        value.pop("sync_timeout_seconds")
        value.pop("sync_after_adopted_triage")
        self.assertFalse(History.model_validate(value).sync_after_adopted_triage)
        with self.assertRaises(ValidationError):
            History.model_validate({**value, "sync_after_adopted_triage": True})


class Synchronization(IsolatedAsyncioTestCase):
    async def exercise(self, *, enabled=True, outcome=None, run=None, failure=None, changed=False):
        p, saved, calls = profile(), [], []
        p.history.sync_after_adopted_triage = enabled
        p.history.sync_timeout_seconds = 30
        card = sync.history.card_from(source(), p)
        @asynccontextmanager
        async def session(*args):
            yield object()
        async def receipt(*args):
            saved.append((args[-2], copy.deepcopy(args[-1])))
            return True
        async def index(*args, **kwargs):
            if failure == "unconfirmed":
                calls.append({"method": "PUT", "path": "/collections/test/points", "state": "failed"})
            if failure:
                raise SourceUnavailable("knowledge_vector_request_failed")
            return {"documents": [{"content_sha256": "b" * 64}]}
        snapshots = [card, {**card, "verification": "changed"}] if changed else [card, card]
        expected = copy.deepcopy(outcome or OUTCOME)
        with patch.object(sync, "configured", return_value=True), patch.object(sync, "load", return_value=(p, "profile")), \
                patch.object(sync, "session", session), patch.object(sync, "receipt", receipt), \
                patch.object(sync, "source", AsyncMock(side_effect=snapshots)), patch.object(sync, "index", index), \
                patch.object(sync, "Vectors", return_value=SimpleNamespace(calls=calls)), \
                patch.object(sync.history, "import_cards", AsyncMock(return_value={"cards": [
                    {"state": "stored", "document_id": "document"}]})) as imported:
            await sync.after_triage(object(), UUID(int=1), run or RUN, expected)
            self.assertEqual(expected, outcome or OUTCOME)
            return saved, imported.await_count

    async def test_disabled_unadopted_and_incident_publications_do_not_write_knowledge(self):
        for args in ({"enabled": False}, {"outcome": {**OUTCOME, "adopted": False}},
                     {"run": {**RUN, "kind": "incident_diagnosis"}}):
            self.assertEqual(await self.exercise(**args), ([], 0))

    async def test_completed_sync_preserves_intent_and_reports_current_index(self):
        saved, count = await self.exercise()
        self.assertEqual(count, 1)
        self.assertEqual(saved[0][1]["storage_state"], "not_attempted")
        self.assertEqual(saved[1][1]["state"], "completed")
        self.assertEqual(saved[1][1]["index_state"], "completed")
        self.assertTrue(saved[1][1]["source_current"])

    async def test_failed_index_keeps_stored_card_and_unconfirmed_write_is_unknown(self):
        for failure, expected in (("before_write", "failed"), ("unconfirmed", "unknown")):
            saved, _ = await self.exercise(failure=failure)
            self.assertEqual(saved[-1][1]["storage_state"], "stored")
            self.assertEqual(saved[-1][1]["index_state"], expected)
            self.assertEqual(saved[-1][1]["state"], expected)

    async def test_indexed_card_changed_at_source_is_not_reported_as_current(self):
        saved, _ = await self.exercise(changed=True)
        self.assertEqual(saved[-1][1]["index_state"], "completed")
        self.assertEqual(saved[-1][1]["state"], "skipped")
        self.assertFalse(saved[-1][1]["source_current"])
