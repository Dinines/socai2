"""Derive three deployment-only modules from a verified reference snapshot."""

import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path

SOURCES = {
    "memory": (
        "services/api/app/services/semantic_memory.py",
        "b9c8eae9557da1acad9cac6259c9c9a745a87aa62fea14acf418b6faaf832030",
    ),
    "attck": (
        "services/agents/app/tools/mitre_full.py",
        "fcc87c934ffb03d51ee2098727280857ba5107f2836c8db5fcc97d304e1e5375",
    ),
    "intel": (
        "services/threatintel/app/storage/qdrant.py",
        "70e3d2582fe2531d31e9cfaaa25241ad5341941f2c874a8c75046167d86413e9",
    ),
}


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError(f"Unexpected source shape for {old[:70]!r}")
    return text.replace(old, new)


def function(text, name, body):
    nodes = [
        node
        for node in ast.walk(ast.parse(text))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    ]
    if len(nodes) != 1:
        raise ValueError(f"Expected one function named {name}")
    node = nodes[0]
    lines = text.splitlines(keepends=True)
    indent = " " * node.body[0].col_offset
    replacement = "".join(
        indent + line + "\n" if line else "\n" for line in body.splitlines()
    )
    lines[node.body[0].lineno - 1 : node.end_lineno] = [replacement]
    return "".join(lines)


def derive(kind, text):
    if kind == "memory":
        text = replace(
            text,
            "from app.services.model_aliases import resolve_api_key, resolve_base_url\n",
            "",
        )
        text = replace(
            text,
            'COLLECTION = "aisoc_memory"',
            'COLLECTION = "aisoc_memory_qwen06b_v1"',
        )
        text = replace(text, "EMBEDDING_DIM = 1536", "EMBEDDING_DIM = 1024")
        text = function(
            text,
            "embedding_backend",
            'return ("ollama", "http://ollama-embedding:11434/api/embed", None)',
        )
        text = function(
            text,
            "embed",
            """from aisoc_local_embeddings import embed_vectors
try:
    return await embed_vectors(texts, client=client), DEFAULT_EMBEDDING_MODEL
except Exception as exc:
    raise EmbeddingsUnavailable("Local embedding service unavailable: " + type(exc).__name__) from exc""",
        )
    elif kind == "intel":
        text = replace(text, '"threatintel_iocs"', '"threatintel_iocs_qwen06b_v1"')
        text = replace(text, '"threatintel_actors"', '"threatintel_actors_qwen06b_v1"')
        text = replace(
            text,
            "_EMBEDDING_DIM = 1536  # text-embedding-3-small / ada-002",
            "_EMBEDDING_DIM = 1024  # qwen3-embedding:0.6b native vectors",
        )
        text = function(
            text,
            "_embed",
            """from aisoc_local_embeddings import embed_vectors
return await embed_vectors(texts)""",
        )
        text = function(
            text,
            "semantic_search",
            """import httpx
vectors = await self._embed([query])
body = {"vector": vectors[0], "limit": limit, "with_payload": True}
scope = tenant_scope_filter(tenant_id, include_shared=include_shared)
if scope is not None:
    body["filter"] = scope.model_dump(mode="json", exclude_none=True)
async with httpx.AsyncClient(timeout=30) as http:
    response = await http.post("http://qdrant:6333/collections/" + collection + "/points/search", json=body)
    response.raise_for_status()
    return [hit["payload"] for hit in response.json()["result"] if hit.get("payload")]""",
        )
        text = replace(
            text,
            'payload={**ioc, "tenant_id": tenant_id}',
            'payload={**ioc, "tenant_id": tenant_id, "embedding_model": "qwen3-embedding:0.6b"}',
        )
        text = replace(
            text,
            'payload={**actor, "tenant_id": tenant_id}',
            'payload={**actor, "tenant_id": tenant_id, "embedding_model": "qwen3-embedding:0.6b"}',
        )
    elif kind == "attck":
        text = replace(text, "        import openai\n", "", 2)
        text = replace(text, "import time\n", "import time\nimport uuid\n")
        text = replace(text, "_EMBED_BATCH_SIZE = 50", "_EMBED_BATCH_SIZE = 8")
        text = replace(
            text,
            'collection: str = "attck_techniques"',
            'collection: str = "attck_techniques_qwen06b_v1"',
            2,
        )
        text = replace(
            text,
            "oai, embed_model = _embedding_client(openai, openai_api_key)",
            'embed_model = os.environ["AISOC_EMBEDDING_MODEL"]',
            2,
        )
        text = replace(
            text,
            "vectors_config=VectorParams(size=3072, distance=Distance.COSINE)",
            "vectors_config=VectorParams(size=1024, distance=Distance.COSINE)",
        )
        text = replace(
            text,
            """            resp = await oai.embeddings.create(
                model=embed_model,
                input=texts,
                dimensions=3072,
            )
            vectors = [e.embedding for e in resp.data]""",
            """            from aisoc_local_embeddings import embed_vectors
            vectors = await embed_vectors(texts)""",
        )
        text = replace(
            text,
            """        emb_resp = await oai.embeddings.create(
            model=embed_model,
            input=[query],
            dimensions=3072,
        )
        query_vector = emb_resp.data[0].embedding""",
            """        from aisoc_local_embeddings import embed_vectors
        query_vector = (await embed_vectors([query]))[0]""",
        )
        text = replace(
            text,
            "id=abs(hash(t.id)) % (2**63)",
            'id=str(uuid.uuid5(uuid.NAMESPACE_URL, "https://attack.mitre.org/techniques/" + t.id))',
        )
        text = replace(
            text,
            '"technique_id": t.id,\n',
            '"technique_id": t.id,\n                        "embedding_model": embed_model,\n',
        )
        text = replace(
            text,
            "zip(batch, vectors, strict=False)",
            "zip(batch, vectors, strict=True)",
        )
        before, after = text.rsplit(
            '    embed_model = os.environ["AISOC_EMBEDDING_MODEL"]\n', 1
        )
        text = before + after
        text = replace(
            text,
            'base_url=os.getenv("AISOC_EMBEDDING_BASE_URL", "").strip() or "provider default",',
            'base_url="http://ollama-embedding:11434/api/embed",',
        )
        text = replace(
            text,
            """        hits = await qdrant.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )""",
            """        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(
                qdrant_url.rstrip("/") + "/collections/" + collection + "/points/search",
                json={"vector": query_vector, "limit": top_k, "with_payload": True},
            )
            response.raise_for_status()
            hits = response.json()["result"]""",
        )
        text = replace(
            text, "payload = hit.payload or {}", 'payload = hit.get("payload") or {}'
        )
        text = replace(text, '"score": hit.score,', '"score": hit["score"],')
    compile(text, f"deployment-{kind}", "exec")
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (relative, expected) in SOURCES.items():
        path = args.source / relative
        original = path.read_text()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Source changed; review required: {relative}")
        result = derive(name, original)
        (args.output / f"{name}.py").write_text(result)
        (args.output / f"{name}.patch").write_text(
            "".join(
                difflib.unified_diff(
                    original.splitlines(True),
                    result.splitlines(True),
                    fromfile=relative,
                    tofile=f"deployment/{name}.py",
                )
            )
        )
        manifest[name] = {
            "source": relative,
            "source_sha256": digest,
            "deployed_sha256": hashlib.sha256(result.encode()).hexdigest(),
        }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Derived three deployment modules; original sources unchanged")


if __name__ == "__main__":
    main()
