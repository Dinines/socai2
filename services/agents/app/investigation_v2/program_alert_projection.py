"""Freeze canonical Alert data only for the explicit new program intent.

Caller authenticates the current tenant/actor, checks run/read permissions, and
loads the owned four-column Alert row. A reference string alone proves none of
those facts. This full document is for the separate program material path; projection
alone does not bind intent, budget and owner to an atomic durable start.
"""
from __future__ import annotations

from datetime import datetime
import json
from uuid import UUID

from .business_profile import BusinessProfileRequest, CheckedBusinessTarget
from .execution_state import ExecutionRejected
from .execution_store import canonical_json, content_hash
from .scope import CheckedAlert, CheckedMemberSnapshot, SourceField, TenantPrincipal, UTCWindow, initialize_scope
from .program_start_contract import program_replay_decision

PROJECTION_SCHEMA = "canonical_program_alert_recon_projection.v1"
_COLUMNS = {"id", "tenant_id", "source_event_ids", "raw_event"}
_PATHS = {"hostname": "hostname", "source_ip": "src_ip", "dest_ip": "dst_ip",
          "dst_port": "raw_event.telemetry[0].dst_port", "protocol": "raw_event.telemetry[0].protocol",
          "source_event_ids": "source_event_ids"}
_SOURCE_PATHS = {key: "source.raw_event.telemetry[0]." + key for key in _PATHS if key != "source_event_ids"}
_SOURCE_PATHS["source_event_ids"] = "source.source_event_ids"


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ExecutionRejected(reason)


def _identity(value) -> UUID:
    _require(isinstance(value, (str, UUID)), "canonical Alert requires UUID identities")
    result = UUID(str(value))
    _require(result.int != 0, "canonical Alert requires nonnil UUID identities")
    return result


def project_program_alert_start(*, intent: dict, current_principal: TenantPrincipal, canonical_alert: dict,
                        ownership_check_ref: str) -> BusinessProfileRequest:
    """Preserve complete selected JSONB data; never infer control from its text."""
    try:
        frozen = json.loads(canonical_json(intent))
        program_replay_decision(frozen)  # Validate the complete pure intent, not authority.
        requested = frozen["request"]
        tenant, alert_id = UUID(requested["tenant_id"]), UUID(requested["target"]["id"])
        _require(isinstance(current_principal, TenantPrincipal) and tenant in current_principal.tenant_ids,
                 "current principal cannot project this tenant")
        _require(isinstance(ownership_check_ref, str) and bool(ownership_check_ref.strip()), "owned Alert check reference required")
        _require(isinstance(canonical_alert, dict) and set(canonical_alert) == _COLUMNS, "exact canonical Alert selected columns required")
        _require((_identity(canonical_alert["id"]), _identity(canonical_alert["tenant_id"])) == (alert_id, tenant),
                 "canonical Alert identity differs from start intent")
        raw = canonical_alert["raw_event"]
        raw = json.loads(raw) if isinstance(raw, str) else raw
        source_ids = canonical_alert["source_event_ids"]
        source_ids = json.loads(source_ids) if isinstance(source_ids, str) else source_ids
        _require(isinstance(raw, dict) and isinstance(source_ids, list) and len(source_ids) == 1,
                 "current Alert projection requires one explicit source UUID")
        _require(isinstance(source_ids[0], str), "source UUID must be a JSON string")
        event = _identity(source_ids[0])
        telemetry = raw["telemetry"]
        _require(isinstance(telemetry, list) and len(telemetry) == 1 and isinstance(telemetry[0], dict),
                 "current Alert projection requires one unambiguous telemetry object")
        network = telemetry[0]
        _require((_identity(network["tenant_id"]), _identity(network["event_id"])) == (tenant, event),
                 "canonical telemetry tenant or source UUID differs")
        values = {key: network[key] for key in ("hostname", "source_ip", "dest_ip", "dst_port", "protocol")}
        # The source preserves actual JSONB values and original IP/UUID spelling.
        # M1 paths name this explicit projection, not nonexistent PG IP columns.
        source = {"id": str(alert_id), "tenant_id": str(tenant), "source_event_ids": source_ids, "raw_event": raw}
        normalized = {"hostname": values["hostname"], "src_ip": values["source_ip"], "dst_ip": values["dest_ip"],
            "source_event_ids": [str(event)], "raw_event": {"telemetry": [{"dst_port": values["dst_port"], "protocol": values["protocol"]}]}}
        document = {"schema": PROJECTION_SCHEMA, "source": source, "source_sha256": content_hash(canonical_json(source)),
            "projection": normalized, "field_sources": dict(_SOURCE_PATHS),
            "normalization": {"source_event_ids": "canonical UUID spelling; original JSON retained in source",
                              "IP": "original spelling retained; M1 canonicalizes the query identity"}}
        body = canonical_json(document)
        record_ref = "checked_projection:pg.alerts:" + str(alert_id) + ":" + content_hash(body) + "#/projection"
        fields = tuple(SourceField(key, record_ref, _PATHS[key], value) for key, value in values.items())
        fields += (SourceField("source_event_ids", record_ref, _PATHS["source_event_ids"], (str(event),)),)
        member = CheckedAlert(tenant, alert_id, record_ref, ownership_check_ref, **values,
                              source_event_ids=(event,), fields=fields, data_only_text=body)
        snapshot = CheckedMemberSnapshot(ownership_check_ref, 1, (member,))
        window = UTCWindow(datetime.fromisoformat(requested["window"]["start"]), datetime.fromisoformat(requested["window"]["end"]))
        context = initialize_scope(principal=current_principal, tenant_id=tenant, run_id=UUID(frozen["run_id"]),
            snapshot=snapshot, window=window, policy_ref=requested["policy_ref"])
        target = CheckedBusinessTarget(tenant, "alert", alert_id, record_ref, ownership_check_ref, ownership_check_ref, (alert_id,))
        return BusinessProfileRequest(context, target, requested["profile"], requested["trigger"], requested["objective"], requested["policy_ref"])
    except ExecutionRejected:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise ExecutionRejected("invalid canonical Alert projection source") from None
