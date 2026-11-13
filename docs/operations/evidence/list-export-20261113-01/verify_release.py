"""Read-only release acceptance: CSV fields, list HTTP, independently read SQL."""
import csv,io,json,sys,urllib.request,urllib.parse,urllib.error
from datetime import datetime
from pathlib import Path
cfg=json.loads(Path(sys.argv[1]).read_text());snapshot=json.loads(Path(sys.argv[2]).read_text());sql=snapshot.get('rows',snapshot)
out=Path(sys.argv[3]);out.mkdir(exist_ok=False)
secret=json.loads(Path(cfg['credential']['file']).read_text())
if cfg['credential'].get('kind')=='existing_login':
 request=urllib.request.Request(cfg['credential']['login_url'],data=json.dumps({k:secret[k] for k in ['email','password']}).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=30) as r:token=json.load(r)['access_token']
else:token=secret['api_key']
with urllib.request.urlopen(cfg['base_url']+'/openapi.json',timeout=30) as r:contract=json.load(r)
candidate=json.loads(Path('docs/operations/evidence/list-export-20261113-01/candidate-openapi.json').read_text())
assert contract['info']['version']==cfg['release']
assert contract['paths']==candidate['paths'] and contract['components']==candidate['components']
columns=json.loads(Path('deploy/api-docs/list-export-columns.json').read_text());calls=[]
def get(kind,params,export=False,code=200):
 path='/api/v1/socai2/'+kind+('/export' if export else '')+'?'+urllib.parse.urlencode(params)
 request=urllib.request.Request(cfg['base_url']+path,headers={'Authorization':'Bearer '+token})
 try:r=urllib.request.urlopen(request,timeout=30)
 except urllib.error.HTTPError as exc:r=exc
 with r:status,head,raw=r.code,{k.lower():v for k,v in r.headers.items()},r.read()
 body=raw.decode('utf-8-sig') if export and status==200 else json.loads(raw)
 calls.append(dict(path=path,status=status,headers={k:v for k,v in head.items() if k.startswith(('content-','x-export'))},body=body))
 (out/'responses.json').write_text(json.dumps(calls,ensure_ascii=False,indent=2)+'\n');assert status==code,(path,status,body)
 if export and status==200:
  assert raw.startswith(b'\xef\xbb\xbf') and head['content-type'].startswith('text/csv')
  rows=list(csv.reader(io.StringIO(body,newline='')));assert len(rows)-1==int(head['x-export-count'])
  assert head['x-export-schema']=='socai2.list-export.v1';assert datetime.fromisoformat(head['x-export-observed-at']).tzinfo
  return rows
 return body
def equal(encoded,expected):
 if expected is None:return encoded==r'\N'
 if isinstance(expected,(dict,list,bool)):return json.loads(encoded)==expected
 if encoded.startswith(('\\\\',"'")):encoded=encoded[1:]
 if str(expected)==encoded:return True
 try:return datetime.fromisoformat(str(expected))==datetime.fromisoformat(encoded)
 except ValueError:return False
for kind in ('alerts','incidents','cases'):
 prefix='case' if kind=='cases' else 'facts'; params={'q':cfg['queries'][kind],'sort_by':'severity','sort_order':'asc'}
 result=get(kind,params|{'columns':','.join(columns[kind]['allowed'])},True);assert result[0]==columns[kind]['allowed']
 listing=[];p=params|{'limit':50}
 while True:
  page=get(kind,p);listing+=page['items']
  if page['next_cursor'] is None:break
  p['cursor']=page['next_cursor']
 assert len(listing)==len(result)-1==len(sql[kind]);byid={r['id']:r for r in sql[kind]}
 for encoded,item in zip(result[1:],listing,strict=True):
  fact=item[prefix];source=byid[fact['id']]
  for path,cell in zip(result[0],encoded,strict=True):
   value=item
   for part in path.split('.'):value=value[part]
   assert equal(cell,value),(kind,path,cell,value)
   if path.startswith(prefix+'.'):assert equal(cell,source[path.split('.',1)[1]]),(kind,path,'SQL mismatch')
 # Successful empty file and invalid pagination demonstrate result/error representation.
 empty=get(kind,{'q':cfg['queries'][kind]+' absent'},True);assert len(empty)==1
 get(kind,params|{'limit':1},True,422)
summary={'state':'passed','release':cfg['release'],'database':cfg['database'],'http_gets':len(calls),'contract_matches_candidate':True,'all_allowed_columns_match_list_and_sql':True,'subject_counts':{k:len(sql[k]) for k in ('alerts','incidents','cases')},'business_writes':0,'models':0}
(out/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
