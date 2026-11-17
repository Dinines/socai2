"""Replay saved replies through the call path; no model, database or network.

The gateway, token counter and storage are explicit substitutes. Original replies
are never repaired. This checks wiring, not model quality or live persistence.
"""
import asyncio
import copy
import hashlib
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
config = json.loads((HERE / "config.json").read_text())
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT / "services/api/tests"), str(ROOT)]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import case_followup_output, case_output_adapter
from app.socai2.baseline_context import Context
from app.socai2.baseline_delivery_compat import normalize
from app.socai2.baseline_delivery_projection import make_publication
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.baseline_reasoning import ModelSteps
from app.socai2.baseline_store import digest
from app.socai2.runtime_policy import active_policy
from test_socai2_v12_review import Ledger


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / name
    with path.open("x") as file:
        file.write(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


flow, previews = ROOT / config["flow"], ROOT / config["previews"]
old_hashes = {str(p.relative_to(ROOT)): sha(p) for folder in (flow, previews)
              for p in folder.rglob("*") if p.is_file()}
db = read(ROOT / config["snapshot"])
artifacts = [a for a in db["artifacts"] if a["run_id"] == config["run_id"]]
base = next(a["content_json"] for a in artifacts if a["schema_version"] == "socai2.case-model-input.v1")
frozen = copy.deepcopy(next(a["content_json"] for a in artifacts
                          if a["schema_version"] == "socai2.baseline-context.v1"))
context = Context.model_validate(frozen)
comparison = {"state": "initial", "result_id": None}


async def replay(stage, numbers):
    body = read(flow / f"Case/calls/call-{numbers[0]}-intent.json")["body"]
    request = next(a["content_json"] for a in artifacts if a["kind"] == "model_request"
                   and a["content_json"]["payload"]["body"] == body)
    replies = [read(flow / f"Case/calls/call-{n}-receipt.json")["raw"] for n in numbers]
    prepared = copy.deepcopy({**(base if stage == "C3" else {}), **request["payload"],
                              "ready": True, "messages": body["messages"], "coverage": base["coverage"]})
    if stage == "C6":
        for aid, coverage in prepared["coverage"].items():
            coverage["included"] = sum(aid in row["alert_ids"] for row in prepared["followup_boundary"]["records"])
    review = (case_output_adapter.CaseReview(prepared, context, {}) if stage == "C3" else
              case_followup_output.FinalReview(prepared, context, comparison))

    def parse(content):
        if stage == "C3":
            return case_output_adapter.parse(content, prepared, context, {})
        return case_followup_output.parse_final(content, prepared, context, comparison)

    ledger = Ledger(context.captured_at)
    ledger.owner["stage_code"] = stage
    limits = active_policy().case.limits(context.captured_at, "offline-correction-wiring")
    run = {"id": uuid4(), "case_id": context.case_id, "requested_by": None, "state": "running",
           "executor_version": "offline-correction-wiring", "limits": limits.model_dump(mode="json")}

    @asynccontextmanager
    async def transaction(_tenant):
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
        provider, model = request["provider"], body["model"]
        schema_profile = request["schema_profile"]

        def __init__(self):
            self.requests = []

        async def configure(self, *_):
            return True

        async def measure(self, wire, meter_stage):
            assert meter_stage == stage
            # A deterministic substitute above recorded usage; not a tokenizer
            # measurement of the changed request or a claim about new usage.
            reserved = max(reply["usage"]["total_tokens"] for reply in replies) + wire["max_tokens"]
            return {"method": "explicit_offline_substitute_not_backend_measurement", "body_sha256": digest(wire),
                    "reserved_total_tokens": reserved, "context_fits": reserved <= active_policy().model.context_tokens}

        async def complete(self, wire, timeout):
            assert timeout > 0 and len(self.requests) < len(replies), "unexpected_additional_dispatch"
            self.requests.append(copy.deepcopy(wire))
            return copy.deepcopy(replies[len(self.requests) - 1])

    gateway = Gateway()
    calls = Calls(SimpleNamespace(transaction=transaction), "offline-correction-wiring.v1")
    output_format = (case_output_adapter.output_format(prepared, context, {}) if stage == "C3" else
                     case_followup_output.final_format(prepared, context, comparison))
    result = await calls.call(uuid4(), context.case_id, run["id"], ledger.owner["id"], stage,
        prepared, gateway, parse, output_format=output_format, review=review,
        wire_transform=compact_execution_wire if stage == "C3" else None,
        response_adapter=normalize if stage == "C6" else None)
    assert len(gateway.requests) == 2
    assert gateway.requests[0] == body
    assert gateway.requests[1] == read(previews / f"{stage}-correction-request-preview.json")
    responses = [a for a in ledger.artifacts if a["kind"] == "model_response"]
    requests = [a for a in ledger.artifacts if a["kind"] == "model_request"]
    assert len(responses) == len(requests) == len(ledger.steps) == 2
    assert [a["payload"]["payload"]["raw"] for a in responses] == replies
    expected = "source_member_mismatch" if stage == "C3" else "delivery_source_not_visible_or_duplicate"
    assert all(a["payload"]["payload"]["validation_error"] == expected for a in responses)
    feedback = requests[1]["payload"]["payload"]["correction"]
    assert feedback["original_response_artifact_id"] == str(responses[0]["id"])
    assert str(responses[0]["id"]) in requests[1]["payload"]["payload"]["input_artifact_ids"]
    assert prepared["correction_result"]["correction_response_artifact_id"] == str(responses[1]["id"])
    assert result[3] == responses[1]["id"] and result[1] == expected
    assert prepared["validation_review"]["state"] == "partial"
    assert (result[0] is not None) == (stage == "C3")
    trace = {"stage": stage, "source_calls": numbers, "gateway_substitute_dispatches": 2,
             "initial_request_unchanged": True, "correction_request_equals_preview": True,
             "original_answers_preserved": True, "correction_result": prepared["correction_result"],
             "responses": [{"id": a["id"], "source_call": n, "raw_sha256": digest(reply),
                            "validation_error": a["payload"]["payload"]["validation_error"],
                            "step_state": step["state"]}
                           for a, n, reply, step in zip(responses, numbers, replies, ledger.steps)],
             "validation_review": prepared["validation_review"],
             "returned_analysis": result[0].model_dump(mode="json") if result[0] else None}
    if stage == "C6":
        graph = next(a["content_json"] for a in artifacts if (a["content_json"] or {}).get("type") == "graph_snapshot")
        members = {UUID(row["alert_id"]): row for row in db["run_members"] if row["run_id"] == config["run_id"]}
        publication, _ = make_publication(result[0], context, members, prepared, comparison, graph, uuid4(), result[1])
        assert publication.validation_state == "rejected" and publication.conclusion is None
        assert publication.conclusion_state == "unavailable" and publication.delivery_state == "partial"
        assert not publication.recommendations and not any(m.conclusion_covered for m in publication.members)
        trace["publication_preview_not_database_write"] = publication.model_dump(mode="json")
    save(f"{stage}-trace.json", trace)
    save(f"{stage}-correction-request.json", gateway.requests[1])
    return {"stage": stage, "original_calls": numbers, "gateway_substitute_dispatches": 2,
            "feedback_characters": len(gateway.requests[1]["messages"][-1]["content"]),
            "original_answers_preserved": True, "original_validation_errors_preserved": True,
            "correction_request_matches_preview": True, "partial_analysis_retained": True,
            "final_conclusion": "not_a_final_stage" if stage == "C3" else "rejected_null_not_eligible"}


async def main():
    outcomes = [await replay("C3", [1, 2]), await replay("C6", [5, 6])]
    assert all(sha(ROOT / name) == value for name, value in old_hashes.items())
    tracked = [Path(__file__), HERE / "config.json", ROOT / config["policy"],
               ROOT / "services/api/tests/test_socai2_v12_review.py"]
    tracked += [ROOT / "services/api/app/socai2" / name for name in (
        "baseline_reasoning.py", "case_output_adapter.py", "case_followup_output.py", "case_citation_feedback.py",
        "analysis_review.py", "baseline_delivery.py", "baseline_delivery_projection.py", "baseline_store.py")]
    save("summary.json", {"kind": "offline_saved_reply_call_path_replay", "status": "passed",
         "real_model_calls": 0, "network_calls": 0, "database_calls": 0, "new_run_created": False,
         "old_profile_and_input_unchanged": True, "original_files_unchanged": True, "old_file_hashes": old_hashes,
         "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in tracked}, "outcomes": outcomes,
         "limits": ["memory_storage_and_token_count_are_substitutes", "saved_usage_is_not_new_usage",
                    "no_real_budget_or_model_correction_effect_verified", "no_database_adoption_executed"]})
    print(json.dumps(outcomes, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
