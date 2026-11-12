"""Rebuild saved inputs only: no model, HTTP, database or original-file writes."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import read, save, sha

_, frozen = initialize(ROOT / "docs/operations/evidence/fixed-investigation-20261112-04/config.json")
from app.socai2 import alert_model_boundary, case_followup_input, case_model_boundary, incident_model_boundary
from app.socai2.baseline_context import Context
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_followup_loader import graph_candidates
from app.socai2.runtime_policy import active_policy

folder = Path(__file__).parent
data = read(frozen / "export/database.json")
before = digest(data)
artifacts = {a["id"]: a for a in data["artifacts"]}
policy = active_policy()
summary = {"kind": "offline_input_rebuild_not_dispatched", "model_calls": 0, "database_writes": 0,
           "source_snapshot": str((frozen / "export/database.json").relative_to(ROOT)), "stages": {}}


def emit(stage, messages, sources):
    user = "\n".join(m["content"] for m in messages if m["role"] == "user")
    path = folder / (stage + "-model-input.txt")
    if path.exists():
        assert path.read_text() == user, "do_not_overwrite_different_evidence"
    else:
        path.write_text(user)
    summary["stages"][stage] = {"user_characters": len(user), "source_count": len(sources),
                                "file": path.name, "sha256": sha(path)}


for stage, rid in (("A", "be4ee7f2-634c-5199-9c76-e46b6c5b1cdc"),
                   ("I", "948e0148-2bfd-5c75-b07b-5c0c72ddcd61")):
    run = next(r for r in data["runs"] if r["id"] == rid)
    source = artifacts[run["input_artifact_id"]]["content_json"]
    if stage == "A":
        queries = [(a["id"], a["content_json"]) for a in data["artifacts"]
                   if a["run_id"] == rid and a["kind"] == "tool_response"]
        result = alert_model_boundary.build(source, run["input_artifact_id"], queries, policy.alert_io,
                                            execution_time=run["started_at"])
    else:
        result = incident_model_boundary.build(source, run["input_artifact_id"], policy.incident_io,
                                               execution_time=run["started_at"])
        skipped = [r for r in result[-1]["records"]
                   if r["header"][1] == "execution_receipt" and r["value"]["state"] == "skipped"]
        assert skipped and all(r["rendered_text"] == "威胁情报：未查询" for r in skipped)
    emit(stage, result[0], result[1])

rid = read(frozen / "execution.json")["run_id"]
run = next(r for r in data["runs"] if r["id"] == rid)
arts = {aid: a for aid, a in artifacts.items() if a["run_id"] == rid and a["content_json"]
        and a["kind"] not in ("model_request", "model_response")}
c1 = next(a for a in arts.values() if a["schema_version"] == "socai2.baseline-context.v1")
context = Context.model_validate(c1["content_json"])
old_base = next(a["content_json"] for a in arts.values() if a["schema_version"] == "socai2.case-model-input.v1")
enrichment = [(a["id"], a["content_json"], {}) for a in arts.values() if a["kind"] == "tool_response"]
materials = {aid: next(m for m in data["alert_materials"] if m["id"] == item.material["id"])
             for aid, item in context.alerts.items() if item.material}
base = case_model_boundary.build(context, c1["id"], enrichment, old_base["source_state_ledger"], materials,
                                execution_time=run["started_at"], run_id=rid)
assert base["ready"], base["reason"]
def source_identity(mapping):
    # Saved tuples become JSON arrays; compare the complete serialized values.
    return {encoded(row["ref"]).decode(): json.loads(encoded(row)) for row in mapping.values()}


assert source_identity(base["source_map"]) == source_identity(old_base["source_map"])
emit("C3", base["messages"], base["source_map"])
summary["stages"]["C3"]["excludes_separate_tool_catalog"] = True

step = max((s for s in data["run_steps"] if s["run_id"] == rid and s["kind"] == "stage"
            and s["stage_code"] in ("C3", "C3.reanalysis") and s["state"] == "completed"), key=lambda s: s["seq"])
previous = arts[step["output_artifact_id"]]
dispatch = next(a["content_json"] for a in arts.values() if a["content_json"].get("type") == "followup_dispatch")
execution, planned = delivery_followups(dispatch, arts[dispatch["initial_analysis_artifact_id"]]["content_json"])
bases = [a for a in arts.values() if a["kind"] == "source_snapshot"
         and a["content_json"].get("type") in ("materials", "query_projection", "deep_summary", "graph_snapshot")]
state, graphs = graph_candidates(bases, arts)
material = next(a["content_json"] for a in bases if a["content_json"].get("type") == "materials")
report = next(a["content_json"] for a in arts.values() if a["content_json"].get("type") == "delivery_report")
# C6 consumes the original frozen C3 input/answer, preserving even source-number
# ordering. The independently rebuilt C3 above checks its current projection.
final = case_followup_input.build("C6", context, old_base, arts, previous=previous["content_json"],
    prior_id=previous["id"], material=material, projections=[],
    extra={"round": "final_delivery", "comparison": report["comparison"],
           "followup_execution": execution, "graph_state": state}, lead=planned, graphs=graphs)
assert final["ready"], final["reason"]
old_final = read(frozen / "C6-input-final.json")["prepared"]
assert encoded(final["source_map"]) == encoded(old_final["source_map"])
assert encoded(final["followup_boundary"]["records"]) == encoded(old_final["followup_boundary"]["records"])
assert encoded(final["case_boundary"]["coverage_facts"]) == encoded(old_final["case_boundary"]["coverage_facts"])
emit("C6", final["messages"], final["source_map"])
assert digest(data) == before
summary.update(original_snapshot_unchanged=True, C3_sources_unchanged=True,
               C6_uses_original_frozen_C3=True, C6_sources_records_and_program_coverage_unchanged=True)
summary["source_sha256"] = {name: sha(ROOT / "services/api/app/socai2" / name) for name in
    ("program_facts.py", "alert_input_text.py", "incident_input_text.py", "case_input_text.py", "case_followup_input.py")}
save(folder / "rebuild-summary.json", summary)
print(json.dumps(summary, ensure_ascii=False))
