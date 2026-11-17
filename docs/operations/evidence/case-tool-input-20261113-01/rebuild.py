"""Rebuild full Case model messages from sealed artifacts, without external calls."""
import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
CONFIG = json.loads((HERE / "config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / CONFIG["policy"])
from app.socai2 import case_followup_input as current_followup
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


old_hierarchy, old_followup = old_module("case_input_hierarchy"), old_module("case_followup_input")
profile = active_policy().case_io
old_raw = (HERE / "before-source/services/api/app/socai2/case-input-v1.json").read_bytes()
old_profile = replace(profile, raw=old_raw, sha256=hashlib.sha256(old_raw).hexdigest())
source = ROOT / CONFIG["source_batch"]
db = read(source / "pg-01/database.json")
run_id = CONFIG["source_run_id"]
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == run_id}
context_artifact = next(a for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
frozen_context = Context.model_validate(context_artifact["content_json"])
assert frozen_context.case_input_profile == old_profile.identity
stored_base = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == c3.SCHEMA)
c2 = next(a["content_json"] for a in artifacts.values()
          if a["schema_version"] == "socai2.baseline-enrichment.v1" and a["kind"] == "source_snapshot")
enrichment = [(s["artifact_id"], artifacts[s["artifact_id"]]["content_json"],
               citation_roles(artifacts[s["artifact_id"]]["content_json"])) for s in c2["sources"]]
materials = {aid: next(m for m in db["alert_materials"] if m["id"] == alert.material["id"])
             for aid, alert in frozen_context.alerts.items() if alert.material}


def base_for(selected):
    # Explicit offline profile binding; no existing Run is resumed or modified.
    context = frozen_context.model_copy(update={"case_input_profile": selected.identity})
    with patch.object(c3, "selected_profile", return_value=selected):
        base = c3.build(context, context_artifact["id"], enrichment, stored_base["source_state_ledger"], materials,
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


old_context, before_base = base_for(old_profile)
new_context, after_base = base_for(profile)
checks, counts = [], Counter()
for request in sorted([a for a in artifacts.values() if a["kind"] == "model_request"], key=lambda a: a["captured_at"]):
    actual = request["content_json"]["payload"]
    stage = actual["case_boundary"].get("stage", "C3")
    counts[stage] += 1
    name = stage + (f"-{counts[stage]:02}" if stage == "Deep" else "")
    before = build(request, old_context, before_base, old_profile, old_followup, old_hierarchy)
    after = build(request, new_context, after_base, profile, current_followup, current_hierarchy)
    assert before["ready"] and after["ready"]
    previous = ROOT / CONFIG["previous_scope_batch"] / "after" / (name + "-model-input.txt")
    assert before["messages"][1]["content"] == previous.read_text(), (name, "prior_scope_preview_differs")
    ledger = "input_ledger" if stage == "C3" else "followup_boundary"
    old_rows, new_rows = before[ledger]["records"], after[ledger]["records"]
    assert len(old_rows) == len(new_rows)
    changed = []
    for old, new in zip(old_rows, new_rows, strict=True):
        if old == new:
            continue
        expected = copy.deepcopy(old)
        if old["block"] == "graph":
            expected["value"].pop("limitations")
        else:
            assert {"name", "value", "transform"} <= set(expected["value"])
            expected["value"].pop("transform")
        assert new == expected, (name, new["id"])
        changed.append(new["id"])
    assert before["source_map"].keys() == after["source_map"].keys()
    for sid, row in after["source_map"].items():
        assert {k: v for k, v in row.items() if k != "visible_value_sha256"} == {
            k: v for k, v in before["source_map"][sid].items() if k != "visible_value_sha256"}
    old_boundary, new_boundary = copy.deepcopy(before["case_boundary"]), copy.deepcopy(after["case_boundary"])
    for boundary in (old_boundary, new_boundary):
        boundary.pop("profile")
        if "coverage_facts" in boundary:
            boundary["coverage_facts"].pop("omission_count")
    assert old_boundary == new_boundary
    if stage != "C3":
        assert before["followup_boundary"]["dependencies"] == after["followup_boundary"]["dependencies"]
        assert before["followup_boundary"]["query_facts"] == after["followup_boundary"]["query_facts"]
        assert before["binding_map"] == after["binding_map"]
    if stage != "C6":
        assert before["tool_presentation"]["catalog"] == after["tool_presentation"]["catalog"]
        assert before["tool_presentation"]["capabilities"] == after["tool_presentation"]["capabilities"]
        assert all(word not in after["messages"][2]["content"] for word in ("共同限制", "使用范围=", "schema_version", "可用=true"))
    for label, prepared in (("before", before), ("after", after)):
        wire = copy.deepcopy(actual["body"])
        wire["messages"] = prepared["messages"]
        save(HERE / label / (name + "-request-preview.json"), wire)
        full = "\n\n".join(f"[{i + 1}. {m['role']}]\n{m['content']}" for i, m in enumerate(prepared["messages"])) + "\n"
        save(HERE / label / (name + "-model-input.txt"), full)
    selected = [r for r in new_rows if r["id"] in changed or r["ref"]["role"] == "execution_receipt"]
    lines = after["messages"][1]["content"].splitlines()
    tool_text = [line for line in lines if any(line.startswith("[" + r["id"] + "]") for r in selected)]
    if stage != "C6":
        tool_text.append(after["messages"][2]["content"])
    save(HERE / "after" / (name + "-tool-material.txt"), "\n".join(tool_text) + "\n")
    save(HERE / "after" / (name + "-selection.json"), {"changed_records": [r for r in new_rows if r["id"] in changed],
        "source_map": after["source_map"], "omissions": after["omissions"],
        "tool_presentation": after.get("tool_presentation"), "case_boundary": after["case_boundary"]})
    checks.append({"stage": name, "request_artifact_id": request["id"], "records": len(new_rows),
        "changed_sources": changed, "unchanged_records": len(new_rows) - len(changed),
        "before_message_characters": [len(m["content"]) for m in before["messages"]],
        "after_message_characters": [len(m["content"]) for m in after["messages"]],
        "before_business_body_matches_previous_preview": True,
        "business_values_scopes_references_prose_prior_dependencies_and_tool_choices_preserved": True})
original_hashes = read(HERE / "source-files.json")
assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in original_hashes.items())
save(HERE / "verification.json", {"status": "passed_offline", "source_run_id": run_id,
    "before_profile": old_profile.identity, "after_profile": profile.identity, "checks": checks,
    "original_files_unchanged": len(original_hashes), "new_model_calls": 0, "database_calls": 0, "new_runs": 0,
    "preview_not_dispatched": True, "model_quality": "NOT_PASSED_UNCHANGED",
    "original_requests_and_responses": CONFIG["source_batch"] + "/pg-01/database.json"})
print(json.dumps(checks, ensure_ascii=False))
