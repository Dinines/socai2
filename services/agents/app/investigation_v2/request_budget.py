"""One complete-message byte contract for preparation and final dispatch.

This is a retention/input byte bound, not a tokenizer or provider HTTP size.
No message repair, evidence clipping, budget reservation or I/O occurs here.
"""
from dataclasses import dataclass
import json

from app.llm.contract_rules import LLMInputContract
from .execution_state import ExecutionRejected
from .execution_store import canonical_json

MAX_INPUT_BYTES = 12 * 1024


class RequestBudgetExceeded(ExecutionRejected):
    def __init__(self, input_bytes: int):
        super().__init__("complete_model_messages_exceed_byte_limit")
        self.details = {"input_bytes": input_bytes, "limit_bytes": MAX_INPUT_BYTES,
                        "excess_bytes": input_bytes - MAX_INPUT_BYTES,
                        "unit": "canonical_messages_utf8_bytes"}


@dataclass(frozen=True)
class CheckedModelInput:
    canonical_messages: str

    @property
    def input_bytes(self) -> int:
        return len(self.canonical_messages.encode("utf-8"))

    @property
    def messages(self) -> list:
        return json.loads(self.canonical_messages)


def serialized_message_bytes(messages) -> int:
    """Measurement only; callers must use checked_model_input before dispatch."""
    return len(canonical_json(LLMInputContract.validate(messages)).encode("utf-8"))


def checked_model_input(messages) -> CheckedModelInput:
    body = canonical_json(LLMInputContract.validate(messages))
    size = len(body.encode("utf-8"))
    if size > MAX_INPUT_BYTES:
        raise RequestBudgetExceeded(size)
    return CheckedModelInput(body)
