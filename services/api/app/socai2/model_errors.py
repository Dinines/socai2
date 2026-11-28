"""Bounded provider diagnostics, never request bodies, URLs or credentials."""
import hashlib
import json
import re

import httpx

MAX_ERROR_BODY = 16384
FIELD_LIMITS = {"code": 128, "type": 128, "param": 256, "message": 1024}
INPUT_CONTRACT_REJECTED = "model_input_contract_rejected"
DEADLINE_BEFORE_DISPATCH = "model_deadline_before_dispatch"
RESPONSE_ENVELOPE_INVALID = "model_response_envelope_invalid"


def provider_error(exc, api_key):
    response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
    return response_error(response, api_key, type(exc).__name__)


def response_error(response, api_key, exception_type):
    result = {"exception_type": exception_type,
        "http_status": response.status_code if response is not None else None,
        "body_state": "unavailable", "fields": {}, "truncated_fields": [], "redacted_fields": []}
    if response is None:
        return result
    try:
        body = response.content
    except httpx.ResponseNotRead:
        return result
    if len(body) > MAX_ERROR_BODY:
        result["body_state"] = "oversize_omitted"
        return result
    try:
        data = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        result["body_state"] = "non_json_omitted"
        return result
    data = data.get("error", data) if isinstance(data, dict) else None
    if isinstance(data, str):
        data = {"message": data}
    if not isinstance(data, dict):
        result["body_state"] = "unsupported_shape_omitted"
        return result
    result["body_state"] = "selected_json_fields"
    for key, limit in FIELD_LIMITS.items():
        value = data.get(key)
        if not isinstance(value, str):
            continue
        original = value
        # Redact before limiting so a cut cannot expose a token prefix.
        if api_key:
            value = value.replace(api_key, "[redacted]")
        value = re.sub(r"(?i)https?://[^\s<>\"']+", "[url omitted]", value)
        value = re.sub(r"(?i)\b(bearer|basic)\s+[^\s,;\"']+", r"\1 [redacted]", value)
        value = re.sub(r"(?i)\bsk-[a-z0-9_-]+", "[redacted]", value)
        value = re.sub(r"(?i)(\b(?:api[-_]?key|token|password|secret|authorization)\b\s*[:=]\s*)[^\s,;]+",
                       r"\1[redacted]", value)
        value = "".join(c for c in value if c in "\n\t" or ord(c) >= 32)
        if value != original:
            result["redacted_fields"].append(key)
        raw = value.encode("utf-8", errors="replace")
        value = raw.decode("utf-8")
        if len(raw) > limit:
            result["truncated_fields"].append(key)
            value = raw[:limit].decode("utf-8", errors="ignore")
        result["fields"][key] = value
    return result


def decode_response(response, api_key):
    """Only called after a complete successful HTTP response, never on transport errors."""
    try:
        value = response.json()
    except (ValueError, UnicodeError, RecursionError) as exc:
        reason, exception_type = "json_decode_failed", type(exc).__name__
    else:
        if isinstance(value, dict):
            return value
        reason, exception_type = "json_top_level_not_object", "InvalidEnvelopeType"
    details = response_error(response, api_key, exception_type)
    if reason == "json_top_level_not_object" and details["body_state"] == "selected_json_fields":
        # A scalar response is not a provider error message just because the
        # existing HTTP-error reader can project strings as messages.
        details.update(body_state="unsupported_shape_omitted", fields={}, truncated_fields=[], redacted_fields=[])
    details.update(failure_phase="response_envelope", response_received=True, envelope_reason=reason,
        response_bytes=len(response.content), response_sha256=hashlib.sha256(response.content).hexdigest())
    raise ModelCallError(details) from None


class ModelCallError(RuntimeError):
    """The call did not yield a model answer; consumption may still be unknown."""

    def __init__(self, details):
        self.details = details
        super().__init__(self.envelope_code or "model_transport_error")

    @property
    def envelope_code(self):
        status = self.details.get("http_status")
        if (self.details.get("failure_phase") == "response_envelope"
                and self.details.get("response_received") is True
                and type(status) is int and 200 <= status < 300):
            return RESPONSE_ENVELOPE_INVALID
        return None

    @property
    def rejection_code(self):
        """Only an explicit schema rejection proves dispatch did not run a model.

        Other HTTP errors (including 408), malformed receipts and timeouts keep
        the uncertainty path. This does not invent usage for a rejected call.
        """
        if self.details.get("http_status") not in {400, 422}:
            return None
        fields = self.details.get("fields", {})
        code = fields.get("code", "").lower()
        message = fields.get("message", "").lower()
        if (code in {"invalid_json_schema", "invalid_schema", "invalid_response_format"}
                or "grammar error: unimplemented keys:" in message
                or ("schema" in message and any(s in message for s in
                    ("invalid schema", "unsupported schema", "schema is invalid")))):
            return "model_schema_rejected"
        return None

    def payload(self):
        # This is a local receipt, not an invented/raw provider response.
        return {"raw": None, "validation_error": self.envelope_code or self.rejection_code or "model_transport_error",
                "transport_error": self.details}
