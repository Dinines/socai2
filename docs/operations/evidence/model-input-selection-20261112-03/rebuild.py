"""Offline I request preview from a saved snapshot; no model or database calls."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
config = json.loads((FOLDER / "config.json").read_text())
sys.path.insert(0, str(ROOT / "services/api"))
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import incident_model_boundary, incident_output_adapter
from app.socai2.baseline_store import digest
from app.socai2.incident_query_receipts import reference_roles
from app.socai2.runtime_policy import active_policy
from app.socai2.stage_results import validate_refs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(name, value):
    path = FOLDER / name
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == text, "do_not_overwrite_different_evidence"
    else:
        path.write_text(text)


snapshot = ROOT / config["snapshot"]
data = json.loads(snapshot.read_text())
before = json.loads((FOLDER / "before.json").read_text())
original_hash = digest(data)
assert original_hash == before["source_sha256"]
run = next(row for row in data["runs"] if row["id"] == config["run_id"])
source = next(a["content_json"] for a in data["artifacts"] if a["id"] == run["input_artifact_id"])
policy = active_policy()
messages, sources, model_data, prepared = incident_model_boundary.build(
    source, run["input_artifact_id"], policy.incident_io, execution_time=run["started_at"])
assert model_data["omission_details"] == before["guard_omissions"]
assert model_data["program_facts"] == before["program_facts"]
assert set(sources) <= set(before["source_map"])
for sid, entry in sources.items():
    for key in ("ref", "alert_ids"):
        assert entry[key] == before["source_map"][sid][key]
validate_refs({"source_refs": [row["ref"] for row in sources.values()]}, source,
              run["input_artifact_id"], reference_roles(source))
for record in prepared["records"]:
    assert all(sources[sid]["visible_value_sha256"] == digest(record["value"]) for sid in record["source_ids"])
    if record.get("shared_analysis"):
        assert any(r["value"] == record["value"] and not r["history"]
                   and list(r["header"][0]) == record["shared_analysis"] for r in prepared["records"])
for member in source["members"]:
    valid = source["triage_validation"].get(member["alert"]["id"], {})
    if valid.get("usable"):
        assert member["triage"]["rationale"] in prepared["user"]
assert digest(data) == original_hash

write_once("I-model-input.txt", prepared["user"])
write_once("I-request-preview.json", {"kind": "offline_request_preview_not_dispatched", "messages": messages,
    "response_format": {"type": "json_schema", "json_schema": {"name": "socai2_incident_boundary", "strict": True,
        "schema": incident_output_adapter.candidate_schema(prepared)}}})
write_once("I-selection.json", {"source_map": sources, "records": prepared["records"],
    "boundary": prepared["boundary"], "guard_omissions": model_data["omission_details"],
    "required_history_rows": model_data["required_history_rows"]})
summary = {"kind": "offline_I_input_selection_not_dispatched", "model_calls": 0, "database_writes": 0,
    "source_snapshot": config["snapshot"], "run_id": run["id"], "snapshot_sha256": original_hash,
    "snapshot_file_sha256": sha(snapshot), "profile_sha256": policy.incident_io.sha256,
    "before_characters": before["characters"], "after_characters": len(prepared["user"]),
    "lines": len(prepared["user"].splitlines()), "before_sources": len(before["source_map"]),
    "visible_sources": len(sources), "visible_business_blocks": len(prepared["records"]),
    "history_groups": len({r["history"] for r in prepared["records"] if r["history"]}),
    "selection_reasons": dict(Counter(row["reason"] for row in prepared["omissions"])),
    "original_snapshot_unchanged": True, "input_guard_and_program_facts_unchanged": True,
    "source_identity_role_path_and_member_scope_preserved": True,
    "all_selected_original_references_validate": True, "valid_A_rationales_preserved_verbatim": True,
    "files_sha256": {name: sha(FOLDER / name) for name in ("I-model-input.txt", "I-request-preview.json", "I-selection.json")},
    "code_sha256": {name: sha(ROOT / "services/api/app/socai2" / name) for name in (
        "incident-input-v1.json", "incident_input_text.py", "incident_model_boundary.py", "incident_output_adapter.py")}}
write_once("rebuild-summary.json", summary)
print(json.dumps({key: summary[key] for key in ("before_characters", "after_characters", "lines", "visible_sources",
                                               "history_groups", "selection_reasons")}, ensure_ascii=False))
