const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(){
 const local=new Map(),listeners={},nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}},dialogs={};let saves=0;
 class FormData{constructor(f){this.values=f.values||f;}get(k){return this.values[k]??null;}getAll(k){const v=this.get(k);return v==null?[]:Array.isArray(v)?v:[v];}*[Symbol.iterator](){yield*Object.entries(this.values);}}
 const s={window:{addEventListener(){}},document:{addEventListener:(k,f)=>(listeners[k]||=[]).push(f),querySelector:k=>nodes[k]||null,getElementById:id=>dialogs[id]||null},location:{hash:'#/alerts'},localStorage:{getItem:k=>local.get(k)||null,setItem(k,v){local.set(k,v);saves++;}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData};vm.createContext(s);
 for(const [,f] of fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)/g)){
  let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,render,fullAlert,casePage,incidentPage,modalMarkup,caseWorkflow,investigationView,caseQueue,caseQueueRows,filteredRows,tableState,caseMetricDefinitions,associateIncidentCase,incidentCaseCandidates,caseAssistant};\n})();');vm.runInContext(code,s);
 }
 const x={...s.window.api,s,nodes,dialogs,local,M:s.window.investigationWorkspaceModel,saves:()=>saves};
 x.dispatch=async(k,target,extra={})=>{for(const f of listeners[k]||[])await f({target,preventDefault(){},...extra});};
 x.click=async(action,id)=>x.dispatch('click',{closest:sel=>sel==='[data-action]'?{dataset:{action,id}}:null});
 x.prepare=async a=>{s.location.hash=`#/alerts/${a.id}/overview`;x.fullAlert(a);dialogs['case-dialog-'+a.id]={open:false,showModal(){this.open=true;}};await x.dispatch('click',{closest:sel=>sel==='[data-detail-investigate]'?{dataset:{detailInvestigate:a.id}}:null});};
 x.form=(a,values)=>{const form={dataset:{detailForm:'case',alert:a.id},values,elements:{caseMode:{},title:{}},querySelector:()=>({})};form.closest=sel=>sel==='[data-detail-form]'||sel==='[data-detail-form="case"]'?form:null;return form;};
 x.select=async(form,id)=>x.dispatch('change',{name:'caseId',value:id,dataset:{},hasAttribute:()=>false,closest:sel=>sel==='[data-detail-form="case"]'?form:null});
 return x;
}
test('all six outcome alerts and three incidents render every shared page',()=>{
 const x=load();
 for(const a of x.store.alerts.filter(a=>a.fixtureSet==='case-outcomes-20261102'))for(const tab of ['overview','timeline','raw','response']){
  x.s.location.hash=`#/alerts/${a.id}/${tab}`;const html=x.fullAlert(a);assert.ok(html.includes(a.title));assert.ok(!/Invalid Date|undefined|>null</.test(html),a.id+'/'+tab);
 }
 for(const i of x.store.incidents.filter(i=>i.fixtureSet==='case-outcomes-20261102'))for(const tab of ['summary','attack','alerts','assets','activities']){
  x.s.location.hash=`#/incidents/${i.id}/${tab}`;assert.ok(!/Invalid Date|>undefined<|>null</.test(x.incidentPage()),i.id+'/'+tab);
 }
 const active=x.M.runs(x.store).find(r=>r.id==='outcome-run-06');assert.equal(active.report,null);assert.equal(x.M.runOutcome(active).hasConclusion,false);
});
test('partial material shapes are normalized without inventing scores, recommendations or conclusions',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='explore-alert-01');assert.ok(a);x.s.location.hash=`#/alerts/${a.id}/overview`;
 x.fullAlert(a);assert.equal(a.detailMaterial.confidence.score,null);assert.equal(a.detailMaterial.responseRecommendations.length,0);assert.ok(a.detailMaterial.explanation.summary);
});
test('ordinary alert association enforces scope and marks baseline update without changing history',async()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='outcome-alert-4'),c=x.store.cases.find(c=>c.id==='outcome-case-01');x.s.location.hash=`#/alerts/${a.id}/overview`;x.fullAlert(a);
 x.dialogs['case-dialog-'+a.id]={showModal(){}};await x.dispatch('click',{closest:sel=>sel==='[data-case-open]'?{dataset:{caseOpen:a.id}}:null});
 const f=x.form(a,{caseMode:'existing'}),foreign=x.store.cases.find(c=>!x.caseWorkflow.eligible(c,a)),before=JSON.stringify(x.store);await x.select(f,foreign.id);await x.dispatch('submit',f);assert.equal(JSON.stringify(x.store),before);
 const runs=JSON.stringify(x.M.runs(x.store));await x.select(f,c.id);await x.dispatch('submit',f);assert.ok(c.alertIds.includes(a.id));assert.deepEqual([...c.baselineUpdate.alertIds],[a.id]);assert.equal(JSON.stringify(x.M.runs(x.store)),runs);assert.equal(x.saves(),1);
});
test('incident creation validates all member scopes before creating a Case',()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='showcase-incident-02'),a=x.store.alerts.find(a=>a.incidentId===inc.id);a.sourceTenantId='foreign';const before=JSON.stringify(x.store);
 assert.throws(()=>x.associateIncidentCase(inc,{mode:'new',title:'must not remain'}),/数据范围/);assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves(),0);
 a.sourceTenantId=inc.sourceTenantId;const c=x.associateIncidentCase(inc,{mode:'new',title:'valid event Case'});assert.ok(c.alertIds.length);assert.equal(c.baselineUpdate.alertIds.length,c.alertIds.length);assert.equal(x.saves(),1);
});
test('move updates both scopes, retains historical inputs and rejects foreign targets atomically',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='outcome-case-01'),target=x.store.cases.find(c=>c.id==='outcome-case-02'),ids=[c.alertIds[0]],before=JSON.stringify(x.store),foreign=x.store.cases.find(t=>!x.caseWorkflow.eligible(t,x.store.alerts.find(a=>a.id===ids[0])));
 assert.throws(()=>x.caseWorkflow.moveMembers(c,foreign,ids),/同一数据范围/);assert.equal(JSON.stringify(x.store),before);
 const runs=JSON.stringify(x.M.runs(x.store)),sourceIds=x.M.forCase(x.store,c).map(r=>r.id);x.caseWorkflow.moveMembers(c,target,ids);
 assert.ok(!c.alertIds.includes(ids[0]));assert.ok(target.alertIds.includes(ids[0]));assert.deepEqual([...x.M.pendingScope(c).removed],ids);assert.deepEqual([...x.M.pendingScope(target).added],ids);assert.equal(JSON.stringify(x.M.runs(x.store)),runs);assert.deepEqual([...x.M.forCase(x.store,c).map(r=>r.id)].sort(),[...sourceIds].sort());assert.equal(x.saves(),1);
});
function assistant(x,answer){
 x.c=x.store.cases.find(c=>c.id==='outcome-case-01');x.renders=[];
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
 const common={store:x.store,ui:x.ui,esc,I:()=>'',btn:(t,a,id)=>`<button data-action="${a}" data-id="${esc(id)}">${t}</button>`,badge:esc,date:v=>String(v||'—'),severity:esc,currentCase:()=>x.c,currentRoute:()=>({page:'cases',id:x.c.id,tab:'story'}),getAlert:id=>x.store.alerts.find(a=>a.id===id),getAsset:id=>x.store.assets.find(a=>a.id===id),render:()=>x.renders.push(x.c.id),toast(){}};
 x.A=x.s.window.createCaseAssistant({...common,workflow:()=>x.caseWorkflow,answer});x.A.open();return x.A;
}
test('assistant answer is not a Run until explicit save, then freezes a deduplicated record',async()=>{
 const x=load(),A=assistant(x),c=x.c,original=JSON.stringify([c.alertIds,c.assessment]),count=x.M.forCase(x.store,c).length;A.send('人工确认了脚本用途，这对案件判断有什么影响？');assert.ok(A.panel().includes('正在读取材料'));await A.session().pending;
 const answer=A.session().messages.at(-1);assert.equal(answer.status,'completed');assert.ok(A.panel().includes('ca-message-system'));assert.ok(A.panel().includes('保存到调查记录'));assert.equal(x.M.forCase(x.store,c).length,count);assert.ok(A.panel().includes('aria-label="建议问题"'));
 const frozen=JSON.stringify(answer.inputSnapshot);x.store.alerts.find(a=>a.id===answer.result.alertIds[0]).title='updated after answer';
 A.handle('ca-save',answer.id);assert.ok(A.panel().includes('ca-save-form'));A.submit({id:'ca-save-form',dataset:{answer:answer.id},values:{title:'已核对的人工反馈影响',conclusion:'人工反馈仅覆盖脚本用途'}});
 const r=x.M.forCase(x.store,c).find(r=>r.id===answer.savedRunId);assert.ok(r);assert.equal(r.outcome.conclusion,'人工反馈仅覆盖脚本用途');assert.equal(JSON.stringify(r.input.alerts),frozen);assert.equal(r.conversation.length,2);assert.equal(r.graphEligible,false);assert.equal(x.M.forCase(x.store,c).length,count+1);assert.equal(JSON.stringify([c.alertIds,c.assessment]),original);
 A.submit({id:'ca-save-form',dataset:{answer:answer.id},values:{title:'repeat',conclusion:'repeat'}});assert.equal(x.M.forCase(x.store,c).length,count+1);assert.ok(A.panel().includes('查看已保存结论'));assert.ok(A.story().includes('人工反馈仅覆盖脚本用途'));
 x.s.location.hash=`#/cases/${c.id}/investigations?run=${encodeURIComponent(r.id)}&view=process`;assert.ok(x.casePage().includes('已保存的对话'));x.s.location.hash=`#/cases/${c.id}/attack`;assert.ok(!x.casePage().includes('沿用当前成员关系'));
});
test('async replies retain request snapshot and Case session across navigation',async()=>{
 const x=load();let resolve;const A=assistant(x,()=>new Promise(r=>resolve=r)),first=x.c,id=first.alertIds[0],a=x.store.alerts.find(a=>a.id===id),title=a.title;
 A.send('核对');const s=A.session(),p=s.pending;await Promise.resolve();a.title='modified';x.c=x.store.cases.find(c=>c.id==='outcome-case-02');A.open();const count=x.renders.length;
 resolve({title:'answer',outcome:{conclusion:'仅核对所选材料',findings:[],impact:'无自动变更'},alertIds:[id],runIds:['outcome-run-01'],taskIds:[]});await p;
 assert.equal(s.messages.at(-1).inputSnapshot[0].title,title);assert.equal(A.session().messages.length,0);assert.equal(x.renders.length,count);x.c=first;assert.equal(A.session().messages.at(-1).status,'completed');
});
test('foreign Run or task references fail before displaying a completed answer',async()=>{
 for(const reference of [{runIds:['INV-20261024-001'],taskIds:[]},{runIds:[],taskIds:['outcome-task-03']}]){
  const x=load(),A=assistant(x,()=>({title:'foreign',outcome:{conclusion:'must not show'},alertIds:['outcome-alert-1'],...reference}));A.send('核对');await A.session().pending;
  assert.equal(A.session().messages.at(-1).status,'failed');assert.ok(!A.panel().includes('must not show'));assert.ok(!A.panel().includes('保存到调查记录'));
 }
});
test('saved AI record preserves the task result at request time and exposes source links',async()=>{
 const x=load();let resolve;const A=assistant(x,()=>new Promise(r=>resolve=r)),task=x.c.tasks.find(t=>t.id==='outcome-task-01'),original=task.result;
 A.send('这个人工结果改变了什么？');const p=A.session().pending;await Promise.resolve();task.result='edited while awaiting answer';
 resolve({title:'人工反馈影响',outcome:{conclusion:'只确认脚本用途',findings:[],impact:'保留其他疑点'},alertIds:['outcome-alert-1'],runIds:['outcome-run-02'],taskIds:[task.id]});await p;const m=A.session().messages.at(-1);
 const r=x.caseWorkflow.saveAssistantResult(x.c,m,A.session().messages,{title:'人工反馈影响',conclusion:'只确认脚本用途'});task.result='edited after save';assert.equal(r.referenceSnapshot.tasks[0].result,original);
 x.s.location.hash=`#/cases/${x.c.id}/investigations?run=${encodeURIComponent(r.id)}&view=process`;const html=x.casePage();assert.ok(html.includes(original));assert.ok(!html.includes('edited after save'));assert.ok(html.includes('查看来源调查'));assert.ok(html.includes('查看人工任务当前记录'));assert.ok(html.includes('确认范围：'));
});
test('complete examples append idempotently and keep edits, unknown outcomes and unfinished-task count',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='outcome-case-01');c.description='user edit';const before=JSON.stringify(x.store);x.s.window.mergeCaseOutcomeData(x.store);assert.equal(JSON.stringify(x.store),before);assert.equal(x.M.pendingTasks(c).length,1);
 const empty=x.M.runOutcome({status:'completed',findings:['Auto-triage: score 95'],outcome:null});assert.equal(empty.hasConclusion,false);assert.equal(empty.findings.length,0);assert.ok(empty.conclusion.includes('未保存结论'));
 assert.equal(x.M.caseAssessment(x.store,c).conclusion,c.assessment.conclusion);x.caseWorkflow.addMembers(c,['outcome-alert-4']);const assessment=x.M.caseAssessment(x.store,c);assert.ok(assessment.unanalysed.includes('outcome-alert-4'));assert.ok(assessment.uncovered.includes('outcome-alert-4'));
});
