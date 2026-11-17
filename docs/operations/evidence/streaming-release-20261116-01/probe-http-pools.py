"""Run inside the selected HTTP candidate with its real environment and pools.

Empty-database connection/transaction check only; no successful business write.
The UPDATE matches zero rows and the writer transaction is rolled back.
"""
import asyncio
import json
import traceback

from sqlalchemy import text

from app.db.case_database import get_case_write_sessions
from app.db.database import engine
from investigation_http.main import app, configured_database_name


IDENTITY = text("""SELECT current_database() AS database,
 current_user AS current_user, session_user AS session_user,
 current_setting('transaction_read_only') AS transaction_read_only,
 r.rolsuper, r.rolbypassrls, r.rolcreaterole, r.rolcreatedb,
 s.ssl, s.version AS tls_version
 FROM pg_roles r JOIN pg_stat_ssl s ON s.pid=pg_backend_pid()
 WHERE r.rolname=current_user""")
COUNTS = text("""SELECT
 (SELECT count(*) FROM socai2.alerts) AS alerts,
 (SELECT count(*) FROM socai2.incidents) AS incidents,
 (SELECT count(*) FROM socai2.cases) AS cases,
 (SELECT count(*) FROM socai2.analysis_tasks) AS analysis_tasks,
 (SELECT count(*) FROM socai2.runs) AS runs""")


async def check_identity(connection, expected, username, readonly):
    row = dict((await connection.execute(IDENTITY)).mappings().one())
    assert row['database'] == expected
    assert row['current_user'] == row['session_user'] == username
    assert not any(row[k] for k in ('rolsuper', 'rolbypassrls', 'rolcreaterole', 'rolcreatedb'))
    assert row['ssl'] is True and row['tls_version']
    assert row['transaction_read_only'] == ('on' if readonly else 'off')
    return row


async def main():
    async with app.router.lifespan_context(app):
        context = app.state.business_context
        tenant = {'tenant': str(context.tenant_id)}
        expected = configured_database_name()
        async with engine.connect() as conn:
            await conn.execute(text('SET TRANSACTION READ ONLY'))
            await conn.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), tenant)
            reader = await check_identity(conn, expected, engine.url.username, True)
            before = dict((await conn.execute(COUNTS)).mappings().one())
            assert not any(before.values()), 'candidate_not_empty'
            actor = (await conn.execute(text("""SELECT id,tenant_id,username FROM public.users
                WHERE id=CAST(:actor AS uuid) AND tenant_id=CAST(:tenant AS uuid)"""),
                {**tenant, 'actor': str(context.user_id)})).mappings().one()
            assert str(actor['id']) == str(context.user_id) and str(actor['tenant_id']) == str(context.tenant_id)
            # actor_name is the configured display label, not the database login name.
            await conn.rollback()
        sessions = get_case_write_sessions()
        async with sessions() as session:
            await session.begin()
            await session.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), tenant)
            writer = await check_identity(session, expected, sessions.kw['bind'].url.username, False)
            access = dict((await session.execute(text("""SELECT
                has_table_privilege(current_user,'socai2.cases','INSERT') AS case_insert,
                has_table_privilege(current_user,'socai2.cases','UPDATE') AS case_update,
                has_table_privilege(current_user,'socai2.analysis_tasks','INSERT') AS task_insert"""))).mappings().one())
            assert all(access.values())
            touched = (await session.execute(text('UPDATE socai2.cases SET title=title WHERE false'))).rowcount
            assert touched == 0
            await session.rollback()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), tenant)
            after = dict((await conn.execute(COUNTS)).mappings().one())
            assert after == before
            await conn.rollback()
        return {'status': 'passed', 'reader': reader, 'writer': writer,
            'context': {'tenant_id': str(context.tenant_id), 'actor_id': str(context.user_id), 'actor_name': context.email},
            'writer_access': access, 'before_counts': before, 'after_counts': after,
            'update_matched_rows': touched, 'writer_rolled_back': True,
            'business_writes_committed': 0, 'business_http_write_verified': False,
            'model_calls': 0, 'kafka_messages': 0,
            'scope': 'real application pools in a probe process within the running formal container', 'actor_record_matches_context_identity': True}


if __name__ == '__main__':
    try:
        receipt = asyncio.run(main())
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
            'sqlstate': getattr(getattr(exc, 'orig', exc), 'sqlstate', None), 'frames':[{'file':f.filename,'line':f.lineno,'function':f.name} for f in traceback.extract_tb(exc.__traceback__)]}))
        raise SystemExit(1) from None
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
