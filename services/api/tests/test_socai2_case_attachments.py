"""Direct attachment input and HTTP port checks; persistence is verified on PG."""
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from app.socai2.case_attachment_contracts import (
    CaseAttachmentCreate,
    CaseAttachmentPage,
    CaseAttachmentView,
)
from httpx import ASGITransport, AsyncClient
from investigation_http.dependencies import attachment_service
from investigation_http.main import app
from pydantic import ValidationError


def metadata():
    return {"operation_key": str(uuid4()), "file_id": "backend-file-01", "file_name": "维护工单.pdf",
        "mime_type": "application/pdf", "size_bytes": 120}


def test_attachment_metadata_is_reference_only():
    base = metadata()
    assert CaseAttachmentCreate(**base).model_dump(mode="json") == {**base, "sha256": None}
    for change in ({"file_id": " "}, {"file_name": "bad\nname"}, {"file_id": "https://example.invalid/file"},
        {"size_bytes": -1}, {"size_bytes": True}, {"size_bytes": 2**63}, {"sha256": "unknown"},
        {"created_by": str(uuid4())}, {"download_url": "https://example.invalid/"}):
        with pytest.raises(ValidationError):
            CaseAttachmentCreate(**(base | change))


def test_attachment_preserves_previous_59_contracts():
    before = json.loads((Path(__file__).resolve().parents[3] /
        "docs/operations/evidence/case-comments-20261113-01/candidate-openapi.json").read_text())
    after = app.openapi()
    assert all(after["paths"][p] == v for p, v in before["paths"].items()
               if p != "/api/v1/socai2/cases/{case_id}/results/{result_id}/adopt")
    assert all(after["components"]["schemas"][n] == v for n, v in before["components"]["schemas"].items() if n != "AdoptCaseAIResult")


@pytest.mark.asyncio
async def test_attachment_http_port_and_actor(monkeypatch):
    calls = []
    item = None

    class Files:
        async def create(self, tenant, case, request, *, actor):
            nonlocal item
            calls.append((tenant, case, actor.user_id))
            item = CaseAttachmentView(id=UUID(int=8), case_id=case,
                **request.model_dump(exclude={"operation_key"}), created_by=actor.user_id,
                created_at=datetime(2026, 11, 13, tzinfo=UTC),
                file_owner="business_backend", availability="managed_by_backend")
            return item

        async def list(self, tenant, case, *, limit, offset):
            return CaseAttachmentPage(items=[item], total=1, next_offset=None, observed_at=datetime.now(UTC))

        async def read(self, tenant, case, identity):
            assert identity == item.id
            return item

    monkeypatch.setattr(app, "dependency_overrides", dict(app.dependency_overrides))
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(UUID(int=3), UUID(int=1),
        "analyst", "attachments@example.invalid", scopes=["cases:read", "cases:write"])
    app.dependency_overrides[attachment_service] = Files
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
        path = f"/api/v1/socai2/cases/{UUID(int=7)}/attachments"
        response = await client.post(path, json=metadata())
        assert response.status_code == 200
        assert calls == [(UUID(int=1), UUID(int=7), UUID(int=3))]
        assert response.json()["availability"] == "managed_by_backend"
        assert (await client.get(path)).json()["items"] == [response.json()]
        assert (await client.get(path + "/" + response.json()["id"])).json() == response.json()
        for query in ({"limit": 0}, {"offset": -1}, {"q": "x"}):
            assert (await client.get(path, params=query)).status_code == 422
