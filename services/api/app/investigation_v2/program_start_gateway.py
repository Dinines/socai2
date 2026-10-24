"""Explicit manual-start protocol. No Agents imports or legacy fallback.

The backend owns the full intent (including its budget) and original ledger.
These checks bind the public operation and validate the complete result DTO;
hash shape alone cannot prove the original actor, budget or source truth.
"""
from __future__ import annotations

import asyncio
from datetime import timezone
import json
import os
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID, NAMESPACE_URL, uuid5

import httpx
from fastapi import HTTPException
from pydantic import AwareDatetime, BaseModel, ConfigDict

from .program_result_gateway import (
    checked_compatible_result, _keys, _artifact, _hash, _ref, _timestamp,
)
from .result_gateway import MAX_BYTES, _canonical, _require, _uuid

URL_ENV = "AISOC_INVESTIGATION_START_URL"
TOKEN_ENV = "AISOC_INVESTIGATION_START_TOKEN"
READ_TOKEN_ENV = "AISOC_INVESTIGATION_COMPAT_READ_TOKEN"
REQUEST_VERSION = "program_alert_recon_start_request.v1"
MAX_BODY_BYTES = 4096
REQUEST_TIMEOUT_SECONDS = 200
CLOSE_TIMEOUT_SECONDS = 5


class _Window(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start: AwareDatetime
    end: AwareDatetime


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation_key: UUID
    window: _Window
    request_version: Literal[REQUEST_VERSION]


def _unique(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value)
        value[key] = item
    return value


def _json(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))


def normalized_start_body(raw: bytes) -> dict:
    _require(type(raw) is bytes and len(raw) <= MAX_BODY_BYTES)
    _json(raw)  # Duplicate keys/nonfinite values must not disappear in parsing.
    body = _Body.model_validate_json(raw)
    _require(body.operation_key.int != 0)
    start, end = (v.astimezone(timezone.utc) for v in (body.window.start, body.window.end))
    _require(0 < (end-start).total_seconds() <= 300)
    return dict(operation_key=str(body.operation_key), request_version=body.request_version,
                window={"start": start.isoformat(timespec="microseconds"), "end": end.isoformat(timespec="microseconds")})


def operation_identity(tenant_id: UUID, operation_key: UUID) -> tuple[UUID, UUID]:
    run = uuid5(NAMESPACE_URL, _canonical(["socai2:investigation-v2:start-operation", str(tenant_id), str(operation_key)]).decode("utf-8"))
    return run, uuid5(run, "exclusive-initial-start-owner")


def checked_start_outcome(payload, *, tenant_id: UUID, alert_id: UUID, operation_key: UUID, read_only: bool) -> dict:
    tenant, alert, key = (_uuid(v) for v in (tenant_id, alert_id, operation_key))
    run, executor = operation_identity(tenant, key)
    _canonical(payload)
    _keys(payload, "schema mode admission external_call_authorized runtime result")
    _require(payload["schema"] == "program_manual_start_outcome.v1" and type(payload["mode"]) is str
             and payload["mode"] in {"coordinated", "read_only"} and payload["external_call_authorized"] is False)
    if read_only: _require(payload["mode"] == "read_only")
    fresh = payload["mode"] == "coordinated"
    admission, runtime, owned = payload["admission"], payload["runtime"], payload["result"]
    _keys(admission, "schema tenant_id run_id executor_id intent_ref request_hash fresh may_enter_runtime external_call_authorized persistence_status admission_artifact admission_event_id begin original_deadline phase")
    _require(admission["schema"] == "program_alert_start_admission_receipt.v1"
             and admission["tenant_id"] == str(tenant) and admission["run_id"] == str(run)
             and admission["executor_id"] == str(executor) and admission["fresh"] is fresh
             and admission["may_enter_runtime"] is fresh and admission["external_call_authorized"] is False
             and admission["persistence_status"] == "committed")
    _ref(admission["intent_ref"], "program-alert-start-intent:"); _hash(admission["request_hash"])
    _artifact(admission["admission_artifact"])
    _require(type(admission["admission_event_id"]) is str); _uuid(admission["admission_event_id"])
    _keys(admission["begin"], "event_id input state")
    _require(type(admission["begin"]["event_id"]) is str); _uuid(admission["begin"]["event_id"])
    _artifact(admission["begin"]["input"]); _artifact(admission["begin"]["state"])
    _timestamp(admission["original_deadline"])
    _require(type(admission["phase"]) is str and admission["phase"] in {"ready", "claimed", "blocked", "stopped"})
    _keys(runtime, "entered_by_this_invocation status http_attempted_by_this_invocation publication_attempted_by_this_invocation")
    _require(runtime["entered_by_this_invocation"] is fresh)
    for field in ("http_attempted_by_this_invocation", "publication_attempted_by_this_invocation"):
        _require(type(runtime[field]) is bool)
    if fresh:
        _require(type(runtime["status"]) is str and runtime["status"] in {"stopped", "in_progress_or_interrupted", "blocked_handoff_pending"})
        stopped = runtime["status"] == "stopped"
        _require(runtime["publication_attempted_by_this_invocation"] is stopped)
    else:
        _require(runtime["status"] is None and runtime["http_attempted_by_this_invocation"] is False
                 and runtime["publication_attempted_by_this_invocation"] is False)
    _require(type(owned) is dict and owned["schema"] == "owned_program_recon_result.v1"
             and owned["target"] == {"type": "alert", "id": str(alert)})
    checked_compatible_result(owned, tenant_id=tenant, run_id=run)
    if fresh:
        _require((owned["publication_state"] == "published") is stopped)
    return payload


def _token(value):
    _require(type(value) is str and 32 <= len(value.encode("ascii")) <= 256
             and not any(c.isspace() for c in value))
    _require(value != os.getenv(READ_TOKEN_ENV))
    return value


async def _close(resource):
    if resource is None: return
    try:
        await asyncio.wait_for(resource.aclose(), timeout=CLOSE_TIMEOUT_SECONDS)
    except Exception:
        # A completed request is never replayed because cleanup failed.
        pass


class _BoundedCloseStream(httpx.AsyncByteStream):
    """HTTPX also closes on normal iterator EOF, inside aiter_bytes()."""
    def __init__(self, stream):
        self._stream = stream

    async def __aiter__(self):
        async for chunk in self._stream:
            yield chunk

    async def aclose(self):
        await _close(self._stream)


class ProgramStartGateway:
    def __init__(self, *, backend_url: str, start_token: str, transport=None):
        try:
            parsed = urlsplit(backend_url)
            _require(type(backend_url) is str and parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                     and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
                     and parsed.path in {"", "/"} and not any(c.isspace() for c in backend_url))
            parsed.port
            token = _token(start_token)
        except (ValueError, TypeError, AttributeError, UnicodeError):
            raise ValueError("explicit isolated start backend and separate strong credential required") from None
        self._url, self._token, self._transport = backend_url.rstrip("/"), token, transport

    @classmethod
    def from_environment(cls):
        return cls(backend_url=os.getenv(URL_ENV) or "", start_token=os.getenv(TOKEN_ENV) or "")

    async def invoke(self, *, tenant_id: UUID, actor_id: UUID, alert_id: UUID, body: dict, read_only: bool) -> dict:
        try:
            tenant, actor, alert = (_uuid(v) for v in (tenant_id, actor_id, alert_id))
            token = _token(self._token)  # Recheck separation after operator rotation.
            _require(type(read_only) is bool)
            normalized = normalized_start_body(_canonical(body))
        except (ValueError, TypeError, AttributeError, UnicodeError, RecursionError):
            raise HTTPException(502, "investigation_start_current_configuration_invalid") from None
        response, client = None, None
        try:
            # HTTPX's timeouts are per phase, so they cannot bound slow chunks.
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False, transport=self._transport)
                path = "operation-read" if read_only else "start"
                request = client.build_request("POST", f"{self._url}/internal/investigation-v2/alerts/{alert}/{path}",
                    headers={"Authorization": "Bearer " + token, "X-AiSOC-Tenant-ID": str(tenant), "X-AiSOC-Actor-ID": str(actor), "Content-Type": "application/json"},
                    content=_canonical(normalized))
                response = await client.send(request, stream=True)
                # Bound both HTTPX's implicit EOF close and our explicit close,
                # without bypassing content decoding or counting only chunks.
                response.stream = _BoundedCloseStream(response.stream)
                status = response.status_code
                if status != 200:
                    mapped = status if status in {409, 413, 422} else (503 if status in {500, 502, 503, 504} else 502)
                    raise HTTPException(mapped, "investigation_start_backend_not_confirmed")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(raw) + len(chunk) > MAX_BYTES:
                        raise ValueError("bounded start response required")
                    raw.extend(chunk)
                payload = _json(bytes(raw))
                return checked_start_outcome(payload, tenant_id=tenant, alert_id=alert,
                    operation_key=UUID(normalized["operation_key"]), read_only=read_only)
        except HTTPException:
            raise
        except (TimeoutError, httpx.HTTPError):
            # Dispatch may already have committed; explicit operation-read is
            # the recovery path. No retry and no claim that nothing executed.
            raise HTTPException(503, "investigation_start_outcome_unknown") from None
        except (ValueError, TypeError, KeyError, AttributeError, UnicodeError, RecursionError):
            raise HTTPException(502, "investigation_start_outcome_mismatch") from None
        finally:
            await _close(response)
            await _close(client)
