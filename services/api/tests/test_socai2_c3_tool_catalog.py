"""C3 capability capacity: exact facts/scopes, complete guards and total cap."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.services.llm_safety import LLMInputContract
from app.socai2 import baseline_analysis as analysis
from app.socai2 import baseline_model_view as view
from app.socai2 import baseline_tool_catalog as catalog
from app.socai2.baseline_store import StoreError, encoded
from socai2_test_model_view import model_messages_data


def option(alias="B1", **changes):
    return {"binding_id": alias, "tool_name": "process_activity", "hostname": "host-one",
        "alert_ids": ["a", "b"], "object_keys": ["host:host-one"], **changes}


def fixture(padding=0):
    prepared = {"messages": [{"role": "system", "content": view.SYSTEM},
        {"role": "user", "content": encoded({"items": [], "members": {}, "padding": "x" * padding}).decode()}]}
    context = SimpleNamespace(model_dump=lambda **_: {"alerts": {}})
    return prepared, context


def test_catalog_hoists_only_adjacent_identical_scopes_and_roundtrips_all_values():
    options = [option("B1"), option("B2", tool_name="network_connections"),
        option("B3", alert_ids=["b"]), option("B4"),
        option("B5", object_keys=["host:another"], extra={"value": None, "flag": False})]
    before = copy.deepcopy(options)
    payload = catalog.data(options)
    assert len(payload["tool_option_groups"]) == 4
    decoded = model_messages_data([{"role": "system", "content": "rules"},
        {"role": "user", "content": '{"items":[]}'}, catalog.message(options)])
    assert decoded["tool_options"] == options == before
    assert payload["schema_version"] == "socai2.c3-tool-catalog.v2"
    capability = next(c for c in payload["capabilities"] if c["tool_name"] == "authentication_activity")
    assert "审批" in capability["cannot_answer"] and "event_time" in capability["returned_fields"]
    assert not capability["available"]


def test_aggregate_cap_excludes_whole_options_without_changing_fact_view():
    prepared, context = fixture(7700)
    before = copy.deepcopy(prepared)
    options = [option("B" + str(i), hostname="host-" + str(i) + "z" * 100) for i in range(20)]
    original_options = copy.deepcopy(options)
    full, _ = analysis.messages(prepared, context, {}, copy.deepcopy(options))
    cap = len(encoded(full)) - 1500
    with patch.object(analysis, "draft_limit", lambda: cap):
        prompt, source_map = analysis.messages(prepared, context, {}, options)
    assert 0 < len(options) < len(original_options)
    assert options == original_options[:len(options)] and source_map == {}
    assert prepared == before and json.loads(prompt[1]["content"])["padding"] == "x" * 7700
    assert len(encoded(prompt)) <= cap
    assert model_messages_data(prompt)["tool_options"] == options
    assert LLMInputContract.validate(prompt) == prompt


def test_catalog_cannot_create_an_evidence_cap_escape_or_unbounded_total():
    prepared, context = fixture(analysis.draft_limit() + 1)
    with pytest.raises(StoreError, match="analysis_input_contract_or_size"):
        analysis.messages(prepared, context, {}, [option()])
    prepared, context = fixture()
    with patch.object(analysis.contract, "PROMPT", "z" * analysis.draft_limit()), pytest.raises(StoreError, match="analysis_input_contract_or_size"):
        analysis.messages(prepared, context, {}, [option()])


@pytest.mark.parametrize("payload", ['{"class_uid":1007}', "-----BEGIN PRIVATE KEY-----"])
def test_full_catalog_guard_runs_before_any_capacity_trimming(payload):
    prepared, context = fixture(7700)
    options = [option("B" + str(i), hostname="host-" + str(i) + "z" * 100) for i in range(20)]
    options.append(option("B21", hostname=payload))
    before = copy.deepcopy(options)
    with pytest.raises(StoreError, match="analysis_input_contract_or_size"):
        analysis.messages(prepared, context, {}, options)
    assert options == before


def test_empty_catalog_retains_execution_shape_and_legacy_inputs_stay_two_messages():
    prepared, context = fixture()
    legacy, _ = analysis.messages(prepared, context, {})
    execution, _ = analysis.messages(prepared, context, {}, [])
    assert len(legacy) == 2 and len(execution) == 3
    assert "tool_options" not in model_messages_data(legacy)
    assert model_messages_data(execution)["tool_options"] == []


def test_closed_local_a_replay_keeps_all_three_bindings_and_all_original_facts():
    from verify_socai2_c3_catalog_20261105 import DEFAULT, load, sha
    if not DEFAULT.exists():
        pytest.skip("closed local a export is not present in this checkout")
    before = sha(DEFAULT)
    sample = load(DEFAULT)
    from app.socai2.baseline_dispatch import offered_bindings
    from app.socai2.baseline_evidence_tools import catalog as evidence_catalog
    from app.socai2.runtime_policy import active_policy
    options, _, _ = offered_bindings(evidence_catalog(sample["context"], sample["run"]["tenant_id"]),
        active_policy().case.limits(sample["now"], "synthetic-capacity-replay"), sample["now"], [], SimpleNamespace(configured=lambda: True))
    prompt, sources = analysis.messages(sample["prepared"], sample["context"], sample["tools"], options)
    original = json.loads(sample["request"]["body"]["input"][1]["content"])
    original.pop("tool_options")
    assert json.loads(prompt[1]["content"]) == original
    assert {k: {f: v for f, v in ref.items() if f != "required"} for k, ref in sources.items()} == sample["request"]["source_map"]
    assert sha(DEFAULT) == before
    assert len(options) == 3
