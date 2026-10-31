const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
function load(){
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/alerts'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 for(const file of ['icons','data','replayed-alerts','alert-detail','workspace-model','workspace-view','investigation-data','alert-flow-workspace','aisoc20-data','recorded-examples','investigation-graph','investigation-workspace'])vm.runInContext(fs.readFileSync(path.join(root,file+'.js'),'utf8'),s);
 const code=fs.readFileSync(path.join(root,'app.js'),'utf8').replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,drawerMarkup,fullAlert,investigationView,filteredRows,caseQueueRows,tableState};\n})();');
 vm.runInContext(code,s);return {...s.window.api,s,data:s.window.aisoc20RecordedData};
}
test('six historical records, six Runs and three explicitly local Cases append idempotently',()=>{
 const x=load(),d=x.data;assert.equal(x.store.alerts.length,64);assert.equal(x.store.cases.length,15);
 assert.equal(x.s.window.investigationWorkspaceModel.runs(x.store).length,14);
 assert.equal(d.runs.filter(r=>r.completion==='partial').length,5);assert.equal(d.runs.filter(r=>r.report).length,5);
 assert.equal(d.runs.reduce((n,r)=>n+r.calls,0),36);assert.equal(d.runs.reduce((n,r)=>n+r.tokens,0),117286);
 assert.equal(d.runs.reduce((n,r)=>n+r.tools.length,0),34);assert.equal(d.runs.reduce((n,r)=>n+r.steps.length,0),71);
 for(const a of d.alerts){assert.equal(a.caseId,null);assert.equal(a.sourceEnvironment,'aisoc20');assert.equal(a.detailMaterial.timelineVersion,2);}
 for(const c of d.cases){assert.equal(c.sourceCaseId,null);assert.equal(c.localCollection,true);assert.equal(c.alertIds.length,2);assert.equal(c.priority,null);}
 const actual=x.store.cases.find(c=>c.id===d.cases[0].id);actual.title='本地编辑';actual.alertIds.pop();const before=JSON.stringify(x.store);
 x.s.window.mergeAiSoc20Data(x.store);assert.equal(JSON.stringify(x.store),before);
});
test('all actual views render without mutation, fabricated attachments, inventory or wrong stage completion',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const r of x.data.runs)for(const view of ['overview','process','tools','graphs','ledger','report']){
  x.s.location.hash=`#/investigations/${r.id}/${view}`;const html=x.investigationView.workbench();assert.ok(!/Invalid Date|undefined/.test(html));
  if(view==='process'&&r.completion==='partial'){assert.ok(html.includes('已跳过'));assert.ok(!html.includes("graph node &#39;attack_path&#39; completed"));}
  if(view==='tools')assert.ok(html.includes('未记录'));
 }
 for(const c of x.data.cases)for(const tab of ['overview','case-info','alerts','assets','attack','evidence','tasks','activities','comments','similar','investigations']){
  x.s.location.hash=`#/cases/${c.id}/${tab}`;const html=x.casePage();assert.ok(!html.includes('iv-source-notice'));assert.ok(!html.includes('本地整理'));assert.ok(!/Invalid Date|undefined|>null</.test(html));
  if(tab==='comments'){assert.ok(html.includes('附件 (0)'));assert.ok(!html.includes('investigation-notes.txt'));}
  if(tab==='assets'){assert.ok(html.includes('未关联库存'));assert.ok(!html.includes('Contoso'));}
 }
 for(const a of x.data.alerts)for(const tab of ['overview','timeline','raw','response']){
  x.s.location.hash=`#/alerts/${a.id}/${tab}`;const html=x.fullAlert(x.store.alerts.find(row=>row.id===a.id));assert.ok(!/Invalid Date|undefined/.test(html));
 }
 assert.equal(JSON.stringify(x.store),before);
});
test('related and similar alert candidates do not cross source environment or tenant',()=>{
 const x=load(),a=x.store.alerts.find(a=>a.sourceEnvironment==='aisoc20'),other=x.store.alerts.find(a=>a.persistedRecord&&a.sourceEnvironment!=='aisoc20'&&a.hostNames.includes(a.hostNames[0]));
 x.s.location.hash=`#/alerts/${a.id}/overview`;const html=x.fullAlert(a);
 for(const id of x.data.cases[0].alertIds.filter(id=>id!==a.id))assert.ok(html.includes(`#/alerts/${id}/overview`));
 for(const row of x.store.alerts.filter(a=>a.persistedRecord&&a.sourceEnvironment!=='aisoc20'))assert.ok(!html.includes(`#/alerts/${row.id}/overview`));
 const second=x.store.alerts.find(row=>row.id===x.data.cases[0].alertIds[1]);second.sourceTenantId='other-tenant';assert.ok(!x.fullAlert(a).includes(`#/alerts/${second.id}/overview`));
 assert.ok(other);
});
test('saved graph is filtered to current Case members and is separate from Run graphs',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id===x.data.cases[0].id);
 x.s.location.hash=`#/cases/${c.id}/attack`;let html=x.casePage();assert.ok(html.includes('OBSERVED_ON'));assert.ok(html.includes('DEMO-FIN-11'));assert.ok(!html.includes('DEMO-APP-12'));
 c.alertIds.splice(1);html=x.casePage();assert.ok(!html.includes(x.data.cases[0].alertIds[1]));
 for(const r of x.data.runs)assert.equal(Object.keys(r.graphs).length,0);
 assert.ok(x.data.graph.nodes.every(n=>!n.attributes.labels.includes('Case')));
});
test('projection omits model prompts/replies, does not fabricate artifact metadata or missing timestamps',()=>{
 const x=load();for(const r of x.data.runs){
  assert.equal(r.ended,null);assert.equal(r.sourceCaseId,null);assert.equal(r.alertIds.length,1);
  for(const s of r.steps){assert.equal(s.payload.prompt,undefined);assert.equal(s.payload.response,undefined);}
  for(const a of r.artifacts){assert.equal(a.id,undefined);assert.equal(a.sha256,undefined);assert.equal(a.created_at,undefined);assert.equal(a.size_bytes,a.actual_bytes);assert.equal(a.hash_match,true);}
 }
 const triage=x.data.runs.find(r=>r.completion==='not_escalated');assert.equal(triage.input,null);assert.equal(triage.started,null);assert.equal(triage.report,null);
 const entity=x.store.assets.find(a=>a.sourceEnvironment==='aisoc20');x.ui.drawer={type:'entity',id:entity.id};const html=x.drawerMarkup();assert.ok(html.includes('未关联库存'));assert.ok(!html.includes('Contoso'));assert.ok(!html.includes('asset-raw:'));
});

test('unscored Cases do not match any numeric priority band or minimum',()=>{
 const x=load(),t=x.tableState('cases');for(const band of ['low','medium','top']){t.priorityBand=band;assert.ok(x.filteredRows('cases',x.caseQueueRows()).every(c=>!c.localCollection));}
 t.priorityBand='';t.minPriority='0';assert.ok(x.filteredRows('cases',x.caseQueueRows()).every(c=>!c.localCollection));
 t.minPriority='';assert.equal(x.filteredRows('cases',x.caseQueueRows()).filter(c=>c.localCollection).length,3);
});

test('recorded Run graph tabs expose saved relations and chronology without turning them into Run artifacts',()=>{
 const x=load(),r=x.data.runs[1],before=JSON.stringify(x.store);
 for(const graph of ['all','attack_chain','attack_path','alert_graph']){
  x.s.location.hash=`#/cases/local-aisoc20-1/investigations?run=${r.id}&view=graphs&graph=${graph}`;
  const html=x.casePage();for(const text of ['7 个对象','8 条已记录关系','DEMO-FIN-11','demo.finance','198.51.100.41','攻击路径分析已跳过','本次输入','不是本次 Run 产生的攻击路径'])assert.ok(html.includes(text));
  assert.ok(!html.includes('本次未保存此类材料'));assert.ok(!html.includes('DEMO-APP-12'));
  if(['all','attack_chain'].includes(graph)){assert.ok(html.includes('关联告警时序'));assert.ok(html.includes('#/alerts/'+x.data.alerts[0].id+'/overview'));}
 }
 x.s.location.hash=`#/investigations/${r.id}/graphs`;assert.ok(x.investigationView.workbench().includes('7 个对象'));
 assert.equal(JSON.stringify(x.store),before);assert.equal(Object.keys(r.graphs).length,0);
});
