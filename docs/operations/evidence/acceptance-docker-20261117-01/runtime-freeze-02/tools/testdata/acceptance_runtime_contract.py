"""Explicit connection and execution contracts for a single acceptance part."""
from typing import Literal
from urllib.parse import urlsplit

from acceptance_contract import Control, Key, Text
from pydantic import Field, field_validator


class Execution(Control):
    schema_version: Literal["socai2.acceptance-execution.v1"]
    execution_id: Key
    time_policy: Literal["preserve"]


class HttpConnection(Control):
    base_url: Text
    tenant_id: Text
    timeout_seconds: float = Field(gt=0)
    page_size: int = Field(ge=1)
    fusion_ready_url: Text

    @field_validator("base_url", "fusion_ready_url")
    @classmethod
    def address(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("explicit HTTP address without credentials required")
        return value.rstrip("/")


class Topics(Control):
    alert: Text
    context: Text


class KafkaConnection(Control):
    producer_env_file: Text
    expected_bootstrap_servers: Text
    security_protocol: Literal["SSL", "SASL_SSL", "PLAINTEXT", "SASL_PLAINTEXT"]
    topics: Topics
    timeout_seconds: float = Field(gt=0, le=60)
    request_timeout_ms: int = Field(gt=0)


class PostgresConnection(Control):
    database_url_file: Text
    expected_database: Text
    expected_user: Text
    schema_name: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    ssl: Literal["require", "verify-ca", "verify-full", "disable"]
    connect_timeout_seconds: float = Field(gt=0)
    query_timeout_seconds: float = Field(gt=0)


class LakeConnection(Control):
    host: Text
    port: int = Field(ge=1, le=65535)
    database: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    table: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    user: Text
    password_file: Text
    secure: bool
    verify: bool
    ca_certs: str | None
    connect_timeout_seconds: float = Field(gt=0)
    read_timeout_seconds: float = Field(gt=0)
    query_timeout_seconds: int = Field(ge=1)

