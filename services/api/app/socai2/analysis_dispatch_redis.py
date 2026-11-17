"""FIFO and hints only. All claims and lifecycle facts are checked against PG."""
from uuid import UUID

from .analysis_dispatch_config import KINDS


class AnalysisQueues:
    def __init__(self, redis, namespace, tenant_id):
        self.redis, self.namespace, self.tenant_id = redis, namespace, tenant_id

    def key(self, name):
        return f"{self.namespace}:{self.tenant_id}:{name}"

    def normal(self, kind):
        if kind not in KINDS:
            raise ValueError("unknown task kind")
        return self.key("task:" + kind)

    @property
    def pending(self):
        return self.key("pending")

    async def push(self, task, *, pending=False):
        await self.redis.rpush(self.pending if pending else self.normal(task["kind"]), str(task["id"]))

    async def pop(self, key):
        raw = await self.redis.lpop(key)
        if raw is None:
            return None
        return UUID(raw.decode() if isinstance(raw, bytes) else raw)

    async def mark_running(self, task):
        await self.redis.hset(self.key("running:" + task["kind"]), str(task["subject_id"]), str(task["id"]))
        await self.redis.sadd(self.key("running"), str(task["id"]))

    async def release(self, task):
        key = self.key("running:" + task["kind"])
        raw = await self.redis.hget(key, str(task["subject_id"]))
        if raw and UUID(raw.decode() if isinstance(raw, bytes) else raw) == task["id"]:
            await self.redis.hdel(key, str(task["subject_id"]))
        await self.redis.srem(self.key("running"), str(task["id"]))

    async def reset_hints(self):
        # Exact owned keys, not FLUSHALL/SCAN-and-delete or another profile's data.
        keys = [self.key("running")]
        keys += [self.key("running:" + kind) for kind in KINDS]
        await self.redis.delete(*keys)
