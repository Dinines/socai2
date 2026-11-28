"""Direct local mapping-audit checks, using invented records only."""
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from audit_sample_field_mapping import (
    analyze,
    audit,
    digest,
    ingress,
    inspect_requirement,
    loads,
    render,
    save,
)


@pytest.fixture
def profile(monkeypatch):
    value = json.loads((Path(__file__).parent / "evidence/sample-field-mapping-5a-20261120-01/profile.json").read_text())
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", value["policy_file"])
    from app.socai2.runtime_policy import active_policy
    active_policy.cache_clear()
    yield value
    active_policy.cache_clear()


def event(cls=2004):
    return {"class_uid": cls, "category_uid": cls // 1000, "activity_id": 1, "type_uid": cls * 100 + 1,
            "severity_id": 0, "time": 1700000000000, "metadata": {"uid": "invented-event", "version": "1.9.0"},
            "is_alert": False}


def run(document, profile):
    card = next(c for c in profile["classes"] if c["class_uid"] == document["class_uid"])
    config = {**profile["ingress_profile"], "topics": tuple(profile["ingress_profile"]["topics"])}
    return analyze(document, profile["common"] + card["requirements"], ingress.IngressProfile(**config),
                   ingress.KafkaPosition(**profile["position"]))


def item(result, path):
    return next(r for r in result["requirements"] if r["path"] == path)


def test_root_detection_preserved_but_no_finding_projection_or_fake_partial_column(profile):
    doc = event()
    doc.update(finding_info={"uid": "invented-finding", "title": "invented detection"},
               evidences=[{"file": {"path": "invented-path"}}])
    result = run(doc, profile)
    assert result["existing_tool"] is None and result["ingress_parse_status"] == "ok"
    assert item(result, "finding_info.title")["root"]["value"] == "invented detection"
    assert item(result, "finding_info.title")["c4_output"] == []
    assert item(result, "is_alert")["root"]["state"] == "present"
    page = render({"classes": [{"class_uid": 2004, "name": "检测", "question": "材料", "analysis": result}]})
    assert "<th>partial原值</th>" not in page and "缺少partial不是数据缺陷" in page


def test_current_unmarked_fallback_is_visible_and_proposed_rule_is_stricter(profile):
    doc = event(4001)
    doc["unmapped"] = {"spirithub": {"partial_fields": {"device": {"hostname": "invented-device"}}}}
    result = run(doc, profile)
    row = item(result, "device.hostname")
    assert row["root"]["state"] == "missing" and row["partial"]["value"] == "invented-device"
    assert row["proposed_selection"]["state"] == "missing"
    assert row["lake_output"]["device_hostname"] == "invented-device"
    doc["unmapped"]["spirithub"]["mapping_status"] = "partial"
    assert item(run(doc, profile), "device.hostname")["proposed_selection"]["from"] == "partial_fields"
    doc["device"] = None
    row = item(run(doc, profile), "device.hostname")
    assert row["proposed_selection"]["state"] == "blocked_parent" and row["lake_output"]["device_hostname"] == ""


def test_arrays_keep_element_identity_conflicts_and_unknown_values(profile):
    doc = event()
    doc["evidences"] = [{"file": {"path": "invented-a"}}, {"process": {"pid": 0}}]
    doc["extra"] = {"flag": False, "precise": Decimal("1.0000000000000000000001")}
    doc["unmapped"] = {"spirithub": {"mapping_status": "partial", "partial_fields": {
        "evidences": [{"file": {"path": "invented-b"}}]}}}
    result = run(doc, profile)
    evidence = item(result, "evidences")
    assert evidence["conflict"] and evidence["proposed_selection"]["value"] == doc["evidences"]
    leaves = {leaf["path"]: leaf for leaf in result["leaf_inventory"]}
    assert leaves['$["evidences"][1]["process"]["pid"]']["value"] == 0
    assert leaves['$["extra"]["flag"]']["value"] is False
    assert leaves['$["extra"]["flag"]']["requirement_paths"] == []


def test_standard_hash_algorithm_id_only_exposes_current_gap(profile):
    doc = event(1001)
    doc["file"] = {"hashes": [{"algorithm_id": 3, "value": "a" * 64}]}
    result = run(doc, profile)
    standard = item(result, "file.hashes")
    assert standard["shape_valid"] and standard["lake_output"]["hash_sha256"] == ""
    assert standard["c4_output"] == []
    assert any(o["reason"] == "sha256_algorithm_not_explicit" for o in standard["c4_omissions"])


def test_exact_readback_types_empty_and_html_escape(tmp_path, profile):
    document = event()
    document["finding_info"] = {"title": "</pre><script>invented()</script>"}
    result = run(document, profile)
    page = render({"classes": [{"class_uid": 2004, "name": "检测", "question": "材料", "analysis": result}]})
    assert "<script>invented()" not in page and "&lt;script&gt;" in page
    precise = {"integer": 2**80, "decimal": Decimal("1.0000000000000000000001"), "flag": False, "empty": []}
    save(tmp_path / "exact.json", precise)
    assert ingress.tagged(loads((tmp_path / "exact.json").read_text())) == ingress.tagged(precise)
    req = {"path": "x", "types": ["boolean"], "use": "business", "columns": []}
    assert inspect_requirement({"x": False}, req, {}, {})["shape_valid"]
    assert not inspect_requirement({"x": 0}, req, {}, {})["shape_valid"]


def test_complete_local_run_preserves_source_and_prints_only_fixed_status(tmp_path, profile, capsys):
    source = tmp_path / "source"
    (source / "ocsf").mkdir(parents=True)
    for card in profile["classes"]:
        save(source / "ocsf" / f"class-{card['class_uid']}.json", event(card["class_uid"]))
    before = {str(p.relative_to(source)): digest(p) for p in source.rglob("*") if p.is_file()}
    save(source / "manifest.json", {"files": before})
    selected = deepcopy(profile)
    selected.update(sample_directory=str(source), output_directory=str(tmp_path / "result"))
    selection = tmp_path / "profile.json"
    save(selection, selected)
    assert audit(selected, selection) == 0
    output = capsys.readouterr().out
    assert "invented-event" not in output and json.loads(output)["execution"] == "completed"
    assert before == {p: digest(source / p) for p in before}
    report = loads((tmp_path / "result/mapping-analysis.json").read_text())
    assert len(report["classes"]) == len(profile["classes"])
    assert (tmp_path / "result/index.html").exists()
