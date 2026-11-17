"""Verify the saved receipts from this single real knowledge-source preparation."""
import hashlib
import json
from pathlib import Path

folder = Path(__file__).resolve().parent


def read(name):
    return json.loads((folder / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


cfg, expected, corpus = (read(n) for n in ("runtime.json", "expected.json", "knowledge-documents.json"))
names = ["knowledge-ingest_K1-01.json", "knowledge-ingest_K2-01.json", "knowledge-readback-03.json",
         "knowledge-index-01.json", "knowledge-retrieve-01.json"]
receipts = {n: read(n) for n in names}
for receipt in receipts.values():
    assert receipt["status"] == "passed" and receipt["returncode"] == 0
    result = receipt["result"]
    assert result["state"] == "passed" and result["generation_calls"] == 0
    assert result["profile_sha256"] == cfg["knowledge_profile_sha256"]
    assert result["identity"]["database"] == cfg["database"] and result["identity"]["ssl"]
assert digest(folder / "knowledge-profile.json") == cfg["knowledge_profile_sha256"]
saved = receipts["knowledge-readback-03.json"]["result"]
assert saved["identity"]["role"] == cfg["reader"] and saved["identity"]["readonly"] == "on"
by_id = {d["row"]["id"]: d for d in saved["documents"]}
assert len(by_id) == 2
doc_ids = {}
for item in corpus["documents"]:
    imported = receipts["knowledge-ingest_" + item["logical_id"] + "-01.json"]["result"]
    assert imported["identity"]["role"] == cfg["writer"] and len(imported["documents"]) == 1
    doc_id = imported["documents"][0]["id"]
    row = by_id[doc_id]["row"]
    assert row["chunk_index"] == 0 and row["chunk_total"] == 1
    assert all(row[k] == item["request"][k] for k in ("title", "doc_kind", "source_url", "tags", "content"))
    doc_ids[item["logical_id"]] = doc_id
indexed = receipts["knowledge-index-01.json"]["result"]["index"]
assert indexed["state"] == "completed" and indexed["collection"] == cfg["knowledge_collection"]
assert {p["doc_id"] for p in indexed["documents"]} == set(by_id)
for payload in indexed["documents"]:
    assert payload["content_sha256"] == by_id[payload["doc_id"]]["content_sha256"]
    assert payload["tenant_id"] == cfg["tenant_id"]
probe = receipts["knowledge-retrieve-01.json"]["result"]["cases"]["event_case"]
assert probe["required_nonempty_coverage"]
assert set(probe["positive_purposes"]) == {"technical_explanation", "investigation_guidance"}
members = set(expected["cases"]["event_case"]["member_ids"])
a01 = set(expected["cases"]["single_A01_case"]["member_ids"])
rows = probe["rows"]
assert len(rows) == 4
assert {a for r in rows if r["purpose"] == "technical_explanation" for a in r["query_alert_ids"]} == a01
assert {a for r in rows if r["purpose"] == "investigation_guidance" for a in r["query_alert_ids"]} == members
for row in rows:
    assert row["record_id"] == doc_ids["K1" if row["purpose"] == "technical_explanation" else "K2"]
    assert row["content_sha256"] == by_id[row["record_id"]]["content_sha256"]
    assert row["record"]["content"] == by_id[row["record_id"]]["row"]["content"]
    assert row["applicability"]["state"] == "applicable"
queries = probe["metadata"]["queries"]
assert len(queries) == 9 and all(q["state"] == "completed" and not q["truncated"] for q in queries)
historical = [q for q in queries if q["purpose"] == "historical_case_reference"]
assert len(historical) == 3 and all(q["outcome"] == "empty" and q["candidate_count"] == 0 for q in historical)
excluded = [c for q in queries for c in q["candidates"] if c["state"] == "excluded"]
assert len(excluded) == 2 and all(c["reason"] == "applicability_conflict" for c in excluded)
calls = indexed["calls"] + probe["metadata"]["calls"]
embeddings = [c for c in calls if c["backend"] == "embedding"]
assert len(embeddings) == 2 and [c["input_count"] for c in embeddings] == [2, 9]
assert all(c["state"] == "completed" and c["http_status"] == 200 for c in embeddings)
assert sum(c["path"].endswith("/points/search") for c in calls) == 9
assert sum(c["method"] == "PUT" and "points?wait=true" in c["path"] for c in calls) == 1
for failed in ("knowledge-readback-01.json", "knowledge-readback-02.json"):
    assert read(failed)["status"] == "failed"
evidence = names + ["knowledge-readback-01.json", "knowledge-readback-02.json", "knowledge-profile.json",
                    "knowledge-documents.json", "source-transfer-03.json", "verify_knowledge.py"]
result = {
    "status": "passed", "scope": "normal_knowledge_import_reader_roundtrip_real_index_and_one_source_probe",
    "batch_id": cfg["batch_id"], "profile_sha256": cfg["knowledge_profile_sha256"],
    "collection": cfg["knowledge_collection"], "document_ids": doc_ids,
    "original_content_and_metadata_preserved": True, "pg_index_retrieval_hashes_match": True,
    "embedding_requests": 2, "embedding_input_counts": [2, 9],
    "embedding_prompt_tokens": [c.get("prompt_tokens") for c in embeddings], "embedding_cost": None,
    "index_invocations": 1, "source_probe_invocations": 1, "vector_search_requests": 9,
    "returned_rows": 4, "unique_documents_returned": 2, "applicability_exclusions": 2,
    "historical_queries": 3, "historical_outcome": "real_empty", "historical_positive_coverage": False,
    "generation_calls_by_test": 0, "case_execution_proven": False, "model_quality_proven": False,
    "failed_readbacks_preserved": ["01: driver sslmode adaptation", "02: reader SELECT missing"],
    "reader_access_receipt": "../streaming-case-20261115-01/knowledge-reader-access-01.json",
    "files": {n: digest(folder / n) for n in evidence},
}
with (folder / "source-acceptance-01.json").open("x") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False))
