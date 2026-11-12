"""Native local embeddings and a document-only Qdrant collection."""
import hashlib
import json
import math
import time
from datetime import datetime
from pathlib import Path

import httpx

from app.core.airgap import enforce_airgap_for_url

from .baseline_optional_sources import SourceUnavailable


class Vectors:
    def __init__(self, profile, *, transport=None):
        self.profile, self.transport = profile, transport
        self.calls = []

    async def request(self, backend, method, path, body=None, *, absent=False):
        config = getattr(self.profile, backend)
        url = str(config.url).rstrip("/") + path
        enforce_airgap_for_url(url)
        headers = {}
        if backend == "vector" and config.api_key_file:
            try:
                headers["api-key"] = Path(config.api_key_file).read_text().strip()
            except OSError:
                raise SourceUnavailable("knowledge_vector_credential_unavailable") from None
        record = {"backend": backend, "method": method, "path": path, "state": "started"}
        self.calls.append(record)
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=config.timeout_seconds) as client:
                response = await client.request(method, url, json=body, headers=headers)
            record["http_status"] = response.status_code
            if absent and response.status_code == 404:
                record["state"] = "absent"
                return None
            response.raise_for_status()
            result = response.json()
            record["state"] = "completed"
            return result
        except (httpx.HTTPError, ValueError):
            record["state"] = "failed"
            raise SourceUnavailable("knowledge_" + backend + "_request_failed") from None
        finally:
            record["elapsed_seconds"] = round(time.monotonic() - started, 4)

    async def embed(self, texts):
        e = self.profile.embedding
        result = await self.request("embedding", "POST", "", {
            "model": e.model, "input": texts, "truncate": False, "options": e.options})
        vectors = result.get("embeddings")
        if result.get("model") != e.model or not isinstance(vectors, list) or len(vectors) != len(texts):
            raise SourceUnavailable("knowledge_embedding_response_mismatch")
        for vector in vectors:
            if (not isinstance(vector, list) or len(vector) != e.dimension
                    or not all(type(v) in (int, float) and math.isfinite(v) for v in vector) or not any(vector)):
                raise SourceUnavailable("knowledge_embedding_vector_invalid")
        self.calls[-1].update(model=e.model, dimension=e.dimension, input_count=len(texts),
            input_sha256=[hashlib.sha256(t.encode()).hexdigest() for t in texts],
            vector_sha256=[hashlib.sha256(json.dumps(v).encode()).hexdigest() for v in vectors],
            prompt_tokens=result.get("prompt_eval_count"))
        return vectors

    @property
    def collection(self):
        return "/collections/" + self.profile.vector.collection

    async def check(self, *, create=False):
        info = await self.request("vector", "GET", self.collection, absent=create)
        if info is None:
            await self.request("vector", "PUT", self.collection,
                {"vectors": {"size": self.profile.embedding.dimension, "distance": "Cosine"}})
            return
        vector = info.get("result", {}).get("config", {}).get("params", {}).get("vectors", {})
        if vector.get("size") != self.profile.embedding.dimension or vector.get("distance") != "Cosine":
            raise SourceUnavailable("knowledge_collection_space_mismatch")

    async def put(self, points):
        result = await self.request("vector", "PUT", self.collection + "/points?wait=true", {"points": points})
        if result.get("result", {}).get("status") != "completed":
            raise SourceUnavailable("knowledge_index_write_unconfirmed")

    async def search(self, tenant, selector, vector):
        conditions = {"tenant_id": str(tenant), "embedding_model": self.profile.embedding.model,
                      "dimension": self.profile.embedding.dimension, "purposes": selector["purpose"]}
        must = [{"key": key, "match": {"value": value}} for key, value in conditions.items()]
        must.append({"key": "doc_kind", "match": {"any": selector["filters"]["doc_kinds"]}})
        filters = {"must": must}
        if selector["purpose"] == "historical_case_reference":
            bounds = selector["filters"]
            must.append({"key": "event_epoch", "range": {
                "gte": datetime.fromisoformat(bounds["event_start"]).timestamp(),
                "lt": datetime.fromisoformat(bounds["event_before"]).timestamp()}})
            filters["must_not"] = [{"key": "source_alert_id", "match": {"any": bounds["exclude_alert_ids"]}}]
        result = await self.request("vector", "POST", self.collection + "/points/search", {
            "vector": vector, "filter": filters, "limit": selector["limit"] + 1,
            "score_threshold": selector["score_threshold"], "with_payload": True, "with_vector": False})
        if not isinstance(result.get("result"), list):
            raise SourceUnavailable("knowledge_vector_response_invalid")
        return result["result"]
