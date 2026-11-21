"""Canonical receipt JSON, retaining exact source numbers for lake alerts."""
import json
from decimal import Decimal

LAKE_INPUT_VERSION = "socai2.lake-alert-input.v1"


def lake_input(alert):
    value = alert.field_metadata.get("lake_ingress")
    return value if isinstance(value, dict) and value.get("schema_version") == LAKE_INPUT_VERSION else None


def model_value(model):
    value = model.model_dump(mode="json")
    if hasattr(model, "alert"):
        value["alert"] = model_value(model.alert)
    elif hasattr(model, "raw_event") and lake_input(model):
        # Pydantic's Any -> JSON encoding changes Decimal into strings.
        # The incoming envelope contains JSON-only values from the lake decoder.
        value["raw_event"] = model.raw_event
    return value


def encoded(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non_finite_receipt_number")
        return str(value)
    if isinstance(value, dict):
        return "{" + ",".join(encoded(k) + ":" + encoded(value[k]) for k in sorted(value)) + "}"
    if isinstance(value, list):
        return "[" + ",".join(encoded(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def decoded(value):
    return json.loads(value, parse_float=Decimal) if isinstance(value, (str, bytes)) else value


def canonical_numbers(value):
    """Versioned snapshot digest form, stable across PostgreSQL JSONB number spelling."""
    if isinstance(value, bool) or value is None:
        return encoded(value)
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("non_finite_receipt_number")
        sign, digits, exponent = number.as_tuple()
        digits = list(digits)
        if not any(digits):
            return "0"
        while digits[-1] == 0:
            digits.pop(); exponent += 1
        return ("-" if sign else "") + "".join(map(str,digits)) + "e" + str(exponent)
    if isinstance(value, list):
        return "[" + ",".join(canonical_numbers(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(encoded(k)+":"+canonical_numbers(value[k]) for k in sorted(value)) + "}"
    return encoded(value)
