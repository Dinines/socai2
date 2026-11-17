"""Explicit local profile. Read configuration never creates a ledger."""
import json
from pathlib import Path

from pydantic import Field, model_validator

from .models import Identifier, Record, Text


class Config(Record):
    ledger_root: Text
    environment_label: Identifier
    host: Text
    port: int = Field(ge=1, le=65535)
    default_limit: int = Field(ge=1)
    max_limit: int = Field(ge=1)
    max_document_bytes: int = Field(ge=1)
    max_evidence_bytes: int = Field(ge=1)
    max_cursor_bytes: int = Field(ge=1)

    @model_validator(mode="after")
    def page_limits(self):
        if self.default_limit > self.max_limit:
            raise ValueError("default limit exceeds maximum")
        return self

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        value = json.loads(path.read_text())
        config = cls.model_validate(value)
        root = Path(config.ledger_root)
        return config.model_copy(update={"ledger_root": str((path.parent / root).resolve())})
