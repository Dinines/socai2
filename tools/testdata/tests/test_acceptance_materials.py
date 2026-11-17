"""Direct offline material → conversion → saved plan/readback contracts."""
import copy
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/testdata"))
import acceptance
from acceptance_contract import Profile, Recipe, Scenario
from acceptance_materials import (
    MaterialError,
    control,
    convert_package,
    inspect_package,
    read_json,
)
from alert_scenarios import generate_batch, json_bytes, sha256

EXAMPLES = ROOT / "tools/testdata/acceptance-examples"
STREAMING = ROOT / "docs/operations/evidence/model-blind-data-20261116-01/revision-02/clean-data-01"


@pytest.fixture
def profile():
    return control(Profile, read_json(EXAMPLES / "profile.json"), "profile")


def recipe(name="streaming"):
    return control(Recipe, read_json(EXAMPLES / f"{name}-conversion.json"), "recipe")


def snapshot(root):
    return {str(p.relative_to(root)): sha256(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


@pytest.fixture(scope="module")
def templates(tmp_path_factory):
    source = tmp_path_factory.mktemp("selected-templates") / "source"
    generate_batch(run_id="acceptance-material-unit", tenant=read_json(EXAMPLES / "profile.json")["tenant_id"],
                   event_time="2026-11-17T08:00:00+08:00", out=source,
                   template_ids=["phishing-macro-email", "webapp-sqli-ssrf-exploit"])
    return source


@pytest.mark.parametrize("kind,counts", [("streaming", [(3, 12), (1, 1)]), ("templates", [(2, 0)])])
def test_two_real_formats_same_entry_preserve_business_and_readback(kind, counts, templates, profile, tmp_path):
    source = STREAMING if kind == "streaming" else templates
    before = snapshot(source)
    out = tmp_path / "converted"
    original_read = Path.read_bytes

    def guarded_read(path):
        if path.is_relative_to(source) and (path.name in {"expected.json", "actions.json", "identity-map.json"}
                                           or "expected" in path.parts):
            raise AssertionError("answers and old execution controls must not be opened")
        return original_read(path)

    with patch("socket.socket", side_effect=AssertionError("offline only")), patch.object(Path, "read_bytes", guarded_read):
        plan = convert_package(source, recipe(kind), profile, out)
        assert inspect_package(out, profile) == plan == read_json(out / "plan.json")
    assert snapshot(source) == before
    assert [(p["counts"]["alerts"], p["counts"]["context"]) for p in plan["parts"]] == counts
    assert plan["selected_part"] == "part1"
    assert [p["selected"] for p in plan["parts"]] == ([True, False] if kind == "streaming" else [True])
    assert all(p["execution_status"] == "not_executed" for p in plan["parts"])
    assert plan["connection_status"] == "not_checked"
    assert plan["execution_identity"] == "requires_new_execution_identity"
    assert plan["business_connections"] == plan["kafka_sends"] == plan["model_calls"] == 0
    receipt = read_json(out / "conversion.json")
    for origin in receipt["records"]:
        raw = (source / origin["source"]).read_bytes()
        old = json.loads(raw.splitlines()[origin["source_line"] - 1] if origin["source_line"] else raw)
        new = read_json(out / origin["target"])
        assert {key: new[key] for key in old} == old
        assert new.keys() - old.keys() <= {"identity_version", "source_alert_id"}
        assert origin["target_sha256"] == sha256((out / origin["target"]).read_bytes())
    if kind == "templates":
        assert sum(len(read_json(p)["raw_event"]["telemetry"]) for p in (out / "part1/alerts").glob("*.json")) == 5
        assert not (out / "part1/context").exists()
        assert plan["parts"][0]["context_query_verification"] == "not_covered"
        assert all(link["material_status"] == "not_provided" for link in plan["parts"][0]["source_links"])
    else:
        assert [c["scope"] for c in plan["scenario"]["cases"]] == ["incident", "alerts"]
        assert [a["action"] for a in plan["parts"][1]["case_actions"]] == ["check", "check"]
        assert all(link["context"] for p in plan["parts"] for link in p["source_links"])
    with pytest.raises(MaterialError, match="already exists"):
        convert_package(source, recipe(kind), profile, out)


def test_historical_source_hashes_do_not_require_current_code_or_environment(profile, tmp_path):
    source = tmp_path / "old"
    shutil.copytree(STREAMING, source)
    manifest = read_json(source / "manifest.json")
    manifest["source_sha256"] = {"old-unavailable-code.py": "a" * 64}
    manifest["candidate_binding"] = {"historical_only": True}
    (source / "manifest.json").write_bytes(json_bytes(manifest))
    alert_path = source / "S01/alerts.jsonl"
    alerts = [json.loads(line) for line in alert_path.read_bytes().splitlines()]
    alerts[0]["unknown_observation"] = {"zero": 0, "disabled": False, "empty_results": [], "text": "原文 保持"}
    alert_path.write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in alerts))
    manifest["inputs"]["S01/alerts.jsonl"] = sha256(alert_path.read_bytes())
    (source / "manifest.json").write_bytes(json_bytes(manifest))
    out = tmp_path / "converted"
    convert_package(source, recipe(), profile, out)
    assert read_json(out / "part1/alerts/001.json")["unknown_observation"] == alerts[0]["unknown_observation"]
    alert_path.write_bytes(alert_path.read_bytes() + b" ")
    with pytest.raises(MaterialError, match="source hash"):
        convert_package(source, recipe(), profile, tmp_path / "bad-hash")
    assert not (tmp_path / "bad-hash").exists()


def test_numeric_order_and_explicit_selection_without_part1(templates, profile, tmp_path):
    out = tmp_path / "converted"
    convert_package(templates, recipe("templates"), profile, out)
    (out / "part1").rename(out / "part7")
    scenario = read_json(out / "scenario.json")
    scenario["parts"][0]["id"] = "part7"
    (out / "scenario.json").write_bytes(json_bytes(scenario))
    (out / "part7/alerts/001.json").rename(out / "part7/alerts/10.json")
    (out / "part7/alerts/002.json").rename(out / "part7/alerts/2.json")
    plan = inspect_package(out, profile)
    assert plan["selected_part"] is None and plan["selection_required"]
    assert plan["parts"][0]["files"]["alerts"] == ["part7/alerts/2.json", "part7/alerts/10.json"]
    assert inspect_package(out, profile, selected_part="part7")["selected_part"] == "part7"
    shutil.copy(out / "part7/alerts/2.json", out / "part7/alerts/02.json")
    with pytest.raises(MaterialError, match="duplicate numeric"):
        inspect_package(out, profile)


@pytest.mark.parametrize("defect,message", [
    ("timezone", "timezone"), ("required", "missing alert fields"),
    ("duplicate", "duplicate alert identity"), ("control", "control sidecars"),
    ("future", "future part"), ("missing_context", "required independent context"),
    ("case_ref", "reference is missing"), ("undeclared", "undeclared part"),
])
def test_actionable_file_and_relation_errors(defect, message, profile, tmp_path):
    out = tmp_path / "converted"
    convert_package(STREAMING, recipe(), profile, out)
    path = out / "part1/alerts/001.json"
    value = read_json(path)
    if defect == "timezone":
        value["event_time"] = "2026-11-17T08:00:00"
    elif defect == "required":
        del value["created_at"]
    elif defect == "duplicate":
        (out / "part1/alerts/002.json").write_bytes(json_bytes(value))
    elif defect == "control":
        value["raw_event"]["serialized"] = '{"expected_verdict":"private author answer"}'
    elif defect == "future":
        value["source_event_ids"] = read_json(out / "part2/alerts/001.json")["source_event_ids"]
    elif defect == "missing_context":
        value["source_event_ids"] = ["missing-independent-source"]
    elif defect == "case_ref":
        scenario = read_json(out / "scenario.json")
        scenario["cases"][0]["alert_refs"] = ["part2/alerts/001.json"]
        (out / "scenario.json").write_bytes(json_bytes(scenario))
    else:
        (out / "part9").mkdir()
    path.write_bytes(json_bytes(value))
    with pytest.raises(MaterialError, match=message):
        inspect_package(out, profile)


def test_opaque_sources_prior_parts_extra_context_and_backend_tenant(templates, profile, tmp_path):
    out = tmp_path / "converted"
    convert_package(templates, recipe("templates"), profile, out)
    (out / "part2/alerts").mkdir(parents=True)
    (out / "part1/alerts/002.json").rename(out / "part2/alerts/001.json")
    scenario = read_json(out / "scenario.json")
    scenario["parts"][0]["context_required"] = True
    scenario["parts"].append({"id": "part2", "check_level": "incident", "context_required": True})
    (out / "scenario.json").write_bytes(json_bytes(scenario))
    (out / "part1/context").mkdir()
    for number, uid in enumerate(("vendor:event:observed", "vendor:event:extra"), 1):
        event = {"schema_version": "v1", "event_id": uid, "tenant_id": profile.tenant_id,
                 "ocsf_event": {"uid": uid, "tenant_uid": profile.tenant_id, "class_uid": 1007, "time": 0,
                                "metadata": {"uid": uid}, "unknown": {"value": 0, "flag": False, "items": []}}}
        (out / f"part1/context/{number:03d}.json").write_bytes(json_bytes(event))
    for part in ("part1", "part2"):
        path = out / part / "alerts/001.json"
        value = read_json(path)
        value["source_event_ids"] = ["vendor:event:observed"]
        path.write_bytes(json_bytes(value))
    plan = inspect_package(out, profile)
    assert plan["parts"][1]["source_links"][0]["context"] == "part1/context/001.json"
    assert plan["parts"][0]["counts"]["context"] == 2
    assert read_json(out / "part1/context/001.json")["ocsf_event"]["tenant_uid"] == profile.tenant_id


def test_explicit_limits_and_safe_outputs(templates, profile, tmp_path):
    constrained = profile.model_copy(update={"limits": profile.limits.model_copy(update={"max_alerts_per_part": 1})})
    with pytest.raises(MaterialError, match="profile limit"):
        convert_package(templates, recipe("templates"), constrained, tmp_path / "too-many")
    assert not (tmp_path / "too-many").exists()
    with pytest.raises(MaterialError, match="outside the source"):
        convert_package(templates, recipe("templates"), profile, templates / "out")


def test_cli_inspects_saves_readback_without_connections(profile, templates, tmp_path, capsys):
    out = tmp_path / "converted"
    with patch("socket.socket", side_effect=AssertionError("offline only")):
        assert acceptance.main(["convert", "--source", str(templates), "--recipe", str(EXAMPLES / "templates-conversion.json"),
                                "--profile", str(EXAMPLES / "profile.json"), "--output", str(out)]) == 0
        capsys.readouterr()
        args = ["inspect", "--materials", str(out), "--profile", str(EXAMPLES / "profile.json"),
                "--report", str(tmp_path / "inspection.json")]
        assert acceptance.main(args) == 0
        summary = json.loads(capsys.readouterr().out)
        assert summary["parts"][0]["counts"] == {"alerts": 2, "context": 0}
        assert read_json(tmp_path / "inspection.json") == inspect_package(out, profile)
        assert acceptance.main(args) == 2
        capsys.readouterr()
        assert acceptance.main([*args[:-1], str(out / "inspection.json")]) == 2
        assert not (out / "inspection.json").exists()


def test_documented_schemas_match_current_control_models():
    for name, model in (("scenario", Scenario), ("profile", Profile), ("conversion", Recipe)):
        assert read_json(ROOT / f"tools/testdata/acceptance-schemas/{name}.schema.json") == model.model_json_schema()
    value = copy.deepcopy(read_json(EXAMPLES / "profile.json"))
    value["tenant_id"] = "not-a-uuid"
    with pytest.raises(MaterialError, match="tenant_id"):
        control(Profile, value, "profile")

