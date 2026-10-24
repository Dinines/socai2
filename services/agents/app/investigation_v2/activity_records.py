"""One M2 record query bound to a trusted M1 snapshot, not globally registered.

The API authenticates a tenant and applies global bounds. This caller applies
the narrower question scope before HTTP; persistent Run admission is M8 work.
No environment fallback, SQL, model invocation or evidence persistence here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ipaddress
import re
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from app.investigation_v2.scope import CAPABILITY, QueryRequest, ScopeContext, UTCWindow, admit_query
from app.tools.registry import Tool

_FILTERS = ("hostname", "source_ip", "dest_ip", "dst_port", "protocol")
_REQUIRED = frozenset((*_FILTERS, "start", "end"))
_ALLOWED = _REQUIRED | {"limit"}
_NAMESPACE = "clickhouse.aisoc.raw_events"
_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$")


def _time(value: Any) -> datetime:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        raise ValueError("time_must_be_iso_string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("time_requires_timezone")
    return parsed.astimezone(timezone.utc)


def _ip(value: Any) -> str:
    address = ipaddress.ip_address(value)
    return str(address.ipv4_mapped or address) if isinstance(address, ipaddress.IPv6Address) else str(address)


def _validate_response(payload: Any, parameters: dict[str, Any]) -> None:
    """Refuse foreign/malformed material rather than attributing it to this scope."""
    if not isinstance(payload, dict) or payload.get("tool") != CAPABILITY:
        raise ValueError("unexpected_tool_response")
    status = payload.get("status")
    if status not in {"ok", "empty", "unavailable", "error", "rejected"}:
        raise ValueError("unknown_query_status")
    if payload.get("available") is not (status in {"ok", "empty"}) or type(payload.get("truncated")) is not bool:
        raise ValueError("query_state_mismatch")
    rows = payload.get("rows")
    receipt = payload.get("query_receipt")
    if not isinstance(rows, list) or not isinstance(receipt, dict):
        raise ValueError("query_material_missing")
    actual = receipt.get("parameters")
    if not isinstance(actual, dict):
        raise ValueError("query_parameters_missing")
    for key, value in parameters.items():
        if key in ("start", "end"):
            if _time(actual.get(key)) != _time(value):
                raise ValueError("query_window_mismatch")
        elif actual.get(key) != value:
            raise ValueError("query_parameter_mismatch")
    if payload.get("row_count") != len(rows) or len(rows) > parameters["limit"]:
        raise ValueError("query_row_count_mismatch")
    if status == "empty" and rows or status in {"error", "unavailable", "rejected"} and rows:
        raise ValueError("query_state_mismatch")
    if status == "ok" and not rows:
        raise ValueError("query_state_mismatch")
    total_bytes = 0
    for row in rows:
        if not isinstance(row, dict) or row.get("namespace") != _NAMESPACE:
            raise ValueError("source_namespace_mismatch")
        UUID(row["event_id"])
        if row.get("tenant_id") != parameters["tenant_id"]:
            raise ValueError("response_tenant_mismatch")
        if not (_time(parameters["start"]) <= _time(row["event_time"]) < _time(parameters["end"])):
            raise ValueError("response_event_outside_window")
        if row.get("src_hostname") != parameters["hostname"] or row.get("class_uid") != 4001:
            raise ValueError("response_entity_or_type_mismatch")
        for key in ("source_ip", "dest_ip"):
            if _ip(row[key]) != _ip(parameters[key]):
                raise ValueError("response_endpoint_mismatch")
        if row.get("dst_port") != parameters["dst_port"] or row.get("protocol") != parameters["protocol"]:
            raise ValueError("response_network_filter_mismatch")
        record_bytes = 0
        for key in ("raw_payload", "ocsf_json"):
            body = row.get(key)
            if not isinstance(body, dict) or not isinstance(body.get("text"), str):
                raise ValueError("source_body_missing")
            kept = len(body["text"].encode("utf-8"))
            if body.get("retained_bytes") != kept or type(body.get("original_bytes")) is not int or body["original_bytes"] < kept:
                raise ValueError("source_body_length_mismatch")
            digest = body.get("sha256", "")
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("source_body_hash_missing")
            if body.get("truncated") is not (kept < body["original_bytes"]):
                raise ValueError("source_body_truncation_mismatch")
            if not body["truncated"] and hashlib.sha256(body["text"].encode("utf-8")).hexdigest() != digest:
                raise ValueError("source_body_hash_mismatch")
            record_bytes += kept
        if record_bytes > 16 * 1024:
            raise ValueError("source_body_exceeds_record_limit")
        total_bytes += record_bytes
    if total_bytes > 256 * 1024:
        raise ValueError("source_body_exceeds_response_limit")


def bind_activity_records(context: ScopeContext, question_id: str, member_id: UUID | str, *,
                          api_url: str, service_token: str,
                          transport: httpx.AsyncBaseTransport | None = None) -> Tool:
    """Trusted program factory. Only the returned Tool's arguments are public.

    ``transport`` supports direct HTTP-contract tests; normal operation uses the
    actual API. The caller owns authentication and the M1 checked snapshot.
    """
    if not isinstance(context, ScopeContext):
        raise ValueError("trusted_scope_required")
    question = next((q for q in context.questions if q.question_id == question_id), None)
    if question is None or CAPABILITY not in question.allowed_capabilities:
        raise ValueError("question_does_not_allow_activity_records")
    member_uuid = UUID(str(member_id))
    member = next((m for m in context.query_scope.members if m.alert_id == member_uuid), None)
    if member is None:
        raise ValueError("member_outside_scope")
    required_entities = {("host", member.hostname), ("ip", member.source_ip), ("ip", member.dest_ip)}
    if not required_entities.issubset({(entity.kind, entity.value) for entity in question.entities}):
        raise ValueError("member_outside_question_scope")
    parsed_url = urlsplit(api_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname or parsed_url.username or parsed_url.query or parsed_url.fragment:
        raise ValueError("invalid_trusted_api_url")
    if not isinstance(service_token, str) or not service_token.strip():
        raise ValueError("service_credential_required")
    endpoint = api_url.rstrip("/") + "/api/v2/investigation/query"
    fixed = {key: getattr(member, key) for key in _FILTERS}
    identity = {"tenant_id": str(context.tenant_id), "run_id": str(context.run_id),
                "scope_revision": context.revision, "policy_ref": context.policy_ref,
                "question_id": question_id, "member_id": str(member_uuid)}

    async def call(**args: Any) -> dict[str, Any]:
        caller_receipt = {**identity, "http_attempted": False, "admission": "rejected"}

        def failed(status: str, reason: str) -> dict[str, Any]:
            return {"tool": CAPABILITY, "status": status, "available": False, "rows": [],
                    "row_count": 0, "truncated": False, "reason": reason,
                    "caller_receipt": caller_receipt}

        if not _REQUIRED.issubset(args) or not set(args).issubset(_ALLOWED):
            return failed("rejected", "missing_or_forbidden_arguments")
        if any(args[key] != fixed[key] or type(args[key]) is not type(fixed[key]) for key in _FILTERS):
            return failed("rejected", "filter_value_has_no_approved_provenance")
        try:
            window = UTCWindow(_time(args["start"]), _time(args["end"]))
            request = QueryRequest(context.tenant_id, context.run_id, context.revision, member_uuid,
                                   window, member.fields, limit=args.get("limit", context.query_scope.max_limit))
            admission = admit_query(context, request)
        except (TypeError, ValueError):
            return failed("rejected", "invalid_query_parameters")
        if not admission.allowed:
            return failed("rejected", admission.reason)
        parameters = {**fixed, "start": window.start.isoformat(timespec="microseconds"),
                      "end": window.end.isoformat(timespec="microseconds"), "limit": request.limit}
        caller_receipt.update(admission=admission.reason, request_parameters=dict(parameters),
                              parameter_sources=[{"parameter": f.parameter, "record_ref": f.record_ref, "path": f.path}
                                                 for f in member.fields],
                              window_source="approved_M1_query_scope", http_attempted=True)
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=transport, follow_redirects=False) as client:
                response = await client.post(endpoint, json={"tool": CAPABILITY, "args": parameters},
                                             headers={"Authorization": "Bearer " + service_token,
                                                      "X-AiSOC-Tenant-ID": str(context.tenant_id)})
            caller_receipt["http_status"] = response.status_code
            response.raise_for_status()
            payload = response.json()
            _validate_response(payload, {"tenant_id": str(context.tenant_id), **parameters})
        except httpx.HTTPError as exc:
            return failed("error", "query_transport_" + type(exc).__name__)
        except (KeyError, TypeError, ValueError):
            return failed("error", "query_response_contract_mismatch")
        payload["caller_receipt"] = caller_receipt
        return payload

    properties = {key: {"type": "integer" if key == "dst_port" else "string", "enum": [value]}
                  for key, value in fixed.items()}
    properties.update(start={"type": "string", "description": "Absolute timezone-aware start, inclusive, within approved scope."},
                      end={"type": "string", "description": "Absolute timezone-aware end, exclusive, within approved scope."},
                      limit={"type": "integer", "minimum": 1, "maximum": context.query_scope.max_limit})
    return Tool(name=CAPABILITY, description="Read attributable network observations within this approved question scope.",
                parameters={"type": "object", "properties": properties, "required": sorted(_REQUIRED),
                            "additionalProperties": False}, fn=call)
