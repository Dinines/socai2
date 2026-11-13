"""Read only this batch's Case/comment rows and compare persisted HTTP fields."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main(args):
    if args.environment:
        os.environ.update(json.loads(args.environment.read_text()))
    sys.path.insert(0, args.api_directory)
    from app.db.database import _normalize_async_pg_url
    from app.models import socai2 as m
    from app.socai2.baseline_service import BaselineService
    from app.socai2.case_comment_contracts import CaseCommentView
    from app.socai2.case_contracts import CaseView, RunView, project
    fixture = json.loads(args.fixture.read_text())
    url = os.environ['SOCAI2_CASE_DATABASE_URL']
    assert make_url(url).database == args.database
    url, opts = _normalize_async_pg_url(url)
    engine = create_async_engine(url, connect_args=opts)
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))
    tenant, cid, other = UUID(args.tenant), UUID(fixture['case_id']), UUID(fixture['other_case_id'])
    try:
        async with service.transaction(tenant, readonly=True) as store:
            identity = dict((await store.db.execute(text('SELECT current_database() AS database,current_user AS role'))).mappings().one())
            data = {}
            for name, model in [('cases',m.Cases),('comments',m.Comments),('runs',m.Runs),('tasks',m.Tasks),('task_revisions',m.TaskRevisions),('results',m.Results)]:
                table = model.__table__
                parent = table.c.id if name == 'cases' else table.c.case_id
                data[name] = [dict(r) for r in (await store.db.execute(select(table).where(*store.where(table, parent.in_([cid,other]))).order_by(table.c.id))).mappings()]
            A,T = m.Activities.__table__,m.ActivityTargets.__table__
            data['comment_activities'] = [dict(r) for r in (await store.db.execute(select(A).where(*store.where(A,A.c.subject_case_id==cid,A.c.action=='case_comment_created')).order_by(A.c.id))).mappings()]
            data['comment_targets'] = [dict(r) for r in (await store.db.execute(select(T).where(*store.where(T,T.c.activity_id.in_([r['id'] for r in data['comment_activities']]))).order_by(T.c.id))).mappings()]
        assert identity['database'] == args.database
        notes = [project(CaseCommentView, r).model_dump(mode='json') for r in data['comments']]
        assert sorted(notes,key=lambda r:r['id']) == sorted(fixture['comments'],key=lambda r:r['id'])
        case = next(r for r in data['cases'] if r['id'] == cid)
        assert project(CaseView,case).model_dump(mode='json') == fixture['case_after']
        run = next(r for r in data['runs'] if r['id'] == UUID(fixture['run']['id']))
        assert project(RunView,run).model_dump(mode='json') == fixture['run']
        assert len(data['runs']) == 2 and all(r['state']=='pending_update' for r in data['runs'])
        assert len(data['tasks']) == len(data['task_revisions']) == 1 and not data['results']
        assert data['task_revisions'][0]['state'] == fixture['task']['current']['state'] == 'not_started'
        assert len(data['comment_activities']) == 2 and len(data['comment_targets']) == 4
        print(json.dumps({'passed':True,'identity':identity,'rows':data,'models':0},default=str,ensure_ascii=False,indent=2))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--environment',type=Path)
    parser.add_argument('--api-directory',required=True)
    parser.add_argument('--database',required=True)
    parser.add_argument('--tenant',required=True)
    parser.add_argument('--fixture',type=Path,required=True)
    asyncio.run(main(parser.parse_args()))
