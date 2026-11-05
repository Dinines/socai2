"""Bounded provider diagnostics, never request bodies, URLs or credentials."""
import json
import re

import httpx

MAX_ERROR_BODY = 16384
FIELD_LIMITS = {"code": 128, "type": 128, "param": 256, "message": 1024}


def provider_error(exc, api_key):
    response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
    result = {"exception_type": type(exc).__name__,
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


class ModelCallError(RuntimeError):
    """The call did not yield a model answer; consumption may still be unknown."""

    def __init__(self, details):
        super().__init__("model_transport_error")
        self.details = details

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
        return {"raw": None, "validation_error": self.rejection_code or "model_transport_error", "transport_error": self.details}
