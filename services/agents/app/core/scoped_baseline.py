"""Optional first-start endpoint restriction; original route auth still runs."""
import json
import os
import re


def enabled():
    return os.getenv("AISOC_SCOPED_BASELINE", "0").lower() in {"1", "true"}


class ScopedBaselineMiddleware:
    def __init__(self, app, service):
        self.app = app
        self.stream_path = re.compile(r"/api/v1/investigations/[^/]+/stream") if service == "agents" else None
        common = [("GET", r"/(health|livez|readyz)")]
        surface = ([
            ("POST", r"/api/v1/cases/[^/]+/investigate"),
            ("POST", r"/api/v1/agent-runs"),
            ("GET", r"/api/v1/agent-runs/[^/]+"),
            ("GET", r"/api/v1/investigations/[^/]+"),
            ("GET", r"/api/v1/investigations/[^/]+/report\.(md|html|pdf)"),
        ] if service == "agents" else [
            ("GET", r"/api/v1/live-actions"),
            ("POST", r"/api/v1/live-actions/dry-run"),
        ])
        self.allowed = [(method, re.compile(pattern)) for method, pattern in common + surface]

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket" and not (
            self.stream_path and self.stream_path.fullmatch(scope["path"])
        ):
            await send({"type":"websocket.close", "code":1008})
            return
        if scope["type"] == "http" and not any(
            scope["method"] == method and pattern.fullmatch(scope["path"])
            for method, pattern in self.allowed
        ):
            body = json.dumps({"detail":"Endpoint unavailable in scoped baseline"}).encode()
            await send({"type":"http.response.start", "status":404,
                        "headers":[(b"content-type",b"application/json")]})
            await send({"type":"http.response.body", "body":body})
            return
        await self.app(scope, receive, send)


def apply_scope(app, service):
    if enabled():
        app.add_middleware(ScopedBaselineMiddleware, service=service)
