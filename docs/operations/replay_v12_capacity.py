"""Rebuild complete C3/C6 requests from an immutable export; no inference or DB writes."""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from app.socai2 import baseline_analysis as c3
from app.socai2 import baseline_delivery_contract as c6
from app.socai2 import baseline_enrichment as enrichment
from app.socai2 import baseline_model_view as view
from app.socai2.baseline_context import Context
from app.socai2.baseline_dispatch import offered_bindings
from app.socai2.baseline_evidence import BaselineEvidence
from app.socai2.baseline_evidence_tools import catalog
from app.socai2.baseline_execution_schema import (
    compact_execution_wire,
    execution_format,
)
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_reanalysis import BaselineReanalysis
from app.socai2.baseline_store import digest
from app.socai2.model_input_view import frozen_items
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy
from app.socai2.structured_output import response_format


async def rebuild(snapshot, run_id):
    data = json.loads(Path(snapshot).read_text())
    rows = [a for a in data["artifacts"] if a["run_id"] == run_id and isinstance(a["content_json"], dict)]
    assert all(digest(a["content_json"]) == a["sha256"] for a in rows)
    by_id = {a["id"]: a for a in rows}
    run = next(r for r in data["runs"] if r["id"] == run_id)
    original = next(r for r in rows if r["schema_version"] == view.SCHEMA)
    frozen = next(r for r in rows if r["schema_version"] == "socai2.baseline-context.v1")
    context = Context.model_validate(frozen["content_json"])
    summary = next(r["content_json"] for r in rows if r["schema_version"] == enrichment.SCHEMA and "sources" in r["content_json"])
    source_states, received = [], []
    for source in summary["sources"]:
        artifact = by_id[source["artifact_id"]]
        payload = artifact["content_json"]
        received.append((artifact["id"], payload, enrichment.citation_roles(payload)))
        source_states.append({k: source[k] for k in ("source", "outcome", "truncated", "reason", "limitations")})
        source_states[-1]["captured_at"] = payload["captured_at"]
    materials = {aid: next(m for m in data["alert_materials"] if m["id"] == alert.material["id"])
                 for aid, alert in context.alerts.items() if alert.material}
    initial = view.build(context, frozen["id"], received, source_states, materials,
        execution_time=run["started_at"], run_id=run["id"])
    assert initial["ready"], initial["reason"]
    initial["artifact_id"] = original["id"]  # provenance only; never persisted to the old Run
    required = [c for c in view.candidates(context, frozen["id"], received, materials) if c["required"]]
    visible = {digest(i["source"]): i["value"] for i in frozen_items(json.loads(initial["messages"][1]["content"]))}
    assert all(visible[digest(c["ref"])] == c["value"] for c in required)
    policy = active_policy()
    gateway = SimpleNamespace(provider=policy.model.protocol, schema_profile=policy.model.schema_profile, model=policy.model.alias)
    limits = policy.case.limits(context.captured_at, policy.identity)
    options, bindings, excluded = offered_bindings(catalog(context, run["tenant_id"]), limits, context.captured_at, [], SimpleNamespace(configured=lambda: True))
    tools = {a["id"]: a["content_json"] for a in rows if a["kind"] == "tool_response"}
    prompt, sources = c3.messages(initial, context, tools, options)
    fmt = execution_format(response_format(c3.contract.ExecutionAnalysis, sources, members=context.alerts,
        questions=[q.id for q in context.questions], objects=context.scope.object_keys, bindings=bindings), bindings)
    initial_body = compact_execution_wire(prepare_request(gateway, {"model": gateway.model, "messages": prompt,
        "max_tokens": policy.model.output_tokens["C3"], "temperature": 0, "response_format": fmt}))

    # Reuse the ended Run's actual query/graph/plan receipts. A failed C3 is
    # explicitly unavailable; no fake model analysis is introduced into C6.
    current = next(a for a in rows if a["content_json"].get("type") == "model_view")
    bases = sorted([a for a in rows if a["content_json"].get("type") in
        {"materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda a: a["id"])
    dispatch = next(a["content_json"] for a in rows if a["content_json"].get("type") == "followup_dispatch")
    plan = by_id[dispatch["initial_analysis_artifact_id"]]["content_json"]
    execution, planned = delivery_followups(dispatch, plan)
    report = next(a["content_json"] for a in rows if a["content_json"].get("type") == "delivery_report")
    class Store:
        def where(self, *_):
            return []
        async def execute(self, _):
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [a for a in rows if a["kind"] == "tool_response"]))
        async def prepare_model_view(self, *_):
            return initial
    @asynccontextmanager
    async def transaction(_):
        store = Store()
        store.db = store
        yield store
    async def model_view(*_):
        return {"artifact_id": current["id"], **current["content_json"]}
    async def read_artifact(_self, _store, _run, identity):
        return by_id[str(identity)]["content_json"]
    with patch.object(BaselineEvidence, "model_view", model_view), patch.object(BaselineReanalysis, "read_artifact", read_artifact):
        final = await BaselineReanalysis(SimpleNamespace(transaction=transaction)).input(
            UUID(run["tenant_id"]), UUID(run["case_id"]), UUID(run_id), context, None, None, bases,
            instruction=c6.PROMPT, extra_data={"round": "final_delivery", "comparison": report["comparison"],
                "preliminary_analysis": {"state": "unavailable", "reason": "no_accepted_main_analysis"},
                "followup_execution": execution}, lead_candidates=planned, executed_plan_id=dispatch["initial_analysis_artifact_id"])
    assert final["ready"], final["reason"]
    final_body = prepare_request(gateway, {"model": gateway.model, "messages": final["messages"],
        "max_tokens": policy.model.output_tokens["C6"], "temperature": 0,
        "response_format": c6.delivery_format(final["source_map"], context, report["comparison"])})
    return {"run_id": run_id, "mode": "offline_rebuild_no_inference_no_persistence", "policy_sha256": policy.sha256,
        "original_ready": original["content_json"]["ready"], "original_reason": original["content_json"]["reason"],
        "required_values": len(required), "required_values_preserved": True, "offered_bindings": len(options),
        "excluded_bindings": excluded, "C3": {"body": initial_body, "source_map": sources, "prepared": initial},
        "C6": {"body": final_body, "source_map": final["source_map"], "prepared": final},
        "limitations": ["no_new_model_answer_or_success_claim", "C6_uses_original_failed_C3_receipt", "no_H_feedback_in_this_export"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value = asyncio.run(rebuild(args.snapshot, args.run_id))
    with Path(args.output).open("x") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k not in {"C3", "C6"}}, ensure_ascii=False))
