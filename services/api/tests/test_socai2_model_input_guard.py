"""Guard-only execution tests using a local ledger substitute, never a database/provider.

The substitute covers only the SQL operations exercised below. PostgreSQL,
HTTP serving and the 4177 snapshot are deliberately outside these assertions.
"""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from app.models import socai2 as models
from app.services.llm_safety import LLMContractViolation, LLMInputContract
from app.socai2 import alert_basic_executor as alert
from app.socai2 import case_c3_completion_flow as completion
from app.socai2 import incident_diagnosis_executor as incident
from app.socai2 import runtime_policy
from app.socai2.analysis_dispatch_types import ExecutionFailure, classify_failure
from app.socai2.baseline_analysis import budget_reason
from app.socai2.baseline_analysis_model import TenantChatGateway
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_failure import accounted_steps
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.baseline_store import BaselineStore, digest, encoded
from app.socai2.citation_quality import new_review
from app.socai2.model_errors import INPUT_CONTRACT_REJECTED
from app.socai2.model_protocol import DEEPSEEK_BASE, DEEPSEEK_PROTOCOL
from app.socai2.run_records import RunRecordLimits, RunRecordService
from app.socai2.stage_delivery import VERSION, validate_sources
from investigation_http.adapters.run_records import RunRecordBackend
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BindParameter, Null
from sqlalchemy.sql.selectable import Join


class Rows(list):
    def mappings(self):
        return self

    def all(self):
        return self

    def scalar_one(self):
        return max((row.get("seq") or 0 for row in self), default=0)


class Ledger:
    """Small substitute for the existing artifact/step SQL, not transaction testing."""
    save_input_artifact = BaselineStore.save_input_artifact

    def __init__(self, kind, version):
        self.tenant_id, self.db = uuid4(), self
        self.clock = datetime.now(timezone.utc)
        self.run = {"id": uuid4(), "kind": kind, "state": "running", "executor_version": version,
            "tenant_id": self.tenant_id, "input_artifact_id": uuid4(), "requested_by": None,
            "started_at": self.clock, "row_version": 1, "stop_reason": None,
            "alert_id": None, "incident_id": None, "case_id": None,
            "limits": Limits(max_model_calls=8, max_tokens=4096, max_tool_calls=0, max_rows_per_query=0,
                deadline_at=self.clock + timedelta(minutes=5), policy_version="guard-test").model_dump(mode="json")}
        subject = {"alert_basic": "alert_id", "incident_diagnosis": "incident_id"}.get(kind, "case_id")
        self.run[subject] = uuid4()
        self.source = {"query_receipts_version": "guard-test"}
        self.tables = {models.Runs.__tablename__: [self.run]}
        self.put(models.Artifacts.__table__, {"id": self.run["input_artifact_id"], "run_id": self.run["id"],
            "tenant_id": self.tenant_id, "kind": "source_snapshot", "material_state": "complete",
            "content_json": self.source, "sha256": digest(self.source), "size_bytes": len(encoded(self.source)),
            subject: self.run[subject]})

    def put(self, table, values):
        row = {column.name: None for column in table.columns}
        row.update(copy.deepcopy(values))
        self.tables.setdefault(table.name, []).append(row)
        return row

    @staticmethod
    def value(expr, row):
        if isinstance(expr, BindParameter):
            return expr.value
        if isinstance(expr, Null):
            return None
        if isinstance(expr, BinaryExpression) and expr.operator is operators.add:
            return Ledger.value(expr.left, row) + Ledger.value(expr.right, row)
        return row[expr.key]

    def matched(self, statement, rows):
        def matches(row, clause):
            left, right = self.value(clause.left, row), self.value(clause.right, row)
            if clause.operator is operators.eq:
                return left == right
            if clause.operator is operators.in_op:
                return left in right
            raise AssertionError("unexpected test query predicate")
        return [row for row in rows if all(matches(row, c) for c in statement._where_criteria)]

    async def execute(self, statement):
        if statement.is_insert:
            self.put(statement.table, statement.compile().params)
            return Rows()
        if statement.is_update:
            rows = self.matched(statement, self.tables.get(statement.table.name, []))
            for row in rows:
                row.update({getattr(key, "key", key): self.value(value, row)
                            for key, value in statement._values.items()})
            return Rows(rows)
        table = statement.get_final_froms()[0]
        if isinstance(table, Join):
            rows = [dict(row, **{"run_" + key: self.run[key] for key in ("alert_id", "incident_id", "case_id")})
                    for row in self.tables.get(models.Artifacts.__tablename__, [])]
        else:
            rows = self.tables.get(table.name, [])
        return Rows(copy.deepcopy(self.matched(statement, rows)))

    async def one(self, statement):
        return next(iter(await self.execute(statement)), None)

    def where(self, _table, *conditions):
        return conditions

    async def now(self):
        return self.clock

    @asynccontextmanager
    async def transaction(self, _tenant, **_):
        yield self

    async def begin(self, *_args, **_kwargs):
        return {"run_id": self.run["id"], "input_artifact_id": self.run["input_artifact_id"],
                "newly_claimed": self.run["state"] == "running"}

    async def locked(self, *_):
        return self.run, None, self.source


@pytest.fixture
def setup(monkeypatch):
    policy = SimpleNamespace(single_model_timeout_seconds=60,
        model=SimpleNamespace(output_tokens={stage: 32 for stage in ("A", "I", "C3", "Deep", "C6")},
                              final_reserved_calls=0, incident_max_structure_whitespace=None))
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: policy)
    monkeypatch.setattr(alert, "active_policy", lambda: policy)
    monkeypatch.setattr(incident, "active_policy", lambda: policy)
    profile = SimpleNamespace(version="guard-test")
    for module in (alert, incident):
        monkeypatch.setattr(module, "execution_policy", lambda *_: SimpleNamespace(alert_io=profile, incident_io=profile))
    post = AsyncMock(side_effect=AssertionError("provider POST forbidden"))
    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    guard = AsyncMock()

    def refuse(_messages):
        guard.calls += 1
        raise LLMContractViolation("guard-test-reason", evidence="guard-test-private-evidence")

    guard.calls = 0
    monkeypatch.setattr(LLMInputContract, "validate", refuse)
    return policy, post, guard


def gateway(protocol="chat_completions"):
    value = TenantChatGateway()
    value.provider, value.schema_profile, value.model = protocol, "standard", "deepseek-flash"
    value.config = SimpleNamespace(base_url=DEEPSEEK_BASE, model=value.model, api_key="")
    value.configure = AsyncMock(return_value=True)

    async def measure(body, _stage):
        return {"body_sha256": digest(body), "reserved_total_tokens": 64, "context_fits": True}

    value.measure = measure
    return value


FORMAT = {"type": "json_schema", "json_schema": {"name": "guard_test", "strict": True,
    "schema": {"type": "object", "properties": {}, "additionalProperties": False, "required": []}}}


@pytest.mark.parametrize("protocol", ["chat_completions", DEEPSEEK_PROTOCOL])
def test_gateway_refusal_is_known_unsent_without_evidence(setup, protocol, caplog):
    from app.socai2.model_protocol import prepare_request
    value = gateway(protocol)
    body = prepare_request(value, {"model": value.model, "messages": [{"role": "user", "content": "{}"}],
                                  "max_tokens": 32, "temperature": 0, "response_format": FORMAT})
    with pytest.raises(ExecutionFailure) as rejected:
        asyncio.run(value.complete(body, 30))
    exc = rejected.value
    assert exc.not_executed and not exc.temporary and exc.code == INPUT_CONTRACT_REJECTED
    assert exc.__suppress_context__ and "guard-test-private-evidence" not in str(exc)
    outcome = classify_failure(exc, stage="execute")
    assert outcome.outcome == "failed" and not outcome.retryable
    setup[1].assert_not_awaited()
    assert "guard-test-private-evidence" not in caplog.text


def assert_receipts(ledger):
    rows = ledger.tables[models.Artifacts.__tablename__]
    receipts = [row for row in rows if row["schema_version"] == VERSION]
    assert receipts
    for row in receipts:
        body = row["content_json"]
        originals = {str(a["id"]): a["content_json"] for a in rows}
        saved = validate_sources(body, originals)
        assert saved.execution.request_dispatched is False
        assert saved.execution.local_state == "ended" and not saved.execution.retry_allowed
        assert saved.parse.state == "no_response" and saved.delivery.state == "none"
        assert not saved.retained_units and not saved.use.conclusion_available
        assert row["sha256"] == digest(body) and row["size_bytes"] == len(encoded(body))
    assert "guard-test-private-evidence" not in str(rows)
    assert "guard-test-reason" not in str(rows)
    assert not ledger.tables.get(models.Results.__tablename__)
    return receipts


@pytest.mark.parametrize("stage", ["A", "I"])
def test_actual_ai_executor_saves_failed_identity_and_reads_existing_adapter(setup, monkeypatch, stage, caplog):
    module, cls, kind = (alert, alert.AlertBasicExecutor, "alert_basic") if stage == "A" else (
        incident, incident.IncidentDiagnosisExecutor, "incident_diagnosis")
    ledger = Ledger(kind, module.VERSION)
    data = {"members": [], "omissions": [], "view_limitations": [], "view_coverage": {},
        "omission_details": [], "omission_detail_count": 0, "omission_details_truncated": False}
    prepared = {"boundary": {}, "severity_opinion_version": "guard-test", "business_verdict_version": "guard-test"}
    build = lambda *_args, **_kwargs: ([{"role": "user", "content": "{}"}], {}, data, prepared)
    if stage == "A":
        monkeypatch.setattr(module, "build", build)
        monkeypatch.setattr(module, "schema", lambda *_: FORMAT)
    else:
        monkeypatch.setattr(module.incident_model_boundary, "build", build)
        monkeypatch.setattr(module.incident_output_adapter, "candidate_schema", lambda *_: FORMAT["json_schema"]["schema"])
    executor = cls(ledger, gateway=gateway())
    if stage == "A":
        monkeypatch.setattr(executor, "background", AsyncMock(return_value={}))

    async def check():
        result = await executor.execute(ledger.tenant_id, uuid4(), uuid4())
        assert result["state"] == "failed" and result["stop_reason"] == INPUT_CONTRACT_REJECTED
        receipts = assert_receipts(ledger)
        steps = ledger.tables[models.RunSteps.__tablename__]
        parent = next(row for row in steps if row["kind"] == "stage")
        model = next(row for row in steps if row["kind"] == "model")
        assert model["parent_step_id"] == parent["id"] and model["state"] == "failed"
        assert model["ended_at"] and parent["ended_at"] and ledger.run["ended_at"]
        assert model["usage"]["total_tokens"] is None
        assert model["error"]["request_dispatched"] is False
        assert receipts[0]["step_id"] == parent["id"] and parent["output_artifact_id"] == receipts[0]["id"]
        original_ids = {entry["artifact_id"] for entry in receipts[0]["content_json"]["originals"]}
        assert original_ids == {str(model["input_artifact_id"]), str(model["output_artifact_id"])}
        reader = RunRecordService(None, limits=RunRecordLimits(10, 20))
        reader.transaction = ledger.transaction
        backend = RunRecordBackend.__new__(RunRecordBackend)
        backend.reader = reader
        read = await backend.step(ledger.tenant_id, ledger.run["id"], model["id"])
        assert read["error"]["request_dispatched"] is False
        assert {r["artifact_id"] for r in read["artifact_refs"]} == {model["input_artifact_id"], model["output_artifact_id"]}
        assert all(str(ledger.run["id"]) in r["content_url"] for r in read["artifact_refs"])
        count = len(ledger.tables[models.Artifacts.__tablename__])
        await executor.execute(ledger.tenant_id, uuid4(), uuid4())
        assert len(ledger.tables[models.Artifacts.__tablename__]) == count

    asyncio.run(check())
    setup[1].assert_not_awaited()
    assert setup[2].calls == 1
    assert "guard-test-private-evidence" not in caplog.text


@pytest.mark.parametrize("stage", ["C3", "C4.deep", "C6"])
def test_actual_case_call_keeps_unsent_receipt_and_releases_token_reservation(setup, monkeypatch, stage, caplog):
    ledger = Ledger("case", "guard-test-case")
    owner = ledger.put(models.RunSteps.__table__, {"id": uuid4(), "run_id": ledger.run["id"], "kind": "stage",
        "stage_code": stage, "state": "running", "seq": 1, "question_id": None})
    caller = ModelSteps(ledger, "guard-test-case")
    monkeypatch.setattr(ModelSteps, "locked", AsyncMock(return_value=ledger.run))
    prepared = {"ready": True, "messages": [{"role": "user", "content": "{}"}], "source_map": {},
        "binding_map": {}, "input_artifact_ids": [str(ledger.run["input_artifact_id"])], "omissions": []}

    async def check():
        result = await caller.call(ledger.tenant_id, ledger.run["case_id"], ledger.run["id"], owner["id"], stage,
                                  prepared, gateway(), lambda _: pytest.fail("no response to parse"), output_format=FORMAT)
        assert result[0] is None and result[1] == INPUT_CONTRACT_REJECTED
        assert ledger.run["state"] == "running"
        assert_receipts(ledger)
        steps = ledger.tables[models.RunSteps.__tablename__]
        model = next(row for row in steps if row["kind"] == "model")
        assert model["parent_step_id"] == owner["id"] and model["state"] == "failed" and model["ended_at"]
        assert model["usage"]["total_tokens"] is None
        accounted = await accounted_steps(ledger, ledger.run["id"], steps)
        entry = next(row for row in accounted if row["id"] == model["id"])
        assert entry["not_executed"] and entry["reserved_tokens"] == 64
        limits = Limits.model_validate(ledger.run["limits"]).model_copy(update={"max_tokens": 64})
        assert budget_reason(accounted, limits, 1, ledger.clock, measurement={"context_fits": True, "reserved_total_tokens": 64}) is None
        assert "not_executed" not in model and model["usage"]["total_tokens"] is None
        if stage == "C3":
            policy = json.loads((Path(__file__).parents[1] / "app/socai2/case-input-v1.json").read_text())["c3_completion"]
            policy["system"] = "guard-test"
            prepared.update(citation_review=new_review(), input_view_id=str(ledger.run["input_artifact_id"]),
                            case_boundary={"c3_completion": policy})
            # No reply reached the receiver. Its empty-domain view is not the
            # behavior under test; the real completion controller must not call.
            monkeypatch.setattr(completion.units, "receive", lambda *_: {"analysis": {}, "closed_sections": [],
                "delivery": {"state": "none", "reasons": [INPUT_CONTRACT_REJECTED]},
                "parse": {"state": "no_response", "truncated": False, "reasons": []},
                "retained_units": [], "missing_units": [], "invalid_units": [], "quality": new_review(),
                "use": {"material_paths": [], "dispatch_paths": [], "conclusion_available": False,
                        "adoption_eligible": False, "comparison_eligible": False, "reasons": []}})
            await completion.complete_sections(ledger, ledger.tenant_id, ledger.run["case_id"], ledger.run["id"],
                owner["id"], prepared, SimpleNamespace(), {}, FORMAT, gateway(), result, schema=caller.schema)
            assert prepared["section_completion_result"]["state"] == "skipped"
            assert prepared["section_completion_result"]["attempts"] == 0
            assert len([row for row in ledger.tables[models.RunSteps.__tablename__] if row["kind"] == "model"]) == 1
            assert_receipts(ledger)

    asyncio.run(check())
    setup[1].assert_not_awaited()
    assert "guard-test-private-evidence" not in caplog.text


@pytest.mark.parametrize("flag,raw,expected", [(False, None, False), (True, None, True),
    (None, None, None), (None, {}, True)])
def test_c3_dispatch_uses_explicit_fact_or_verified_response(flag, raw, expected):
    model = {"error": {"request_dispatched": flag}}
    originals = {"response": {"direction": "response", "payload": {"raw": raw}}}
    assert completion.request_dispatched(model, originals) is expected
    assert completion.request_dispatched({"error": None}, {}) is None
    assert completion.request_dispatched(None, {}) is False


@pytest.mark.parametrize("first,second,expected", [(False, False, False), (False, None, None),
    (None, None, None), (True, None, True), (None, True, True)])
def test_c3_dispatch_aggregation_preserves_unknown(first, second, expected):
    assert completion.combined_dispatch(first, second) is expected


@pytest.mark.parametrize("exception", [RuntimeError, ValueError, TimeoutError, httpx.ReadTimeout])
def test_gateway_does_not_convert_adjacent_failures_to_guard_rejection(setup, monkeypatch, exception):
    from app.services import llm_safety
    from app.socai2.model_errors import ModelCallError
    monkeypatch.setattr(LLMInputContract, "validate", lambda messages: messages)
    monkeypatch.setattr(llm_safety.httpx.AsyncClient, "post", AsyncMock(side_effect=exception("test-only")))
    value = gateway()
    body = {"model": value.model, "messages": [], "max_tokens": 32, "response_format": FORMAT}
    with pytest.raises(ModelCallError if issubclass(exception, httpx.HTTPError) else exception) as failed:
        asyncio.run(value.complete(body, 30))
    assert not isinstance(failed.value, ExecutionFailure)
    if exception in {TimeoutError, httpx.ReadTimeout}:
        assert classify_failure(failed.value, stage="execute").outcome == "unknown"
