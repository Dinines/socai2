"""Offline reconstruction of the failed synthetic C6 input; no database/model."""
import argparse
import asyncio
import copy
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from app.socai2 import baseline_delivery_contract as contract
from app.socai2.baseline_context import Context
from app.socai2.baseline_evidence import BaselineEvidence
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_reanalysis import BaselineReanalysis
from app.socai2.baseline_reasoning import fit_final_request
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_input_view import items
from app.socai2.model_protocol import DEEPSEEK_PROTOCOL, prepare_request
from app.socai2.structured_output import response_format

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/operations/evidence/socai2-followup-fix-20261105"


async def rebuild():
    fixture = json.loads((DIRECTORY / "pg-wire-frozen-synthetic.json").read_text("utf-8"))
    rows = [r for r in fixture["artifacts"] if isinstance(r["content_json"], dict)]
    assert all(digest(r["content_json"]) == r["sha256"] for r in rows)
    by_id = {r["id"]: r for r in rows}
    context = Context.model_validate(next(r["content_json"] for r in rows if r["schema_version"] == "socai2.baseline-context.v1"))
    view = next(r for r in rows if r["schema_version"] == "socai2.baseline-model-view.v4")
    dispatch = next(r["content_json"] for r in rows if r["content_json"].get("type") == "followup_dispatch")
    initial_id = dispatch["initial_analysis_artifact_id"]
    previous = by_id[initial_id]["content_json"]
    current = [r for r in rows if r["content_json"].get("type") == "model_view"
        and r["content_json"]["question_id"] == context.questions[0].id][-1]
    bases = sorted([r for r in rows if r["content_json"].get("type") in {
        "materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda r: r["id"])
    tools = [r for r in rows if r["kind"] == "tool_response"]
    report = next(r["content_json"] for r in rows if r["content_json"].get("type") == "delivery_report")

    class Store:
        def __init__(self):
            self.db = self

        def where(self, *_):
            return []

        async def execute(self, _):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: tools))

        async def prepare_model_view(self, *_):
            return {"artifact_id": view["id"], **view["content_json"]}

    @asynccontextmanager
    async def transaction(*_):
        yield Store()

    async def model_view(*_):
        return {"artifact_id": current["id"], **current["content_json"]}

    async def read_artifact(_self, _store, _run_id, identity):
        return by_id[str(identity)]["content_json"]

    meta, planned = delivery_followups(dispatch, previous)
    with patch.object(BaselineEvidence, "model_view", model_view), patch.object(BaselineReanalysis, "read_artifact", read_artifact):
        prepared = await BaselineReanalysis(SimpleNamespace(transaction=transaction)).input(
            UUID(fixture["tenant_id"]), UUID(fixture["case_id"]), UUID(fixture["run_id"]), context,
            previous, initial_id, bases, instruction=contract.PROMPT,
            extra_data={"round": "final_delivery", "comparison": report["comparison"], "followup_execution": meta},
            lead_candidates=planned, executed_plan_id=initial_id)
    assert prepared["ready"], prepared["reason"]
    body = prepare_request(SimpleNamespace(provider=DEEPSEEK_PROTOCOL), {"model": "deepseek-flash",
        "messages": prepared["messages"], "max_tokens": 3000, "temperature": 0,
        "response_format": response_format(contract.Delivery, prepared["source_map"], members=context.alerts,
            questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
    before = copy.deepcopy(body)
    byte_limit = fixture["limits"]["max_tokens"] - 3000 - 3000 - 256
    fit_final_request(body, prepared, byte_limit)
    visible = items(json.loads(body["input"][1]["content"]))
    return {"scope": "offline exact-code rebuild from frozen synthetic PG artifacts; no model/DB writes",
        "run_id": fixture["run_id"], "byte_limit": byte_limit, "before_bytes": len(encoded(before)),
        "after_bytes": len(encoded(body)), "fits": len(encoded(body)) <= byte_limit,
        "schema_bytes": len(encoded(body["text"])), "messages_bytes": len(encoded(body["input"])),
        "system_bytes": len(body["input"][0]["content"].encode()), "user_bytes": len(body["input"][1]["content"].encode()),
        "visible_fields": [{"id": i["id"], "required": prepared["source_map"][i["id"]]["required"],
            "bytes": len(encoded(i)), "value": i["value"]} for i in visible],
        "prepared": prepared, "body": body}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, choices=["wire-before.json", "wire-after.json", "wire-after-v2.json", "wire-after-v3.json"])
    args = parser.parse_args()
    out = DIRECTORY / args.output
    if out.exists():
        raise RuntimeError("fixed replay already exists")
    result = asyncio.run(rebuild())
    with out.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"prepared", "body", "visible_fields"}}))
