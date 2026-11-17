"""Offline previews from a sealed batch; no model, network, database or old writes."""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).resolve().parent
config = json.loads((FOLDER / "config.json").read_text())
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import case_followup_output, case_model_boundary, case_output_adapter
from app.socai2.baseline_analysis_contract import AnalysisRejected
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.baseline_store import encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path = FOLDER / name
    if path.exists():
        assert path.read_text() == raw, "do_not_overwrite_evidence: " + name
    else:
        path.write_text(raw)


flow = ROOT / config["flow"]
old_hashes = {str(p.relative_to(ROOT)): sha(p) for p in flow.rglob("*") if p.is_file()}
db = read(ROOT / config["snapshot"])
arts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == config["run_id"]}
run = next(r for r in db["runs"] if r["id"] == config["run_id"])
c1 = next(a for a in arts.values() if a["schema_version"] == "socai2.baseline-context.v1")
old_base = next(a["content_json"] for a in arts.values() if a["schema_version"] == "socai2.case-model-input.v1")
raw = copy.deepcopy(c1["content_json"])
raw["case_input_profile"] = active_policy().case_io.identity
context = Context.model_validate(raw)  # Only this offline copy uses the current profile.
materials = {aid: next(m for m in db["alert_materials"] if m["id"] == row.material["id"])
             for aid, row in context.alerts.items() if row.material}
c2 = next(a["content_json"] for a in arts.values() if a["kind"] == "source_snapshot"
          and a["schema_version"] == "socai2.baseline-enrichment.v1")
enrichment = [(row["artifact_id"], arts[row["artifact_id"]]["content_json"], row) for row in c2["sources"]]
prepared = case_model_boundary.build(context, c1["id"], enrichment, old_base["source_state_ledger"], materials,
    execution_time=run["started_at"], run_id=run["id"])
assert prepared["ready"], prepared["reason"]
messages, _ = case_model_boundary.messages(prepared, context, [])
old_call = read(flow / "Case/calls/call-1-intent.json")["body"]
old_request = next(a["content_json"] for a in arts.values() if a["kind"] == "model_request"
                   and a["content_json"]["payload"]["body"] == old_call)
assert old_request["payload"]["binding_map"] == {}
gateway = SimpleNamespace(provider=old_request["provider"], schema_profile=old_request["schema_profile"])
body = compact_execution_wire(prepare_request(gateway, {**old_call, "messages": messages,
    "response_format": case_output_adapter.output_format(prepared, context, {})}))
old_rows = {r["id"]: r for r in old_base["input_ledger"]["records"]}
new_rows = {r["id"]: r for r in prepared["input_ledger"]["records"]}
removed = sorted(old_rows.keys() - new_rows.keys())
assert removed == ["N3_S130", "N3_S186"]
for sid, row in new_rows.items():
    assert encoded(row) == encoded(old_rows[sid]), (sid, "retained_row_changed")
    assert encoded(prepared["source_map"][sid]) == encoded(old_base["source_map"][sid])
assert new_rows["N3_S239"]["alert_ids"] == []
assert new_rows["N3_S239"]["membership_basis"] == "history_record_outside_case"
assert "N3_S238" in new_rows  # Explicit I dependency, not an optional catalog wrapper.
assert new_rows["N3_S238"]["alert_ids"] == []
assert "｜案件外历史｜" in messages[1]["content"]
assert prepared["input_ledger"]["program_facts"] == old_base["input_ledger"]["program_facts"]
save("C3-model-input.txt", messages[1]["content"])
save("C3-request-preview.json", body)
save("C3-selection.json", {"source_map": prepared["source_map"], "input_ledger": prepared["input_ledger"]})

corrections = []
for stage, first, second in (("C3", 1, 2), ("C6", 5, 6)):
    request = read(flow / "Case/calls" / f"call-{first}-intent.json")["body"]
    old_correction = read(flow / "Case/calls" / f"call-{second}-intent.json")["body"]
    payload = next(a["content_json"]["payload"] for a in arts.values() if a["kind"] == "model_request"
                   and a["content_json"]["payload"]["body"] == request)
    content = read(flow / "Case/calls" / f"call-{first}-receipt.json")["raw"]["choices"][0]["message"]["content"]
    assert old_correction["messages"][-2] == {"role": "assistant", "content": content}
    if stage == "C3":
        review = case_output_adapter.CaseReview(old_base, context, {})
        parser = lambda value: case_output_adapter.parse(value, old_base, context, {})
    else:
        final = copy.deepcopy(payload)
        final["coverage"] = copy.deepcopy(old_base["coverage"])
        for aid, value in final["coverage"].items():
            value["included"] = sum(aid in r["alert_ids"] for r in final["followup_boundary"]["records"])
        comparison = {"state": "initial", "result_id": None}
        review = case_followup_output.FinalReview(final, context, comparison)
        parser = lambda value, prepared=final, compare=comparison: case_followup_output.parse_final(value, prepared, context, compare)
    feedback = review.feedback(content)
    assert feedback and not feedback["allowed_sources"] and not feedback["local_findings"]
    preview = copy.deepcopy(old_correction)
    preview["messages"][-1]["content"] = encoded(feedback).decode()
    assert preview["messages"][:-1] == old_correction["messages"][:-1]
    rejections = []
    for number in (first, second):
        original = read(flow / "Case/calls" / f"call-{number}-receipt.json")["raw"]["choices"][0]["message"]["content"]
        try:
            parser(original)
        except AnalysisRejected as exc:
            rejections.append({"call": number, "reason": str(exc)})
        else:
            raise AssertionError("old_failure_was_accepted")
    save(stage + "-correction-feedback.json", feedback)
    save(stage + "-correction-model-input.txt", preview["messages"][-1]["content"])
    save(stage + "-correction-request-preview.json", preview)
    corrections.append({"stage": stage, "before_characters": len(old_correction["messages"][-1]["content"]),
        "after_characters": len(preview["messages"][-1]["content"]), "errors": feedback["errors"],
        "original_requests_and_answers_unchanged": True, "old_answers_still_rejected": rejections,
        "context": "replay_feedback_on_original_frozen_input_not_the_new_C3_projection"})

assert old_hashes == {str(p.relative_to(ROOT)): sha(p) for p in flow.rglob("*") if p.is_file()}
source_files = ["services/api/app/socai2/" + name for name in (
    "case_c3_input_selection.py", "case_input_text.py", "case_citation_feedback.py", "case-input-v1.json")]
source_files += ["services/api/tests/" + name for name in (
    "test_socai2_case_model_boundary.py", "test_socai2_case_scope_recovery.py", "test_socai2_case_followup_boundary.py")]
source_files += [str(Path(__file__).relative_to(ROOT)), config["policy"]]
summary = {"kind": "offline_input_and_citation_feedback_preview", "model_calls": 0, "network_calls": 0,
    "database_writes": 0, "old_run_id": config["run_id"], "old_file_hashes": old_hashes,
    "old_files_unchanged": True, "profile_rebound_only_in_offline_copy": True,
    "preview_profile": active_policy().case_io.identity, "C3": {"before_characters": len(old_call["messages"][1]["content"]),
        "after_characters": len(messages[1]["content"]), "removed_sources": removed,
        "retained_rows_and_sources_equal": True, "source_count": len(new_rows),
        "necessary_prior_analysis_and_original_scope_preserved": True, "program_facts_unchanged": True},
    "corrections": corrections, "source_sha256": {p: sha(ROOT / p) for p in source_files},
    "limits": ["not_dispatched_not_a_new_Run", "old_results_remain_rejected_partial_null_unadopted",
               "no_claim_of_model_correction_success_or_semantic_quality", "no_HTTP_or_database_contract_change"]}
save("summary.json", summary)
print(json.dumps({"C3": summary["C3"], "corrections": corrections, "model_calls": 0}, ensure_ascii=False))
