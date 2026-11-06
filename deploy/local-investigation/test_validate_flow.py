"""Offline driver tests: no private configuration, socket or model access."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from config import DATABASE, LAKE, TENANT
from flow_export import TABLES, classify, query_for
from flow_fixture import PILOT_BATCH, PILOT_CAMPAIGN, SOURCE, encoded, prepare, uid
from validate_flow import ConfigurationStopped, Driver, FlowStopped, validate_campaign


@pytest.mark.parametrize("states", [("completed", "completed", "failed"), ("failed", "completed", "completed"),
                                    ("completed", "unknown", "completed")])
def test_known_prior_failure_still_starts_case_but_unknown_does_not(states, tmp_path):
    driver = Driver.__new__(Driver)
    driver.batch = "local-unit-prior-failure"
    driver.plan = {"case": {"host": "local-unit-host"}}
    driver.root = tmp_path
    (tmp_path / "plan.json").write_text("{}")
    driver.preflight = AsyncMock()
    driver.budget = AsyncMock(return_value={"attempted_models": 3})
    driver.read = lambda name: {"passed": True, "alert_ids": ["a0", "a1"], "incident_id": "i"}
    driver.pg = AsyncMock(side_effect=[[{"state": s, "stop_reason": "unit-reason"}] for s in states])
    driver.http = AsyncMock(return_value={"body": {"case_id": "c", "pending_run_id": "r", "scope_revision": 1}})
    driver.start_round = AsyncMock()
    saved = {}
    driver.save = lambda name, value: saved.update({name: value})
    if "unknown" in states:
        with pytest.raises(FlowStopped, match="stage_not_completed"):
            asyncio.run(driver.first())
        driver.start_round.assert_not_awaited()
    else:
        asyncio.run(driver.first())
        driver.start_round.assert_awaited_once_with("C1", "c", "r", 1)
        assert [s["state"] for s in saved["prior-stage-outcomes"]["stages"]] == list(states)


def test_fixture_uses_new_tenant_ids_and_separate_oracle():
    original = SOURCE.read_bytes()
    plan, oracle = prepare("local-unit-one", "2026-11-05T12:00:00+00:00")
    other, _ = prepare("local-unit-two", "2026-11-05T12:00:00+00:00")
    assert SOURCE.read_bytes() == original
    assert plan["tenant_id"] == TENANT and plan["database"] == DATABASE and plan["lake_database"] == LAKE
    assert len(plan["canonical_alert_ids"]) == len(set(plan["canonical_alert_ids"])) == 2
    assert not set(plan["canonical_alert_ids"]) & set(other["canonical_alert_ids"])
    assert plan["case"]["host"] == "local-unit-one-host"
    assert all(e["tenant_id"] == TENANT for e in plan["case"]["events"])
    assert all(a["tenant_id"] == TENANT for a in plan["case"]["alerts"])
    assert "behavior_truth" not in encoded(plan).decode() and oracle["authorization_available_after_H_only"]
    assert plan["max_model_calls"] == 11 and plan["global_local_model_call_cap"] == 50
    UUID(uid("local-unit-one", "A0"))


def test_additional_campaign_preserves_prior_usage_and_bounds_dispatch():
    plan, _ = prepare("local-eval-20261106-01", "2026-11-06T03:00:00+00:00",
        scenario="routine", additional_tests=True)
    assert (plan["previous_attempts"], plan["additional_attempt_cap"], plan["global_local_model_call_cap"]) == (48,21,69)
    assert plan["max_model_calls"] == 7 and plan["case"]["rounds"] == 1
    with pytest.raises(AssertionError):
        prepare("local-unregistered", "2026-11-06T03:00:00+00:00",scenario="routine",additional_tests=True)
    driver=Driver.__new__(Driver);driver.plan=plan
    driver.pg=AsyncMock(return_value=[{"state":"completed","calls":63}])
    with pytest.raises(FlowStopped,match="global_69"):
        asyncio.run(driver.budget(7))
    assert asyncio.run(driver.budget(6))["global_cap"] == 69


def pilot(**changes):
    settings = {"batch": PILOT_BATCH, "window_start": "2026-11-06T07:00:00+00:00", "scenario": "routine",
                "backend": "deployed", "deployed_pilot": True, "model_values": {
                    "OPENAI_MODEL": "local-test-model", "OPENAI_BASE_URL": "http://model.invalid/v1",
                    "SOCAI2_MODEL_PROTOCOL": "chat_completions", "SOCAI2_MODEL_SCHEMA_PROFILE": "vllm_grammar_v1"}}
    return prepare(**{**settings, **changes})


def test_deployed_pilot_real_inputs_and_campaign_boundaries():
    plan, oracle = pilot()
    validate_campaign(plan, PILOT_BATCH)
    assert (plan["comparison_batch_id"], plan["previous_attempts"], plan["max_model_calls"],
            plan["global_local_model_call_cap"], plan["max_runs"]) == ("local-eval-20261106-01", 63, 7, 70, 4)
    assert oracle["behavior_truth"] == "benign" and b"behavior_truth" not in encoded(plan)
    assert plan["case"]["rounds"] == 1 and "second" not in plan["phase_order"]
    reference, _ = prepare("local-eval-20261106-01", "2026-11-06T03:00:00+00:00", scenario="routine",
                           additional_tests=True)
    assert set(reference["canonical_alert_ids"]).isdisjoint(plan["canonical_alert_ids"])
    alerts = plan["case"]["alerts"]
    assert alerts[0]["username"] == alerts[1]["username"] and "operator-0" not in str(plan["case"])
    for alert, event, other in zip(alerts, plan["case"]["events"], reference["case"]["events"], strict=True):
        ocsf = event["ocsf_event"]
        assert alert["raw_event"] == event and ocsf["actor"]["user"]["name"] == alert["username"]
        assert json.loads(ocsf["raw_data"]) == {k: v for k, v in ocsf.items() if k != "raw_data"}
        assert ocsf["activity"] == other["ocsf_event"]["activity"] and ocsf["process"] == other["ocsf_event"]["process"]
    with pytest.raises(ConfigurationStopped):
        validate_campaign(plan, "local-different-directory")
    with pytest.raises(ConfigurationStopped):
        validate_campaign({**plan, "global_local_model_call_cap": 71}, PILOT_BATCH)
    with pytest.raises(ConfigurationStopped):
        validate_campaign({**plan, "campaign": "legacy", "global_local_model_call_cap": 50}, PILOT_BATCH)


@pytest.mark.parametrize("changes", [
    {"deployed_pilot": False}, {"batch": "local-different-batch"}, {"scenario": "credential"},
    {"backend": "deepseek"}, {"additional_tests": True},
])
def test_deployed_pilot_is_explicit_and_single_case(changes):
    with pytest.raises(ValueError):
        pilot(**changes)


@pytest.mark.parametrize("used,allowed", [(0, False), (62, False), (63, True), (64, False)])
def test_deployed_pilot_requires_63_prior_attempts_and_7_available(used, allowed):
    driver = Driver.__new__(Driver)
    driver.plan = {"campaign": PILOT_CAMPAIGN, "global_local_model_call_cap": 70}
    driver.pg = AsyncMock(return_value=[{"state": "completed", "calls": used}])
    if allowed:
        assert asyncio.run(driver.budget(7))["attempted_models"] == 63
    else:
        with pytest.raises(FlowStopped):
            asyncio.run(driver.budget(7))


def test_deployed_pilot_does_not_run_another_round():
    driver = Driver.__new__(Driver)
    driver.plan, _ = pilot()
    driver.preflight = AsyncMock()
    with pytest.raises(ConfigurationStopped, match="no_human_followup"):
        asyncio.run(driver.second())
    driver.preflight.assert_not_awaited()


def test_all_29_exports_are_readonly_and_parameter_scoped():
    assert len(TABLES) == len(set(TABLES)) == 29
    for table in TABLES:
        query = query_for(table)
        assert "t.tenant_id=s.tenant" in query and all(f"${i}::uuid" in query for i in range(1, 6))
        assert query.startswith("WITH scope AS (SELECT") and "jsonb_agg(to_jsonb(t)" in query
        assert not any(command in query.upper() for command in ("DELETE ", "UPDATE ", "INSERT ", "DROP "))
    with pytest.raises(AssertionError):
        query_for("users")


@pytest.mark.parametrize("scenario", ["routine", "credential", "impact"])
def test_comparison_payload_identity_and_oracle_separation(scenario):
    plan, oracle = prepare("local-unit-" + scenario, "2026-11-05T13:00:00+00:00", scenario=scenario)
    case = plan["case"]
    for alert, event in zip(case["alerts"], case["events"], strict=True):
        assert alert["raw_event"] == event
        assert alert["source_event_ids"] == [event["event_id"]]
        ocsf = dict(event["ocsf_event"])
        raw = json.loads(ocsf.pop("raw_data"))
        assert raw == ocsf and alert["event_time"] == ocsf["time"]
        assert alert["mitre_tactics"] == alert["mitre_techniques"] == []
    assert "behavior_truth" not in encoded(plan).decode()
    assert oracle["behavior_truth"] == ("benign" if scenario == "routine" else "malicious")
    assert case["rounds"] == 1 and "second" not in plan["phase_order"]


@pytest.mark.parametrize("state,calls,reserve,expected", [("unknown", 1, 0, "active_or_unknown"),
    ("running", 1, 0, "active_or_unknown"), ("completed", 44, 7, "global_50"), ("completed", 46, 4, None)])
def test_global_budget_and_unknown_never_dispatch(state, calls, reserve, expected):
    driver = Driver.__new__(Driver)
    driver.pg = AsyncMock(return_value=[{"id": uid("local-unit-one", "run"), "state": state, "calls": calls}])
    if expected:
        with pytest.raises(FlowStopped, match=expected):
            asyncio.run(driver.budget(reserve))
    else:
        result = asyncio.run(driver.budget(reserve))
        assert result["attempted_models"] == 46 and result["global_cap"] == 50


def test_intent_is_exclusive_and_export_classification_does_not_call_failure_accuracy(tmp_path):
    driver = Driver.__new__(Driver)
    driver.root = tmp_path
    driver.save("first-intent", {"max_model_calls": 7})
    with pytest.raises(FileExistsError):
        driver.save("first-intent", {"max_model_calls": 7})
    result = classify({"run_steps": [{"id": "s", "run_id": "r", "stage_code": "C6", "state": "skipped",
        "error": {"code": "model_token_budget_insufficient"}}]})
    assert result["counts"] == {"skip_policy": 1} and result["failure_counts"] == {}
    assert "not_model_accuracy" in result["meaning"]


def test_export_preserves_raw_states_and_separates_skips_from_failures():
    from copy import deepcopy

    pairs = [("skipped", "no_supported_frozen_objects"), ("skipped", "source_not_connected"),
        ("skipped", "tool_budget_reserved_for_evidence"), ("skipped", "model_view_not_ready"),
        ("skipped", "unrecognized_reason"), ("skipped", None),
        ("failed", "no_supported_frozen_objects"), ("unknown", "source_not_connected"),
        ("failed", "delivery_shape_invalid"), ("completed", None)]
    data = {"run_steps": [{"id": str(i), "run_id": "r", "stage_code": "C2", "state": state,
        "error": {"code": code} if code is not None else None} for i, (state, code) in enumerate(pairs)]}
    original = deepcopy(data)
    result = classify(data)
    assert data == original and len(result["rows"]) == 9
    assert [(r["state"], r["code"]) for r in result["rows"]] == pairs[:-1]
    assert result["skip_counts"] == {"skip_not_applicable": 1, "skip_source_availability": 1,
        "skip_policy": 1, "skip_missing_prerequisite": 1, "skip_unclassified": 2}
    assert result["failure_counts"] == {"contract_or_execution": 2}
    assert result["unknown_counts"] == {"uncertain_execution": 1}
    assert result["state_counts"] == {"skipped": 6, "failed": 2, "unknown": 1}


def test_second_round_rejects_system_only_or_wrong_first_identity():
    created = {"case_id": "case"}
    run = {"run": {"id": "run", "state": "completed"}, "result_ids": ["result"]}
    result = {"id": "result", "case_id": "case", "source_run_id": "run", "validation_state": "system_only",
        "conclusion_origin": "system", "conclusion": None}
    driver = Driver.__new__(Driver)
    values = {"case-create-response": {"body": created}, "C1-response": {"body": run},
        "C1-result-0-response": {"body": {"result": result}}}
    driver.read = values.__getitem__
    with pytest.raises(AssertionError):
        driver.accepted_first()
    result.update(validation_state="accepted", conclusion_origin="model", conclusion="Needs review")
    assert driver.accepted_first()[1] == result
    result["case_id"] = "other"
    with pytest.raises(AssertionError):
        driver.accepted_first()


def test_export_manifest_keeps_api_sources_and_excludes_oracle(tmp_path):
    from contextlib import asynccontextmanager
    from pathlib import Path

    from flow_export import export
    from flow_fixture import sha
    case_row={"id":uid("local-test-export","case"),"tenant_id":TENANT,"title":"retained",
        "row_version":1,"scope_revision":0,"current_assessment_id":None,"current_evidence_artifact_id":None}
    @asynccontextmanager
    async def transaction(**kwargs):
        assert kwargs == {"isolation": "repeatable_read", "readonly": True}
        yield
    async def fetchval(sql, *_args):
        return json.dumps([case_row]) if "FROM socai2.cases t " in sql else "[]"
    connection = SimpleNamespace(transaction=transaction, execute=AsyncMock(), fetchval=fetchval, close=AsyncMock())
    body = {"current_assessment": {"input_freshness": {"freshness_status": "current"}}}
    async def http(_label, method, path, **_kwargs):
        return {"method": method, "path": path, "status": 200, "body": body}
    driver = SimpleNamespace(root=tmp_path, plan={"batch_id": "local-test-export",
        "canonical_alert_ids": [uid("local-test-export", "a0"), uid("local-test-export", "a1")]},
        connect=AsyncMock(return_value=connection), http=http)
    (tmp_path / "expected.json").write_text('{"oracle":"must remain separate"}')
    result = asyncio.run(export(driver))
    folder = Path(result["export_directory"])
    manifest = json.loads((folder / "manifest.json").read_text())
    data = json.loads((folder / "database.json").read_text())
    assert manifest["schema_version"] == "socai2.page-export.v1" and manifest["input_kind"] == "synthetic"
    assert data["cases"] == [case_row] and len(data) == 29
    assert manifest["source_sha256"] == sha((folder / "database.json").read_bytes())
    responses = json.loads((folder / "api-responses.json").read_text())
    assert all(r["body"] == body for r in responses) and not (folder / "expected.json").exists()
    page=json.loads((folder/'case-page-data.json').read_text())[0]['page_data']
    assert page['determination'] is None and page['evidence']['evidence_count'] is None
