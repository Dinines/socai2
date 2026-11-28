"""Bare OCSF v1 projection. Originals stay intact; this module performs no I/O."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "socai2.lake-record.v1"
MAPPING_VERSION = "spirithub-ocsf-lake-v1"
NEW_COLUMNS = (
    "source_namespace", "source_event_id", "source_version", "is_alert", "device_hostname", "device_ip",
    "event_time_source", "parse_status", "mapping_version", "kafka_cluster", "kafka_topic",
    "kafka_partition", "kafka_offset", "kafka_timestamp",
)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
MIN_TIME = datetime(1900, 1, 1, tzinfo=UTC)
MAX_TIME = datetime(2300, 1, 1, tzinfo=UTC)
ABSENT = object()
BLOCKED = object()


@dataclass(frozen=True)
class IngressProfile:
    database: str
    tenant_id: str
    source_namespace: str
    connector_type: str
    kafka_cluster: str
    topics: tuple[str, ...]
    mapping_version: str
    ocsf_version: str

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", self.database):
            raise ValueError("invalid ingress database")
        object.__setattr__(self, "tenant_id", str(uuid.UUID(self.tenant_id)))
        for name in ("source_namespace", "connector_type", "kafka_cluster"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"missing ingress {name}")
            value.encode("utf-8", errors="strict")
        if not isinstance(self.topics, tuple) or not self.topics or any(not isinstance(t, str) or not t.strip() for t in self.topics):
            raise ValueError("ingress topics must be explicitly selected")
        if self.mapping_version != MAPPING_VERSION or self.ocsf_version != "1.9.0":
            raise ValueError("unsupported ingress mapping/OCSF version")

    @classmethod
    def load(cls, path: str | Path, *, database: str) -> IngressProfile:
        if not path:
            raise ValueError("explicit ingress profile required")
        path = Path(path)
        body = json.loads(path.read_text())
        expected = set(cls.__dataclass_fields__) | {"storage_policy_file", "legacy_activity_extension_enabled"}
        if set(body) != expected or body["legacy_activity_extension_enabled"] is not False:
            raise ValueError("incomplete/unsupported ingress profile")
        storage_file = body.pop("storage_policy_file")
        body.pop("legacy_activity_extension_enabled")
        if not isinstance(storage_file, str) or not storage_file.strip():
            raise ValueError("explicit storage policy file required")
        if not isinstance(body["topics"], list):
            raise TypeError("ingress topics must be a list")
        body["topics"] = tuple(body["topics"])
        profile = cls(**body)
        storage = json.loads((path.parent / storage_file).read_text())
        if set(storage) != {"database", "retention"} or not isinstance(storage["retention"], dict):
            raise ValueError("invalid storage policy structure")
        if profile.database != database or storage["database"] != database:
            raise ValueError("ingress/storage/runtime database mismatch")
        retention = storage["retention"]
        if set(retention) != {"ingest_mapping_versions", "ingest_days", "legacy_days"}:
            raise ValueError("incomplete storage retention policy")
        versions = retention["ingest_mapping_versions"]
        if not isinstance(versions, list) or any(not isinstance(v, str) or not v for v in versions):
            raise ValueError("invalid storage mapping versions")
        if type(retention["legacy_days"]) is not int or not 1 <= retention["legacy_days"] <= 3650:
            raise ValueError("invalid storage legacy retention")
        if profile.mapping_version not in retention["ingest_mapping_versions"] or type(retention["ingest_days"]) is not int or retention["ingest_days"] != 400:
            raise ValueError("ingress requires its approved ingestion-time retention policy")
        return profile


@dataclass(frozen=True)
class KafkaPosition:
    topic: str
    partition: int
    offset: int
    timestamp_ms: int | None = None

    def __post_init__(self):
        for name, limit in (("partition", 2**31), ("offset", 2**63)):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value < limit:
                raise ValueError(f"invalid Kafka {name}")
        if not isinstance(self.topic, str) or not self.topic.strip():
            raise ValueError("missing Kafka topic")
        if self.timestamp_ms is not None and epoch_time(self.timestamp_ms)[1] != "ocsf_time_ms":
            raise ValueError("invalid Kafka timestamp; represent unavailable time as None")


@dataclass(frozen=True)
class AdaptedRecord:
    row: dict[str, Any]
    issues: tuple[str, ...]


def json_text(value: Any) -> str:
    """Serialize parsed JSON values without converting exact decimals to floats/strings."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(json_text(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(json_text(k) + ":" + json_text(v) for k, v in value.items()) + "}"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def tagged(value: Any) -> list:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, str):
        value.encode("utf-8", errors="strict")
        return ["string", value]
    if isinstance(value, (int, Decimal)):
        # Integer-only OCSF projections distinguish 1 from 1.0. Collapsing
        # those here would give one identity different time/class sort keys.
        kind = "integer" if type(value) is int else "decimal"
        number = Decimal(value)
        if not number.is_finite():
            raise ValueError("nonfinite")
        if number == 0:
            return [kind, "0e0"]
        sign, digits, exponent = number.as_tuple()
        digits = list(digits)
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        return [kind, ("-" if sign else "") + "".join(map(str, digits)) + "e" + str(exponent)]
    if isinstance(value, list):
        return ["array", [tagged(v) for v in value]]
    if isinstance(value, dict):
        for key in value:
            key.encode("utf-8", errors="strict")
        return ["object", [[key, tagged(value[key])] for key in sorted(value)]]
    raise TypeError("unsupported canonical value")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(_):
    raise ValueError("nonfinite JSON number")


def decode(payload: bytes | None):
    if payload is None:
        return None, "", "tombstone", None
    if not isinstance(payload, bytes):
        raise TypeError("bare ingress requires original bytes or a Kafka tombstone")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, base64.b64encode(payload).decode("ascii"), "invalid_utf8", None
    try:
        value = json.loads(text, parse_float=Decimal, object_pairs_hook=_unique, parse_constant=_nonfinite)
        canonical = json_text(tagged(value)).encode("utf-8")
    except (ValueError, UnicodeError, InvalidOperation, RecursionError, OverflowError):
        return None, text, "invalid_json", None
    if not isinstance(value, dict):
        return None, text, "non_object", None
    version = "sha256:full-record-v1:" + hashlib.sha256(canonical).hexdigest()
    return value, text, "ok", version


def epoch_time(value):
    if value is ABSENT or value is None:
        return EPOCH, "missing"
    if type(value) is not int:
        return EPOCH, "invalid"
    try:
        result = EPOCH + timedelta(milliseconds=value)
    except OverflowError:
        return EPOCH, "invalid"
    return (result, "ocsf_time_ms") if MIN_TIME <= result < MAX_TIME else (EPOCH, "invalid")


def datetime_milliseconds(value: datetime) -> int:
    delta = value - EPOCH
    return delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000


def nested(value, path):
    for key in path:
        if not isinstance(value, dict):
            return BLOCKED  # explicit null/invalid ancestor is not an absent path
        if key not in value:
            return ABSENT
        value = value[key]
    return value


class Projection:
    def __init__(self, document):
        self.document = document
        self.issues: set[str] = set()

    def value(self, path, *, role=False):
        value = nested(self.document, path)
        if role and value is ABSENT:
            value = nested(self.document, ("unmapped", "spirithub", "partial_fields", *path))
        return value

    def bad(self, path, reason):
        self.issues.add(".".join(path) + ":" + reason)

    def string(self, path, *, role=False):
        value = self.value(path, role=role)
        if value is ABSENT or value is None:
            return ""
        if not isinstance(value, str):
            self.bad(path, "invalid_string")
            return ""
        return value

    def uint(self, path, bits, *, required=False, role=False):
        value = self.value(path, role=role)
        if type(value) is int and 0 <= value < 2**bits:
            return value
        if required or value is not ABSENT and value is not None:
            self.bad(path, "missing_or_invalid_integer")
        return 0

    def ip(self, path):
        value = self.value(path, role=True)
        if value is ABSENT or value is None:
            return None
        try:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("not an IP string")
            ip = ipaddress.ip_address(value.strip())
            return ipaddress.IPv6Address("::ffff:" + str(ip)) if isinstance(ip, ipaddress.IPv4Address) else ip
        except ValueError:
            self.bad(path, "invalid_ip")
            return None

    def array(self, path, *, role=False):
        value = self.value(path, role=role)
        if value is ABSENT or value is None:
            return []
        if not isinstance(value, list):
            self.bad(path, "invalid_array")
            return []
        return value

    def strings(self, value, path):
        if not isinstance(value, list):
            self.bad(path, "invalid_array")
            return []
        if any(not isinstance(v, str) for v in value):
            self.bad(path, "invalid_string_item")
        return [v for v in value if isinstance(v, str) and v]


def project_labels(projection):
    """Return explicit techniques/tactics, retaining the projection's issues."""
    p = projection
    techniques = p.strings(p.array(("mitre_techniques",)), ("mitre_techniques",))
    tactics = p.strings(p.array(("mitre_tactics",)), ("mitre_tactics",))
    for field in (("mitre_attck",), ("attacks",), ("finding_info", "attacks")):
        for item in p.array(field):
            if not isinstance(item, dict):
                p.bad(field, "invalid_object_item")
                continue
            paths = (("technique_id",), ("tactic_names",)) if field == ("mitre_attck",) else (("technique", "uid"), ("tactic", "uid"))
            for output, path in zip((techniques, tactics), paths, strict=True):
                value = nested(item, path)
                if value is ABSENT or value is None:
                    continue
                output.extend(p.strings(value if path == ("tactic_names",) else [value], (*field, *path)))
    return list(dict.fromkeys(techniques)), list(dict.fromkeys(tactics))


def _fingerprints(p):
    sha256, values = "", []
    for item in p.array(("file", "fingerprints"), role=True):
        if not isinstance(item, dict):
            p.bad(("file", "fingerprints"), "invalid_object_item")
            continue
        algorithm_id = item.get("algorithm_id")
        algorithm = item.get("algorithm")
        named_sha = isinstance(algorithm, str) and algorithm.upper().replace("-", "") == "SHA256"
        id_sha = type(algorithm_id) is int and algorithm_id == 3
        is_sha = named_sha or id_sha
        if is_sha and (algorithm_id is not None and not id_sha or algorithm is not None and not named_sha):
            p.bad(("file", "fingerprints"), "conflicting_sha256_algorithm")
            continue
        value = item.get("value")
        if not isinstance(value, str) or not value or is_sha and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            p.bad(("file", "fingerprints"), "invalid_fingerprint")
            continue
        values.append(value)
        if is_sha and not sha256:
            sha256 = value
    return sha256, values


def adapt_ocsf(payload: bytes | None, *, profile: IngressProfile, position: KafkaPosition) -> AdaptedRecord:
    if position.topic not in profile.topics:
        raise ValueError("Kafka topic is outside the selected ingress profile")
    document, original, status, version = decode(payload)
    p = Projection(document or {})
    row = {name: "" for name in (
        "actor_kind", "actor_kind_source", "actor_id", "actor_on_behalf_of", "action", "resource_type", "resource_id", "resource_owner",
        "src_country_code", "src_as_org", "client_family", "client_version", "client_category", "client_raw", "outcome",
        "session_id", "session_key", "session_key_kind", "session_originating_human",
    )}
    row.update(src_asn=0, src_reputation=0.0, src_reputation_known=0)
    row.update({name: p.uint((name,), bits, required=True) for name, bits in (("class_uid", 32), ("category_uid", 32), ("activity_id", 32), ("severity_id", 8))})
    # OCSF 1.9 type_uid is long_t; it is retained in JSON, not a UInt32 column.
    p.uint(("type_uid",), 63, required=True)
    event_time, time_source = epoch_time(p.value(("time",)))
    if time_source != "ocsf_time_ms":
        p.bad(("time",), time_source)
    if not isinstance(p.value(("metadata",)), dict):
        p.bad(("metadata",), "missing_or_invalid_object")
    if p.string(("metadata", "version")) != profile.ocsf_version:
        p.bad(("metadata", "version"), "missing_or_unsupported_version")
    source_id = p.string(("metadata", "uid"))
    source_id = source_id if source_id.strip() else ""
    src, dst, device = (p.ip((role, "ip")) for role in ("src_endpoint", "dst_endpoint", "device"))
    is_alert = p.value(("is_alert",), role=True)
    if type(is_alert) is bool or type(is_alert) is int and is_alert in (0, 1):
        is_alert = int(is_alert)
    else:
        if is_alert is not ABSENT and is_alert is not None:
            p.bad(("is_alert",), "invalid_bool")
        is_alert = None
    sha256, fingerprints = _fingerprints(p)
    techniques, tactics = project_labels(p)
    raw = p.value(("raw_data",))
    row.update(
        tenant_id=profile.tenant_id, event_time=event_time, severity=p.string(("severity",)),
        source_ip=str(src or "::"), dest_ip=str(dst or "::"),
        src_port=p.uint(("src_endpoint", "port"), 16, role=True), dst_port=p.uint(("dst_endpoint", "port"), 16, role=True),
        protocol=p.string(("connection_info", "protocol_name"), role=True),
        src_hostname=p.string(("src_endpoint", "hostname"), role=True), dst_hostname=p.string(("dst_endpoint", "hostname"), role=True),
        device_hostname=p.string(("device", "hostname"), role=True), device_ip=str(device) if device else None,
        user_name=p.string(("user", "name") if row["class_uid"] == 3002 else ("actor", "user", "name"), role=True),
        process_name=p.string(("process", "name") if row["class_uid"] == 1007 else ("actor", "process", "name"), role=True),
        file_path=p.string(("file", "path"), role=True), hash_sha256=sha256, connector_type=profile.connector_type,
        raw_payload=("" if raw is ABSENT else raw if isinstance(raw, str) else json_text(raw)) if document is not None else original,
        ocsf_json=original if document is not None else "", mitre_techniques=techniques, mitre_tactics=tactics,
        iocs=list(dict.fromkeys([*(str(ip.ipv4_mapped or ip) for ip in (src, dst) if ip is not None), *fingerprints])),
        source_namespace=profile.source_namespace, source_event_id=source_id, is_alert=is_alert,
        event_time_source=time_source, mapping_version=profile.mapping_version, kafka_cluster=profile.kafka_cluster,
        kafka_topic=position.topic, kafka_partition=position.partition, kafka_offset=position.offset,
        kafka_timestamp=epoch_time(position.timestamp_ms)[0] if position.timestamp_ms is not None else None,
    )
    if document is not None:
        if p.value(("unmapped", "spirithub", "mapping_status")) == "partial":
            p.bad(("unmapped", "spirithub", "mapping_status"), "upstream_partial")
        status = "partial" if p.issues else "unclassified" if row["class_uid"] == 0 else "ok"
    else:
        version = f"sha256:raw-bytes-v1:{status}:" + hashlib.sha256(payload or b"").hexdigest()
        p.issues = {status}
    identity = [CONTRACT_VERSION, profile.tenant_id, profile.source_namespace]
    identity += ["source", source_id, version] if source_id else ["kafka", profile.kafka_cluster, position.topic, position.partition, position.offset, version]
    row.update(source_version=version, parse_status=status, event_id=str(uuid.uuid5(uuid.NAMESPACE_URL, json_text(identity))))
    return AdaptedRecord(row, tuple(sorted(p.issues)))
