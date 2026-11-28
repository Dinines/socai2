"""Confirmed global immutable source identity; all records are synthetic."""
import copy
import importlib.util
import json
from datetime import datetime

import pytest
from app.services.lake_alert_selection import (
    SelectionPolicy,
    delivery_effect,
    reconcile_immutable_versions,
    select_alert,
)

from .test_lake_alert_selection import ROOT, decision, document, partial, row

POLICY = ROOT / "deploy/aisoc21/lake-alert-selection-4a/selection.example.json"


@pytest.fixture
def policy():
    return SelectionPolicy.load(POLICY)


def changed_policy(policy, tmp_path, **changes):
    body = copy.deepcopy(policy.body)
    body.update(changes)
    path = tmp_path / "selection.json"
    path.write_text(json.dumps(body))
    return SelectionPolicy.load(path)


@pytest.mark.parametrize("cls", [2003, 2004, 4001])
def test_global_metadata_identity_needs_no_product_or_finding(policy, cls):
    doc = document(cls)
    del doc["metadata"]["product"]
    del doc["finding_info"]
    out = decision(doc, policy)
    assert out["schema_version"] == "socai2.lake-alert-selection.v2"
    assert out["action"] == "new_alert_candidate"
    assert out["identity"]["ready"] and out["identity"]["semantics_confirmed"]
    assert out["identity"]["scope_paths"] == []
    assert out["identity"]["source_id_path"] == "$.metadata.uid"
    assert out["identity_scope"] == "global" and out["alert_lifecycle"] == "immutable"


def test_global_identity_and_query_ownership_are_separate(policy, tmp_path):
    original = decision(document(), policy)
    other = changed_policy(policy, tmp_path, source_namespace="lyc-other-source",
                           tenant_id="20000000-0000-0000-0000-000000000002")
    doc = document()
    doc["metadata"]["product"] = {"name": "Another product"}
    doc["device"] = {"uid": "other-device", "hostname": "other-host"}
    out = decision(doc, other)
    assert out["identity"]["source_subject_id"] == original["identity"]["source_subject_id"]
    assert out["lake_ref"]["tenant_id"] != original["lake_ref"]["tenant_id"]
    with pytest.raises(ValueError, match="outside_selection_scope"):
        select_alert(row(doc, other), policy)


def test_different_records_do_not_merge_by_finding_id(policy):
    one = decision(document(), policy)
    doc = document()
    doc["metadata"]["uid"] = "lyc-record-2"
    two = decision(doc, policy)
    assert one["identity"]["source_subject_id"] != two["identity"]["source_subject_id"]
    doc["metadata"]["uid"] = "lyc-record-1"
    doc["finding_info"]["uid"] = "another-finding"
    assert decision(doc, policy)["identity"]["source_subject_id"] == one["identity"]["source_subject_id"]


@pytest.mark.parametrize("activity,status", [(2, None), (3, None), (1, 3), (1, 4), (1, 5), (1, 6)])
def test_finding_lifecycle_is_review_not_an_update(policy, activity, status):
    doc = document(activity=activity)
    if status is not None:
        doc["status_id"] = status
    out = decision(doc, policy)
    assert out["action"] == "review"
    assert out["reasons"] == ["immutable_source_lifecycle_conflict"]
    assert delivery_effect(out, subject_exists=False, delivered_keys=set()) == "review"
    assert delivery_effect(out, subject_exists=True, delivered_keys={out["delivery_key"]}) == "review"


def test_network_close_and_partial_keep_their_meaning(policy):
    assert decision(document(4001, 2), policy)["action"] == "new_alert_candidate"
    doc = partial(document())
    doc["unmapped"]["spirithub"]["partial_fields"]["finding_info"] = None
    out = decision(doc, policy)
    assert out["action"] == "new_alert_candidate" and out["identity"]["ready"]
    assert out["reported_class_uid"] == 0 and out["target_class_uid"] == 2004


@pytest.mark.parametrize("activity", [0, 99])
@pytest.mark.parametrize("as_partial", [False, True])
def test_explicit_immutable_initial_activity_preserves_source_semantics(policy, activity, as_partial):
    doc = document(activity=activity)
    source = partial(doc) if as_partial else doc
    out = decision(source, policy)
    assert out["action"] == "new_alert_candidate" and out["activity_id"] == activity
    assert out["identity"]["ready"]
    doc["is_alert"] = False
    assert decision(partial(doc) if as_partial else doc, policy)["action"] == "lake_only"
    missing = partial(doc) if as_partial else doc
    target = missing["unmapped"]["spirithub"]["partial_fields"] if as_partial else missing
    del target["is_alert"]
    assert decision(missing, policy)["reasons"] == ["finding_alert_flag_missing"]


def test_immutable_initial_activities_are_opt_in_and_cannot_include_updates(policy, tmp_path):
    rules = copy.deepcopy(policy.body["rules"])
    for rule in rules.values():
        rule.pop("initial_activity_ids", None)
    old = changed_policy(policy, tmp_path, rules=rules)
    assert decision(document(activity=0), old)["reasons"] == ["finding_activity_semantics_unmapped"]
    rules["2004"]["initial_activity_ids"] = [1, 2]
    with pytest.raises(ValueError, match="invalid_immutable_initial_activities"):
        changed_policy(policy, tmp_path, rules=rules)


def test_partial_cannot_supply_a_missing_global_id(policy):
    doc = partial(document())
    del doc["metadata"]["uid"]
    doc["unmapped"]["spirithub"]["partial_fields"]["metadata"] = {"uid": "lyc-partial-id"}
    out = decision(doc, policy)
    assert out["identity"]["source_subject_id"] is None and not out["identity"]["ready"]


def test_partial_id_conflict_does_not_hide_the_root_from_reconciliation(policy):
    doc = partial(document())
    doc["unmapped"]["spirithub"]["partial_fields"]["metadata"] = {"uid": "lyc-other-id"}
    valid, conflict = decision(document(), policy), decision(doc, policy)
    assert conflict["identity"]["source_subject_id"] == valid["identity"]["source_subject_id"]
    assert not conflict["identity"]["ready"] and "subject_id_conflict" in conflict["identity"]["blockers"]
    assert all(d["action"] == "review" for d in reconcile_immutable_versions([valid, conflict]))


@pytest.mark.parametrize("value", [None, "", " ", 123])
def test_missing_or_invalid_global_id_cannot_fall_back(policy, value):
    doc = document()
    doc["metadata"]["uid"] = value
    out = decision(doc, policy)
    assert not out["identity"]["ready"] and out["identity"]["source_subject_id"] is None
    assert delivery_effect(out, subject_exists=False, delivered_keys=set()) == "hold_identity"


def test_first_receipt_retry_and_conflicting_version(policy):
    first = decision(document(), policy)
    retry = decision(document(), policy, offset=20)
    assert first["delivery_key"] == retry["delivery_key"]
    assert delivery_effect(first, subject_exists=False, delivered_keys=set()) == "create_alert_and_initial_task"
    args = {"subject_exists": True, "delivered_keys": {first["delivery_key"]}}
    assert delivery_effect(retry, **args, subject_version=first["lake_ref"]["source_version"]) == "duplicate_version"
    assert delivery_effect(retry, **args) == "hold_existing_version_unproven"
    changed = decision(document(message="Changed source body"), policy)
    assert changed["identity"]["source_subject_id"] == first["identity"]["source_subject_id"]
    assert delivery_effect(changed, **args, subject_version=first["lake_ref"]["source_version"]) == "hold_immutable_content_conflict"
    assert delivery_effect(first, subject_exists=False, delivered_keys={first["delivery_key"]}) == "hold_existing_subject_unproven"


def test_policy_and_time_representation_do_not_change_delivery_key(policy, tmp_path):
    one = decision(document(), policy)
    limits = {**policy.body["read_limits"], "max_records": 500}
    revised = changed_policy(policy, tmp_path, read_limits=limits)
    two = decision(document(), revised)
    assert one["delivery_key"] == two["delivery_key"] and one["decision_id"] != two["decision_id"]
    original = row(document(), policy)
    native = datetime.fromisoformat(str(original["event_time"]))
    original["event_time"] = native
    assert select_alert(original, policy)["delivery_key"] == one["delivery_key"]
    original["event_time"] = native.isoformat(timespec="microseconds")
    assert select_alert(original, policy)["delivery_key"] == one["delivery_key"]


@pytest.mark.parametrize("other", [document(message="Changed source body"), document(1007), document(is_alert=False)])
def test_conflicting_versions_hold_every_candidate_independent_of_order(policy, other):
    source = [decision(document(), policy), decision(other, policy)]
    forward = reconcile_immutable_versions(copy.deepcopy(source))
    backward = reconcile_immutable_versions(list(reversed(copy.deepcopy(source))))
    assert forward == list(reversed(backward))
    assert all(d["action"] != "new_alert_candidate" for d in forward)
    assert all("immutable_subject_content_conflict" in d["reasons"] for d in forward)
    identical = reconcile_immutable_versions([source[0], copy.deepcopy(source[0])])
    assert all(d["action"] == "new_alert_candidate" for d in identical)


def test_read_only_saved_report_reconciles_before_counting(policy, tmp_path):
    spec = importlib.util.spec_from_file_location("immutable_probe", ROOT / "docs/operations/inspect_lake_alert_candidates.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    originals = [row(document(), policy), row(document(message="Changed body"), policy, offset=2)]

    class Client:
        def execute(self, sql, params, *, settings):
            assert sql.startswith("SELECT") and settings["readonly"] == 2 and params == policy.scope()
            return [(len(originals),)]

        def execute_iter(self, sql, params, *, with_column_types, settings):
            assert sql.startswith("SELECT") and settings["readonly"] == 2
            yield [(f, "unused") for f in probe.FIELDS]
            for original in originals:
                yield [original[f] for f in probe.FIELDS]

    report = probe.scan(Client(), policy)
    assert report["counts"]["actions"] == {"review": 2}
    assert all(d["prospective_effect_without_existing_subject"] == "review" for d in report["decisions"])
    probe.save_and_readback(report, tmp_path)
    assert json.loads((tmp_path / "report.json").read_text()) == report
    assert (tmp_path / "report.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(identity_scope="tenant"),
    lambda p: p.update(alert_lifecycle="mutable"),
    lambda p: p.update(identity_scope_paths=["metadata.product.name"]),
    lambda p: p["rules"]["2004"].update(identity_path="finding_info.uid"),
])
def test_v2_policy_rejects_unconfirmed_scope_assumptions(policy, tmp_path, mutation):
    body = copy.deepcopy(policy.body)
    mutation(body)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        SelectionPolicy.load(path)
