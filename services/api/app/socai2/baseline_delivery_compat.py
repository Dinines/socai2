"""Narrow C6 transport compatibility; the strict delivery parser remains final.

Keep the provider response intact. Only the known, empty conflicts_note extension
may be removed, with the exact transformed content retained beside the raw reply.
Missing fields, nonempty extras, scope, citations and safety checks are unchanged.
"""
import hashlib
import json

from .baseline_analysis_contract import AnalysisRejected

POLICY = "socai2.c6-null-conflicts-note.v1"


def normalize(content):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise AnalysisRejected("duplicate_json_key")
            value[key] = item
        return value

    def invalid_number(_):
        raise AnalysisRejected("invalid_json_number")

    try:
        raw = json.loads(content, object_pairs_hook=unique, parse_constant=invalid_number)
    except (ValueError, TypeError) as exc:
        if isinstance(exc, AnalysisRejected):
            raise
        raise AnalysisRejected("delivery_shape_invalid") from None
    analysis = raw.get("analysis") if isinstance(raw, dict) else None
    if not isinstance(analysis, dict) or "conflicts_note" not in analysis or analysis["conflicts_note"] is not None:
        return content, None
    del analysis["conflicts_note"]
    normalized = json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
    return normalized, {
        "policy": POLICY,
        "removed": [{"path": ["analysis", "conflicts_note"], "value": None}],
        "original_content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "normalized_content_sha256": hashlib.sha256(normalized.encode()).hexdigest(),
        "normalized_content": normalized,
        "note": "transport_only_full_delivery_validation_still_required",
    }
