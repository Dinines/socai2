"""A dead-letter queue an operator can actually read.

Three DLQ implementations existed and none of them could answer the
question a DLQ exists for. `LoggingDLQ` writes a log line, which is
findable only if you already know to look. `KafkaDLQ` writes to
`aisoc.alerts.dlq`, which has no consumer. `InMemoryDLQ` forgets on
restart.

So events were being dropped correctly and invisibly — and an invisible
drop is indistinguishable from an event that never arrived, which is the
worse of the two possibilities and the one nobody investigates.

This persists them. Two properties matter more than the writing:

**Recording has an explicit confirmation result.** Direct callers retain
the fail-soft interface: missing storage or an INSERT failure is logged
and returns False rather than raising. A confirmed INSERT returns True.
The live worker must not treat False as a stored dead letter: it holds
the input and stops that consumption round before any later offset can
pass it. Logging a failure is not proof that the rejected input survived.

**The payload is truncated, never stored whole.** It is untrusted by
definition — it is the thing the pipeline refused — and may be large or
hostile. Storing all of it makes this table an unbounded sink for exactly
the content that was rejected.
"""

from __future__ import annotations

from collections.abc import Callable

import asyncpg
import structlog

from app.services.dlq import DeadLetter, DeadLetterQueue

logger = structlog.get_logger(__name__)

#: Characters of payload kept. Enough to recognise the shape and find the
#: producer; far short of enough to reconstruct the event, which is
#: deliberate — this is a triage record, not a replay buffer.
MAX_EXCERPT = 2000

_INSERT_SQL = """
INSERT INTO aisoc_dead_letters
    (tenant_id, topic, reason, schema_version, payload_excerpt, source_event_id,
     topic_partition, kafka_offset)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
"""


class PostgresDLQ(DeadLetterQueue):
    """Persist rejected messages so they can be triaged.

    Takes a provider rather than a pool, because the connection pool is
    opened during worker startup — after this is constructed. Capturing it
    eagerly would capture ``None`` and silently drop every dead letter,
    which is the failure this class exists to end.

    A provider *always*, never "a pool or a provider": telling the two
    apart with ``callable()`` is wrong for anything with ``__call__``,
    which includes every mock, and a constructor whose behaviour depends
    on duck-typing its own argument is one that fails differently in
    tests than in production. Callers with a concrete pool pass
    ``lambda: pool``.
    """

    def __init__(self, pool_provider: Callable[[], asyncpg.Pool | None]) -> None:
        self._pool_provider = pool_provider

    def _pool_now(self) -> asyncpg.Pool | None:
        return self._pool_provider()

    async def record(self, letter: DeadLetter) -> bool:
        excerpt = (letter.payload_excerpt or "")[:MAX_EXCERPT]
        tenant_id = _as_uuid(letter.tenant_id)

        pool = self._pool_now()
        if pool is None:
            # The sink never opened, so there is nowhere to write. Logged
            # at warning rather than silently skipped: a DLQ that records
            # nothing looks exactly like a pipeline dropping nothing.
            logger.warning(
                "dlq.no_pool",
                topic=letter.topic,
                reason=letter.reason,
            )
            return False

        try:
            async with pool.acquire() as conn:
                status = await conn.execute(
                    _INSERT_SQL,
                    tenant_id,
                    letter.topic,
                    letter.reason,
                    letter.schema_version,
                    excerpt,
                    letter.source_event_id,
                    # Nullable, and left null rather than guessed when the
                    # refusal came from a path with no Kafka record behind it
                    # — a fabricated offset replays somebody else's message.
                    letter.partition,
                    letter.offset,
                )
                if status != "INSERT 0 1":
                    raise RuntimeError("PostgreSQL dead-letter INSERT was not confirmed")
        except Exception as exc:  # noqa: BLE001 - see the module docstring
            # Preserve the direct fail-soft call while making the failure
            # explicit to safe_record and the live worker. The input may be
            # committed only after a confirmed durable dead-letter INSERT.
            logger.warning(
                "dlq.persist_failed",
                topic=letter.topic,
                reason=letter.reason,
                error=str(exc),
            )
            return False

        logger.info(
            "dlq.recorded",
            topic=letter.topic,
            reason=letter.reason,
            tenant_id=letter.tenant_id,
        )
        return True


def _as_uuid(value: str | None):
    """Parse a tenant id, or None.

    A malformed envelope can carry a tenant field that is not a uuid.
    Rejecting the whole record over it would lose the dead letter entirely
    — and the dead letter is the evidence that something is producing
    malformed envelopes.
    """
    if not value:
        return None
    import uuid  # noqa: PLC0415 - only needed on the failure path

    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
