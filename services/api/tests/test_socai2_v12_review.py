"""Actual call/validation/publication functions with a labelled in-memory ledger."""
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.socai2 import baseline_analysis_contract as contract
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.analysis_review import Review, partial_analysis
from app.socai2.baseline_context import Context
from app.socai2.baseline_delivery_projection import make_publication
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.runtime_policy import active_policy
from test_socai2_followup_scope import frozen


def packet():
    stored, answer = frozen()
    context = Context.model_validate(stored["context"])
    return stored, answer, context


def test_invalid_finding_drops_dependent_domain_but_preserves_independent_members_and_followups():
    stored, raw, context = packet()
    raw["findings"][0]["support_ids"] = ["not-in-input"]
    before = copy.deepcopy(raw)
    value, diagnostics = partial_analysis(json.dumps(raw), stored["source_map"], context, stored["coverage"])
    assert raw == before
    assert raw["findings"][0]["id"] not in {f.id for f in value.findings}
    assert value.members[1].model_dump(mode="json") == raw["members"][1]
    assert value.followups[0].model_dump(mode="json") == raw["followups"][0]
    assert all(raw["findings"][0]["id"] not in d.finding_ids for d in value.domains)
    assert any(d["path"] == ["findings", 0] for d in diagnostics)
    contract.parse(value.model_dump_json(), stored["source_map"], context, stored["coverage"])


@pytest.mark.parametrize("bad", ['{"summary":', '{"members":[],"members":[]}', '{"summary":NaN}'])
def test_unparseable_or_ambiguous_answers_are_not_salvaged(bad):
    stored, _, context = packet()
    with pytest.raises(contract.AnalysisRejected):
        partial_analysis(bad, stored["source_map"], context, stored["coverage"])


def final_answer(raw):
    return {"analysis": raw, "conclusion": {"text": "unsupported synthetic malicious conclusion", "state": "supported",
        "alert_ids": [m["alert_id"] for m in raw["members"]], "support_ids": ["not-in-input"], "limitations": []},
        "closing_note": "synthetic unsupported whole-case claim", "comparison": {"kind": "initial", "summary": None, "support_ids": []},
        "impact": {"summary": "unknown", "alert_ids": [], "support_ids": [], "supported_changes": [],
            "cannot_generalize": ["synthetic limitation"], "next_steps": []}, "recommendations": []}


def test_final_invalid_conclusion_preserves_analysis_and_cannot_replace_case_judgment():
    stored, raw, context = packet()
    review = Review("C6", stored["source_map"], context, stored["coverage"])
    assert review.partial(json.dumps(final_answer(raw))) is None
    prepared = {"source_map": stored["source_map"], "validation_review": review.details}
    members = {UUID(aid): {"read_state": "read", "analysis_state": "analyzed"} for aid in context.alerts}
    pub, _ = make_publication(None, context, members, prepared, {"state": "initial"},
        {"delivery_state": "complete", "graph_artifact_id": str(uuid4())}, uuid4(), "delivery_source_not_visible_or_duplicate")
    assert pub.terminal_state == "completed" and pub.delivery_state == "partial"
    assert pub.validation_state == "rejected" and pub.conclusion_state == "unavailable" and pub.conclusion is None
    assert not any(m.conclusion_covered for m in pub.members)
    assert len(pub.findings) == len(raw["findings"]) and len(pub.questions) == 6
    assert "malicious" not in pub.model_dump_json()


class Ledger:
    def __init__(self, now):
        self.db, self.time = self, now
        self.steps, self.artifacts = [], []
        self.owner = {"id": uuid4(), "stage_code": "C3", "question_id": None}
    def where(self, _table, *conditions):
        return conditions
    async def now(self):
        return self.time
    async def one(self, _):
        return self.owner
    async def execute(self, query):
        if query.is_select:
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: copy.deepcopy(self.steps)))
        params = query.compile().params
        if query.is_insert:
            self.steps.append({**params, "usage": None})
        elif query.is_update:
            target = next(s for s in self.steps if s["id"] == params["id_1"])
            target.update({k: v for k, v in params.items() if k != "id_1"})
        return SimpleNamespace()


def execute(replies, *, calls=6, stage="C3", fail_transport=False):
    stored, _valid, context = packet()
    ledger = Ledger(context.captured_at)
    ledger.owner["stage_code"] = stage
    limits = active_policy().case.limits(context.captured_at, "synthetic-unit-ledger").model_copy(update={"max_model_calls": calls})
    run = {"id": uuid4(), "case_id": context.case_id, "state": "running", "requested_by": None,
        "executor_version": "synthetic-unit-ledger", "limits": limits.model_dump(mode="json")}
    @asynccontextmanager
    async def transaction(_):
        yield ledger
    class Calls(ModelSteps):
        async def locked(self, *_):
            return run
        async def idle(self, *_):
            return None
        async def seq(self, *_):
            return len(ledger.steps) + 1
        async def save(self, _store, _run, _step, payload, kind, refs=()):
            identity = uuid4()
            ledger.artifacts.append({"id": identity, "kind": kind, "payload": copy.deepcopy(payload), "refs": refs})
            return identity
    class Gateway:
        model, provider, schema_profile = "synthetic-no-network", "chat_completions", "standard"
        count = 0
        async def configure(self, *_):
            return True
        async def measure(self, body, meter_stage):
            assert meter_stage == stage
            return {"method": "explicit_test_substitute", "context_fits": True,
                "reserved_total_tokens": body["max_tokens"] + 2000}
        async def complete(self, body, timeout):
            self.count += 1
            if fail_transport:
                raise TimeoutError("synthetic timeout after dispatch")
            raw = replies[min(self.count - 1, len(replies) - 1)]
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(raw)}}],
                "usage": {"prompt_tokens": 500, "completion_tokens": 500, "total_tokens": 1000}}
    gateway = Gateway()
    review = Review(stage, stored["source_map"], context, stored["coverage"])
    prepared = {"ready": True, "messages": stored["messages"], "source_map": stored["source_map"],
        "input_artifact_ids": [str(uuid4())], "omissions": []}
    parser = (lambda text: contract.parse(text, stored["source_map"], context, stored["coverage"])) if stage == "C3" else (
        lambda text: delivery.parse(text, stored["source_map"], context, stored["coverage"], {"state": "initial", "result_id": None}))
    method = Calls(SimpleNamespace(transaction=transaction), "synthetic-test-schema")
    result = asyncio.run(method.call(uuid4(), run["case_id"], run["id"], ledger.owner["id"], stage,
        prepared, gateway, parser, output_format=stored["response_format"], review=review))
    return result, prepared, ledger, gateway


def test_empty_reference_feedback_corrects_once_and_saves_both_answers():
    _, valid, _ = packet()
    invalid = copy.deepcopy(valid)
    invalid["questions"][0].update(state="answered", evidence_ids=[])
    result, prepared, ledger, gateway = execute([invalid, valid])
    assert gateway.count == 2 and result[0].model_dump(mode="json") == valid
    requests = [a["payload"]["payload"] for a in ledger.artifacts if a["kind"] == "model_request"]
    responses = [a["payload"]["payload"] for a in ledger.artifacts if a["kind"] == "model_response"]
    feedback = requests[1]["correction"]
    assert feedback["attempt"] == 1 and feedback["errors"][0]["path"] == ["questions", 0, "evidence_ids"]
    assert {s["id"] for s in feedback["allowed_sources"]} == set(requests[0]["source_map"])
    assert json.loads(responses[0]["raw"]["choices"][0]["message"]["content"]) == invalid
    assert prepared["correction_result"]["dispatched"] and len(ledger.steps) == 2


@pytest.mark.parametrize("calls,expected_calls", [(6, 2), (1, 1)])
def test_repeated_empty_reference_or_no_budget_preserves_valid_units_without_more_calls(calls, expected_calls):
    _, invalid, _ = packet()
    invalid["questions"][0].update(state="answered", evidence_ids=[])
    result, prepared, ledger, gateway = execute([invalid], calls=calls)
    assert gateway.count == expected_calls and len(ledger.steps) == expected_calls
    assert result[0].questions[0].state == "unresolved"
    assert result[0].findings and prepared["validation_review"]["state"] == "partial"
    if calls == 1:
        assert prepared["correction_result"]["reason"] == "model_call_budget_exhausted"


def test_transport_timeout_is_not_a_correction_request():
    _, valid, _ = packet()
    with pytest.raises(TimeoutError):
        execute([valid], fail_transport=True)


@pytest.mark.parametrize("wrong_type", [None, 5, "invalid", {}])
def test_complete_bad_shape_is_saved_without_retry_or_unknown(wrong_type):
    _, raw, _ = packet()
    raw["questions"] = wrong_type
    result, _, ledger, gateway = execute([raw])
    assert result[0] is None and result[1] == "analysis_shape_invalid" and gateway.count == 1
    saved = next(a["payload"] for a in ledger.artifacts if a["kind"] == "model_response")
    assert json.loads(saved["payload"]["raw"]["choices"][0]["message"]["content"]) == raw
    assert ledger.steps[0]["state"] == "failed"


@pytest.mark.parametrize("bad_state", [[], {}])
def test_bad_state_type_cannot_lose_received_answer(bad_state):
    _, raw, _ = packet()
    raw["questions"][0]["state"] = bad_state
    result, _, ledger, gateway = execute([raw])
    assert result[1] == "analysis_shape_invalid" and gateway.count == 1
    assert len([a for a in ledger.artifacts if a["kind"] == "model_response"]) == 1


def test_malformed_correction_keeps_original_response_as_retained_analysis_source():
    _, first, _ = packet()
    first["questions"][0].update(state="answered", evidence_ids=[])
    second = {**copy.deepcopy(first), "questions": None}
    result, prepared, ledger, gateway = execute([first, second])
    responses = [a for a in ledger.artifacts if a["kind"] == "model_response"]
    assert gateway.count == 2 and result[0] is not None
    assert result[3] == responses[0]["id"] and result[3] != responses[1]["id"]
    assert prepared["correction_result"]["correction_response_artifact_id"] == str(responses[1]["id"])
