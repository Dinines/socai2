"""Internal execution boundary, bounded error classification and small completion receipts."""
import asyncio
import errno
import json
import socket
import ssl
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

import httpx


@dataclass(frozen=True)
class Material:
    digest: str
    value: Any
    capacity_changed: bool = False
    unchanged_from_attempt_id: UUID | None = None
    unchanged_from_stopped_task_id: UUID | None = None


@dataclass(frozen=True)
class Outcome:
    outcome: str
    error_code: str | None = None
    error_stage: str | None = None
    error_detail: dict | None = None
    retryable: bool = False
    retry_after: datetime | None = None

    def __post_init__(self):
        if self.outcome not in {"completed", "failed", "unknown"} or (self.outcome != "completed" and not self.error_code):
            raise ValueError("invalid execution outcome")
        if self.error_detail is not None and (not isinstance(self.error_detail, dict)
                or set(self.error_detail) - {"exception_type", "http_status", "stage", "code"}
                or any(not isinstance(v, (str, int, bool)) for v in self.error_detail.values())):
            raise ValueError("invalid sanitized outcome detail")
        if self.retry_after is not None and (not isinstance(self.retry_after, datetime) or self.retry_after.tzinfo is None):
            raise ValueError("invalid retry-after timestamp")


class ExecutionFailure(Exception):
    """Adapter supplies known execution facts, never inferred from a status alone."""
    def __init__(self, code, *, stage, not_executed=False, known_failed=False,
                 temporary=False, status_code=None, retry_after=None):
        self.code, self.stage = code, stage
        self.not_executed, self.known_failed, self.temporary = not_executed, known_failed, temporary
        self.status_code, self.retry_after = status_code, retry_after
        super().__init__(code)


def classify_failure(error, *, stage, deadline=False):
    from .model_errors import ModelCallError
    detail = {"exception_type": type(error).__name__}
    if deadline:
        return Outcome("unknown", "call_timeout", stage, detail)
    if isinstance(error, ModelCallError):
        reported = error.details
        detail = {"exception_type": reported.get("exception_type", "ModelCallError")}
        status = reported.get("http_status")
        if type(status) is int:
            detail["http_status"] = status
        if detail["exception_type"] in {"ConnectTimeout", "PoolTimeout"}:
            return Outcome("failed", "service_unavailable", stage, detail, True)
        if error.rejection_code or status in {400, 401, 403, 404, 422}:
            return Outcome("failed", error.rejection_code or "invalid_input", stage, detail)
        return Outcome("unknown", "call_timeout" if detail["exception_type"] == "ReadTimeout" else "model_transport_error", stage, detail)
    if isinstance(error, ExecutionFailure):
        if error.status_code is not None:
            detail["http_status"] = error.status_code
        known = error.not_executed or error.known_failed
        return Outcome("failed" if known else "unknown", error.code, error.stage, detail,
            known and error.temporary and error.status_code not in {400, 401, 403, 404, 422}, error.retry_after)
    if isinstance(error, (httpx.PoolTimeout, httpx.ConnectTimeout, ConnectionRefusedError)):
        return Outcome("failed", "service_unavailable", stage, detail, True)
    if isinstance(error, OSError) and error.errno in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
        return Outcome("failed", "service_unavailable", stage, detail, True)
    if isinstance(error, socket.gaierror) and error.errno == socket.EAI_AGAIN:
        return Outcome("failed", "service_unavailable", stage, detail, True)
    if isinstance(error, (TimeoutError, httpx.ReadTimeout, httpx.ReadError, httpx.WriteError, httpx.WriteTimeout,
                          httpx.RemoteProtocolError, asyncio.CancelledError)):
        return Outcome("unknown", "call_timeout" if isinstance(error, (TimeoutError, httpx.ReadTimeout)) else "execution_unknown", stage, detail)
    if isinstance(error, (ssl.SSLError, ValueError, TypeError, httpx.InvalidURL)):
        return Outcome("failed", "invalid_input", stage, detail)
    # A bare HTTP 5xx/ConnectError does not establish whether execution happened.
    return Outcome("failed" if stage == "input" else "unknown", "execution_failed", stage, detail)


class Executor(Protocol):
    async def load(self, task: dict) -> Material: ...
    async def execute(self, context, material: Material) -> Outcome: ...


@dataclass
class Completion:
    task: dict
    attempt_id: UUID | None
    ended_at: datetime
    result: Outcome | None = None
    action: str = "finish"
    preparation_started_at: datetime | None = None

    def document(self):
        # Identity/short sanitized outcome only; no inputs, models, credentials or query bodies.
        task = {key: str(self.task[key]) for key in ("id", "tenant_id", "subject_id", "subject_type", "kind", "intent")}
        return {"task": task, "attempt_id": str(self.attempt_id) if self.attempt_id else None,
                "ended_at": self.ended_at.isoformat(), "action": self.action,
                "preparation_started_at": self.preparation_started_at.isoformat() if self.preparation_started_at else None,
                "result": asdict(self.result) if self.result else None}

    @classmethod
    def from_document(cls, value):
        task = value["task"]
        for key in ("id", "tenant_id", "subject_id"):
            task[key] = UUID(task[key])
        result = value["result"]
        if result and result["retry_after"]:
            result["retry_after"] = datetime.fromisoformat(result["retry_after"])
        return cls(task, UUID(value["attempt_id"]) if value["attempt_id"] else None,
            datetime.fromisoformat(value["ended_at"]), Outcome(**result) if result else None, value["action"],
            datetime.fromisoformat(value["preparation_started_at"]) if value["preparation_started_at"] else None)


class CompletionFiles:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)

    def put(self, receipt):
        path = self.directory / (str(receipt.task["id"]) + ".json")
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt.document(), ensure_ascii=False, default=str) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)

    def load(self):
        return [Completion.from_document(json.loads(p.read_text())) for p in self.directory.glob("*.json")]

    def remove(self, receipt):
        (self.directory / (str(receipt.task["id"]) + ".json")).unlink(missing_ok=True)
