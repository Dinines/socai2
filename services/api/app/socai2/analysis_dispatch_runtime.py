"""Explicit single-process entry point. Never imported to start a loop in HTTP workers."""
import argparse
import asyncio
import fcntl
import importlib
import json
import logging
import signal
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .analysis_dispatch_config import KINDS, DispatchPolicy
from .analysis_dispatch_redis import AnalysisQueues
from .analysis_dispatch_store import DispatchRepository
from .analysis_dispatcher import AnalysisDispatcher
from .analysis_task_policy import AnalysisTaskPolicy
from .analysis_tasks import AnalysisTaskService


def load_profile(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("explicit absolute dispatcher profile required")
    value = json.loads(path.read_text())
    required = {"enabled", "tenant_id", "database_url_file", "database_connect_args", "database_pool_size",
                "redis_url_file", "redis_socket_timeout_seconds", "redis_connect_timeout_seconds",
                "lifecycle_policy_file", "executor_factory", "executor_config_file", "dispatch"}
    if set(value) != required or type(value["enabled"]) is not bool:
        raise ValueError("invalid dispatcher profile fields")
    UUID(value["tenant_id"])
    DispatchPolicy(**value["dispatch"])
    for name in ("database_url_file", "redis_url_file", "lifecycle_policy_file", "executor_config_file"):
        if not Path(value[name]).is_absolute():
            raise ValueError("explicit absolute config path required: " + name)
    if type(value["database_pool_size"]) is not int or value["database_pool_size"] < 1:
        raise ValueError("invalid database pool size")
    for name in ("redis_socket_timeout_seconds", "redis_connect_timeout_seconds"):
        if type(value[name]) not in {int, float} or not 0 < value[name] < float("inf"):
            raise ValueError("invalid Redis timeout")
    if not isinstance(value["database_connect_args"], dict):
        raise TypeError("invalid database options")
    if value["enabled"] and (not isinstance(value["executor_factory"], str)
            or value["executor_factory"].count(":") != 1):
        raise ValueError("enabled dispatcher requires an explicit executor factory")
    return value


@contextmanager
def exclusive_process(path):
    """One deployment instance on one host; workers must share this configured path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("dispatcher instance already active") from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


async def run(profile):
    if not profile["enabled"]:
        logging.getLogger(__name__).info("analysis_dispatch_disabled")
        return
    policy = DispatchPolicy(**profile["dispatch"])
    with exclusive_process(policy.lock_file):
        lifecycle = AnalysisTaskPolicy(**json.loads(Path(profile["lifecycle_policy_file"]).read_text()))
        engine = create_async_engine(Path(profile["database_url_file"]).read_text().strip(), hide_parameters=True,
            connect_args=profile["database_connect_args"], pool_size=profile["database_pool_size"], max_overflow=0)
        redis = Redis.from_url(Path(profile["redis_url_file"]).read_text().strip(),
            socket_timeout=profile["redis_socket_timeout_seconds"],
            socket_connect_timeout=profile["redis_connect_timeout_seconds"])
        tenant_id = UUID(profile["tenant_id"])
        service = AnalysisTaskService(async_sessionmaker(engine, expire_on_commit=False), lifecycle)
        repository = DispatchRepository(service, tenant_id)
        queues = AnalysisQueues(redis, policy.namespace, tenant_id)
        stop, loop = asyncio.Event(), asyncio.get_running_loop()
        for name in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(name, stop.set)
        try:
            module, factory = profile["executor_factory"].split(":")
            executors = getattr(importlib.import_module(module), factory)(
                json.loads(Path(profile["executor_config_file"]).read_text()), service)
            validate_executors(executors)
            await AnalysisDispatcher(repository, queues, policy, executors).serve(stop)
        finally:
            for name in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(name)
            await redis.aclose()
            await engine.dispose()


def validate_executors(executors):
    required = {"case_investigation", "alert_triage", "incident_diagnosis"}
    if (not isinstance(executors, dict) or not required <= set(executors)
            or set(executors) - set(KINDS)):
        raise ValueError("dispatcher requires current A/I/Case executors")
    if any(not callable(getattr(e, action, None)) for e in executors.values() for action in ("load", "execute")):
        raise ValueError("executors require load and execute")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run(load_profile(args.profile)))
