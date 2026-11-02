"""Bounded, verifiable first-result snapshots for the live alert path.

An ID-only dedup hit is not evidence of an incident or of the enrichments
originally used. Missing/expired snapshots therefore stop delivery rather
than manufacturing a replacement result. This is not a distributed claim
or a promise of recovery after loss of both Postgres and Redis.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.models.alert import FusedAlert, FusionDecision, RawAlert
from app.services.event_schema import canonical_source_event_id

SNAPSHOT_VERSION = 1
MAX_SNAPSHOT_BYTES = 1024 * 1024
_PREFIX = "aisoc:fusion:delivery:v1:"


class DeliveryHold(RuntimeError):
    """A live input must remain uncommitted until its evidence is resolved."""


@dataclass(frozen=True)
class SnapshotLookup:
    exists: bool
    snapshot: dict[str, Any] | None = None
    alert_id: str | None = None


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _check_identity(fused: FusedAlert, expected: RawAlert) -> None:
    if (
        fused.alert.identity_version != expected.identity_version
        or fused.id != expected.deterministic_id()
        or fused.alert.id != fused.id
        or fused.alert.deterministic_id() != fused.id
        or fused.tenant_id != expected.tenant_id
        or fused.alert.tenant_id != expected.tenant_id
        or fused.alert.fingerprint() != expected.fingerprint()
        or fused.incident_id is None
        or fused.fusion_decision == FusionDecision.DUPLICATE
    ):
        raise DeliveryHold("fusion first-result snapshot identity or incident is unproven")


def make_snapshot(fused: FusedAlert) -> dict[str, Any]:
    _check_identity(fused, fused.alert)
    payload = fused.model_dump(mode="json")
    snapshot = {"version": SNAPSHOT_VERSION, "sha256": hashlib.sha256(_canonical(payload)).hexdigest(), "fused": payload}
    if len(_canonical(snapshot)) > MAX_SNAPSHOT_BYTES:
        raise DeliveryHold("fusion first-result snapshot exceeds the bounded size")
    return snapshot


def restore_snapshot(snapshot: Any, expected: RawAlert) -> FusedAlert:
    try:
        if isinstance(snapshot, (str, bytes)):
            if len(snapshot.encode("utf-8") if isinstance(snapshot, str) else snapshot) > MAX_SNAPSHOT_BYTES:
                raise ValueError("oversize")
            snapshot = json.loads(snapshot)
        if not isinstance(snapshot, dict) or snapshot.get("version") != SNAPSHOT_VERSION:
            raise ValueError("version")
        if len(_canonical(snapshot)) > MAX_SNAPSHOT_BYTES:
            raise ValueError("oversize")
        payload = snapshot["fused"]
        if hashlib.sha256(_canonical(payload)).hexdigest() != snapshot.get("sha256"):
            raise ValueError("hash")
        fused = FusedAlert.model_validate(payload)
        _check_identity(fused, expected)
        return fused
    except DeliveryHold:
        raise
    except Exception as exc:
        raise DeliveryHold("fusion first-result snapshot is invalid") from exc


def legacy_event_candidate(alert: RawAlert) -> RawAlert:
    """Only a lookup candidate, never authority to reuse an old folded row."""
    legacy = alert.model_copy(update={"identity_version": "legacy-v1", "identity_event_id": None,
                                      "identity_origin": None})
    legacy.id = legacy.deterministic_id()
    return legacy


def matches_legacy_event(fused: FusedAlert, incoming: RawAlert) -> bool:
    """Reuse only the exact first event recorded in a verified legacy snapshot.

    Appended PG references and similar titles cannot prove what the original
    report described. No legacy data or snapshot is backfilled here.
    """
    saved = fused.alert
    if saved.identity_version != "legacy-v1" or incoming.identity_version != "event-v1":
        return False
    # Older promotions did not project vendor rule IDs. Rule detection still
    # requires the same rule; this exception cannot bypass exact source IDs.
    same_rule = saved.rule_id == incoming.rule_id or (incoming.identity_origin == "promotion" and saved.rule_id is None)
    if saved.connector_id != incoming.connector_id or not same_rule or saved.source != incoming.source:
        return False
    saved_origin = None
    if saved.source.startswith("detection:"):
        if saved.description.startswith("Windowed detection "):
            saved_origin = "window"
        elif saved.description.startswith("Detection rule "):
            saved_origin = "rule"
    else:
        saved_origin = "promotion"
    return (saved_origin == incoming.identity_origin
            and incoming.identity_event_id in [canonical_source_event_id(value) for value in saved.source_event_ids])


class DeliveryRecovery:
    """A finite-TTL first-write cache; PostgreSQL remains authoritative."""

    def __init__(self, redis: Any, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = max(1, int(ttl_seconds))

    @staticmethod
    def key(alert: RawAlert) -> str:
        return f"{_PREFIX}{alert.tenant_id}:{alert.deterministic_id()}"

    async def load(self, alert: RawAlert) -> FusedAlert | None:
        try:
            value = await self._redis.get(self.key(alert))
            return None if value is None else restore_snapshot(value, alert)
        except DeliveryHold:
            raise
        except Exception as exc:
            raise DeliveryHold("fusion first-result cache cannot be read") from exc

    async def remember(self, fused: FusedAlert) -> FusedAlert:
        snapshot = make_snapshot(fused)
        try:
            # NX preserves the first completed result even when two callers
            # raced before the upstream dedup marker was visible. It does
            # not claim the upstream correlation/scoring side effects once.
            stored = await self._redis.set(self.key(fused.alert), _canonical(snapshot), ex=self._ttl, nx=True)
            if stored:
                return fused
            existing = await self.load(fused.alert)
            if existing is None:
                raise DeliveryHold("fusion first-result cache expired during recovery")
            return existing
        except DeliveryHold:
            raise
        except Exception as exc:
            raise DeliveryHold("fusion first-result cache cannot be confirmed") from exc
