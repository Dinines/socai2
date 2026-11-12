"""Rebuild three frozen A inputs offline; never dispatch or change originals."""
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
sys.path.insert(0, str(ROOT / "services/api"))
config = json.loads((ROOT / "docs/operations/evidence/fixed-investigation-20261112-04/config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import alert_model_boundary, alert_output_adapter
from app.socai2.baseline_store import digest
from app.socai2.runtime_policy import active_policy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path, value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == text, "do_not_overwrite_different_evidence"
    else:
        path.write_text(text)


snapshot = ROOT / config["output"] / "export/database.json"
data = json.loads(snapshot.read_text())
before = json.loads((FOLDER / "before.json").read_text())
original_hash = digest(data)
assert original_hash == before["snapshot_sha256"]
artifacts = {row["id"]: row for row in data["artifacts"]}
policy = active_policy()
summary = {"kind": "offline_A_input_selection_not_dispatched", "model_calls": 0, "database_writes": 0,
           "source_snapshot": str(snapshot.relative_to(ROOT)), "snapshot_sha256": original_hash,
           "snapshot_file_sha256": sha(snapshot), "profile_sha256": policy.alert_io.sha256, "runs": {}}

for rid, previous in before["runs"].items():
    run = next(row for row in data["runs"] if row["id"] == rid)
    source = artifacts[run["input_artifact_id"]]["content_json"]
    queries = [(a["id"], a["content_json"]) for a in data["artifacts"]
               if a["run_id"] == rid and a["kind"] == "tool_response"]
    messages, sources, model_data, prepared = alert_model_boundary.build(
        source, run["input_artifact_id"], queries, policy.alert_io, execution_time=run["started_at"])
    assert model_data["omission_details"] == previous["guard_omissions"]
    assert set(sources) <= set(previous["source_map"])
    for sid, entry in sources.items():
        assert entry["ref"] == previous["source_map"][sid]["ref"]
        assert entry["visible_value_sha256"] == digest(prepared["selected_values"][sid])
    user = prepared["user"]
    name = rid + "-after.txt"
    write_once(FOLDER / name, user)
    write_once(FOLDER / (rid + "-request-preview.json"), {
        "kind": "offline_request_preview_not_dispatched", "messages": messages,
        "response_format": alert_output_adapter.schema(sources)})
    write_once(FOLDER / (rid + "-selection.json"), {
        "source_map": sources, "selected_values": prepared["selected_values"],
        "boundary": prepared["boundary"], "guard_omissions": model_data["omission_details"]})
    summary["runs"][rid] = {
        "title": previous["title"], "before_characters": previous["characters"], "after_characters": len(user),
        "visible_source_count": len(sources), "file": name, "sha256": sha(FOLDER / name),
        "selection_reasons": dict(Counter(row["reason"] for row in prepared["omissions"])),
        "selected_sources_keep_original_identity_role_and_path": True, "input_guard_unchanged": True}

assert digest(data) == original_hash
assert sha(snapshot) == summary["snapshot_file_sha256"]
summary["original_snapshot_unchanged"] = True
summary["code_sha256"] = {name: sha(ROOT / "services/api/app/socai2" / name) for name in
                          ("alert_input_text.py", "alert-input-v1.json", "alert_model_boundary.py", "alert_output_adapter.py")}
write_once(FOLDER / "rebuild-summary.json", summary)
print(json.dumps({rid: {k: row[k] for k in ("before_characters", "after_characters", "visible_source_count")}
                  for rid, row in summary["runs"].items()}, ensure_ascii=False))
