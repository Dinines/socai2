"""Control-side schemas for the acceptance CLI; never model inputs."""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

PartID = Annotated[str, Field(pattern=r"^part[1-9][0-9]*$")]
Key = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")]
Text = Annotated[str, Field(min_length=1)]


class Control(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Part(Control):
    id: PartID
    check_level: Literal["alert", "incident", "case"]
    context_required: bool


class CasePlan(Control):
    key: Key
    title: Text
    create_after_part: PartID
    scope: Literal["incident", "alerts"]
    alert_refs: list[Text] = Field(min_length=1)
    check_after_parts: list[PartID]


class Scenario(Control):
    schema_version: Literal["socai2.acceptance-scenario.v1"]
    scenario_id: Key
    title: Text
    parts: list[Part] = Field(min_length=1)
    cases: list[CasePlan]


class ConnectionFiles(Control):
    http: Text
    kafka: Text
    postgres: Text
    lake: Text

    @field_validator("*")
    @classmethod
    def absolute_path(cls, value: str) -> str:
        if not value.startswith("/") or "\x00" in value or ".." in value.split("/"):
            raise ValueError("use an absolute configuration file path")
        return value


class Limits(Control):
    max_alerts_per_part: int = Field(ge=1)
    max_context_events_per_part: int = Field(ge=0)


class Timing(Control):
    send_interval_seconds: float = Field(ge=0)
    poll_interval_seconds: float = Field(gt=0)
    part_timeout_seconds: float = Field(gt=0)


class Profile(Control):
    schema_version: Literal["socai2.acceptance-profile.v1"]
    profile_id: Key
    environment_label: Text
    tenant_id: str
    connection_files: ConnectionFiles
    limits: Limits
    timing: Timing

    @field_validator("tenant_id")
    @classmethod
    def canonical_tenant(cls, value: str) -> str:
        if str(UUID(value)) != value:
            raise ValueError("tenant_id must be a canonical UUID")
        return value


class PartSource(Control):
    id: PartID
    alerts: list[Text] = Field(min_length=1)
    context: list[Text]


class Recipe(Control):
    schema_version: Literal["socai2.acceptance-conversion.v1"]
    source_format: Literal["streaming-v2", "alert-scenarios-v2"]
    scenario: Scenario
    parts: list[PartSource] = Field(min_length=1)
