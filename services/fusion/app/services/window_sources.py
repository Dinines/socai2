"""Bounded lineage beside existing threshold counters, never detection policy."""
import json
from datetime import UTC, datetime

MAX_WINDOW_SOURCES = 200


async def record_sources(redis, key, event_id, event_time, now, window):
    try:
        if event_id:
            value = json.dumps([event_id, event_time.isoformat() if event_time else None], separators=(",", ":"))
            await redis.zadd(key, {value: now})
            await redis.zremrangebyscore(key, 0, now - window)
            await redis.expire(key, window)
            count = await redis.zcard(key)
            if count > MAX_WINDOW_SOURCES:
                await redis.zremrangebyrank(key, 0, count - MAX_WINDOW_SOURCES - 1)
                await redis.set(key + ":truncated", "1", ex=window)
        else:
            await redis.set(key + ":missing", "1", ex=window)
        return True
    except Exception:
        # Optional evidence collection cannot suppress an otherwise firing rule.
        return False


async def read_sources(redis, key, now, window, available):
    metadata = {"scope": "matched_events_in_processing_window", "window_seconds": window,
                "window_start": datetime.fromtimestamp(now - window, UTC).isoformat(),
                "window_end": datetime.fromtimestamp(now, UTC).isoformat()}
    if not available:
        return [], {**metadata, "status": "unavailable", "complete": False}
    try:
        entries = await redis.zrangebyscore(key, now - window, now)
        values = [json.loads(entry) for entry in entries]
        ids = list(dict.fromkeys(value[0] for value in values))
        times = sorted(value[1] for value in values if value[1])
        truncated = bool(await redis.get(key + ":truncated"))
        missing = bool(await redis.get(key + ":missing"))
        return ids[:MAX_WINDOW_SOURCES], {**metadata, "status": "available", "truncated": truncated,
                   "missing_ids": missing, "complete": False, "coverage": "bounded_observed_references",
                   "retained_ids": len(ids[:MAX_WINDOW_SOURCES]),
                   "retained_event_time_min": times[0] if times else None,
                   "retained_event_time_max": times[-1] if times else None}
    except Exception:
        return [], {**metadata, "status": "unavailable", "complete": False}
