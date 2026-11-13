"""Direct HTTP input and boundary checks; persistence is verified on real PG."""
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from app.socai2.case_comment_contracts import (
    CaseCommentCreate,
    CaseCommentPage,
    CaseCommentView,
)
from httpx import ASGITransport, AsyncClient
from investigation_http.dependencies import comment_service
from investigation_http.main import app
from pydantic import ValidationError


def test_comment_preserves_original_text_and_rejects_blank_or_client_author():
    body = "  原文\n<script>text only</script>  "
    assert CaseCommentCreate(operation_key=uuid4(), body=body).body == body
    for extra in ({"body": "\n "}, {"body": "x" * 20001}, {"body": "ok", "author_id": str(uuid4())}):
        with pytest.raises(ValidationError):
            CaseCommentCreate(operation_key=uuid4(), **extra)


def test_comments_keep_existing_57_contracts():
    before = json.loads((Path(__file__).resolve().parents[3] /
        "docs/operations/evidence/case-comments-20261113-01/before-openapi.json").read_text())
    after = app.openapi()
    assert all(after["paths"][p] == value for p, value in before["paths"].items())
    assert all(after["components"]["schemas"][n] == value for n, value in before["components"]["schemas"].items())


@pytest.mark.asyncio
async def test_comment_http_uses_actor_and_port_and_validates_paging(monkeypatch):
    calls = []
    class Notes:
        async def create(self, tenant, case, request, *, actor):
            calls.append((tenant, case, actor, request))
            return CaseCommentView(id=UUID(int=8), case_id=case, body=request.body,
                author_id=actor.user_id, author_name_snapshot=actor.name,
                created_at=datetime(2026, 11, 13, tzinfo=UTC), edited_at=None, edited_by=None, row_version=1)

        async def list(self, tenant, case, *, limit, offset):
            return CaseCommentPage(items=[], total=0, next_offset=None, observed_at=datetime.now(UTC))
    monkeypatch.setattr(app, "dependency_overrides", dict(app.dependency_overrides))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(UUID(int=3), UUID(int=1),
        "analyst", "comments@example.invalid", scopes=["cases:read", "cases:write"])
    app.dependency_overrides[comment_service] = Notes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
        path = f"/api/v1/socai2/cases/{UUID(int=7)}/comments"
        result = await client.post(path, json={"operation_key": str(uuid4()), "body": "普通说明"})
        assert result.status_code == 200 and result.json()["author_name_snapshot"] == "comments@example.invalid"
        assert calls[0][:2] == (UUID(int=1), UUID(int=7))
        assert calls[0][2].user_id == UUID(int=3)
        assert (await client.get(path)).json()["total"] == 0
        for query in ({"limit": 0}, {"offset": -1}, {"q": "x"}):
            assert (await client.get(path, params=query)).status_code == 422
