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
  for(const file of ['icons.js','workspace-layout.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../'+file),'utf8'),context);
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

test('service entry takes control before demo initialization; default remains demo',()=>{
  const h=harness();assert.equal(h.api.active(),true);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app.js'),'utf8'),h.context);
  assert.match(h.app.innerHTML,/连接案件服务/);assert.match(h.app.innerHTML,/type="password"/);assert.doesNotMatch(h.app.innerHTML,/synthetic-only/);
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

test('HTTP queue -> H save -> refreshed stale basis -> prepare/start -> history and frozen material',async t=>{
  const {state,base}=await startServer(t);const h=harness(base);h.start();const connection=await h.connect();assert.equal(connection.token.value,'');assert.match(h.app.innerHTML,/模拟验证/);assert.equal(state.requests[0].hasBearer,true);
  await h.navigate(`#/cases/${ids.case}/tasks`);assert.match(h.app.innerHTML,/完成者/);assert.match(h.app.innerHTML,/修改者/);await h.click('edit-task',ids.task);
  await h.submit('task',[...Object.entries(taskValues),['scope_member',ids.alert]]);assert.equal(state.tasks[0].current.state,'completed');assert.equal(state.tasks[0].row_version,2);assert.match(h.app.innerHTML,/人工结果已保存/);
  await h.click('task-revisions',ids.task);assert.match(h.app.innerHTML,/版本 2/);await h.click('close');
  await h.navigate(`#/cases/${ids.case}/overview`);assert.match(h.app.innerHTML,/调查依据已更新，需重新调查/);
  await h.click('prepare');const pending=state.runs.find(x=>x.state==='pending_update');assert.ok(pending);assert.equal(state.requests.filter(x=>x.pathname.endsWith('/start')).length,0);assert.match(h.app.innerHTML,/待启动的下一轮/);
  await h.click('start',pending.id);await h.submit('start',{window_start:'',window_end:''});assert.equal(pending.state,'completed');assert.match(h.app.innerHTML,/本轮调查依据未变化/);
  await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}&view=process`);assert.match(h.app.innerHTML,/部分交付/);assert.match(h.app.innerHTML,/执行步骤/);await h.navigate(`#/cases/${ids.case}/investigations?run=${ids.run}&view=tools`);await h.click('material',ids.material);assert.match(h.app.innerHTML,/Process Start/);await h.click('close');await h.click('artifact',ids.artifact);assert.match(h.app.innerHTML,/task_revisions/);
  await h.navigate(`#/cases/${ids.case}/investigations?result=${ids.result}`);assert.match(h.app.innerHTML,/仅适用于当前一条成员/);
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
  const {state,base}=await startServer(t);state.runs.push({...state.runs[0],id:'pending',state:'pending_update',title:'待启动记录'});state.runs[0].state='running';const h=harness(base);h.start();await h.connect();await h.navigate(`#/cases/${ids.case}/overview`);assert.match(h.app.innerHTML,/正在执行 \/ 状态待核实/);assert.match(h.app.innerHTML,/待启动的下一轮/);assert.match(h.app.innerHTML,/data-id="pending" disabled/);assert.match(h.app.innerHTML,/已有调查正在执行或状态待核实/);assert.equal(state.requests.filter(x=>x.method==='POST').length,0);
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
