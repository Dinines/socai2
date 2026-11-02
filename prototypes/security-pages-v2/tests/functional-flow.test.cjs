const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(){
 const listeners={},nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}},dialogs={};let saves=0;
 class FormData{constructor(f){this.values=f.values||f;}get(k){return this.values[k]??null;}getAll(k){const v=this.get(k);return v==null?[]:Array.isArray(v)?v:[v];}*[Symbol.iterator](){yield*Object.entries(this.values);}}
 const s={window:{addEventListener(){}},document:{addEventListener:(k,f)=>(listeners[k]||=[]).push(f),querySelector:k=>nodes[k]||null,getElementById:id=>dialogs[id]||null},location:{hash:'#/alerts'},localStorage:{getItem:()=>null,setItem(){saves++;}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData};vm.createContext(s);
 for(const [,f] of fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)/g)){
  let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,render,fullAlert,casePage,incidentPage,modalMarkup,caseWorkflow,investigationView,caseQueue,caseQueueRows,filteredRows,tableState,caseMetricDefinitions};\n})();');vm.runInContext(code,s);
 }
 const x={...s.window.api,s,nodes,dialogs,M:s.window.investigationWorkspaceModel,saves:()=>saves};
 x.dispatch=async(k,target,extra={})=>{for(const f of listeners[k]||[])await f({target,preventDefault(){},...extra});};
 x.click=async(action,id)=>x.dispatch('click',{closest:sel=>sel==='[data-action]'?{dataset:{action,id}}:null});
 x.prepare=async a=>{s.location.hash=`#/alerts/${a.id}/overview`;x.fullAlert(a);dialogs['case-dialog-'+a.id]={open:false,showModal(){this.open=true;}};await x.dispatch('click',{closest:sel=>sel==='[data-detail-investigate]'?{dataset:{detailInvestigate:a.id}}:null});};
 x.form=(a,values)=>{const form={dataset:{detailForm:'case',alert:a.id},values,elements:{caseMode:{},title:{}},querySelector:()=>({})};form.closest=sel=>sel==='[data-detail-form]'||sel==='[data-detail-form="case"]'?form:null;return form;};
 x.select=async(form,id)=>x.dispatch('change',{name:'caseId',value:id,dataset:{},hasAttribute:()=>false,closest:sel=>sel==='[data-detail-form="case"]'?form:null});
 return x;
}
test('single linked alert opens scoped Case assistant without creating manual work or a Run',async()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='showcase-alert-01-1'),c=x.store.cases.find(c=>c.alertIds.includes(a.id)),before=JSON.stringify(x.store);
 await x.prepare(a);assert.equal(x.s.location.hash,`#/cases/${c.id}/overview`);x.render();
 assert.ok(x.nodes['#app'].innerHTML.includes('案件 AI 助手'));assert.ok(x.nodes['#app'].innerHTML.includes(a.title));assert.ok(!x.nodes['#app'].innerHTML.includes('cw-plan-form'));
 await x.click('ca-close','');assert.ok(!x.nodes['#app'].innerHTML.includes('案件 AI 助手'));assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves(),0);
 assert.ok(!x.fullAlert(a).includes('value="investigate"'));assert.ok(x.fullAlert(a).includes('type="button" data-detail-investigate'));
});
test('multiple linked Cases require explicit selection and a linked choice writes nothing',async()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='showcase-alert-01-1'),c=x.store.cases.find(c=>c.alertIds.includes(a.id));
 const other={...structuredClone(c),id:'qa-second-case',title:'第二个案件'};x.store.cases.push(other);const before=JSON.stringify(x.store);
 await x.prepare(a);assert.equal(x.s.location.hash,`#/alerts/${a.id}/overview`);assert.ok(x.dialogs['case-dialog-'+a.id].open);
 assert.ok(!/name="caseId"[^>]*checked/.test(x.nodes['#app'].innerHTML));
 const f=x.form(a,{caseMode:'existing'});await x.select(f,other.id);await x.dispatch('submit',f);x.render();
 assert.equal(x.s.location.hash,`#/cases/${other.id}/overview`);assert.ok(x.nodes['#app'].innerHTML.includes('案件 AI 助手'));assert.ok(!x.nodes['#app'].innerHTML.includes('cw-plan-form'));assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves(),0);
});
test('unlinked alert association opens the scoped assistant and preserves existing Run history',async()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='showcase-alert-02-1'),runs=JSON.stringify(x.M.runs(x.store)),original=JSON.stringify(x.store);
 assert.ok(!x.store.cases.some(c=>c.alertIds.includes(a.id)));await x.prepare(a);assert.equal(JSON.stringify(x.store),original);assert.equal(x.saves(),0);
 const f=x.form(a,{caseMode:'new',title:'核实当前告警'});await x.dispatch('submit',f);x.render();
 const c=x.store.cases.find(c=>c.title==='核实当前告警');assert.ok(c);assert.ok(x.caseWorkflow.eligible(c,a));assert.equal(c.investigationDrafts,undefined);assert.equal(x.saves(),1);
 assert.equal(JSON.stringify(x.M.runs(x.store)),runs);assert.ok(!a.detailMaterial.history.some(h=>h.title==='告警启动调查'&&h.description.includes(c.id)));
 assert.ok(x.nodes['#app'].innerHTML.includes('案件 AI 助手'));assert.ok(!x.nodes['#app'].innerHTML.includes('cw-plan-form'));
});
test('preparation rejects cross-source choices and explicitly linking a same-source Case only adds membership',async()=>{
 const x=load(),a=x.store.alerts.find(a=>a.id==='showcase-alert-02-1');await x.prepare(a);
 const f=x.form(a,{caseMode:'existing'}),foreign=x.store.cases.find(c=>!x.caseWorkflow.eligible(c,a)),before=JSON.stringify(x.store);
 await x.select(f,foreign.id);await x.dispatch('submit',f);assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves(),0);
 const c=x.store.cases.find(c=>x.caseWorkflow.eligible(c,a)),runs=JSON.stringify(x.M.runs(x.store));await x.select(f,c.id);await x.dispatch('submit',f);x.render();
 assert.ok(c.alertIds.includes(a.id));assert.ok(x.nodes['#app'].innerHTML.includes('案件 AI 助手'));assert.ok(!x.nodes['#app'].innerHTML.includes('cw-plan-form'));assert.equal(c.investigationDrafts,undefined);assert.equal(JSON.stringify(x.M.runs(x.store)),runs);
});
test('incident edits no longer change security classification, including legacy or injected form values',async()=>{
 const x=load(),inc=x.store.incidents.find(i=>i.id==='showcase-incident-01');inc.classification='False positive';x.s.location.hash=`#/incidents/${inc.id}/summary`;x.ui.modal={type:'manage-incident',id:inc.id};
 assert.ok(!x.modalMarkup().includes('name="classification"'));assert.ok(!x.incidentPage().split('<div class="tabs"')[0].includes('误报'));
 x.nodes['#manage-incidents-form']={title:inc.title,severity:inc.severity,status:inc.status,owner:inc.owner,classification:'True positive',tags:'audit',note:''};await x.click('save-incidents','');assert.equal(inc.classification,'False positive');assert.equal(inc.tags[0],'audit');
 x.ui.modal={type:'bulk-incidents',ids:[inc.id]};assert.ok(!x.modalMarkup().includes('name="classification"'));
});
test('response cards preserve suggestion indexes, approval decisions and unmatched execution without double rendering',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='17420');x.s.location.hash='#/cases/17420/investigations?run=INV-20261024-001&view=report';
 const source=x.s.window.designInvestigationRuns.find(r=>r.id==='INV-20261024-001');
 source.report='原报告';source.actions=[{id:'a1',description:'需审批动作',target:'host',requires_approval:true,rationale:'待核对影响'},{description:'缺目标动作',requires_approval:true},'人工核实', {id:'a4',description:'免审批建议'}];
 source.executed=[{action_id:'a1',description:'对应动作的实际记录',status:'failed'},{description:'只有执行记录，没有建议ID'}];
 const r=x.M.forCase(x.store,c).find(r=>r.id===source.id),before=JSON.stringify(x.M.runs(x.store));let html=x.casePage();
 for(const label of ['需审批动作','缺目标动作','人工核实','免审批建议','对应动作的实际记录','只有执行记录，没有建议ID'])assert.ok(html.includes(label),label);
 assert.equal((html.match(/>需审批动作<\/h4>/g)||[]).length,1);assert.equal((html.match(/data-action="cw-review"/g)||[]).length,1);assert.ok(html.includes('本轮其他执行记录'));
 x.caseWorkflow.decide(c,r.id,0,'approved','核对完成，等待执行');html=x.casePage();assert.ok(html.includes('已批准 · 待执行'));assert.ok(html.includes('核对完成，等待执行'));assert.ok(html.includes('status'));
 assert.equal(JSON.stringify(x.M.runs(x.store)),before);assert.ok(!html.includes('<h3>响应审阅</h3>'));assert.ok(!html.includes('<h3>建议与执行</h3>'));
});
test('history remains complete and old execution links survive primary navigation reduction',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='17420'),runs=x.M.forCase(x.store,c),before=JSON.stringify(x.store);
 x.s.location.hash='#/cases/17420/overview';const home=x.casePage();assert.ok(home.includes('查看全部调查历史'));assert.ok(!home.includes('iv-case-history-row'));
 x.s.location.hash='#/cases/17420/investigations';for(const r of runs)assert.ok(x.casePage().includes(`run=${r.id}`));
 for(const r of runs){x.s.location.hash=`#/cases/17420/investigations?run=${r.id}&view=ledger`;const html=x.casePage();assert.ok(html.includes('<h3>执行明细</h3>'));assert.ok(html.includes('返回 AI 分析'));const nav=html.split('aria-label="调查运行内容">')[1].split('</nav>')[0];assert.equal((nav.match(/<a /g)||[]).length,5);assert.ok(!nav.includes('view=ledger'));if(r.depth?.strategy_id)assert.ok(html.includes(r.depth.strategy_id));}
 assert.equal(JSON.stringify(x.store),before);
});

test('every Case and Run uses the same current routes, graph and source-material components without mutating inputs',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);assert.equal(x.store.cases.length,25);assert.equal(x.M.runs(x.store).length,27);
 for(const c of x.store.cases){
  for(const tab of ['case-info','overview','investigations','alerts','attack','evidence','tasks','activities','comments','similar']){
   x.s.location.hash=`#/cases/${c.id}/${tab}`;const html=x.casePage();assert.equal((html.match(/class="case-nav-button /g)||[]).length,10,c.id+'/'+tab);
   assert.ok(!/Invalid Date|>undefined<|>null</.test(html),c.id+'/'+tab);
   if(tab==='attack'){assert.ok(html.includes('data-investigation-graph'),c.id);assert.ok(!html.includes('reference-graph'));}
   if(tab==='case-info')assert.ok(html.includes('案件资料摘要'),c.id);
  }
 }
 for(const r of x.M.runs(x.store))for(const view of ['overview','process','tools','graphs','ledger','report']){
  x.s.location.hash=`#/investigations/${r.id}/${view}`;const html=x.investigationView.workbench();assert.ok(html.includes('iv-run-selector'),r.id+'/'+view);assert.ok(!/Invalid Date|>undefined<|>null</.test(html),r.id+'/'+view);
  if(view==='graphs'){assert.ok(html.includes(`data-run-id="${r.id}"`));for(const name of ['攻击链 · Attack Chain','攻击路径 · Attack Path','关联范围 · Alert Graph'])assert.ok(html.includes(name),r.id+'/'+name);}
 }
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);assert.equal(x.saves(),0);
});
test('missing Run fields and newly created Cases use the same readers and empty states regardless of source flags',()=>{
 const x=load(),c={...structuredClone(x.store.cases[0]),id:'empty-case',alertIds:[],sourceEnvironment:'empty-source',sourceTenantId:'tenant-a',tasks:[]};x.store.cases.push(c);
 const raw={id:'sparse-run',caseId:c.id,sourceEnvironment:c.sourceEnvironment,sourceTenantId:c.sourceTenantId,status:'completed',completion:'partial',findings:'仅保存一条说明',graphs:null};x.store.caseDemoRuns.push(raw);
 const before=JSON.stringify(raw),r=x.M.forCase(x.store,c)[0];assert.deepEqual([...r.findings],['仅保存一条说明']);for(const k of ['alertIds','tools','actions','artifacts','executed','steps'])assert.equal(r[k].length,0);
 for(const view of ['overview','process','tools','graphs','ledger','report']){x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=${view}`;const html=x.casePage();raw.recorded=!raw.recorded;c.localCollection=!c.localCollection;c.recordedCase=!c.recordedCase;assert.equal(x.casePage(),html,view);assert.ok(!/Invalid Date|>undefined<|>null</.test(html),view);}
 delete raw.recorded;assert.equal(JSON.stringify(raw),before);
 c.alertIds=[x.store.alerts[0].id];c.sourceRunIds=['INV-20261024-001'];assert.deepEqual([...x.M.forCase(x.store,c).map(r=>r.id)],['sparse-run']);
 x.s.location.hash=`#/cases/${c.id}/comments`;assert.ok(x.casePage().includes('附件 (0)'));assert.ok(!x.casePage().includes('investigation-notes.txt'));
});
test('graph context rejects conflicting alert and asset sources and never treats missing source as a wildcard',()=>{
 const x=load(),r=x.M.normalizeRun({id:'isolated-run',alertIds:['scope-alert'],sourceEnvironment:'env',sourceTenantId:'tenant-a'});
 const a={id:'scope-alert',title:'foreign title',entityIds:['scope-asset'],sourceEnvironment:'env',sourceTenantId:'tenant-b'},asset={id:'scope-asset',type:'device',name:'foreign host',sourceEnvironment:'env',sourceTenantId:'tenant-b'};
 x.store.alerts.push(a);x.store.assets.push(asset);
 let context=x.M.graphContext(x.store,r);assert.equal(context.nodes.length,0);assert.equal(context.edges.length,0);let graph=x.s.window.investigationGraphModel.build(r,x.store,context);assert.ok(!graph.nodes.some(n=>['foreign title','foreign host'].includes(n.label)));assert.equal(graph.edges.length,0);
 a.sourceTenantId='tenant-a';context=x.M.graphContext(x.store,r);assert.equal(context.nodes.length,1);assert.equal(context.edges.length,0);
 delete a.sourceEnvironment;delete a.sourceTenantId;context=x.M.graphContext(x.store,r);assert.equal(context.nodes.length,0);graph=x.s.window.investigationGraphModel.build(r,x.store,context);assert.ok(!graph.nodes.some(n=>n.label==='foreign title'));
 const known=x.s.window.alertFlowData.incidents[0],knownAlert=x.store.alerts.find(a=>a.id===known.sourceAlertIds[0]);const saved=x.M.normalizeRun({id:'missing-graph-run',alertIds:[knownAlert.id],sourceEnvironment:known.sourceEnvironment,sourceTenantId:known.sourceTenantId});
 assert.ok(x.M.graphContext(x.store,saved).nodes.some(n=>n.id===knownAlert.id));
});

test('sparse Path arrays and explicit approval-free actions retain their meanings in the common renderer',()=>{
 const x=load(),r=x.s.window.pageShowcaseData.runs.find(r=>r.id==='showcase-run-02');r.actions=[{description:'明确不要求审批',requires_approval:false},{description:'未说明要求'}];r.graphs={attack_path:{status:'success',data:{nodes:[]}}};const before=JSON.stringify(r);
 x.s.location.hash=`#/investigations/${r.id}/graphs`;let html=x.investigationView.workbench();assert.ok(html.includes('0 个对象 · 0 条已记录关系'));
 r.graphs.attack_path.data.nodes=[{id:'case-node',label:'Case'}];x.investigationView.workbench();r.graphs.attack_path.data.nodes=[];
 x.s.location.hash=`#/investigations/${r.id}/report`;html=x.investigationView.workbench();assert.ok(html.includes('无需审批'));assert.ok(html.includes('未记录审批要求'));assert.equal(JSON.stringify(r),before);
});


test('Case queue counts actionable Cases consistently, deduplicates follow-up and excludes resolved or unknown status',()=>{
 const x=load(),count=rows=>Object.fromEntries(x.caseMetricDefinitions.map(m=>[m.id,rows.filter(m.matches).length]));
 assert.deepEqual(count(x.caseQueueRows()),{unassigned:11,processing:9,high:18,followup:4});
 const fixture=[
  {id:'a',status:'New',owner:'未分配',severity:'高',tasks:[{status:'New'},{status:'In progress'}]},
  {id:'b',status:'In progress',owner:'Analyst',severity:'中',tasks:[{status:'Completed'}]},
  {id:'c',status:'Resolved',owner:'未分配',severity:'高',tasks:[{status:'New'}]},
  {id:'d',status:null,owner:null,severity:'高',tasks:[{status:'New'}]},
  {id:'e',status:'New',owner:' ',severity:'低',tasks:[{status:null}]},
  {id:'f',status:'New',owner:'Unknown',severity:null,tasks:[]}
 ];
 assert.deepEqual(count(fixture),{unassigned:2,processing:1,high:1,followup:1});
 for(const row of fixture){row.recordedCase=true;row.localCollection=true;row.sourceEnvironment='another-source';}
 assert.deepEqual(count(fixture),{unassigned:2,processing:1,high:1,followup:1});
 const html=x.caseQueue();assert.ok(!/case-type-tabs|Generic|有关联调查的案件|部分交付的调查|当前案件<\/small>/.test(html));assert.ok(html.includes('查看案件统计说明'));
});
test('Case metric drilldown replaces filters, preserves columns and sort, and does not write business data',async()=>{
 const x=load();x.s.location.hash='#/cases';const before=JSON.stringify(x.store),t=x.tableState('cases');
 Object.assign(t,{query:'no match',status:'Resolved',severity:'低',owner:'other',start:'2026-11-02',minPriority:'99',columns:['id','title'],sort:'created',direction:-1,page:3,selected:['17420']});
 await x.click('case-metric','unassigned');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,11);assert.deepEqual([...t.columns],['id','title']);assert.equal(t.sort,'created');assert.equal(t.direction,-1);assert.equal(t.page,1);assert.equal(t.selected.length,0);assert.equal(t.query,'');assert.equal(t.start,'');assert.equal(t.minPriority,'');
 t.query='no match';assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,0);assert.ok(x.caseQueue().includes('<b>11</b><small>个案件</small>'));
 await x.click('case-metric','high');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,18);
 await x.click('case-metric','high');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,25);
 await x.click('case-metric','followup');assert.deepEqual([...x.filteredRows('cases',x.caseQueueRows()).map(c=>c.id)],['outcome-case-02','explore-case-02','outcome-case-01','17420']);
 await x.dispatch('click',{closest:sel=>sel==='[data-action]'?{dataset:{action:'remove-filter',key:'cases',field:'caseMetric'}}:null});assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,25);
 await x.click('case-metric','processing');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,9);
 await x.click('clear-filters','cases');assert.equal(t.caseMetric,'');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,25);
 assert.equal(JSON.stringify(x.store),before);assert.equal(x.saves(),0);
});
test('Case metric filter sets preserve the criterion and old filter sets clear it',async()=>{
 const x=load();x.s.location.hash='#/cases';const business=JSON.stringify([x.store.cases,x.M.runs(x.store)]);
 await x.click('case-metric','high');x.nodes['#filter-set-form']={values:{name:'高严重程度待处理'}};await x.click('confirm-case-filter-set','');
 const saved=x.store.caseFilterSets.find(s=>s.name==='高严重程度待处理');assert.equal(saved.filters.caseMetric,'high');
 x.store.caseFilterSets.push({id:'legacy-set',name:'旧筛选',filters:{query:'',severity:'中',status:'',owner:'',start:'',end:''}});
 await x.click('case-metric','followup');
 const choose=value=>x.dispatch('change',{dataset:{},value,hasAttribute:name=>name==='data-case-filter-set',closest:()=>null});
 await choose(saved.id);assert.equal(x.tableState('cases').caseMetric,'high');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,18);
 await choose('legacy-set');assert.equal(x.tableState('cases').caseMetric,'');assert.equal(x.filteredRows('cases',x.caseQueueRows()).length,4);
 assert.equal(JSON.stringify([x.store.cases,x.M.runs(x.store)]),business);
});
