"""One labelled synthetic memory through HTTP; remove only that test record."""

import json
import pathlib
import subprocess
import urllib.request
import uuid


def main():
    root = pathlib.Path("/home/lychee/beenuar")
    credentials = json.loads((root / "deployment/admin-credentials.json").read_text())
    base = "http://192.168.1.20:3000/api/v1"
    token = None

    def request(method, path, body=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(
            base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=180) as response:
            return json.load(response)

    token = request(
        "POST",
        "/auth/login",
        {"email": credentials["email"], "password": credentials["password"]},
    )["access_token"]
    test_ref = "deployment:embedding-smoke:" + str(uuid.uuid4())
    report = {"input_kind": "synthetic deployment verification", "source_ref": test_ref}
    item_id = None
    try:
        created = request(
            "POST",
            "/memory/items",
            {
                "kind": "memory",
                "subject": test_ref,
                "source_ref": test_ref,
                "source": "deployment-smoke",
                "title": "合成部署验证：PowerShell 编码脚本",
                "content": "这是合成部署验证记录，不是真实事件经验。PowerShell 编码命令调查需要检查父进程、命令行与网络连接。",
            },
        )
        item_id = created["item"]["id"]
        report.update(
            item_id=item_id,
            indexed=created["indexed"],
            embedding_model=created["item"]["embedding_model"],
        )
        assert created["indexed"], created.get("index_error")
        assert report["embedding_model"] == "qwen3-embedding:0.6b"
        hits = request(
            "POST",
            "/memory/recall",
            {
                "query": "PowerShell 编码脚本应检查父进程与网络连接",
                "kinds": ["memory"],
                "limit": 3,
            },
        )
        match = next(hit for hit in hits if hit["item"]["id"] == item_id)
        assert match["item"]["source"] == "deployment-smoke"
        report.update(retrieved=True, score=match["score"], status="passed")
    finally:
        if item_id:
            request("DELETE", "/memory/items/" + item_id)
        # The API retires a memory. Delete only this labelled test row afterward.
        # The reference deployment contains no real memory records at this point.
        cleanup = """import asyncio,os,uuid,asyncpg
from app.services.semantic_memory import forget_item
async def main():
    db=await asyncpg.connect(os.environ['DATABASE_MIGRATION_URL'].replace('postgresql+asyncpg://','postgresql://'))
    try:
        rows=await db.fetch("DELETE FROM aisoc_memory_items WHERE tenant_id=$1 AND source=$2 AND source_ref=$3 RETURNING id",uuid.UUID('00000000-0000-0000-0000-000000000001'),'deployment-smoke',TEST_REF)
        for row in rows: await forget_item(row['id'])
        count=await db.fetchval("SELECT count(*) FROM aisoc_memory_items WHERE tenant_id=$1",uuid.UUID('00000000-0000-0000-0000-000000000001'))
        print(count)
    finally: await db.close()
asyncio.run(main())
""".replace("TEST_REF", repr(test_ref))
        result = subprocess.run(
            ["docker", "exec", "-i", "aisoc-api", "python", "-"],
            input=cleanup,
            text=True,
            capture_output=True,
            check=True,
        )
        report["memory_rows_after_cleanup"] = int(result.stdout.strip())
        assert report["memory_rows_after_cleanup"] == 0
        (root / "deployment/embedding/memory-smoke.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
