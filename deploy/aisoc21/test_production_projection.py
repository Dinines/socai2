"""Offline production ingress checks. Run with services/fusion on PYTHONPATH."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import production_projection as worker
from aiokafka import TopicPartition
from processing_audit_seed import fixtures
from production_ingress import IngressError, source_delivery, sync_subject


class TestProductionProjection(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from app.services.delivery_recovery import make_snapshot

        self.fused = fixtures()[0][1][0]
        self.tenant, self.alert, self.incident = self.fused.tenant_id, self.fused.id, self.fused.incident_id
        self.row = {"tenant_id": self.tenant, "id": self.alert, "source_incident_id": str(self.incident),
                    "snapshot": make_snapshot(self.fused)}
        self.packet = {"tenant_id": str(self.tenant), "id": str(self.alert), "alert_row_id": str(self.alert),
                       "incident_id": str(self.incident), "persist_outcome": "inserted"}
        self.record = SimpleNamespace(value=json.dumps(self.packet), offset=21, partition=2)

    def test_source_preserves_original_and_ids(self):
        for by_incident, subject in ((False, self.alert), (True, self.incident)):
            restored, raw = source_delivery(self.row, self.tenant, subject, by_incident)
            self.assertEqual(restored, self.fused)
            self.assertEqual(raw, self.row["snapshot"])

    def test_missing_tampered_and_foreign_rows_rejected(self):
        bad = dict(self.row["snapshot"], sha256="a" * 64)
        for fields in ({"snapshot": None}, {"snapshot": bad}, {"id": UUID(int=1)},
                       {"tenant_id": UUID(int=2)}, {"source_incident_id": str(UUID(int=3))}):
            with self.subTest(fields=fields.keys()), self.assertRaises(IngressError):
                source_delivery(self.row | fields, self.tenant, self.alert, False)

    async def test_commit_follows_projection_and_failure_holds(self):
        consumer = AsyncMock()
        with patch.object(worker, "project", new_callable=AsyncMock) as project:
            await worker.handle(consumer, self.record)
            project.assert_awaited_once_with(self.tenant, [self.alert], [], expected_incident=self.incident)
            consumer.commit.assert_awaited_once_with({TopicPartition(worker.TOPIC, 2): 22})
            consumer.commit.reset_mock()
            project.side_effect = IngressError("source_subject_absent")
            with self.assertRaises(IngressError):
                await worker.handle(consumer, self.record)
            consumer.commit.assert_not_awaited()

    async def test_malformed_packet_cannot_acknowledge(self):
        consumer = AsyncMock()
        for bad in ({"alert_row_id": str(UUID(int=1))}, {"persist_outcome": "failed"}, {"incident_id": None}):
            self.record.value = json.dumps(self.packet | bad)
            with self.assertRaises(IngressError):
                await worker.handle(consumer, self.record)
        consumer.commit.assert_not_awaited()

    async def test_existing_native_subject_only_suffices_for_manual_jobs(self):
        async def empty(*_args, **_kwargs):
            for row in []:
                yield row
        conn = SimpleNamespace(cursor=empty, fetchval=AsyncMock(return_value=True))
        self.assertEqual(await sync_subject(conn, None, self.tenant, self.alert, False), 0)
        with self.assertRaisesRegex(IngressError, "source_subject_absent"):
            await sync_subject(conn, None, self.tenant, self.alert, False, expected_incident=self.incident)

    async def test_conflicting_existing_snapshot_or_event_never_enters_sink(self):
        async def cursor(*_args, **_kwargs):
            yield self.row
        conn = SimpleNamespace(cursor=cursor, fetchval=AsyncMock(return_value="another_hash"))
        sink = SimpleNamespace(_write=AsyncMock())
        with self.assertRaisesRegex(IngressError, "source_identity_mismatch"):
            await sync_subject(conn, sink, self.tenant, self.alert, False)
        with self.assertRaisesRegex(IngressError, "notification_incident_mismatch"):
            await sync_subject(conn, sink, self.tenant, self.alert, False, expected_incident=UUID(int=1))
        sink._write.assert_not_awaited()

    async def test_activate_fixes_start_and_never_advances_existing_offset(self):
        consumer = MagicMock(commit=AsyncMock())
        pos = {"0": {"begin": 0, "end": 4, "committed": None}}
        with tempfile.TemporaryDirectory() as folder, patch.object(worker, "BOUNDARY", Path(folder) / "start.json"):
            first = await worker.activate(consumer, pos)
            consumer.assign.assert_called_once_with([TopicPartition(worker.TOPIC, 0)])
            consumer.commit.assert_awaited_once_with({TopicPartition(worker.TOPIC, 0): 4})
            consumer.commit.reset_mock()
            pos["0"].update(end=20, committed=11)
            self.assertEqual(await worker.activate(consumer, pos), first)
            consumer.commit.assert_not_awaited()
            pos["0"]["committed"] = None
            with self.assertRaisesRegex(IngressError, "offset_missing"):
                worker.validate_offsets(pos, first)
            pos["0"]["begin"] = 15
            with self.assertRaisesRegex(IngressError, "out_of_range"):
                await worker.activate(consumer, pos)
            consumer.commit.assert_not_awaited()
