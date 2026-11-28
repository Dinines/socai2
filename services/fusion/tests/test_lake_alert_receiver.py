"""Direct input/serialization/size checks; PG and HTTP are verified on 21."""
import copy
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.models.alert import FusedAlert, FusionDecision, RawAlert
from app.services import socai2_projection as p
from app.services.delivery_recovery import (
    DeliveryHold,
    DeliveryRecovery,
    make_snapshot,
    restore_snapshot,
)
from app.services.lake_alert_receiver import ReceiptHold, ReceivePolicy, adapt_alert
from app.services.lake_alert_selection import SelectionPolicy
from app.services.lake_ingress import Projection, project_labels
from app.services.receipt_json import canonical_numbers, decoded, encoded, model_value
from app.services.socai2_sink import Socai2AlertSink

from .lake_ingress_cases import event
from .test_lake_alert_selection import document, partial, row

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def policies():
    return (SelectionPolicy.load(ROOT / "deploy/aisoc21/lake-alert-selection-4a/selection.example.json"),
            ReceivePolicy.load(ROOT / "deploy/aisoc21/lake-alert-receive-4b/receive.example.json"))


def fused_for(alert):
    return FusedAlert(id=alert.id, tenant_id=alert.tenant_id, incident_id=uuid4(), alert=alert,
                      fusion_decision=FusionDecision.NEW_INCIDENT, confidence_status="unknown")


def test_received_source_v1_and_full_provenance(policies):
    selection, policy = policies
    doc = document(device={"hostname":"Device", "ip":"192.0.2.1"}, src_endpoint={"hostname":"Source","ip":"192.0.2.2"},
                   confidence_id=0)
    analytic = {"uid": "rule-1", "name": "Synthetic rule"}
    doc["finding_info"]["analytic"] = analytic
    source = row(doc, selection)
    alert = adapt_alert(source, selection, policy)
    assert alert.identity_version == "source-v1" and alert.id == alert.deterministic_id()
    assert alert.external_id == doc["metadata"]["uid"] and alert.source_event_ids == [alert.external_id]
    assert alert.hostname == "Device" and alert.src_ip == "192.0.2.2" and alert.event_time is not None
    assert alert.raw_event["ocsf_event"] == doc and alert.raw_event["source_ocsf_json"] == source["ocsf_json"]
    assert (alert.rule_id, alert.rule_name) == (analytic["uid"], analytic["name"])
    fused = restore_snapshot(encoded(make_snapshot(fused_for(alert))), alert)
    _, material, refs, objects = p.project(fused, alert, p.snapshot_id(alert.id))
    assert material["raw_text"] == source["ocsf_json"] and not material["retention"]["truncated"]
    assert material["detection"]["rule_id"] == analytic["uid"]
    assert material["detection"]["rule_name"] == analytic["name"]
    assert material["ocsf_json"]["confidence_id"] == 0
    metadata = material["raw_json"]["field_metadata"]
    assert metadata["rule_id_source"] == "$.finding_info.analytic.uid"
    assert metadata["rule_name_source"] == "$.finding_info.analytic.name"
    assert refs[0]["source_namespace"] == selection.body["source_namespace"]
    assert refs[0]["source_event_id"] == alert.external_id and refs[0]["observed_at"] == alert.event_time
    assert any(obj["source_path"] == "$.ocsf_json.device.ip" for obj in objects)
    assert material["raw_json"]["field_metadata"]["lake_ingress"]["lake_ref"]["event_id"] == str(source["event_id"])


def test_native_finding_labels_reach_material_without_changing_source(policies):
    selection, policy = policies
    doc = document()
    native = event()["attacks"][0]
    doc["finding_info"]["attacks"] = [native, copy.deepcopy(native)]
    original = copy.deepcopy(doc)
    source = row(doc, selection)
    alert = adapt_alert(source, selection, policy)
    expected_tactics = [native["tactic"]["uid"]]
    expected_techniques = [native["technique"]["uid"]]
    assert source["mitre_tactics"] == alert.mitre_tactics == expected_tactics
    assert source["mitre_techniques"] == alert.mitre_techniques == expected_techniques
    _, material, _, _ = p.project(fused_for(alert), alert, p.snapshot_id(alert.id))
    assert material["detection"]["tactics"] == expected_tactics
    assert material["detection"]["techniques"] == expected_techniques
    assert material["detection"]["labels_provided"] is True
    assert material["raw_text"] == source["ocsf_json"]
    assert material["ocsf_json"] == original == doc
    assert alert.raw_event["ocsf_event"] == original

    # Keep valid labels and the same typed issue semantics; never infer from names.
    doc["finding_info"]["attacks"].extend([
        {"tactic": {"uid": False}},
        {"tactic": {"name": doc["finding_info"]["title"]}},
    ])
    projection = Projection(doc)
    assert project_labels(projection) == (expected_techniques, expected_tactics)
    assert projection.issues == {"finding_info.attacks.tactic.uid:invalid_string_item"}
    assert row(doc, selection)["parse_status"] == "partial"


def test_missing_event_time_and_partial_title_are_not_fabricated(policies):
    selection, policy = policies
    original = document()
    original["finding_info"]["analytic"] = {"uid": "rule-1", "name": "Synthetic rule"}
    doc = partial(original)
    doc.pop("time")
    alert = adapt_alert(row(doc, selection), selection, policy)
    assert alert.event_time is None and alert.ocsf_class_uid == 0
    assert alert.title == document()["finding_info"]["title"]
    assert alert.field_metadata["title_source"].startswith("$.unmapped.spirithub.partial_fields.")
    assert (alert.rule_id, alert.rule_name) == ("rule-1", "Synthetic rule")
    rule_path = "$.unmapped.spirithub.partial_fields.finding_info.analytic."
    assert alert.field_metadata["rule_id_source"] == rule_path + "uid"
    assert alert.field_metadata["rule_name_source"] == rule_path + "name"


def test_explicit_empty_rule_fields_keep_their_source_paths(policies):
    selection, policy = policies
    doc = document()
    doc["finding_info"]["analytic"] = {"uid": None, "name": ""}
    alert = adapt_alert(row(doc, selection), selection, policy)
    assert alert.rule_id is None and alert.rule_name is None
    assert alert.field_metadata["rule_id_source"] == "$.finding_info.analytic.uid"
    assert alert.field_metadata["rule_name_source"] == "$.finding_info.analytic.name"
    assert alert.raw_event["ocsf_event"] == doc


@pytest.mark.parametrize("root_uid", [None, "conflicting-rule"])
def test_rule_conflict_between_root_and_partial_fields_is_held(policies, root_uid):
    selection, policy = policies
    doc = document()
    doc["finding_info"]["analytic"] = {"uid": "rule-1"}
    candidate = partial(doc)
    candidate["finding_info"] = {"analytic": {"uid": root_uid}}
    with pytest.raises(ReceiptHold, match="projection_field_conflict"):
        adapt_alert(row(candidate, selection), selection, policy)


@pytest.mark.parametrize("mutation,reason", [
    (lambda d: d.update(severity_id=0), "source_severity_unmapped"),
    (lambda d: d.update(severity_id=None), "source_severity_unmapped"),
    (lambda d: d.pop("finding_info"), "source_title_missing"),
    (lambda d: d.update(is_alert=False), "selection_not_deliverable"),
    (lambda d: d["metadata"].pop("uid"), "selection_not_deliverable"),
])
def test_unsupported_input_has_a_specific_hold(policies, mutation, reason):
    selection, policy = policies
    doc = document(); mutation(doc)
    with pytest.raises(ReceiptHold, match=reason):
        adapt_alert(row(doc, selection), selection, policy)


def test_retries_keep_identity_and_material_key(policies):
    selection, policy = policies
    one = adapt_alert(row(document(), selection, offset=1), selection, policy)
    two = adapt_alert(row(document(), selection, offset=20), selection, policy)
    assert one.id == two.id and p.material_id(one) == p.material_id(two)
    assert one.rule_id is None and one.rule_name is None
    assert "rule_id_source" not in one.field_metadata and "rule_name_source" not in one.field_metadata


def test_long_body_exact_numbers_snapshot_and_projection(policies):
    selection, policy = policies
    raw = json.dumps(document(message="合成长正文"*100000)).removesuffix("}") + ',"large":123456789012345678901234567890,"fraction":0.12345678901234567890123456789}'
    source = row(raw.encode(), selection)
    alert = adapt_alert(source, selection, policy)
    fused = fused_for(alert)
    assert len(encoded(model_value(alert)).encode()) > 1024*1024
    with pytest.raises(DeliveryHold):
        make_snapshot(fused)
    maximum = policy.body["limits"]["snapshot_bytes"]
    saved = make_snapshot(fused, max_bytes=maximum)
    restored = restore_snapshot(encoded(saved), alert, max_bytes=maximum)
    expected = Decimal("0.12345678901234567890123456789")
    assert restored.alert.raw_event["ocsf_event"]["fraction"] == expected
    material = p.project(restored, alert, p.snapshot_id(alert.id))[1]
    readback = decoded(encoded(material))
    assert readback["ocsf_json"]["fraction"] == expected
    assert readback["raw_json"]["raw_event"]["ocsf_event"]["large"] == 123456789012345678901234567890
    assert readback["raw_text"] == source["ocsf_json"] and readback["retention"]["truncated"] is False


@pytest.mark.asyncio
async def test_large_snapshot_recovery_honors_the_selected_budget(policies):
    selection, policy = policies
    alert = adapt_alert(row(document(message="x"*1100000), selection), selection, policy)
    values = {}
    async def get(key): return values.get(key)
    async def put(key, value, **kwargs): values[key] = value; return True
    cache = SimpleNamespace(get=get, set=put)
    recovery = DeliveryRecovery(cache, policy.body["limits"]["recovery_ttl_seconds"], max_bytes=policy.body["limits"]["snapshot_bytes"])
    saved = await recovery.remember(fused_for(alert))
    loaded = await recovery.load(alert)
    assert model_value(saved) == model_value(loaded)


def test_configured_bound_holds_without_truncating(policies):
    selection, policy = policies
    body = copy.deepcopy(policy.body); body["limits"]["material_bytes"] = 100
    source = row(document(), selection); original = dict(source)
    with pytest.raises(ReceiptHold, match="received_material_exceeds_configured_limit"):
        adapt_alert(source, selection, ReceivePolicy(body))
    assert source == original


def test_new_sink_budget_is_explicit_legacy_defaults_unchanged(policies):
    _, policy = policies
    old = Socai2AlertSink("postgresql://unused", analysis_policy=policy.body["initial_analysis"])
    assert old.material_max_bytes == old.snapshot_max_bytes == 1024*1024
    new = Socai2AlertSink("postgresql://unused", analysis_policy=policy.body["initial_analysis"],
        material_max_bytes=policy.body["limits"]["material_bytes"], snapshot_max_bytes=policy.body["limits"]["snapshot_bytes"])
    assert new.material_max_bytes > old.material_max_bytes and new.snapshot_max_bytes > old.snapshot_max_bytes


def test_snapshot_digest_matches_api_after_jsonb_number_normalization(policies):
    selection, policy = policies
    alert = adapt_alert(row(document(),selection),selection,policy)
    alert.raw_event["ocsf_event"]["fraction"] = Decimal("0.12345678901234567890123456789")
    fused = fused_for(alert)
    fused.confidence_score = 0.000001
    snapshot = make_snapshot(fused)
    assert snapshot["version"] == 2
    normalized = encoded(snapshot).replace("1e-06", "0.000001")
    restored = restore_snapshot(normalized,alert)
    assert restored.confidence_score == fused.confidence_score
    spec = importlib.util.spec_from_file_location("api_material_json",ROOT / "services/api/app/socai2/material_json.py")
    api = importlib.util.module_from_spec(spec); spec.loader.exec_module(api)
    assert api.canonical_numbers(api.loads(normalized)) == canonical_numbers(snapshot)


def test_legacy_snapshot_keeps_its_original_float_digest():
    alert = RawAlert(tenant_id=uuid4(), source="lyc-legacy-receipt", title="Synthetic finding",
                     raw_event={"fraction": 0.000001})
    alert.id = alert.deterministic_id()
    fused = fused_for(alert)
    fused.confidence_score = 0.000001
    saved = make_snapshot(fused)
    assert saved["version"] == 1
    jsonb = encoded(saved).replace("1e-06", "0.000001")
    for value in (jsonb, decoded(jsonb)):
        restored = restore_snapshot(value, alert)
        assert restored.model_dump(mode="json") == fused.model_dump(mode="json")
