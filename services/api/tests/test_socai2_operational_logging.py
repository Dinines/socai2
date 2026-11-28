"""Direct file/entrypoint checks, without business records or model calls."""
import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
import structlog
from app.core.operational_logging import (
    OperationalHTTPMiddleware,
    configure_file_logging,
    load_logging_profile,
    log_context,
    log_exception,
)


@pytest.fixture
def configured(tmp_path):
    root, previous = logging.getLogger(), structlog.get_config()
    old_handlers, old_level = list(root.handlers), root.level
    others = {name: (list(logging.getLogger(name).handlers), logging.getLogger(name).propagate,
                     logging.getLogger(name).level)
              for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine")}

    def setup(**changes):
        profile = {"service": "socai2-test", "instance": "fixture", "directory": str(tmp_path / "logs"),
                   "level": "INFO", "format": "json", "max_bytes": 20971520, "backup_count": 10, **changes}
        path = tmp_path / "logging.json"
        path.write_text(json.dumps(profile))
        return configure_file_logging(path), path

    yield setup
    for handler in list(root.handlers):
        if handler not in old_handlers:
            root.removeHandler(handler)
            handler.close()
    root.handlers, root.level = old_handlers, old_level
    for name, (handlers, propagate, level) in others.items():
        logger = logging.getLogger(name)
        logger.handlers, logger.propagate, logger.level = handlers, propagate, level
    structlog.configure(**previous)


def records(handler):
    return [json.loads(line) for line in Path(handler.baseFilename).read_text().splitlines()]


def test_new_failure_log_keeps_console_only_fallback_body_free():
    import io

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.Logger("console-only-fixture")
    logger.addHandler(handler)
    try:
        raise ValueError("private dependency body")
    except ValueError:
        log_exception(logger, "dependency_call_failed", extra={"operation": "read_source"})
    assert stream.getvalue().strip() == "dependency_call_failed"


def test_explicit_profile_and_fusion_copy(configured, tmp_path):
    _, path = configured()
    assert load_logging_profile(path)["max_bytes"] == 20971520
    with pytest.raises(ValueError):
        load_logging_profile("relative.json")
    profile = json.loads(path.read_text())
    profile["directory"] = "relative"
    path.write_text(json.dumps(profile))
    with pytest.raises(ValueError):
        load_logging_profile(path)
    root = Path(__file__).resolve().parents[3]
    assert (root / "services/api/app/core/operational_logging.py").read_bytes() == (
        root / "services/fusion/app/core/operational_logging.py").read_bytes()


def test_both_logging_facilities_save_context_and_exception_locations(configured, capsys):
    handler, _ = configured()
    with log_context(task_id="test-task", attempt_no=1, stage="input", retry_count=0):
        logging.getLogger(__name__).info("input_prepared", extra={"operation": "prepare_input"})
        try:
            try:
                raise OSError("private dependency body")
            except OSError as exc:
                raise RuntimeError("private wrapper body") from exc
        except RuntimeError:
            structlog.get_logger(__name__).error("input_failed", exc_info=True,
                operation="load_input", dependency="postgres", error_code="source_unavailable")
    saved = records(handler)
    assert saved[-1]["message"] == "input_failed" and saved[-2]["operation"] == "prepare_input"
    assert saved[-1]["task_id"] == "test-task" and saved[-1]["retry_count"] == 0
    assert saved[-1]["attempt_no"] == 1 and saved[-1]["dependency"] == "postgres"
    assert [e["exception_type"] for e in saved[-1]["traceback"]] == ["RuntimeError", "OSError"]
    assert all(e["frames"][0]["line"] > 0 for e in saved[-1]["traceback"])
    assert saved[-1]["timestamp"].endswith("+00:00")
    assert "private" not in Path(handler.baseFilename).read_text()
    assert '"message": "input_failed"' in capsys.readouterr().out
    assert Path(handler.baseFilename).stat().st_mode & 0o777 == 0o600


def test_concurrent_task_contexts_do_not_leak(configured):
    handler, _ = configured()

    async def emit(task, step):
        with log_context(task_id=task, run_id="test-run", step_id=step, stage="C4"):
            await asyncio.sleep(0)
            logging.getLogger(__name__).warning("tool_query_failed", extra={"dependency": "component_http"})

    async def together():
        await asyncio.gather(emit("task-one", "step-one"), emit("task-two", "step-two"))
        logging.getLogger(__name__).warning("service_dependency_failed")

    asyncio.run(together())
    saved = records(handler)
    assert {(r["task_id"], r["step_id"]) for r in saved if r["message"] == "tool_query_failed"} == {
        ("task-one", "step-one"), ("task-two", "step-two")}
    assert "task_id" not in saved[-1] and "run_id" not in saved[-1]


def test_real_rotation_and_process_separation(configured):
    handler, path = configured(max_bytes=600, backup_count=2)
    for _ in range(6):
        logging.getLogger(__name__).error("rotation_fixture_event")
    files = list(Path(handler.baseFilename).parent.glob(Path(handler.baseFilename).name + "*"))
    assert len(files) == 3
    assert all(json.loads(line)["message"] for file in files for line in file.read_text().splitlines())
    script = ("import sys; from app.core.operational_logging import configure_file_logging; "
              "configure_file_logging(sys.argv[1])")
    for _ in range(2):
        subprocess.run([sys.executable, "-c", script, str(path)], check=True, capture_output=True,
                       env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])})
    main_files = list(Path(handler.baseFilename).parent.glob("*.jsonl"))
    assert len(main_files) == 3
    assert len({json.loads(file.read_text().splitlines()[0])["process"] for file in main_files}) == 3


def test_write_failure_reports_once_and_keeps_business_exception(configured, tmp_path, capsys):
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("existing file")
    handler, _ = configured(directory=str(blocked / "logs"))
    with pytest.raises(ValueError, match="original business failure"):
        try:
            raise ValueError("original business failure")
        except ValueError:
            logging.getLogger(__name__).exception("business_operation_failed")
            logging.getLogger(__name__).error("second_file_write")
            raise
    stderr = capsys.readouterr().err.splitlines()
    assert len(stderr) == 1 and json.loads(stderr[0])["file_saved"] is False
    assert handler.write_failed and not Path(handler.baseFilename).exists()
    assert blocked.read_text() == "existing file"


def test_http_failure_has_controlled_response_and_saved_association(configured):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from investigation_http.contracts import StoreError
    from investigation_http.errors import invoke_record

    handler, _ = configured()
    app = FastAPI()
    app.add_middleware(OperationalHTTPMiddleware)

    async def unavailable():
        raise StoreError("service_unavailable", 503)

    @app.get("/example/{subject_id}")
    async def read(subject_id: str):
        return await invoke_record(unavailable())

    response = TestClient(app).get("/example/private-identifier")
    assert response.status_code == 503 and "traceback" not in response.text
    saved = [r for r in records(handler) if r["message"] in {"http_use_case_failed", "http_error_response"}]
    assert len(saved) == 2 and saved[0]["correlation_id"] == saved[1]["correlation_id"]
    assert saved[-1]["route"] == "/example/{subject_id}"
    assert "private-identifier" not in Path(handler.baseFilename).read_text()


def test_component_transport_failure_keeps_run_step_and_existing_error(configured, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import httpx
    from app.socai2 import baseline_analysis_model, runtime_policy
    from app.socai2.model_errors import ModelCallError

    handler, _ = configured()
    monkeypatch.setattr(runtime_policy, "active_policy", lambda: SimpleNamespace(single_model_timeout_seconds=2))
    monkeypatch.setattr(baseline_analysis_model, "enforce_airgap_for_url", lambda _: None)
    monkeypatch.setattr(baseline_analysis_model, "safe_chat_completions_request", AsyncMock(
        side_effect=httpx.ConnectError("private upstream text")))
    gateway = baseline_analysis_model.TenantChatGateway()
    gateway.config = SimpleNamespace(base_url="https://fixture.invalid/v1", api_key="fixture-secret")
    with log_context(task_id="task-fixture", attempt_no=1, run_id="run-fixture", step_id="step-fixture", stage="C6"):
        with pytest.raises(ModelCallError):
            asyncio.run(gateway.complete({"model": "fixture", "messages": [], "max_tokens": 1,
                                         "response_format": {}}, 1))
    saved = [r for r in records(handler) if r["message"] == "model_http_call_failed"]
    assert len(saved) == 1 and saved[0]["run_id"] == "run-fixture" and saved[0]["step_id"] == "step-fixture"
    assert saved[0]["stage"] == "C6" and saved[0]["dependency"] == "model_http"
    assert saved[0]["exception_type"] == "ConnectError"
