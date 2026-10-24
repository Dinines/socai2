"""Atomic manual program admission. No HTTP/auth implementation or dispatch.

The caller supplies a currently authenticated principal/actor. This store owns
tenant-qualified Alert reads and the Run/begin/intent transaction. Legacy writer
exclusion and actual run/read permissions remain entry-policy prerequisites.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from uuid import UUID, uuid4

from .business_profile import BusinessProfileRequest
from .execution_state import BudgetLimits, OpeningUsage, ExecutionRejected, initial_state
from .execution_store import ExecutionPersistenceError, canonical_json, content_hash, scope_snapshot, _object
from .program_alert_projection import project_program_alert_start
from .program_profile_restore import restore_program_alert_read_request
from .program_recon_publication_store import ProgramReconPublicationStore
from .program_result_reader import _owned_artifact
from .program_runtime_state import RUNTIME_VERSION, install_program_recon, make_program_recon_plan
from .program_runtime_store import CONTROL_KINDS
from .program_start_contract import _checked_program_intent
from .scope import PrincipalScope, TenantPrincipal
from .start_contract import StartBudgetPolicy

EVENT_KIND = "program_alert_start_admitted"
EVENT_AGENT = "program_alert_recon_start.v1"
ARTIFACT_KIND = "program_alert_start_intent"
ADMISSION_SCHEMA = "program_alert_start_admission.v1"
PIN_SCHEMA = "program_alert_start_admission_pin.v1"
RECEIPT_SCHEMA = "program_alert_start_admission_receipt.v1"
LEGACY_FIELDS = ("id", "tenant_id", "status", "completed_at", "total_tokens", "total_cost_usd")
RUN_COLUMNS = ",".join((*LEGACY_FIELDS, "case_id"))


def _require(value, reason):
    if not value:
        raise ExecutionRejected(reason)


def _same(left, right, reason):
    _require(canonical_json(left) == canonical_json(right), reason)


def _time(value):
    if isinstance(value, str): value = datetime.fromisoformat(value)
    _require(isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None,
             "admission timestamp must have timezone")
    return value.astimezone(timezone.utc)


def _limits(policy, admitted_at, parent_deadline):
    end = _time(admitted_at) + timedelta(seconds=policy.duration_seconds)
    if parent_deadline is not None: end = min(end, _time(parent_deadline))
    return BudgetLimits(**{k: v for k, v in asdict(policy).items() if k != "duration_seconds"}, deadline=end)


def _opening(run_id):
    return OpeningUsage(0, 0, 0, 0, 0, "confirmed-new-manual-run:" + str(run_id))


def _ref(row):
    return {"artifact_id": str(row["id"]), "sha256": row["sha256"]}


@dataclass(frozen=True)
class AdmittedProgramOperation:
    request: BusinessProfileRequest
    receipt: dict


class ProgramAlertStartStore:
    def __init__(self, pool, *, budget_policy: StartBudgetPolicy):
        _require(pool is not None and isinstance(budget_policy, StartBudgetPolicy), "explicit admission pool and server budget required")
        self.pool = pool
        self.budget_policy = StartBudgetPolicy(**asdict(budget_policy))

    def _authorize(self, intent, current_principal, current_actor_id):
        intent = _checked_program_intent(intent)
        _require(isinstance(current_principal, TenantPrincipal), "current authenticated principal required")
        principal = PrincipalScope(current_principal.tenant_ids, current_principal.subject, current_principal.delegated)
        try: actor = UUID(str(current_actor_id))
        except (ValueError, TypeError, AttributeError): raise ExecutionRejected("current actor UUID required") from None
        _require(actor.int != 0 and str(actor) == intent["request"]["actor_id"]
                 and UUID(intent["request"]["tenant_id"]) in principal.tenant_ids, "current actor or tenant differs from start request")
        _same(intent["request"]["budget_policy"], self.budget_policy.descriptor, "intent budget differs from current trusted server policy")
        return intent

    @asynccontextmanager
    async def _transaction(self, tenant):
        try:
            async with self.pool.acquire() as conn:
                # Locking alone does not refresh a repeatable-read snapshot.
                async with conn.transaction(isolation="read_committed"):
                    await conn.execute("SELECT set_config('app.current_tenant_id', $1, true)", str(tenant))
                    yield conn
        except ExecutionRejected:
            raise
        except Exception as exc:
            raise ExecutionPersistenceError("admission transaction not confirmed; entering runtime/replay forbidden") from exc

    async def _run(self, conn, tenant, run_id):
        return await conn.fetchrow("SELECT " + RUN_COLUMNS + " FROM investigation_runs WHERE id=$1 AND tenant_id=$2 FOR UPDATE", run_id, tenant)

    async def _read_locked(self, conn, run, principal, expected_intent=None):
        try:
            return await self._checked_read_locked(conn, dict(run), principal, expected_intent)
        except ExecutionRejected:
            raise
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ExecutionRejected("owned admission format or original anchors rejected") from None

    async def _checked_read_locked(self, conn, run, principal, expected_intent):
        tenant, run_id = UUID(str(run["tenant_id"])), UUID(str(run["id"]))
        _require(tenant in principal.tenant_ids, "current principal cannot read admitted tenant")
        events = await conn.fetch("SELECT id,tenant_id,run_id,seq,ts,kind,agent,payload,input_hash,output_hash "
            "FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 AND kind=ANY($3::text[]) ORDER BY seq ASC LIMIT 2",
            run_id, tenant, [EVENT_KIND])
        _require(len(events) == 1, "unique owned admission marker required; existing Run cannot be upgraded")
        event = events[0]; pin = _object(event["payload"])
        _require((event["run_id"], event["tenant_id"], event["kind"], event["agent"]) == (run_id, tenant, EVENT_KIND, EVENT_AGENT)
                 and type(event["seq"]) is int and event["seq"] >= 1, "typed owned admission event required")
        _require(set(pin) == {"schema", "event_id", "seq", "tenant_id", "run_id", "executor_id", "body_artifact_id", "body_hash", "begin", "scope_hash"}
                 and pin["schema"] == PIN_SCHEMA, "admission event pin shape differs")
        _same([pin["event_id"], pin["seq"], pin["tenant_id"], pin["run_id"]],
              [str(event["id"]), event["seq"], str(tenant), str(run_id)], "admission event pin identity differs")
        artifact = await _owned_artifact(conn, tenant_id=tenant, run_id=run_id, artifact_id=UUID(pin["body_artifact_id"]),
                                         event_id=event["id"], kind=ARTIFACT_KIND)
        _require(pin["body_hash"] == artifact["sha256"] == event["input_hash"] and event["output_hash"] is None,
                 "admission intent is not pinned by immutable event")
        document = _object(artifact["content"])
        _require(set(document) == {"schema", "intent", "run_anchor", "begin", "scope_hash", "admitted_at", "parent_deadline"}
                 and document["schema"] == ADMISSION_SCHEMA, "admission document shape differs")
        original = _checked_program_intent(document["intent"])
        if expected_intent is not None: _same(original, expected_intent, "operation key is bound to a different start request")
        _same([original["run_id"], original["request"]["tenant_id"], original["executor_id"]],
              [str(run_id), str(tenant), pin["executor_id"]], "admitted operation identities differ")
        target_id = original["request"]["target"]["id"]
        _require(run["case_id"] == "v2-alert:" + target_id and run["status"] == "running" and run["completed_at"] is None
                 and type(run["total_tokens"]) is int and run["total_tokens"] == 0
                 and type(run["total_cost_usd"]) is not bool and run["total_cost_usd"] == 0, "new manual Run anchor changed")
        _same(document["run_anchor"], run, "original admission Run fields changed")
        _same(document["begin"], pin["begin"], "admission begin references differ")
        _require(set(pin["begin"]) == {"event_id", "input", "state"}, "admission begin pin shape differs")
        store = ProgramReconPublicationStore(self.pool, tenant_id=tenant, run_id=run_id, executor_id=UUID(pin["executor_id"]))
        begin = await store._event(conn, UUID(pin["begin"]["event_id"]))
        _require(begin["kind"] == CONTROL_KINDS[0] and type(begin["seq"]) is int and begin["seq"] >= 1
                 and begin["seq"] < event["seq"], "original program begin must precede admission marker")
        bp = _object(begin["payload"])
        body = await _owned_artifact(conn, tenant_id=tenant, run_id=run_id, artifact_id=UUID(bp["body_artifact_id"]), event_id=begin["id"], kind="unified_step_input")
        snapshot = await _owned_artifact(conn, tenant_id=tenant, run_id=run_id, artifact_id=UUID(bp["state_artifact_id"]), event_id=begin["id"], kind="unified_state_snapshot")
        _same(_ref(body), pin["begin"]["input"], "admission original input reference changed")
        _same(_ref(snapshot), pin["begin"]["state"], "admission original state reference changed")
        _require(bp["body_hash"] == begin["input_hash"] == body["sha256"] and bp["state_hash"] == snapshot["sha256"]
                 and begin["output_hash"] is None, "original begin event pins differ")
        state, original_input = _object(snapshot["content"]), _object(body["content"])
        await store._check_event_bodies(conn, begin, state)
        request = restore_program_alert_read_request(current_principal=principal, begin_input=original_input, begin_state=state)
        _same(state["executor_id"], original["executor_id"], "original executor differs")
        _same(state["scope_hash"], document["scope_hash"], "admission scope differs")
        _same(pin["scope_hash"], state["scope_hash"], "admission event scope differs")
        _same(state["legacy_run_snapshot"], {k: run[k] for k in LEGACY_FIELDS}, "legacy Run snapshot changed")
        _same(_time(document["admitted_at"]), _time(state["updated_at"]), "admitted timestamp differs from original begin")
        policy = StartBudgetPolicy(**{k: v for k, v in original["request"]["budget_policy"].items() if k != "schema"})
        _same(state["limits"], {**asdict(_limits(policy, document["admitted_at"], document["parent_deadline"])), "currency": "USD"},
              "original admission deadline or limits differ")
        _same(state["opening_usage"], asdict(_opening(run_id)), "manual opening usage differs")
        source = json.loads(request.context.member_snapshot.selected[0].data_only_text)["source"]
        frozen = request.context.principal
        rebuilt = project_program_alert_start(intent=original, current_principal=TenantPrincipal(frozen.tenant_ids, frozen.subject, frozen.delegated),
            canonical_alert=source, ownership_check_ref=self._ownership_ref(tenant, target_id))
        _same(scope_snapshot(rebuilt.context), scope_snapshot(request.context), "frozen source does not bind the original start window or scope")
        _same(rebuilt.descriptor, request.descriptor, "frozen source profile differs from original intent")
        unknown = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 "
            "AND kind LIKE 'unified_%' AND (NOT (kind=ANY($3::text[])) OR agent IS DISTINCT FROM $4))",
            run_id, tenant, list(store.event_kinds), RUNTIME_VERSION)
        _require(not unknown, "unknown or mixed managed event; admission fallback forbidden")
        # Strongly verify publication if present, without nested Run locks.
        await store._read_result_locked(conn, request)
        current = await store._load(conn)
        return request, original, document, pin, artifact, current

    @staticmethod
    def _ownership_ref(tenant, target):
        return "pg.alerts:owned:" + str(tenant) + ":" + str(target)

    def _output(self, checked, *, fresh):
        request, intent, document, pin, artifact, state = checked
        receipt = dict(schema=RECEIPT_SCHEMA, tenant_id=intent["request"]["tenant_id"], run_id=intent["run_id"],
            executor_id=intent["executor_id"], intent_ref=intent["intent_ref"], request_hash=intent["request_hash"],
            fresh=fresh, may_enter_runtime=fresh, external_call_authorized=False, persistence_status="committed",
            admission_artifact=_ref(artifact), admission_event_id=pin["event_id"], begin=pin["begin"],
            original_deadline=state["limits"]["deadline"], phase=state["recon"]["phase"])
        return AdmittedProgramOperation(request, json.loads(canonical_json(receipt)))

    async def read_operation(self, *, intent, current_principal, current_actor_id):
        intent = self._authorize(intent, current_principal, current_actor_id)
        tenant, run_id = UUID(intent["request"]["tenant_id"]), UUID(intent["run_id"])
        async with self._transaction(tenant) as conn:
            run = await self._run(conn, tenant, run_id)
            _require(run is not None, "owned admitted Run not found")
            checked = await self._read_locked(conn, run, current_principal, intent)
        return self._output(checked, fresh=False)

    async def admit(self, *, intent, current_principal, current_actor_id, parent_deadline=None):
        intent = self._authorize(intent, current_principal, current_actor_id)
        tenant, run_id, target = UUID(intent["request"]["tenant_id"]), UUID(intent["run_id"]), UUID(intent["request"]["target"]["id"])
        if parent_deadline is not None: parent_deadline = _time(parent_deadline)
        fresh = False
        async with self._transaction(tenant) as conn:
            run = await self._run(conn, tenant, run_id)
            if run is None:
                alert = await conn.fetchrow("SELECT id,tenant_id,source_event_ids,raw_event FROM alerts WHERE id=$1 AND tenant_id=$2 FOR UPDATE", target, tenant)
                _require(alert is not None, "owned canonical Alert not found")
                # All decisions below are re-queried AFTER the Alert row lock.
                run = await self._run(conn, tenant, run_id)
                if run is None:
                    candidates = await conn.fetch("SELECT " + RUN_COLUMNS + " FROM investigation_runs WHERE tenant_id=$1 AND case_id=$2 ORDER BY id FOR UPDATE",
                                                   tenant, "v2-alert:" + str(target))
                    for candidate in candidates:
                        prior = await self._read_locked(conn, candidate, current_principal)
                        current = prior[-1]
                        _require(current["recon"]["phase"] == "stopped" and current["stage_usage"]["unsettled_attempts"] == 0
                                 and current["run_total"]["unknown_calls"] == 0, "another admitted operation is active or unsettled for this Alert")
                    run = await conn.fetchrow("INSERT INTO investigation_runs (id,tenant_id,case_id,status,total_tokens,total_cost_usd) "
                        "VALUES ($1,$2,$3,'running',0,0) ON CONFLICT (id) DO NOTHING RETURNING " + RUN_COLUMNS,
                        run_id, tenant, "v2-alert:" + str(target))
                    if run is None:
                        run = await self._run(conn, tenant, run_id)
                        _require(run is not None, "operation identity conflicts with an unavailable owned Run")
                    else:
                        await self._create_locked(conn, dict(run), dict(alert), intent, current_principal, parent_deadline)
                        fresh = True
            checked = await self._read_locked(conn, run, current_principal, intent)
        # Reaching this point, including transaction __aexit__, is required.
        return self._output(checked, fresh=fresh)

    async def _create_locked(self, conn, run, alert, intent, principal, parent_deadline):
        tenant, run_id, owner = UUID(intent["request"]["tenant_id"]), UUID(intent["run_id"]), UUID(intent["executor_id"])
        _require(not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM investigation_events WHERE run_id=$1)", run_id), "new Run already has ledger history")
        request = project_program_alert_start(intent=intent, current_principal=principal, canonical_alert=alert,
                                             ownership_check_ref=self._ownership_ref(tenant, intent["request"]["target"]["id"]))
        controls, sources = scope_snapshot(request.context)
        body = canonical_json(dict(input=dict(business_profile=request.descriptor, runtime_plan=make_program_recon_plan(request)),
                                   scope_sources=sources, scope_hash=content_hash(canonical_json(controls))))
        now = _time(await conn.fetchval("SELECT clock_timestamp()")); body_id = uuid4()
        store = ProgramReconPublicationStore(self.pool, tenant_id=tenant, run_id=run_id, executor_id=owner)
        state = initial_state(scope=controls, input_snapshot_ref="urn:uuid:" + str(body_id), input_hash=content_hash(body),
            limits=_limits(self.budget_policy, now, parent_deadline), opening=_opening(run_id), executor_id=owner, now=now)
        state = install_program_recon(state, request, now=now)
        state["legacy_run_snapshot"] = json.loads(canonical_json({k: run[k] for k in LEGACY_FIELDS}))
        saved = await store._append(conn, state, kind=CONTROL_KINDS[0], body=body, body_id=body_id, body_kind="unified_step_input", now=now)
        bp = saved["receipt"]
        begin = dict(event_id=bp["event_id"], input=dict(artifact_id=bp["body_artifact_id"], sha256=bp["body_hash"]),
                     state=dict(artifact_id=bp["state_artifact_id"], sha256=content_hash(canonical_json(saved["state"]))))
        document = dict(schema=ADMISSION_SCHEMA, intent=intent, run_anchor=run, begin=begin, scope_hash=state["scope_hash"],
                        admitted_at=now, parent_deadline=parent_deadline)
        text = canonical_json(document); artifact_id, event_id = uuid4(), uuid4()
        seq = await conn.fetchval("SELECT COALESCE(MAX(seq),0)+1 FROM investigation_events WHERE run_id=$1", run_id)
        pin = dict(schema=PIN_SCHEMA, event_id=str(event_id), seq=seq, tenant_id=str(tenant), run_id=str(run_id),
                   executor_id=str(owner), body_artifact_id=str(artifact_id), body_hash=content_hash(text), begin=begin, scope_hash=state["scope_hash"])
        actual = await conn.fetchval("INSERT INTO investigation_events (id,run_id,tenant_id,seq,ts,kind,agent,summary,payload,input_hash,output_hash) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11) RETURNING id",
            event_id, run_id, tenant, seq, now, EVENT_KIND, EVENT_AGENT, EVENT_KIND, canonical_json(pin), content_hash(text), None)
        if actual != event_id: raise ExecutionPersistenceError("admission event insert not confirmed")
        await store._insert_artifact(conn, artifact_id=artifact_id, event_id=event_id, kind=ARTIFACT_KIND, body=text)
