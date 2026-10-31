const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
test('incident association explanations use exact shared identities and distinct source alerts',()=>{
 const x=load(),members=[{id:'a',entityIds:['host','host','user','same-name-1']},{id:'b',entityIds:['host','user','same-name-2']},{id:'c',entityIds:['host']}];
 const store={assets:[{id:'host',name:'HOST',type:'device'},{id:'user',name:'Account',type:'user'},{id:'same-name-1',name:'Duplicate'},{id:'same-name-2',name:'Duplicate'}]};
 const before=JSON.stringify({store,members}),rows=x.M.sharedObjects(store,members);
 assert.deepEqual(Array.from(rows,r=>[r.id,r.alerts.length]),[['host',3],['user',2]]);assert.equal(JSON.stringify({store,members}),before);
});
test('incident overview focuses on aggregation and linked business Cases rather than Run ownership or judgment',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident);x.s.location.hash=`#/incidents/${inc.id}/summary`;
 let html=x.incidentPage();for(const text of ['事件是什么','为什么关联在一起','共同主机','归并规则','进入 Case'])assert.ok(html.includes(text),text);
 for(const text of ['>基础调查<','>关联 AI 调查','调查判定：','>已有判定<','>继续核查<','choose-incident'])assert.ok(!html.includes(text),text);
 const linked=x.incidentCases(inc),runIds=JSON.stringify(x.M.runs(x.store));x.store.cases=x.store.cases.filter(c=>!linked.includes(c));
 html=x.incidentPage();assert.ok(html.includes('新建 Case'));assert.equal(x.incidentCases(inc).length,0);assert.equal(JSON.stringify(x.M.runs(x.store)),runIds);
 x.ui.modal={type:'incident-case',id:inc.id,mode:'existing'};html=x.modalMarkup();assert.ok(html.includes('关联已有 Case'));assert.ok(html.includes('新建 Case'));assert.ok(!html.includes('新 Case 名称'));assert.ok((html.match(/class="iv-case-choice /g)||[]).length<=7);
 x.ui.modal.mode='new';html=x.modalMarkup();assert.ok(html.includes('新 Case 名称'));assert.ok(html.includes(inc.title));assert.ok(!html.includes('搜索 Case'));
});
test('explicit incident Case creation and association preserve alerts, statuses, historical Runs and other memberships',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),linked=x.incidentCases(inc);x.store.cases=x.store.cases.filter(c=>!linked.includes(c));
 const alerts=JSON.stringify(x.store.alerts),runs=JSON.stringify(x.M.runs(x.store)),status=inc.status,members=Array.from(x.store.alerts.filter(a=>a.incidentId===inc.id),a=>a.id);
 assert.throws(()=>x.associateIncidentCase(inc,{mode:'new',title:' '}),/名称/);
 const c=x.associateIncidentCase(inc,{mode:'new',title:'联合核查'});assert.deepEqual(Array.from(c.alertIds),members);assert.equal(c.title,'联合核查');assert.equal(c.priority,null);assert.equal(x.incidentCases(inc)[0].id,c.id);
 assert.throws(()=>x.associateIncidentCase(inc,{mode:'new',title:'duplicate'}),/已关联/);
 const target=x.store.cases.find(row=>row.id==='17420'),before=[...target.alertIds];x.associateIncidentCase(inc,{mode:'existing',caseId:target.id});
 assert.deepEqual(Array.from(target.alertIds),[...new Set([...before,...members])]);assert.deepEqual(Array.from(c.alertIds),members);
 x.associateIncidentCase(inc,{mode:'existing',caseId:target.id});assert.equal(new Set(target.alertIds).size,target.alertIds.length);
 const foreign=x.store.cases.find(row=>row.recordedCase&&row.sourceEnvironment!==inc.sourceEnvironment);assert.throws(()=>x.associateIncidentCase(inc,{mode:'existing',caseId:foreign.id}),/可关联/);
 assert.equal(JSON.stringify(x.store.alerts),alerts);assert.equal(JSON.stringify(x.M.runs(x.store)),runs);assert.equal(inc.status,status);
 const reloaded=load(JSON.stringify(x.store));assert.equal(reloaded.store.cases.find(row=>row.id===c.id).alertIds.length,members.length);
});
test('a newly created incident Case renders actual Run completeness and empty collaboration without adopting fixture defaults',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='85b81836-be47-4ab0-8c1f-6d360c5fb0a2'),linked=x.incidentCases(inc);x.store.cases=x.store.cases.filter(c=>!linked.includes(c));
 const c=x.associateIncidentCase(inc,{mode:'new',title:'新建联合核查'});assert.equal(c.incidentCreated,true);assert.equal(c.recordedCase,undefined);assert.equal(c.localCollection,undefined);assert.equal(c.sourceTenantId,inc.sourceTenantId);
 for(const state of [x,load(JSON.stringify(x.store))]){
  const current=state.store.cases.find(row=>row.id===c.id);assert.equal(state.caseQueueRows().find(row=>row.id===c.id).investigation,'Partial');
  assert.equal(state.incidentCases(state.store.incidents.find(row=>row.id===inc.id)).find(row=>row.id===c.id).id,c.id);
  const before=JSON.stringify(state.store);for(const view of ['overview','case-info','alerts','assets','attack','evidence','investigations','tasks','activities','comments']){
   state.s.location.hash=`#/cases/${c.id}/${view}`;const html=state.casePage();assert.ok(!/Invalid Date|>undefined<|investigation-notes.txt|evidence-register.csv/.test(html),view);
   if(view==='overview')assert.ok(html.includes('部分交付'));
   if(view==='comments')assert.ok(html.includes('附件 (0)'));
   if(view==='case-info')assert.ok(html.includes('案件判定尚未设置'));
   if(view==='tasks')assert.ok(html.includes('暂无任务'));
   if(view==='attack')assert.ok(html.includes('源告警记录的对象关联'));
  }
  assert.equal(JSON.stringify(state.store),before);assert.equal(state.M.forCase(state.store,current).length,2);
 }
});
test('creating a Case from the complete design incident retains both design Runs and its incident link after reload',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='262144'),linked=x.incidentCases(inc);x.store.cases=x.store.cases.filter(c=>!linked.includes(c));
 const expected=Array.from(x.M.forAlerts(x.store,x.store.alerts.filter(a=>a.incidentId===inc.id)),r=>r.id);assert.equal(expected.length,2);
 const c=x.associateIncidentCase(inc,{mode:'new',title:'多告警调查'});
 for(const state of [x,load(JSON.stringify(x.store))]){
  const current=state.store.cases.find(row=>row.id===c.id);assert.deepEqual(Array.from(state.M.forCase(state.store,current),r=>r.id),expected);
  const parent=state.store.incidents.find(row=>row.id===inc.id);assert.ok(state.incidentCases(parent).some(row=>row.id===c.id));
  state.s.location.hash=`#/cases/${c.id}/overview`;const html=state.casePage();for(const id of expected)assert.ok(html.includes(id));assert.ok(html.includes('部分交付'));
 }
});
function load(saved=null){
 const handlers={},nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}};
 const s={window:{addEventListener(){}},document:{addEventListener:(type,fn)=>(handlers[type]||=[]).push(fn),querySelector:selector=>nodes[selector]||null},location:{hash:'#/incidents'},localStorage:{getItem:()=>saved,setItem(){}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData:class{constructor(form){return Object.entries(form);}}};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(x=>x[1]);
 for(const f of files){let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,incidentCases,incidentCaseResults,associateIncidentCase,incidentPage,incidentContext,incidentProcessingCount,incidentQueueMetrics,incidentHostNames,drawerMarkup,modalMarkup,investigationView,scopeActivities,alertsPage,casePage,caseQueueRows,tableState,filteredRows,workspaceView};\n})();');vm.runInContext(code,s);}
 return {...s.window.api,s,nodes,click:async (action,id='')=>{for(const fn of handlers.click)await fn({target:{closest:selector=>selector==='[data-action]'?{dataset:{action,id}}:null},preventDefault(){}});},M:s.window.investigationWorkspaceModel,F:s.window.alertFlowWorkspace};
}
test('three saved incident groups append once and preserve original and edited browser records',()=>{
 const x=load();assert.equal(x.store.incidents.length,21);assert.equal(x.store.alerts.length,78);assert.equal(x.store.cases.length,21);
 for(const inc of x.store.incidents.filter(i=>i.recordedIncident&&i.sourceEnvironment==='socai2-21')){
  const members=x.store.alerts.filter(a=>a.incidentId===inc.id);assert.equal(members.length,2);assert.equal(inc.priority,null);assert.equal(inc.status,'New');assert.equal(inc.owner,'未记录');assert.equal(inc.tags.length,0);
  assert.deepEqual([...members.map(a=>a.id)].sort(),[...inc.sourceAlertIds].sort());assert.ok(members.every(a=>a.caseId===null));
 }
 const old=x.store.incidents[0],actual=x.store.incidents.find(i=>i.recordedIncident);old.title='local fixture edit';actual.title='local event edit';actual.owner='Analyst';
 const y=load(JSON.stringify(x.store));assert.equal(y.store.incidents.length,21);assert.equal(y.store.incidents[0].title,old.title);assert.equal(y.store.incidents.find(i=>i.id===actual.id).owner,'Analyst');
 assert.equal(JSON.stringify(y.store.alerts),JSON.stringify(x.store.alerts));
});
test('incident statistics use six source alerts and do not claim disruption or inventory',()=>{
 const x=load(),m=x.F.metrics(x.store);assert.equal(m.alerts,6);assert.equal(m.groups,3);assert.equal(m.reduction,50);
 const html=x.incidentPage();assert.ok(html.includes('6 条流程告警归为 3 个事件'));assert.ok(html.includes('处理中的事件'));assert.ok(!html.includes('攻击中断'));assert.ok(!html.includes('67 条告警聚合'));assert.ok(html.includes('涉及资产'));
 const inc=x.store.incidents.find(i=>i.recordedIncident);x.ui.drawer={type:'incident',id:inc.id};const drawer=x.drawerMarkup();assert.ok(drawer.includes('尚未评分'));assert.ok(!drawer.includes('攻击阶段与关联'));
});
test('processing incident card follows effective handling state independently of investigation delivery',()=>{
 const x=load(),before=JSON.stringify(x.store);
 const expected=x.store.incidents.filter(i=>i.status==='In progress').length;
 assert.equal(x.incidentProcessingCount(),expected);
 const card=x.incidentPage().match(/<article class="queue-metric">[\s\S]*?<\/article>/)[0];
 assert.ok(card.includes('处理中的事件'));assert.ok(card.includes(`<b>${expected}</b>`));assert.ok(card.includes('已开始处理，尚未解决'));
 assert.ok(!card.includes('含部分交付'));assert.equal(JSON.stringify(x.store),before);
 const columns=x.alertsPage();assert.ok(columns.includes('涉及资产'));assert.ok(!columns.includes('受影响资产'));
 x.store.incidents=[
  {id:'fresh',status:'New',owner:'未分配'},
  {id:'assigned',status:'New',owner:'Analyst'},
  {id:'processing',status:'In progress',owner:'Analyst'},
  {id:'resolved',status:'Resolved',owner:'Analyst'},
  {id:'missing'},
  {id:'unknown',status:'unknown',owner:'Analyst'}
 ];
 x.M.runs=()=>{throw new Error('The processing metric must not read investigation Runs');};
 assert.equal(x.incidentProcessingCount(),2);
 x.store.incidents[1].status='Resolved';assert.equal(x.incidentProcessingCount(),1);
 x.store.incidents[0].owner='Analyst';assert.equal(x.incidentProcessingCount(),2);
 x.store.incidents[2].owner='未分配';assert.equal(x.incidentProcessingCount(),2);
});
test('four incident metrics use distinct incidents and a rolling occurrence-time window without changing historical records',()=>{
 const x=load(),now=Date.parse('2026-10-31T12:00:00+08:00');
 assert.deepEqual({...x.incidentQueueMetrics(now)},{active:17,unassigned:5,recent:2,high:15});
 const summary=x.incidentPage().match(/<div class="queue-inline-stats"[\s\S]*?<\/div>/)[0];
 assert.equal((summary.match(/<b>/g)||[]).length,4);assert.ok(summary.includes('24h有新告警'));assert.ok(summary.includes('高严重程度'));assert.ok(!summary.includes('状态未提供'));
 x.store.incidents=[
  {id:'a',status:'New',owner:'未分配',severity:'高'},
  {id:'b',status:'In progress',owner:'Analyst',severity:'中'},
  {id:'future',status:'Not set',owner:'未记录',severity:'高'},
  {id:'old',status:'Resolved',owner:'未分配',severity:'低'},
  {id:'missing'},{id:'legacy'}
 ];
 const iso=time=>new Date(time).toISOString();
 x.store.alerts=[
  {incidentId:'a',event_time:iso(now-86400000)},
  {incidentId:'a',event_time:iso(now-1000)},
  {incidentId:'b',event_time:'2026-10-31T12:00:00+08:00'},
  {incidentId:'future',event_time:iso(now+1)},
  {incidentId:'old',event_time:iso(now-86400001),updated:iso(now)},
  {incidentId:'missing',persistedRecord:true,first:iso(now)},
  {incidentId:'missing',event_time:'invalid',first:iso(now)},
  {incidentId:'legacy',first:iso(now)},
  {incidentId:'unlinked',event_time:iso(now)}
 ];
 const before=JSON.stringify(x.store);assert.deepEqual({...x.incidentQueueMetrics(now)},{active:2,unassigned:2,recent:3,high:2});
 assert.equal(x.incidentQueueMetrics(now+86400001).recent,1); // Only the formerly future alert has now occurred inside the window.
 assert.equal(JSON.stringify(x.store),before);
});
test('incident context uses asset tags and host names, preserves source state and keeps member scores outside the incident summary',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='8db5aafa-011a-47db-9beb-9b16a6f97a1d'),members=x.store.alerts.filter(a=>a.incidentId===inc.id);
 inc.tags=['事件管理标记'];members[0].tags=['告警自身标签'];members[0].hostNames.push('HOST-B','HOST-C','<host>');
 x.store.assets.find(a=>a.id===members[0].entityIds[0]).tags=['文件服务器'];
 const fp=members.find(a=>a.detailMaterial.raw.disposition==='false_positive');fp.disposition='true_positive';
 const before=JSON.stringify(x.store),ctx=x.incidentContext(inc);
 assert.deepEqual([...ctx.tags],['文件服务器']);assert.equal(ctx.hostNames[0],'DEMO-DATA-13');assert.equal(ctx.hostNames.length,4);
 const hosts=x.incidentHostNames(ctx.hostNames);assert.ok(hosts.includes('+2'));assert.ok(hosts.includes('&lt;host&gt;'));assert.ok(!hosts.includes('<host>'));
 x.tableState('incidents').columns=['title','tags','assetCount','status'];x.incidentPage();assert.ok(x.tableState('incidents').columns.includes('hostNames'));
 x.tableState('incidents').tag='文件服务器';const rows=x.store.incidents.map(i=>({...i,tags:x.incidentContext(i).tags}));assert.ok(x.filteredRows('incidents',rows).some(i=>i.id===inc.id));
 x.ui.modal={type:'filter',key:'incidents'};const filter=x.modalMarkup();assert.ok(filter.includes('资产标签'));assert.ok(!filter.includes('事件管理标记'));assert.ok(!filter.includes('状态未提供'));assert.ok(filter.includes('新建'));assert.match(filter,/<option value="In progress"[^>]*>处理中<\/option>/);
 x.ui.drawer={type:'incident',id:inc.id};const html=x.drawerMarkup();assert.ok(html.includes('处理状态：新建'));assert.equal(inc.sourceHandlingStatus,'Not set');assert.ok(html.includes('文件服务器'));assert.ok(!html.includes('事件管理标记'));assert.ok(!html.includes('AiSOC 告警评分'));assert.ok(!html.includes('<b>95</b><span>误报</span>'));assert.ok(html.includes('事件优先级：尚未评分'));assert.ok(html.includes('事件整体研判结论尚未记录'));
 assert.equal(JSON.stringify(x.store),before);
});
test('incident preview summarizes current members and distinct started Runs without inventing a joint verdict',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='85b81836-be47-4ab0-8c1f-6d360c5fb0a2');
 const members=x.store.alerts.filter(a=>a.incidentId===inc.id);x.ui.drawer={type:'incident',id:inc.id};
 const before=JSON.stringify(x.store),actual=x.drawerMarkup();
 assert.ok(actual.includes('本事件关联 2 条告警，涉及主机 DEMO-FIN-11。'));assert.ok(actual.includes('已有 2 次关联调查，其中 2 次部分交付。'));
 assert.ok(actual.includes('线索包括Office启动隐藏PowerShell、脚本进程向文档地址建立HTTPS连接。'));
 assert.ok(!actual.includes('按保存告警的事件标识汇集成员'));
 x.M.forAlerts=()=>[
  {id:'joint',alertIds:members.map(a=>a.id),completion:'partial',verdict:'true_positive'},
  {id:'joint',alertIds:[members[0].id],completion:'partial'},
  {id:'triage',alertIds:[members[0].id],completion:'not_escalated'},
  {id:'complete',alertIds:[members[0].id],completion:'completed',verdict:'benign'}
 ];
 const html=x.drawerMarkup();assert.ok(html.includes('已有 2 次关联调查，其中 1 次部分交付。'));
 assert.ok(!html.includes('真实威胁'));assert.ok(!html.includes('正常行为'));assert.ok(html.includes('事件整体研判结论尚未记录'));
 x.M.forAlerts=()=>[{id:'triage',completion:'not_escalated'}];assert.ok(x.drawerMarkup().includes('暂无已启动的关联调查。'));
 assert.equal(JSON.stringify(x.store),before);
 x.ui.drawer={type:'incident',id:'262144'};const demo=x.drawerMarkup();assert.ok(demo.includes('优先级评估因素'));assert.ok(demo.includes(x.store.incidents.find(i=>i.id==='262144').description));
});
test('all saved incident regions render with source links, honest empty values and no data mutation',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const inc of x.store.incidents.filter(i=>i.recordedIncident))for(const tab of ['summary','alerts','triage','attack','chain','assets','investigations','evidence','activities','similar','context']){
  x.s.location.hash=`#/incidents/${inc.id}/${tab}`;const html=x.incidentPage();assert.ok(html.includes(inc.id));assert.ok(!html.includes('Invalid Date'));assert.ok(!html.includes('>undefined<'));
  if(tab==='attack')assert.ok(html.includes('源告警记录的对象关联'));
  if(tab==='evidence')assert.ok(html.includes('查询与证据'));
  if(tab==='assets')assert.ok(!html.includes('Contoso'));
 }
 assert.equal(JSON.stringify(x.store),before);
});
test('all saved event rows are displayed with their own Run and public payloads',()=>{
 const x=load(),rows=x.M.runs(x.store).filter(r=>x.s.window.alertFlowData.runs.some(source=>source.id===r.id)),kinds={};let count=0;
 for(const r of rows){for(const e of r.steps){count++;kinds[e.kind]=(kinds[e.kind]||0)+1;assert.ok(e.id);assert.ok(!Object.hasOwn(e.payload,'prompt'));}
  x.s.location.hash=`#/investigations/${r.id}/ledger`;const html=x.investigationView.workbench();assert.equal((html.match(/class="iv-step"/g)||[]).length,r.steps.length);
 }
 assert.equal(rows.length,6);assert.equal(count,92);assert.equal(kinds.llm_call,6);assert.equal(kinds.graph_usage,5);
 const a=rows[0];x.s.location.hash=`#/investigations/${a.id}/ledger?kind=llm_call`;assert.ok(x.investigationView.workbench().includes('rationale'));
 const source=JSON.stringify(x.s.window.alertFlowData);for(const key of ['prompt','prompt_block','reasoning_content','messages','api_key','password'])assert.ok(!source.includes('"'+key+'":'));
});
test('artifact bodies retain source identity and cannot leak another Run or execute HTML',()=>{
 const x=load(),rows=x.M.runs(x.store).filter(r=>x.s.window.alertFlowData.runs.some(source=>source.id===r.id));let modes={};
 for(const r of rows){for(const a of r.artifacts){const b=r.artifactBodies[a.id];assert.ok(b);assert.ok(r.steps.some(e=>e.id===a.event_id));modes[b.mode]=(modes[b.mode]||0)+1;}
  x.s.location.hash=`#/investigations/${r.id}/tools`;const html=x.investigationView.workbench();assert.ok(html.includes('原件SHA256'));assert.ok(!html.includes('<!DOCTYPE'));assert.ok(html.includes('提示词正文'));
 }
 assert.deepEqual(modes,{excerpt:40,metadata:6,full:31});
 const a=rows[0],other=rows[1].artifacts.find(k=>k.kind==='report_md');x.s.location.hash=`#/investigations/${a.id}/tools?artifact=${other.id}`;let html=x.investigationView.workbench();assert.ok(html.includes('本次调查中没有该材料'));assert.ok(!html.includes(other.sha256));
 const key=a.artifacts.find(k=>k.kind==='report_md').id;x.s.window.alertFlowData.runs[0].artifactBodies[key].content='<img src=x onerror=alert(1)>';
 html=x.investigationView.workbench();assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img src=x'));
});
test('editing only the incident title keeps the default state and unrecorded owner without changing any alert',async()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),alerts=JSON.stringify(x.store.alerts),cases=JSON.stringify(x.store.cases);
 x.s.location.hash=`#/incidents/${inc.id}/summary`;x.ui.modal={type:'manage-incident',id:inc.id};
 const html=x.modalMarkup(),form={title:inc.title+'（复核）',tags:'',note:''};
 for(const match of html.matchAll(/<select[^>]+name="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)){
  const options=[...match[2].matchAll(/<option value="([^"]*)"([^>]*)>/g)];form[match[1]]=(options.find(o=>o[2].includes('selected'))||options[0])[1];
 }
 assert.equal(form.status,'New');assert.equal(form.owner,'未记录');x.nodes['#manage-incidents-form']=form;
 await x.click('save-incidents');assert.equal(inc.title,form.title);assert.equal(inc.status,'New');assert.equal(inc.owner,'未记录');
 assert.equal(JSON.stringify(x.store.alerts),alerts);assert.equal(JSON.stringify(x.store.cases),cases);assert.equal(x.ui.modal,null);
});
test('reset restores all three real incident groups immediately without a page reload',async()=>{
 const x=load(),id=x.store.incidents.find(i=>i.recordedIncident).id;x.s.location.hash=`#/incidents/${id}/summary`;
 x.store.incidents.find(i=>i.id===id).title='local edit';await x.click('confirm-reset');
 assert.equal(x.store.incidents.length,21);assert.equal(x.store.alerts.length,78);assert.equal(x.store.cases.length,21);
 const actual=x.store.incidents.filter(i=>i.recordedIncident&&i.sourceEnvironment==='socai2-21');assert.equal(actual.length,3);
 for(const inc of actual){assert.equal(x.store.alerts.filter(a=>a.incidentId===inc.id).length,2);assert.equal(inc.status,'New');}
 assert.ok(x.nodes['#app'].innerHTML.includes(id));assert.ok(!x.store.incidents.find(i=>i.id===id).title.includes('local edit'));
});
test('unknown completeness does not erase a recorded joint investigation and triage is not counted',()=>{
 const x=load(),joint=x.s.window.persistedCaseData.runs[0],members=x.store.alerts.filter(a=>joint.alertIds.includes(a.id));assert.equal(joint.completion,null);
 assert.equal(x.M.coverage(x.M.assessments(x.store,members)).investigated,3);
 const triage=x.M.runs(x.store).find(r=>r.sourceEnvironment==='socai2-21'&&r.completion==='not_escalated');assert.equal(x.F.started(triage),false);
});
test('legacy incident chain routes show only member relationships and activities stay in scope',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),members=x.store.alerts.filter(a=>a.incidentId===inc.id),runs=x.M.forAlerts(x.store,members);
 for(const a of members){x.s.location.hash=`#/incidents/${inc.id}/chain?seed=${a.id}`;const html=x.incidentPage();assert.ok(html.includes('事件实体关系图'));assert.ok(!html.includes('Chain种子告警'));for(const r of runs)assert.ok(!html.includes(`investigations/${r.id}/graphs`));}
 x.s.location.hash=`#/incidents/${inc.id}/activities`;const acts=x.scopeActivities();assert.equal(acts.length,2+runs.reduce((n,r)=>n+r.steps.length,0));assert.ok(acts.every(a=>a.incidentId===inc.id&&a.caseIds.length===0&&a.status==='Recorded'));
 x.ui.drawer={type:'activity',id:acts[0].id};assert.ok(x.drawerMarkup().includes('此记录已保存'));
});

test('three local Cases collect original members and Runs without source Case ownership',()=>{
 const x=load(),cs=x.store.cases.filter(c=>c.alertFlowCollection);assert.equal(cs.length,3);
 for(const c of cs){assert.equal(c.sourceCaseId,null);assert.ok(c.localCollection);assert.equal(c.alertIds.length,2);assert.equal(c.sourceRunIds.length,2);assert.equal(c.created,x.s.window.alertFlowData.organizedAt);assert.notEqual(c.created,c.sourceCapturedAt);assert.equal(c.priority,null);assert.equal(c.tasks.length,0);
  for(const r of x.M.forCase(x.store,c)){assert.equal(r.alertIds.length,1);assert.ok(!r.sourceCaseId);assert.ok(c.alertIds.includes(r.alertIds[0]));assert.equal(r.sourceTenantId,c.sourceTenantId);}
  for(const a of x.store.alerts.filter(a=>c.alertIds.includes(a.id)))assert.equal(a.caseId,null);
 }
 const before=JSON.stringify(x.store);x.F.merge(x.store);assert.equal(JSON.stringify(x.store),before);
});
test('all local Case regions and six Run views expose scoped materials and empty collaboration records',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const c of x.store.cases.filter(c=>c.alertFlowCollection)){
  for(const tab of ['overview','case-info','alerts','assets','attack','evidence','tasks','activities','comments','similar','investigations']){
   x.s.location.hash=`#/cases/${c.id}/${tab}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html),tab);assert.ok(!html.includes('iv-source-notice'));assert.ok(!html.includes('本地整理'));
   if(tab==='overview')for(const r of x.M.forCase(x.store,c))assert.ok(html.includes(r.id));
   if(tab==='evidence'){for(const r of x.M.forCase(x.store,c))for(const a of r.artifacts)assert.ok(html.includes(a.sha256));assert.ok(html.includes('原件不自动视为'));assert.ok(!html.includes('本次调查中没有该材料'));}
   if(tab==='attack'){assert.ok(html.includes('6 个对象'));assert.ok(html.includes('8 条来源关系'));assert.ok(!html.includes('MAPS_TO'));}
   if(tab==='comments'){assert.ok(html.includes('附件 (0)'));assert.ok(!html.includes('investigation-notes.txt'));}
   if(tab==='tasks')assert.ok(html.includes('暂无任务'));
  }
  for(const r of x.M.forCase(x.store,c))for(const view of ['overview','process','tools','graphs','ledger','report']){
   x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=${view}`;const html=x.casePage();assert.ok(html.includes(r.id));assert.ok(!/Invalid Date|>undefined<|>null</.test(html));
   if(view==='graphs'&&r.completion==='partial')assert.ok(html.includes('未关联 Case'));
  }
 }
 assert.equal(JSON.stringify(x.store),before);
});
test('member edits affect current relations but retain referenced Run inputs across reload',()=>{
 const x=load(),c=x.store.cases.find(c=>c.alertFlowCollection),runs=x.M.forCase(x.store,c),saved=JSON.stringify(runs),removed=c.alertIds.pop();
 assert.equal(x.M.forCase(x.store,c).length,2);x.s.location.hash=`#/cases/${c.id}/attack`;let html=x.casePage();assert.ok(html.includes('5 个对象'));assert.ok(!html.includes('#/alerts/'+removed+'/overview'));
 c.alertIds=[];x.s.location.hash=`#/cases/${c.id}/overview`;assert.equal((x.casePage().match(/已不在当前成员中/g)||[]).length,2);
 x.s.location.hash=`#/cases/${c.id}/activities`;assert.equal(x.scopeActivities().length,runs.reduce((n,r)=>n+r.steps.length,0));
 const y=load(JSON.stringify(x.store)),copy=y.store.cases.find(row=>row.id===c.id);assert.equal(copy.alertIds.length,0);assert.equal(JSON.stringify(y.M.forCase(y.store,copy)),saved);
});
test('local Case Run references stay within source environment and tenant',()=>{
 const x=load(),c=x.store.cases.find(c=>c.alertFlowCollection),other=x.s.window.aisoc20RecordedData.runs[0];c.alertIds.push(other.alertIds[0]);c.sourceRunIds.push(other.id);assert.equal(x.M.forCase(x.store,c).length,2);
 const id=c.sourceRunIds[0];x.s.window.alertFlowData.runs.find(r=>r.id===id).sourceTenantId='different-tenant';assert.ok(!x.M.forCase(x.store,c).some(r=>r.id===id));
});
test('Case counts and source activities stay scoped without assigning a joint verdict',()=>{
 const x=load(),cs=x.store.cases.filter(c=>c.alertFlowCollection),stats=x.F.caseStats(cs.flatMap(c=>x.M.forCase(x.store,c)));
 assert.equal(stats.events,92);assert.equal(stats.tools,49);assert.equal(stats.artifacts,77);assert.equal(stats.partial,5);assert.equal(stats.triage,1);
 for(const c of cs){const row=x.caseQueueRows().find(r=>r.id===c.id);assert.equal(row.status,'New');assert.equal(row.investigation,'Partial');assert.equal(row.determination,'未设置');
  x.s.location.hash=`#/cases/${c.id}/activities`;const acts=x.scopeActivities();assert.equal(acts.length,2+x.M.forCase(x.store,c).reduce((n,r)=>n+r.steps.length,0));assert.ok(acts.every(a=>a.caseIds.length===1&&a.caseIds[0]===c.id&&a.status==='Recorded'));
  const record=acts.find(a=>a.runId);x.ui.drawer={type:'activity',id:record.id};assert.ok(x.drawerMarkup().includes(`cases/${c.id}/investigations?run=${record.runId}&view=ledger`));
 }
});
test('Case edits persist locally and reset restores collections without changing source records',async()=>{
 const x=load(),c=x.store.cases.find(c=>c.alertFlowCollection),alerts=JSON.stringify(x.store.alerts),runs=JSON.stringify(x.M.runs(x.store));x.s.window.referenceWorkspaces.updateCase(x.store,c,{title:'自定义案件',owner:'Megan Bowen',status:'Resolved'});c.alertIds.pop();
 const y=load(JSON.stringify(x.store)),copy=y.store.cases.find(row=>row.id===c.id);assert.equal(copy.title,'自定义案件');assert.equal(copy.alertIds.length,1);assert.equal(copy.owner,'Megan Bowen');assert.equal(JSON.stringify(y.store.alerts),alerts);assert.equal(JSON.stringify(y.M.runs(y.store)),runs);
 await y.click('confirm-reset');const reset=y.store.cases.find(row=>row.id===c.id);assert.equal(reset.alertIds.length,2);assert.equal(reset.status,'New');assert.equal(y.store.cases.length,21);
});
test('Case recent-date filter includes newly organized collections and keeps explicit custom dates',async()=>{
 const x=load();x.s.location.hash='#/cases';x.ui.modal={type:'date-filter',key:'cases'};assert.ok(x.modalMarkup().includes('2026-10-31'));
 x.nodes['#date-form']={range:'7',start:'',end:''};await x.click('save-dates');assert.equal(x.tableState('cases').end,'2026-10-31T23:59');assert.equal(x.filteredRows('cases',x.caseQueueRows()).filter(c=>c.alertFlowCollection).length,3);
 x.ui.modal={type:'date-filter',key:'cases'};x.nodes['#date-form']={range:'custom',start:'2026-10-25T00:00',end:'2026-10-25T23:59'};await x.click('save-dates');assert.equal(x.tableState('cases').end,'2026-10-25T23:59');assert.equal(x.filteredRows('cases',x.caseQueueRows()).filter(c=>c.alertFlowCollection).length,0);
});

test('incident lifecycle initializes local defaults and retains source state across reload without adopting investigation outcomes',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),others=x.store.incidents.filter(i=>i.recordedIncident);
 for(const i of others){assert.equal(i.status,'New');assert.equal(i.sourceHandlingStatus,'Not set');}
 assert.ok(x.s.window.alertFlowData.incidents.every(i=>i.status==='Not set'));
 const alerts=x.store.alerts.filter(a=>a.incidentId===inc.id);alerts.forEach(a=>a.status='Resolved');
 let y=load(JSON.stringify(x.store));assert.equal(y.store.incidents.find(i=>i.id===inc.id).status,'New');
 inc.owner='Alex Wilber';y=load(JSON.stringify(x.store));assert.equal(y.store.incidents.find(i=>i.id===inc.id).status,'In progress');
 inc.status='Resolved';y=load(JSON.stringify(x.store));assert.equal(y.store.incidents.find(i=>i.id===inc.id).status,'Resolved');
 assert.equal(y.store.incidents.find(i=>i.id===inc.id).sourceHandlingStatus,'Not set');
});
test('assigning an incident starts processing and only manual resolution with a note closes it',async()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),members=x.store.alerts.filter(a=>a.incidentId===inc.id),statuses=members.map(a=>a.status),runs=JSON.stringify(x.M.runs(x.store));
 const form={title:inc.title,tags:'',note:'',status:'New',owner:'Alex Wilber'};
 x.nodes['#manage-incidents-form']=form;x.nodes['#modal-error']={textContent:''};x.s.location.hash=`#/incidents/${inc.id}/summary`;
 x.ui.modal={type:'manage-incident',id:inc.id};await x.click('save-incidents');
 assert.equal(inc.status,'In progress');assert.ok(members.every(a=>a.owner==='Alex Wilber'));assert.deepEqual(members.map(a=>a.status),statuses);assert.ok(x.store.activities.some(a=>a.incidentId===inc.id&&a.title==='分配事件并开始处理'));
 const y=load(JSON.stringify(x.store));assert.equal(y.store.incidents.find(i=>i.id===inc.id).status,'In progress');
 form.status='Resolved';x.ui.modal={type:'manage-incident',id:inc.id};await x.click('save-incidents');assert.equal(inc.status,'In progress');assert.ok(x.nodes['#modal-error'].textContent.includes('解决说明'));
 form.note='已完成核查';await x.click('save-incidents');assert.equal(inc.status,'Resolved');assert.ok(members.every(a=>a.status==='Resolved'));
 form.owner='Megan Bowen';form.note='';x.ui.modal={type:'manage-incident',id:inc.id};await x.click('save-incidents');assert.equal(inc.status,'Resolved');
 assert.equal(JSON.stringify(x.M.runs(x.store)),runs);
});
test('batch assignment handles each incident separately and placeholders never start processing',async()=>{
 const x=load(),[fresh,closed]=x.store.incidents.filter(i=>i.recordedIncident);closed.status='Resolved';
 x.nodes['#manage-incidents-form']={status:'',owner:'Alex Wilber',tags:'',note:''};x.ui.modal={type:'bulk-incidents',ids:[fresh.id,closed.id]};await x.click('save-incidents');
 assert.equal(fresh.status,'In progress');assert.equal(closed.status,'Resolved');
 for(const owner of ['未分配','未记录','']){
  const y=load(),inc=y.store.incidents.find(i=>i.recordedIncident);
  y.nodes['#manage-incidents-form']={title:inc.title,status:'New',owner,tags:'',note:''};y.ui.modal={type:'manage-incident',id:inc.id};await y.click('save-incidents');assert.equal(inc.status,'New');
 }
});

test('saved incident overview sorts actual occurrences, leaves missing times empty and links to one fixed-scope relationship view without mutations',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='85b81836-be47-4ab0-8c1f-6d360c5fb0a2'),members=x.store.alerts.filter(a=>a.incidentId===inc.id);
 x.s.location.hash=`#/incidents/${inc.id}/summary`;
 members[0].event_time='2026-10-24T10:00:00Z';members[1].event_time='2026-10-24T09:00:00Z';
 let html=x.incidentPage(),timeline=html.split('<div class="iv-incident-timeline">')[1].split('</article>')[0];assert.ok(timeline.indexOf(members[0].id)<timeline.indexOf(members[1].id));
 members[0].event_time=null;members[0].persistedRecord=true;members[0].first='2020-01-01T01:01:00Z';const before=JSON.stringify(x.store);
 html=x.incidentPage();timeline=html.split('<div class="iv-incident-timeline">')[1].split('</article>')[0];assert.ok(timeline.includes('未记录'));assert.ok(!timeline.includes('01/01'));assert.ok(!html.includes('攻击故事'));assert.ok(!html.includes('事件实体关系图'));
 x.s.location.hash=`#/incidents/${inc.id}/attack`;html=x.incidentPage();assert.ok(!html.includes('aria-label="关联分析视图"'));assert.ok(html.includes('事件实体关系图'));assert.ok(!html.includes('>关联告警链<'));
 x.s.location.hash=`#/incidents/${inc.id}/chain?seed=${members[1].id}&window=6`;const old=x.incidentPage();
 x.s.location.hash=`#/incidents/${inc.id}/attack?view=chain&seed=${members[1].id}&window=6`;const current=x.incidentPage();
 for(const value of [old,current]){assert.ok(!value.includes('Chain种子告警'));assert.ok(!value.includes('仅此事件'));assert.ok(value.includes('事件实体关系图'));assert.ok(value.includes('aria-selected="true" href="#/incidents/'+inc.id+'/attack"'));}

 assert.equal(JSON.stringify(x.store),before);
});

test('recorded incident graphs preserve every source alert-object edge in the shared workspace',()=>{
 const x=load(),W=x.s.window.referenceWorkspaces,before=JSON.stringify(x.store);
 for(const inc of x.store.incidents.filter(i=>i.recordedIncident)){
  const members=x.store.alerts.filter(a=>a.incidentId===inc.id),expected=x.F.relations(x.store,members);
  for(const grouped of [false,true]){
   const model=W.sourceGraph(x.store,members,{grouped,blast:true,selected:'u1'},inc);
   assert.equal(model.nodes.filter(n=>n.type==='alert').length,members.length);
   assert.equal(model.nodes.filter(n=>n.type!=='alert').flatMap(n=>n.members).length,expected.nodes.filter(n=>n.kind!=='alert').length);
   assert.equal(model.edges.length,expected.edges.length);assert.equal(model.paths.length,0);assert.equal(model.selectedPath,null);
   for(const e of model.edges){const a=members.find(a=>a.id===e.alertIds[0]);assert.ok(a.entityIds.includes(e.to));assert.equal(e.from,'alert:'+a.id);assert.ok(model.nodes.some(n=>n.id===e.target&&n.members.includes(e.to)));assert.ok(model.nodes.some(n=>n.id===e.source));}
  }
  for(const tab of ['attack']){x.s.location.hash=`#/incidents/${inc.id}/${tab}`;const html=x.incidentPage();for(const part of ['workspace-attack','graph-node','图谱布局','相似节点分组','图谱严重程度','重置视角'])assert.ok(html.includes(part),inc.id+':'+part);assert.ok(!html.includes('未找到潜在路径'));}
 }
 assert.equal(JSON.stringify(x.store),before);
});

test('source graph expansion requires known source identities and exact shared objects',()=>{
 const x=load(),W=x.s.window.referenceWorkspaces,inc=x.store.incidents.find(i=>i.recordedIncident),member=x.store.alerts.find(a=>a.incidentId===inc.id),st=structuredClone(x.store);
 const add=(id,fields,alertFields)=>{const a={...member,id:'alert-'+id,incidentId:id,...alertFields};st.alerts.push(a);st.incidents.push({...inc,id,sourceAlertIds:[a.id],...fields});};
 add('same',{},{});add('foreign-env',{sourceEnvironment:'foreign'},{sourceEnvironment:'foreign'});add('foreign-tenant',{sourceTenantId:'foreign'},{sourceTenantId:'foreign'});
 add('missing',{sourceEnvironment:null},{sourceEnvironment:null});add('demo',{recordedIncident:false},{});add('name-only',{}, {entityIds:['different-id']});
 add('legacy-exact',{}, {sourceEnvironment:undefined,sourceTenantId:undefined});
 add('legacy-unknown',{sourceAlertIds:[]},{sourceEnvironment:undefined,sourceTenantId:undefined});
 add('mismatched-alert',{}, {sourceTenantId:'foreign'});
 st.assets.push({id:'different-id',type:'device',name:st.assets.find(a=>a.id===member.entityIds[0]).name});
 const before=JSON.stringify(st),m=W.sourceGraph(st,[member],{associated:true},inc);
 assert.deepEqual(Array.from(m.associated,i=>i.id).sort(),['legacy-exact','same']);assert.equal(m.alerts.length,3);
 assert.equal(W.sourceGraph(st,[member],{associated:true},{...inc,sourceTenantId:null}).alerts.length,1);assert.equal(JSON.stringify(st),before);
});

test('source graph filters and playback retain missing times, isolated alerts and original grouped endpoints',()=>{
 const x=load(),W=x.s.window.referenceWorkspaces;
 const st={incidents:[],assets:[{id:'one',type:'ip',name:'1'},{id:'two',type:'ip',name:'2'}]},base={status:'New',source:'sensor',severity:'高'};
 const members=[{...base,id:'missing',title:'Missing time',first:'2000-01-01',entityIds:[]},{...base,id:'late',title:'Late',event_time:'2026-10-31T02:00:00Z',severity:'中',entityIds:['one','two']},{...base,id:'early',title:'Early',event_time:'2026-10-31T01:00:00Z',entityIds:['one','one','unavailable']}];
 let m=W.sourceGraph(st,members,{index:0,grouped:true});assert.deepEqual(Array.from(m.visible,a=>a.id),['early']);assert.equal(m.edges.length,1);
 m=W.sourceGraph(st,members,{grouped:true});assert.deepEqual(Array.from(m.alerts,a=>a.id),['early','late','missing']);assert.equal(m.nodes.filter(n=>n.type==='alert').length,3);assert.equal(m.edges.length,3);assert.ok(m.nodes.some(n=>n.members.length===2));
 m=W.sourceGraph(st,members,{severity:'中',hidden:new Set(['ip'])});assert.equal(m.nodes.length,1);assert.equal(m.nodes[0].alertId,'late');assert.equal(m.edges.length,0);
 assert.equal(W.sourceGraph(st,members,{status:'Resolved'}).nodes.length,0);assert.equal(W.sourceGraph(st,members,{source:'other'}).alerts.length,0);
});

test('source graph node and edge selections keep source details and timestamps in the shared panel',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident);x.s.location.hash=`#/incidents/${inc.id}/attack`;
 const members=x.store.alerts.filter(a=>a.incidentId===inc.id),a=members[0],W=x.s.window.referenceWorkspaces;
 x.workspaceView.resetScope();x.ui.graph.selected='alert:'+a.id;let html=x.incidentPage();assert.ok(html.includes('查看告警详情'));assert.ok(html.includes('告警时间'));
 const edge=W.sourceGraph(x.store,members,{grouped:true},inc).edges[0];x.ui.graph.edge=edge.id;html=x.incidentPage();assert.ok(html.includes('关系详情'));assert.ok(html.includes('关联依据'));assert.ok(html.includes('源告警记录的对象关联'));assert.ok(html.includes('data-id="'+a.id+'"'));
 x.ui.graph.edge=null;x.ui.graph.selected='group-ip';html=x.incidentPage();assert.ok(html.includes('分组成员'));assert.ok(html.includes('10.78.10.11'));assert.ok(html.includes('198.51.100.41'));
 a.event_time=null;a.first='2099-01-01';x.ui.graph.selected='alert:'+a.id;html=x.incidentPage();assert.ok(html.includes('<h4>告警时间</h4>未记录'));assert.ok(!html.includes('2099'));
});


test('quoted source identifiers remain intact in graph nodes, alert links and edge endpoints',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident);x.s.location.hash=`#/incidents/${inc.id}/attack`;
 const a=x.store.alerts.find(a=>a.incidentId===inc.id),asset=x.store.assets.find(e=>e.id===a.entityIds[0]),old=asset.id;
 asset.id+='"quoted&<';a.id+='"quoted&<';
 for(const row of x.store.alerts)row.entityIds=row.entityIds.map(id=>id===old?asset.id:id);
 const escape=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 x.workspaceView.resetScope();x.ui.graph.alert=a.id;
 const html=x.incidentPage();
 for(const id of [asset.id,a.id,'alert:'+a.id]){assert.ok(html.includes('data-id="'+escape(id)+'"'));assert.ok(!html.includes('data-id="'+id+'"'));}
 const members=x.store.alerts.filter(a=>a.incidentId===inc.id),m=x.s.window.referenceWorkspaces.sourceGraph(x.store,members,{},inc);
 const e=m.edges.find(e=>e.to===asset.id&&e.alertIds.includes(a.id));assert.ok(e);assert.equal(e.from,'alert:'+a.id);
 x.ui.graph.alert=null;x.ui.graph.edge=e.id;const detail=x.incidentPage();assert.ok(detail.includes('data-id="'+escape(a.id)+'"'));assert.ok(detail.includes('data-id="'+escape(asset.id)+'"'));
});

test('all incident graphs reject stale expansion and path state while Case controls remain available',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const inc of x.store.incidents){
  const members=x.store.alerts.filter(a=>a.incidentId===inc.id),memberIds=new Set(members.map(a=>a.id));
  x.s.location.hash=`#/incidents/${inc.id}/summary`;assert.ok(!x.incidentPage().includes('workspace-attack'));
  for(const tab of ['attack','chain?window=168','attack?view=chain']){
   x.s.location.hash=`#/incidents/${inc.id}/${tab}`;Object.assign(x.ui.graph,{associated:true,blast:true,path:'potential-u1-c1',selected:'u1',severity:'',index:99,hidden:new Set()});
   const html=x.incidentPage();assert.equal((html.match(/class="graph-svg"/g)||[]).length,members.length?1:0);
   for(const forbidden of ['data-ws-scope','所有关联事件','ws-blast','ws-path','潜在影响','┄ 潜在路径','Chain种子告警','关联分析视图'])assert.ok(!html.includes(forbidden),inc.id+':'+forbidden);
   assert.ok(!html.includes('仅此事件'));assert.ok(html.includes('aria-label="图谱数据来源"'));assert.equal(x.ui.graph.associated,false);assert.equal(x.ui.graph.blast,false);
   for(const match of html.matchAll(/data-action="ws-alert" data-id="([^"]+)"/g))assert.ok(memberIds.has(match[1]),match[1]);
  }
 }
 x.s.location.hash='#/cases/17420/attack';x.workspaceView.resetScope();x.ui.graph.selected='u1';const html=x.casePage();assert.ok(html.includes('data-ws-scope'));assert.ok(html.includes('ws-blast'));
 assert.equal(JSON.stringify(x.store),before);
});

test('an incident without a Case opens new-case mode and creates all members only on explicit confirmation',async()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),linked=x.incidentCases(inc);x.store.cases=x.store.cases.filter(c=>!linked.includes(c));x.s.location.hash=`#/incidents/${inc.id}/alerts`;
 const count=x.store.cases.length,alerts=JSON.stringify(x.store.alerts),runs=JSON.stringify(x.M.runs(x.store)),status=inc.status,others=JSON.stringify(x.store.cases);
 await x.click('incident-case',inc.id);assert.equal(x.ui.modal.mode,'new');assert.equal(x.store.cases.length,count);
 let html=x.modalMarkup();assert.ok(html.includes('新 Case 名称'));assert.ok(html.includes('value="'+inc.title+'"'));assert.ok(html.includes('创建并进入 Case'));assert.ok(!html.includes('搜索 Case'));
 await x.click('incident-case-mode','existing');assert.ok(x.modalMarkup().includes('搜索 Case'));await x.click('close-modal');assert.equal(x.store.cases.length,count);
 await x.click('incident-case',inc.id);x.nodes['#incident-case-title']={value:inc.title};await x.click('save-incident-case');
 const c=x.store.cases.find(c=>c.incidentCreated&&c.incidentId===inc.id);assert.ok(c);assert.equal(x.store.cases.length,count+1);assert.equal(c.title,inc.title);
 assert.deepEqual(Array.from(c.alertIds).sort(),Array.from(x.store.alerts.filter(a=>a.incidentId===inc.id),a=>a.id).sort());assert.equal(x.s.location.hash,'#/cases/'+c.id+'/overview');
 assert.equal(JSON.stringify(x.store.cases.filter(row=>row.id!==c.id)),others);assert.equal(JSON.stringify(x.store.alerts),alerts);assert.equal(JSON.stringify(x.M.runs(x.store)),runs);assert.equal(inc.status,status);
 const y=load(JSON.stringify(x.store));y.s.location.hash=`#/incidents/${inc.id}/alerts`;html=y.incidentPage();assert.ok(html.includes('进入 Case')||html.includes('选择 Case'));assert.ok(y.incidentCases(y.store.incidents.find(i=>i.id===inc.id)).some(row=>row.id===c.id));assert.ok(!html.includes('>新建 Case<'));
});
