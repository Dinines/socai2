const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),clone=x=>JSON.parse(JSON.stringify(x));
function load(saved=null){
 const nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}},s={window:{addEventListener(){}},document:{addEventListener(){},querySelector:q=>nodes[q]||null,getElementById:id=>nodes['#'+id]||null},location:{hash:'#/cases/explore-case-01/attack'},localStorage:{getItem:()=>saved,setItem(){}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData:class{constructor(f){this.f=f;}get(k){return this.f[k]||'';}getAll(k){return this.f[k]||[];}}};vm.createContext(s);
 for(const f of [...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(m=>m[1])){let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,caseQueue,caseWorkflow,investigationView,caseIncidents};\n})();');vm.runInContext(code,s);}
 const x={...s.window.api,s,nodes,M:s.window.investigationWorkspaceModel,E:s.window.caseExplorationModel,G:s.window.investigationGraphModel};x.c=x.store.cases.find(c=>c.id==='explore-case-01');x.W=x.caseWorkflow;x.r=x.M.forCase(x.store,x.c)[0];x.base=x.G.build({...x.r,graphs:{...x.r.graphs,attack_chain:null}},x.store);x.base.anchorTime=x.r.ended;x.eligible=(c,a)=>x.W.eligible(c,a);return x;
}
test('exploration fixtures append once, preserving all actual records and editable demonstrations',()=>{
 const x=load(),before=JSON.stringify(x.store),actual=JSON.stringify(x.M.runs(x.store).filter(r=>r.recorded));x.s.window.mergeCaseExplorationData(x.store);assert.equal(JSON.stringify(x.store),before);assert.equal(x.M.runs(x.store).filter(r=>r.recorded).length,13);
 x.c.title='本地修改';x.store.caseDemoRuns[0].status='failed';const y=load(JSON.stringify(x.store));assert.equal(y.c.title,'本地修改');assert.equal(y.store.caseDemoRuns[0].status,'failed');assert.equal(JSON.stringify(y.M.runs(y.store).filter(r=>r.recorded)),actual);
});
test('candidate expansion is bounded, scoped, ranked and does not expand taxonomy',()=>{
 const x=load(),before=JSON.stringify(x.store),rows=x.E.candidates(x.store,x.c,x.base,null,x.eligible);assert.equal(rows.length,6);assert.ok(rows.every(r=>r.shared.length&&r.dt<=86400000));assert.ok(rows.every((r,i)=>!i||r.score<=rows[i-1].score));
 assert.equal(x.E.supported({kind:'tech'}),false);assert.equal(x.E.supported({kind:'tactic'}),false);assert.equal(x.E.supported({kind:'device'}),true);
 const a=clone(x.store.alerts.find(a=>a.id===rows[0].alertId));a.id='alien';a.sourceTenantId='foreign';x.store.alerts.push(a);assert.ok(!x.E.candidates(x.store,x.c,x.base,null,x.eligible).some(r=>r.alertId==='alien'));x.store.alerts.pop();assert.equal(JSON.stringify(x.store),before);
});
test('expansion uses explicit object edges, supports a second pivot and preserves source graph',()=>{
 const x=load(),before=JSON.stringify([x.store,x.r]),row=x.E.candidates(x.store,x.c,x.base,null,x.eligible).find(r=>r.alertId==='explore-alert-09'),branch=x.E.branch(x.store,x.c,x.base,row,null,x.eligible),g=x.E.project(x.base,[branch]);
 assert.ok(g.nodes.find(n=>n.id==='explore-share').explored);assert.ok(g.nodes.find(n=>n.id==='explore-alert-09').explored);assert.ok(g.edges.filter(e=>e.layer==='exploration').every(e=>e.from==='explore-alert-09'));
 const next=x.E.candidates(x.store,x.c,g,'explore-share',x.eligible);assert.ok(next.some(r=>r.alertId==='explore-alert-10'));assert.equal(x.E.candidates(x.store,x.c,g,'explore-isolated',x.eligible).filter(r=>!r.already).length,0);
 assert.equal(new Set(g.nodes.map(n=>n.id)).size,g.nodes.length);assert.equal(JSON.stringify([x.store,x.r]),before);
});
test('preview, undo, save and reload keep exploration separate from membership and Runs',()=>{
 const x=load(),before=JSON.stringify([x.c.alertIds,x.M.runs(x.store)]);x.casePage();x.investigationView.handle('cx-recommend','');x.investigationView.handle('cx-preview','explore-alert-09');let html=x.nodes['#app'].innerHTML;assert.match(html,/cx-preview/);assert.equal(x.c.graphExploration,undefined);
 x.investigationView.handle('cx-add','explore-alert-09');x.investigationView.handle('cx-pick','explore-share');x.investigationView.handle('cx-save','');assert.equal(x.c.graphExploration.branches.length,1);
 const y=load(JSON.stringify(x.store));assert.match(y.casePage(),/cx-expanded/);assert.match(y.casePage(),/cx-picked/);y.investigationView.handle('cx-undo','');assert.ok(!y.nodes['#app'].innerHTML.includes('cx-expanded'));assert.equal(JSON.stringify([x.c.alertIds,x.M.runs(x.store)]),before);
});
test('preparing outside alerts requires explicit confirmation and validates everything before membership writes',()=>{
 const x=load(),before=JSON.stringify(x.store),outside='explore-alert-09';x.W.prepareFromGraph({alertIds:[outside],entityIds:['explore-share'],sourceRunId:x.r.id});assert.match(x.W.modal(),/加入并保存安排/);x.ui.modal=null;assert.equal(JSON.stringify(x.store),before);
 assert.throws(()=>x.W.saveDraft(x.c,{objective:'检查授权',alertIds:[outside],entityIds:[],confirmAdd:true,materialIds:['bad']}),/材料已不可用/);assert.equal(JSON.stringify(x.store),before);
 const history=JSON.stringify(x.M.runs(x.store)),d=x.W.saveDraft(x.c,{objective:'检查授权',alertIds:[outside],entityIds:['explore-share'],confirmAdd:true,sourceRunId:x.r.id,materialIds:[]});assert.ok(x.c.alertIds.includes(outside));assert.equal(d.status,'draft');assert.equal(JSON.stringify(x.M.runs(x.store)),history);
 x.W.cancelDraft(x.c,d.id);assert.equal(d.status,'cancelled');assert.ok(x.c.alertIds.includes(outside));assert.throws(()=>x.W.saveDraft(x.c,{id:d.id,objective:'不应覆盖',alertIds:[outside]}),/不能修改/);
});
test('entity-only draft freezes inputs on explicit simulation and active Run prevents a second start',()=>{
 const x=load(),d=x.W.saveDraft(x.c,{objective:'核实账号授权',alertIds:[],entityIds:['explore-user'],materialIds:[]});assert.equal(x.M.forCase(x.store,x.c).length,1);
 const r=x.W.startSimulation(x.c,d.id),frozen=JSON.stringify(r.snapshot);assert.equal(r.status,'queued');assert.equal(r.alertIds.length,0);assert.equal(x.W.activeRun(x.c).id,r.id);assert.equal(x.M.forCase(x.store,x.c).length,2);assert.equal(r.tools.length,0);
 const next=x.W.saveDraft(x.c,{objective:'下一轮',alertIds:x.c.alertIds,materialIds:[]});assert.throws(()=>x.W.startSimulation(x.c,next.id),/已有执行中/);x.W.cancelDraft(x.c,next.id);assert.equal(r.status,'queued');
 x.W.addMembers(x.c,['explore-alert-09']);assert.equal(JSON.stringify(r.snapshot),frozen);x.W.advanceSimulation(x.c,r.id);x.W.advanceSimulation(x.c,r.id);x.W.advanceSimulation(x.c,r.id);assert.equal(r.status,'completed');assert.equal(r.completion,'partial');assert.equal(x.W.activeRun(x.c),null);assert.equal(r.tools.length,0);assert.equal(r.report,null);assert.equal(x.M.runs(x.store).filter(r=>r.id.startsWith('SIM')).length,1);
});
test('real Cases cannot simulate execution and historical graph never offers expansion',()=>{
 const x=load();x.s.location.hash='#/cases/17420/attack';const c=x.store.cases.find(c=>c.id==='17420');assert.throws(()=>x.W.startSimulation(c,'fake'),/尚未接入/);
 x.s.location.hash='#/cases/explore-case-01/investigations?run=explore-run-01&view=graphs';const before=JSON.stringify(x.store),html=x.casePage();assert.ok(!html.includes('data-action="cx-'));assert.ok(html.includes('到案件图探索'));assert.equal(JSON.stringify(x.store),before);
});
test('active banner persists across Case pages and drafts remain cancellable without stopping execution',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='explore-case-02'),r=x.W.activeRun(c),before=JSON.stringify(r);
 for(const tab of ['case-info','overview','attack','alerts','evidence','tasks']){x.s.location.hash=`#/cases/${c.id}/${tab}`;assert.match(x.casePage(),tab==='overview'?/aria-label="AI 调查进度"/:/cw-active-banner/);}
 x.W.cancelDraft(c,'explore-draft-next');assert.equal(JSON.stringify(r),before);assert.throws(()=>x.W.startSimulation(c,'explore-draft-next'),/已有执行中/);
});
test('multiple incidents remain navigable, members deduplicate and other Cases are untouched',()=>{
 const x=load(),events=x.s.window.caseExplorationData.incidents.map(i=>i.id),ids=x.store.alerts.filter(a=>events.includes(a.incidentId)).map(a=>a.id),other=JSON.stringify(x.store.cases.filter(c=>c.id!==x.c.id)),history=JSON.stringify(x.M.runs(x.store));
 x.W.addMembers(x.c,ids,events);assert.equal(x.c.alertIds.length,10);assert.equal(x.caseIncidents(x.c).length,3);assert.equal(JSON.stringify(x.store.cases.filter(c=>c.id!==x.c.id)),other);assert.equal(JSON.stringify(x.M.runs(x.store)),history);
});
test('Case metric counts handling progress independently of active investigation status',()=>{
 const x=load();x.s.location.hash='#/cases';const metric=()=>x.caseQueue().match(/<button[^>]*data-action="case-metric" data-id="processing"[^>]*>[\s\S]*?<\/button>/)[0];assert.ok(!x.caseQueue().includes('多告警案件'));let n=x.store.cases.filter(c=>c.status==='In progress').length;assert.ok(metric().includes(`<b>${n}</b>`));x.c.status='Resolved';assert.ok(metric().includes(`<b>${n-1}</b>`));assert.match(metric(),/处理中/);
});
test('saved exploration pins its old base after a new completion and reset deliberately switches',()=>{
 const x=load();x.casePage();x.investigationView.handle('cx-save','');const old=x.r.id,newRun={...clone(x.r),id:'new-finished',ended:'2026-11-03T00:00:00Z'};x.store.caseDemoRuns.push(newRun);assert.match(x.casePage(),new RegExp(`data-run-id="${old}"`));assert.match(x.casePage(),/已保存探索的原调查/);
 const y=load(JSON.stringify(x.store));assert.match(y.casePage(),new RegExp(`data-run-id="${old}"`));y.investigationView.handle('cx-reset','');assert.match(y.nodes['#app'].innerHTML,/data-run-id="new-finished"/);
});
test('time range validates before draft adoption and all simulated views keep frozen inputs',()=>{
 const x=load(),before=JSON.stringify(x.store);assert.throws(()=>x.W.saveDraft(x.c,{objective:'x',alertIds:['explore-alert-09'],confirmAdd:true,timeStart:'2026-11-02T02:00:00Z',timeEnd:'2026-11-02T01:00:00Z'}),/起止时间/);assert.equal(JSON.stringify(x.store),before);
 const d=x.W.saveDraft(x.c,{objective:'对象授权核查',entityIds:['explore-user'],alertIds:[],materialIds:[],timeStart:'2026-11-02T00:00:00Z',timeEnd:'2026-11-03T00:00:00Z'}),r=x.W.startSimulation(x.c,d.id),snap=JSON.stringify(r.snapshot);assert.equal(r.snapshot.timeRange.start,d.timeRange.start);
 for(const view of ['overview','process','tools','graphs','ledger','report']){x.s.location.hash=`#/cases/${x.c.id}/investigations?run=${r.id}&view=${view}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html));assert.doesNotMatch(html,/本地演示|模拟推进下一阶段/);assert.equal(r.simulation,true);}assert.equal(JSON.stringify(r.snapshot),snap);
});
test('global fixture listings retain source flags without prototype badges or progress controls',()=>{
 const x=load(),d=x.W.saveDraft(x.c,{objective:'全局模拟标识验证',alertIds:x.c.alertIds,materialIds:[]}),r=x.W.startSimulation(x.c,d.id);x.s.location.hash='#/investigations';assert.doesNotMatch(x.investigationView.queue(),/本地演示/);assert.equal(r.simulation,true);
 for(const view of ['overview','process','tools','graphs','ledger','report']){x.s.location.hash=`#/investigations/${r.id}/${view}`;const html=x.investigationView.workbench();assert.doesNotMatch(html,/本地演示|未调用调查服务或 AI/);assert.ok(!html.includes('data-action="cw-simulate-next"'));assert.equal(r.simulation,true);}
});
test('read-only graph visits follow the latest completion while actual unsaved expansion pins with honest wording',()=>{
 const x=load();x.casePage();const next={...clone(x.r),id:'new-readonly-completion',ended:'2026-11-03T00:00:00Z'};x.store.caseDemoRuns.push(next);assert.match(x.casePage(),/data-run-id="new-readonly-completion"/);assert.ok(!x.casePage().includes('已保存探索的原调查'));
 const y=load();y.casePage();y.investigationView.handle('cx-recommend','');y.investigationView.handle('cx-add','explore-alert-09');y.store.caseDemoRuns.push(next);assert.match(y.casePage(),/data-run-id="explore-run-01"/);assert.match(y.casePage(),/当前探索的原调查/);assert.ok(!y.casePage().includes('已保存探索的原调查'));
});
test('recommendation panel survives redraw and Case-only empty list does not claim saved Chain is missing',()=>{
 const x=load();x.casePage();x.investigationView.handle('cx-recommend','');assert.match(x.nodes['#app'].innerHTML,/查看更多（剩余 1）/);
 x.s.location.hash='#/cases/82b1246f-9f34-463c-8c2d-27d2b075c741/attack';x.casePage();x.investigationView.handle('ug-list','candidates');const html=x.nodes['#app'].innerHTML;assert.match(html,/当前画布没有其他关联告警/);assert.ok(!html.includes('未保存关联查询结果'));
});
test('simulated input snapshot and completed graph labels remain frozen after source alert edits',()=>{
 const x=load(),d=x.W.saveDraft(x.c,{objective:'冻结原始输入',alertIds:[x.c.alertIds[0]],materialIds:[]}),r=x.W.startSimulation(x.c,d.id),title=x.store.alerts.find(a=>a.id===d.alertIds[0]).title;
 x.store.alerts.find(a=>a.id===d.alertIds[0]).title='后来修改的名称';for(let i=0;i<3;i++)x.W.advanceSimulation(x.c,r.id);
 const g=x.G.build(r,x.store);assert.equal(r.input.alerts[0].title,title);assert.equal(g.nodes.find(n=>n.id===d.alertIds[0]).label,title);
});


test('Case exploration omits historic source panels while linked Runs retain original materials',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const c of x.store.cases){
  x.s.location.hash=`#/cases/${c.id}/attack`;const html=x.casePage();assert.ok(html.includes('data-action="cx-recommend"'),c.id);
  for(const text of ['iv-graph-materials','来源材料与关联范围','攻击路径分析已跳过','攻击路径：未关联 Case','原记录见下方来源材料'])assert.ok(!html.includes(text),c.id+text);
  const r=x.M.latestFinished(x.M.forCase(x.store,c).filter(r=>r.graphEligible!==false));if(!r)continue;
  assert.ok(html.includes(`run=${r.id}&view=graphs`),c.id);
  x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=graphs`;const history=x.casePage();assert.ok(history.includes('iv-graph-materials'),c.id);assert.ok(history.includes('来源材料与关联范围'),c.id);assert.ok(!history.includes('data-action="cx-'),c.id);
 }
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});
test('both reported recorded Cases expose entity expansion and draft preparation without writes',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]);
 for(const [cid,label] of [['local-aisoc20-3','demo.export'],['local-socai2-7bde0c0b-0d18-4abc-9382-9752f2ae5e98','demo.finance']]){
  x.s.location.hash=`#/cases/${cid}/attack`;const html=x.casePage(),tag=html.match(/<button\b[^>]*>/g).find(t=>t.includes('data-action="ug-node"')&&t.includes(`aria-label="${label}"`));assert.ok(tag,cid);
  const id=tag.match(/data-id="([^"]+)"/)[1];x.investigationView.handle('ug-node',id);assert.match(x.nodes['#app'].innerHTML,/以此节点扩展/);
  x.investigationView.handle('cx-expand',id);assert.match(x.nodes['#app'].innerHTML,/扩展线索/);assert.match(x.nodes['#app'].innerHTML,/data-action="cx-add"/);
  x.investigationView.handle('cx-pick',id);x.investigationView.handle('cx-prepare','');assert.ok(x.W.modal().includes('调查目标'),cid);x.ui.modal=null;
 }
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});

test('sidebar separates leads from hidden-node messages and retains pivot when inspecting objects',()=>{
 const x=load(),before=JSON.stringify([x.store,x.M.runs(x.store)]),device=x.base.nodes.find(n=>n.kind==='device').id;
 const sidebar=()=>x.nodes['#app'].innerHTML.match(/<aside class="ug-detail"[\s\S]*?<\/aside>/)[0];
 x.casePage();x.investigationView.handle('ug-node',device);x.investigationView.handle('cx-expand',device);const original=sidebar();assert.match(original,/cx-leads-view/);assert.ok(!original.includes('cx-object-view'));
 x.investigationView.handle('ug-type','device');assert.ok(!sidebar().includes('所选对象已隐藏'));assert.match(sidebar(),/cx-leads-view/);
 x.investigationView.handle('ug-node',x.c.alertIds[0]);assert.match(sidebar(),/cx-object-view/);assert.ok(!sidebar().includes('cx-candidate-title'));
 x.investigationView.handle('cx-panel','leads');assert.equal(sidebar(),original);
 x.investigationView.handle('cx-recommend','');assert.match(sidebar(),/查看线索规则/);assert.match(sidebar(),/时间基准（UTC\+8）/);assert.ok(!sidebar().includes(x.r.ended));
 assert.equal(JSON.stringify([x.store,x.M.runs(x.store)]),before);
});

test('graph adopts selected outside alerts only after confirmation and marks a baseline update without creating a Run',()=>{
 const x=load(),before=JSON.stringify(x.store),runs=JSON.stringify(x.M.runs(x.store));x.casePage();const html=x.casePage();assert.ok(!html.includes('data-action="cx-prepare"'));assert.ok(html.includes('data-action="cx-adopt"'));assert.ok(html.includes('data-action="cx-ask-picked"'));
 x.W.openGraphAdoption(['explore-alert-09']);assert.equal(x.ui.modal.type,'cw-add');assert.equal(x.ui.modal.selected[0],'explore-alert-09');assert.equal(JSON.stringify(x.store),before);
 x.W.addMembers(x.c,x.ui.modal.selected);assert.equal(x.c.baselineUpdate.status,'pending');assert.ok(x.c.baselineUpdate.alertIds.includes('explore-alert-09'));assert.equal(JSON.stringify(x.M.runs(x.store)),runs);
});
test('previous manual preparations become editable human tasks while source drafts and Runs stay unchanged',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='explore-case-02');x.s.location.hash=`#/cases/${c.id}/tasks`;const history=JSON.stringify(x.M.runs(x.store)),drafts=JSON.stringify(c.investigationDrafts),task=x.M.humanTasks(c).find(t=>t.sourceDraftId==='explore-draft-next');assert.ok(task);assert.equal(c.tasks.length,0);assert.match(x.W.tasks(),/补充核对服务账号/);assert.ok(!x.W.tasks().includes('cw-simulate-start'));
 x.W.saveTask(c,{id:task.id,title:task.title,status:'Completed',result:'已由负责人确认属于正常备份。',owner:'Alex Wilber',sourceRunId:task.sourceRunId,referenceContext:task.referenceContext,materialIds:[]});assert.equal(c.tasks.length,1);assert.equal(x.M.humanTasks(c).filter(t=>t.sourceDraftId===task.sourceDraftId).length,1);assert.equal(c.tasks[0].status,'Completed');assert.equal(JSON.stringify(c.investigationDrafts),drafts);assert.equal(JSON.stringify(x.M.runs(x.store)),history);
});
