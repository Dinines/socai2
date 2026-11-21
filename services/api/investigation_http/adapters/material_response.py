"""HTTP serialization adapter preserving numbers in the existing ContentView."""
from decimal import Decimal

from app.socai2.material_json import dumps
from fastapi.encoders import jsonable_encoder
from starlette.responses import Response

from investigation_http.contracts import ContentView
from investigation_http.errors import invoke


async def material_response(call):
    value = ContentView.model_validate(await invoke(call)).model_dump(mode="python")
    content = dumps(jsonable_encoder(value,custom_encoder={Decimal:lambda value:value}))
    return Response(content=content,media_type="application/json")
