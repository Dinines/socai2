"""Minimal reserved AI API contracts; successful Q behavior is deferred."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from .baseline_contracts import Contract

QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
TitleText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ConclusionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class AskCaseAI(Contract):
    operation_key: UUID
    question: QuestionText
    conversation_id: UUID | None = None


class SaveCaseAIAnswer(Contract):
    operation_key: UUID
    title: TitleText
    conclusion: ConclusionText


class AdoptCaseAIResult(Contract):
    operation_key: UUID
    expected_scope_revision: int = Field(ge=0)


class AIUnavailableDetail(Contract):
    code: Literal["case_ai_not_implemented"] = "case_ai_not_implemented"
    status: Literal["not_implemented"] = "not_implemented"
    message: str = "AI问答功能暂未实现；本次请求未执行、保存或采用任何结果。"


class AIUnavailable(Contract):
    detail: AIUnavailableDetail = Field(default_factory=AIUnavailableDetail)
