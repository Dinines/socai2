"""Program-generated previews of saved material; never dispatch or rewrite it."""
import argparse
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
config = json.loads((FOLDER / "config.json").read_text())
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
from app.socai2 import case_followup_input, case_followup_output
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.baseline_store import digest, encoded
from app.socai2.case_followup_loader import graph_candidates
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=["before", "Deep", "C6"])
phase = parser.parse_args().phase


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path = FOLDER / name
    if path.exists():
        assert path.read_text() == text, "do_not_overwrite_different_evidence: " + name
    else:
        path.write_text(text)


snapshot_path = ROOT / config["snapshot"]
snapshot = json.loads(snapshot_path.read_text())
original_hash = sha(snapshot_path)
policy = active_policy()
arts = {a["id"]: a for a in snapshot["artifacts"] if a["run_id"] == config["run_id"]
        and a["content_json"] and a["kind"] not in ("model_request", "model_response")}
c1 = next(a for a in arts.values() if a["schema_version"] == "socai2.baseline-context.v1")
old_base = next(a for a in arts.values() if a["schema_version"] == "socai2.case-model-input.v1")
raw, base = copy.deepcopy(c1["content_json"]), copy.deepcopy(old_base["content_json"])
# Offline-only compatibility, explicitly recorded. Runtime drift checks stay on.
raw["case_input_profile"] = policy.case_io.identity
base["case_boundary"]["profile"] = policy.case_io.identity
context = Context.model_validate(raw)
step = max((s for s in snapshot["run_steps"] if s["run_id"] == config["run_id"] and s["kind"] == "stage"
            and s["stage_code"] in ("C3", "C3.reanalysis") and s["state"] == "completed"), key=lambda s: s["seq"])
previous = arts[step["output_artifact_id"]]
dispatch = next(a["content_json"] for a in arts.values() if a["content_json"].get("type") == "followup_dispatch")
execution, lead = delivery_followups(dispatch, arts[dispatch["initial_analysis_artifact_id"]]["content_json"])
bases = [a for a in arts.values() if a["kind"] == "source_snapshot"
         and a["content_json"].get("type") in ("materials", "query_projection", "deep_summary", "graph_snapshot")]
state, graphs = graph_candidates(bases, arts)
material = next(a["content_json"] for a in bases if a["content_json"].get("type") == "materials")
projections = [a for a in bases if a["content_json"].get("type") == "query_projection"]
assert not projections  # This frozen Run did not execute external followup queries.
report = next(a["content_json"] for a in arts.values() if a["content_json"].get("type") == "delivery_report")
request_record = next(a["content_json"] for a in snapshot["artifacts"]
               if a["run_id"] == config["run_id"] and a["kind"] == "model_request")
request = request_record["payload"]["body"]
gateway = SimpleNamespace(provider=request_record["provider"], schema_profile=request_record["schema_profile"])
stages = ["Deep", "C6"] if phase == "before" else [phase]
summary = {"kind": config["kind"], "phase": phase, "model_calls": 0, "http_calls": 0, "database_calls": 0,
           "snapshot_sha256": original_hash, "original_profile": c1["content_json"]["case_input_profile"],
           "preview_profile": policy.case_io.identity, "offline_copy_profile_rebound": True, "stages": {}}
for stage in stages:
    kwargs = ({"question_id": config["question_id"], "options": [], "binding_map": {}} if stage == "Deep" else
              {"extra": {"round": "final_delivery", "comparison": report["comparison"],
                         "followup_execution": execution, "graph_state": state}, "lead": lead, "graphs": graphs})
    prepared = case_followup_input.build(stage, context, base, arts, previous=previous["content_json"],
        prior_id=previous["id"], material=material, projections=projections, **kwargs)
    assert prepared["ready"], prepared["reason"]
    stem = ("before-" if phase == "before" else "") + stage
    body = prepared["messages"][1]["content"]
    save(stem + "-model-input.txt", body)
    if stage == "Deep":
        save(stem + "-tools.txt", prepared["messages"][2]["content"])
    fmt = (case_followup_output.deep_format(prepared) if stage == "Deep" else
           case_followup_output.final_format(prepared, context, report["comparison"]))
    wire = compact_execution_wire(prepare_request(gateway, {"model": request["model"],
        "messages": prepared["messages"], "response_format": fmt, "temperature": 0,
        "max_tokens": policy.model.output_tokens[stage]}))
    save(stem + "-request-preview.json", wire)
    save(stem + "-selection.json", {k: prepared[k] for k in
        ("source_map", "case_boundary", "followup_boundary", "omissions", "coverage")})
    dependencies = prepared["followup_boundary"]["dependencies"]
    for dep in dependencies:
        if dep["visible_id"]:
            target = prepared["source_map"][dep["visible_id"]]
            assert target["ref"] == dep["original_source"]["ref"]
            assert target["alert_ids"] == dep["original_source"]["alert_ids"]
    # C3/Deep prose is immutable: only fields/containers and structured IDs change.
    def prose(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k in ("summary", "statement", "answer", "text", "reason", "objective", "required_evidence") and isinstance(v, str):
                    yield v
                elif k in ("limitations", "alternatives"):
                    yield from (s for s in v if isinstance(s, str))
                else:
                    yield from prose(v)
        elif isinstance(value, list):
            for v in value:
                yield from prose(v)
    originals = set(prose(previous["content_json"]["analysis"]))
    originals.update(s for a in arts.values() if a["content_json"].get("type") == "deep_summary"
                     for s in prose(a["content_json"].get("answer")))
    for row in prepared["followup_boundary"]["records"]:
        if row["block"] in {"C3", "Deep", "plan"}:
            assert all(s in originals for s in prose(row["value"])), row["id"]
    if phase != "before":
        old_sources = {encoded(v["ref"]): v for v in base["source_map"].values()}
        for source in prepared["source_map"].values():
            old = old_sources.get(encoded(source["ref"]))
            if old:
                for key in ("ref", "alert_ids", "original_scope", "membership_basis", "query_alert_ids", "record_alert_ids", "knowledge"):
                    assert source.get(key) == old.get(key), key
        assert not any(word in body for word in ("[材料限制]", "[原计划执行情况", "execution_plan_index"))
        if stage == "C6":
            c3 = next(r for r in prepared["followup_boundary"]["records"] if r["block"] == "C3")
            assert "followups" not in c3["value"]
            assert all(q["id"] != "coverage" for q in c3["value"]["questions"])
            assert prepared["followup_boundary"]["program_metadata"]["followup_execution"] == execution
            assert len([r for r in prepared["followup_boundary"]["records"] if r["block"] == "Deep"]) == 2
    summary["stages"][stage] = {"body_characters": len(body), "sources": len(prepared["source_map"]),
        "visible_dependencies": sum(d["visible_id"] is not None for d in dependencies),
        "unavailable_dependencies": sum(d["visible_id"] is None for d in dependencies),
        "original_prose_and_dependency_scopes_preserved": True,
        "tools_characters": len(prepared["messages"][2]["content"]) if stage == "Deep" else None,
        "files": {name: sha(FOLDER / name) for name in
                  (stem + "-model-input.txt", stem + "-request-preview.json", stem + "-selection.json")}}
assert sha(snapshot_path) == original_hash
summary["original_snapshot_unchanged"] = True
summary["source_files"] = {str(p.relative_to(ROOT)): sha(p) for p in [
    *[ROOT / "services/api/app/socai2" / n for n in
      ("case_followup_input.py", "case_c3_input_selection.py", "case-input-v1.json")],
    *list((ROOT / "services/api/app/socai2").glob("case_followup_selection.py")), FOLDER / "rebuild.py"]}
save(phase + "-summary.json", summary)
print(json.dumps(summary["stages"], ensure_ascii=False))
