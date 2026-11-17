"""Explicit C3/Deep/C6 and source substitutes for initial-task wiring checks."""
import json

from app.socai2.baseline_evidence_tools import query_sql
from app.socai2.baseline_optional_sources import SourceUnavailable
from app.socai2.baseline_store import F
from jsonschema import Draft202012Validator
from socai2_test_model_view import synthetic_measure
from sqlalchemy import select
from test_socai2_baseline_evidence import SyntheticLake
from test_socai2_case_followup_boundary import final_answer
from test_socai2_case_model_boundary import answer_for


async def empty_query(service, tenant, name, args):
    async with service.transaction(tenant, readonly=True) as store:
        return [], await store.now()


class Lake(SyntheticLake):
    def __init__(self, mode="normal"):
        super().__init__()
        self.mode = mode

    async def query(self, args, query_id, timeout):
        query_sql(args)  # Exercise the actual SQL validator at the frozen limit.
        if self.mode == "query_failure":
            raise SourceUnavailable("controlled_source_unavailable")
        self.count = args["limit"] + 1 if self.mode == "timing" else 1
        return await super().query(args, query_id, timeout)


class Gateway:
    provider, model = "controlled", "controlled-case-initial-no-network"

    def __init__(self, service, tenant, claim, mode, calls, hook=None):
        self.service, self.tenant, self.claim = service, tenant, claim
        self.mode, self.calls, self.hook = mode, calls, hook

    async def configure(self, *_):
        return True

    async def measure(self, body, stage):
        result = await synthetic_measure(body, stage)
        if self.mode == "capacity":
            result.update(context_fits=False, reserved_total_tokens=result["context_tokens"] + 1)
        return result

    async def complete(self, body, timeout):
        assert timeout > 0 and self.mode != "capacity"
        async with self.service.transaction(self.tenant, readonly=True) as store:
            request = (await store.db.execute(select(F.c.content_json).where(*store.where(F,
                F.c.run_id == self.claim.run_id, F.c.kind == "model_request"))
                .order_by(F.c.captured_at.desc()).limit(1))).scalar_one()["payload"]
            context = await store.read_context(self.claim.case_id, self.claim.run_id)
        assert request["body"] == body
        stage = request["case_boundary"].get("stage", "C3")
        if stage == "C3":
            if self.hook:
                await self.hook(self.claim, context)
            answer = answer_for(request, context)
            if self.mode in {"timing", "query_failure"}:
                alias = next(key for key, binding in request["binding_map"].items()
                    if binding["tool_name"] == "process_activity")
                members = [m["alert_id"] for m in answer["members"]]
                answer["followups"] = [
                    {"question_id": context.questions[0].id, "alert_ids": members, "mode": "query",
                     "objective": "Synthetic log query.", "required_evidence": "Process observation.",
                     "source_ids": [], "object_keys": [], "binding_id": alias, "priority": "decision_critical"},
                    {"question_id": context.questions[1].id, "alert_ids": members, "mode": "deep",
                     "objective": "Synthetic focused analysis.", "required_evidence": "Authorization context.",
                     "source_ids": [], "object_keys": [], "binding_id": None, "priority": "decision_critical"}]
        elif stage == "Deep":
            answer = {"action": "answer", "binding_id": None, "reason": "Synthetic focused check completed.",
                "answer": {"state": "unresolved", "text": "Synthetic authorization remains unverified.",
                    "support_ids": [], "counter_ids": [], "alternatives": [], "limitations": ["Synthetic dependency."]}}
        else:
            assert stage == "C6"
            answer = final_answer(request, context, request["followup_boundary"]["program_metadata"]["comparison"])
        Draft202012Validator(body["response_format"]["json_schema"]["schema"]).validate(answer)
        reply = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(answer)}}],
            "usage": {"prompt_tokens": 200, "completion_tokens": 200, "total_tokens": 400}}
        self.calls.append({"run_id": str(self.claim.run_id), "case_id": str(self.claim.case_id),
            "stage": stage, "request": body, "response": reply})
        return reply
