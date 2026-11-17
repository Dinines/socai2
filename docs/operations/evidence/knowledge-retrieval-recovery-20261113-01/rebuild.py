"""Offline input preview: new real query, old frozen context and prior answers."""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "services/api")]
config = json.loads((HERE / "config.json").read_text())
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])

from app.socai2 import (
    case_followup_input,
    case_followup_output,
    case_model_boundary,
    case_output_adapter,
)
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / "inputs" / name
    path.parent.mkdir(exist_ok=True)
    body = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        assert path.read_text() == body, "different_offline_evidence: " + name
    else:
        with path.open("x") as file:
            file.write(body)


intent, result = read(HERE / "query-intent.json"), read(HERE / "query-result.json")
assert result["state"] == "completed"
assert all(sha(ROOT / name) == value for name, value in intent["original_flow_sha256"].items())
db = read(ROOT / config["snapshot"])
artifacts = {a["id"]: a for a in db["artifacts"] if a["run_id"] == config["run_id"]
             and isinstance(a["content_json"], dict)}
frozen = next(a for a in artifacts.values() if a["schema_version"] == "socai2.baseline-context.v1")
old_base = next(a["content_json"] for a in artifacts.values() if a["schema_version"] == "socai2.case-model-input.v1")
context_value = copy.deepcopy(frozen["content_json"])
context_value["case_input_profile"] = active_policy().case_io.identity
context = Context.model_validate(context_value)
materials = {aid: next(m for m in db["alert_materials"] if m["id"] == item.material["id"])
             for aid, item in context.alerts.items() if item.material}
enrichment = [(a["id"], a["content_json"], {}) for a in artifacts.values()
              if a["kind"] == "tool_response" and a["content_json"]["tool_name"] != "knowledge"]
preview_id = str(uuid5(NAMESPACE_URL, config["batch"] + ":offline-knowledge-receipt"))
receipt = {"schema_version": "socai2.baseline-enrichment.v1", "tool_name": "knowledge",
    "contract_version": intent["args"]["contract_version"], "actual_args": intent["args"],
    "state": "completed", "rows": result["rows"], "returned_rows": len(result["rows"]),
    "truncated": bool(result["metadata"]["source_truncated_count"]),
    "query_id": "offline-preview:" + preview_id, "error": None, "captured_at": result["captured_at"]}
enrichment.append((preview_id, receipt, {}))
states = copy.deepcopy(old_base["source_state_ledger"])
state = next(s for s in states if s["source"] == "knowledge")
state.update(reason=None, outcome="data" if result["rows"] else "empty", captured_at=result["captured_at"],
             truncated=receipt["truncated"])
run = next(r for r in db["runs"] if r["id"] == config["run_id"])
base = case_model_boundary.build(context, frozen["id"], enrichment, states, materials,
                                execution_time=run["started_at"], run_id=run["id"])
assert base["ready"], base["reason"]
c3_messages, _ = case_model_boundary.messages(base, context, [])
prior = next(a for a in artifacts.values() if a["content_json"]
             and isinstance(a["content_json"], dict) and "analysis" in a["content_json"])
deep_prior = next(a for a in artifacts.values() if isinstance(a["content_json"], dict)
                  and a["content_json"].get("type") == "deep_summary")
common = {"previous": prior["content_json"], "prior_id": prior["id"]}
deep = case_followup_input.build("Deep", context, base, artifacts,
    question_id=deep_prior["content_json"]["question_id"], **common)
final = case_followup_input.build("C6", context, base, artifacts, **common)
assert deep["ready"] and final["ready"], (deep["reason"], final["reason"])
comparison = read((ROOT / config["snapshot"]).parents[1] / "summary.json")["comparison"]
old_request = next(a["content_json"] for a in artifacts.values() if a["kind"] == "model_request")
gateway = SimpleNamespace(provider=old_request["provider"], schema_profile=old_request["schema_profile"])
stages = []
save("knowledge-receipt-preview.json", {"kind": "offline_wrapper_not_saved_artifact",
                                      "preview_id": preview_id, "receipt": receipt})
for name, prepared, messages, fmt in (
    ("C3", base, c3_messages, case_output_adapter.output_format(base, context, {})),
    ("Deep", deep, deep["messages"], case_followup_output.deep_format(deep)),
    ("C6", final, final["messages"], case_followup_output.final_format(final, context, comparison)),
):
    records = prepared["input_ledger"]["records"] if name == "C3" else prepared["followup_boundary"]["records"]
    cards = [r for r in records if r.get("knowledge", {}).get("part") == "card"]
    assert len(cards) == 1
    card = cards[0]
    origins = card["knowledge"]["origins"]
    assert {o["purpose"] for o in origins} == {r["purpose"] for r in result["rows"]}
    assert all(o["ref"]["id"] == preview_id for o in origins)
    assert card["ref"]["role"] == "source_label" and card["ref"]["id"] == preview_id
    assert card["membership_basis"] == "query_binding_only"
    assert set(card["query_alert_ids"]) == {aid for r in result["rows"] for aid in r["query_alert_ids"]}
    original = result["rows"][0]["record"]["content"]
    content = card["value"]["record"]["content"]
    source = json.loads(original)
    assert source["description"] in content
    assert all(v["description"] in content for v in source["x_mitre_mutable_elements"])
    assert messages[1]["content"].count(content) == 1
    assert original not in messages[1]["content"]
    assert "x_mitre_data_component_ref" not in content
    wire = prepare_request(gateway, {"model": old_request["payload"]["body"]["model"], "messages": messages,
        "temperature": 0, "max_tokens": active_policy().model.output_tokens[name], "response_format": fmt})
    if name == "C3":
        wire = compact_execution_wire(wire)
    save(name + "-input-preview.txt", messages[1]["content"])
    save(name + "-request-preview.json", wire)
    save(name + "-selection.json", {"knowledge_cards": cards, "source_map": prepared["source_map"],
                                  "omissions": prepared["omissions"]})
    save(name + "-knowledge-content.txt", content)
    stages.append({"stage": name, "input_characters": len(messages[1]["content"]),
        "knowledge_cards": len(cards), "knowledge_body_characters": len(content),
        "source_id": card["id"], "role": card["ref"]["role"], "original_characters": len(original),
        "purposes": [o["purpose"] for o in origins], "query_alert_ids": card["query_alert_ids"],
        "original_body_preserved_in_receipt": True, "body_occurrences_in_model_view": 1})
assert all(sha(ROOT / name) == value for name, value in intent["original_flow_sha256"].items())
files = [HERE / "rebuild.py", HERE / "query-result.json", ROOT / config["policy"]]
files.extend(p for p in (ROOT / "services/api/app/socai2").glob("*") if p.suffix in {".py", ".json"})
save("summary.json", {"kind": "offline_new_query_with_frozen_context_preview", "stages": stages,
    "generation_calls": 0, "database_writes": 0, "preview_profile": active_policy().case_io.identity,
    "old_context_profile": frozen["content_json"]["case_input_profile"],
    "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
    "prior_C3_artifact_id": prior["id"], "prior_Deep_artifact_id": deep_prior["id"],
    "prior_answers_from_old_failed_run_not_recalculated": True,
    "normal_C6_or_knowledge_quality_acceptance": False,
    "limits": ["explicit_offline_profile_rebind", "preview_receipt_id_not_database_artifact",
               "not_a_new_Run_or_dispatched_model_request", "frozen_prior_answers_predate_new_knowledge"]})
print(json.dumps(stages, ensure_ascii=False))
