"""Merge this batch's immutable exports and use the existing frontend adapter."""
import asyncio
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from tools.testdata.case_scope_recovery.real_model import initialize
from tools.testdata.incident_integration.run import read,save,sha


async def main():
    initialize(HERE/'config.json')
    from app.socai2.case_data import export_page_data
    from fastapi.encoders import jsonable_encoder
    cfg=read(HERE/'demo-config.json')
    merged={};responses={};sources=[]
    for key in cfg['scenarios']:
        folder=HERE/'flow'/key/'export'
        manifest=read(folder/'manifest.json')
        sums={s['file']:s['sha256'] for s in manifest['sources']}
        assert sums['database.json']==sha(folder/'database.json')
        data=read(folder/'database.json')
        for table,rows in data.items():
            target=merged.setdefault(table,{})
            for row in rows:
                identity=(row['tenant_id'],row.get('id') or row['case_id'])
                assert identity not in target or target[identity]==row,('different_shared_row',table,identity)
                target[identity]=row
        for response in read(folder/'http-readback.json').values():
            assert response['path'].startswith('/socai2/')
            path=cfg['public_api_prefix']+response['path']
            normalized={**response,'method':'GET','path':path,'recorded_asgi_path':response['path'],
                'transport':'ASGI; public prefix normalized only for existing frontend importer'}
            assert path not in responses or responses[path]==normalized,('different_shared_GET',path)
            responses[path]=normalized
        sources.append({'scenario':key,'database':str((folder/'database.json').relative_to(ROOT)),
            'sha256':sums['database.json'],'manifest_sha256':sha(folder/'manifest.json')})
    database={table:list(rows.values()) for table,rows in merged.items()}
    assert len(database['alerts'])==4 and len(database['incidents'])==2 and len(database['cases'])==3 and len(database['runs'])==9
    page_data=jsonable_encoder(await export_page_data(database))
    out=HERE/'demo-export'
    out.mkdir(exist_ok=False)
    save(out/'database.json',database)
    save(out/'api-responses.json',list(responses.values()))
    save(out/'case-page-data.json',page_data)
    save(out/'manifest.json',{'schema_version':'socai2.page-export.v1','batch_id':cfg['batch'],
        'source_environment':cfg['source_environment'],'exported_at':datetime.now(UTC).isoformat(),
        'input_kind':'synthetic','source_sha256':sha(out/'database.json'),
        'sources':[{'role':role,'file':name,'sha256':sha(out/name)} for role,name in
            (('database','database.json'),('api_responses','api-responses.json'),('case_page_data','case-page-data.json'))],
        'limitations':['Saved local test snapshots; no live API or production database claim.',
            'Shared A/I rows deduplicated by original tenant and row identity with exact equality.',
            'C02 uses authored, explicitly scoped H; no independent ground truth or accuracy claim.']})
    save(out/'source-snapshots.json',sources)
    proto=ROOT/cfg['prototype_root']
    result=subprocess.run(['node',str(proto/'scripts/generate-socai2-recorded.cjs'),'--database',str(out/'database.json'),
        '--manifest',str(out/'manifest.json'),'--output',str(proto/cfg['output_script'])],capture_output=True,text=True)
    if result.returncode:
        save(out/'generator-failure.json',{'returncode':result.returncode,'stderr':result.stderr})
        raise RuntimeError('demo_generation_failed')
    receipt=json.loads(result.stdout)
    save(out/'generator-receipt.json',receipt)
    index=proto/'index.html';old=index.read_bytes()
    save(out/'index-before.json',{'sha256':hashlib.sha256(old).hexdigest()})
    (out/'index-before.html').write_bytes(old)
    marker='  <script defer src="./recorded-examples.js'
    assert old.decode().count(marker)==1 and cfg['output_script'] not in old.decode()
    new=old.decode().replace(marker,'  <script defer src="./'+cfg['output_script']+'?v='+cfg['batch']+'"></script>\n'+marker)
    index.write_text(new)
    save(out/'publication.json',{'counts':receipt['counts'],'generated_script':cfg['prototype_root']+'/'+cfg['output_script'],
        'output_sha256':receipt['output_sha256'],'index_after_sha256':sha(index),'existing_data_files_unchanged':True,
        'browser_local_storage_cleared':False,'preview_base_url':cfg['preview_base_url']})
    print(json.dumps({'state':'demo_data_ready','counts':receipt['counts'],'script':cfg['output_script']}))


if __name__=='__main__':
    asyncio.run(main())
