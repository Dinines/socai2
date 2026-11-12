"""Direct knowledge contract checks; no claim of real retrieval/model quality."""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import patch
from uuid import UUID

import httpx
from app.socai2.baseline_optional_sources import SourceUnavailable
from app.socai2.knowledge_config import Profile, content_hash, selectors
from app.socai2.knowledge_source import index, query
from app.socai2.knowledge_vectors import Vectors

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "deploy/local-investigation/knowledge-profile.json"
TENANT, DOC = UUID(int=1), UUID(int=4)


def profile():
    value = json.loads(PROFILE.read_text())
    # Keep the two-purpose compatibility checks independent of optional history.
    value["purposes"].pop("historical_case_reference", None)
    value.pop("history", None)
    value["vector"]["api_key_file"] = None
    return Profile.model_validate(value)


def keys(p):
    alert = SimpleNamespace(alert={"title": "Process activity", "source_namespace": "lab"})
    context = SimpleNamespace(alerts={"a": alert})
    material = {"id": DOC, "ocsf_json": {"process": {"cmd_line": "example --list", "name": "example"}}}
    return [{**k, "profile_sha256": "fixture"} for k in selectors(context, {"a": material}, p)]


def document():
    return {"id": DOC, "tenant_id": TENANT, "title": "Technical reference", "content": "Command explanation.",
        "doc_kind": "other", "source_url": "https://example.invalid/reference", "chunk_index": 0, "chunk_total": 1,
        "tags": ["knowledge:technical_explanation", "knowledge:investigation_guidance"],
        "created_at": None, "updated_at": None}


class DB:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, *args):
        return SimpleNamespace(mappings=lambda: self.rows)


class Service:
    def __init__(self, rows):
        self.rows = rows

    @asynccontextmanager
    async def transaction(self, tenant, **kwargs):
        assert tenant == TENANT
        yield SimpleNamespace(db=DB(self.rows))


class FakeVectors:
    def __init__(self, rows, fail=False):
        self.calls = []
        self.rows, self.fail = rows, fail
        self.selections = []

    async def check(self, **kwargs):
        pass

    async def embed(self, texts):
        if self.fail:
            raise SourceUnavailable("knowledge_embedding_request_failed")
        return [[1.] for _ in texts]

    async def search(self, tenant, key, vector):
        self.selections.append(key["purpose"])
        return self.rows


class TopicTests(TestCase):
    def test_purposes_have_distinct_queries_filters_and_source_roles(self):
        p = profile()
        a, b = keys(p)
        self.assertNotEqual(a["value"], b["value"])
        self.assertNotEqual(a["filters"], b["filters"])
        self.assertIn("example --list", a["value"])
        self.assertEqual(a["source_paths"][-1]["role"], "source_label")
        self.assertEqual(a["source_paths"][0]["role"], "observation")
        self.assertEqual(selectors(SimpleNamespace(alerts={}), {}, p), [])

    def test_original_metadata_change_invalidates_index_identity(self):
        original = document()
        self.assertNotEqual(content_hash(original), content_hash({**original, "tags": []}))


class RetrievalTests(IsolatedAsyncioTestCase):
    async def test_two_purposes_and_empty_are_saved_without_observation_role(self):
        p, doc = profile(), document()
        hit = {"id": str(DOC), "score": .8, "payload": {"content_sha256": content_hash(doc),
            "embedding_model": p.embedding.model, "purposes": list(p.purposes)}}
        with patch("app.socai2.knowledge_source.load", return_value=(p, "fixture")):
            transport = FakeVectors([hit])
            rows, _, meta = await query(Service([doc]), TENANT, {"parameters": {"selectors": keys(p)}}, vectors=transport)
            self.assertEqual(len(rows), 2)
            self.assertEqual(transport.selections, list(p.purposes))
            self.assertTrue(all(r["record"]["content"] == doc["content"] for r in rows))
            self.assertTrue(all(q["outcome"] == "data" for q in meta["queries"]))
            rows, _, meta = await query(Service([]), TENANT, {"parameters": {"selectors": keys(p)}}, vectors=FakeVectors([]))
            self.assertEqual(rows, [])
            self.assertTrue(all(q["state"] == "completed" and q["outcome"] == "empty" for q in meta["queries"]))

    async def test_failure_and_stale_document_are_not_successful_empty_results(self):
        p = profile()
        with patch("app.socai2.knowledge_source.load", return_value=(p, "fixture")):
            for transport, code in [
                (FakeVectors([], fail=True), "knowledge_embedding_request_failed"),
                (FakeVectors([{"id": str(DOC), "payload": {}, "score": .8}]), "knowledge_index_document_stale_or_missing"),
            ]:
                with self.assertRaises(SourceUnavailable) as captured:
                    await query(Service([document()]), TENANT, {"parameters": {"selectors": keys(p)}}, vectors=transport)
                self.assertEqual(str(captured.exception), code)
                self.assertEqual(captured.exception.metadata["error"], code)

    async def test_native_vector_dimension_is_enforced(self):
        p = profile()
        def response(request):
            return httpx.Response(200, json={"model": p.embedding.model, "embeddings": [[.1, .2]]})
        with patch.dict(os.environ, {"AISOC_AIRGAPPED": "false"}), \
                self.assertRaisesRegex(SourceUnavailable, "knowledge_embedding_vector_invalid"):
            await Vectors(p, transport=httpx.MockTransport(response)).embed(["text"])

    async def test_index_refuses_missing_document_or_unclassified_content(self):
        p = profile()
        with patch("app.socai2.knowledge_source.load", return_value=(p, "fixture")):
            with self.assertRaisesRegex(SourceUnavailable, "knowledge_index_document_missing"):
                await index(DB([]), TENANT, [DOC])
            with self.assertRaisesRegex(SourceUnavailable, "knowledge_document_purpose_missing"):
                await index(DB([{**document(), "tags": []}]), TENANT, [DOC])
