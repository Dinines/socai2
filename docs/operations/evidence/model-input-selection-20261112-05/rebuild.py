"""Frozen-input check and explicit new-import fixture preview; no external calls."""
import copy
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).parent
config = json.loads((FOLDER / "config.json").read_text())
sys.path[:0] = [str(ROOT / "services/api"), str(ROOT)]
os.environ["SOCAI2_INVESTIGATION_POLICY"] = str(ROOT / config["policy"])
from app.services.kb_chunking import chunk_text
from app.socai2 import case_followup_input, case_model_boundary, case_output_adapter
from app.socai2.baseline_context import Context
from app.socai2.baseline_execution_schema import compact_execution_wire
from app.socai2.baseline_store import digest, encoded
from app.socai2.knowledge_config import content_hash
from app.socai2.model_protocol import prepare_request
from app.socai2.runtime_policy import active_policy


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path = FOLDER / name
    if path.exists():
        assert path.read_text() == text, "do_not_overwrite_different_evidence: " + name
    else:
        path.write_text(text)


snapshot_path = ROOT / config["snapshot"]
snapshot = json.loads(snapshot_path.read_text())
snapshot_hash = sha(snapshot_path)
corpus = json.loads((ROOT / config["corpus"]).read_text())[0]
full_text = corpus["request"]["content"]
full_value = json.loads(full_text)
# Verify the saved import request against its explicitly recorded original,
# not by joining retrieved fragments that happen to have similar titles.
original_path = Path(corpus["source"]["file"])
assert sha(original_path) == corpus["source"]["file_sha256"]
source = next(o for o in json.loads(original_path.read_text())["objects"] if o["id"] == corpus["source"]["object_id"])
assert source["modified"] == corpus["source"]["object_modified"]
assert full_value == {k: source[k] for k in corpus["source"]["fields"]}
assert sha(FOLDER / "original-kb-chunking.py") == config["original_chunker_sha256"]
spec = importlib.util.spec_from_file_location("original_chunker", FOLDER / "original-kb-chunking.py")
original_chunker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original_chunker)
old_chunks = original_chunker.chunk_text(full_text)
new_chunks = chunk_text(full_text)
assert new_chunks == [full_text]
kb_profile = json.loads((ROOT / config["knowledge_profile"]).read_text())
assert len(full_text) <= kb_profile["max_chunk_characters"]

policy = active_policy()
arts = {a["id"]: a for a in snapshot["artifacts"] if a["run_id"] == config["run_id"]}
run = next(r for r in snapshot["runs"] if r["id"] == config["run_id"])
c1 = next(a for a in arts.values() if a["schema_version"] == "socai2.baseline-context.v1")
old_base = next(a for a in arts.values() if a["schema_version"] == "socai2.case-model-input.v1")
old_request = next(a["content_json"] for a in arts.values() if a["kind"] == "model_request"
                   and a["content_json"]["payload"].get("input_view_id") == old_base["id"])
assert old_request["payload"]["binding_map"] == {}
raw = copy.deepcopy(c1["content_json"])
raw["case_input_profile"] = policy.case_io.identity  # Explicit offline-only profile rebind.
context = Context.model_validate(raw)
materials = {aid: next(m for m in snapshot["alert_materials"] if m["id"] == item.material["id"])
             for aid, item in context.alerts.items() if item.material}
enrichment = [(a["id"], a["content_json"], {}) for a in arts.values() if a["kind"] == "tool_response"]


def build(values):
    result = case_model_boundary.build(context, c1["id"], values, old_base["content_json"]["source_state_ledger"], materials,
                                      execution_time=run["started_at"], run_id=run["id"])
    assert result["ready"], result["reason"]
    return result


frozen = build(enrichment)
assert frozen["messages"][1]["content"] == (FOLDER.parent / "model-input-selection-20261112-04/C3-model-input.txt").read_text()
save("C3-frozen-input-unchanged.txt", frozen["messages"][1]["content"])

# Construct an explicitly synthetic C2 result for a newly imported complete
# document. Old receipts and rows remain untouched; no embeddings are queried.
new_doc_id = str(uuid5(NAMESPACE_URL, FOLDER.name + ":new-document-preview"))
new_receipt_id = str(uuid5(NAMESPACE_URL, FOLDER.name + ":new-receipt-preview"))
preview_enrichment = []
matched, seen_parts, preview_rows = 0, set(), []
for identity, original_body, state in enrichment:
    if original_body["tool_name"] != "knowledge":
        preview_enrichment.append((identity, original_body, state))
        continue
    body = copy.deepcopy(original_body)
    retained, seen = [], set()
    for row in body["rows"]:
        record = row["record"]
        if record.get("source_url") != corpus["request"]["source_url"]:
            retained.append(row)
            continue
        assert record["title"] == corpus["request"]["title"]
        assert record["chunk_total"] == len(old_chunks)
        assert record["content"] == old_chunks[record["chunk_index"]]
        seen_parts.add(record["chunk_index"])
        matched += 1
        key = (row["purpose"], row["object_key"], tuple(row["query_alert_ids"]))
        if key in seen:
            continue
        seen.add(key)
        record.update(id=new_doc_id, content=full_text, chunk_index=0, chunk_total=1,
                      created_at=config["preview_timestamp"], updated_at=config["preview_timestamp"])
        row.update(record_id=new_doc_id, content_sha256=content_hash({**record, "tenant_id": run["tenant_id"]}),
                   similarity=None, match_basis="offline_preview_without_retrieval")
        retained.append(row)
    body.update(rows=retained, returned_rows=len(retained), metadata={"kind": config["kind"], "retrieval_executed": False})
    preview_rows = retained
    preview_enrichment.append((new_receipt_id, body, {}))
assert matched and seen_parts == set(range(len(old_chunks)))
save("new-import-fixture.json", {"kind": config["kind"], "not_imported_or_indexed": True,
     "original_import_request": corpus["request"], "new_document_id_is_synthetic": new_doc_id,
     "new_receipt_id_is_synthetic": new_receipt_id, "rows": preview_rows})
prepared = build(preview_enrichment)
messages, source_map = case_model_boundary.messages(prepared, context, [])
gateway = SimpleNamespace(provider=old_request["provider"], schema_profile=old_request["schema_profile"])
body = compact_execution_wire(prepare_request(gateway, {
    "model": old_request["payload"]["body"]["model"], "messages": messages,
    "max_tokens": policy.model.output_tokens["C3"], "temperature": 0,
    "response_format": case_output_adapter.output_format(prepared, context, {})}))
save("C3-new-import-preview.txt", messages[1]["content"])
save("C3-new-import-request-preview.json", body)
save("C3-selection.json", {"kind": config["kind"], "source_map": source_map, "ledger": prepared["input_ledger"]})
knowledge = next(r for r in prepared["input_ledger"]["records"]
                 if r.get("knowledge", {}).get("part") == "card" and r["value"].get("record", {}).get("content"))
content = knowledge["value"]["record"]["content"]
assert knowledge["original_value"]["record"]["content"] == full_text
assert full_value["description"] in content
assert all(item["description"] in content for item in full_value["x_mitre_mutable_elements"])
assert "x_mitre_data_component_ref" not in content
save("knowledge-model-content.txt", content)

stages = {}
for stage in ("Deep", "C6"):
    kwargs = {"question_id": next(q.id for q in context.questions if q.id != "coverage")} if stage == "Deep" else {}
    following = case_followup_input.build(stage, context, prepared, {}, **kwargs)
    assert following["ready"], following["reason"]
    record = next(r for r in following["followup_boundary"]["records"]
                  if r.get("knowledge", {}).get("identity") == knowledge["knowledge"]["identity"])
    assert record["value"]["record"]["content"] == content
    assert record["ref"] == knowledge["ref"]
    assert following["source_map"][record["id"]]["knowledge"] == source_map[knowledge["id"]]["knowledge"]
    stages[stage] = {"kind": "offline_new_import_no_prior_model_analysis", "source": following["source_map"][record["id"]],
                     "knowledge_content": content, "stage_ready_is_not_model_acceptance": following["ready"]}
save("Deep-C6-knowledge-consumption.json", stages)
assert sha(snapshot_path) == snapshot_hash

files = ["services/api/app/services/kb_chunking.py", *["services/api/app/socai2/" + name for name in (
    "knowledge_content.py", "case_c3_input_selection.py", "case_followup_input.py", "case-input-v1.json")],
    *["services/api/tests/" + name for name in ("test_kb_chunker.py", "test_case_purpose_knowledge.py",
                                              "test_socai2_case_followup_boundary.py")],
    str((FOLDER / "rebuild.py").relative_to(ROOT))]
summary = {"kind": config["kind"], "http_calls": 0, "database_writes": 0, "embedding_calls": 0, "model_calls": 0,
    "snapshot_sha256": snapshot_hash, "full_source_verified": corpus["source"],
    "old_chunks_exactly_match_frozen_rows": True, "old_chunk_count": len(old_chunks), "new_chunk_count": len(new_chunks),
    "original_characters": len(full_text), "selected_model_content_characters": len(content),
    "index_max_characters_unchanged": kb_profile["max_chunk_characters"],
    "old_frozen_C3_body_unchanged": True, "old_frozen_C3_characters": len(frozen["messages"][1]["content"]),
    "new_import_C3_preview_characters": len(messages[1]["content"]), "preview_sources": len(source_map),
    "shared_content_and_references_match_in_C3_Deep_C6": True,
    "original_frozen_profile": c1["content_json"]["case_input_profile"], "preview_profile": policy.case_io.identity,
    "profile_rebound_only_in_offline_copy": True,
    "http_contract_and_database_schema_changed": False,
    "deployment_note": "New ingestion changes chunk counts; old JSON fragments need a separately authorized new import/index, never an in-place rewrite.",
    "source_files": {name: sha(ROOT / name) for name in files},
    "files": {name: sha(FOLDER / name) for name in (
        "config.json", "original-kb-chunking.py", "C3-frozen-input-unchanged.txt", "new-import-fixture.json",
        "C3-new-import-preview.txt", "C3-new-import-request-preview.json", "C3-selection.json",
        "knowledge-model-content.txt", "Deep-C6-knowledge-consumption.json")},
    "limits": ["offline fixture is not a real import/index/retrieval or Run", "no new save/read model-result validation",
               "unsupported structured formats and existing fragments are not semantically rewritten", "full Deep/C6 cleanup still pending"]}
save("rebuild-summary.json", summary)
print(json.dumps({k: summary[k] for k in ("old_chunk_count", "new_chunk_count", "selected_model_content_characters",
                                        "old_frozen_C3_characters", "new_import_C3_preview_characters")}, ensure_ascii=False))
