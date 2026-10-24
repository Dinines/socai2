"""One manual start, gated by current policy and confirmed fresh admission.

No authentication implementation, HTTP registration, background task, retry or
legacy writer exclusion is provided here. The explicit server guard must supply
the current deployment's target eligibility; a reference alone proves nothing.
"""
from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from .execution_state import ExecutionRejected
from .execution_store import ExecutionPersistenceError, canonical_json
from .program_recon_runtime import ProgramReconRuntime
from .program_recon_publication_store import ProgramReconPublicationStore
from .program_result_reader import CompatibleOwnedReconResultReader
from .program_start_store import ProgramAlertStartStore, RECEIPT_SCHEMA
from .scope import TenantPrincipal

ELIGIBILITY_SCHEMA = "program_manual_target_eligibility.v1"
OUTCOME_SCHEMA = "program_manual_start_outcome.v1"


def _require(value, reason):
    if not value:
        raise ExecutionRejected(reason)


class ProgramManualStartCoordinator:
    def __init__(self, admission_store: ProgramAlertStartStore, reader: CompatibleOwnedReconResultReader, *,
                 target_guard, target_policy_ref: str, api_url: str, service_token: str, transport=None):
        _require(isinstance(admission_store, ProgramAlertStartStore) and isinstance(reader, CompatibleOwnedReconResultReader)
                 and reader.pool is admission_store.pool, "matching explicit program admission and owned reader required")
        _require(target_guard is not None and callable(getattr(target_guard, "assess", None))
                 and type(target_policy_ref) is str and bool(target_policy_ref.strip()), "explicit server target eligibility policy required")
        try:
            parsed = urlsplit(api_url)
            valid_url = (type(api_url) is str and not any(c.isspace() for c in api_url)
                         and parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username
                         and not parsed.password and not parsed.query and not parsed.fragment and parsed.path in {"", "/"})
            parsed.port
            valid_token = (type(service_token) is str and 32 <= len(service_token.encode("ascii")) <= 256
                           and not any(c.isspace() for c in service_token))
        except (ValueError, TypeError, AttributeError, UnicodeError):
            valid_url = valid_token = False
        _require(valid_url and valid_token, "explicit controlled tool API configuration required")
        self._admission, self._reader = admission_store, reader
        self._guard, self._policy_ref = target_guard, target_policy_ref
        self._api_url, self._token, self._transport = api_url.rstrip("/"), service_token, transport

    async def _current(self, intent, principal, actor):
        # Pure validation/detachment occurs before awaiting the trusted guard.
        intent = self._admission._authorize(intent, principal, actor)
        tenant = UUID(intent["request"]["tenant_id"])
        actor = UUID(intent["request"]["actor_id"])
        target = UUID(intent["request"]["target"]["id"])
        try:
            decision = await self._guard.assess(current_principal=principal, tenant_id=tenant, actor_id=actor,
                                                alert_id=target, policy_ref=self._policy_ref)
        except Exception:
            raise ExecutionPersistenceError("current target eligibility unavailable") from None
        try:
            _require(type(decision) is dict and set(decision) == {"schema", "policy_ref", "tenant_id", "actor_id", "target", "eligible", "reason"},
                     "target eligibility contract not confirmed")
            expected = dict(schema=ELIGIBILITY_SCHEMA, policy_ref=self._policy_ref, tenant_id=str(tenant),
                            actor_id=str(actor), target={"type": "alert", "id": str(target)})
            _require(canonical_json({k: decision[k] for k in expected}) == canonical_json(expected)
                     and type(decision["eligible"]) is bool and type(decision["reason"]) is str,
                     "current target eligibility identity or policy differs")
            _require(decision["eligible"] is True, "current target eligibility refused")
        except ExecutionRejected:
            raise
        except (KeyError, ValueError, TypeError, AttributeError):
            raise ExecutionRejected("target eligibility contract not confirmed") from None
        return intent, tenant, actor

    async def _owned(self, intent, principal):
        tenant, run_id = UUID(intent["request"]["tenant_id"]), UUID(intent["run_id"])
        result = await self._reader.read(current_principal=principal, tenant_id=tenant, run_id=run_id)
        _require(type(result) is dict and canonical_json([result.get("schema"), result.get("tenant_id"), result.get("run_id"),
            result.get("profile"), result.get("target"), result.get("objective"), result.get("notification")]) == canonical_json([
            "owned_program_recon_result.v1", str(tenant), str(run_id), "alert_recon", intent["request"]["target"],
            intent["request"]["objective"], None]), "coordinated owned result identity differs")
        return result

    @staticmethod
    def _receipt(admitted, intent):
        receipt = admitted.receipt
        _require(receipt["schema"] == RECEIPT_SCHEMA and receipt["persistence_status"] == "committed"
                 and receipt["external_call_authorized"] is False
                 and type(receipt["fresh"]) is bool and type(receipt["may_enter_runtime"]) is bool
                 and receipt["fresh"] is receipt["may_enter_runtime"], "confirmed admission flags required")
        _require(canonical_json([receipt["tenant_id"], receipt["run_id"], receipt["executor_id"], receipt["intent_ref"], receipt["request_hash"]])
                 == canonical_json([intent["request"]["tenant_id"], intent["run_id"], intent["executor_id"], intent["intent_ref"], intent["request_hash"]]),
                 "admission identity differs")
        return receipt

    @staticmethod
    def _outcome(admitted, result, *, entered, runtime_status, http_attempted, publication_attempted):
        return dict(schema=OUTCOME_SCHEMA, mode="coordinated" if entered else "read_only",
            admission=admitted.receipt, external_call_authorized=False,
            runtime=dict(entered_by_this_invocation=entered, status=runtime_status,
                http_attempted_by_this_invocation=http_attempted, publication_attempted_by_this_invocation=publication_attempted),
            result=result)

    async def read_operation(self, *, intent, current_principal: TenantPrincipal, current_actor_id):
        try:
            intent, _, actor = await self._current(intent, current_principal, current_actor_id)
            admitted = await self._admission.read_operation(intent=intent, current_principal=current_principal, current_actor_id=actor)
            receipt = self._receipt(admitted, intent)
            _require(receipt["fresh"] is False, "operation read cannot grant execution")
            result = await self._owned(intent, current_principal)
            return self._outcome(admitted, result, entered=False, runtime_status=None, http_attempted=False, publication_attempted=False)
        except ExecutionRejected:
            raise ExecutionRejected("program operation read contract refused") from None
        except Exception:
            raise ExecutionPersistenceError("program operation read not confirmed") from None

    async def start(self, *, intent, current_principal: TenantPrincipal, current_actor_id, parent_deadline=None):
        try:
            intent, tenant, actor = await self._current(intent, current_principal, current_actor_id)
            admitted = await self._admission.admit(intent=intent, current_principal=current_principal,
                                                 current_actor_id=actor, parent_deadline=parent_deadline)
            receipt = self._receipt(admitted, intent)
            entered, status, http_attempted, publication_attempted = False, None, False, False
            if receipt["fresh"] is True:
                store = ProgramReconPublicationStore(self._admission.pool, tenant_id=tenant, run_id=UUID(intent["run_id"]),
                                                     executor_id=UUID(intent["executor_id"]))
                runtime = ProgramReconRuntime(store, admitted.request, api_url=self._api_url, service_token=self._token, transport=self._transport)
                entered = True
                outcome = await runtime.execute()  # Admission already saved the only begin.
                status, http_attempted = outcome["status"], outcome["http_attempted_by_this_invocation"]
                _require(type(http_attempted) is bool and status in {"stopped", "in_progress_or_interrupted", "blocked_handoff_pending"},
                         "managed runtime outcome not confirmed")
                if status == "stopped":
                    handoff = outcome["handoff"]
                    _require(type(handoff) is dict and handoff["retention"] == "committed"
                             and handoff["state"]["recon"]["phase"] == "stopped", "confirmed stopped handoff required before publication")
                    publication_attempted = True
                    await store.publish(admitted.request)
            result = await self._owned(intent, current_principal)
            return self._outcome(admitted, result, entered=entered, runtime_status=status,
                                 http_attempted=http_attempted, publication_attempted=publication_attempted)
        except ExecutionRejected:
            raise ExecutionRejected("program manual start contract refused") from None
        except Exception:
            raise ExecutionPersistenceError("program manual start not confirmed; replay forbidden") from None
