"""The reference deployment's single CPU embedding route; no chat traffic."""

import hashlib
import json
import math
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

MODEL = "qwen3-embedding:0.6b"
DIMENSION = 1024
URL = "http://ollama-embedding:11434/api/embed"


def validate_vectors(vectors, count):
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ValueError("Embedding response count differs from input count")
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != DIMENSION:
            raise ValueError(
                "Embedding response must contain native 1024-dimensional vectors"
            )
        if any(
            isinstance(x, bool)
            or not isinstance(x, (int, float))
            or not math.isfinite(x)
            for x in vector
        ):
            raise ValueError("Embedding response contains invalid numbers")
        if not any(x != 0 for x in vector):
            raise ValueError("Embedding response contains a zero vector")
    return vectors


async def embed_vectors(texts, *, client=None):
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("Embedding inputs must be nonempty text")
    owns_client = client is None
    http = client or httpx.AsyncClient()
    vectors = []
    try:
        for offset in range(0, len(texts), 8):
            batch = texts[offset : offset + 8]
            call_id = str(uuid.uuid4())
            started = time.monotonic()
            record = {
                "call_id": call_id,
                "started_at": datetime.now(UTC).isoformat(),
                "service": os.environ.get("EMBEDDING_SERVICE_NAME"),
                "endpoint": URL,
                "model": MODEL,
                "input_sha256": [hashlib.sha256(t.encode()).hexdigest() for t in batch],
                "cost": None,
                "cost_source": "unknown",
            }
            try:
                response = await http.post(
                    URL,
                    json={
                        "model": MODEL,
                        "input": batch,
                        "truncate": False,
                        "keep_alive": "30m",
                        "options": {"num_gpu": 0, "num_thread": 16, "num_ctx": 32768},
                    },
                    timeout=180,
                )
                response.raise_for_status()
                data = response.json()
                result = validate_vectors(data.get("embeddings"), len(batch))
                if data.get("model") != MODEL:
                    raise ValueError("Embedding response names an unexpected model")
                vectors.extend(result)
                record.update(
                    status="succeeded",
                    dimension=DIMENSION,
                    output_sha256=[
                        hashlib.sha256(json.dumps(v).encode()).hexdigest()
                        for v in result
                    ],
                    prompt_tokens=data.get("prompt_eval_count"),
                    provider_duration_ns=data.get("total_duration"),
                )
            except Exception as exc:
                record.update(status="failed_or_unknown", error_type=type(exc).__name__)
                raise
            finally:
                record["elapsed_seconds"] = round(time.monotonic() - started, 6)
                audit = os.environ.get("EMBEDDING_RECORD_DIR")
                if audit:
                    path = Path(audit) / (call_id + ".json")
                    path.write_text(json.dumps(record, indent=2) + "\n")
    finally:
        if owns_client:
            await http.aclose()
    return vectors
