"""Offline current-input previews from one sealed H/comparison/plan snapshot."""
import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
config = json.loads((HERE / "config.json").read_text())
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import (
    case_followup_input,
    case_followup_output,
    case_model_boundary,
    case_output_adapter,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.case_followup_loader import graph_candidates
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    phase = parser.parse_args().phase
    folder = HERE / phase
    folder.mkdir(exist_ok=True)
    snapshot = ROOT / config["snapshot"]
    original_hash = sha(snapshot)
    db = json.loads(snapshot.read_text())
    run = next(r for r in db["runs"] if r["id"] == config["run_id"])
    artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == run["id"]}
    c1 = next(a for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
    frozen = copy.deepcopy(c1["content_json"])
    frozen["case_input_profile"] = active_policy().case_io.identity
    context = Context.model_validate(frozen)
    material = {aid: next(m for m in db["alert_materials"] if m["id"] == row.material["id"])
                for aid, row in context.alerts.items() if row.material}

    def stage(code):
        step = next(s for s in db["run_steps"] if s["run_id"] == run["id"]
                    and s["kind"] == "stage" and s["stage_code"] == code)
        return artifacts[step["output_artifact_id"]]

    c2 = stage("C2")["content_json"]
    enrichment = [(r["artifact_id"], artifacts[r["artifact_id"]]["content_json"], r) for r in c2["sources"]]
    old_base = next(a["content_json"] for a in artifacts.values()
                    if a["schema_version"] == "socai2.case-model-input.v1")
    base = case_model_boundary.build(context, c1["id"], enrichment, old_base["source_state_ledger"], material,
                                    execution_time=run["started_at"], run_id=run["id"])
    assert base["ready"], base["reason"]
    c3_messages, _ = case_model_boundary.messages(base, context, [])
    prior = stage("C3")
    dispatch = stage("C4.routing")["content_json"]
    initial = artifacts[dispatch["initial_analysis_artifact_id"]]
    execution, plans = delivery_followups(dispatch, initial["content_json"])
    report = next(a["content_json"] for a in artifacts.values()
                  if (a["content_json"] or {}).get("type") == "delivery_report")
    comparison = report["comparison"]
    lead = []
    if comparison["state"] == "eligible":
        result = context.prior_results[comparison["result_id"]]
        value = {k: result[k] for k in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "delivery_state")}
        value["comparison_result_id"] = comparison["result_id"]
        lead.append({"original": value, "required": True, "entry": {"value": value},
                     "source": {"ref": case_followup_input.reference("result", comparison["result_id"], "prior_analysis"),
                                "alert_ids": comparison["shared_alert_ids"]}})
    bases = sorted([a for a in artifacts.values() if (a["content_json"] or {}).get("type") in
                    {"materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda a: a["id"])
    graph_state, graphs = graph_candidates(bases, artifacts)
    material_receipt = stage("C4.materials")["content_json"]
    projections = [a for a in bases if a["content_json"].get("type") == "query_projection"]
    frozen_artifacts = {aid: a for aid, a in artifacts.items() if a["content_json"] is not None
                        and a["kind"] not in {"model_request", "model_response"}}
    final = case_followup_input.build("C6", context, base, frozen_artifacts, previous=prior["content_json"], prior_id=prior["id"],
        material=material_receipt, projections=projections, graphs=graphs, lead=[*lead, *plans],
        extra={"comparison": comparison, "followup_execution": execution, "graph_state": graph_state})
    assert final["ready"], final["reason"]
    gateway_source = next(a["content_json"] for a in artifacts.values() if a["kind"] == "model_request")
    gateway = SimpleNamespace(provider=gateway_source["provider"], schema_profile=gateway_source["schema_profile"])
    model = gateway_source["payload"]["body"]["model"]

    def save(name, value):
        content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        with (folder / name).open("x") as file:
            file.write(content)

    summary = []
    for name, prepared, messages, fmt in (
        ("C3", base, c3_messages, case_output_adapter.output_format(base, context, {})),
        ("C6", final, final["messages"], case_followup_output.final_format(final, context, comparison)),
    ):
        wire = prepare_request(gateway, {"model": model, "messages": messages, "temperature": 0,
                               "max_tokens": active_policy().model.output_tokens[name], "response_format": fmt})
        if name == "C3":
            wire = compact_execution_wire(wire)
        rows = prepared["input_ledger"]["records"] if name == "C3" else prepared["followup_boundary"]["records"]
        save(name + "-model-input.txt", messages[1]["content"])
        save(name + "-request-preview.json", wire)
        save(name + "-selection.json", {"records": rows, "source_map": prepared["source_map"], "omissions": prepared["omissions"]})
        summary.append({"stage": name, "characters": len(messages[1]["content"]), "sources": len(prepared["source_map"]),
                        "human_sources": [r["id"] for r in rows if r["ref"]["role"] == "human_statement"],
                        "plan_sources": [r["id"] for r in rows if r["block"] == "plan"]})
    assert sha(snapshot) == original_hash
    save("summary.json", {"kind": "offline_frozen_H_comparison_plan_preview", "source_run_id": run["id"],
         "snapshot": config["snapshot"], "snapshot_sha256": original_hash,
         "real_model_calls": 0, "database_calls": 0, "network_calls": 0,
         "profile_rebound_only_in_offline_copy": True, "profile": active_policy().case_io.identity,
         "comparison": comparison, "original_plan_artifact_id": initial["id"], "stages": summary})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
