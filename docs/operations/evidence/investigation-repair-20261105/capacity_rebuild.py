import asyncio
import json
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from app.socai2 import baseline_analysis_contract as analysis
from app.socai2 import baseline_delivery_contract as delivery
from app.socai2.baseline_analysis import budget_reason, messages
from app.socai2.baseline_capacity import final_reservation, final_wire_reason
from app.socai2.baseline_context import Context
from app.socai2.baseline_contracts import Limits
from app.socai2.baseline_dispatch import offered_bindings
from app.socai2.baseline_evidence_tools import catalog
from app.socai2.baseline_store import digest, encoded
from app.socai2.model_protocol import prepare_request
from app.socai2.structured_output import response_format
from diagnose_socai2_kafka_inputs_20261105 import DIRECTORY, one


async def main():
 db=json.loads(max(DIRECTORY.glob('database-*.json')).read_text())
 gw=SimpleNamespace(provider='deepseek_responses',schema_profile='standard',model='deepseek-flash')
 output=[]
 for run in [r for r in db['runs'] if r['stop_reason']=='required_model_input_unavailable']:
  rows=[a for a in db['artifacts'] if a['run_id']==run['id'] and isinstance(a['content_json'],dict)]
  context=Context.model_validate(next(a['content_json'] for a in rows if a['schema_version']=='socai2.baseline-context.v1'))
  result=await one(db,run); p=result['prepared']
  res=final_reservation(gw,context)
  limits=Limits(max_model_calls=4,max_tokens=48000,max_tool_calls=4,max_rows_per_query=50,deadline_at=context.captured_at+timedelta(seconds=120),policy_version='capacity-candidate-only')
  prepared=next(a['content_json'] for a in rows if a['schema_version']=='socai2.baseline-model-view.v4')
  opts,mapping,_excluded=offered_bindings(catalog(context,run['tenant_id']),limits,context.captured_at,[],SimpleNamespace(configured=lambda:True))
  c3prompt,sm=messages(prepared,context,{str(a['id']):a['content_json'] for a in rows if a['kind']=='tool_response'},opts)
  mapping={o['binding_id']:mapping[o['binding_id']] for o in opts}
  c3=prepare_request(gw,{'model':gw.model,'messages':c3prompt,'max_tokens':3000,'temperature':0,'response_format':response_format(analysis.ExecutionAnalysis,sm,members=context.alerts,questions=[q.id for q in context.questions],objects=context.scope.object_keys,bindings=mapping)})
  c6=prepare_request(gw,{'model':gw.model,'messages':p['messages'],'max_tokens':3000,'temperature':0,'response_format':response_format(delivery.Delivery,p['source_map'],members=context.alerts,questions=[q.id for q in context.questions],objects=context.scope.object_keys)})
  output.append({'run_id':run['id'],'original_budget':run['limits']['max_tokens'],'candidate_budget':48000,'member_count':len(context.alerts),'c3_wire_bytes':len(encoded(c3)),'c3_messages_bytes':len(encoded(c3prompt)),'c3_view_bytes':len(c3prompt[1]['content'].encode()),'offered_binding_count':len(opts),'c6_wire_bytes':len(encoded(c6)),'c6_view_bytes':p['bytes'],'required_count':result['required_count'],'required_omissions':[r for r in result['required'] if r['omitted']],'reservation':res,'c3_admission':budget_reason([],limits,len(encoded(c3)),context.captured_at,reserve_calls=1,reservation=res),'final_wire_admission':final_wire_reason(c6,res),'new_c3_request_sha256':digest(c3),'new_c6_request_sha256':digest(c6)})
 Path('/private/tmp/socai2-capacity-candidate-20261105.json').write_text(json.dumps({'kind':'offline_candidate_measurement_not_execution','source':str(DIRECTORY),'packets':output},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(output,ensure_ascii=False,indent=2))
asyncio.run(main())
