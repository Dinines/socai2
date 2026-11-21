"""An investigation SELECT owns its connection and waits for its worker to exit."""
import asyncio
import logging
import threading

from .clickhouse import (
    DEFAULT_QUERY_SETTINGS,
    LakeQueryError,
    LakeQueryNotConfiguredError,
    LakeQueryResult,
)

LOG = logging.getLogger(__name__)


class LakeQueryInterrupted(LakeQueryError):
    def __init__(self, code, columns, rows):
        super().__init__(code)
        self.code, self.columns, self.rows = code, columns, rows


class LakeQueryRejected(LakeQueryError):
    """The server explicitly returned an error, so its outcome is known."""


def owned_client(policy):
    from app.core.config import settings
    try:
        from clickhouse_driver import Client
    except ImportError:
        raise LakeQueryNotConfiguredError("clickhouse_driver_unavailable") from None
    if not settings.CLICKHOUSE_HOST or settings.AISOC_DISABLE_CLICKHOUSE:
        raise LakeQueryNotConfiguredError("clickhouse_not_configured")
    return Client(host=settings.CLICKHOUSE_HOST, port=settings.CLICKHOUSE_PORT,
        database=settings.CLICKHOUSE_DATABASE, user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD or "", connect_timeout=policy["connect_timeout_seconds"],
        send_receive_timeout=policy["send_receive_timeout_seconds"],
        sync_request_timeout=policy["connect_timeout_seconds"], disable_reconnect=True,
        settings=DEFAULT_QUERY_SETTINGS)


async def execute_owned(sql, *, policy, timeout_seconds, extra_settings, params, query_id):
    from clickhouse_driver.errors import (
        NetworkError,
        ServerException,
        SocketTimeoutError,
    )
    seconds = min(timeout_seconds, policy["query_timeout_seconds"])
    if seconds < 1:
        raise ValueError("insufficient_query_time")
    client = owned_client(policy)
    columns, rows, failure = [], [], []
    stopping = threading.Event()
    close_lock = threading.Lock()
    settings = {**DEFAULT_QUERY_SETTINGS, **(extra_settings or {}), "max_execution_time": int(seconds)}
    started = asyncio.get_running_loop().time()

    def close_owned():
        # driver.disconnect mutates connection.socket; the worker and timeout
        # owner must not race its shutdown/close/reset sequence.
        with close_lock:
            client.disconnect()

    def run():
        try:
            if stopping.is_set():
                return
            stream = iter(client.execute_iter(sql, params or {}, with_column_types=True,
                settings=settings, query_id=query_id))
            metadata = next(stream)
            columns.extend(name for name, _ in metadata)
            for row in stream:
                if stopping.is_set():
                    break
                rows.append(list(row))
        except ServerException as exc:
            raise LakeQueryRejected("query_server_rejected:" + str(exc.code)) from None
        except (NetworkError, SocketTimeoutError, OSError, EOFError) as exc:
            failure.append("query_transport_interrupted:" + type(exc).__name__)
        finally:
            close_owned()

    worker = asyncio.create_task(asyncio.to_thread(run))
    cancelled, interrupted = False, None
    try:
        await asyncio.wait_for(asyncio.shield(worker), timeout=seconds)
    except TimeoutError:
        interrupted = "query_timeout"
    except asyncio.CancelledError:
        cancelled, interrupted = True, "query_cancelled"
    finally:
        if not worker.done():
            stopping.set()
            close = asyncio.create_task(asyncio.to_thread(close_owned))
            settling = asyncio.gather(close, worker, return_exceptions=True)
            try:
                await asyncio.wait_for(asyncio.shield(settling), timeout=policy["close_timeout_seconds"])
            except TimeoutError:
                LOG.error("investigation_query_worker_close_deadline_exceeded")
            except asyncio.CancelledError:
                cancelled = True
            # A close deadline is an observation, not permission to abandon a
            # live thread or release its analysis slot. Repeated cancellation
            # can stop new work, but cannot make this worker already ended.
            while not settling.done():
                try:
                    await asyncio.shield(settling)
                except asyncio.CancelledError:
                    cancelled = True
            outcomes = settling.result()
            unexpected = next((r for r in outcomes if isinstance(r, BaseException)), None)
            if unexpected and not cancelled:
                raise unexpected
    if cancelled:
        raise asyncio.CancelledError
    if interrupted or failure:
        raise LakeQueryInterrupted(interrupted or failure[0], columns, rows)
    return LakeQueryResult(columns=columns, rows=rows, row_count=len(rows),
        elapsed_ms=int((asyncio.get_running_loop().time() - started) * 1000))
