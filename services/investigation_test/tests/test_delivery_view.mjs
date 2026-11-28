import test from 'node:test';
import assert from 'node:assert/strict';
import {readPart,readPagePart} from '../web/viewer_state.mjs';
import {DELIVERY_SCHEMA,deliveryRecord,closingRecord,readClosingReport,closingTitle,localEndLabel} from '../web/delivery_view.mjs';

const identity={subject_type:'case',subject_id:'case-a',run_id:'run-a'};
test('a later page failure retains the already read page and never means empty',async()=>{
  const result=await readPagePart(async cursor=>{
    if(cursor)throw new Error('HTTP 503');
    return {...identity,items:[{id:'kept'}],next_cursor:'second'};
  },identity);
  assert.deepEqual(result.data,[{id:'kept'}]);assert.equal(result.availability,'partial');assert.match(result.error,/503/);
});
test('a foreign second page cannot enter the retained same-Run directory',async()=>{
  const result=await readPagePart(async cursor=>cursor?{...identity,run_id:'foreign',items:[{id:'wrong'}],next_cursor:null}:
    {...identity,items:[{id:'own'}],next_cursor:'second'},identity);
  assert.deepEqual(result.data,[{id:'own'}]);assert.equal(result.availability,'partial');assert.match(result.error,/不一致/);
});
test('optional errors stay local while a cancelled selection cannot publish partial data',async()=>{
  const [good,bad]=await Promise.all([readPart(async()=>({id:'kept'})),readPart(async()=>{throw new Error('failed');})]);
  assert.equal(good.data.id,'kept');assert.equal(bad.availability,'error');assert.equal(bad.data,null);
  await assert.rejects(readPart(async()=>{throw new DOMException('switched','AbortError');}),{name:'AbortError'});
  await assert.rejects(readPagePart(async()=>{throw new DOMException('switched','AbortError');}),{name:'AbortError'});
});
test('empty and unavailable directories remain different and a new GET can succeed',async()=>{
  assert.deepEqual(await readPagePart(async()=>({items:[],next_cursor:null})),{data:[],availability:'available',error:null});
  const bad=await readPagePart(async()=>{throw new Error('unavailable');});assert.equal(bad.availability,'error');
  const good=await readPagePart(async()=>({items:[{id:'recovered'}],next_cursor:null}));assert.equal(good.data[0].id,'recovered');
});
test('an ended unknown attempt is scoped to the selected Run; no success is inferred',()=>{
  const run={id:'run-a',state:'unknown'};
  assert.match(localEndLabel(run,{attempts:[{run_id:'run-a',local_state:'ended'}]}),/本地执行已结束，远端结果未知/);
  assert.match(localEndLabel(run,{attempts:[{run_id:'run-b',local_state:'ended'}]}),/未确认/);
  assert.match(localEndLabel(run,null,{run_id:'run-a',execution:{local_state:'ended'}}),/已结束/);
  assert.equal(localEndLabel({id:'run-a',state:'completed'}),null);
});
test('stage delivery preserves literal values and rejects a receipt from another step',()=>{
  const record={type:'stage_delivery',schema_version:DELIVERY_SCHEMA,run_id:'run-a',step_id:'step-a',retained_units:[{value:{text:'原文',flag:false,count:0}}]};
  assert.equal(deliveryRecord(record,{id:'run-a'},{id:'step-a'}),record);
  assert.throws(()=>deliveryRecord(record,{id:'run-a'},{id:'other'}),/不一致/);
});
test('the closing report is same-Run material and distinguishes no-response from failed reading',()=>{
  const report={type:'delivery_report',run_id:'run-a',result:{conclusion_origin:'model',conclusion:'保留原文'}};
  assert.equal(closingRecord(report,{id:'run-a'}),report);
  assert.throws(()=>closingRecord(report,{id:'other'}),/不一致/);
  assert.match(closingTitle(report),/未形成可采用结果/);
  assert.match(closingTitle(report,true),/结果读取失败/);
  const systemTitle=closingTitle({...report,result:{conclusion_origin:'system'}});
  assert.match(systemTitle,/未形成可采用结果/);assert.doesNotMatch(systemTitle,/未收到/);
});
test('the C6 receipt binds the detailed report, not the compact report_json',async()=>{
  const run={id:'run-a'},step={id:'c6',run_id:run.id,kind:'stage',stage_code:'C6',output_artifact_id:'receipt'};
  const artifacts=[['receipt','source_snapshot'],['detail','source_snapshot'],['compact','report_json']]
    .map(([id,kind])=>({id,kind,run_id:run.id,step_id:step.id}));
  const bodies={receipt:{type:'delivery_receipt',run_id:run.id,detail_artifact_id:'detail',report_artifact_id:'compact'},
    detail:{type:'delivery_report',run_id:run.id,result:{conclusion:'原结论'}},compact:{conclusion:'原结论'}};
  const reads=[];
  assert.equal(await readClosingReport({run,steps:[step],artifacts,readContent:async ref=>{reads.push(ref.id);return bodies[ref.id];}}),bodies.detail);
  assert.deepEqual(reads,['receipt','detail']);
  await assert.rejects(readClosingReport({run,steps:[step],artifacts:artifacts.map(a=>a.id==='detail'?{...a,run_id:'other'}:a),readContent:async ref=>bodies[ref.id]}),/身份不一致/);
});
