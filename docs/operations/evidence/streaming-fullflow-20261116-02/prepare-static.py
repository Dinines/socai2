"""Prepare two scoped, unchanged snapshots for the established local audit importer."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parent;p=json.loads((root/'batch/profile.json').read_text());snap=json.loads((root/'final-pg.json').read_text());snap=snap.get('value',snap);rows=snap['rows']
mapping=json.loads((root/'case-mapping.json').read_text())
assert {c['id'] for c in rows['cases']} == {c['case_id'] for c in mapping.values()}
assert all(t['state'] in {'completed','failed','skipped','merged'} for t in rows['analysis_tasks'])
assert all(r['state'] not in {'running','pending_update'} for r in rows['runs'])
for case in rows['cases']:
    cid=case['id'];folder=root/'static-export/cases'/cid/'export';folder.mkdir(parents=True)
    aids={r['alert_id'] for r in rows['case_alerts'] if r['case_id']==cid}
    iids={r['incident_id'] for r in rows['case_incidents'] if r['case_id']==cid}
    ids={r['id'] for r in rows['runs'] if r['case_id']==cid or r['alert_id'] in aids or r['incident_id'] in iids}
    tasks={r['id'] for r in rows['analysis_tasks'] if r['subject_id'] in {cid,*aids,*iids}}
    resultids={r['id'] for r in rows['results'] if r['case_id']==cid}
    data={}
    for table,values in rows.items():
        if table=='cases':part=[case]
        elif table=='alerts':part=[r for r in values if r['id'] in aids]
        elif table=='incidents':part=[r for r in values if r['id'] in iids]
        elif table=='runs':part=[r for r in values if r['id'] in ids]
        elif table in ('analysis_tasks','analysis_subject_state'):part=[r for r in values if r['subject_id'] in {cid,*aids,*iids}]
        elif table=='analysis_attempts':part=[r for r in values if r['task_id'] in tasks]
        elif table=='artifacts':part=[r for r in values if r['run_id'] in ids or r['run_id'] is None and (r['case_id']==cid or r['alert_id'] in aids or r['incident_id'] in iids)]
        elif table in ('run_steps','run_members'):part=[r for r in values if r['run_id'] in ids]
        elif table=='result_members':part=[r for r in values if r['result_id'] in resultids]
        elif table.startswith('case_') or table=='results':part=[r for r in values if r['case_id']==cid]
        elif table.startswith('incident_'):part=[r for r in values if r['incident_id'] in iids]
        elif table.startswith('alert_'):part=[r for r in values if r['alert_id'] in aids]
        else:raise ValueError(table)
        data[table]=part
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode();(folder/'database.json').write_bytes(raw)
    manifest={'schema_version':'socai2.page-export.v1','batch_id':p['batch_id'],'tenant_id':p['tenant_id'],'case_id':cid,'exported_at':snap['identity']['captured_at'].replace(' ','T'),'sources':[{'file':'database.json','sha256':hashlib.sha256(raw).hexdigest()}]}
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (folder.parent/'plan.json').write_text(json.dumps({'batch_id':p['batch_id'],'case':{'key':cid,'title':case['title']}},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'cases':len(rows['cases']),'source':'final-pg.json','source_rows_unchanged':True}))
