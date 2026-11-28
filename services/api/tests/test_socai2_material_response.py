"""The frozen material DTO preserves number values and exact source text."""
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from investigation_http.adapters.material_response import material_response


@pytest.mark.asyncio
async def test_content_view_keeps_exact_numbers_and_existing_fields():
    content={"number":Decimal("0.12345678901234567890123456789"),"integer":123456789012345678901234567890}
    async def read():
        return {"metadata":{"received_at":datetime(2026,11,19,tzinfo=UTC)},"availability":"available",
                "content_json":content,"content_text":"Full original"}
    response=await material_response(read())
    value=json.loads(response.body,parse_float=Decimal)
    assert value["content_json"]==content
    assert set(value)=={"metadata","availability","content_json","content_text"}
    assert value["content_text"]=="Full original" and response.media_type=="application/json"
