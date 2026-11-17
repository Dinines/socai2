"""Existing local non-TLS fixture: ordinary login, actual HTTP pools, rollback only."""
import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ["services/api/app/db/database.py", "services/api/app/db/case_database.py",
           "services/api/investigation_http/adapters/runtime.py"]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


async def verify(config, result):
    import httpx
    from sqlalchemy import URL, text
    from sqlalchemy.ext.asyncio import create_async_engine

    db = json.loads(Path(config["writer_profile"]).read_text())
    source = json.loads(Path(config["source_receipt"]).read_text())
    assert db["sslmode"] == "disable", "This fixture is explicitly non-TLS"
    password = Path(db["password_file"]).read_text().strip()
    url = URL.create("postgresql+asyncpg", username=db["user"], password=password,
                     host=db["host"], port=db["port"], database=db["database"], query={"sslmode": db["sslmode"]})
    environment = json.loads(Path(config["application_environment"]).read_text())
    os.environ.update(environment)
    for key in ("PGPASSWORD", "PGPASSFILE", "PGSSLROOTCERT", "PGSSLCERT", "PGSSLKEY"):
        os.environ.pop(key, None)
    os.environ.update(config["http_environment"])
    os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),
                      SOCAI2_CASE_DATABASE_URL=url.render_as_string(hide_password=False),
                      SOCAI2_SERVICE_DATABASE_NAME=db["database"],
                      SOCAI2_HTTP_CONTEXT_FILE=config["context_file"])
    sys.path.insert(0, str(ROOT / "services/api"))
    from app.db.case_database import get_case_write_sessions
    from app.db.database import AsyncSessionLocal, _normalize_async_pg_url
    from investigation_http.main import app

    async def scope(session, *, readonly):
        if readonly:
            await session.execute(text("SET TRANSACTION READ ONLY"))
        await session.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
                              {"tenant": source["tenant_id"]})

    async def snapshot():
        async with AsyncSessionLocal() as session, session.begin():
            await scope(session, readonly=True)
            row = (await session.execute(text("SELECT to_jsonb(c) FROM socai2.cases c WHERE id=:case AND tenant_id=:tenant"),
                                         {"case": source["case_id"], "tenant": source["tenant_id"]})).scalar_one()
            return row

    async def identity(session):
        return dict((await session.execute(text("""SELECT current_database() AS database,
            session_user AS login_role, current_user AS effective_role,
            inet_server_addr()::text AS server_address, r.rolsuper, r.rolbypassrls,
            s.ssl FROM pg_roles r JOIN pg_stat_ssl s ON s.pid=pg_backend_pid()
            WHERE r.rolname=session_user"""))).mappings().one())

    result["target"] = {key: db[key] for key in ("host", "port", "database", "user", "sslmode")}
    result["fixture"] = {key: source[key] for key in ("tenant_id", "actor_id", "case_id")}
    result["credential_usage"] = "same ordinary LOGIN account on two real HTTP pools; no SET ROLE"
    async with app.router.lifespan_context(app):
        writer = get_case_write_sessions()
        assert writer is not AsyncSessionLocal
        result["lifespan"] = "actual_reader_and_writer_connections_passed"
        async with AsyncSessionLocal() as session:
            result["reader_identity"] = await identity(session)
        async with writer() as session:
            result["writer_identity"] = await identity(session)
        for key in ("reader_identity", "writer_identity"):
            info = result[key]
            assert info["database"] == db["database"]
            assert info["login_role"] == info["effective_role"] == db["user"]
            assert info["ssl"] is False and not info["rolsuper"] and not info["rolbypassrls"]
        before = await snapshot()
        assert before["title"] != config["temporary_title"], "use a distinct rollback marker"
        endpoint = f"/api/v1/socai2/cases/{source['case_id']}/management"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://verification.invalid") as client:
            response = await client.get(endpoint)
            result["http_before"] = {"path": endpoint, "status": response.status_code}
            assert response.status_code == 200
            result["http_before"]["sha256"] = digest(response.json())
            async with writer() as session:
                await session.begin()
                try:
                    await scope(session, readonly=False)
                    row = (await session.execute(text("""UPDATE socai2.cases SET title=:title
                        WHERE id=:case AND tenant_id=:tenant RETURNING title"""),
                        {"title": config["temporary_title"], "case": source["case_id"],
                         "tenant": source["tenant_id"]})).scalar_one()
                    assert row == config["temporary_title"]
                    readback = (await session.execute(text("SELECT title FROM socai2.cases WHERE id=:case"),
                                                     {"case": source["case_id"]})).scalar_one()
                    assert readback == row
                    result["write_in_transaction"] = {"state": "passed", "rows": 1,
                                                      "readback_matches": True, "committed": False}
                finally:
                    await session.rollback()
                    result["rollback_completed"] = True
            after = await snapshot()
            assert before == after
            result["case_row_before_sha256"] = digest(before)
            result["case_row_after_sha256"] = digest(after)
            response = await client.get(endpoint)
            result["http_after"] = {"path": endpoint, "status": response.status_code}
            assert response.status_code == 200
            result["http_after"]["sha256"] = digest(response.json())
            assert result["http_before"] == result["http_after"]

    invalid = url.set(password=password + config["invalid_password_suffix"])
    normalized, options = _normalize_async_pg_url(invalid.render_as_string(hide_password=False))
    options.update(timeout=db["connect_timeout_seconds"])
    engine = create_async_engine(normalized, connect_args=options, hide_parameters=True, echo=False)
    try:
        try:
            async with engine.connect():
                raise AssertionError("wrong_password_accepted")
        except Exception as exc:  # noqa: BLE001 -- retain type/SQLSTATE, never credential-bearing text.
            code = getattr(exc, "sqlstate", None) or getattr(getattr(exc, "orig", None), "sqlstate", None)
            result["wrong_password"] = {"exception_type": type(exc).__name__, "sqlstate": code}
            assert code == "28P01"
            result["wrong_password"]["state"] = "passed"
    finally:
        await engine.dispose()


def main(args):
    assert not args.output.exists(), "new receipt required"
    config = json.loads(args.config.read_text())
    result = {"state": "started", "observed_at": datetime.now(UTC).isoformat(),
              "mode": "actual_local_PG_non_TLS_HTTP_ASGI_and_rollback",
              "source_sha256_before": hashes(), "model_calls": 0, "business_commits": 0,
              "new_cases": 0, "new_runs": 0, "kafka_messages": 0, "http_socket_started": False}
    try:
        asyncio.run(verify(config, result))
        result["source_sha256_after"] = hashes()
        assert result["source_sha256_before"] == result["source_sha256_after"]
        result["state"] = "passed"
    except Exception as exc:  # noqa: BLE001 -- save sanitized failure and preserve original attempt.
        result.update(state="failed", error_type=type(exc).__name__)
    with args.output.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"state": result["state"], "receipt": str(args.output)}, ensure_ascii=False))
    return 0 if result["state"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    sys.exit(main(parser.parse_args()))
