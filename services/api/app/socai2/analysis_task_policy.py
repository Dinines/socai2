"""Explicit lifecycle policy; no implicit environment or database fallback."""
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .baseline_store import StoreError


@dataclass(frozen=True)
class AnalysisTaskPolicy:
    retry_limit: int
    retry_delay_seconds: int
    automatic_window_seconds: int
    incident_check_interval_seconds: int
    case_check_interval_seconds: int
    default_limit: int
    max_limit: int

    def __post_init__(self):
        values = asdict(self)
        if (any(type(v) is not int or v < 0 for v in values.values())
                or any(values[k] == 0 for k in values if k not in {"retry_limit", "retry_delay_seconds"})
                or self.default_limit > self.max_limit):
            raise ValueError("invalid analysis task policy")

    @classmethod
    def load(cls):
        try:
            path = Path(os.environ["SOCAI2_ANALYSIS_TASKS_CONFIG_FILE"])
            if not path.is_absolute():
                raise ValueError("explicit absolute profile path required")
            return cls(**json.loads(path.read_text()))
        except (KeyError, OSError, ValueError, TypeError):
            raise StoreError("service_unavailable", 503) from None

    def page_size(self, requested):
        value = self.default_limit if requested is None else requested
        if type(value) is not int or not 1 <= value <= self.max_limit:
            raise StoreError("invalid_input", 422)
        return value
