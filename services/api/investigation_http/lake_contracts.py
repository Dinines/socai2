"""Lake read-only HTTP views; shared business contracts live in the core."""
from typing import Any, Literal

from investigation_http.contracts import (
    LakeEventView,
    LakeMaterial,
    LakeModel,
    LakeReadError,
    LakeRecordRef,
    LakeSearch,
    LakeSearchResult,
)


class LakeEventHttpView(LakeEventView):
    material_url: str


class LakeSearchHttpResult(LakeSearchResult):
    items: list[LakeEventHttpView]


class LakeHttpError(LakeModel):
    code: str
    state: Literal["failed", "unknown", "unavailable", "not_found"]


class LakeErrorResponse(LakeModel):
    detail: LakeHttpError | list[dict[str, Any]]


__all__ = ["LakeErrorResponse", "LakeMaterial", "LakeReadError", "LakeRecordRef", "LakeSearch", "LakeSearchHttpResult"]
