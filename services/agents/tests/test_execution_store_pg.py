"""Opt-in M3.2 PostgreSQL contracts on four new, retained synthetic Runs.

Set M3_PG_TEST_CONFIG to private JSON containing ``dsn`` and ``ssl_ca``.
The fixed batch refuses existing Run IDs and performs no cleanup/replay. These
tests write only the controlled tenant's ledger fixtures: no HTTP/model calls.
Every direct SQL transaction sets a local tenant, and every ledger read carries
an explicit tenant predicate. The independent reader verifies committed rows.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import ssl
import unittest
from unittest.mock import patch
from uuid import NAMESPACE_URL, UUID, uuid5


BATCH = "investigation-m3-20261023-01"
TENANT = UUID("53824f24-d1d4-5820-8147-f6cfda8a1247")
ALERT = UUID("121d8fa6-d431-5428-b4f4-6b928b40e91b")
SOURCE_IDS = (UUID("951c5352-2df4-53d8-a431-b2763fea5e6e"),
              UUID("d92cb914-0026-509d-916a-9f9d43f03546"))
WINDOW_START = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)


def fixture_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"socai2:{BATCH}:{name}")


class ExecutionStorePostgresTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        config_path = os.environ.get("M3_PG_TEST_CONFIG")
        if not config_path:
            self.skipTest("M3_PG_TEST_CONFIG is not set; no PostgreSQL access")
        # Normal package imports are intentional; no alternate implementation.
        import asyncpg
        from app.investigation_v2 import execution_store, scope
        from app.investigation_v2.execution_state import BudgetLimits, OpeningUsage, ExecutionRejected

        self.module, self.scope_module = execution_store, scope
        self.BudgetLimits, self.OpeningUsage, self.Rejected = BudgetLimits, OpeningUsage, ExecutionRejected
        config = json.loads(Path(config_path).read_text(encoding="utf-8"))
        self.assertEqual(set(config), {"dsn", "ssl_ca"})
        context = ssl.create_default_context(cafile=config["ssl_ca"])
        self.pool = await asyncpg.create_pool(dsn=config["dsn"], ssl=context,
                                              min_size=1, max_size=3, timeout=10, command_timeout=10)
        self.addAsyncCleanup(self._close_pool)
        self.reader = await asyncpg.connect(dsn=config["dsn"], ssl=context, timeout=10, command_timeout=10)
        self.addAsyncCleanup(self.reader.close, timeout=5)

    async def _close_pool(self):
        try:
            await asyncio.wait_for(self.pool.close(), timeout=5)
        except TimeoutError:
            self.pool.terminate()
            raise

    async def _fixture(self, name: str, *, legacy: bool = False, max_unsettled: int = 2,
                       source_text: str = ""):
        self.run_id = fixture_id(name)
        self.owner = fixture_id("owner")
        self.source_text = source_text
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(TENANT))
                self.assertFalse(await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM investigation_runs WHERE id=$1 AND tenant_id=$2)",
                    self.run_id, TENANT), "fixed fixture Run already exists; do not replay or overwrite")
                now = await conn.fetchval("SELECT clock_timestamp()")
                saved = await conn.fetchval(
                    "INSERT INTO investigation_runs "
                    "(id,tenant_id,case_id,alert_summary,raw_alert,status,completed_at,total_tokens,total_cost_usd) "
                    "VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7,$8,$9) RETURNING id",
                    self.run_id, TENANT, f"{BATCH}:{name}", "M3 synthetic persistence fixture; no model call",
                    json.dumps({"fixture_batch": BATCH, "synthetic": True, "alert_id": str(ALERT)}),
                    "completed" if legacy else "running", now if legacy else None,
                    2000 if legacy else 0, Decimal("0.02") if legacy else Decimal("0"))
                self.assertEqual(saved, self.run_id)
                if legacy:
                    event = await conn.fetchval(
                        "INSERT INTO investigation_events "
                        "(id,run_id,tenant_id,seq,ts,kind,agent,summary,payload) "
                        "VALUES ($1,$2,$3,7,$4,'triage','synthetic_fixture',$5,$6::jsonb) RETURNING id",
                        fixture_id(name + ":triage-event"), self.run_id, TENANT, now,
                        "Synthetic prior triage usage; not an actual model invocation",
                        json.dumps({"synthetic": True, "known_tokens": 2000, "known_cost_microusd": 20000}))
                    self.assertEqual(event, fixture_id(name + ":triage-event"))
        self.store = self.module.ExecutionStore(self.pool, tenant_id=TENANT, run_id=self.run_id,
                                               executor_id=self.owner)
        self.context = self._scope()
        self.limits = self.BudgetLimits(
            max_model_calls=4, max_tool_calls=2, max_tokens=100, max_cost_microusd=10000,
            max_unsettled=max_unsettled, deadline=now + timedelta(minutes=10),
            config_ref=f"{BATCH}:explicit-test-budget",
            legacy_model_limit_mapping="test legacy max_tool_calls=4 -> max_model_calls=4; tool cap=2 explicit")
        self.opening = self.OpeningUsage(model_calls=1 if legacy else 0, known_tokens=2000 if legacy else 0,
                                        known_cost_microusd=20000 if legacy else 0, unknown_calls=0,
                                        unpriced_calls=0, source_ref=f"{BATCH}:{name}:synthetic-opening")

    def _scope(self):
        m = self.scope_module
        record = "pg.alerts:" + str(ALERT)
        source_values = tuple(str(value) for value in SOURCE_IDS)
        fields = (
            m.SourceField("hostname", record, "hostname", "investigation-ch-20261023-01-host"),
            m.SourceField("source_ip", record, "src_ip", "192.0.2.70"),
            m.SourceField("dest_ip", record, "dst_ip", "198.51.100.70"),
            m.SourceField("dst_port", record, "raw_event.telemetry[0].dst_port", 443),
            m.SourceField("protocol", record, "raw_event.telemetry[0].protocol", "TCP"),
            m.SourceField("source_event_ids", record, "source_event_ids", source_values),
        )
        alert = m.CheckedAlert(
            tenant_id=TENANT, alert_id=ALERT, record_ref=record,
            ownership_check_ref="D3:investigation-ch-20261023-01:association.json:passed",
            hostname="investigation-ch-20261023-01-host", source_ip="192.0.2.70",
            dest_ip="198.51.100.70", dst_port=443, protocol="TCP", source_event_ids=SOURCE_IDS, fields=fields,
            data_only_text=self.source_text)
        return m.initialize_scope(
            principal=m.TenantPrincipal(frozenset({TENANT}), "m3-controlled-fixture-caller", True),
            tenant_id=TENANT, run_id=self.run_id,
            snapshot=m.CheckedMemberSnapshot("D3:checked-canonical-alert", 1, (alert,)),
            window=m.UTCWindow(WINDOW_START, WINDOW_START + timedelta(minutes=5)))

    async def _begin(self, store=None, **changes):
        return await (store or self.store).begin(
            scope=self.context, limits=self.limits, opening=self.opening,
            input_data={"purpose": "验证预算持久化", "synthetic": True, "model_invoked": False}, **changes)

    def _request(self, number=1, **changes):
        args = dict(step_id=fixture_id(f"{self.run_id}:step:{number}"),
                    attempt_id=fixture_id(f"{self.run_id}:attempt:{number}"),
                    subtask_id=f"fixture-subtask-{number}", question_id="Q1", kind="model",
                    reserve_tokens=20, reserve_cost_microusd=1000,
                    input_data={"synthetic_prompt": "仅预算测试，不发模型", "number": number})
        args.update(changes)
        return args

    async def _read(self):
        """Separate connection, independent SQL and hashlib; no store load shortcut."""
        async with self.reader.transaction(readonly=True):
            await self.reader.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(TENANT))
            run = await self.reader.fetchrow(
                "SELECT id,tenant_id,case_id,status,completed_at,total_tokens,total_cost_usd,iterations "
                "FROM investigation_runs WHERE id=$1 AND tenant_id=$2", self.run_id, TENANT)
            events = await self.reader.fetch(
                "SELECT id,run_id,tenant_id,seq,kind,payload,input_hash,output_hash "
                "FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 ORDER BY seq", self.run_id, TENANT)
            artifacts = await self.reader.fetch(
                "SELECT id,run_id,tenant_id,event_id,kind,content,sha256,size_bytes "
                "FROM investigation_artifacts WHERE run_id=$1 AND tenant_id=$2 ORDER BY id", self.run_id, TENANT)
        self.assertIsNotNone(run)
        events, artifacts = [dict(e) for e in events], [dict(a) for a in artifacts]
        event_ids = {event["id"] for event in events}
        for event in events:
            event["payload"] = json.loads(event["payload"]) if isinstance(event["payload"], str) else event["payload"]
        for artifact in artifacts:
            self.assertEqual((artifact["run_id"], artifact["tenant_id"]), (self.run_id, TENANT))
            self.assertIn(artifact["event_id"], event_ids)
            encoded = artifact["content"].encode("utf-8")
            self.assertEqual(artifact["size_bytes"], len(encoded))
            self.assertEqual(artifact["sha256"], hashlib.sha256(encoded).hexdigest())
        return {"run": dict(run), "events": events, "artifacts": artifacts}

    def _assert_refs(self, view, result):
        receipt = result["receipt"]
        event = next(e for e in view["events"] if str(e["id"]) == receipt["event_id"])
        bodies = {str(a["id"]): a for a in view["artifacts"]}
        state = bodies[receipt["state_artifact_id"]]
        body = bodies[receipt["body_artifact_id"]]
        self.assertEqual(event["seq"], receipt["seq"])
        self.assertEqual(state["kind"], "unified_state_snapshot")
        self.assertEqual(state["event_id"], event["id"])
        self.assertEqual(body["event_id"], event["id"])
        self.assertEqual(event["payload"]["state_hash"], state["sha256"])
        self.assertEqual(receipt["body_hash"], body["sha256"])
        self.assertEqual(json.loads(state["content"]), result["state"])
        field = "output_hash" if body["kind"] == "unified_step_output" else "input_hash"
        self.assertEqual(event[field], body["sha256"])

    async def test_normal_preserves_legacy_and_commits_exactly_once(self):
        source_text = "源" * 102400  # Exactly 300 KiB in UTF-8, repeated in the two M1 views.
        self.assertEqual(len(source_text.encode("utf-8")), 300 * 1024)
        await self._fixture("normal", legacy=True, source_text=source_text)
        baseline = await self._read()
        started = await self._begin()
        self.assertEqual(started["receipt"]["seq"], 8)
        scope_hash = self.module.scope_fingerprint(self.context)
        self.assertEqual(started["state"]["scope_hash"], scope_hash)
        self.source_text = source_text + "changed"
        changed_hash = self.module.scope_fingerprint(self._scope())
        self.source_text = source_text
        self.assertNotEqual(changed_hash, scope_hash)
        before_wrong_scope = await self._read()
        with self.assertRaises(self.Rejected):
            await self.store.reserve(scope_hash=changed_hash, **self._request())
        self.assertEqual(await self._read(), before_wrong_scope)
        reserved = await self.store.reserve(scope_hash=scope_hash,
                                            **self._request(reserve_tokens=60, reserve_cost_microusd=4000))
        self.assertEqual(reserved["receipt"]["seq"], 9)
        completion = dict(attempt_id=self._request()["attempt_id"],
                          output_data={"synthetic_reply": "仅结算虚构用量", "model_invoked": False},
                          outcome="responded", actual_tokens=70, actual_cost_microusd=3000,
                          usage_source_ref=f"{BATCH}:synthetic-usage-not-provider")
        completed = await self.store.complete(**completion)
        self.assertEqual(completed["receipt"]["seq"], 10)
        self.assertEqual(completed["state"]["stage_usage"]["known_tokens"], 70)
        self.assertEqual(completed["state"]["run_total"]["total_tokens"], 2070)
        self.assertEqual(completed["state"]["run_total"]["total_cost_microusd"], 23000)
        self.assertTrue(completed["state"]["budget_breached"])
        with self.assertRaises(self.Rejected):
            await self.store.reserve(scope_hash=started["state"]["scope_hash"], **self._request(2))
        persisted = await self._read()
        self.assertEqual((len(persisted["events"]), len(persisted["artifacts"])), (4, 6))
        self.assertEqual(persisted["run"], baseline["run"])
        self.assertEqual(persisted["events"][0], baseline["events"][0])
        for result in (started, reserved, completed):
            self._assert_refs(persisted, result)
        source_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        source_ref = "scope-source:" + source_hash
        begin_body = next(a for a in persisted["artifacts"]
                          if str(a["id"]) == started["receipt"]["body_artifact_id"])
        begin_input = json.loads(begin_body["content"])
        self.assertEqual(begin_input, {
            "input": {"purpose": "验证预算持久化", "synthetic": True, "model_invoked": False},
            "scope_sources": {source_ref: source_text}, "scope_hash": scope_hash,
        })
        self.assertEqual(sum(source_text in a["content"] for a in persisted["artifacts"]), 1)
        for artifact in persisted["artifacts"]:
            if artifact["kind"] == "unified_state_snapshot":
                self.assertNotIn("源" * 20, artifact["content"])
                self.assertNotIn('"data_only_text"', artifact["content"])
                control = json.loads(artifact["content"])["scope"]
                for member in (control["member_snapshot"]["selected"][0], control["query_scope"]["members"][0]):
                    self.assertEqual(member["data_only_source"],
                                     {"ref": source_ref, "sha256": source_hash, "size_bytes": 300 * 1024})
        repeated = await self.store.complete(**completion)
        self.assertTrue(repeated["repeated"])
        self.assertEqual(repeated["receipt"], completed["receipt"])
        with self.assertRaises(self.Rejected):
            await self.store.complete(**{**completion, "output_data": {"changed": True}})
        self.assertEqual(await self._read(), persisted)

    async def test_failure_after_snapshot_insert_rolls_back_each_transition(self):
        await self._fixture("failure")
        original = self.store._insert_artifact

        async def fail_after_state(*args, **kwargs):
            await original(*args, **kwargs)
            if kwargs["kind"] == "unified_state_snapshot":
                raise RuntimeError("injected failure after state INSERT")

        baseline = await self._read()
        with self.assertRaises(self.Rejected):
            await self._begin(parent_deadline=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(await self._read(), baseline)
        with patch.object(self.store, "_insert_artifact", side_effect=fail_after_state):
            with self.assertRaises(self.module.ExecutionPersistenceError):
                await self._begin()
        self.assertEqual(await self._read(), baseline)
        earlier_deadline = self.limits.deadline - timedelta(minutes=1)
        started = await self._begin(parent_deadline=earlier_deadline)
        self.assertEqual(datetime.fromisoformat(started["state"]["limits"]["deadline"]), earlier_deadline)
        before_reserve = await self._read()
        request = self._request()
        with patch.object(self.store, "_insert_artifact", side_effect=fail_after_state):
            with self.assertRaises(self.module.ExecutionPersistenceError):
                await self.store.reserve(scope_hash=started["state"]["scope_hash"], **request)
        self.assertEqual(await self._read(), before_reserve)
        reserved = await self.store.reserve(scope_hash=started["state"]["scope_hash"], **request)
        before_complete = await self._read()
        with patch.object(self.store, "_insert_artifact", side_effect=fail_after_state):
            with self.assertRaises(self.module.ExecutionPersistenceError):
                await self.store.complete(attempt_id=request["attempt_id"], output_data={"synthetic": True},
                                          outcome="responded", actual_tokens=10, actual_cost_microusd=500,
                                          usage_source_ref="synthetic-usage")
        self.assertEqual(await self._read(), before_complete)
        state = await self.store.load()
        self.assertEqual(state, reserved["state"])
        self.assertEqual(state["attempts"][str(request["attempt_id"])]["status"], "reserved")
        self.assertEqual(state["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual(state["stage_usage"]["known_tokens"], 0)

    async def test_parallel_reservations_share_one_slot_and_do_not_collide_seq(self):
        await self._fixture("parallel", max_unsettled=1)
        started = await self._begin()
        second = self.module.ExecutionStore(self.pool, tenant_id=TENANT, run_id=self.run_id,
                                            executor_id=self.owner)
        start = asyncio.Event()

        async def compete(store, number):
            await start.wait()
            return await store.reserve(scope_hash=started["state"]["scope_hash"], **self._request(number))

        tasks = [asyncio.create_task(compete(self.store, 1)), asyncio.create_task(compete(second, 2))]
        start.set()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [result for result in results if isinstance(result, dict)]
        refusals = [result for result in results if isinstance(result, self.Rejected)]
        self.assertEqual((len(successes), len(refusals)), (1, 1), [type(result).__name__ for result in results])
        view = await self._read()
        self.assertEqual([event["seq"] for event in view["events"]], [1, 2])
        self.assertEqual(len(view["artifacts"]), 4)
        self._assert_refs(view, successes[0])
        state = await self.store.load()
        self.assertEqual(state["stage_usage"]["model_calls"], 1)
        self.assertEqual(state["stage_usage"]["unsettled_attempts"], 1)
        self.assertEqual(len(state["attempts"]), 1)

    async def test_unknown_cannot_reset_change_owner_cross_tenant_or_retry(self):
        await self._fixture("unknown", max_unsettled=1)
        started = await self._begin()
        scope_hash = started["state"]["scope_hash"]
        request = self._request()
        await self.store.reserve(scope_hash=scope_hash, **request)
        unknown = await self.store.complete(
            attempt_id=request["attempt_id"], output_data={"synthetic_transport_outcome": "unknown"},
            outcome="unknown", actual_tokens=None, actual_cost_microusd=None,
            usage_source_ref="synthetic-unknown-no-real-call")
        baseline = await self._read()
        self._assert_refs(baseline, unknown)
        attempts = unknown["state"]["attempts"]
        attempt = attempts[str(request["attempt_id"])]
        self.assertEqual((attempt["remaining_tokens"], attempt["remaining_cost_microusd"]), (20, 1000))
        self.assertIsNone(attempt["actual_tokens"])
        self.assertIsNone(attempt["actual_cost_microusd"])
        self.assertEqual(unknown["state"]["stage_usage"]["unknown_attempts"], 1)
        other_owner = self.module.ExecutionStore(self.pool, tenant_id=TENANT, run_id=self.run_id,
                                                 executor_id=fixture_id("other-owner"))
        other_tenant = self.module.ExecutionStore(self.pool, tenant_id=fixture_id("other-tenant"),
                                                  run_id=self.run_id, executor_id=self.owner)
        for label, store in (("same-owner reset", self.store), ("owner takeover", other_owner)):
            with self.subTest(label=label), self.assertRaises(self.Rejected):
                await self._begin(store)
        for label, store in (("other-owner load", other_owner), ("other-tenant load", other_tenant)):
            with self.subTest(label=label), self.assertRaises(self.Rejected):
                await store.load()
        with self.assertRaises(self.Rejected):
            await self.store.reserve(scope_hash=scope_hash,
                                     **{**request, "attempt_id": fixture_id("unknown:retry"),
                                        "retry_of": request["attempt_id"]})
        with self.assertRaises(self.Rejected):
            await self.store.reserve(scope_hash=scope_hash, **self._request(2))
        self.assertEqual(await self._read(), baseline)


if __name__ == "__main__":
    unittest.main()
