"""Shared explicit priority edits for Case and Incident, never Alert requests."""
from decimal import Decimal
from typing import Annotated

from pydantic import Field, StrictBool, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from .baseline_contracts import Contract

PriorityValue = Annotated[float, Field(ge=0, le=100, strict=True, allow_inf_nan=False, multiple_of=0.01)]


class PriorityManagementFields(Contract):
    priority_value: PriorityValue | SkipJsonSchema[None] = Field(default=None,
        description="人工优先级0–100（含0），最多两位小数；省略保持，不接受null；须priority_reason。",
        json_schema_extra=lambda s: s.pop('default', None))
    priority_reason: str | None = Field(default=None, min_length=1, max_length=20000,
        description="设置或撤销人工优先级的非空理由；不能单独提交。")
    clear_priority_override: StrictBool = Field(default=False,
        description="true显式撤销人工优先级并恢复当前等级映射；须priority_reason，与priority_value互斥；省略/false保持。")

    @field_validator("priority_value", mode="before")
    @classmethod
    def priority_not_null(cls, value):
        if value is None:
            raise ValueError("priority_value cannot be null; use clear_priority_override")
        return value

    @field_validator("priority_value")
    @classmethod
    def priority_precision(cls, value):
        number = Decimal(str(value))
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("priority_value supports at most two decimal places")
        return value

    @model_validator(mode="after")
    def explicit_priority(self):
        setting = "priority_value" in self.model_fields_set
        if setting and self.clear_priority_override:
            raise ValueError("priority_value and clear_priority_override are mutually exclusive")
        if setting or self.clear_priority_override:
            if not self.priority_reason or not self.priority_reason.strip():
                raise ValueError("priority change requires a nonblank priority_reason")
        elif "priority_reason" in self.model_fields_set:
            raise ValueError("priority_reason requires setting or clearing priority")
        return self
