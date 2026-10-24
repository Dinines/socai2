"""Independent internal start HTTP configuration; no legacy app registration.

Controlled target references are operator configuration, not proof that another
writer is excluded. Actual operational isolation must be checked separately.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import asyncio
from contextlib import asynccontextmanager
import hmac
import json
import os
import ssl
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import FastAPI, HTTPException, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, ValidationError

from .execution_state import ExecutionRejected
from .execution_store import ExecutionPersistenceError, canonical_json
from .program_start_coordinator import ELIGIBILITY_SCHEMA, OUTCOME_SCHEMA, ProgramManualStartCoordinator
from .program_start_contract import normalize_program_alert_start, REQUEST_VERSION
from .program_start_store import ProgramAlertStartStore, RECEIPT_SCHEMA
from .program_result_reader import CompatibleOwnedReconResultReader
from .scope import PrincipalScope, TenantPrincipal, UTCWindow
from .start_contract import StartBudgetPolicy, BUDGET_SCHEMA

PREFIX = "AISOC_INVESTIGATION_"
TOKEN_ENV = PREFIX + "START_TOKEN"
DSN_ENV = PREFIX + "START_PG_DSN"
CA_ENV = PREFIX + "START_CA_FILE"
TOOL_URL_ENV = PREFIX + "START_TOOL_API_URL"
TOOL_TOKEN_ENV = PREFIX + "START_TOOL_TOKEN"
BUDGET_ENV = PREFIX + "START_BUDGET_JSON"
POLICY_ENV = PREFIX + "START_TARGET_POLICY_JSON"
READ_TOKEN_ENV = PREFIX + "COMPAT_READ_TOKEN"
POLICY_SCHEMA = "controlled_manual_start_targets.v1"
MAX_BODY_BYTES = 4096


def _require(value):
    if not value: raise ValueError("explicit valid isolated start configuration required")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _json(text):
    try:
        _require(type(text) is str and len(text.encode("utf-8")) <= 65536)
        value = json.loads(text, object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        _require(type(value) is dict)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError("invalid isolated start JSON configuration") from None


def _uuid(value):
    _require(type(value) is str)
    result = UUID(value)
    _require(result.int != 0)
    return result


def _text(value):
    _require(type(value) is str and bool(value.strip()))
    return value


def checked_start_token(value):
    try:
        _require(type(value) is str and 32 <= len(value.encode("ascii")) <= 256
                 and not any(c.isspace() for c in value))
        return value
    except (ValueError, TypeError, UnicodeError):
        raise ValueError("explicit strong isolated start credential required") from None


@dataclass(frozen=True)
class ControlledTarget:
    tenant_id: UUID
    alert_id: UUID
    operational_isolation_ref: str


@dataclass(frozen=True)
class ControlledManualTargetPolicy:
    policy_ref: str
    targets: tuple[ControlledTarget, ...]

    @classmethod
    def from_document(cls, value):
        try:
            _require(type(value) is dict and set(value) == {"schema", "policy_ref", "mode", "targets"}
                     and value["schema"] == POLICY_SCHEMA and value["mode"] == "isolated_manual_test"
                     and type(value["targets"]) is list and bool(value["targets"]))
            version = _text(value["policy_ref"])
            targets, identities = [], set()
            for row in value["targets"]:
                _require(type(row) is dict and set(row) == {"tenant_id", "alert_id", "operational_isolation_ref"})
                target = ControlledTarget(_uuid(row["tenant_id"]), _uuid(row["alert_id"]), _text(row["operational_isolation_ref"]))
                identity = (target.tenant_id, target.alert_id)
                _require(identity not in identities)
                identities.add(identity); targets.append(target)
            return cls(version, tuple(targets))
        except (ValueError, TypeError, KeyError, AttributeError):
            raise ValueError("explicit controlled manual test target policy required") from None

    async def assess(self, *, current_principal, tenant_id, actor_id, alert_id, policy_ref):
        _require(isinstance(current_principal, TenantPrincipal))
        current = PrincipalScope(current_principal.tenant_ids, current_principal.subject, current_principal.delegated)
        tenant, actor, alert = (_uuid(str(v)) for v in (tenant_id, actor_id, alert_id))
        eligible = (policy_ref == self.policy_ref and tenant in current.tenant_ids
                    and any((target.tenant_id, target.alert_id) == (tenant, alert) for target in self.targets))
        return dict(schema=ELIGIBILITY_SCHEMA, policy_ref=self.policy_ref, tenant_id=str(tenant), actor_id=str(actor),
            target={"type": "alert", "id": str(alert)}, eligible=eligible,
            reason="configured_controlled_test_target" if eligible else "controlled_target_not_allowed")


def checked_budget(value):
    try:
        _require(type(value) is dict and value.get("schema") == BUDGET_SCHEMA)
        return StartBudgetPolicy(**{k: v for k, v in value.items() if k != "schema"})
    except Exception:
        raise ValueError("explicit supported isolated start budget required") from None


@dataclass(frozen=True)
class StartAPIConfig:
    token: str = field(repr=False)
    dsn: str = field(repr=False)
    ca_file: str | None = field(repr=False)
    tool_url: str = field(repr=False)
    tool_token: str = field(repr=False)
    budget: StartBudgetPolicy
    target_policy: ControlledManualTargetPolicy

    @classmethod
    def from_environment(cls, token):
        try:
            token = checked_start_token(token)
            tool_token = checked_start_token(os.getenv(TOOL_TOKEN_ENV))
            _require(token != tool_token and token != os.getenv(READ_TOKEN_ENV))
            dsn = _text(os.getenv(DSN_ENV))
            tool_url = _text(os.getenv(TOOL_URL_ENV)); parsed = urlsplit(tool_url)
            _require(parsed.scheme in {"http", "https"} and bool(parsed.hostname) and parsed.path in {"", "/"}
                     and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
                     and not any(c.isspace() for c in tool_url))
            parsed.port
            budget = checked_budget(_json(os.getenv(BUDGET_ENV)))
            target_policy = ControlledManualTargetPolicy.from_document(_json(os.getenv(POLICY_ENV)))
            return cls(token, dsn, os.getenv(CA_ENV) or None, tool_url.rstrip("/"), tool_token, budget, target_policy)
        except Exception:
            raise ValueError("explicit isolated start configuration unavailable") from None


class _WindowBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start: AwareDatetime
    end: AwareDatetime


class _StartBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation_key: UUID
    window: _WindowBody
    request_version: Literal[REQUEST_VERSION]


def _gateway(request, expected_token, forbidden_tokens):
    try:
        expected_token = checked_start_token(expected_token)
        _require(all(expected_token != value for value in forbidden_tokens if value is not None))
        values = request.headers.getlist("Authorization")
        _require(len(values) == 1)
        scheme, _, actual = values[0].partition(" ")
        _require(scheme.lower() == "bearer" and hmac.compare_digest(actual.encode("utf-8"), expected_token.encode("utf-8")))
    except (ValueError, TypeError, UnicodeError):
        raise HTTPException(401, "investigation_start_credential_required", headers={"WWW-Authenticate": "Bearer"}) from None


def _gateway_identity(request, header, name):
    try:
        values = request.headers.getlist(header)
        _require(len(values) == 1)
        return _uuid(values[0])
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "valid_single_" + name + "_required") from None


async def _body(request):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "start_body_exceeds_limit")
        raw.extend(chunk)
    try:
        _json(raw.decode("utf-8"))  # Reject duplicate keys before model parsing.
        body = _StartBody.model_validate_json(bytes(raw))
        _require(body.operation_key.int != 0)
        window = UTCWindow(body.window.start, body.window.end)
        _require((window.end-window.start).total_seconds() <= 300)
        return body, window
    except (ValueError, TypeError, UnicodeError, RecursionError, ValidationError):
        raise HTTPException(422, "valid_strict_start_body_required") from None


def _checked_outcome(result, intent, read_only):
    """Minimal write envelope; full nested DTO checks remain the API gateway."""
    try:
        _require(type(result) is dict and set(result) == {"schema", "mode", "admission", "external_call_authorized", "runtime", "result"}
                 and result["schema"] == OUTCOME_SCHEMA and type(result["mode"]) is str
                 and result["mode"] in {"coordinated", "read_only"} and result["external_call_authorized"] is False)
        if read_only: _require(result["mode"] == "read_only")
        admission, runtime, owned = result["admission"], result["runtime"], result["result"]
        _require(type(admission) is dict and admission["schema"] == RECEIPT_SCHEMA
                 and admission["persistence_status"] == "committed" and admission["external_call_authorized"] is False)
        for key, value in {"tenant_id": intent["request"]["tenant_id"], "run_id": intent["run_id"],
                           "executor_id": intent["executor_id"], "intent_ref": intent["intent_ref"], "request_hash": intent["request_hash"]}.items():
            _require(admission[key] == value)
        fresh = result["mode"] == "coordinated"
        _require(admission["fresh"] is fresh and admission["may_enter_runtime"] is fresh)
        _require(type(runtime) is dict and set(runtime) == {"entered_by_this_invocation", "status", "http_attempted_by_this_invocation", "publication_attempted_by_this_invocation"}
                 and runtime["entered_by_this_invocation"] is fresh)
        for key in ("http_attempted_by_this_invocation", "publication_attempted_by_this_invocation"):
            _require(type(runtime[key]) is bool)
        if not fresh:
            _require(runtime["status"] is None and runtime["http_attempted_by_this_invocation"] is False
                     and runtime["publication_attempted_by_this_invocation"] is False)
        else:
            _require(type(runtime["status"]) is str and runtime["status"] in {"stopped", "in_progress_or_interrupted", "blocked_handoff_pending"})
            _require(runtime["publication_attempted_by_this_invocation"] is (runtime["status"] == "stopped"))
        _require(type(owned) is dict and canonical_json([owned["schema"], owned["tenant_id"], owned["run_id"], owned["profile"], owned["target"], owned["objective"], owned["notification"]])
                 == canonical_json(["owned_program_recon_result.v1", intent["request"]["tenant_id"], intent["run_id"], "alert_recon",
                                    intent["request"]["target"], intent["request"]["objective"], None])
                 and type(owned["publication_state"]) is str and owned["publication_state"] in {"published", "not_published"})
        if runtime["publication_attempted_by_this_invocation"]: _require(owned["publication_state"] == "published")
        canonical_json(result)  # Whole response bounded; no secret diagnostics.
        return result
    except (KeyError, ValueError, TypeError, AttributeError, ExecutionRejected, RecursionError, UnicodeError):
        raise HTTPException(502, "investigation_start_outcome_mismatch") from None


def create_app(*, coordinator=None, start_token=None, budget_policy=None):
    """Explicit write app; injected coordinators remain owned by their caller."""
    try:
        token = checked_start_token(os.getenv(TOKEN_ENV) if start_token is None else start_token)
        _require(token != os.getenv(READ_TOKEN_ENV) and token != os.getenv(TOOL_TOKEN_ENV))
        if coordinator is None:
            config = StartAPIConfig.from_environment(token)
            budget = config.budget
        else:
            config = None
            _require(callable(getattr(coordinator, "start", None)) and callable(getattr(coordinator, "read_operation", None)))
            _require(isinstance(budget_policy, StartBudgetPolicy))
            budget = checked_budget(budget_policy.descriptor)
            if isinstance(coordinator, ProgramManualStartCoordinator):
                _require(token != coordinator._token and canonical_json(budget.descriptor) == canonical_json(coordinator._admission.budget_policy.descriptor))
    except Exception:
        raise ValueError("explicit isolated start app configuration required") from None

    @asynccontextmanager
    async def lifespan(app):
        pool = None
        try:
            if coordinator is None:
                import asyncpg
                try:
                    tls = ssl.create_default_context(cafile=config.ca_file)
                    pool = await asyncpg.create_pool(config.dsn, ssl=tls, min_size=1, max_size=2, timeout=10, command_timeout=10)
                    admission = ProgramAlertStartStore(pool, budget_policy=config.budget)
                    app.state.coordinator = ProgramManualStartCoordinator(admission, CompatibleOwnedReconResultReader(pool),
                        target_guard=config.target_policy, target_policy_ref=config.target_policy.policy_ref,
                        api_url=config.tool_url, service_token=config.tool_token)
                except Exception:
                    raise RuntimeError("isolated start pool startup unavailable") from None
            yield
        finally:
            if pool is not None:
                app.state.coordinator = None
                try:
                    await asyncio.wait_for(pool.close(), timeout=5)
                except TimeoutError:
                    pool.terminate()
                except Exception:
                    pool.terminate()
                    raise RuntimeError("isolated start pool shutdown unavailable") from None

    app = FastAPI(title="Investigation v2 isolated internal manual start", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.coordinator, app.state.start_token, app.state.budget_policy = coordinator, token, budget

    async def invoke(alert_id, request, read_only):
        configured = app.state.coordinator
        forbidden_tokens = [os.getenv(READ_TOKEN_ENV), os.getenv(TOOL_TOKEN_ENV)]
        if config is not None: forbidden_tokens.append(config.tool_token)
        if isinstance(configured, ProgramManualStartCoordinator): forbidden_tokens.append(configured._token)
        _gateway(request, app.state.start_token, forbidden_tokens)
        tenant = _gateway_identity(request, "X-AiSOC-Tenant-ID", "tenant")
        actor = _gateway_identity(request, "X-AiSOC-Actor-ID", "actor")
        try:
            alert = UUID(alert_id)
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(422, "valid_alert_path_required") from None
        if not alert.int: raise HTTPException(400, "nonnil_alert_path_required")
        if request.query_params: raise HTTPException(400, "start_accepts_no_query_overrides")
        body, window = await _body(request)
        principal = TenantPrincipal(frozenset({tenant}), "verified-api-starter:" + str(actor), True)
        try:
            intent = normalize_program_alert_start(principal=principal, tenant_id=tenant, actor_id=actor, operation_key=body.operation_key,
                alert_id=alert, window=window, budget_policy=app.state.budget_policy, profile="alert_recon", trigger="manual", request_version=body.request_version)
            configured = app.state.coordinator
            if configured is None: raise HTTPException(503, "investigation_start_not_ready")
            method = configured.read_operation if read_only else configured.start
            result = await method(intent=intent, current_principal=principal, current_actor_id=actor)
        except ExecutionRejected:
            raise HTTPException(409, "investigation_start_contract_refused") from None
        except ExecutionPersistenceError:
            raise HTTPException(503, "investigation_start_not_confirmed") from None
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "investigation_start_backend_unavailable") from None
        return _checked_outcome(result, intent, read_only)

    @app.post("/internal/investigation-v2/alerts/{alert_id}/start")
    async def start(alert_id: str, request: Request):
        return await invoke(alert_id, request, False)

    @app.post("/internal/investigation-v2/alerts/{alert_id}/operation-read")
    async def read_operation(alert_id: str, request: Request):
        return await invoke(alert_id, request, True)

    return app
