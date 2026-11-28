"""Bounded lake discovery and durable ordered delivery to the 4b receiver."""
from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

from app.services.lake_alert_receiver import ReceiveResult
from app.services.lake_alert_selection import (
    reconcile_immutable_versions,
    select_alert,
    validate_read_limits,
)
from app.services.receipt_json import decoded, encoded

FIELDS = ("tenant_id", "source_namespace", "mapping_version", "event_id", "source_version", "event_time", "class_uid",
          "parse_status", "source_event_id", "ocsf_json", "event_time_source")
OPEN_STATES = ("pending", "receiving", "failed", "unknown", "held")


@dataclass(frozen=True)
class DeliveryPolicy:
    body: dict
    directory: Path

    @classmethod
    def load(cls, path):
        path = Path(path)
        body = json.loads(path.read_text())
        required = {"version", "enabled", "selection_profile_file", "receive_profile_file", "connection_file",
                    "poll_interval_seconds", "max_deliveries_per_cycle", "statement_timeout_seconds", "runtime"}
        if set(body) not in (required, required | {"read_limits"}) or body["version"] != "socai2.lake-alert-delivery.v1" or type(body["enabled"]) is not bool:
            raise ValueError("invalid_delivery_profile")
        if "read_limits" in body:
            validate_read_limits(body["read_limits"])
        for key in ("selection_profile_file", "receive_profile_file", "connection_file"):
            if not isinstance(body[key], str) or not body[key].strip():
                raise ValueError("explicit_delivery_files_required")
        for key in ("poll_interval_seconds", "max_deliveries_per_cycle", "statement_timeout_seconds"):
            if type(body[key]) is not int or body[key] <= 0:
                raise ValueError("invalid_delivery_limits")
        runtime = body["runtime"]
        if set(runtime) != {"dedup_window_seconds", "correlation_window_seconds", "max_alerts_per_incident", "confidence_enabled", "log_level"}:
            raise ValueError("explicit_delivery_runtime_required")
        if (any(type(runtime[k]) is not int or runtime[k] <= 0 for k in
                ("dedup_window_seconds", "correlation_window_seconds", "max_alerts_per_incident"))
                or type(runtime["confidence_enabled"]) is not bool or runtime["log_level"] not in {"WARNING", "ERROR"}):
            raise ValueError("invalid_delivery_runtime")
        return cls(body, path.resolve().parent)

    def file(self, name):
        return self.directory / self.body[name]

    def read_limits(self, selection):
        return dict(self.body.get("read_limits", selection.body["read_limits"]))


def binding_digest(selection, receive):
    return hashlib.sha256(encoded({"selection": selection.body, "receive": receive.body}).encode()).hexdigest()


def decide(rows, selection):
    decisions = reconcile_immutable_versions([select_alert(row, selection) for row in rows])
    if len({d["delivery_key"] for d in decisions}) != len(decisions):
        raise ValueError("duplicate_lake_version_after_dedup")
    return [(row, decision) for row, decision in zip(rows, decisions, strict=True)]


def initial_state(decision):
    if decision["action"] == "new_alert_candidate" and (decision["identity"] or {}).get("ready"):
        return "pending"
    return "lake_only" if decision["action"] == "lake_only" else "review"


class LakeDeliverySource:
    def __init__(self, client, selection, *, read_limits=None):
        self.client, self.selection = client, selection
        self.read_limits = dict(selection.body["read_limits"] if read_limits is None else read_limits)
        validate_read_limits(self.read_limits)

    def _scan(self):
        policy = self.selection
        limits, scope = self.read_limits, policy.scope()
        settings = {"readonly": 2, "max_execution_time": limits["query_timeout_seconds"],
                    "max_result_rows": limits["max_records"]+1, "max_result_bytes": limits["max_result_bytes"],
                    "result_overflow_mode": "throw"}
        base = f"FROM {policy.body['database']}.raw_events WHERE tenant_id=%(tenant_id)s AND source_namespace=%(source_namespace)s AND mapping_version=%(mapping_version)s"
        count = self.client.execute("SELECT uniqExact(tuple(event_time,class_uid,event_id)) "+base, scope, settings=settings)[0][0]
        if not 0 <= count <= limits["max_records"]:
            raise ValueError("lake_delivery_scan_exceeds_limit")
        fields = ",".join(FIELDS)
        values = self.client.execute(f"""SELECT {fields} FROM (
            SELECT {fields}, row_number() OVER (PARTITION BY tenant_id,event_time,class_uid,event_id
              ORDER BY ingest_time DESC,kafka_topic DESC,kafka_partition DESC,kafka_offset DESC) AS source_rank
            {base}) WHERE source_rank=1 ORDER BY event_time,class_uid,event_id LIMIT %(fetch_limit)s""",
            {**scope, "fetch_limit": limits["max_records"]+1}, settings=settings)
        if len(values) != count:
            raise ValueError("lake_delivery_scan_incomplete_or_changed")
        return [dict(zip(FIELDS, row, strict=True)) for row in values]

    async def scan(self):
        task = asyncio.create_task(asyncio.to_thread(self._scan))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            try:
                await task
            finally:
                raise


class DeliveryStore:
    def __init__(self, pool, selection, receive, policy):
        self.pool, self.selection, self.receive, self.policy = pool, selection, receive, policy
        self.tenant = UUID(selection.body["tenant_id"])
        self.scope = (self.tenant, selection.body["database"], selection.body["source_namespace"], selection.body["mapping_version"])
        self.binding = binding_digest(selection, receive)
        self.lock_key = int.from_bytes(hashlib.sha256(encoded([str(x) for x in self.scope]).encode()).digest()[:8], signed=True)

    @asynccontextmanager
    async def locked(self):
        async with self.pool.acquire() as conn:
            if await conn.fetchval("SELECT current_database()") != self.receive.body["postgres_database"]:
                raise ValueError("delivery_database_mismatch")
            await conn.execute("SELECT set_config('statement_timeout',$1,false)", str(self.policy.body["statement_timeout_seconds"])+"s")
            obtained = await conn.fetchval("SELECT pg_try_advisory_lock($1::bigint)", self.lock_key)
            try:
                yield conn if obtained else None
            finally:
                if obtained and not conn.is_closed():
                    await conn.execute("SELECT pg_advisory_unlock($1::bigint)", self.lock_key)

    @asynccontextmanager
    async def transaction(self, conn):
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(self.tenant))
            yield

    async def register(self, conn, selected):
        async with self.transaction(conn):
            changed = await conn.fetchval("""SELECT 1 FROM socai2.lake_alert_deliveries
                WHERE tenant_id=$1 AND lake_database=$2 AND source_namespace=$3 AND mapping_version=$4
                  AND binding_digest<>$5 LIMIT 1""", *self.scope, self.binding)
            if changed:
                raise ValueError("delivery_binding_changed")
            for _, decision in selected:
                identity = (decision["identity"] or {}).get("source_subject_id")
                inserted = await conn.fetchval("""INSERT INTO socai2.lake_alert_deliveries
                    (id,tenant_id,lake_database,source_namespace,mapping_version,lake_ref,binding_digest,decision,source_subject_id,state)
                    VALUES($1,$2,$3,$4,$5,$6::jsonb,$7,$8::jsonb,$9,$10) ON CONFLICT(id) DO NOTHING RETURNING id""",
                    UUID(decision["delivery_key"]), *self.scope, encoded(decision["lake_ref"]), self.binding,
                    encoded(decision), UUID(identity) if identity else None, initial_state(decision))
                if inserted is None:
                    prior = await conn.fetchrow("""SELECT lake_database,binding_digest,lake_ref FROM socai2.lake_alert_deliveries
                        WHERE tenant_id=$1 AND id=$2""", self.tenant, UUID(decision["delivery_key"]))
                    if (prior is None or prior["lake_database"] != self.scope[1] or prior["binding_digest"] != self.binding
                            or decoded(prior["lake_ref"]) != decision["lake_ref"]):
                        raise ValueError("delivery_identity_scope_conflict")

    async def head(self, conn):
        async with self.transaction(conn):
            return await conn.fetchrow("""SELECT * FROM socai2.lake_alert_deliveries
                WHERE tenant_id=$1 AND lake_database=$2 AND source_namespace=$3 AND mapping_version=$4
                  AND state=ANY($5::text[]) ORDER BY created_at,id LIMIT 1""", *self.scope, list(OPEN_STATES))

    async def begin(self, conn, item):
        async with self.transaction(conn):
            # An unfinished earlier attempt remains unknown forever; recovery
            # is a separate attempt, not a rewrite of that history.
            await conn.execute("""UPDATE socai2.lake_alert_delivery_attempts
                SET outcome='unknown',reason='previous_attempt_interrupted',ended_at=clock_timestamp()
                WHERE tenant_id=$1 AND delivery_id=$2 AND ended_at IS NULL""", self.tenant, item["id"])
            number = await conn.fetchval("""UPDATE socai2.lake_alert_deliveries
                SET state='receiving',reason=NULL,attempt_count=attempt_count+1,updated_at=clock_timestamp()
                WHERE tenant_id=$1 AND id=$2 AND state=ANY($3::text[]) RETURNING attempt_count""",
                self.tenant, item["id"], list(OPEN_STATES))
            if number is None:
                raise ValueError("delivery_head_changed")
            await conn.execute("""INSERT INTO socai2.lake_alert_delivery_attempts
                (tenant_id,delivery_id,attempt_no,outcome) VALUES($1,$2,$3,'receiving')""", self.tenant, item["id"], number)
        return number

    async def finish(self, conn, item, number, result, *, recovered=False):
        durable = result.durable
        outcome = "recovered" if durable and recovered else result.state
        if outcome not in {"created", "duplicate", "recovered", "failed", "unknown", "held"}:
            raise ValueError("unsupported_delivery_result")
        async with self.transaction(conn):
            updated = await conn.fetchval("""UPDATE socai2.lake_alert_deliveries
                SET state=$4,reason=$5,alert_id=$6,material_id=$7,
                    confirmed_at=CASE WHEN $4='delivered' THEN clock_timestamp() ELSE NULL END,updated_at=clock_timestamp()
                WHERE tenant_id=$1 AND id=$2 AND attempt_count=$3 AND state='receiving' RETURNING id""",
                self.tenant, item["id"], number, "delivered" if durable else result.state, result.reason,
                UUID(result.alert_id) if durable else None, UUID(result.material_id) if durable else None)
            if updated is None:
                raise ValueError("delivery_attempt_ownership_lost")
            updated = await conn.fetchval("""UPDATE socai2.lake_alert_delivery_attempts
                SET outcome=$4,reason=$5,receipt=$6::jsonb,ended_at=clock_timestamp()
                WHERE tenant_id=$1 AND delivery_id=$2 AND attempt_no=$3 AND ended_at IS NULL RETURNING attempt_no""",
                self.tenant, item["id"], number, outcome, result.reason, encoded(asdict(result)))
            if updated is None:
                raise ValueError("delivery_attempt_missing")
        # The caller cannot count/advance before this transaction has committed.


@dataclass(frozen=True)
class DeliveryCycle:
    state: str
    reason: str
    delivered: int = 0


class LakeAlertDelivery:
    def __init__(self, source, receiver, store, policy):
        self.source, self.receiver, self.store, self.policy = source, receiver, store, policy
        if (not receiver.selection.immutable or source.selection.body != receiver.selection.body
                or store.binding != binding_digest(receiver.selection, receiver.policy)):
            raise ValueError("delivery_components_mismatch")

    async def cycle(self, *, deliver=True):
        count = 0
        try:
            async with self.store.locked() as conn:
                if conn is None:
                    return DeliveryCycle("busy", "delivery_scope_already_running")
                selected = decide(await self.source.scan(), self.receiver.selection)
                await self.store.register(conn, selected)
                if not deliver:
                    return DeliveryCycle("staged", "durable_registration_completed")
                current = {d["delivery_key"]: (row, d) for row, d in selected}
                for _ in range(self.policy.body["max_deliveries_per_cycle"]):
                    item = await self.store.head(conn)
                    if item is None:
                        return DeliveryCycle("completed", "delivery_queue_drained", count)
                    number = await self.store.begin(conn, item)
                    recovered = item["state"] in {"receiving", "unknown"}
                    pair = current.get(str(item["id"]))
                    if pair is None:
                        result = ReceiveResult("unknown", "queued_lake_version_not_observed")
                    else:
                        row, decision = pair
                        if encoded(decision["lake_ref"]) != encoded(decoded(item["lake_ref"])):
                            result = ReceiveResult("held", "queued_lake_reference_mismatch")
                        elif initial_state(decision) != "pending":
                            result = ReceiveResult("held", "current_selection_not_deliverable")
                        elif recovered:
                            observed = await self.receiver.lookup_receipt(row, decision=decision)
                            result = observed if observed.durable else ReceiveResult("unknown", "prior_delivery_not_proven")
                        else:
                            result = await self.receiver.receive(row, decision=decision)
                            if result.durable:
                                observed = await self.receiver.lookup_receipt(row, decision=decision)
                                if (not observed.durable or (observed.alert_id, observed.material_id) != (result.alert_id, result.material_id)):
                                    result = ReceiveResult("unknown", "committed_delivery_not_proven")
                    await self.store.finish(conn, item, number, result, recovered=recovered)
                    if not result.durable:
                        return DeliveryCycle("blocked", result.reason or "delivery_not_confirmed", count)
                    count += 1
                return DeliveryCycle("completed", "delivery_cycle_limit_reached", count)
        except Exception:  # noqa: BLE001 -- any unconfirmed transaction stops the loop.
            return DeliveryCycle("unknown", "delivery_cycle_unconfirmed", count)
