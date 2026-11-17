"""Rebuild full Case model messages from sealed artifacts, without external calls."""
import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
CONFIG = json.loads((HERE / "config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / CONFIG["policy"])
from app.socai2 import case_followup_input as current_followup
from app.socai2 import case_input_text, case_followup_selection, case_output_adapter, case_followup_output
from app.socai2 import case_input_hierarchy as current_hierarchy
from app.socai2 import case_model_boundary as c3
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Scope
from app.socai2.baseline_enrichment import citation_roles
from app.socai2.baseline_followup_projection import delivery_followups
from app.socai2.case_followup_loader import graph_candidates
from app.socai2.runtime_policy import active_policy


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body, ("existing_evidence_differs", str(path))
    else:
        path.write_text(body)


def old_module(filename):
    spec = importlib.util.spec_from_file_location("app.socai2._tool_before_" + filename,
        HERE / "before-source/services/api/app/socai2" / (filename + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old_selection = old_module("case_c3_input_selection")


@contextmanager
def before_selection():
    with patch.object(case_input_text, "select_rows", old_selection.select_rows), patch.object(
            case_followup_selection, "select_rows", old_selection.select_rows):
        yield

profile = active_policy().case_io
old_raw = (HERE / "before-source/services/api/app/socai2/case-input-v1.json").read_bytes()
old_profile = replace(profile, raw=old_raw, sha256=hashlib.sha256(old_raw).hexdigest())
source = ROOT / CONFIG["source_batch"]
db = read(source / "pg-01/database.json")
run_id = CONFIG["source_run_id"]
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == run_id}
context_artifact = next(a for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
frozen_context = Context.model_validate(context_artifact["content_json"])
# The stored Run used an earlier profile. Both previews explicitly rebind
# the frozen context offline; they never resume or mutate that Run.
stored_base = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == c3.SCHEMA)
c2 = next(a["content_json"] for a in artifacts.values()
          if a["schema_version"] == "socai2.baseline-enrichment.v1" and a["kind"] == "source_snapshot")
enrichment = [(s["artifact_id"], artifacts[s["artifact_id"]]["content_json"],
               citation_roles(artifacts[s["artifact_id"]]["content_json"])) for s in c2["sources"]]
materials = {aid: next(m for m in db["alert_materials"] if m["id"] == alert.material["id"])
             for aid, alert in frozen_context.alerts.items() if alert.material}


def base_for(selected, queries=None):
    # Explicit offline profile binding; no existing Run is resumed or modified.
    context = frozen_context.model_copy(update={"case_input_profile": selected.identity})
    with patch.object(c3, "selected_profile", return_value=selected):
        base = c3.build(context, context_artifact["id"], enrichment if queries is None else queries,
                        stored_base["source_state_ledger"] if queries is None else [], materials,
                        execution_time=stored_base["input_ledger"]["program_facts"]["execution_started_at"], run_id=run_id)
    assert base["ready"], base["reason"]
    return context, base


def option(alias, binding):
    return {"binding_id": alias, "tool_name": binding["tool_name"], "hostname": binding["hostname"],
            "alert_ids": binding["alert_ids"], "object_keys": sorted({o["object_key"] for o in binding["objects"]})}


def build(request, context, base, selected, followup, hierarchy):
    payload = request["content_json"]["payload"]
    stage = payload["case_boundary"].get("stage", "C3")
    if stage == "C3":
        prepared = copy.deepcopy(base)
        options = [option(alias, binding) for alias, binding in payload["binding_map"].items()]
        with patch.object(c3, "selected_profile", return_value=selected), patch.object(c3, "render_tools", hierarchy.render_tools):
            prepared["messages"], _ = c3.messages(prepared, context, options)
        return prepared
    frozen = {aid: a for aid, a in artifacts.items() if a["content_json"] is not None
              and a["kind"] not in {"model_request", "model_response"} and a["captured_at"] < request["captured_at"]}
    prior_id = next(r["ref"]["id"] for r in payload["followup_boundary"]["records"] if r["block"] == "C3")
    material = next(a["content_json"] for a in frozen.values() if a["content_json"].get("type") == "materials")
    projections = sorted([a for a in frozen.values() if a["content_json"].get("type") == "query_projection"],
                         key=lambda a: (a["captured_at"], a["id"]))
    options, lead, graphs = [], [], []
    extra = copy.deepcopy(payload["followup_boundary"]["program_metadata"])
    if stage == "Deep":
        options = [option(alias, material["catalog"]["bindings"][bid]) for alias, bid in payload["binding_map"].items()]
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
        extra["followup_execution"], plans = delivery_followups(dispatch, frozen[dispatch["initial_analysis_artifact_id"]]["content_json"])
        lead.extend(plans)
        bases = sorted([a for a in frozen.values() if a["content_json"].get("type") in
                        {"materials", "query_projection", "deep_summary", "graph_snapshot"}], key=lambda a: a["id"])
        extra["graph_state"], graphs = graph_candidates(bases, frozen)
    with patch.object(followup, "selected_profile", return_value=selected), patch.object(followup, "render_tools", hierarchy.render_tools):
        return followup.build(stage, context, base, frozen, previous=frozen[prior_id]["content_json"], prior_id=prior_id,
                              question_id=payload["case_boundary"].get("question_id"), material=material,
                              projections=projections, options=options, binding_map=payload["binding_map"],
                              extra=extra, lead=lead, graphs=graphs)


def full_text(prepared):
    return "\n\n".join(f"[{i + 1}. {m['role']}]\n{m['content']}" for i, m in enumerate(prepared["messages"])) + "\n"


def rows(prepared, stage):
    return prepared["input_ledger" if stage == "C3" else "followup_boundary"]["records"]


with before_selection():
    old_context, before_base = base_for(old_profile)
new_context, after_base = base_for(profile)
REFERENCE_FIELDS = {"source_refs", "evidence_ids", "source_ids", "support_ids", "counter_ids",
                    "support", "counterevidence", "evidence_refs", "visible", "visible_id", "material_source_ids",
                    "receipt_source_id"}


def normalized(value, sources, key=None):
    # Normalize only structural references for comparison, never prose.
    if isinstance(value, list):
        return [normalized(v, sources, key) for v in value]
    if isinstance(value, dict):
        return {k: normalized(v, sources, k) for k, v in value.items()}
    if key in REFERENCE_FIELDS and isinstance(value, str) and value in sources:
        return {"resolved_reference": sources[value]["ref"]}
    return value


def ref_key(row):
    return json.dumps(row["ref"], sort_keys=True)


def allowed_projection(row, sources):
    result = normalized(copy.deepcopy(row), sources)
    result.pop("id")
    path = row["ref"].get("source_path") or ""
    value = result["value"]
    if path.startswith("$.incidents.") and isinstance(value, dict):
        if isinstance(value.get("limitations"), list):
            value["limitations"] = [v for v in value["limitations"] if v != "member_coverage:unresolved"]
        scope = value.get("declared_scope")
        if isinstance(scope, dict) and isinstance(scope.get("limitations"), list):
            scope["limitations"] = [v for v in scope["limitations"] if v != "frozen_incident_members_only"]
            if not scope["limitations"]:
                scope.pop("limitations")
    return result


checks, counts = [], Counter()
for request in sorted([a for a in artifacts.values() if a["kind"] == "model_request"], key=lambda a: a["captured_at"]):
    actual = request["content_json"]["payload"]
    stage = actual["case_boundary"].get("stage", "C3")
    counts[stage] += 1
    name = stage + (f"-{counts[stage]:02}" if stage == "Deep" else "")
    with before_selection():
        before = build(request, old_context, before_base, old_profile, current_followup, current_hierarchy)
    after = build(request, new_context, after_base, profile, current_followup, current_hierarchy)
    assert before["ready"] and after["ready"]
    previous = ROOT / CONFIG["previous_batch"] / "recorded" / (name + "-model-input.txt")
    assert full_text(before) == previous.read_text(), (name, "previous_preview_differs")
    for label, prepared, context in (("before", before, old_context), ("after", after, new_context)):
        wire = copy.deepcopy(actual["body"])
        wire["messages"] = prepared["messages"]
        wire["response_format"] = (case_output_adapter.output_format(prepared, context, actual["binding_map"]) if stage == "C3"
            else case_followup_output.deep_format(prepared) if stage == "Deep"
            else case_followup_output.final_format(prepared, context, prepared["followup_boundary"]["program_metadata"]["comparison"]))
        save(HERE / label / (name + "-model-input.txt"), full_text(prepared))
        save(HERE / label / (name + "-request-preview.json"), wire)
        save(HERE / label / (name + "-selection.json"), {"records": rows(prepared, stage),
            "source_map": prepared["source_map"], "omissions": prepared["omissions"],
            "case_boundary": prepared["case_boundary"],
            "dependencies": prepared.get("followup_boundary", {}).get("dependencies", [])})
        selected = [r for r in rows(prepared, stage) if (r["ref"].get("source_path") or "").startswith("$.incidents.")]
        save(HERE / label / (name + "-incident-material.txt"),
             "\n".join(line for line in prepared["messages"][1]["content"].splitlines()
                       if any(line.startswith("[" + r["id"] + "]") for r in selected)) + "\n")
    old_rows, new_rows = {ref_key(r): r for r in rows(before, stage)}, {ref_key(r): r for r in rows(after, stage)}
    assert not new_rows.keys() - old_rows.keys(), name
    removed = [old_rows[k] for k in old_rows.keys() - new_rows.keys()]
    assert all(r["value"] == [] and r["ref"]["source_path"].endswith(".diagnosis.limitations") for r in removed), name
    changed, remapped = [], []
    for key, row in new_rows.items():
        old = old_rows[key]
        actual_row = normalized(copy.deepcopy(row), after["source_map"])
        actual_row.pop("id")
        assert actual_row == allowed_projection(old, before["source_map"]), (name, row["id"], "unexpected_record_change")
        prior_row = normalized(copy.deepcopy(old), before["source_map"])
        prior_row.pop("id")
        if prior_row != actual_row:
            changed.append(row["id"])
        if old["id"] != row["id"]:
            remapped.append({"before": old["id"], "after": row["id"], "ref": row["ref"]})
        old_map, new_map = before["source_map"][old["id"]], after["source_map"][row["id"]]
        assert {k: v for k, v in old_map.items() if k != "visible_value_sha256"} == {
            k: v for k, v in new_map.items() if k != "visible_value_sha256"}, (name, row["id"], "source_changed")
    if stage != "C3":
        assert normalized(before["followup_boundary"]["dependencies"], before["source_map"]) == normalized(
            after["followup_boundary"]["dependencies"], after["source_map"]), (name, "dependency_changed")
        assert normalized(before["followup_boundary"]["query_facts"], before["source_map"]) == normalized(
            after["followup_boundary"]["query_facts"], after["source_map"]), (name, "query_changed")
        assert before["binding_map"] == after["binding_map"]
    checks.append({"stage": name, "request_artifact_id": request["id"],
        "records_before": len(old_rows), "records_after": len(new_rows),
        "omitted_empty_incident_limits": [{"id": r["id"], "ref": r["ref"]} for r in removed],
        "presentation_changed_records": changed, "remapped_source_ids": remapped,
        "all_retained_original_values_roles_scopes_refs_and_dependencies_preserved": True,
        "before_matches_previous_complete_preview": True,
        "message_characters_before": [len(m["content"]) for m in before["messages"]],
        "message_characters_after": [len(m["content"]) for m in after["messages"]]})
original_hashes = read(HERE / "source-files.json")
assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in original_hashes.items())
save(HERE / "verification.json", {"status": "passed_offline", "source_run_id": run_id,
    "before_profile": old_profile.identity, "after_profile": profile.identity,
    "checks": checks, "original_files_unchanged": len(original_hashes),
    "new_model_calls": 0, "database_calls": 0, "new_runs": 0,
    "preview_not_dispatched": True, "model_quality": "NOT_PASSED_UNCHANGED"})
print(json.dumps([{k: v for k, v in c.items() if k != "remapped_source_ids"} for c in checks], ensure_ascii=False))
