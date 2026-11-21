"""File logging for the investigation chain, independent of service databases.

Canonical copy; Fusion ships the identical module because images have separate
Python paths (as with app._health). Records select operational fields only;
business records and third-party exception text are not log inputs.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import UUID, uuid4

import structlog

_CONTEXT = ContextVar("investigation_log_context", default={})
_FIELDS = frozenset({
    "operation", "stage", "dependency", "error_code", "exception_type", "correlation_id",
    "task_id", "attempt_id", "attempt_no", "run_id", "step_id", "step_code", "subject_type",
    "subject_id", "retry_count", "retryable", "next_retry_at", "first_observed_at",
    "outcome", "http_status", "http_method", "route",
    "receipt_ended_at", "database_started_at", "database_latest_start", "database_observed_ended_at",
})
_EVENT = re.compile(r"[a-z][a-z0-9_.-]*\Z")


@contextmanager
def log_context(**fields):
    token = _CONTEXT.set({**_CONTEXT.get(), **fields})
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def bind_log_context(**fields):
    """Update only the current asynchronous execution's context."""
    _CONTEXT.set({**_CONTEXT.get(), **fields})


def exception_structure(error):
    """Stack locations and exception links, without text, source lines or locals."""
    chain, seen = [], set()
    relation = "raised"
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        frames, tb = [], error.__traceback__
        while tb is not None:
            frames.append({"file": tb.tb_frame.f_code.co_filename,
                           "line": tb.tb_lineno, "function": tb.tb_frame.f_code.co_name})
            tb = tb.tb_next
        chain.append({"exception_type": type(error).__name__, "relation": relation, "frames": frames})
        if error.__cause__ is not None:
            error, relation = error.__cause__, "cause"
        elif not error.__suppress_context__:
            error, relation = error.__context__, "context"
        else:
            break
    return chain


def exception_fields(error=None):
    error = error if error is not None else sys.exc_info()[1]
    return ({"exception_type": type(error).__name__, "traceback": exception_structure(error)}
            if error is not None else {})


def log_exception(logger, event, *, extra=None, level=logging.ERROR, error=None):
    # Also safe with the old console-only logger: no original exc_info/text is
    # handed to a foreign formatter. This selects structure, never edits data.
    logger.log(level, event, extra={**exception_fields(error), **(extra or {})})


class OperationalFormatter(logging.Formatter):
    def __init__(self, service, instance):
        super().__init__()
        self.service, self.instance = service, instance

    def format(self, record):
        values = record.msg if isinstance(record.msg, dict) else {"event": record.msg}
        event = values.get("event")
        # A stable program event, not arbitrary interpolated exception/body text.
        message = event if isinstance(event, str) and _EVENT.fullmatch(event) else "service_log_record"
        stamp = datetime.fromtimestamp(record.created, UTC).isoformat()
        body = {"timestamp": stamp, "observed_at": stamp, "level": record.levelname,
                "service": self.service, "module": record.name, "instance": self.instance,
                "process": record.process, "message": message,
                "operation": message, "stage": "service", "dependency": "unspecified"}
        for key, value in {**_CONTEXT.get(), **record.__dict__, **values}.items():
            if key in _FIELDS and value is not None:
                if isinstance(value, (UUID, datetime)):
                    value = value.isoformat() if isinstance(value, datetime) else str(value)
                if isinstance(value, (str, int, float, bool)):
                    body[key] = value
        info = record.exc_info or values.get("exc_info")
        error = info if isinstance(info, BaseException) else (
            info[1] if isinstance(info, tuple) else sys.exc_info()[1] if info else None)
        if error is not None:
            body["exception_type"] = type(error).__name__
            body["traceback"] = exception_structure(error)
        else:
            stack = values.get("traceback", getattr(record, "traceback", None))
            if isinstance(stack, list):
                body["traceback"] = stack
        return json.dumps(body, ensure_ascii=False, allow_nan=False)


class OperationalFileHandler(RotatingFileHandler):
    """Report a file failure once, without feeding the failed logger again."""
    def __init__(self, filename, *, max_bytes, backup_count):
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count,
                         encoding="utf-8", delay=True)
        self.write_failed = False

    def _open(self):
        Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        return os.fdopen(os.open(self.baseFilename, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600),
                         self.mode, encoding=self.encoding, errors=self.errors)

    def handleError(self, record):  # noqa: N802 -- logging API
        if self.write_failed:
            return
        self.write_failed = True
        try:
            sys.stderr.write(json.dumps({"timestamp": datetime.now(UTC).isoformat(),
                "level": "ERROR", "message": "operational_log_file_unavailable",
                "operation": "log_file_write", "file_saved": False,
                "exception_type": type(sys.exc_info()[1]).__name__}) + "\n")
            sys.stderr.flush()
        except Exception:  # noqa: BLE001 -- neither stderr nor disk may mask the business failure
            pass


def load_logging_profile(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("explicit_absolute_logging_profile_required")
    body = json.loads(path.read_text())
    if (set(body) != {"service", "instance", "directory", "level", "format", "max_bytes", "backup_count"}
            or body["format"] != "json" or body["level"] not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            or not Path(body["directory"]).is_absolute()
            or any(not isinstance(body[k], str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", body[k])
                   for k in ("service", "instance"))
            or any(type(body[k]) is not int or body[k] < 1 for k in ("max_bytes", "backup_count"))):
        raise ValueError("invalid_operational_logging_profile")
    return body


def configure_file_logging(path):
    profile = load_logging_profile(path)
    root = logging.getLogger()
    # Idempotent within a process; do not disturb test capture/foreign handlers.
    for handler in list(root.handlers):
        if getattr(handler, "_investigation_handler", False):
            root.removeHandler(handler)
            handler.close()
    filename = Path(profile["directory"]) / f'{profile["service"]}.{profile["instance"]}.{os.getpid()}.jsonl'
    file_handler = OperationalFileHandler(filename, max_bytes=profile["max_bytes"],
                                          backup_count=profile["backup_count"])
    formatter = OperationalFormatter(profile["service"], profile["instance"])
    for handler in (file_handler, logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formatter)
        handler.setLevel(profile["level"])
        handler._investigation_handler = True
        root.addHandler(handler)
    root.setLevel(profile["level"])
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    structlog.configure(
        processors=[structlog.contextvars.merge_contextvars, structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger, context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(), cache_logger_on_first_use=False,
    )
    logging.getLogger(__name__).info("operational_logging_configured", extra={"operation": "configure_logging"})
    return file_handler


class OperationalHTTPMiddleware:
    """Request association and failure locations; no request/response bodies."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        status = None

        async def capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        with log_context(correlation_id=uuid4(), operation="http_request", stage="http",
                         http_method=scope["method"]):
            try:
                await self.app(scope, receive, capture)
            except Exception:
                log_exception(logging.getLogger(__name__), "http_request_failed", extra={
                    "error_code": "service_unavailable", "route": getattr(scope.get("route"), "path", None)})
                raise
            if status is not None and status >= 500:
                logging.getLogger(__name__).error("http_error_response", extra={
                    "http_status": status, "route": getattr(scope.get("route"), "path", None)})
