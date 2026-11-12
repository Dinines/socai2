"""Preview C3 from frozen inputs, without model/HTTP/database calls or old writes."""
import copy
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
config = json.loads((FOLDER / "config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import case_model_boundary as boundary, case_output_adapter as adapter
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy


def save(name, value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path = FOLDER / name
    if path.exists():
        assert path.read_text() == text, "do_not_overwrite_different_evidence: " + name
    else:
        path.write_text(text)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


snapshot_path = ROOT / config["snapshot"]
snapshot = json.loads(snapshot_path.read_text())
before = json.loads((FOLDER / "before.json").read_text())
assert digest(snapshot) == before["snapshot_sha256"]
policy = active_policy()
arts = {a["id"]: a for a in snapshot["artifacts"] if a["run_id"] == config["run_id"]}
run = next(r for r in snapshot["runs"] if r["id"] == config["run_id"])
c1 = next(a for a in arts.values() if a["schema_version"] == "socai2.baseline-context.v1")
old_base = next(a for a in arts.values() if a["schema_version"] == "socai2.case-model-input.v1")
old_request = next(a["content_json"] for a in arts.values() if a["kind"] == "model_request"
                   and a["content_json"]["payload"].get("input_view_id") == old_base["id"])
assert old_request["payload"]["binding_map"] == {}

# Explicit offline-only rebind: the live drift check is unchanged and tested.
raw = copy.deepcopy(c1["content_json"])
raw["case_input_profile"] = policy.case_io.identity
context = Context.model_validate(raw)
materials = {aid: next(m for m in snapshot["alert_materials"] if m["id"] == item.material["id"])
             for aid, item in context.alerts.items() if item.material}
enrichment = [(a["id"], a["content_json"], {}) for a in arts.values() if a["kind"] == "tool_response"]
prepared = boundary.build(context, c1["id"], enrichment, old_base["content_json"]["source_state_ledger"], materials,
                          execution_time=run["started_at"], run_id=run["id"])
assert prepared["ready"], prepared["reason"]
messages, sources = boundary.messages(prepared, context, [])
gateway = SimpleNamespace(provider=old_request["provider"], schema_profile=old_request["schema_profile"])
body = compact_execution_wire(prepare_request(gateway, {
    "model": old_request["payload"]["body"]["model"], "messages": messages,
    "max_tokens": policy.model.output_tokens["C3"], "temperature": 0,
    "response_format": adapter.output_format(prepared, context, {})}))
assert body["messages"] == messages

# All retained IDs keep their original role, path, record subject and query scope.
old_sources = {encoded(s["ref"]): s for s in before["source_map"].values()}
for source in sources.values():
    previous = old_sources[encoded(source["ref"])]
    assert digest({k: v for k, v in source.items() if k != "visible_value_sha256"}) == digest(
        {k: v for k, v in previous.items() if k != "visible_value_sha256"})
ledger = prepared["input_ledger"]
assert ledger["program_facts"] == before["program_facts"]
guards = [o for o in prepared["omissions"] if o["reason"] == "input_guard"]
assert guards == before["guard_omissions"]
payloads = {c1["id"]: c1["content_json"], **{a["id"]: a["content_json"] for a in arts.values()
                                            if a["kind"] == "tool_response"}}
material_by_id = {m["id"]: m for m in materials.values()}
for row in ledger["records"]:
    ref = row["ref"]
    actual = material_by_id[ref["id"]] if ref["type"] == "alert_material" else payloads[ref["id"]]
    path = ref.get("source_path")
    for part in (path[2:].split(".") if path else []):
        actual = actual[int(part)] if isinstance(actual, list) else actual[part]
    if ref["role"] == "execution_receipt":
        assert all(actual[k] == row["original_value"][k] for k in ("tool_name", "state", "returned_rows"))
    else:
        assert actual == row["original_value"]
    if row["block"] == "triage":
        assert row["value"]["rationale"] == row["original_value"]["rationale"]
    if row.get("knowledge") and row["knowledge"]["part"] == "card" and "content" in row["value"]["record"]:
        assert row["value"]["record"]["content"] == row["original_value"]["record"]["content"]

shared = copy.deepcopy(policy.case_io.config)
shared.pop("c3_input_selection")
shared_sha = hashlib.sha256((json.dumps(shared, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
assert shared_sha == before["preview_profile"]["sha256"]
assert policy.case_io.identity["business_sha256"] == before["preview_profile"]["business_sha256"]
assert digest(json.loads(snapshot_path.read_text())) == before["snapshot_sha256"]

save("C3-model-input.txt", messages[1]["content"])
save("C3-tools.txt", messages[2]["content"])
save("C3-request-preview.json", body)
save("C3-selection.json", {"profile": policy.case_io.identity, "source_map": sources,
     "input_ledger": ledger, "tool_presentation": prepared["tool_presentation"]})
source_files = ["services/api/app/socai2/" + name for name in (
    "case_c3_input_selection.py", "case_input_text.py", "case_model_boundary.py", "case-input-v1.json")]
source_files += ["services/api/tests/test_socai2_case_model_boundary.py", str((FOLDER / "rebuild.py").relative_to(ROOT))]
summary = {
    "kind": "offline_C3_input_preview_not_dispatched", "model_calls": 0, "database_writes": 0,
    "snapshot": config["snapshot"], "snapshot_sha256": before["snapshot_sha256"],
    "frozen_run_id": config["run_id"], "original_frozen_profile": c1["content_json"]["case_input_profile"],
    "preview_profile": policy.case_io.identity, "profile_rebound_only_in_offline_copy": True,
    "before_user_characters": before["user_characters"], "user_characters": len(messages[1]["content"]),
    "user_lines": len(messages[1]["content"].splitlines()), "before_tool_characters": before["tool_characters"],
    "tool_characters": len(messages[2]["content"]), "system_characters": len(messages[0]["content"]),
    "wire_json_characters": len(encoded(body).decode()), "source_count": len(sources), "group_count": ledger["group_count"],
    "omission_reasons": dict(Counter(o["reason"] for o in prepared["omissions"])),
    "retained_references_resolve_originals": True, "retained_source_scope_and_metadata_unchanged": True,
    "original_guards_unchanged": True, "full_program_facts_unchanged": True,
    "prior_rationale_and_selected_knowledge_content_unchanged": True,
    "shared_case_config_without_c3_selector_sha256": shared_sha,
    "shared_case_config_matches_before": True, "shared_business_config_unchanged": True,
    "source_files": {p: file_sha(ROOT / p) for p in source_files},
    "files": {name: file_sha(FOLDER / name) for name in (
        "C3-model-input.txt", "C3-tools.txt", "C3-request-preview.json", "C3-selection.json")},
    "limits": ["no_new_model_or_storage_acceptance", "not_a_model_quality_result",
               "technical_knowledge_chunks_remain_original_prose_not_reconstructed_documents",
               "Deep_and_C6_templates_not_changed"]}
save("rebuild-summary.json", summary)
print(json.dumps({k: summary[k] for k in ("user_characters", "tool_characters", "source_count", "group_count")}, ensure_ascii=False))
