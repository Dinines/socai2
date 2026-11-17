// Controlled responses/timers here are test doubles, never real candidate evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import {businessGate, active, boundResults, pageUrl, runPath, subjectListPath, subjectEntry, subjectHistory, resumeVisible, ReadScope, VisiblePoll} from '../web/viewer_state.mjs';
const origin = 'http://localhost:9999';
test('archive and environment mismatch prohibit business reads', () => {
  const cap = {investigation_http: {environment_label:'current'}};
  assert.equal(businessGate({mode:'live',environment:'current'},cap), null);
  assert.match(businessGate({mode:'archive',environment:'current'},cap), /归档/);
  assert.match(businessGate({mode:'live',environment:'old'},cap), /环境不一致/);
  assert.equal(businessGate(null,cap),null);
  assert.match(businessGate(null,{}),/未配置/);
});
test('business lists keep their distinct contracts and use cursor-capable sorting without a ledger',()=>{
  assert.equal(subjectEntry('case',{case:{id:'case-1',title:'Case'}}).mapping.subject_id,'case-1');
  assert.equal(subjectEntry('incident',{facts:{id:'incident-1',title:'Incident'}}).mapping.subject_type,'incident');
  assert.equal(subjectEntry('alert',{facts:{id:'alert-1'}}).mapping.subject_id,'alert-1');
  assert.throws(()=>subjectEntry('incident',{case:{id:'wrong'}}),/真实 ID/);
  assert.match(subjectListPath('incident'),/sort_by=last_activity_at&sort_order=desc/);
  assert.match(subjectListPath('alert'),/sort_by=event_time&sort_order=desc/);
});
test('round discovery binds both subject identifiers and retains each round task and detail URL',()=>{
  const mapping={subject_type:'incident',subject_id:'i1'};
  const rows=[{...mapping,run_id:'r2',task_id:'t2',detail_url:'/r2'},{...mapping,run_id:'r1',task_id:'t1',detail_url:'/r1'}];
  const history=subjectHistory(mapping,[...rows,rows[1]]);
  assert.deepEqual(history.map(h=>[h.run.id,h.mapping.task_id,h.url]),[['r2','t2','/r2'],['r1','t1','/r1']]);
  assert.throws(()=>subjectHistory(mapping,[{...rows[0],subject_id:'i2'}]),/其他主体/);
  assert.throws(()=>subjectHistory(mapping,[{...rows[0],subject_type:'case'}]),/其他主体/);
  assert.deepEqual(subjectHistory(mapping,[]),[]);
});
test('task pending run distinctions and same Run result binding', () => {
  assert.equal(active('task','accepted'), true);
  for (const status of ['completed','failed','skipped','unknown']) assert.equal(active('task',status),false);
  assert.equal(active('run','pending'),true);
  assert.equal(active('run','unknown'),false);
  const mapping = {subject_type:'incident',subject_id:'old-subject',run_id:'old-run'};
  const task = {latest_run_id:'new-run',results:[{source_run_id:'new-run'},{source_run_id:'old-run'}]};
  assert.match(runPath(mapping), /old-run$/);
  assert.deepEqual(boundResults(task,mapping.run_id),[{source_run_id:'old-run'}]);
});
test('pagination retains filters and cursor, rejects foreign target', () => {
  const url = new URL(pageUrl('/api/v1/socai2/analysis-runs?kind=model',2,'a+b/=',origin),origin);
  assert.equal(url.searchParams.get('cursor'),'a+b/=');
  assert.equal(url.searchParams.get('kind'),'model');
  assert.equal(url.searchParams.get('limit'),'2');
  assert.throws(()=>pageUrl('http://elsewhere/api/v1/socai2/analysis-runs',1,null,origin));
});
test('a late response cannot replace a new selection even if transport ignores abort', async () => {
  const scope = new ReadScope(); let finish;
  const pending = scope.read('/api/v1/socai2/cases',1,origin,()=>new Promise(resolve=>{finish=resolve;}));
  scope.reset();
  finish(new Response('{"id":"old"}'));
  await assert.rejects(pending,{name:'AbortError'});
  assert.equal(scope.controllers.size,0);
});
test('failure and timeout remain errors rather than empty or archived records', async () => {
  const scope = new ReadScope();
  await assert.rejects(scope.read('/api/v1/socai2/cases',1,origin,async()=>new Response('unavailable',{status:503})), /HTTP 503/);
  await assert.rejects(scope.read('/api/v1/socai2/cases',0.005,origin,async(_url,{signal})=>new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError'))))), /读取超时/);
  assert.equal(scope.controllers.size,0);
});
test('only visible active object polls and stopping clears the timer', async () => {
  let visible=true, reads=0;
  const poll=new VisiblePoll(0.005,()=>visible), refresh=()=>reads++;
  poll.schedule(false,refresh); await new Promise(resolve=>setTimeout(resolve,10)); assert.equal(reads,0);
  visible=false; poll.schedule(true,refresh); await new Promise(resolve=>setTimeout(resolve,10)); assert.equal(reads,0);
  visible=true; poll.schedule(true,refresh); poll.stop(); await new Promise(resolve=>setTimeout(resolve,10)); assert.equal(reads,0);
  poll.schedule(true,refresh); await new Promise(resolve=>setTimeout(resolve,10)); assert.equal(reads,1);
});
test('controlled large original preserves initial, correction, merged output and field origins', async () => {
  const body = {fixture:true, provenance:'synthetic_fixture',
    initial:{raw:'初答'+ 'x'.repeat(1024*1024)}, correction:{raw:'补答'},
    merged:{finding:'程序合并'}, field_origins:{finding:'correction'}};
  const raw = JSON.stringify(body), scope = new ReadScope();
  const result = await scope.read('/api/v1/socai2/analysis-runs/fixture/artifacts',1,origin,async()=>new Response(raw));
  assert.ok(Buffer.byteLength(raw)>1024*1024);
  assert.equal(result.raw,raw);
  assert.deepEqual(result.data,body);
  assert.equal(result.data.initial.raw.length,2+1024*1024);
  assert.equal(result.data.correction.raw,'补答');
  assert.equal(result.data.field_origins.finding,'correction');
});
test('returning to a visible page resumes only active or interrupted reads, not terminal or nested originals', () => {
  assert.equal(resumeVisible(false,false,false),false);
  assert.equal(resumeVisible(true,false,false),true);
  assert.equal(resumeVisible(false,true,false),true);
  assert.equal(resumeVisible(true,false,true),false);
});
