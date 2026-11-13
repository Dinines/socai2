"""Direct synthetic list acceptance: normal TCP HTTP and local PostgreSQL.

Seed only the configured local validation database. Verify is GET/READ ONLY;
it never starts an investigation, model, consumer or retries a mutation.
"""
import argparse
import asyncio
import csv
import io
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


async def database(cfg, action, fixture_path):
    os.environ.update(json.loads((ROOT / cfg["environment"]).read_text()))
    sys.path.insert(0, str(ROOT / "services/api"))
    from sqlalchemy import insert, select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.db.database import _normalize_async_pg_url
    from app.models import socai2 as m
    from app.socai2.baseline_service import BaselineService

    url = os.environ["SOCAI2_CASE_DATABASE_URL"]
    assert make_url(url).database == cfg["database"]
    normalized, connect_args = _normalize_async_pg_url(url)
    engine = create_async_engine(normalized, connect_args=connect_args)
    tenant, actor = UUID(cfg["tenant_id"]), UUID(cfg["actor_id"])
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))
    tables = {kind: getattr(m, name).__table__ for kind, name in
              (("alerts", "Alerts"), ("incidents", "Incidents"), ("cases", "Cases"))}
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT current_database()"))).scalar_one() == cfg["database"]
        if action == "seed":
            assert cfg["local_seed_allowed"] and cfg["database"] != "aisoc"
            assert not fixture_path.exists()
            prefix = "SYNTHETIC list-export " + str(uuid4())
            data = {"q": prefix, "tenant_id": str(tenant), "actor_id": str(actor),
                    "ids": {kind: [str(uuid4()) for _ in range(55 if kind == "alerts" else 3)] for kind in tables}}
            write(fixture_path.with_suffix(".intent.json"), data)
            start = datetime.fromisoformat(cfg["fixture_time"])
            severity = ["info", "high", "high", "critical", None, "low", "info", "critical"]
            offsets = [0, 1, 1, 3, None, 5, -1, 6]
            async with service.transaction(tenant) as store:
                for kind, table in tables.items():
                    for i, identity in enumerate(data["ids"][kind]):
                        when = start + timedelta(hours=offsets[i % 8]) if offsets[i % 8] is not None else None
                        row = dict(id=UUID(identity), tenant_id=tenant,
                            title=f'{prefix} {kind} {i} 中文,"引用"\n下一行',
                            description=[None, "", r"\N", "=1+1", "'original"][i % 5],
                            owner_id=actor if i == 1 else None,
                            assignment_state="assigned" if i == 1 else "unresolved" if i == 2 else "unassigned",
                            owner_source_value="synthetic missing owner" if i == 2 else None,
                            handling_status="in_progress" if i == 1 else "unknown" if i == 2 else
                                ("completed" if kind == "alerts" else "resolved") if i == 3 else "new",
                            tags=["synthetic", prefix])
                        if kind == "alerts":
                            row.update(source_namespace="synthetic-list-export", source_identity_key=identity,
                                severity=severity[i % 8], event_time=when,
                                event_time_source="source" if when else "unknown",
                                ingested_at=start+timedelta(minutes=5-i))
                        elif kind == "incidents":
                            row.update(source_namespace="synthetic-list-export", source_incident_id=identity,
                                created_at=start+timedelta(minutes=5-i))
                            if i == 2:
                                row.update(severity_override="low", severity_override_reason="Synthetic override",
                                    severity_override_at=start, severity_override_by=actor)
                        else:
                            row.update(severity=severity[i % 8], created_at=start+timedelta(minutes=5-i),
                                business_updated_at=when or start+timedelta(hours=4))
                        await store.db.execute(insert(table).values(**row))
                for i, members in enumerate(((0,), (1, 2), (3,))):
                    for member in members:
                        await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant,
                            incident_id=UUID(data["ids"]["incidents"][i]), alert_id=UUID(data["ids"]["alerts"][member]),
                            membership_source="manual", source_operation_id=uuid4(),
                            correlation_basis={"synthetic": True}, basis_version="synthetic.list.v1"))
                for member in (0, 1):
                    await store.db.execute(insert(m.CaseAlerts).values(id=uuid4(), tenant_id=tenant,
                        case_id=UUID(data["ids"]["cases"][0]), alert_id=UUID(data["ids"]["alerts"][member]),
                        membership_source="manual", source_operation_id=uuid4()))
            write(fixture_path, data)
        else:
            data = json.loads(fixture_path.read_text())
        snapshot = {}
        async with service.transaction(tenant, readonly=True) as store:
            for kind, table in tables.items():
                rows = (await store.db.execute(select(table).where(*store.where(table,
                    table.c.id.in_([UUID(x) for x in data["ids"][kind]]))).order_by(table.c.id))).mappings()
                snapshot[kind] = [dict(r) for r in rows]
            links = m.IncidentAlerts.__table__
            snapshot["links"] = [dict(r) for r in (await store.db.execute(select(links).where(*store.where(links,
                links.c.incident_id.in_([UUID(x) for x in data["ids"]["incidents"]]))).order_by(links.c.id))).mappings()]
        links = m.CaseAlerts.__table__
        async with service.transaction(tenant, readonly=True) as store:
            snapshot["case_links"] = [dict(r) for r in (await store.db.execute(select(links).where(*store.where(links,
                links.c.case_id.in_([UUID(x) for x in data["ids"]["cases"]]))).order_by(links.c.id))).mappings()]
        if action == "limits":
            from app.socai2.list_export import ListExportService, ExportLimits
            from app.socai2.list_query_contracts import AlertListQuery
            from app.socai2.baseline_store import StoreError
            small = ListExportService(service.sessions, limits=ExportLimits(54, 16777216, 30000))
            try:
                await small.read(tenant, "alerts", AlertListQuery(q=data["q"]))
                raise AssertionError("row_limit_not_enforced")
            except StoreError as exc:
                assert exc.status == 413 and exc.code == "export_row_limit_exceeded"
        return json.loads(json.dumps(snapshot, default=str))
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seed','verify'])
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); cfg=json.loads(args.profile.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    before=asyncio.run(database(cfg,args.action,args.fixture));write(args.output/'sql-before.json',before)
    if args.action=='seed':
        print(json.dumps({'seeded':{k:len(v) for k,v in before.items()},'models':0}));return
    sys.path.insert(0,str(ROOT/'services/api'))
    from investigation_http.csv_export import ALLOWED, DEFAULTS, cell
    fixture=json.loads(args.fixture.read_text());token=json.loads((ROOT/cfg['credential']['file']).read_text())['api_key']
    calls=[]
    def get(kind, params, export=False, code=200, base=None):
        path='/api/v1/socai2/'+kind+('/export' if export else '')+'?'+urllib.parse.urlencode(params)
        req=urllib.request.Request((base or cfg['base_url'])+path,headers={'Authorization':'Bearer '+token})
        try:r=urllib.request.urlopen(req,timeout=cfg['timeout_seconds'])
        except urllib.error.HTTPError as exc:r=exc
        with r: status,headers,raw=r.code,{k.lower():v for k,v in r.headers.items()},r.read()
        body=raw.decode('utf-8-sig') if export and status==200 else json.loads(raw)
        calls.append(dict(path=path,base=base or cfg['base_url'],status=status,headers={k:v for k,v in headers.items() if k.lower().startswith(('content-','x-export'))},body=body))
        write(args.output/'responses.json',calls)
        assert status==code,(path,status,body)
        if export and code==200:
            assert raw.startswith(b'\xef\xbb\xbf') and headers['content-type'].startswith('text/csv')
            assert headers['x-export-schema']=='socai2.list-export.v1'
            assert datetime.fromisoformat(headers['x-export-observed-at']).tzinfo
            assert headers['content-disposition'].startswith('attachment; filename="'+kind+'-')
            rows=list(csv.reader(io.StringIO(body,newline='')))
            assert len(rows)-1==int(headers['x-export-count'])
            return rows
        return body
    def value(row,path):
        for key in path.split('.'):row=row[key]
        return row
    def compare(kind,filters,fields=None):
        params={'q':fixture['q'],**filters}; rows=get(kind,params|({'columns':','.join(fields)} if fields else {}),True)
        columns=fields or DEFAULTS[kind];assert rows[0]==list(columns)
        listing=[];p=params|{'limit':20}
        while True:
            page=get(kind,p); listing+=page['items']
            if page['next_cursor'] is None:break
            p['cursor']=page['next_cursor']
        assert len(rows)-1==len(listing)==page['total' if kind=='cases' else 'filtered_total']
        for output,item in zip(rows[1:],listing,strict=True):
            for col,actual in zip(columns,output,strict=True):
                expected=cell(value(item,col))
                # Both are ISO aware datetimes; DTO JSON uses Z while derived SQL uses +00:00.
                if actual!=expected and isinstance(value(item,col),str) and 'T' in actual:
                    assert datetime.fromisoformat(actual)==datetime.fromisoformat(expected),(col,actual,expected)
                else:assert actual==expected,(kind,col,actual,expected)
        return rows
    for kind in ('alerts','incidents','cases'):
        default=compare(kind,{})
        assert len(default)-1==len(fixture['ids'][kind])
        compare(kind,{'sort_by':'severity','sort_order':'asc'},ALLOWED[kind])
        compare(kind,{'handling_status':'new','severity':'high','sort_order':'asc'})
        compare(kind,{'time_from':cfg['fixture_time'],'time_to':(datetime.fromisoformat(cfg['fixture_time'])+timedelta(hours=2)).isoformat()})
        compare(kind,{'q':fixture['q']+' absent'})
        for invalid in ({'columns':'tenant_id'},{'columns':'facts.id,facts.id'},{'limit':1},{'cursor':'x'},
                        {'sort_by':'invalid'},{'time_from':'2026-11-13T00:00:00'},{'unknown':'x'}):
            get(kind,{'q':fixture['q'],**invalid},True,422)
        if cfg.get('legacy_base_url'):
            params={'q':fixture['q'],'limit':2,'sort_by':'severity'}
            old=get(kind,params,base=cfg['legacy_base_url']);new=get(kind,params)
            for doc in (old,new):doc.pop('observed_at',None)
            assert old==new,kind
    after=asyncio.run(database(cfg,'limits',args.fixture));write(args.output/'sql-after.json',after)
    assert before==after
    write(args.output/'summary.json',{'passed':True,'http_calls':len(calls),'synthetic_counts':{k:len(v) for k,v in before.items()},
        'all_public_columns_compared':{k:len(v) for k,v in ALLOWED.items()},'over_50_rows_complete':True,
        'real_pg_row_limit_413':True,'sql_unchanged':True,'models':0,'runs_started':0})
    print((args.output/'summary.json').read_text())

if __name__=='__main__':main()
