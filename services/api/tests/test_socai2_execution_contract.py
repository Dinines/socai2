"""Current execution rejects incomplete contracts before storage, queues or models."""
import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from app.socai2 import analysis_case_executor, runtime_policy
from app.socai2.alert_basic_executor import AlertBasicExecutor
from app.socai2.analysis_dispatch_runtime import validate_executors
from app.socai2.baseline_context import capture
from app.socai2.baseline_deep import BaselineDeep
from app.socai2.baseline_executor import BaselineExecutor
from app.socai2.baseline_reanalysis import BaselineReanalysis
from app.socai2.baseline_store import StoreError
from app.socai2.case_allocation_policy import CaseAllocationPolicy
from app.socai2.incident_diagnosis_executor import IncidentDiagnosisExecutor

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml"


@pytest.fixture
def current(monkeypatch):
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(POLICY))
    selected = runtime_policy.active_policy
    selected.cache_clear()
    yield selected()
    selected.cache_clear()


def config(path=POLICY):
    value = json.loads((ROOT / "deploy/local-investigation/analysis-aic-executors.example.json").read_text())
    return {**value, "investigation_policy_file": str(path)}


@pytest.mark.parametrize("missing", ["alert_io", "incident_io", "case_io"])
def test_factory_rejects_missing_contract_before_constructing_handlers(current, missing, monkeypatch):
    monkeypatch.setattr(analysis_case_executor, "active_policy", lambda: replace(current, **{missing: None}))
    def forbidden(*args):
        pytest.fail("partial handlers must not be constructed")
    monkeypatch.setattr(analysis_case_executor, "ai_executors", forbidden)
    with pytest.raises(ValueError, match="execution_profile_required:" + missing):
        analysis_case_executor.executors(config(), SimpleNamespace(sessions=None))


def test_complete_factory_and_configured_budget_remain_valid(current, tmp_path, monkeypatch):
    target = tmp_path / "policy.toml"
    source = POLICY.read_text()
    configured_budget = f"C3 = {current.model.output_tokens['C3']}"
    assert source.count(configured_budget) == 1
    target.write_text(source.replace(configured_budget, "C3 = 4096", 1))
    monkeypatch.setenv("SOCAI2_INVESTIGATION_POLICY", str(target))
    runtime_policy.active_policy.cache_clear()
    policy = runtime_policy.active_policy()
    assert policy.model.output_tokens["C3"] == 4096
    monkeypatch.setattr(CaseAllocationPolicy, "load", lambda: CaseAllocationPolicy(100, 100, 20, 100))
    handlers = analysis_case_executor.executors(config(target), SimpleNamespace(sessions=None))
    assert set(handlers) == {"alert_triage", "incident_diagnosis", "case_investigation"}
    validate_executors(handlers)
    with pytest.raises(ValueError, match="differs from selected runtime policy"):
        analysis_case_executor.executors(config(), SimpleNamespace(sessions=None))


@pytest.mark.parametrize("name", ["incident_io", "case_io"])
def test_old_nested_contract_is_readable_but_not_executable(current, name):
    profile = getattr(current, name)
    value = profile.config
    if name == "incident_io":
        value.pop("output_validation")
    else:
        value["program_output"]["version"] = "socai2.case-program-output.v1"
    raw = json.dumps(value).encode()
    policy = replace(current, **{name: replace(profile, raw=raw, sha256=hashlib.sha256(raw).hexdigest())})
    assert policy.snapshot()["profiles"][name]["json_text"] == raw.decode()
    with pytest.raises(ValueError, match="execution_profile_not_current:" + name):
        policy.require_execution_profiles()


@pytest.mark.parametrize("missing", ["alert_triage", "incident_diagnosis", "case_investigation"])
def test_partial_dispatcher_registration_is_rejected(missing):
    handler = SimpleNamespace(load=AsyncMock(), execute=AsyncMock())
    handlers = dict.fromkeys({"alert_triage", "incident_diagnosis", "case_investigation"} - {missing}, handler)
    with pytest.raises(ValueError, match="requires current A/I/Case"):
        validate_executors(handlers)
    handler.load.assert_not_awaited()
    handler.execute.assert_not_awaited()


@pytest.mark.parametrize("kind,executor", [("alert_io", AlertBasicExecutor), ("incident_io", IncidentDiagnosisExecutor)])
def test_actual_stage_entry_rejects_missing_contract_before_claim(current, kind, executor, monkeypatch):
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: replace(current, **{kind: None}))
    service = SimpleNamespace(begin=AsyncMock())
    gateway = SimpleNamespace(configure=AsyncMock(), complete=AsyncMock())
    with pytest.raises(StoreError, match="investigation_execution_contract_required"):
        asyncio.run(executor(service, gateway=gateway).execute(uuid4(), uuid4(), uuid4()))
    service.begin.assert_not_awaited()
    gateway.configure.assert_not_awaited()
    gateway.complete.assert_not_awaited()


def test_case_capture_rejects_old_policy_before_database_read(current, monkeypatch):
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: replace(current, case_io=None))
    db = SimpleNamespace(execute=AsyncMock())
    with pytest.raises(StoreError, match="investigation_execution_contract_required"):
        asyncio.run(capture(db, uuid4(), uuid4(), None))
    db.execute.assert_not_awaited()


@pytest.mark.parametrize("profile", [None, {"version": "old", "sha256": "old", "business_sha256": "old"}])
def test_case_and_followup_entries_cannot_fall_back_to_old_frozen_input(current, profile):
    context = SimpleNamespace(case_input_profile=profile)
    store = SimpleNamespace(read_context=AsyncMock(return_value=context))
    @asynccontextmanager
    async def transaction(*args, **kwargs):
        yield store
    service = SimpleNamespace(transaction=transaction)
    gateway = SimpleNamespace(configure=AsyncMock(), complete=AsyncMock())
    tenant, case, run = uuid4(), uuid4(), uuid4()
    calls = [
        BaselineExecutor(service, tenant, gateway=gateway, lake=object()).execute(SimpleNamespace(case_id=case, run_id=run)),
        BaselineDeep(service).input(tenant, case, run, "q", {}, uuid4(), None),
        BaselineReanalysis(service).input(tenant, case, run, context, {}, uuid4(), [], extra_data={"round": "final_delivery"}),
    ]
    for call in calls:
        with pytest.raises(StoreError, match="case_input_profile_changed"):
            asyncio.run(call)
    gateway.configure.assert_not_awaited()
    gateway.complete.assert_not_awaited()


def test_older_policy_snapshots_remain_loadable_without_becoming_execution_defaults():
    policy = runtime_policy.load_policy(POLICY.with_name("investigation-policy.toml"))
    assert policy.snapshot()["toml_text"] and not policy.snapshot()["profiles"]
    with pytest.raises(ValueError, match="execution_profile_required"):
        policy.require_execution_profiles()


def test_incident_context_admission_still_saves_measurement_and_blocks_insufficient_run_budget(current, monkeypatch):
    from datetime import UTC, datetime

    import httpx
    from app.socai2 import incident_diagnosis_executor as implementation
    from app.socai2.baseline_store import digest, encoded
    from app.socai2.token_budget import BackendTokenMeter

    now = datetime.now(UTC)
    tenant, subject, run_id, input_id, stage_id = (uuid4() for _ in range(5))
    source = {"query_receipts_version": "unit"}
    policy = current.model
    full_reservation = 1 + policy.context_tokens + policy.tokenizer["safety_tokens"] + policy.output_tokens["I"]
    limits = current.incident_diagnosis.limits(now, current.identity).model_copy(
        update={"max_tokens": full_reservation - 1})
    run = {"started_at": now, "input_artifact_id": input_id, "limits": limits.model_dump(mode="json")}
    result = Mock()
    result.mappings.return_value.all.return_value = []
    store = SimpleNamespace(
        one=AsyncMock(return_value={"material_state": "complete", "sha256": digest(source), "size_bytes": len(encoded(source))}),
        db=SimpleNamespace(execute=AsyncMock(return_value=result)), now=AsyncMock(return_value=now),
        where=lambda table, *clauses: clauses)

    @asynccontextmanager
    async def transaction(*args, **kwargs):
        yield store

    service = SimpleNamespace(transaction=transaction, begin=AsyncMock(return_value={
        "newly_claimed": True, "run_id": run_id, "input_artifact_id": input_id}))

    def tokenize(request):
        body = json.loads(request.content)
        return httpx.Response(200, json={"count": 1 if "messages" in body else policy.context_tokens,
                                        "max_model_len": policy.context_tokens})

    meter = BackendTokenMeter(policy, transport=httpx.MockTransport(tokenize))
    gateway = SimpleNamespace(model=policy.alias, provider=policy.protocol, schema_profile=policy.schema_profile,
                              configure=AsyncMock(return_value=True), measure=meter.measure, complete=AsyncMock())
    executor = IncidentDiagnosisExecutor(service, gateway=gateway)
    executor.locked = AsyncMock(return_value=(run, source))
    executor.step = AsyncMock(return_value=stage_id)
    executor.save = AsyncMock(return_value=uuid4())
    executor.stop = AsyncMock()
    executor.outcome = AsyncMock(return_value={"state": "failed", "stop_reason": "model_token_budget_insufficient"})
    data = {"members": [], "omissions": {}, "view_limitations": [], "omission_details": [],
            "omission_detail_count": 0, "omission_details_truncated": False}
    prepared = {"boundary": {}, "severity_opinion_version": "unit", "business_verdict_version": "unit"}
    monkeypatch.setattr(implementation.incident_model_boundary, "build", lambda *args, **kwargs: (
        [{"role": "user", "content": "synthetic evidence"}], {}, data, prepared))
    monkeypatch.setattr(implementation.incident_output_adapter, "candidate_schema", lambda value: {"type": "object"})
    outcome = asyncio.run(executor.execute(tenant, subject, uuid4()))
    assert outcome["stop_reason"] == "model_token_budget_insufficient"
    executor.save.assert_awaited_once()
    saved = executor.save.await_args.args[4]
    measured = saved["token_measurement"]
    assert measured["context_fits"] and measured["context_required_tokens"] < policy.context_tokens
    assert measured["context_accounting"] == "chat_template_plus_output_and_safety"
    assert measured["reserved_total_tokens"] == saved["reserved_token_upper_bound"] == full_reservation
    assert measured["body_sha256"] == digest(saved["body"])
    assert not saved["preflight_passed"] and saved["preflight_error"] == "model_token_budget_insufficient"
    assert json.loads(json.dumps(saved))["token_measurement"] == measured
    executor.stop.assert_awaited_once_with(tenant, run_id, "failed", "model_token_budget_insufficient")
    gateway.complete.assert_not_awaited()
