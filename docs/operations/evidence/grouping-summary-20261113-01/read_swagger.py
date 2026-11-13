import sys,json,subprocess,urllib.request,hashlib,datetime
from pathlib import Path
cfg={k:v for k,v in (l.split('=',1) for l in Path(sys.argv[1]).read_text().splitlines() if l and not l.startswith('#'))}
url='http://'+cfg['DOCS_BIND']+':'+cfg['DOCS_PORT']
raw=json.loads(subprocess.check_output(['docker','inspect','socai2-api-docs-swagger-1']))[0]
result={'url':url+'/','image':raw['Config']['Image'],'configured_platform':cfg['DOCS_PLATFORM'],'runtime_arch':subprocess.check_output(['docker','exec','socai2-api-docs-swagger-1','uname','-m'],text=True).strip(),'container':'socai2-api-docs-swagger-1','running':raw['State']['Running'],'started_at':raw['State']['StartedAt'],'content_mount':next(m['Source'] for m in raw['Mounts'] if m['Destination']=='/usr/share/nginx/html/handoff'),'http':{}}
for path in ['/','/handoff/index.html','/handoff/openapi.json','/handoff/guide.html','/handoff/audit/interfaces.html','/handoff/audit/response-fields.html','/handoff/audit/dynamic-fields.html','/handoff/swagger-config.json','/handoff/manifest.json']:
 with urllib.request.urlopen(url+path,timeout=15) as response:
  data=response.read();result['http'][path]={'status':response.status,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
  if path.endswith('/manifest.json'):result['document_manifest']=json.loads(data)
  if path.endswith('/openapi.json'):
   o=json.loads(data);result['openapi_version']=o['info']['version'];result['business_groups']=[t['name'] for t in o['tags']]
assert result['openapi_version']=='2026-11-13.docs10'
assert result['document_manifest']['feature_groups']=={'告警':22,'事件':15,'调查':88}
assert result['business_groups']==['告警','事件','调查']
assert result['document_manifest']['operations']==57
assert result['document_manifest']['fixed_output_fields']==554
assert result['content_mount']==cfg['DOCS_CONTENT']
print(json.dumps(result,ensure_ascii=False,indent=2))
