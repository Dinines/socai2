"""One explicitly configured investigation environment; GET only, no retries."""
import hashlib
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import Field, model_validator

from .models import Identifier, Record, Text

PREFIX = "/api/v1/socai2/"
RESPONSE_HEADERS = {"content-type", "content-length", "content-disposition", "content-encoding",
                    "etag", "last-modified", "cache-control", "x-content-sha256", "x-request-id"}


class UpstreamConfig(Record):
    environment_label: Identifier
    tenant_id: UUID
    base_url: Text
    openapi_file: Text
    openapi_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    connect_timeout_seconds: float = Field(gt=0)
    read_timeout_seconds: float = Field(gt=0)
    max_connections: int = Field(ge=1)
    max_keepalive_connections: int = Field(ge=0)
    chunk_bytes: int = Field(ge=1)

    @model_validator(mode="after")
    def explicit_origin(self):
        url = urlsplit(self.base_url)
        if (url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password
                or url.path not in {"", "/"} or url.query or url.fragment):
            raise ValueError("upstream must be an explicit HTTP origin without credentials")
        if self.max_keepalive_connections > self.max_connections:
            raise ValueError("keepalive limit exceeds connection limit")
        return self

    @classmethod
    def load(cls, path):
        path = Path(path).resolve()
        config = cls.model_validate_json(path.read_bytes())
        return config.model_copy(update={"openapi_file": str((path.parent / config.openapi_file).resolve())})


class ReadProxy:
    def __init__(self, config, *, transport=None):
        self.config = config
        self.transport = transport
        self.client = None
        data = Path(config.openapi_file).read_bytes()
        if hashlib.sha256(data).hexdigest() != config.openapi_sha256:
            raise ValueError("upstream contract digest mismatch")
        schema = json.loads(data)
        self.routes = []
        for path, item in schema["paths"].items():
            if not path.startswith(PREFIX) or "get" not in item:
                continue
            if not re.fullmatch(r"/[A-Za-z0-9_/{}/-]+", path):
                raise ValueError("unsupported upstream path")
            expression = "".join("[A-Za-z0-9_-]+" if part.startswith("{") else re.escape(part)
                                 for part in re.split(r"(\{[A-Za-z0-9_]+\})", path))
            params = item.get("parameters", []) + item["get"].get("parameters", [])
            if any("$ref" in param for param in params):
                raise ValueError("unresolved upstream parameter")
            queries = {p["name"] for p in params if p["in"] == "query"}
            self.routes.append((path, re.compile(expression), queries))
        if not self.routes:
            raise ValueError("no investigation GET contract")
        self.routes.sort(key=lambda row: (row[0].count("{"), row[0]))

    def description(self):
        return {"environment_label": self.config.environment_label,
                "tenant_id": self.config.tenant_id, "contract_sha256": self.config.openapi_sha256,
                "get_operations": len(self.routes), "read_only": True, "runtime_verified": False}

    @asynccontextmanager
    async def lifespan(self, app):
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.read_timeout_seconds, connect=self.config.connect_timeout_seconds),
            limits=httpx.Limits(max_connections=self.config.max_connections,
                                max_keepalive_connections=self.config.max_keepalive_connections),
            follow_redirects=False, trust_env=False, transport=self.transport,
        ) as client:
            self.client = client
            try:
                yield
            finally:
                self.client = None

    def error(self, code, status):
        return JSONResponse({"detail": {"code": code, "source": "investigation_http_proxy",
            "environment": self.config.environment_label}}, status_code=status,
            headers={"X-Investigation-Environment": self.config.environment_label})

    async def forward(self, request: Request):
        path = request.url.path
        allowed = next((params for _, pattern, params in self.routes if pattern.fullmatch(path)), None)
        if allowed is None:
            return self.error("read_path_not_allowed", 404)
        if any(key not in allowed or len(request.query_params.getlist(key)) != 1 for key in request.query_params):
            return self.error("invalid_proxy_query", 422)
        if self.client is None:
            return self.error("proxy_not_started", 503)
        response = None
        try:
            upstream = self.client.build_request("GET", self.config.base_url.rstrip("/") + path,
                params=list(request.query_params.multi_items()), headers={"Accept-Encoding": "identity"})
            response = await self.client.send(upstream, stream=True)
            if 300 <= response.status_code < 400 and response.status_code != 304:
                await response.aclose()
                return self.error("upstream_redirect_rejected", 502)
            chunks = response.aiter_raw(self.config.chunk_bytes)
            first = await anext(chunks, b"")
        except httpx.TimeoutException:
            if response is not None:
                await response.aclose()
            return self.error("upstream_timeout", 504)
        except httpx.HTTPError:
            if response is not None:
                await response.aclose()
            return self.error("upstream_unavailable", 502)
        except BaseException:
            if response is not None:
                await response.aclose()
            raise

        async def body():
            try:
                if first:
                    yield first
                async for chunk in chunks:
                    yield chunk
            finally:
                await response.aclose()

        headers = {key: value for key, value in response.headers.items() if key in RESPONSE_HEADERS}
        headers["X-Investigation-Environment"] = self.config.environment_label
        headers["X-Investigation-Contract"] = self.config.openapi_sha256
        return StreamingResponse(body(), status_code=response.status_code, headers=headers)

    def mount(self, app):
        app.add_api_route(PREFIX + "{business_path:path}", self.forward,
                          methods=["GET"], include_in_schema=False)
