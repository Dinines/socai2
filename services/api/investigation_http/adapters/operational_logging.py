"""Bind HTTP use-case failures to the existing structured exception logger."""

from app.core.operational_logging import log_exception


def log_service_error(logger, exc):
    if exc.status >= 500:
        log_exception(logger, "http_use_case_failed", extra={
            "operation": "http_use_case", "stage": "http", "error_code": exc.code,
            "http_status": exc.status})
