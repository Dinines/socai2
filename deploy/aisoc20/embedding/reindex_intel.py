"""Re-embed preserved public CISA records into the new model collection."""

import asyncio
import hashlib
import json
from pathlib import Path

from qdrant_client import AsyncQdrantClient

from app.storage.qdrant import IOC_COLLECTION, QdrantStore


async def main():
    source = Path("/embedding-source.json")
    raw = source.read_bytes()
    points = json.loads(raw)
    # This deployment snapshot was fully checked as public CISA data.
    assert all(
        p["payload"]["source"] == "cisa-kev" and p["payload"]["tenant_id"] == "shared"
        for p in points
    )
    client = AsyncQdrantClient(url="http://qdrant:6333", timeout=60)
    store = QdrantStore(client)
    report = {
        "source_collection": "threatintel_iocs",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "destination_collection": IOC_COLLECTION,
        "model": "qwen3-embedding:0.6b",
        "source_count": len(points),
        "committed": 0,
    }
    try:
        await store.initialize()
        for start in range(0, len(points), 64):
            batch = points[start : start + 64]
            for point in batch:
                data = point["payload"]
                assert point["id"] == store._point_id(
                    data["tenant_id"], f"{data['type']}:{data['value']}"
                )
            await store.upsert_iocs([p["payload"] for p in batch], tenant_id="shared")
            report["committed"] += len(batch)
            Path("/embedding-records/reindex-progress.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            print(
                f"Public CISA records committed: {report['committed']}/{len(points)}",
                flush=True,
            )
        info = await client.get_collection(IOC_COLLECTION)
        report["destination_count"] = info.points_count
        assert report["destination_count"] == len(points)
        report["status"] = "completed"
        Path("/embedding-records/reindex-progress.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
