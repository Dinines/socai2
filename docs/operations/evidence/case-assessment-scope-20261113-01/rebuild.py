"""Offline replay of stored requests; no database, provider or source mutation."""
import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
CONFIG = json.loads((HERE / "config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / CONFIG["policy"])
from app.socai2 import case_followup_input as followup
from app.socai2 import case_model_boundary as c3
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Scope
from app.socai2.baseline_enrichment import citation_roles
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.case_followup_loader import graph_candidates


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body, ("existing_evidence_differs", str(path))
    else:
        path.write_text(body)


source = ROOT / CONFIG["source_batch"]
db = read(source / "pg-01/database.json")
run_id = CONFIG["source_run_id"]
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == run_id}
context_artifact = next(a for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
context = Context.model_validate(context_artifact["content_json"])
base_artifact = next(a for a in artifacts.values() if a["schema_version"] == c3.SCHEMA)
stored_base = base_artifact["content_json"]
summary = next(a["content_json"] for a in artifacts.values()
               if a["schema_version"] == "socai2.baseline-enrichment.v1" and a["kind"] == "source_snapshot")
enrichment = [(s["artifact_id"], artifacts[s["artifact_id"]]["content_json"],
               citation_roles(artifacts[s["artifact_id"]]["content_json"])) for s in summary["sources"]]
materials = {aid: next(m for m in db["alert_materials"] if m["id"] == alert.material["id"])
             for aid, alert in context.alerts.items() if alert.material}
old_path = HERE / "before-source/services/api/app/socai2/case_input_text.py"
spec = importlib.util.spec_from_file_location("app.socai2._scope_before", old_path)
old_input = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_input)


def build_base(prepare):
    with patch.object(c3, "prepare", prepare):
        return c3.build(context, context_artifact["id"], enrichment, stored_base["source_state_ledger"], materials,
                        execution_time=stored_base["input_ledger"]["program_facts"]["execution_started_at"], run_id=run_id)


before_base, after_base = build_base(old_input.prepare), build_base(c3.prepare)
assert before_base["source_map"] == stored_base["source_map"]
assert before_base["input_ledger"]["records"] == stored_base["input_ledger"]["records"]


def build_followup(request, base):
    payload = request["content_json"]["payload"]
    stage = payload["case_boundary"]["stage"]
    frozen = {aid: a for aid, a in artifacts.items() if a["content_json"] is not None
              and a["kind"] not in {"model_request", "model_response"} and a["captured_at"] < request["captured_at"]}
    prior_id = next(r["ref"]["id"] for r in payload["followup_boundary"]["records"] if r["block"] == "C3")
    material = next(a["content_json"] for a in frozen.values() if a["content_json"].get("type") == "materials")
    projections = sorted([a for a in frozen.values() if a["content_json"].get("type") == "query_projection"],
                         key=lambda a: (a["captured_at"], a["id"]))
    options, lead, graphs = [], [], []
    extra = copy.deepcopy(payload["followup_boundary"]["program_metadata"])
    if stage == "Deep":
        for alias, bid in payload["binding_map"].items():
            binding = material["catalog"]["bindings"][bid]
            options.append({"binding_id": alias, "tool_name": binding["tool_name"], "hostname": binding["hostname"],
                            "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})})
    else:
        raw = extra["comparison"]
        comparison = {k: raw[k] for k in ("result_id", "state", "prior_scope", "added_alert_ids",
                                          "removed_alert_ids", "shared_alert_ids", "limitations")}
        comparison["prior_scope"] = Scope.model_validate(comparison["prior_scope"]).model_dump(mode="json")
        extra["comparison"] = comparison
        result = context.prior_results[comparison["result_id"]]
        value = {k: result[k] for k in ("conclusion", "conclusion_state", "conclusion_origin", "validation_state", "delivery_state")}
        value["comparison_result_id"] = comparison["result_id"]
        lead.append({"original": value, "required": True, "entry": {"value": value},
                     "source": {"ref": followup.reference("result", comparison["result_id"], "prior_analysis"),
                                "alert_ids": comparison["shared_alert_ids"]}})
        dispatch = next(a["content_json"] for a in frozen.values() if a["content_json"].get("type") == "followup_dispatch")
        execution, plans = delivery_followups(dispatch, frozen[dispatch["initial_analysis_artifact_id"]]["content_json"])
        extra["followup_execution"] = execution
        lead.extend(plans)
        bases = sorted([a for a in frozen.values() if a["content_json"].get("type") in
                        {"materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda a: a["id"])
        extra["graph_state"], graphs = graph_candidates(bases, frozen)
    return followup.build(stage, context, base, frozen, previous=frozen[prior_id]["content_json"], prior_id=prior_id,
                          question_id=payload["case_boundary"].get("question_id"), material=material,
                          projections=projections, options=options, binding_map=payload["binding_map"],
                          extra=extra, lead=lead, graphs=graphs)


checks, counts = [], Counter()
for request in sorted([a for a in artifacts.values() if a["kind"] == "model_request"], key=lambda a: a["captured_at"]):
    actual = request["content_json"]["payload"]
    stage = actual["case_boundary"].get("stage", "C3")
    counts[stage] += 1
    name = stage + (f"-{counts[stage]:02}" if stage == "Deep" else "")
    before, after = ((before_base, after_base) if stage == "C3" else
                     (build_followup(request, before_base), build_followup(request, after_base)))
    assert before["ready"] and after["ready"]
    assert before["source_map"] == actual["source_map"], (name, "recorded_source_map_differs")
    ledger = "input_ledger" if stage == "C3" else "followup_boundary"
    old_rows, new_rows = before[ledger]["records"], after[ledger]["records"]
    assert len(old_rows) == len(new_rows)
    changed = []
    for old, new in zip(old_rows, new_rows, strict=True):
        if old == new:
            continue
        assert old.get("context_kind") == new.get("context_kind") == "current_assessment"
        expected = copy.deepcopy(old)
        expected["original_scope"] = {"alert_ids": sorted({m["alert_id"] for m in context.assessment_members})}
        aliases = after["case_boundary"]["member_aliases"]
        expected["value"]["declared_scope"] = {"alert_ids": [aliases[a] for a in expected["original_scope"]["alert_ids"]]}
        assert new == expected
        changed.append(new["id"])
        source_before, source_after = before["source_map"][old["id"]], after["source_map"][new["id"]]
        assert source_before["ref"] == source_after["ref"] and source_before["alert_ids"] == source_after["alert_ids"]
        assert source_after["original_scope"] == expected["original_scope"]
    assert len(changed) == 1, (name, changed)
    assert before["case_boundary"] == after["case_boundary"]
    if stage != "C3":
        assert before["followup_boundary"]["dependencies"] == after["followup_boundary"]["dependencies"]
        assert before["followup_boundary"]["records"] == actual["followup_boundary"]["records"]
    preview = copy.deepcopy(actual["body"])
    preview["messages"][:len(after["messages"])] = after["messages"]
    # Old requests/replies remain authoritative; these are previews, not new answers.
    save(HERE / "before" / (name + "-actual-request.json"), actual["body"])
    save(HERE / "before" / (name + "-rebuilt-input.txt"), before["messages"][1]["content"])
    save(HERE / "after" / (name + "-request-preview.json"), preview)
    save(HERE / "after" / (name + "-model-input.txt"), after["messages"][1]["content"])
    row = next(r for r in new_rows if r["id"] in changed)
    save(HERE / "after" / (name + "-scope-selection.json"), {"record": row, "source": after["source_map"][row["id"]]})
    checks.append({"stage": name, "request_artifact_id": request["id"], "records": len(new_rows),
                   "changed_source": changed[0], "before_characters": len(before["messages"][1]["content"]),
                   "after_characters": len(after["messages"][1]["content"]),
                   "before_input_matches_recorded_text": before["messages"][1]["content"] == actual["body"]["messages"][1]["content"],
                   "before_records_and_source_map_match_saved_request": True,
                   "other_records_prose_refs_current_ownership_and_targets_unchanged": True})
old_hashes = read(HERE / "source-files.json")
assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected for name, expected in old_hashes.items())
save(HERE / "verification.json", {"status": "passed_offline", "source_run_id": run_id, "checks": checks,
                                  "original_batch_files_unchanged": len(old_hashes), "new_model_calls": 0,
                                  "database_calls": 0, "new_runs": 0, "preview_not_dispatched": True,
                                  "saved_result_and_current_assessment_evidence": CONFIG["source_batch"] + "/persistence-verification.json",
                                  "quality": "NOT_PASSED_UNCHANGED"})
print(json.dumps(checks, ensure_ascii=False))
