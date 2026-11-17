"""Explicit Case capacity and relationship paging policy."""
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .baseline_store import StoreError


@dataclass(frozen=True)
class CaseAllocationPolicy:
    max_alerts: int
    source_page_size: int
    default_limit: int
    max_limit: int

    def __post_init__(self):
        if (any(type(v) is not int or v <= 0 for v in vars(self).values())
                or self.default_limit > self.max_limit):
            raise ValueError("invalid case allocation policy")

    @classmethod
    def load(cls):
        try:
            path = Path(os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"])
            if not path.is_absolute():
                raise ValueError("explicit absolute profile path required")
            body = json.loads(path.read_text())
            case = body.pop("case")
            if set(case) != {"max_alerts"}:
                raise ValueError("invalid case capacity")
            return cls(**case, **body)
        except (KeyError, OSError, ValueError, TypeError):
            raise StoreError("service_unavailable", 503) from None

    def page_size(self, limit):
        value = self.default_limit if limit is None else limit
        if type(value) is not int or not 1 <= value <= self.max_limit:
            raise StoreError("invalid_input", 422)
        return value
