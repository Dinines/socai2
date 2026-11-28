"""4a semantics and prospective effects; synthetic-only, no live sink/consumer."""
import copy
import json
from pathlib import Path

import pytest
from app.services.lake_alert_selection import (
    SelectionPolicy,
    delivery_effect,
    select_alert,
)
from app.services.lake_ingress import IngressProfile, KafkaPosition, adapt_ocsf

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "docs/operations/evidence/lake-alert-selection-4a-20261119-01/selection-actual.json"


@pytest.fixture
def policy(tmp_path):
    body = json.loads(POLICY.read_text())
    for rule in body["rules"].values():
        rule["identity_semantics_confirmed"] = True  # synthetic source contract only
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(body))
    return SelectionPolicy.load(path)


def document(cls=2004, activity=1, **changes):
    return {"class_uid": cls, "category_uid": cls//1000, "activity_id": activity, "type_uid": cls*100+activity,
        "severity_id": 4, "time": 1795046400000, "is_alert": True,
        "metadata": {"version": "1.9.0", "uid": "lyc-record-1", "product": {"vendor_name": "Example", "name": "Sensor"}},
        "finding_info": {"uid": "lyc-finding-1", "title": "Synthetic signal"}, **changes}


def row(doc, policy, *, offset=1):
    profile = IngressProfile(database=policy.body["database"], tenant_id=policy.body["tenant_id"],
        source_namespace=policy.body["source_namespace"], connector_type="lyc-ocsf", kafka_cluster="lyc-cluster",
        topics=("lyc-selection",), mapping_version=policy.body["mapping_version"], ocsf_version="1.9.0")
    position = KafkaPosition(topic="lyc-selection", partition=0, offset=offset, timestamp_ms=1795046400000)
    raw = json.dumps(doc).encode() if isinstance(doc, dict) else doc
    return adapt_ocsf(raw, profile=profile, position=position).row


def decision(doc, policy, **kwargs):
    return select_alert(row(doc, policy, **kwargs), policy)


@pytest.mark.parametrize(("cls", "activity", "flag", "expected"), [
    (2004,1,True,"new_alert_candidate"), (2003,1,True,"new_alert_candidate"),
    (2004,1,False,"lake_only"), (2003,1,False,"lake_only"),
    (4001,0,True,"new_alert_candidate"), (4001,2,True,"new_alert_candidate"),
    (2004,2,False,"update_candidate"), (2004,3,False,"close_candidate"),
    (2004,3,True,"close_candidate"), (2003,2,True,"update_candidate"),
    (1007,1,True,"review"), (1007,1,False,"lake_only"), (2004,99,True,"review"),
])
def test_class_specific_activity(policy, cls, activity, flag, expected):
    out = decision(document(cls, activity, is_alert=flag), policy)
    assert out["action"] == expected and out["execution"] == "not_dispatched"


@pytest.mark.parametrize("flag", [None, 0, 1, "true", "false", [], {}])
def test_only_json_boolean_is_an_alert_flag(policy, flag):
    out = decision(document(is_alert=flag), policy)
    assert out["action"] == "review" and out["reasons"] == ["alert_flag_invalid"]


def test_missing_flags_and_inactive_status(policy):
    doc = document(); del doc["is_alert"]
    assert decision(doc, policy)["reasons"] == ["finding_alert_flag_missing"]
    for activity, expected in ((2, "update_candidate"), (3, "close_candidate")):
        assert decision({**doc, "activity_id": activity, "type_uid": 200400+activity}, policy)["action"] == expected
    doc = document(4001); del doc["is_alert"]
    out = decision(doc, policy)
    assert out["action"] == "lake_only" and out["is_alert"] is None and out["reasons"] == ["unmarked_activity"]
    assert decision(document(status_id=4), policy)["action"] == "update_candidate"
    assert decision(document(status_id=True), policy)["action"] == "review"


def partial(doc):
    original = copy.deepcopy(doc)
    result = {k:v for k,v in doc.items() if k not in {"is_alert", "finding_info"}}
    result.update(class_uid=0, category_uid=0, activity_id=0, type_uid=0)
    result["unmapped"] = {"spirithub": {"mapping_status": "partial",
        "classification": {k: original[k] for k in ("class_uid", "category_uid", "activity_id", "type_uid")},
        "partial_fields": {k: original[k] for k in ("is_alert", "finding_info")}}}
    return result


def test_partial_recovery_keeps_reported_class_and_original(policy):
    doc = partial(document()); original = copy.deepcopy(doc)
    out = decision(doc, policy)
    assert out["action"] == "new_alert_candidate" and out["reported_class_uid"] == 0 and out["target_class_uid"] == 2004
    assert out["is_alert_path"].startswith("$.unmapped.spirithub.partial_fields.") and out["quality"] == "partial"
    assert out["identity"]["source_subject_id"] == decision(document(), policy)["identity"]["source_subject_id"]
    assert doc == original


def test_explicit_null_or_conflict_never_hidden(policy):
    doc = partial(document())
    assert decision({**doc, "is_alert": None}, policy)["action"] == "review"
    assert decision({**doc, "is_alert": False}, policy)["reasons"] == ["alert_flag_conflict"]
    for value in (None, {"uid": None}, {"uid": "different"}):
        out = decision({**doc, "finding_info": value}, policy)
        assert not out["identity"]["ready"]
        assert delivery_effect(out, subject_exists=False, delivered_keys=set()) == "hold_identity"
    doc["unmapped"]["spirithub"]["classification"]["type_uid"] = 400100
    assert decision(doc, policy)["reasons"] == ["class_activity_contract_invalid"]
    root_class_conflict = document(unmapped={"spirithub": {"mapping_status": "partial", "classification": {"class_uid": 4001}}})
    assert decision(root_class_conflict, policy)["reasons"] == ["reported_partial_class_conflict"]


def test_same_version_updates_source_and_scope_identity(policy):
    one = decision(document(), policy)
    retry = decision(document(), policy, offset=2)
    assert one["delivery_key"] == retry["delivery_key"] and one["identity"] == retry["identity"]
    update_doc = document(activity=2)
    update_doc["metadata"]["uid"] = "lyc-record-2"
    update = decision(update_doc, policy)
    assert one["identity"]["source_subject_id"] == update["identity"]["source_subject_id"]
    assert one["delivery_key"] != update["delivery_key"]
    changed_product = document(); changed_product["metadata"]["product"]["name"] = "Other Sensor"
    assert decision(changed_product, policy)["identity"]["source_subject_id"] != one["identity"]["source_subject_id"]
    bad = row(document(), policy); bad["source_namespace"] = "lyc-other-source"
    with pytest.raises(ValueError, match="outside_selection_scope"):
        select_alert(bad, policy)


def test_unconfirmed_identity_and_prospective_effects(policy):
    actual_policy = SelectionPolicy.load(POLICY)
    out = decision(document(), actual_policy)
    assert out["action"] == "new_alert_candidate" and not out["identity"]["ready"]
    assert delivery_effect(out, subject_exists=False, delivered_keys=set()) == "hold_identity"
    new = decision(document(), policy)
    assert new["delivery_key"] == out["delivery_key"] and new["decision_id"] != out["decision_id"]
    assert delivery_effect(new, subject_exists=False, delivered_keys=set()) == "create_alert_and_initial_task"
    assert delivery_effect(new, subject_exists=True, delivered_keys=set()) == "append_material"
    assert delivery_effect(new, subject_exists=True, delivered_keys={new["delivery_key"]}) == "duplicate_version"
    for activity, effect in ((2,"append_source_update"), (3,"append_source_close")):
        out = decision(document(activity=activity), policy)
        assert delivery_effect(out, subject_exists=False, delivered_keys=set()) == "hold_unlinked_lifecycle"
        assert delivery_effect(out, subject_exists=True, delivered_keys=set()) == effect


@pytest.mark.parametrize("raw", [None, b"not json", b"[]", b"\xff"])
def test_invalid_records_keep_lake_reference(policy, raw):
    out = decision(raw, policy)
    assert out["action"] == "review" and out["lake_ref"]["event_id"] and out["execution"] == "not_dispatched"


def test_missing_log_identity_and_corrupted_body(policy):
    doc = document(); del doc["metadata"]["uid"]
    out = decision(doc, policy)
    assert "source_record_id_missing_or_invalid" in out["identity"]["blockers"]
    original = row(document(), policy); original["source_version"] = "mismatched"
    with pytest.raises(ValueError, match="original_version_mismatch"):
        select_alert(original, policy)


def test_read_only_report_saved_and_read_back(policy, tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("selection_probe", ROOT / "docs/operations/inspect_lake_alert_candidates.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    original = row(document(), policy)

    class Client:
        def execute(self, sql, params, *, settings):
            assert sql.startswith("SELECT") and settings["readonly"] == 2
            assert params == policy.scope()
            return [(1,)]

        def execute_iter(self, sql, params, *, with_column_types, settings):
            assert "source_rank=1" in sql and "LIMIT" in sql and settings["readonly"] == 2
            assert params["source_namespace"] == policy.body["source_namespace"]
            yield [(f, "unused") for f in probe.FIELDS]
            yield [original[f] for f in probe.FIELDS]

    report = probe.scan(Client(), policy)
    probe.save_and_readback(report, tmp_path)
    saved = json.loads((tmp_path/"report.json").read_text())
    assert saved == report and saved["mode"] == "read_only_no_dispatch"
    assert saved["counts"]["logical_versions"] == 1
    assert "ocsf_json" not in saved["decisions"][0] and saved["decisions"][0]["execution"] == "not_dispatched"
    assert (tmp_path/"report.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("mutation", [
    lambda p: p["read_limits"].update(max_records=0),
    lambda p: p.update(identity_scope_paths=["raw_data.password"]),
    lambda p: p["rules"]["2004"].update(identity_path="policy.uid"),
    lambda p: p["rules"]["2004"].update(close_activity_ids=[1]),
    lambda p: p["rules"]["2004"].update(identity_semantics_confirmed=1),
])
def test_policy_rejects_incomplete_or_conflicting_rules(tmp_path, mutation):
    body = json.loads(POLICY.read_text()); mutation(body)
    path = tmp_path / "bad.json"; path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        SelectionPolicy.load(path)
