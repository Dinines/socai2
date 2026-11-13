"""CSV representation and HTTP rejection; PG/TCP acceptance is recorded separately."""
import csv
import io
from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.api.v1.deps import CurrentUser, get_current_user
from app.socai2.list_export import ExportRows
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from investigation_http.csv_export import ALLOWED, columns_for, response
from investigation_http.dependencies import export_service


def test_csv_represents_null_empty_json_and_special_text_without_truncation():
    values = [None, "", 0, False, ["中文", "a,b"], "逗号,引号\"\n下一行", "=1+1", "  @SUM(A1)", "\\N", "'原文"]
    rows = [{"facts": {"title": x}} for x in values]
    result = ExportRows(rows, datetime(2026, 11, 13, tzinfo=UTC), 10000)
    rendered = response("alerts", ("facts.title",), result)
    assert rendered.body.startswith(b"\xef\xbb\xbf")
    decoded = list(csv.reader(io.StringIO(rendered.body.decode("utf-8-sig"), newline="")))
    assert decoded == [["facts.title"], ["\\N"], [""], ["0"], ["false"], ['["中文","a,b"]'],
        ['逗号,引号"\n下一行'], ["'=1+1"], ["'  @SUM(A1)"], ["\\\\N"], ["''原文"]]
    assert rendered.headers["x-export-count"] == "10"
    assert rendered.headers["x-export-schema"] == "socai2.list-export.v1"
    assert "attachment" in rendered.headers["content-disposition"]
    assert response("alerts", ("facts.title",), ExportRows(rows, result.observed_at, len(rendered.body))).body == rendered.body
    with pytest.raises(HTTPException) as error:
        response("alerts", ("facts.title",), ExportRows(rows, result.observed_at, len(rendered.body)-1))
    assert error.value.status_code == 413


@pytest.mark.asyncio
async def test_export_parameters_and_empty_csv_use_dedicated_routes(monkeypatch):
    from investigation_http.main import app as real_app
    for kind in ("alerts", "incidents", "cases"):
        assert all("tenant_id" not in f and "source_identity_key" not in f for f in ALLOWED[kind])
        for bad in ("", "missing", "facts.id,facts.id"):
            with pytest.raises(HTTPException):
                columns_for(kind, bad)

    app = real_app
    monkeypatch.setattr(app, "dependency_overrides", {})
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(UUID(int=3), UUID(int=1),
        "viewer", "export@example.invalid", scopes=["cases:read", "alerts:read"])
    class Empty:
        async def read(self, tenant, kind, query):
            return ExportRows([], datetime(2026, 11, 13, tzinfo=UTC), 10000)
    app.dependency_overrides[export_service] = Empty
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://synthetic.local") as client:
        for kind in ("alerts", "incidents", "cases"):
            path = f"/api/v1/socai2/{kind}/export"
            for params in ({"limit": "20"}, {"cursor": "x"}, {"before_id": str(UUID(int=1))},
                    {"offset": "0"}, {"unknown": "x"}, {"columns": ""}, {"sort_by": "invalid"},
                    {"time_from": "2026-11-13T00:00:00"},
                    {"time_from": "2026-11-13T00:00:00Z", "time_to": "2026-11-12T00:00:00Z"}):
                r = await client.get(path, params=params)
                assert r.status_code == 422, r.text
            r = await client.get(path)
            assert r.status_code == 200 and r.headers["x-export-count"] == "0"
            assert len(list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))) == 1
