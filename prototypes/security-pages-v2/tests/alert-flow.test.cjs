const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(saved=null){
 const handlers={},nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}};
 const s={window:{addEventListener(){}},document:{addEventListener:(type,fn)=>(handlers[type]||=[]).push(fn),querySelector:selector=>nodes[selector]||null},location:{hash:'#/incidents'},localStorage:{getItem:()=>saved,setItem(){}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData:class{constructor(form){return Object.entries(form);}}};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(x=>x[1]);
 for(const f of files){let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,incidentPage,drawerMarkup,modalMarkup,investigationView,scopeActivities,alertsPage,casePage,caseQueueRows,tableState,filteredRows,workspaceView};\n})();');vm.runInContext(code,s);}
 return {...s.window.api,s,nodes,click:async action=>{for(const fn of handlers.click)await fn({target:{closest:selector=>selector==='[data-action]'?{dataset:{action}}:null},preventDefault(){}});},M:s.window.investigationWorkspaceModel,F:s.window.alertFlowWorkspace};
}
test('three saved incident groups append once and preserve original and edited browser records',()=>{
 const x=load();assert.equal(x.store.incidents.length,18);assert.equal(x.store.alerts.length,67);assert.equal(x.store.cases.length,19);
 for(const inc of x.store.incidents.filter(i=>i.recordedIncident&&i.sourceEnvironment==='socai2-21')){
  const members=x.store.alerts.filter(a=>a.incidentId===inc.id);assert.equal(members.length,2);assert.equal(inc.priority,null);assert.equal(inc.status,'Not set');assert.equal(inc.owner,'未记录');assert.equal(inc.tags.length,0);
  assert.deepEqual([...members.map(a=>a.id)].sort(),[...inc.sourceAlertIds].sort());assert.ok(members.every(a=>a.caseId===null));
 }
 const old=x.store.incidents[0],actual=x.store.incidents.find(i=>i.recordedIncident);old.title='local fixture edit';actual.title='local event edit';actual.owner='Analyst';
 const y=load(JSON.stringify(x.store));assert.equal(y.store.incidents.length,18);assert.equal(y.store.incidents[0].title,old.title);assert.equal(y.store.incidents.find(i=>i.id===actual.id).owner,'Analyst');
 assert.equal(JSON.stringify(y.store.alerts),JSON.stringify(x.store.alerts));
});
test('incident statistics use six source alerts and do not claim disruption or inventory',()=>{
 const x=load(),m=x.F.metrics(x.store);assert.equal(m.alerts,6);assert.equal(m.groups,3);assert.equal(m.reduction,50);
 const html=x.incidentPage();assert.ok(html.includes('6 条流程告警归为 3 个事件'));assert.ok(html.includes('尚无可核验的自动中断记录'));assert.ok(!html.includes('67 条告警聚合'));assert.ok(html.includes('涉及对象'));
 const inc=x.store.incidents.find(i=>i.recordedIncident);x.ui.drawer={type:'incident',id:inc.id};const drawer=x.drawerMarkup();assert.ok(drawer.includes('尚未评分'));assert.ok(!drawer.includes('攻击阶段与关联'));
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
test('editing only the incident title preserves unrecorded management fields and every alert',async()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),alerts=JSON.stringify(x.store.alerts),cases=JSON.stringify(x.store.cases);
 x.s.location.hash=`#/incidents/${inc.id}/summary`;x.ui.modal={type:'manage-incident',id:inc.id};
 const html=x.modalMarkup(),form={title:inc.title+'（复核）',tags:'',note:''};
 for(const match of html.matchAll(/<select[^>]+name="([^"]+)"[^>]*>([\s\S]*?)<\/select>/g)){
  const options=[...match[2].matchAll(/<option value="([^"]*)"([^>]*)>/g)];form[match[1]]=(options.find(o=>o[2].includes('selected'))||options[0])[1];
 }
 assert.equal(form.status,'Not set');assert.equal(form.owner,'未记录');x.nodes['#manage-incidents-form']=form;
 await x.click('save-incidents');assert.equal(inc.title,form.title);assert.equal(inc.status,'Not set');assert.equal(inc.owner,'未记录');
 assert.equal(JSON.stringify(x.store.alerts),alerts);assert.equal(JSON.stringify(x.store.cases),cases);assert.equal(x.ui.modal,null);
});
test('reset restores all three real incident groups immediately without a page reload',async()=>{
 const x=load(),id=x.store.incidents.find(i=>i.recordedIncident).id;x.s.location.hash=`#/incidents/${id}/summary`;
 x.store.incidents.find(i=>i.id===id).title='local edit';await x.click('confirm-reset');
 assert.equal(x.store.incidents.length,18);assert.equal(x.store.alerts.length,67);assert.equal(x.store.cases.length,19);
 const actual=x.store.incidents.filter(i=>i.recordedIncident&&i.sourceEnvironment==='socai2-21');assert.equal(actual.length,3);
 for(const inc of actual){assert.equal(x.store.alerts.filter(a=>a.incidentId===inc.id).length,2);assert.equal(inc.status,'Not set');}
 assert.ok(x.nodes['#app'].innerHTML.includes(id));assert.ok(!x.store.incidents.find(i=>i.id===id).title.includes('local edit'));
});
test('unknown completeness does not erase a recorded joint investigation and triage is not counted',()=>{
 const x=load(),joint=x.s.window.persistedCaseData.runs[0],members=x.store.alerts.filter(a=>joint.alertIds.includes(a.id));assert.equal(joint.completion,null);
 assert.equal(x.M.coverage(x.M.assessments(x.store,members)).investigated,3);
 const triage=x.M.runs(x.store).find(r=>r.sourceEnvironment==='socai2-21'&&r.completion==='not_escalated');assert.equal(x.F.started(triage),false);
});
test('saved incident chains follow the selected seed and activities stay in the member scope',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.recordedIncident),members=x.store.alerts.filter(a=>a.incidentId===inc.id),runs=x.M.forAlerts(x.store,members);
 for(const a of members){x.s.location.hash=`#/incidents/${inc.id}/chain?seed=${a.id}`;const html=x.incidentPage();const selected=runs.find(r=>r.alertIds.includes(a.id));assert.ok(html.includes(selected.id));for(const r of runs.filter(r=>r.id!==selected.id))assert.ok(!html.includes(`investigations/${r.id}/graphs`));}
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
   x.s.location.hash=`#/cases/${c.id}/${tab}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html),tab);assert.ok(html.includes('本地整理 Case'));
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
 await y.click('confirm-reset');const reset=y.store.cases.find(row=>row.id===c.id);assert.equal(reset.alertIds.length,2);assert.equal(reset.status,'New');assert.equal(y.store.cases.length,19);
});
test('Case recent-date filter includes newly organized collections and keeps explicit custom dates',async()=>{
 const x=load();x.s.location.hash='#/cases';x.ui.modal={type:'date-filter',key:'cases'};assert.ok(x.modalMarkup().includes('2026-10-29'));
 x.nodes['#date-form']={range:'7',start:'',end:''};await x.click('save-dates');assert.equal(x.tableState('cases').end,'2026-10-29T23:59');assert.equal(x.filteredRows('cases',x.caseQueueRows()).filter(c=>c.alertFlowCollection).length,3);
 x.ui.modal={type:'date-filter',key:'cases'};x.nodes['#date-form']={range:'custom',start:'2026-10-25T00:00',end:'2026-10-25T23:59'};await x.click('save-dates');assert.equal(x.tableState('cases').end,'2026-10-25T23:59');assert.equal(x.filteredRows('cases',x.caseQueueRows()).filter(c=>c.alertFlowCollection).length,0);
});
