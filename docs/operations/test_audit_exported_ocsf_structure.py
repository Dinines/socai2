"""Synthetic checks only; no private fixture is emitted by these tests."""
import copy
import json
from decimal import Decimal
from pathlib import Path

from app.services.lake_ingress import ABSENT, BLOCKED
from audit_exported_ocsf_structure import (
    Audit,
    classification,
    resolve,
    review_markdown,
    usable,
    values,
)

PROFILE = json.loads((Path(__file__).parent / "evidence/json-structure-design-5a-20261119-01/profile.json").read_text())


def partial(root, fallback, cls=4003):
    return {**root, "unmapped": {"spirithub": {"mapping_status": "partial", "partial_fields": fallback,
        "classification": {"class_uid": cls, "category_uid": cls // 1000, "activity_id": 1, "type_uid": cls * 100 + 1}}}}


def event():
    return {"class_uid": 4003, "category_uid": 4, "activity_id": 1, "type_uid": 400301,
        "metadata": {"uid": "synthetic-stable-id", "version": "1.9.0"}, "time": 1800000000000,
        "device": {"hostname": "synthetic-host"}, "query": {"hostname": "synthetic.invalid"}}


def test_only_absence_falls_back_and_null_ancestors_block():
    fallback = {"device": {"hostname": "synthetic-fallback"}}
    assert resolve(partial({}, fallback), "device.hostname") == ("synthetic-fallback", "partial", False)
    assert resolve(partial({"device": None}, fallback), "device.hostname") == (BLOCKED, "root", True)
    assert resolve(partial({"device": {"hostname": None}}, fallback), "device.hostname") == (None, "root", True)
    assert resolve({}, "device.hostname") == (ABSENT, "absent", False)


def test_zero_false_empty_arrays_and_recursive_typed_conflicts():
    document = partial({"is_alert": False, "rcode_id": 0, "answers": []}, {"is_alert": False, "rcode_id": 0, "answers": [{"rdata": "synthetic"}]})
    assert resolve(document, "is_alert") == (False, "root", False)
    assert usable(False, PROFILE["fields"]["is_alert"])
    assert usable(0, PROFILE["fields"]["rcode_id"])
    assert values(document, "answers[].rdata", "effective") == ([], "root", True)
    assert resolve(partial({"file": {"size": 1}}, {"file": {"size": True}}), "file")[2]
    assert resolve(partial({"file": {"size": 1}}, {"file": {"size": Decimal('1.0')}}), "file")[2]


def test_array_source_is_whole_and_pairs_are_same_element():
    document = partial(event(), {"answers": [{"type": "A", "rdata": "synthetic"}]})
    document["answers"] = [{"type": "A"}, {"rdata": "synthetic"}, None]
    vals, source, conflict = values(document, "answers[].rdata", "effective")
    assert vals == [ABSENT, "synthetic", BLOCKED] and source == "root" and conflict
    audit = Audit(PROFILE)
    audit.add(document)
    _, review = audit.reports()
    array = review["groups"][0]["arrays"]["answers"]
    assert array["same_element"]["type + rdata"] == "none"
    assert array["shapes"]["non_object_element"] == "all"
    del document["unmapped"]
    audit = Audit(PROFILE)
    audit.add(document)
    assert audit.reports()[1]["groups"][0]["arrays"]["answers"]["same_element"]["type + rdata"] == "none"


def test_partial_class_needs_consistent_declaration_not_relabeling():
    document = partial({"class_uid": 0}, {})
    identity, cls, status = classification(document, PROFILE["target_class_uids"])
    assert identity["root_class_uid"] == 0 and cls == 4003 and status == "class_arithmetic_consistent"
    document["unmapped"]["spirithub"]["classification"]["type_uid"] = 200401
    assert classification(document, PROFILE["target_class_uids"])[1] is None
    assert document["class_uid"] == 0
    document["class_uid"] = 4001
    assert classification(document, PROFILE["target_class_uids"])[2] == "conflicting_class_declaration"


def test_query_conditions_cannot_combine_separate_records_or_partial_identity():
    first, second = event(), event()
    del first["device"]
    del second["query"]
    audit = Audit(PROFILE)
    audit.add(first)
    audit.add(second)
    third = partial(event(), {"metadata": {"uid": "synthetic-fallback-id"}})
    del third["metadata"]["uid"]
    audit.add(third)
    _, review = audit.reports()
    assert all(g["same_record"]["dns_activity:effective_query_prerequisites"] == "none" for g in review["groups"])


def test_review_contains_only_whitelisted_structure_and_no_private_values():
    document = event()
    document["finding_info"] = {"title": "SECRET-SYNTHETIC-TITLE"}
    document["SECRET-SYNTHETIC-KEY"] = {"child": ["SECRET-SYNTHETIC-VALUE"]}
    original = copy.deepcopy(document)
    audit = Audit(PROFILE)
    audit.add(document)
    private, review = audit.reports()
    output = json.dumps(review) + review_markdown(review, PROFILE)
    assert "SECRET-SYNTHETIC" not in output
    assert "synthetic-stable-id" not in output and "synthetic-host" not in output and "synthetic.invalid" not in output
    assert "1800000000000" not in output and "records" not in review
    assert "SECRET-SYNTHETIC-KEY" in private["groups"][0]["inventory"]
    assert {f["path"] for f in review["groups"][0]["fields"]} == set(PROFILE["fields"])
    assert document == original
