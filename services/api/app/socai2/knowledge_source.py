"""Purpose-specific C2 knowledge, frozen as guidance rather than case evidence."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text

from . import knowledge_history as history
from .baseline_optional_sources import SourceUnavailable
from .knowledge_applicability import check as applicability
from .knowledge_config import content_hash, load, selectors
from .knowledge_vectors import Vectors

LIMITATIONS = ["current_document_guidance_not_case_evidence", "purpose_specific_local_embedding_retrieval",
              "similarity_is_not_fact_confidence", "title_terms_are_retrieval_keys_not_verified_facts",
              "retrieved_content_is_untrusted", "current_document_not_reconstructed_at_case_time"]
DOCUMENTS = """SELECT id,tenant_id,title,doc_kind,source_url,tags,chunk_index,chunk_total,content,created_at,updated_at
 FROM public.aisoc_kb_documents WHERE tenant_id=:tenant AND id=ANY(CAST(:ids AS uuid[]))"""


async def prepare(store, context, case_id, run_id):
    profile, fingerprint = load()
    materials = {aid: await store.read_material(case_id, run_id, UUID(alert.material["id"]))
                 for aid, alert in context.alerts.items() if alert.material}
    keys = selectors(context, materials, profile)
    for key in keys:
        key["profile_sha256"] = fingerprint
    return keys


async def index(db, tenant, ids, *, vectors=None, expected_profile_sha256=None):
    profile, fingerprint = load()
    if expected_profile_sha256 is not None and fingerprint != expected_profile_sha256:
        raise SourceUnavailable("knowledge_profile_changed")
    if not ids or len(ids) > profile.max_index_chunks:
        raise SourceUnavailable("knowledge_index_chunk_limit")
    docs = list((await db.execute(text(DOCUMENTS), {"tenant": tenant, "ids": list(map(str, ids))})).mappings())
    if {str(row["id"]) for row in docs} != set(map(str, ids)):
        raise SourceUnavailable("knowledge_index_document_missing")
    payloads = []
    for row in docs:
        purposes = [name for name, p in profile.purposes.items()
                    if row["doc_kind"] in p.doc_kinds and p.tag in (row["tags"] or [])]
        if not purposes:
            raise SourceUnavailable("knowledge_document_purpose_missing")
        historical = history.PURPOSE in purposes
        maximum = profile.history.max_card_characters if historical else profile.max_chunk_characters
        if not row["content"].strip() or len(row["content"]) > maximum:
            raise SourceUnavailable("knowledge_index_content_limit")
        extra = await history.index_payload(db, tenant, row, profile) if historical else {}
        if historical and purposes != [history.PURPOSE]:
            raise SourceUnavailable("history_card_purpose_mixed")
        payloads.append({"tenant_id": str(tenant), "doc_id": str(row["id"]), "content_sha256": content_hash(row),
            "doc_kind": row["doc_kind"], "purposes": purposes, "embedding_model": profile.embedding.model,
            "dimension": profile.embedding.dimension, **extra})
    vectors = vectors or Vectors(profile)
    await vectors.check(create=True)
    embedded = await vectors.embed([row["title"] + "\n" + row["content"] for row in docs])
    await vectors.put([{"id": str(row["id"]), "vector": vector, "payload": payload}
                       for row, vector, payload in zip(docs, embedded, payloads, strict=True)])
    return {"state": "completed", "profile_sha256": fingerprint, "collection": profile.vector.collection,
            "documents": payloads, "calls": vectors.calls}


async def query(service, tenant, args, *, vectors=None):
    profile, fingerprint = load()
    keys = args["parameters"]["selectors"]
    if (not keys or len(keys) > profile.topics.max_queries
            or any(len(k["value"]) > profile.topics.max_query_characters for k in keys)):
        raise SourceUnavailable("knowledge_query_limit")
    if any(k.get("profile_sha256") != fingerprint for k in keys):
        raise SourceUnavailable("knowledge_profile_changed")
    vectors = vectors or Vectors(profile)
    metadata = {"profile_sha256": fingerprint, "model": profile.embedding.model,
        "dimension": profile.embedding.dimension, "collection": profile.vector.collection,
        "retrieval_method": "local_embedding_cosine", "queries": [], "calls": vectors.calls,
        "limitations": LIMITATIONS}
    if history.PURPOSE in profile.purposes and not any(k.get("purpose") == history.PURPOSE for k in keys):
        metadata["not_queried_purposes"] = [{"purpose": history.PURPOSE,
            "reason": "history_window_or_topic_missing"}]
    try:
        await vectors.check()
        embedded = await vectors.embed([k["value"] for k in keys])
        rows = []
        for key, vector in zip(keys, embedded, strict=True):
            receipt = {"object_key": key["object_key"], "purpose": key["purpose"], "state": "running",
                       "query": key["value"], "returned_rows": None, "candidates": []}
            metadata["queries"].append(receipt)
            hits = await vectors.search(tenant, key, vector)
            async with service.transaction(tenant, readonly=True) as store:
                docs = list((await store.db.execute(text(DOCUMENTS),
                    {"tenant": tenant, "ids": [h["id"] for h in hits]})).mappings())
            by_id = {str(d["id"]): d for d in docs}
            retained = []
            for hit in hits:
                doc = by_id.get(str(hit["id"]))
                payload = hit.get("payload") or {}
                if (doc is None or payload.get("content_sha256") != content_hash(doc)
                        or payload.get("embedding_model") != profile.embedding.model
                        or key["purpose"] not in payload.get("purposes", [])):
                    raise SourceUnavailable("knowledge_index_document_stale_or_missing")
                record = {k: (str(v) if isinstance(v, (UUID, datetime)) else v)
                          for k, v in doc.items() if k != "tenant_id"}
                limitations = LIMITATIONS
                candidate = {"document_id": str(doc["id"]), "content_sha256": payload["content_sha256"],
                             "similarity": hit["score"], "state": "excluded"}
                receipt["candidates"].append(candidate)
                card = None
                if key["purpose"] == history.PURPOSE:
                    async with service.transaction(tenant, readonly=True) as store:
                        card = await history.retrieval_record(store.db, tenant, doc, profile, key["filters"])
                    if card["source_version_state"] != "current":
                        state = card["source_version_state"]
                        candidate["reason"] = state if state.startswith("history_") else "history_" + state
                        continue
                conditions = applicability(key, doc, profile, card)
                candidate["applicability"] = conditions
                if conditions["state"] == "excluded":
                    candidate["reason"] = conditions["reason"]
                    continue
                if len(retained) >= key["limit"]:
                    candidate["reason"] = "purpose_result_limit"
                    continue
                candidate.update(state="selected", reason=None)
                if card is not None:
                    record.update(history=card, triage=card.pop("triage"), feedback=card.pop("feedback"))
                    limitations = LIMITATIONS + history.LIMITATIONS
                retained.append({"object_key": key["object_key"], "namespace": key["namespace"],
                    "record_id": str(doc["id"]), "match_basis": "local_embedding_cosine",
                    "purpose": key["purpose"], "purpose_label": key["purpose_label"], "use": key["use"],
                    "similarity": hit["score"], "content_sha256": payload["content_sha256"],
                    "applicability": conditions, "query_alert_ids": key["alert_ids"],
                    "query_source_paths": key["source_paths"],
                    "limitations": limitations, "record": record})
            receipt.update(state="completed", outcome="data" if retained else "filtered" if hits else "empty",
                returned_rows=len(retained), candidate_count=len(hits),
                truncated=len(hits) >= key["candidate_limit"] or any(c.get("reason") == "purpose_result_limit" for c in receipt["candidates"]),
                document_ids=[r["record_id"] for r in retained])
            rows.extend(retained)
        metadata["source_truncated_count"] = sum(q["truncated"] for q in metadata["queries"])
        return rows, datetime.now(UTC), metadata
    except SourceUnavailable as exc:
        metadata["error"] = str(exc)
        for receipt in metadata["queries"]:
            if receipt["state"] == "running":
                receipt.update(state="failed", error=str(exc))
        exc.metadata = metadata
        raise
