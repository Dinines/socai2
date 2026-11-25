"""Direct rule mapping checks extracted from the accepted receiver tests."""
import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from app.models.alert import FusedAlert, FusionDecision
from app.services import socai2_projection as p
from app.services.delivery_recovery import make_snapshot, restore_snapshot
from app.services.lake_alert_receiver import ReceiptHold, ReceivePolicy, adapt_alert
from app.services.lake_alert_selection import SelectionPolicy
from app.services.lake_ingress import IngressProfile, KafkaPosition, adapt_ocsf
from app.services.receipt_json import encoded

ROOT = Path(__file__).resolve().parents[3]


def document(cls=2004, activity=1, **changes):
    return {"class_uid": cls, "category_uid": cls//1000, "activity_id": activity, "type_uid": cls*100+activity,
        "severity_id": 4, "time": 1795046400000, "is_alert": True,
        "metadata": {"version": "1.9.0", "uid": "lyc-record-1", "product": {"vendor_name": "Example", "name": "Sensor"}},
        "finding_info": {"uid": "lyc-finding-1", "title": "Synthetic signal"}, **changes}



def partial(doc):
    original = copy.deepcopy(doc)
    result = {k:v for k,v in doc.items() if k not in {"is_alert", "finding_info"}}
    result.update(class_uid=0, category_uid=0, activity_id=0, type_uid=0)
    result["unmapped"] = {"spirithub": {"mapping_status": "partial",
        "classification": {k: original[k] for k in ("class_uid", "category_uid", "activity_id", "type_uid")},
        "partial_fields": {k: original[k] for k in ("is_alert", "finding_info")}}}
    return result



def row(doc, policy, *, offset=1):
    profile = IngressProfile(database=policy.body["database"], tenant_id=policy.body["tenant_id"],
        source_namespace=policy.body["source_namespace"], connector_type="lyc-ocsf", kafka_cluster="lyc-cluster",
        topics=("lyc-selection",), mapping_version=policy.body["mapping_version"], ocsf_version="1.9.0")
    position = KafkaPosition(topic="lyc-selection", partition=0, offset=offset, timestamp_ms=1795046400000)
    raw = json.dumps(doc).encode() if isinstance(doc, dict) else doc
    return adapt_ocsf(raw, profile=profile, position=position).row



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
