"""Freeze one causal I replay; alter only known-incompatible prose grammar keys."""
import copy,hashlib,json
from pathlib import Path
E=Path(__file__).resolve().parent;REPO=E.parents[3]
old=REPO/'docs/operations/evidence/streaming-release-20261116-01/revision-02/smoke/model-input-output/incident-request.json'
original=json.loads(old.read_text());candidate=copy.deepcopy(original);changes=[]
schema=candidate['response_format']['json_schema']['schema']
for name,node in schema['$defs'].items():
 if node.get('type')=='string' and node.get('pattern')==r'\S':
  for key in ['pattern','minLength','maxLength']:
   if key in node:changes.append({'path':'/$defs/'+name+'/'+key,'before':node.pop(key),'operation':'omit_from_provider_only'})
assert len(changes)==3
assert {k:v for k,v in original.items() if k!='response_format'}=={k:v for k,v in candidate.items() if k!='response_format'}
assert original['max_tokens']==8192 and original['temperature']==0
def save(name,value):
 raw=value if isinstance(value,bytes) else (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
 with (E/name).open('xb') as f:f.write(raw)
 return hashlib.sha256(raw).hexdigest()
hashes={'original-request.json':save('original-request.json',old.read_bytes()),'candidate-request.json':save('candidate-request.json',candidate)}
save('preparation.json',{'status':'prepared_not_sent','experiment':'model-output-compatibility-20261116-01','source_request':str(old.relative_to(REPO)),'files':hashes,'changes':changes,'messages_model_temperature_max_tokens_equal':True,'canonical_result_contract_changed':False,'known_nested_source_field_preserved_for_causal_comparison':True,'max_generation_calls':1,'scope':'diagnostic model call only; no business task/Run or retry of old task'})
profile={'experiment':'model-output-compatibility-20261116-01','release_root':'/opt/sting-aisoc-socai2/deployments/streaming-release-20261116-02','remote_directory':'/opt/sting-aisoc-socai2/deployments/streaming-release-20261116-02/verification/model-output-compatibility-20261116-01','ssh_target':'sting-infra21','tenant_id':'00000000-0000-0000-0000-000000000001','processing_image':'sha256:e95a878b8d1bed6a6639666d5e46215bd38f478a5bd46c9bee5e30992cc7669d','container':'socai2-model-output-compatibility-20261116-01','max_generation_calls':1,'timeout_seconds':300,'output_tokens':8192,'candidate_request_sha256':hashes['candidate-request.json'],'original_request_sha256':hashes['original-request.json']}
save('profile.json',profile)
print(json.dumps({'status':'prepared_not_sent','changes':changes,'hashes':hashes},ensure_ascii=False,indent=2))
