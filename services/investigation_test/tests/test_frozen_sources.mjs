import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {loadCaseSources,loadFrozenCase,sourceEntries,readSourceExecution,checkArtifact} from '../web/frozen_sources.mjs';
import {runPath} from '../web/viewer_state.mjs';

// Saved real HTTP, not responses reconstructed from database rows. No network or model calls.
const root=new URL('../../../',import.meta.url);
const file=path=>JSON.parse(readFileSync(new URL(path,root),'utf8'));
const rows=file('docs/operations/evidence/streaming-fullflow-20261116-02/final-http-01.json').value.http;
const pathOf=path=>new URL(path,'http://saved.invalid').pathname;
const readBody=async path=>{
  const row=rows.find(r=>r.path===path&&r.status===200);
  assert.ok(row,`saved HTTP not found: ${path}`);
  return {data:structuredClone(row.body),raw:JSON.stringify(row.body)};
};
const readPages=async(path,identity)=>{
  const found=rows.filter(r=>pathOf(r.path)===pathOf(path)&&Array.isArray(r.body?.items));
  assert.ok(found.length,`saved directory not found: ${path}`);
  const items=new Map();
  for(const row of found) {
    if(identity)for(const key of ['subject_type','subject_id','run_id'])assert.equal(row.body[key],identity[key]);
    row.body.items.forEach(item=>items.set(item.id,structuredClone(item)));
  }
  return [...items.values()];
};
const whole='52752ea4-08b1-5e9d-8105-7e041d23f89a',single='1db68510-6378-5666-a47e-2c0b52208af4';
const r1='1ae2cb6e-ee3e-483b-828c-0414d3529917',r2='30c0c38c-ee33-4073-bd94-566a73017fed',s1='1422d925-f8e5-4f6a-84ed-3f9e2a15ca4e';
async function selected(id,caseId=whole) {
  const detail=(await readBody(runPath({subject_type:'case',subject_id:caseId,run_id:id}))).data;
  return {run:detail.run,artifacts:await readPages(detail.artifacts_url),previousUrl:detail.previous_run_url,readBody,readPages};
}

test('real R2 freezes four A, three reused plus one new, and a new I source; returning R1 keeps three',async()=>{
  const second=await loadCaseSources(await selected(r2));assert.deepEqual(second.issues,[]);
  const alerts=second.entries.filter(e=>e.kind==='alert');
  assert.equal(alerts.length,4);assert.equal(alerts.filter(e=>e.relation==='沿用上一轮').length,3);
  assert.equal(alerts.filter(e=>e.relation==='本轮新增').length,1);
  assert.equal(second.entries.find(e=>e.kind==='incident').relation,'来源版本变化');
  assert.equal(second.previous.run.id,r1);
  const first=await loadCaseSources(await selected(r1));assert.deepEqual(first.issues,[]);
  assert.equal(first.entries.filter(e=>e.kind==='alert').length,3);
  assert.ok(first.entries.every(e=>e.relation==='首轮使用'));
  assert.equal(first.entries.find(e=>e.kind==='incident').runId,'10535c76-6a2e-5943-8cfc-efcc31c456a9');
});
test('single Case retains shared I original scope of three and its Case intersection of one',async()=>{
  const singleRound=await loadCaseSources(await selected(s1,single));assert.deepEqual(singleRound.issues,[]);
  assert.equal(singleRound.entries.filter(e=>e.kind==='alert').length,1);
  const i=singleRound.entries.find(e=>e.kind==='incident');
  assert.equal(i.coverage.selected,3);assert.equal(i.coverage.retainedIds.length,3);
  assert.equal(i.coverage.caseSelectedIds.length,1);assert.equal(i.coverage.caseRetainedIds.length,1);
  assert.equal(i.data.analysis_material.units.find(u=>u.path==='$.findings[0]').scope.alert_ids.length,3);
});
test('each frozen A/I reads its exact source Run and all artifacts; original envelopes remain traceable',async()=>{
  const sources=await loadCaseSources(await selected(r2));
  for(const e of sources.entries) {
    const source=await readSourceExecution(e,readBody,readPages);assert.deepEqual(source.issues,[]);
    assert.equal(source.run.id,e.runId);assert.ok(source.steps.length);
    const original=source.artifacts.find(a=>a.kind==='source_snapshot');
    if(original)checkArtifact(original,(await readBody(original.content_url)).data);
  }
});
test('C1 must be unique and referenced by this manifest, never picked by role or latest schema',async()=>{
  const input=await selected(r2),frozen=await loadFrozenCase(input.run,input.artifacts,readBody);
  const noRef=async path=>{const r=await readBody(path);if(path===frozen.manifestRef.content_url)r.data.content_json.source_materials=[];return r;};
  await assert.rejects(loadFrozenCase(input.run,input.artifacts,noRef),/实际匹配 0/);
  const duplicate={...frozen.ref,id:'another-c1'};
  const multiple=async path=>{const r=await readBody(path);if(path===frozen.manifestRef.content_url)r.data.content_json.source_materials.push({type:'artifact',id:duplicate.id});return r;};
  await assert.rejects(loadFrozenCase(input.run,[...input.artifacts,duplicate],multiple),/实际匹配 2/);
  const wrongCase=async path=>{const r=await readBody(path);if(path===frozen.ref.content_url)r.data.artifact.case_id=single;return r;};
  await assert.rejects(loadFrozenCase(input.run,input.artifacts,wrongCase),/case_id/);
});
test('unreadable previous C1 retains all current sources but never labels them reused',async()=>{
  const input=await selected(r2),original=await loadCaseSources(input);
  const current=await loadCaseSources({...input,readBody:async path=>{
    if(path===original.previous.ref.content_url)throw new Error('controlled_previous_unavailable');return readBody(path);
  }});
  assert.equal(current.entries.length,5);assert.equal(current.comparison,'unavailable');
  assert.ok(current.issues[0].includes('controlled_previous_unavailable'));
  assert.ok(current.entries.every(e=>e.relation==='无法比较'));
});
test('missing A identities and unusable triage do not become usable merely by matching a previous source',async()=>{
  const source=await loadCaseSources(await selected(r2)),now=structuredClone(source.current.context),prev=structuredClone(source.previous.context);
  const id=Object.keys(prev.alerts)[0];delete now.alerts[id].triage.source_run_id;delete prev.alerts[id].triage.source_run_id;
  let item=sourceEntries(now,prev,'available').find(e=>e.id===id);
  assert.equal(item.runId,null);assert.equal(item.identityComplete,false);assert.equal(item.relation,'来源不完整，无法比较');
  await assert.rejects(readSourceExecution(item,()=>assert.fail('must not query latest'),readPages),/未记录源Run/);
  const usable=structuredClone(source.current.context);usable.alerts[id].triage_usable=false;
  item=sourceEntries(usable,source.previous.context,'available').find(e=>e.id===id);
  assert.equal(item.relation,'沿用上一轮');assert.equal(item.data.triage_usable,false);
});
test('historical partial/none components retain receipt and source even without a complete diagnosis',()=>{
  for(const [variant,expected,delivery] of [['partial-02',1,'partial'],['none-01',0,'none']]) {
    const context=file(`docs/operations/evidence/incident-signal-d4b-20261116-01/pg-${variant}/frozen-context.json`);
    const entry=sourceEntries(context).find(e=>e.kind==='incident');
    assert.equal(entry.data.diagnosis_scope,null);assert.equal(entry.data.diagnosis_usable,false);
    assert.ok(entry.runId);assert.equal(entry.data.analysis_material.receipt.delivery.state,delivery);
    assert.equal(entry.coverage.retainedIds.length,expected);assert.ok(entry.data.analysis_material.receipt.missing_units.length);
    assert.ok(entry.coverage.selected>expected);
    const missing=structuredClone(context);delete Object.values(missing.incidents)[0].analysis_material.units;
    assert.equal(sourceEntries(missing).find(e=>e.kind==='incident').coverage.retainedIds,null);
  }
});
test('current missing source is local, and mismatched source Run or artifact digest is visible',async()=>{
  const input=await selected(r2);
  const absent=await loadCaseSources({...input,artifacts:[]});assert.equal(absent.entries.length,0);assert.equal(absent.issues.length,1);
  const missingIncident=sourceEntries({scope:{alert_ids:[]},incidents:{missing:null}})[0];
  assert.equal(missingIncident.runId,null);assert.equal(missingIncident.coverage.retainedIds,null);
  const e=(await loadCaseSources(input)).entries.find(e=>e.kind==='incident');
  await assert.rejects(readSourceExecution(e,async path=>{
    const r=await readBody(path);if(path.endsWith('/trace'))r.data.run.incident_id='other';return r;
  },readPages),/身份不一致/);
  const changed=structuredClone(e);changed.data.analysis_material.input.sha256='wrong';
  const source=await readSourceExecution(changed,readBody,readPages);
  assert.ok(source.issues[0].includes('摘要不一致'));
});
