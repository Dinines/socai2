"""Optional static read viewer; public settings contain no upstream connections."""
from pathlib import Path
from typing import Annotated

from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from . import __version__
from .models import Record

VIEWER_VERSION = __version__
WEB = Path(__file__).resolve().parent / "web"


class ViewerAssets(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


class ViewerConfig(Record):
    poll_interval_seconds: float = Field(gt=0, allow_inf_nan=False)
    request_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    page_size: int = Field(ge=1, le=100)
    test_source_prefixes: list[Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]] = Field(default_factory=list)

    @classmethod
    def load(cls, path):
        return cls.model_validate_json(Path(path).read_bytes())


def mount(app, config):
    @app.get("/", include_in_schema=False)
    @app.get("/index.html", include_in_schema=False)
    def entry():
        return RedirectResponse("/viewer/", headers={"Cache-Control": "no-store"})

    @app.get("/viewer/", include_in_schema=False)
    def index():
        return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/viewer/config.json", include_in_schema=False)
    def settings():
        return {"viewer_version": VIEWER_VERSION, **config.model_dump()}

    app.mount("/viewer/assets", ViewerAssets(directory=WEB), name="viewer-assets")
