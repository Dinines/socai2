"""Prepare 4177 formal configuration without switching its running container."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);c=json.loads((root/'config/release.json').read_text());v=c['viewer'];hp=json.loads((root/'config/http-profile.json').read_text())
dest=root/'viewer/config';dest.mkdir(parents=True)
old=Path(v['old_config'])
s=json.loads((old/'service.json').read_text());s.update(environment_label=c['release'])
u=json.loads((old/'upstream.json').read_text());u.update(environment_label=c['release'],tenant_id=c['identity']['tenant_id'],base_url=v['upstream'])
contract=json.loads((root/'http/releases'/hp['release']/'contract/openapi.json').read_text());contract['info']['version']=hp['release']
raw=(json.dumps(contract,ensure_ascii=False,indent=2)+'\n').encode();name=Path(u['openapi_file']).name
u['openapi_file']='/run/test-config/'+name;u['openapi_sha256']=hashlib.sha256(raw).hexdigest()
files={'service.json':(json.dumps(s,ensure_ascii=False,indent=2)+'\n').encode(),'upstream.json':(json.dumps(u,ensure_ascii=False,indent=2)+'\n').encode(),'viewer.json':(old/'viewer.json').read_bytes(),name:raw}
for name,body in files.items():
 with (dest/name).open('xb') as f:f.write(body)
assert json.loads((dest/'service.json').read_text())['environment_label']==json.loads((dest/'upstream.json').read_text())['environment_label']
swagger=json.loads((root/'swagger/handoff/openapi.json').read_text());canonical=lambda x:{k:v for k,v in x.items() if k not in {'info','servers'}}
assert {(p,m) for p,methods in swagger['paths'].items() for m in methods if m in {'get','post','put','patch','delete'}} == {(p,m) for p,methods in contract['paths'].items() for m in methods if m in {'get','post','put','patch','delete'}}
assert swagger['components']['schemas']==contract['components']['schemas']
assert swagger['servers']==[{'url':c['swagger']['upstream']}]
print(json.dumps({'status':'prepared_not_switched','service':s,'upstream':u,'viewer':json.loads(files['viewer.json']),'configuration_hashes':{name:hashlib.sha256(body).hexdigest() for name,body in files.items()},'swagger_contract_sha256':hashlib.sha256((root/'swagger/handoff/openapi.json').read_bytes()).hexdigest(),'swagger_servers':swagger['servers'],'swagger_http_proxy_contracts_semantically_equal':True,'ledger_written':False,'services_changed':False},ensure_ascii=False,indent=2))
