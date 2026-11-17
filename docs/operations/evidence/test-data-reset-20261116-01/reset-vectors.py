"""Remove points from an explicit list of test knowledge collections; keep schemas."""
import hashlib,json,os,sys
from pathlib import Path
from urllib.request import Request,urlopen
c=json.load(sys.stdin);root=Path(c['backup_root']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
key=Path(c['key_file']).read_text().strip() if c.get('key_file') else ''
def request(path,body=None,method=None):
    headers={'api-key':key} if key else {}
    if body is not None:headers['Content-Type']='application/json'
    with urlopen(Request(c['url']+path,data=json.dumps(body).encode() if body is not None else None,
                         headers=headers,method=method),timeout=30) as r:return json.load(r)
for name in c['collections']:
    assert name.startswith('socai2_') and '/' not in name
    path='/collections/'+name
    before=request(path)['result'];points=[];offset=None
    while True:
        body={'limit':100,'with_payload':True,'with_vector':True}
        if offset is not None:body['offset']=offset
        result=request(path+'/points/scroll',body)['result'];points+=result['points'];offset=result['next_page_offset']
        if offset is None:break
    backup=json.dumps({'collection':before,'points':points}).encode()
    target=root/(name+'.json')
    with target.open('xb') as f:f.write(backup)
    os.chmod(target,0o600)
    if points:request(path+'/points/delete?wait=true',{'points':[p['id'] for p in points]})
    after=request(path+'/points/count',{'exact':True})['result']['count']
    assert after==0
    assert request(path)['result']['config']==before['config']
    print(json.dumps({'collection':name,'before':len(points),'after':after,'config_unchanged':True,
                      'backup_sha256':hashlib.sha256(backup).hexdigest()}),flush=True)
