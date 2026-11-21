'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {randomUUID}=require('node:crypto');
const {createFixtureServer,ids}=require('./service-fixture-server.cjs');
const source=fs.readFileSync(path.join(__dirname,'../service-workspace.js'),'utf8');
const plain=value=>JSON.parse(JSON.stringify(value));
function harness(base='http://127.0.0.1:4196',fetcher=fetch) {
  const events={},windowEvents={},app={innerHTML:''},box={innerHTML:'',textContent:''};let renders=0;
  Object.defineProperty(app,'innerHTML',{get(){return this.html||'';},set(value){renders++;this.html=value;}});
  const location={href:base+'/?data=service#/cases',search:'?data=service',origin:base,hash:'#/cases'};
  class Fields {constructor(form){this.values=form.fields;} [Symbol.iterator](){return this.values[Symbol.iterator]();} getAll(name){return this.values.filter(([key])=>key===name).map(([,value])=>value);}}
  const document={querySelector:selector=>selector==='#app'?app:box,addEventListener:(event,listener)=>events[event]=listener};
  const window={fetch:fetcher,addEventListener:(event,listener)=>windowEvents[event]=listener,confirm:()=>false};
  const context=vm.createContext({window,document,location,URL,URLSearchParams,FormData:Fields,crypto:{randomUUID},console});
  Object.defineProperty(context,'localStorage',{get(){throw Error('Service must not access localStorage');}});
  for(const file of ['icons.js','workspace-layout.js','subject-risk.js','recommendation-view.js','assessment-view.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../'+file),'utf8'),context);
  vm.runInContext(source,context);
  const api=window.socai2ServiceWorkspace;
  const form=(action,values)=>{const token={value:values.token||''},submit={disabled:false};const f={dataset:{svcForm:action},fields:Array.isArray(values)?values:Object.entries(values),token,submit,querySelector:s=>s==='[name=token]'?token:s==='[data-svc-form-error]'?(action==='connect'||action==='filter'?null:box):null,querySelectorAll:()=>[submit],closest:()=>f};return f;};
  const submit=async(action,values)=>{const f=form(action,values);await events.submit({target:f,preventDefault(){}});return f;};
  return {api,app,box,context,location,get renders(){return renders;},
    start(){api.start();},submit,
    async connect(){return submit('connect',{base:base+'/api/v1/socai2',token:'synthetic-only'});},
    async click(action,id=''){const el={dataset:{svc:action,id},disabled:false,closest:()=>el};await events.click({target:el,preventDefault(){}});},
    async navigate(hash){location.hash=hash;return windowEvents.hashchange();}
  };
}
async function startServer(t){const fixture=createFixtureServer();await new Promise(resolve=>fixture.server.listen(0,'127.0.0.1',resolve));t.after(()=>new Promise(resolve=>fixture.server.close(resolve)));return {...fixture,base:'http://127.0.0.1:'+fixture.server.address().port};}
const taskValues={title:'确认授权',description:'向系统负责人核实',assignee_id:'',due_at:'',state:'completed',result_text:'负责人确认仅授权此主机上的本次操作。',kind:'selected_alerts',object_keys:'',window_start:'',window_end:'',limitations:'不推广到其他主机'};

function recommendationFixture(state){
  const advice=reason=>({id:'unit-advice',action_type:'verify',reason,targets:[{object_key:'host:unit',display_name:'Unit target'}],approval_requirement:'unknown',source_refs:[{type:'artifact',id:'unit-evidence',role:'observation'}],limitations:['Unit scope only']});
  state.results[0].recommendations=[advice('Unit adopted body')];state.adoptedResultId=ids.result;
  state.runs.push({...state.runs[0],id:'unit-later-run',title:'Unit later run'});
  state.results.push({...state.results[0],id:'unit-later-result',source_run_id:'unit-later-run',recommendations:[advice('Unit later body')]});
}
function assessmentFixture(state){
  recommendationFixture(state);
  const scope={kind:'selected_alerts',alert_ids:[ids.alert,'unit-removed-alert'],object_keys:['host:unit'],window_start:'2026-01-01T00:00:00Z',window_end:'2026-01-01T01:00:00Z',limitations:['Unit frozen scope']};
  const reference={type:'artifact',id:'unit-support',role:'observation',source_path:'rows',row_keys:['unit-row']};
  for(const [index,result] of state.results.entries()){
    result.findings=[{id:'unit-finding',statement:index?'Unit newer finding':'Unit adopted finding',state:'observed',scope:index?{...scope,alert_ids:[ids.alert]}:scope,support:[reference],counterevidence:[{...reference,id:'unit-counter',role:'human_statement'}],limitations:['Unit finding limit']}];
    result.questions=[{id:'unit-question',text:index?'Unit newer question':'Unit adopted question',state:'not_attempted',scope,evidence_requirements:['Unit evidence need'],answer:null,evidence_refs:[reference],limitations:[]}];
    result.case_impact={summary:'Unit original impact',supported_changes:[],cannot_generalize:['Unit no expansion'],affected_scope:scope,next_steps:[]};
  }
}
test('adopted basis and original removed-member scope remain separate from another selected Result',async t=>{
  const {state,base}=await startServer(t);assessmentFixture(state);const h=harness(base);h.start();await h.connect();
  state.results[0].business_verdict='needs_review';state.results[1].business_verdict='benign';
  await h.navigate(`#/cases/${ids.case}/case-info`);
  for(const marker of ['Unit adopted finding','Unit adopted question','unit-removed-alert','host:unit','unit-support','unit-counter','human_statement','Unit evidence need','Unit no expansion'])assert.ok(h.app.innerHTML.includes(marker),marker);
  assert.doesNotMatch(h.app.innerHTML,/Unit newer finding|Unit newer question/);
  assert.match(h.app.innerHTML,/data-business-verdict>待复核/);
  await h.navigate(`#/cases/${ids.case}/investigations?run=unit-later-run`);assert.match(h.app.innerHTML,/Unit newer finding/);assert.doesNotMatch(h.app.innerHTML,/Unit adopted finding/);
  assert.match(h.app.innerHTML,/data-business-verdict>正常/);assert.doesNotMatch(h.app.innerHTML,/data-business-verdict>待复核/);
  await h.click('refresh');assert.match(h.app.innerHTML,/Unit newer question/);
  await h.navigate(`#/cases/${ids.case}/overview`);assert.match(h.app.innerHTML,/Unit adopted finding/);assert.doesNotMatch(h.app.innerHTML,/Unit newer question/);
  assert.ok(state.requests.every(x=>x.method==='GET'));
});
test('basis read failure stays distinct from empty results and retries without business writes',async t=>{
  const {state,base}=await startServer(t);assessmentFixture(state);let failure=true;
  const h=harness(base,async(url,options)=>failure&&String(url).includes('/results/')?new Response('{}',{status:503}):fetch(url,options));
  h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);assert.match(h.app.innerHTML,/来源读取失败/);assert.doesNotMatch(h.app.innerHTML,/未保存未解决事项|Unit adopted finding/);
  failure=false;await h.click('refresh');assert.match(h.app.innerHTML,/Unit adopted finding/);
  state.results[0].findings=[];state.results[0].questions=[];await h.click('refresh');assert.match(h.app.innerHTML,/未保存未解决事项/);
  assert.ok(state.requests.every(x=>x.method==='GET'));
});
test('incident detail and a clicked older diagnostic round display only their own verdicts',async t=>{
  const {base}=await startServer(t);let wrongRun=false;
  const target=`/incidents/${ids.incident}`,path=`${target}/analysis/runs/${ids.run}`;
  const h=harness(base,async(url,options)=>{
    const relative=new URL(url).pathname.replace('/api/v1/socai2','');
    if(relative===target)return new Response(JSON.stringify({facts:{id:ids.incident,title:'Unit incident'},business_verdict:'benign'}));
    if(relative===path)return new Response(JSON.stringify({run:{id:ids.run,kind:'incident_diagnosis'},
      result:{source_run_id:wrongRun?ids.target:ids.run,business_verdict:'needs_review',diagnosis:{conclusion:'Unit original diagnosis'}}}));
    return fetch(url,options);
  });
  h.start();await h.connect();await h.navigate(`#/incidents/${ids.incident}/case-info`);
  assert.match(h.app.innerHTML,/data-business-verdict>正常/);
  await h.navigate(`#/incidents/${ids.incident}/investigations?run=${ids.run}`);
  assert.match(h.app.innerHTML,/data-business-verdict>待复核/);assert.match(h.app.innerHTML,/Unit original diagnosis/);
  assert.doesNotMatch(h.app.innerHTML,/data-business-verdict>正常/);
  wrongRun=true;await h.click('refresh');assert.match(h.app.innerHTML,/诊断不属于所选事件或轮次/);
  assert.doesNotMatch(h.app.innerHTML,/data-business-verdict>待复核/);
});
test('incident diagnostic failure keeps the scoped record and its explicit null result fields visible',async t=>{
  const {base}=await startServer(t),target=`/incidents/${ids.incident}`,reason='stage_core_conclusion_unavailable';
  const h=harness(base,async(url,options)=>{
    const relative=new URL(url).pathname.replace('/api/v1/socai2','');
    if(relative===target)return new Response(JSON.stringify({facts:{id:ids.incident,title:'Unit incident facts'},business_verdict:null}));
    if(relative===`${target}/analysis/runs/${ids.run}`)return new Response(JSON.stringify({
      run:{id:ids.run,kind:'incident_diagnosis',state:'failed',stop_reason:reason},
      result:{source_run_id:ids.run,state:'failed',error_code:reason,business_verdict:null,diagnosis:null,summary:null,open_questions:null},
    }));
    return fetch(url,options);
  });
  h.start();await h.connect();await h.navigate(`#/incidents/${ids.incident}/investigations?run=${ids.run}`);
  assert.match(h.app.innerHTML,/Unit incident facts/);
  assert.match(h.app.innerHTML,/本轮诊断失败 · stage_core_conclusion_unavailable/);
  assert.match(h.app.innerHTML,/本轮暂无诊断正文/);
  assert.match(h.app.innerHTML,/data-business-verdict>未记录/);
  assert.doesNotMatch(h.app.innerHTML,/诊断不属于所选事件或轮次|data-business-verdict>待复核/);
});

test('incomplete human or artifact source references fail explicitly without a latest Result fallback',async t=>{
  const {state,base}=await startServer(t);assessmentFixture(state);
  const h=harness(base,async(url,options)=>{const response=await fetch(url,options);if(!String(url).endsWith('/cases/'+ids.case))return response;const data=await response.json();data.current_assessment.sources=[{task_revision_id:'unit-old-revision'},{artifact_id:'unit-closing-report'}];return new Response(JSON.stringify(data),{status:200});});
  h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);assert.match(h.app.innerHTML,/来源未提供任务ID/);assert.match(h.app.innerHTML,/来源未提供工件所属轮次/);assert.match(h.app.innerHTML,/unit-old-revision/);assert.doesNotMatch(h.app.innerHTML,/Unit adopted finding|Unit newer finding/);
  assert.ok(!state.requests.some(x=>x.pathname.includes('/results/')));
});
function frozenSourceFixture(state){
  const original=state.revisions[0];Object.assign(original,{state:'completed',result_text:'Unit adopted old feedback',result_scope:{kind:'selected_alerts',alert_ids:['unit-removed'],object_keys:['host:unit'],window_start:null,window_end:null,limitations:['Unit frozen limit']},source_refs:[{type:'artifact',id:ids.artifact,role:'human_statement'}]});
  const current={...original,id:'unit-new-revision',revision:2,result_text:'Unit newer feedback'};state.revisions.push(current);state.tasks[0].current=current;state.tasks[0].current_revision_id=current.id;
  state.adoptionSources=[{task_revision_id:original.id,task_id:original.task_id},{artifact_id:ids.artifact,run_id:ids.run},{artifact_id:'unit-case-artifact',run_id:null}];
  state.artifactContents={[ids.artifact]:{artifact:{id:ids.artifact,case_id:ids.case,run_id:ids.run,kind:'source_snapshot'},content_json:{saved:'Unit Run artifact',zero:0,flag:false},content_text:null,availability:'available'},'unit-case-artifact':{artifact:{id:'unit-case-artifact',case_id:ids.case,run_id:null,kind:'report_markdown'},content_json:null,content_text:'Unit Case artifact',availability:'retained_partial'}};
}
test('adopted human revision and both artifact levels read their frozen HTTP identities',async t=>{
  const {state,base}=await startServer(t);frozenSourceFixture(state);const h=harness(base);h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);
  for(const marker of ['Unit adopted old feedback','unit-removed','Unit frozen limit','human_statement','Unit Run artifact','Unit Case artifact','retained_partial'])assert.ok(h.app.innerHTML.includes(marker),marker);
  assert.doesNotMatch(h.app.innerHTML,/Unit newer feedback/);
  for(const path of [`/cases/${ids.case}/tasks/${ids.task}/revisions/${ids.revision}`,`/cases/${ids.case}/runs/${ids.run}/artifacts/${ids.artifact}`,`/cases/${ids.case}/artifacts/unit-case-artifact`])assert.ok(state.requests.some(x=>x.pathname===path));
  assert.ok(!state.requests.some(x=>x.pathname.endsWith('/tasks')||x.pathname.endsWith('/tasks/'+ids.task)||x.pathname.includes('/results/')));
  await h.click('refresh');assert.match(h.app.innerHTML,/Unit adopted old feedback/);assert.ok(state.requests.every(x=>x.method==='GET'));
});
test('one frozen source may fail and retry while other sources remain visible; foreign versions are rejected',async t=>{
  const {state,base}=await startServer(t);frozenSourceFixture(state);let failed=true,wrong=false;
  const h=harness(base,async(url,options)=>{if(failed&&String(url).endsWith('/artifacts/'+ids.artifact))return new Response('{}',{status:503});const response=await fetch(url,options);if(wrong&&String(url).includes('/revisions/')){const body=await response.json();body.id='unit-new-revision';body.result_text='Unit newer feedback';return new Response(JSON.stringify(body));}return response;});
  h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/overview`);assert.match(h.app.innerHTML,/来源读取失败/);assert.match(h.app.innerHTML,/Unit adopted old feedback/);assert.match(h.app.innerHTML,/Unit Case artifact/);assert.doesNotMatch(h.app.innerHTML,/Unit Run artifact/);
  failed=false;await h.click('refresh');assert.match(h.app.innerHTML,/Unit Run artifact/);wrong=true;await h.click('refresh');assert.match(h.app.innerHTML,/人工版本与采用来源不一致/);assert.doesNotMatch(h.app.innerHTML,/Unit adopted old feedback|Unit newer feedback/);assert.match(h.app.innerHTML,/Unit Case artifact/);assert.ok(state.requests.every(x=>x.method==='GET'));
});
test('late frozen-source content cannot replace a subsequently opened subject list',async t=>{
  const {state,base}=await startServer(t);frozenSourceFixture(state);let finish;
  const h=harness(base,async(url,options)=>{if(String(url).includes('/revisions/')){const response=await fetch(url,options);return new Promise(resolve=>{finish=()=>resolve(response);});}return fetch(url,options);});
  h.start();await h.connect();const reading=h.navigate(`#/cases/${ids.case}/case-info`);
  while(!finish)await new Promise(resolve=>setImmediate(resolve));await h.navigate('#/cases');const renders=h.renders;finish();await reading;assert.equal(h.renders,renders);assert.doesNotMatch(h.app.innerHTML,/Unit adopted old feedback|Unit Case artifact/);
});
test('current adopted recommendations and selected Run keep separate sources after switching and refresh',async t=>{
  const {state,base}=await startServer(t);recommendationFixture(state);const h=harness(base);h.start();await h.connect();
  await h.navigate(`#/cases/${ids.case}/case-info`);
  assert.match(h.app.innerHTML,/Unit adopted body/);assert.doesNotMatch(h.app.innerHTML,/Unit later body/);
  for(const marker of ['Unit target','host:unit','unit-evidence','Unit scope only','审批要求未知'])assert.ok(h.app.innerHTML.includes(marker));
  await h.navigate(`#/cases/${ids.case}/investigations?run=unit-later-run&view=report`);
  assert.match(h.app.innerHTML,/Unit later body/);assert.doesNotMatch(h.app.innerHTML,/Unit adopted body/);
  await h.click('refresh');assert.match(h.app.innerHTML,/Unit later body/);
  await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}&view=report`);assert.match(h.app.innerHTML,/Unit adopted body/);assert.doesNotMatch(h.app.innerHTML,/Unit later body/);
  assert.ok(state.requests.every(x=>x.method==='GET'));
});
test('recommendation read errors and identity mismatch are retryable and never shown as empty advice',async t=>{
  const {state,base}=await startServer(t);recommendationFixture(state);let fault='failed';
  const h=harness(base,async(url,options)=>{
    const response=await fetch(url,options);if(!String(url).includes('/results/'))return response;
    if(fault==='failed')return new Response(JSON.stringify({detail:'unit_read_failed'}),{status:503});
    if(fault==='mismatch'){const data=await response.json();data.result.source_run_id='unit-other-run';return new Response(JSON.stringify(data),{status:200});}
    return response;
  });h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);
  assert.match(h.app.innerHTML,/来源读取失败/);assert.doesNotMatch(h.app.innerHTML,/本结果未保存建议/);
  fault=null;await h.click('refresh');assert.match(h.app.innerHTML,/Unit adopted body/);
  fault='mismatch';await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}`);assert.match(h.app.innerHTML,/结果读取失败/);assert.doesNotMatch(h.app.innerHTML,/Unit adopted body/);
  fault=null;state.results[0].recommendations=[];await h.click('refresh');assert.match(h.app.innerHTML,/本结果未保存建议/);
});
test('late current-source read cannot replace a subsequently selected Run',async t=>{
  const {state,base}=await startServer(t);recommendationFixture(state);let enter,release;
  const entered=new Promise(resolve=>enter=resolve),gate=new Promise(resolve=>release=resolve);
  const h=harness(base,async(url,options)=>{const response=await fetch(url,options);if(String(url).endsWith('/results/'+ids.result)){enter();await gate;}return response;});
  h.start();await h.connect();const pending=h.navigate(`#/cases/${ids.case}/case-info`);await entered;
  await h.navigate(`#/cases/${ids.case}/investigations?run=unit-later-run`);release();await pending;
  assert.match(h.app.innerHTML,/Unit later body/);assert.doesNotMatch(h.app.innerHTML,/Unit adopted body/);
});

test('service entry takes control before demo initialization; default remains demo',()=>{
  const h=harness();assert.equal(h.api.active(),true);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app.js'),'utf8'),h.context);
  assert.match(h.app.innerHTML,/连接调查服务/);assert.match(h.app.innerHTML,/type="password"/);assert.doesNotMatch(h.app.innerHTML,/synthetic-only/);
  delete h.context.window.socai2ServiceWorkspace;vm.runInContext(fs.readFileSync(path.join(__dirname,'../app.js'),'utf8'),h.context);assert.match(h.app.innerHTML,/案件服务页面未能加载/);
  h.location.search='';assert.equal(h.api.active(),false);
  assert.doesNotMatch(source,/localStorage|sessionStorage/);
});

test('client uses Bearer with no URL credential, cookies, cache, redirect or automatic retry',async()=>{
  const h=harness();const calls=[];
  const client=h.api.createClient('https://case.example/api/v1/socai2','memory-token',async(url,options)=>{calls.push({url,options});return {ok:false,status:409,json:async()=>({detail:'conflict'})};});
  await assert.rejects(client.request('/cases/c/tasks',{method:'POST',body:{title:'input'},query:{q:'中文 & 范围'}}),error=>error.status===409);
  assert.equal(calls.length,1);assert.equal(calls[0].options.headers.Authorization,'Bearer memory-token');assert.equal(calls[0].options.credentials,'omit');assert.equal(calls[0].options.redirect,'error');assert.equal(calls[0].options.cache,'no-store');assert.doesNotMatch(calls[0].url,/memory-token/);
  for(const base of ['https://user:pass@case.example/api','http://remote.example/api','https://case.example/api?token=secret'])assert.throws(()=>h.api.createClient(base,'x'));
});

test('H scope keeps optional objects and null time, metadata revision and prior references',()=>{
  const h=harness(),existing={row_version:4,current:{source_refs:[{type:'result',id:ids.result,unused:'strip'}]}};
  const payload=h.api.taskPayload(taskValues,[ids.alert],existing,7,ids.revision);
  assert.deepEqual(plain(payload.result_scope),{kind:'selected_alerts',alert_ids:[ids.alert],object_keys:[],window_start:null,window_end:null,limitations:['不推广到其他主机']});assert.equal(payload.expected_row_version,4);assert.equal(payload.expected_scope_revision,7);assert.deepEqual(plain(payload.source_refs),[{type:'result',id:ids.result}]);
  assert.throws(()=>h.api.taskPayload(taskValues,[],null,1,ids.revision),/明确选择成员/);
  assert.throws(()=>h.api.taskPayload({...taskValues,kind:'explicit_objects'},[ids.alert],null,1,ids.revision),/至少选择一个对象/);
  assert.throws(()=>h.api.taskPayload({...taskValues,window_start:'2026-11-05T10:00'},[ids.alert],null,1,ids.revision),/同时填写/);
  const original={...plain(payload.result_scope),window_start:'2026-11-05T00:00:00Z',window_end:'2026-11-05T00:10:00Z'};const saved={row_version:5,current:{state:'completed',result_text:taskValues.result_text,result_scope:original,source_refs:[],due_at:null}};
  const normalized={...taskValues,window_start:h.api.localInputTime(original.window_start).replace(/:00\.000$/,''),window_end:h.api.localInputTime(original.window_end).replace(/:00\.000$/,'')};const unchanged=h.api.taskPayload(normalized,[ids.alert],saved,2,ids.revision);assert.deepEqual(plain(unchanged.result_scope),original);assert.equal(h.api.taskFactsChanged(unchanged,saved),false);
});

test('basis freshness and coverage remain separate, truncated scope stays unknown',()=>{
  const {api}=harness();const detail={member_count:2,members:[{alert_id:ids.alert},{alert_id:ids.extra}],members_truncated:false,current_assessment:{value:{conclusion:'待核实'},members:[{alert_id:ids.alert}],members_truncated:false,covers_current_members:false,uncovered_current_alert_ids:[ids.extra],input_freshness:{state:'current',reasons:[]}}};
  let a=api.assessmentModel(detail);assert.equal(a.freshness,'current');assert.equal(a.covered,1);assert.equal(a.total,2);assert.equal(a.coverageKnown,true);assert.deepEqual(plain(a.uncovered),[ids.extra]);
  detail.current_assessment.input_freshness={state:'stale',reasons:['human_feedback_changed']};assert.match(api.assessmentModel(detail).freshnessLabel,/需重新调查/);
  detail.members_truncated=true;detail.current_assessment.covers_current_members=null;a=api.assessmentModel(detail);assert.equal(a.coverageKnown,false);
  delete detail.current_assessment.input_freshness;assert.equal(api.assessmentModel(detail).freshness,'unverified');
  const groups=api.groupRuns(['running','unknown','pending_update','completed'].map(state=>({run:{state}})));assert.deepEqual(plain(groups.active.map(x=>x.run.state)),['running','unknown']);assert.deepEqual(plain(groups.pending.map(x=>x.run.state)),['pending_update']);
});

test('HTTP queue -> H save -> stale basis -> async check -> task read and frozen material',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();const connection=await h.connect();assert.equal(connection.token.value,'');assert.match(h.app.innerHTML,/模拟验证/);assert.equal(state.requests[0].hasBearer,true);
  await h.navigate(`#/cases/${ids.case}/tasks`);assert.match(h.app.innerHTML,/完成者/);assert.match(h.app.innerHTML,/修改者/);await h.click('edit-task',ids.task);
  await h.submit('task',[...Object.entries(taskValues),['scope_member',ids.alert]]);assert.equal(state.tasks[0].current.state,'completed');assert.equal(state.tasks[0].row_version,2);assert.match(h.app.innerHTML,/人工结果已保存/);
  await h.click('task-revisions',ids.task);assert.match(h.app.innerHTML,/版本 2/);await h.click('close');
  await h.navigate(`#/cases/${ids.case}/overview`);assert.match(h.app.innerHTML,/调查依据已更新，需重新调查/);
  await h.click('prepare');assert.equal(state.analysisTasks.length,0);await h.submit('analysis',{mode:'check'});
  assert.equal(state.analysisTasks.length,1);assert.equal(state.analysisTasks[0].intent,'check');assert.match(h.app.innerHTML,/分析任务 · 已受理/);assert.match(h.app.innerHTML,/尚无执行尝试或Run/);assert.equal(state.runs.length,1);
  assert.equal(state.requests.filter(x=>x.pathname.endsWith('/start')||x.pathname.endsWith('/baseline/prepare')).length,0);
  const submission=state.requests.find(x=>x.pathname.endsWith('/investigations'));assert.deepEqual(Object.keys(submission.body).sort(),['mode','operation_key']);
  state.analysisTasks[0].status='skipped';state.analysisTasks[0].reason_code='no_changes';await h.click('refresh-analysis-task');assert.match(h.app.innerHTML,/no_changes/);
  await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}&view=process`);assert.match(h.app.innerHTML,/部分交付/);assert.match(h.app.innerHTML,/执行步骤/);await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}&view=tools`);await h.click('material',ids.material);assert.match(h.app.innerHTML,/Process Start/);await h.click('close');await h.click('artifact',ids.artifact);assert.match(h.app.innerHTML,/task_revisions/);
  await h.navigate(`#/cases/${ids.case}/investigations?result=${ids.result}`);assert.match(h.app.innerHTML,/仅适用于当前一条成员/);
});

test('create follows every actual allocation and reads initial task without a second submission',async t=>{
  const {state,base}=await startServer(t);state.allocationIds=[ids.case,ids.target];const h=harness(base);h.start();await h.connect();await h.click('create');await h.submit('create',[['title','New investigation'],['alert',ids.extra]]);
  assert.match(h.app.innerHTML,/实际案件分配/);for(const id of state.allocationIds){assert.ok(h.app.innerHTML.includes(`#/cases/${id}/overview`));assert.ok(state.requests.some(x=>x.method==='GET'&&x.pathname===`/cases/${id}`));assert.ok(state.requests.some(x=>x.method==='GET'&&x.pathname.startsWith(`/cases/${id}/analysis-tasks/`)));}
  assert.equal(state.analysisTasks.length,2);assert.equal(state.requests.filter(x=>x.method==='POST').length,1);assert.equal(h.location.hash,'#/cases');
});

test('accepted task with failed read keeps receipt and retries GET only; mismatched task is rejected',async t=>{
  const {state,base}=await startServer(t);let failRead=true,wrongIdentity=false;const h=harness(base,async(url,options)=>{
    if(options.method==='GET'&&/\/analysis-tasks\/[^/]+$/.test(new URL(url).pathname)){
      if(failRead)throw Error('read unavailable');const response=await fetch(url,options),task=await response.json();if(wrongIdentity)task.subject_id=ids.target;return new Response(JSON.stringify(task),{status:200});
    }return fetch(url,options);
  });h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/overview`);await h.click('rerun');await h.submit('analysis',{mode:'rerun'});
  assert.match(h.box.innerHTML,/连接失败/);assert.equal(state.analysisTasks.length,1);failRead=false;wrongIdentity=true;await h.submit('analysis',{mode:'rerun'});assert.match(h.box.innerHTML,/身份或读取链接不一致/);
  wrongIdentity=false;await h.submit('analysis',{mode:'rerun'});assert.match(h.app.innerHTML,/分析任务 · 已受理/);assert.equal(state.requests.filter(x=>x.method==='POST').length,1);
});

test('unknown submission preserves mode and key and late response cannot replace another subject',async t=>{
  const {state,base}=await startServer(t);let lose=true;const h=harness(base,async(url,options)=>{const response=await fetch(url,options);if(options.method==='POST'&&lose){lose=false;throw Error('lost response');}return response;});h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/overview`);await h.click('prepare');await h.submit('analysis',{mode:'check'});await h.submit('analysis',{mode:'rerun'});assert.match(h.box.innerHTML,/勿改意图重发/);assert.equal(state.requests.filter(x=>x.method==='POST').length,1);await h.submit('analysis',{mode:'check'});
  const posts=state.requests.filter(x=>x.method==='POST');assert.equal(posts.length,2);assert.deepEqual(posts[0].body,posts[1].body);assert.equal(state.analysisTasks.length,1);
  let release,entered;const started=new Promise(resolve=>entered=resolve),gate=new Promise(resolve=>release=resolve);const late=harness(base,async(url,options)=>{const response=await fetch(url,options);if(options.method==='POST'){entered();await gate;}return response;});late.start();await late.connect();await late.navigate(`#/cases/${ids.case}/overview`);await late.click('rerun');const pending=late.submit('analysis',{mode:'rerun'});await started;await late.navigate(`#/cases/${ids.target}/overview`);release();await pending;assert.doesNotMatch(late.app.innerHTML,/请求已受理，以下显示/);assert.equal(late.location.hash,`#/cases/${ids.target}/overview`);
});

test('allocation receipt rejects missing initial task and foreign status URL',()=>{
  const {api}=harness();assert.throws(()=>api.allocationTargets({case_id:ids.case}),/实际案件分配/);assert.throws(()=>api.allocationTargets({allocations:[{case_id:ids.case,created:true}]}),/首轮任务/);
  assert.throws(()=>api.analysisTaskPath({task_id:ids.task,subject_type:'case',subject_id:ids.case,status_url:'https://foreign.invalid/task'},'case',ids.case),/身份或读取链接/);
});

test('incident diagnosis uses the async endpoint and displays its independently read task',async t=>{
  const {state,base}=await startServer(t);const h=harness(base,async(url,options)=>{
    const p=new URL(url).pathname;
    if(p.endsWith('/incidents/'+ids.incident))return new Response(JSON.stringify({facts:{id:ids.incident,title:'Incident',handling_status:'in_progress'},derived:{}}));
    if(p.endsWith('/analysis-runs'))return new Response(JSON.stringify({items:[],next_cursor:null}));
    return fetch(url,options);
  });h.start();await h.connect();await h.navigate(`#/incidents/${ids.incident}/investigations`);assert.match(h.app.innerHTML,/检查并更新诊断/);await h.click('prepare');await h.submit('analysis',{mode:'check'});
  const task=state.analysisTasks[0];assert.equal(task.subject_type,'incident');assert.equal(task.subject_id,ids.incident);assert.match(h.app.innerHTML,/分析任务 · 已受理/);assert.ok(state.requests.some(x=>x.method==='POST'&&x.pathname===`/incidents/${ids.incident}/diagnose`));assert.ok(state.requests.some(x=>x.method==='GET'&&x.pathname===`/incidents/${ids.incident}/analysis-tasks/${task.task_id}`));
});

test('HTTP 409 retains task form and values; latest version is read without saving or discarding input',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/tasks`);await h.click('edit-task',ids.task);state.rejectNextTask=true;
  const renders=h.renders;const form=await h.submit('task',[...Object.entries(taskValues),['scope_member',ids.alert]]);assert.equal(h.renders,renders);assert.match(h.box.innerHTML,/输入内容已保留/);assert.match(h.box.innerHTML,/查看最新版本/);assert.equal(form.fields.find(([key])=>key==='result_text')[1],taskValues.result_text);assert.equal(state.tasks[0].row_version,1);
  await h.click('latest-task');assert.match(h.box.innerHTML,/最新版本 1/);assert.equal(h.renders,renders);await h.click('reload-task');assert.equal(h.renders,renders);assert.equal(state.requests.filter(x=>x.method==='PUT').length,1);
});

test('service failure clears previously shown queue without fixture fallback or writes',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();await h.connect();assert.match(h.app.innerHTML,/模拟验证/);state.fault=503;await h.click('refresh');assert.match(h.app.innerHTML,/服务暂时不可用/);assert.doesNotMatch(h.app.innerHTML,/模拟验证/);assert.equal(state.requests.filter(x=>x.method!=='GET').length,0);
});

test('HTTP association and move send selected members and both actual scope revisions',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/alerts`);await h.click('associate');await h.submit('associate',[['alert',ids.extra]]);assert.equal(state.members.length,2);assert.equal(state.cas.scope_revision,2);
  await h.submit('move-select',[['member',ids.extra]]);await h.submit('move',{target:ids.target});const move=state.requests.find(x=>x.pathname.endsWith('/members/move'));assert.deepEqual(move.body.alert_ids,[ids.extra]);assert.equal(move.body.expected_source_scope_revision,2);assert.equal(move.body.expected_target_scope_revision,2);assert.equal(state.members.length,1);
});

test('running plus pending render independently and pending start remains unavailable',async t=>{
  const {state,base}=await startServer(t);state.runs.push({...state.runs[0],id:'pending',state:'pending_update',title:'待启动记录'});state.runs[0].state='running';const h=harness(base);h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/overview`);assert.match(h.app.innerHTML,/正在执行 \/ 状态待核实/);assert.match(h.app.innerHTML,/尚未执行的Run/);assert.doesNotMatch(h.app.innerHTML,/data-svc="start"/);assert.match(h.app.innerHTML,/尚无已受理的分析任务/);assert.equal(state.requests.filter(x=>x.method==='POST').length,0);
});

test('H metadata edits preserve original whole-case scope and subsecond timestamps after membership changes',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);
  const original={kind:'whole_case',alert_ids:[ids.extra,ids.alert],object_keys:[],window_start:'2026-11-05T00:00:12.123456Z',window_end:'2026-11-05T00:30:45.654321Z',limitations:['仅原范围']};
  Object.assign(state.tasks[0].current,{state:'completed',result_text:'原人工确认',result_scope:original,completed_by:ids.actor,completed_at:'2026-11-05T00:35:01Z'});
  h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/tasks`);await h.click('edit-task',ids.task);
  const fields={...taskValues,title:'只改任务标题',result_text:'原人工确认',kind:'whole_case',window_start:h.api.localInputTime(original.window_start),window_end:h.api.localInputTime(original.window_end),limitations:'仅原范围'};
  const body=h.api.taskPayload(fields,[ids.alert,ids.extra],state.tasks[0],1,ids.revision);assert.equal(h.api.taskFactsChanged(body,state.tasks[0]),false);assert.deepEqual(plain(body.result_scope),original);
  await h.submit('task',[...Object.entries(fields),['scope_member',ids.alert],['scope_member',ids.extra]]);const put=state.requests.find(x=>x.method==='PUT');assert.ok(put);assert.deepEqual(put.body.result_scope,original);assert.equal(put.body.title,'只改任务标题');
  const changed=h.api.taskPayload({...fields,result_text:'改了确认事实'},[ids.alert,ids.extra],state.tasks[0],1,ids.revision);assert.equal(h.api.taskFactsChanged(changed,state.tasks[0]),true);
});

test('service uses the same global and Case frames as demo and keeps unsupported navigation unavailable',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();await h.connect();assert.match(h.app.innerHTML,/case-queue-metrics/);assert.match(h.app.innerHTML,/table-card/);assert.match(h.app.innerHTML,/nav-item selected/);
  await h.navigate(`#/cases/${ids.case}/case-info`);assert.match(h.app.innerHTML,/sidebar compact/);assert.match(h.app.innerHTML,/class="case-body"/);assert.match(h.app.innerHTML,/aria-label="Case 内部导航"/);assert.match(h.app.innerHTML,/case-overview-grid/);assert.match(h.app.innerHTML,/copilot-card/);assert.match(h.app.innerHTML,/Case 详细信息/);assert.match(h.app.innerHTML,/案件故事暂未开放/);assert.doesNotMatch(h.app.innerHTML,/<nav class="tabs">/);
  const before=state.requests.length;await h.click('new-task');await h.click('close');assert.equal(state.requests.length,before);
});

test('original single-run tabs keep saved capability limits explicit without inferring legacy capacity',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();await h.connect();
  await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}&view=process`);assert.match(h.app.innerHTML,/aria-label="调查运行内容"/);assert.match(h.app.innerHTML,/未提供本轮能力快照/);assert.doesNotMatch(h.app.innerHTML,/四个分析视角共用一次/);
  state.executionSummary={artifact_id:ids.artifact,availability:'available',capabilities:{offered_tools_at_start:[],binding_count:0,limitations:['four_domains_share_one_model_pass','200_members_storage_limit_not_model_capacity_promise'],unsupported:['authentication_requires_frozen_source_hostname']},limits:{max_model_tokens:48000},final_reservation:{},limitations:[]};
  await h.click('refresh');assert.match(h.app.innerHTML,/四个分析视角共用一次模型分析/);assert.match(h.app.innerHTML,/200 条成员是保存上限/);assert.match(h.app.innerHTML,/缺少主机时无法绑定/);assert.match(h.app.innerHTML,/启动时可提供的查询：无/);
  await h.navigate(`#/cases/${ids.case}/investigations?result=${ids.result}`);assert.match(h.app.innerHTML,/调查详情/);assert.match(h.app.innerHTML,/现有依据不足/);assert.doesNotMatch(h.app.innerHTML,/48000/);
  await h.navigate(`#/cases/${ids.case}/tasks`);assert.doesNotMatch(h.app.innerHTML,/来源调查结果/);await h.click('task-revisions',ids.task);assert.match(h.app.innerHTML,/查看原调查结果/);
});

test('risk conflict keeps the draft and key until explicit latest-version acceptance; success independently reads',async t=>{
  const {state,base}=await startServer(t),writes=[];let conflict=true,detailReads=0;
  const fetcher=async(url,options)=>{
    const pathname=new URL(url).pathname;
    if(pathname.endsWith('/management')){
      const body=JSON.parse(options.body);writes.push(body);
      if(conflict)return new Response(JSON.stringify({detail:'row_version_conflict'}),{status:409});
      state.cas.severity=body.severity;state.cas.priority_value=body.priority_value;state.cas.row_version++;
      return new Response(JSON.stringify({case:state.cas,changed:true}));
    }
    if(pathname.endsWith('/cases/'+ids.case))detailReads++;
    return fetch(url,options);
  };
  state.cas.row_version=2;
  const h=harness(base,fetcher);h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);await h.click('manage-risk');
  const input={level_action:'set',level:'low',level_reason:'severity_reason',priority_action:'set',priority:'0',priority_reason:'priority_reason'};
  const renders=h.renders,form=await h.submit('risk',input);
  assert.equal(h.renders,renders);assert.match(h.box.innerHTML,/保留草稿/);assert.equal(form.fields.find(x=>x[0]==='priority')[1],'0');
  await h.submit('risk',input);assert.equal(writes[0].operation_key,writes[1].operation_key);
  state.cas.row_version=3;await h.click('latest-risk');assert.equal(h.renders,renders);assert.equal(writes.length,2);
  await h.click('accept-risk-version');assert.equal(h.renders,renders);conflict=false;
  const before=detailReads;await h.submit('risk',input);
  assert.notEqual(writes[2].operation_key,writes[0].operation_key);assert.equal(writes[2].expected_row_version,3);assert.equal(writes[2].priority_value,0);assert.ok(detailReads>before);assert.equal(state.cas.priority_value,0);
});

test('unknown management response retries the same request and never silently changes intent or operation key',async t=>{
  const {base}=await startServer(t),writes=[];
  const h=harness(base,async(url,options)=>{if(new URL(url).pathname.endsWith('/management')){writes.push(JSON.parse(options.body));throw new TypeError('network_unknown');}return fetch(url,options);});
  h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);await h.click('manage-risk');
  const input={level_action:'keep',priority_action:'set',priority:'0',priority_reason:'priority_reason'};
  await h.submit('risk',input);await h.submit('risk',{...input,priority:'1'});assert.equal(writes.length,1);assert.match(h.box.innerHTML,/尚未确认/);
  await h.submit('risk',input);assert.deepEqual(writes[1],writes[0]);
});

test('late management response cannot replace the subject reached after navigation',async t=>{
  const {base}=await startServer(t);let finish;
  const h=harness(base,async(url,options)=>{if(new URL(url).pathname.endsWith('/management'))return new Promise(resolve=>{finish=()=>resolve(new Response('{}'));});return fetch(url,options);});
  h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/case-info`);await h.click('manage-risk');
  const saving=h.submit('risk',{level_action:'keep',priority_action:'clear',priority_reason:'priority_reason'});
  await h.navigate('#/cases');const renders=h.renders;finish();await saving;
  assert.equal(h.renders,renders);assert.doesNotMatch(h.app.innerHTML,/属性已保存/);
});
