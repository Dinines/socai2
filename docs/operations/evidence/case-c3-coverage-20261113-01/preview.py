"""Offline C3 before/after projection; never resumes the sealed source Run."""
import copy
import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / "deploy/local-investigation/investigation-policy-case-v1.toml")
from app.socai2 import case_model_boundary as c3
from app.socai2 import case_output_adapter as output
from app.socai2.baseline_context import Context
from app.socai2.baseline_enrichment import citation_roles
from app.socai2.runtime_policy import active_policy


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")


source = ROOT / "docs/operations/evidence/fixed-investigation-20261113-09/flow/R01"
db = read(source / "export/database.json")
rid = read(source / "start-request.json")["run_id"]
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == rid}
context_artifact = next(a for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
frozen = Context.model_validate(context_artifact["content_json"])
stored = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == c3.SCHEMA)
c2 = next(a["content_json"] for a in artifacts.values()
          if a["schema_version"] == "socai2.baseline-enrichment.v1" and a["kind"] == "source_snapshot")
enrichment = [(s["artifact_id"], artifacts[s["artifact_id"]]["content_json"],
               citation_roles(artifacts[s["artifact_id"]]["content_json"])) for s in c2["sources"]]
materials = {aid: next(m for m in db["alert_materials"] if m["id"] == alert.material["id"])
             for aid, alert in frozen.alerts.items() if alert.material}
request = next(a["content_json"]["payload"] for a in artifacts.values()
               if a["kind"] == "model_request" and "followup_boundary" not in a["content_json"]["payload"])
options = [{"binding_id": alias, "tool_name": b["tool_name"], "hostname": b["hostname"],
            "alert_ids": b["alert_ids"], "object_keys": sorted({o["object_key"] for o in b["objects"]})}
           for alias, b in request["binding_map"].items()]
profile = active_policy().case_io
old_raw = (HERE / "before-source/services/api/app/socai2/case-input-v1.json").read_bytes()
old = replace(profile, raw=old_raw, sha256=hashlib.sha256(old_raw).hexdigest())
views = {}
for label, selected in (("before", old), ("after", profile)):
    context = frozen.model_copy(update={"case_input_profile": selected.identity})
    with patch.object(c3, "selected_profile", return_value=selected):
        prepared = c3.build(context, context_artifact["id"], enrichment, stored["source_state_ledger"], materials,
            execution_time=stored["input_ledger"]["program_facts"]["execution_started_at"], run_id=rid)
        assert prepared["ready"], prepared["reason"]
        messages, _ = c3.messages(prepared, context, options)
    wire = copy.deepcopy(request["body"])
    wire.update(messages=messages, response_format=output.output_format(prepared, context, request["binding_map"]))
    save(label + "/C3-request-preview.json", wire)
    save(label + "/C3-model-input.txt", "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages) + "\n")
    views[label] = prepared

before, after = views["before"], views["after"]
for key in ("source_map", "coverage", "omissions"):
    assert before[key] == after[key], key
assert before["input_ledger"]["records"] == after["input_ledger"]["records"]
assert "coverage：" in before["messages"][1]["content"] and "coverage：" not in after["messages"][1]["content"]
save("after/program-coverage-facts.json", after["case_boundary"]["coverage_facts"])
# Original v2 C3 answer is checked only against its original frozen boundary.
raw = read(source / "calls/call-1-receipt.json")["raw"]["choices"][0]["message"]["content"]
parsed = output.parse(raw, stored, frozen, request["binding_map"])
assert len(parsed.questions) == 6
preserved = read(HERE / "original-sha256.json")
assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha for p, sha in preserved.items())
save("preview-summary.json", {"offline_only": True, "new_model_or_database_calls": 0,
    "source_run_id": rid, "records_unchanged": len(after["input_ledger"]["records"]),
    "sources_unchanged": len(after["source_map"]), "old_files_unchanged": len(preserved),
    "original_six_question_answer_still_accepted": True,
    "base_message_characters": {k: [len(m["content"]) for m in v["messages"]] for k, v in views.items()},
    "comparison": "Same frozen materials, explicitly rebound offline profiles; not actual model execution or controlled model A/B."})
print("C3 five-question preview, unchanged facts/references and original six-question answer verified.")
