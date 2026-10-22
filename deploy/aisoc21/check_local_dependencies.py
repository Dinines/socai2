#!/usr/bin/env python3
"""Audit the shared local API/Agents environment without contacting services.

Declarations define required versions/extras; direct lock pins, with the
documented local instrumentation compatibility override, provide the install
input. Separate image locks have different transitive versions, so
this shared development environment is resolved together, never described as
identical to either deployment image. No private configuration is read.
"""
from __future__ import annotations

import argparse
from collections import deque
import importlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import sys
import tomllib

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[2]
LOCAL_COMPATIBILITY = {"sqlalchemy": {"version": "2.0.52",
    "reason": "SQLAlchemyInstrumentor 0.66b0 supports sqlalchemy>=1.0,<2.1; both service declarations allow 2.0.52"}}


def constraint(value: str) -> str:
    if value.startswith("^"):
        parts = [int(x) for x in value[1:].split(".")]
        parts += [0] * (3 - len(parts))
        index = next((i for i, x in enumerate(parts) if x), 2)
        upper = parts[:index] + [parts[index] + 1] + [0] * (2 - index)
        return ">=" + value[1:] + ",<" + ".".join(map(str, upper))
    if re.fullmatch(r"\d[\w.+-]*", value):
        return "==" + value
    return value if value != "*" else ""


def declarations() -> tuple[list[dict], dict]:
    records, locks = [], {}
    for service in ("api", "agents"):
        folder = ROOT / "services" / service
        poetry = tomllib.loads((folder / "pyproject.toml").read_text())["tool"]["poetry"]
        locks[service] = {canonicalize_name(p["name"]): p["version"]
            for p in tomllib.loads((folder / "poetry.lock").read_text())["package"]}
        groups = {"runtime": poetry["dependencies"], "dev": poetry["group"]["dev"]["dependencies"]}
        for group, deps in groups.items():
            for name, value in deps.items():
                if name == "python":
                    continue
                data = value if isinstance(value, dict) else {"version": value}
                records.append({"service": service, "group": group, "name": canonicalize_name(name),
                    "constraint": constraint(data["version"]), "extras": data.get("extras", []),
                    "optional": bool(data.get("optional")), "locked": locks[service][canonicalize_name(name)]})
    return records, locks


def audit() -> tuple[dict, list[str]]:
    records, locks = declarations()
    required = {r["name"] for r in records if not r["optional"]}
    pins, direct = {}, []
    for record in records:
        if record["name"] not in required:
            continue
        name = record["name"]
        # API wins the only different shared direct pin (PyJWT); validate
        # it against every declaration below rather than silently overriding.
        pins.setdefault(name, LOCAL_COMPATIBILITY.get(name, {}).get("version", record["locked"]))
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = None
        direct.append({**record, "installed": installed, "selected_pin": pins[name], "pin_matches": installed == pins[name],
            "satisfied": installed is not None and SpecifierSet(record["constraint"]).contains(installed, prereleases=True)})
    requirements = []
    extras_by_name = {}
    for name in sorted(required):
        applicable = [r for r in records if r["name"] == name]
        assert all(SpecifierSet(r["constraint"]).contains(pins[name], prereleases=True) for r in applicable)
        extras = sorted({extra for r in applicable for extra in r["extras"]})
        extras_by_name[name] = extras
        requirements.append(name + ("[" + ",".join(extras) + "]" if extras else "") + "==" + pins[name])
    queue = deque((name, tuple(extras_by_name[name])) for name in sorted(required))
    seen, issues = set(), []
    while queue:
        name, extras = queue.popleft()
        key = (canonicalize_name(name), extras)
        if key in seen:
            continue
        seen.add(key)
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue  # A direct missing distribution is already recorded.
        for raw in dist.requires or []:
            req = Requirement(raw)
            contexts = [dict(default_environment(), extra=e) for e in ("", *extras)]
            if req.marker is not None and not any(req.marker.evaluate(ctx) for ctx in contexts):
                continue
            try:
                installed = metadata.version(req.name)
            except metadata.PackageNotFoundError:
                installed = None
            if installed is None or not req.specifier.contains(installed, prereleases=True):
                issues.append({"parent": dist.metadata["Name"], "requirement": str(req), "installed": installed})
            if installed is not None:
                queue.append((req.name, tuple(sorted(req.extras))))
    differing = [{"name": n, "api": locks["api"][n], "agents": locks["agents"][n]}
        for n in sorted(locks["api"].keys() & locks["agents"].keys()) if locks["api"][n] != locks["agents"][n]]
    report = {"python": platform.python_version(), "executable": sys.executable,
        "platform": platform.platform(), "scope": "API and Agents runtime + dev + declared required extras",
        "unique_direct_requirements": len(required), "declarations": direct,
        "direct_issues": [r for r in direct if not r["satisfied"]],
        "transitive_and_extra_issues": issues, "shared_lock_version_differences": differing,
        "local_compatibility_overrides": LOCAL_COMPATIBILITY,
        "installed": sorted({d.metadata["Name"]: d.version for d in metadata.distributions()}.items()),
        "satisfied": not any(not r["satisfied"] for r in direct) and not issues}
    return report, requirements


def smoke(service: str) -> dict:
    import asyncio
    import os
    import socket

    class NetworkForbidden(BaseException):
        pass

    def refuse(*args, **kwargs):
        raise NetworkForbidden("Dependency smoke check must not contact a network service")

    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse
    socket.create_connection = refuse
    socket.getaddrinfo = refuse
    for name in list(os.environ):
        if name.startswith(("OPENAI_", "LLM_", "LITELLM_", "ANTHROPIC_", "AISOC_")) or name in {"DATABASE_URL", "DATABASE_DSN", "REDIS_URL", "KAFKA_BOOTSTRAP_SERVERS", "QDRANT_URL"}:
            os.environ.pop(name, None)
    os.environ.update({"ENVIRONMENT": "test", "ENV": "test", "DEBUG": "false",
        "SECRET_KEY": "dependency-check-local-only-unused-secret",
        "DATABASE_URL": "postgresql+asyncpg://dependency_check:unused@127.0.0.1:1/dependency_check",
        "REDIS_URL": "redis://127.0.0.1:1/0", "OTEL_EXPORTER": "none", "AISOC_DETERMINISTIC": "1",
        "AISOC_TRIAGE_WORKER_ENABLED": "false", "AISOC_PLAYBOOK_SEED_DISABLE": "1",
        "AISOC_ATTCK_STARTUP_DISABLE": "1", "AISOC_ATTCK_INDEX_DISABLE": "1",
        "AISOC_HUNT_SCHEDULER_DISABLE": "1"})
    sys.path.insert(0, str(ROOT / "services" / service))
    modules = ["fastapi", "uvicorn", "pydantic", "email_validator", "sqlalchemy.ext.asyncio", "asyncpg",
        "greenlet", "redis.asyncio", "hiredis", "httpx", "jwt", "cryptography.fernet", "aiokafka.admin",
        "opentelemetry.instrumentation.fastapi", "neo4j", "clickhouse_driver", "weasyprint"]
    if service == "api":
        modules += ["alembic", "opentelemetry.instrumentation.sqlalchemy", "boto3", "sigma.backends.opensearch",
            "yara", "strawberry.fastapi", "webauthn", "onelogin.saml2.auth", "xmlsec", "lxml.etree", "croniter",
            "app.api.v1.endpoints.graph", "app.main"]
    else:
        modules += ["langchain", "langchain_openai", "langchain_community", "langgraph.graph",
            "langgraph.checkpoint", "langgraph_sdk", "mcp", "fastembed", "onnxruntime", "markdown",
            "opentelemetry.instrumentation.httpx", "app.context.bundle", "app.workers.fused_alert_consumer", "app.main"]
    results = []
    for name in modules:
        try:
            importlib.import_module(name)
            results.append({"module": name, "status": "passed"})
        except BaseException as exc:
            results.append({"module": name, "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:600]})

    async def sqlite_check():
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.connect() as conn:
                assert (await conn.execute(text("SELECT 1"))).scalar_one() == 1
        finally:
            await engine.dispose()

    try:
        asyncio.run(sqlite_check())
        results.append({"check": "sqlalchemy_async_greenlet_sqlite", "status": "passed"})
    except BaseException as exc:
        results.append({"check": "sqlalchemy_async_greenlet_sqlite", "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:600]})
    if service == "api":
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            instrumentor = SQLAlchemyInstrumentor()
            assert instrumentor.is_instrumented_by_opentelemetry
            results.append({"check": "sqlalchemy_tracing_instrumented", "status": "passed",
                "supported": list(instrumentor.instrumentation_dependencies())})
        except BaseException as exc:
            results.append({"check": "sqlalchemy_tracing_instrumented", "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:600]})
        try:
            from weasyprint import HTML
            rendered = HTML(string="<p>Local dependency check</p>").write_pdf()
            assert rendered.startswith(b"%PDF-")
            results.append({"check": "native_pango_cairo_memory_render", "status": "passed", "bytes": len(rendered)})
        except BaseException as exc:
            results.append({"check": "native_pango_cairo_memory_render", "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:600]})
    return {"service": service, "network_blocked": True, "lifespan_started": False,
        "probe_requests_no_models": True, "results": results, "satisfied": all(r["status"] == "passed" for r in results)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--requirements", type=Path)
    parser.add_argument("--smoke", choices=["api", "agents"])
    args = parser.parse_args()
    if args.smoke:
        report = smoke(args.smoke)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"service": args.smoke, "checks": len(report["results"]), "satisfied": report["satisfied"],
            "failed": [r for r in report["results"] if r["status"] != "passed"]}))
        sys.exit(0 if report["satisfied"] else 1)
    report, requirements = audit()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.requirements:
        args.requirements.write_text("# Shared local environment; API/Agents declarations and direct lock pins.\n# Local SQLAlchemy 2.0.52 override keeps instrumentation 0.66b0 within its supported <2.1 range.\n" +
            "\n".join(requirements) + "\n")
    print(json.dumps({k: report[k] for k in ("python", "unique_direct_requirements", "satisfied")} | {
        "missing_direct": len({r["name"] for r in report["direct_issues"] if r["installed"] is None}),
        "out_of_range_direct": len({r["name"] for r in report["direct_issues"] if r["installed"] is not None}),
        "transitive_or_extra_issues": len(report["transitive_and_extra_issues"]),
        "shared_lock_version_differences": len(report["shared_lock_version_differences"])}))
