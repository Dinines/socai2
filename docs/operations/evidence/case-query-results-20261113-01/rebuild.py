"""Rebuild full Case model messages from sealed artifacts, without external calls."""
import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from contextlib import contextmanager, nullcontext
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
    previous = ROOT / CONFIG["previous_batch"] / "after" / (name + "-model-input.txt")
    assert full_text(before) == previous.read_text()
    assert before["messages"] == after["messages"]
    assert rows(before, stage) == rows(after, stage)
    assert before["source_map"] == after["source_map"]
    if stage != "C3":
        assert before["followup_boundary"]["dependencies"] == after["followup_boundary"]["dependencies"]
        assert before["followup_boundary"]["query_facts"] == after["followup_boundary"]["query_facts"]
    wire = copy.deepcopy(actual["body"])
    wire["messages"] = after["messages"]
    save(HERE / "recorded" / (name + "-model-input.txt"), full_text(after))
    save(HERE / "recorded" / (name + "-request-preview.json"), wire)
    checks.append({"stage": name, "request_artifact_id": request["id"], "records": len(rows(after, stage)),
                   "messages_source_map_dependencies_unchanged": True,
                   "matches_previous_complete_preview": True,
                   "message_characters": [len(m["content"]) for m in after["messages"]]})

# The recorded batch has no positive rows for these four sources. Add an
# explicitly synthetic, contract-shaped example; do not call it a real query.
sys.path.insert(0, str(ROOT / "services/api/tests"))
from test_socai2_case_followup_boundary import background_query_example, answer_for
from uuid import UUID
synthetic = background_query_example(frozen_context)
original_synthetic = copy.deepcopy(synthetic)
save(HERE / "synthetic-source.json", {"kind": "synthetic_nonempty_tool_results_no_execution",
    "frozen_context_source": CONFIG["source_batch"] + "/pg-01/database.json",
    "enrichment": synthetic, "prior_analysis": "synthetic_unresolved_with_explicit_result_dependencies"})
identities = {identity for identity, _, _ in synthetic}
variants = {}
for label, selected in (("before", old_profile), ("after", profile)):
    with before_selection() if label == "before" else nullcontext():
        context, base = base_for(selected, synthetic)
        with patch.object(c3, "selected_profile", return_value=selected):
            base["messages"], _ = c3.messages(base, context, [])
        evidence = [r for r in rows(base, "C3") if r["ref"]["id"] in identities and r["ref"]["source_path"]]
        answer = answer_for(base, context)
        answer["questions"][0]["evidence_ids"] = [r["id"] for r in evidence]
        prior = {"analysis": json.loads(case_output_adapter.restore(json.dumps(answer), base["case_boundary"])),
                 "source_map": base["source_map"], "validation": "structure_scope_sources_checked"}
        views = {"C3": base}
        for stage in ("Deep", "C6"):
            with patch.object(current_followup, "selected_profile", return_value=selected):
                views[stage] = current_followup.build(stage, context, base, {}, previous=prior, prior_id=UUID(int=2000),
                    question_id=context.questions[0].id if stage == "Deep" else None)
        variants[label] = views
        for stage, prepared in views.items():
            assert prepared["ready"], prepared["reason"]
            fmt = (case_output_adapter.output_format(prepared, context, {}) if stage == "C3" else
                   case_followup_output.deep_format(prepared) if stage == "Deep" else
                   case_followup_output.final_format(prepared, context, {"state": "not_selected", "result_id": None}))
            save(HERE / "synthetic" / label / (stage + "-model-input.txt"), full_text(prepared))
            save(HERE / "synthetic" / label / (stage + "-request-preview.json"),
                 {"messages": prepared["messages"], "response_format": fmt})
            selected_rows = [r for r in rows(prepared, stage) if r["ref"]["id"] in identities]
            save(HERE / "synthetic" / label / (stage + "-selection.json"), {
                "records": selected_rows, "source_map": prepared["source_map"],
                "omissions": prepared["omissions"], "case_boundary": prepared["case_boundary"]})
            lines = prepared["messages"][1]["content"].splitlines()
            save(HERE / "synthetic" / label / (stage + "-tool-material.txt"),
                 "\n".join(line for line in lines if any(line.startswith("[" + r["id"] + "]") for r in selected_rows)) + "\n")
positive_checks = []


def dependency_identity(items):
    normalized = copy.deepcopy(items)
    for item in normalized:
        # The synthetic predecessor is built from each view. Its presentation
        # fingerprint changes, but its real reference and visible target do not.
        item["original_source"].pop("visible_value_sha256", None)
    return normalized


for stage in ("C3", "Deep", "C6"):
    before, after = variants["before"][stage], variants["after"][stage]
    changed = []
    for old, new in zip(rows(before, stage), rows(after, stage), strict=True):
        assert {k: v for k, v in old.items() if k != "value"} == {k: v for k, v in new.items() if k != "value"}
        if old["value"] != new["value"]:
            assert old["ref"]["id"] in identities and old["ref"]["source_path"]
            old_value = copy.deepcopy(old["value"])
            old_value.pop("match_basis")
            record = old_value["record"]
            for key in ("profile_id", "imported_at", "imported_at_status", "imported_at_raw_sha256"):
                record.pop(key, None)
            for key, known in (("confidence_provenance", "stored_score_calculation_unverified"),
                               ("score_provenance", "stored_prior_analysis_calculation_unverified")):
                if record.get(key) == known:
                    record.pop(key)
            assert new["value"] == old_value
            changed.append(new["id"])
    assert len(changed) == 5
    assert before["source_map"].keys() == after["source_map"].keys()
    for sid, source in before["source_map"].items():
        assert {k: v for k, v in source.items() if k != "visible_value_sha256"} == {
            k: v for k, v in after["source_map"][sid].items() if k != "visible_value_sha256"}
    if stage != "C3":
        assert dependency_identity(before["followup_boundary"]["dependencies"]) == dependency_identity(
            after["followup_boundary"]["dependencies"])
        assert before["followup_boundary"]["query_facts"] == after["followup_boundary"]["query_facts"]
    positive_checks.append({"stage": stage, "changed_result_rows": changed,
        "record_count": len(rows(after, stage)), "business_values_refs_roles_scope_and_dependencies_preserved": True,
        "before_message_characters": [len(m["content"]) for m in before["messages"]],
        "after_message_characters": [len(m["content"]) for m in after["messages"]],
        "dependencies_before": before.get("followup_boundary", {}).get("dependencies", []),
        "dependencies_after": after.get("followup_boundary", {}).get("dependencies", [])})
assert synthetic == original_synthetic
original_hashes = read(HERE / "source-files.json")
assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in original_hashes.items())
save(HERE / "verification.json", {"status": "passed_offline", "source_run_id": run_id,
    "before_profile": old_profile.identity, "after_profile": profile.identity,
    "recorded": checks, "synthetic_positive_examples": positive_checks,
    "original_files_unchanged": len(original_hashes), "new_model_calls": 0, "database_calls": 0, "new_runs": 0,
    "preview_not_dispatched": True, "model_quality": "NOT_PASSED_UNCHANGED"})
print(json.dumps({"recorded": checks, "synthetic": positive_checks}, ensure_ascii=False))
