"""Direct contracts for bare ingress; legacy writer tests remain unchanged."""

import base64
import dataclasses
import json
from copy import deepcopy
from pathlib import Path

import pytest
from app.services.lake_ingress import (
    EPOCH,
    IngressProfile,
    KafkaPosition,
    adapt_ocsf,
    datetime_milliseconds,
)
from app.services.lake_writer import _INGRESS_COLUMNS, LakePersistenceError, LakeWriter

from .lake_ingress_cases import database_cases, encoded, event

ROOT = Path(__file__).resolve().parents[3]
PROFILE_FILE = ROOT / "deploy/aisoc21/lake-ingress-3c/ingress.example.json"


@pytest.fixture
def profile():
    return IngressProfile.load(PROFILE_FILE, database="lyc_lake_3c_example")


def position(offset=0, **kw):
    return KafkaPosition("lyc-ocsf-events", 0, offset, **kw)


def test_roles_labels_and_complete_column_contract(profile):
    body = event(tenant_id="not-the-profile", connector_type="body-must-not-route", activity={"actor": {"kind": "not-enabled"}})
    raw = encoded(body)
    result = adapt_ocsf(raw, profile=profile, position=position())
    row = result.row
    assert set(row) == set(_INGRESS_COLUMNS) and len(row) == 61 and "ingest_time" not in row
    schema = json.loads((ROOT / "services/api/app/db/lake_columns_v1.json").read_text())
    assert set(row) == {column[0] for column in schema["columns"] if column[0] != "ingest_time"}
    assert row["tenant_id"] == profile.tenant_id and row["connector_type"] == profile.connector_type
    assert (row["device_hostname"], row["src_hostname"], row["dst_hostname"]) == ("sensor.example", "source.example", "destination.example")
    assert row["device_ip"] != row["source_ip"] != row["dest_ip"]
    assert row["hash_sha256"] == "a" * 64 and row["hash_sha256"] != row["source_version"]
    assert row["mitre_techniques"] == ["T1003"] and row["mitre_tactics"] == ["TA0006"]
    assert row["actor_kind"] == "" and row["ocsf_json"].encode() == raw
    assert row["raw_payload"] == "false" and row["is_alert"] == 0 and row["parse_status"] == "ok"


def test_partial_fallback_does_not_override_null_invalid_or_class(profile):
    partial = {"spirithub": {"mapping_status": "partial", "partial_fields": {
        "class_uid": 4001, "is_alert": True, "device": {"hostname": "fallback.example", "ip": "203.0.113.1"}}}}
    body = event(class_uid=0, is_alert=None, device=None, unmapped=partial)
    row = adapt_ocsf(encoded(body), profile=profile, position=position()).row
    assert row["class_uid"] == 0 and row["is_alert"] is None
    assert row["device_hostname"] == "" and row["device_ip"] is None and row["parse_status"] == "partial"
    body.pop("device")
    row = adapt_ocsf(encoded(body), profile=profile, position=position()).row
    assert row["device_hostname"] == "fallback.example" and row["src_hostname"] == "source.example"


def test_class_specific_subject_and_no_guess_from_display_name(profile):
    for uid, target, expected in [(3002, "user", "user_name"), (1007, "process", "process_name")]:
        body = event(class_uid=uid, **{target: {"name": "target"}})
        assert adapt_ocsf(encoded(body), profile=profile, position=position()).row[expected] == "target"
        body.pop(target)
        assert adapt_ocsf(encoded(body), profile=profile, position=position()).row[expected] == ""
    row = adapt_ocsf(encoded(event(device={"name": "display-only"}, src_endpoint={})), profile=profile, position=position()).row
    assert row["device_hostname"] == row["src_hostname"] == ""


def test_content_identity_precision_retry_update_and_scope(profile):
    a = encoded(event(counter=9007199254740993, fraction="DECIMAL"))
    a = a.replace(b'"DECIMAL"', b'123456789012345678901234567890.010')
    b = a.replace(b'.010', b'.01')
    first = adapt_ocsf(a, profile=profile, position=position()).row
    retry = adapt_ocsf(b, profile=profile, position=position(9, timestamp_ms=2000)).row
    assert first["event_id"] == retry["event_id"] and first["source_version"] == retry["source_version"]
    assert first["source_event_id"] == "opaque/record:0"
    for changed in [a.replace(b'9007199254740993', b'9007199254740992'), a.replace(b'.010', b'.02'), a.replace(b'false', b'0')]:
        assert adapt_ocsf(changed, profile=profile, position=position()).row["event_id"] != first["event_id"]
    scoped = dataclasses.replace(profile, source_namespace="lyc-other")
    assert adapt_ocsf(a, profile=scoped, position=position()).row["event_id"] != first["event_id"]
    body = event(metadata={"version": "1.9.0"})
    missing_id = adapt_ocsf(encoded(body), profile=profile, position=position()).row
    assert missing_id["event_id"] == adapt_ocsf(encoded(body), profile=profile, position=position()).row["event_id"]
    assert missing_id["event_id"] != adapt_ocsf(encoded(body), profile=profile, position=position(1)).row["event_id"]


def test_time_is_integer_milliseconds_and_fixed_when_missing(profile):
    for value, expected in [(-1, -1), (0, 0), (1000, 1000), (False, 0), ("1000", 0), (1.0, 0), (10**30, 0)]:
        row = adapt_ocsf(encoded(event(time=value)), profile=profile, position=position()).row
        assert datetime_milliseconds(row["event_time"]) == expected
        assert row["event_time_source"] == ("ocsf_time_ms" if type(value) is int and value < 10**30 else "invalid")
    body = event(); body.pop("time")
    a = adapt_ocsf(encoded(body), profile=profile, position=position(timestamp_ms=10)).row
    b = adapt_ocsf(encoded(body), profile=profile, position=position(5, timestamp_ms=2000)).row
    assert a["event_time"] == b["event_time"] == EPOCH and a["event_id"] == b["event_id"]


def test_integer_and_decimal_tokens_cannot_share_identity_when_projection_differs(profile):
    normal = adapt_ocsf(encoded(event()), profile=profile, position=position()).row
    for body in [event(time=1000.0), event(class_uid=4001.0)]:
        changed = adapt_ocsf(encoded(body), profile=profile, position=position()).row
        assert changed["parse_status"] == "partial"
        assert changed["event_id"] != normal["event_id"]
        assert changed["source_version"] != normal["source_version"]


def test_complete_large_and_invalid_material(profile):
    cases = dict(database_cases())
    raw = cases["large"]
    row = adapt_ocsf(raw, profile=profile, position=position()).row
    assert len(raw) > 262144 and len(row["raw_payload"].encode()) > 65536
    assert row["ocsf_json"].encode() == raw and row["raw_payload"] == json.loads(raw)["raw_data"]
    assert json.loads(row["ocsf_json"])["_socai2_storage"] == {"upstream_field": "must stay unchanged"}
    for label, status in [("tombstone", "tombstone"), ("empty", "invalid_json"), ("invalid_utf8", "invalid_utf8"), ("duplicate_key", "invalid_json"), ("non_object", "non_object")]:
        raw = cases[label]; row = adapt_ocsf(raw, profile=profile, position=position()).row
        assert row["parse_status"] == status and row["ocsf_json"] == ""
        restored = base64.b64decode(row["raw_payload"]) if status == "invalid_utf8" else row["raw_payload"].encode()
        assert restored == (raw or b"")
    assert adapt_ocsf(None, profile=profile, position=position()).row["event_id"] != adapt_ocsf(b"", profile=profile, position=position()).row["event_id"]
    for raw in [b'{"x":NaN}', b'{"x":"\\ud800"}']:
        assert adapt_ocsf(raw, profile=profile, position=position()).row["parse_status"] == "invalid_json"


def test_raw_json_numbers_and_invalid_projection_retained(profile):
    raw = encoded(event(raw_data="NUMBER")).replace(b'"NUMBER"', b'{"n":9007199254740993,"v":12345678901234567890.010,"zero":0,"flag":false,"null":null}')
    row = adapt_ocsf(raw, profile=profile, position=position()).row
    assert '9007199254740993' in row["raw_payload"] and '12345678901234567890.010' in row["raw_payload"]
    body = event(is_alert="false", src_endpoint={"port": 65536, "ip": "invalid"}, file={"fingerprints": [{"algorithm_id": 3,"algorithm":"MD5","value":"a"*64}]})
    row = adapt_ocsf(encoded(body), profile=profile, position=position()).row
    assert row["src_port"] == 0 and row["source_ip"] == "::" and row["is_alert"] is None
    assert row["hash_sha256"] == "" and row["parse_status"] == "partial"
    assert json.loads(row["ocsf_json"]) == body


def test_type_uid_retains_ocsf_nonnegative_int64_range(profile):
    body = event(class_uid=50000000, type_uid=5000000001)
    valid = adapt_ocsf(encoded(body), profile=profile, position=position()).row
    assert valid["parse_status"] == "ok" and json.loads(valid["ocsf_json"])["type_uid"] == 5000000001
    for value in (-1, 2**63, False):
        row = adapt_ocsf(encoded(event(type_uid=value)), profile=profile, position=position()).row
        assert row["parse_status"] == "partial" and json.loads(row["ocsf_json"])["type_uid"] == value


def test_explicit_profile_and_transport_boundaries(profile, tmp_path):
    with pytest.raises(ValueError, match="mismatch"):
        IngressProfile.load(PROFILE_FILE, database="another_database")
    with pytest.raises(ValueError, match="explicit"):
        IngressProfile.load("", database=profile.database)
    body = json.loads(PROFILE_FILE.read_text()); body["storage_policy_file"] = "missing.json"
    path = tmp_path / "ingress.json"; path.write_text(json.dumps(body))
    with pytest.raises(FileNotFoundError):
        IngressProfile.load(path, database=profile.database)
    storage = json.loads(PROFILE_FILE.with_name("storage.example.json").read_text())
    storage["retention"]["ingest_mapping_versions"] = profile.mapping_version
    (tmp_path / "missing.json").write_text(json.dumps(storage))
    with pytest.raises(ValueError, match="mapping versions"):
        IngressProfile.load(path, database=profile.database)
    with pytest.raises(ValueError, match="topic"):
        adapt_ocsf(b'{}', profile=profile, position=KafkaPosition("other-topic", 0, 0))
    with pytest.raises(TypeError, match="bytes"):
        adapt_ocsf({}, profile=profile, position=position())
    with pytest.raises(ValueError, match="offset"):
        KafkaPosition("lyc-ocsf-events", 0, -1)


@pytest.mark.asyncio
async def test_save_receipt_is_after_insert_and_failure_is_unknown(profile):
    class Client:
        def __init__(self): self.calls = []; self.fail = False
        def execute(self, sql, rows, **kwargs):
            self.calls.append((sql, deepcopy(rows), kwargs))
            if self.fail: raise RuntimeError("synthetic backend failure")
    writer = LakeWriter(host="unused.invalid", database=profile.database, ingress_profile=profile)
    with pytest.raises(LakePersistenceError) as error:
        await writer.write_ocsf_batch([(encoded(event()), position())])
    assert error.value.outcome == "not_attempted"
    client = Client(); writer._client = client
    receipts = await writer.write_ocsf_batch([(encoded(event(time=-1)), position())])
    assert len(client.calls) == 1 and len(receipts) == 1 and receipts[0].persisted
    assert client.calls[0][1][0]["event_time"] == -1 and client.calls[0][2]["settings"]["async_insert"] == 0
    assert "ingest_time" not in client.calls[0][0]
    assert writer.metrics()["buffered"] == 0
    client.fail = True
    with pytest.raises(LakePersistenceError) as error:
        await writer.write_ocsf_batch([(encoded(event()), position(1))])
    assert error.value.outcome == "unknown" and writer.rows_written == 1 and writer.rows_dropped == 0
