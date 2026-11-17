"""One diagnostic generation through the same configured gateway; no business writes."""
import asyncio,hashlib,json,os,sys,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import UUID
from app.socai2.analysis_dispatch_runtime import load_profile
from app.socai2.stage_results import StageResultService
from app.socai2.baseline_analysis_model import TenantChatGateway,usage
from app.socai2.incident_output_adapter import BoundaryAnswer
from app.socai2.model_protocol import response_choices
from app.socai2.runtime_policy import active_policy
from app.services.llm_safety import LLMInputContract
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker

FOLDER=Path('/probe');OUT=FOLDER/'out';P=json.loads((FOLDER/'profile.json').read_text())
def save(name,value):
 with (OUT/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,default=str)
def now():return datetime.now(timezone.utc).isoformat()
async def main():
 request_path=FOLDER/'candidate-request.json';body=json.loads(request_path.read_text());original=json.loads((FOLDER/'original-request.json').read_text())
 assert hashlib.sha256(request_path.read_bytes()).hexdigest()==P['candidate_request_sha256']
 assert {k:v for k,v in original.items() if k!='response_format'}=={k:v for k,v in body.items() if k!='response_format'}
 assert body['max_tokens']==P['output_tokens'] and P['max_generation_calls']==1
 assert LLMInputContract.validate(body['messages'])==body['messages']
 config=load_profile('/run/analysis/dispatcher.json');assert config['tenant_id']==P['tenant_id']
 engine=create_async_engine(Path(config['database_url_file']).read_text().strip(),connect_args=config['database_connect_args'],hide_parameters=True)
 service=StageResultService(async_sessionmaker(engine,expire_on_commit=False));gateway=TenantChatGateway()
 try:
  assert await gateway.configure(service,UUID(P['tenant_id']))
  assert gateway.model==body['model'] and gateway.provider=='chat_completions'
  measurement=await gateway.measure(body,'I')
  save('token-measurement.json',measurement)
  assert measurement['context_fits'] and measurement['output_tokens']==P['output_tokens']
  save('intent.json',{'experiment':P['experiment'],'started_at':now(),'request_sha256':P['candidate_request_sha256'],'state':'started_outcome_unknown','max_generation_calls':1,'same_gateway':True,'business_task_created':False,'business_writes':0})
  started=time.monotonic()
  try:response=await gateway.complete(body,P['timeout_seconds'])
  except BaseException as exc:
   save('failure.json',{'observed_at':now(),'outcome':'unknown','error_type':type(exc).__name__,'automatic_retry':False});raise
  elapsed=time.monotonic()-started
  # Raw provider response is kept in the controlled probe directory before validation.
  save('response.json',response)
  choices=response_choices(response);assert isinstance(choices,list) and len(choices)==1
  choice=choices[0];content=choice.get('message',{}).get('content');assert isinstance(content,str)
  with (OUT/'output.txt').open('x') as f:f.write(content)
  shape_error=None
  try:BoundaryAnswer.model_validate_json(content,strict=True)
  except Exception as exc:shape_error=type(exc).__name__
  report={'experiment':P['experiment'],'observed_at':now(),'elapsed_seconds':elapsed,'request_sha256':P['candidate_request_sha256'],'model':response.get('model'),'system_fingerprint':response.get('system_fingerprint'),'finish_reason':choice.get('finish_reason'),'usage':usage(response),'output_characters':len(content),'non_whitespace_characters':sum(not c.isspace() for c in content),'trailing_whitespace_characters':len(content)-len(content.rstrip()),'canonical_shape_error':shape_error,'canonical_nonblank_length_validation_preserved':True,'business_writes':0,'new_business_runs':0,'generation_calls':1,'scope':'diagnostic replay; no automatic adoption or complete business acceptance'}
  save('outcome.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
 finally:await engine.dispose()
asyncio.run(main())
