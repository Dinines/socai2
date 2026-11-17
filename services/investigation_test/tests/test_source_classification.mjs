import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {classifySources,classifyRunSources,registeredRun,sourceCaption} from '../web/test_sources.mjs';
import {loadFrozenCase} from '../web/frozen_sources.mjs';
import {runPath} from '../web/viewer_state.mjs';

// Replay actual saved HTTP; never connect to a service or alter the old execution.
const dir=new URL('../../../docs/operations/evidence/acceptance-fullflow-21-20261117-01/results/prepared/runs/part2/',import.meta.url);
const saved=JSON.parse(readFileSync(new URL('saved-records.json',dir),'utf8'));
const responses=new Map();
for(const name of readdirSync(new URL('http/',dir)).sort()) {
  if(!name.endsWith('.json')||name.endsWith('.intent.json'))continue;
  const row=JSON.parse(readFileSync(new URL(`http/${name}`,dir),'utf8'));
  if(row.request?.method==='GET' && row.response?.status===200)responses.set(row.request.path,row.response.body);
}
const traces=JSON.parse(readFileSync(new URL('../../../docs/operations/evidence/workbench-test-source-20261117-01/live-traces.json',import.meta.url),'utf8'));
for(const row of traces.reads)responses.set(row.path,row.body);
const readBody=async url=>{
  assert.ok(responses.has(url),`saved HTTP missing: ${url}`);
  return {data:structuredClone(responses.get(url))};
};
const pathname=p=>new URL(p,'http://saved.invalid').pathname;
function readPages(url) {
  const items=new Map();
  for(const [path,body] of responses)if(pathname(path)===pathname(url))
    for(const item of body.items??[])items.set(item.id,item);
  return [...items.values()];
}
async function input(row) {
  const type=row.case_id?'case':row.incident_id?'incident':'alert';
  const mapping={subject_type:type,subject_id:row[`${type}_id`],run_id:row.id};
  const url=runPath(mapping),detail=(await readBody(url)).data;
  const directory=type==='case'?detail:(await readBody(`${url}/trace`)).data;
  const artifacts=readPages(directory.artifacts_url),run=directory.run??detail.run;
  const context=type==='case'?(await loadFrozenCase(run,artifacts,readBody)).context:null;
  return {mapping,run,artifacts,context,readBody,prefixes:['telemetry-channel-02']};
}

test('actual six saved HTTP Runs classify their own frozen 1/2 members without a ledger',async()=>{
  for(const row of saved.runs) {
    const options=await input(row),result=await classifyRunSources(options);
    const expected=row.case_id?(row.scope_revision===1?1:2):row.alert_id?1:
      row.id==='0ebbdc73-98e2-57ef-8d79-591df28c7d07'?1:2;
    assert.deepEqual(result,{state:'test',total:expected,matched:expected,unknown:0});
    assert.match(sourceCaption(result),new RegExp(`${expected} 条告警`));
    assert.deepEqual(await classifyRunSources({...options,prefixes:['lyc']}),
      {state:'none',total:expected,matched:0,unknown:0});
  }
});
test('lyc, normal, mixed and incomplete sources are distinct and do not infer from titles',()=>{
  const a={id:'a',connector_type:'lyc-channel-01'},b={id:'b',connector_type:'sensor-01',title:'lyc test'},missing={id:'b'};
  assert.equal(classifySources([a],['a'],['lyc']).state,'test');
  assert.equal(classifySources([b],['b'],['lyc']).state,'none');
  assert.equal(classifySources([{...a,connector_type:'LYC-channel'}],['a'],['lyc']).state,'none');
  assert.deepEqual(classifySources([a,b],['a','b'],['lyc']),{state:'mixed',total:2,matched:1,unknown:0});
  assert.deepEqual(classifySources([a,missing],['a','b'],['lyc']),{state:'mixed',total:2,matched:1,unknown:1});
  assert.equal(classifySources([missing],['b'],['lyc']).state,'unknown');
  assert.equal(classifySources([a],['a'],[]).state,'disabled');
  assert.throws(()=>classifySources([a,a],['a'],['lyc']),/重复/);
  assert.throws(()=>classifySources([a,b],['a'],['lyc']),/其他告警/);
});
test('controlled lyc mixed later Case round never changes frozen first round',async()=>{
  const cases=saved.runs.filter(r=>r.case_id).sort((a,b)=>a.scope_revision-b.scope_revision);
  const first=await input(cases[0]),second=await input(cases[1]);
  for(const options of [first,second]) {
    options.prefixes=['lyc'];
    for(const value of Object.values(options.context.alerts))value.alert.connector_type='lyc-channel-01';
  }
  const secondIds=second.context.scope.alert_ids;
  second.context.alerts[secondIds[1]].alert.connector_type='ordinary-channel';
  assert.equal((await classifyRunSources(first)).state,'test');
  assert.equal((await classifyRunSources(second)).state,'mixed');
  assert.equal((await classifyRunSources(first)).state,'test');
  delete second.context.alerts[secondIds[0]].alert.connector_type;
  assert.equal((await classifyRunSources(second)).state,'unknown');
});
test('unavailable or mismatched selected inputs stay unknown without looking up latest',async()=>{
  const options=await input(saved.runs.find(r=>r.alert_id));
  let count=0;
  const failed=await classifyRunSources({...options,readBody:async()=>{count++;throw new Error('controlled 503');}});
  assert.equal(failed.state,'unknown');assert.equal(count,1);assert.match(failed.reason,/503/);
  const mismatch=await classifyRunSources({...options,mapping:{...options.mapping,run_id:'other'}});
  assert.equal(mismatch.state,'unknown');assert.match(mismatch.reason,/主体或Run/);
  const missing=await classifyRunSources({...options,artifacts:[]});
  assert.equal(missing.state,'unknown');assert.match(missing.reason,/工件/);
});
test('legacy registration identifies only the exact subject and Run',()=>{
  const mapping={subject_type:'case',subject_id:'c',run_id:'r1'};
  const ops=[{mappings:[mapping,{...mapping,run_id:null}]}];
  assert.equal(registeredRun(ops,mapping),true);
  assert.equal(registeredRun(ops,{...mapping,run_id:'r2'}),false);
  assert.equal(registeredRun(ops,{...mapping,subject_id:'other'}),false);
  assert.equal(registeredRun(ops,{...mapping,run_id:null}),false);
  assert.equal(sourceCaption({state:'none'},false),null);
  assert.match(sourceCaption({state:'none'},true),/本轮已登记/);
});
