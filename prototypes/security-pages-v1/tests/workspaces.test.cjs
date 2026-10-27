const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
function setup(){
 const sandbox={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/cases/17420/overview'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};
 vm.createContext(sandbox);
 for(const name of ['icons','data','replayed-alerts','alert-detail','workspace-model','workspace-view'])vm.runInContext(fs.readFileSync(path.join(root,name+'.js'),'utf8'),sandbox);
 const app=fs.readFileSync(path.join(root,'app.js'),'utf8').replace('readQueueLink();render();\n})();','window.testAPI={store,ui,casePage,scopeAlerts,workspaceView};\n})();');
 assert.ok(app.includes('window.testAPI='));vm.runInContext(app,sandbox);
 return {...sandbox.window.testAPI,W:sandbox.window.referenceWorkspaces,sandbox};
}
test('explicit relations have visible supporting alerts with both endpoints',()=>{
 const {store,W}=setup();
 for(const source of ['',...new Set(store.alerts.map(a=>a.source))])for(const index of [0,3,99]){
  const m=W.graph(store,store.alerts.filter(a=>a.incidentId==='262144'),{source,index});
  for(const e of m.edges){assert.equal(e.kind,'association');assert.ok(e.alertIds.length);for(const id of e.alertIds){const a=m.visible.find(x=>x.id===id);assert.ok(a);assert.ok(a.entityIds.includes(e.from)&&a.entityIds.includes(e.to));}}
 }
});
test('associated view, grouping and potential paths do not change members or alerts',()=>{
 const {store,W}=setup(),members=store.alerts.filter(a=>a.incidentId==='262144'),before=JSON.stringify(store);
 const base=W.graph(store,members,{grouped:true}),expanded=W.graph(store,members,{associated:true});
 assert.ok(expanded.alerts.length>base.alerts.length);assert.equal(base.nodes.flatMap(n=>n.members).length,8);
 const path=W.graph(store,members,{selected:'u1',blast:true});assert.ok(path.selectedPath);assert.ok(path.edges.some(e=>e.kind==='potential'));assert.ok(path.edges.filter(e=>e.kind==='potential').every(e=>!e.alertIds.length));
 assert.equal(W.graph(store,members,{selected:'ip1',blast:true}).selectedPath,undefined);
 assert.equal(W.graph(store,members,{selected:'u1',blast:true,hidden:new Set(['app'])}).paths.length,0);
 assert.equal(W.graph(store,[],{selected:'u1',blast:true}).paths.length,0);
 assert.equal(JSON.stringify(store),before);
});
test('Case directory exposes tasks and follows current investigation membership',()=>{
 const {store,casePage,W}=setup(),c=store.cases[0];
 assert.match(casePage(),/#\/cases\/17420\/tasks/);assert.equal(W.investigationRecords(store.alerts.filter(a=>c.alertIds.includes(a.id))).length,2);
 c.alertIds=[store.alerts[9].id];const html=casePage();assert.match(html,/investigations[^>]*>调查<span class="count">0<\/span>/);
 assert.equal(W.investigationRecords(store.alerts.filter(a=>c.alertIds.includes(a.id))).length,0);
});
test('Case closure and assignment keep every alert and other Case unchanged',()=>{
 const {store,W}=setup(),before=JSON.stringify(store.alerts),other=JSON.stringify(store.cases[1]);
 W.updateCase(store,store.cases[0],{status:'Resolved',owner:'Megan Bowen',resolutionNote:'已完成复核',tags:'复核，交接'});
 assert.equal(store.cases[0].status,'Resolved');assert.equal(store.cases[0].tags.join(','),'复核,交接');
 assert.equal(JSON.stringify(store.alerts),before);assert.equal(JSON.stringify(store.cases[1]),other);
});
test('actual replays do not acquire fixture investigations, relationships or paths',()=>{
 const {store,W}=setup(),actual=store.alerts.filter(a=>a.persistedRecord);
 assert.equal(W.investigationRecords(actual).length,0);
 const g=W.graph(store,actual,{selected:'u1',blast:true});assert.equal(g.edges.length,0);assert.equal(g.paths.length,0);
});
test('changing object clears graph focus, filters and pending playback',()=>{
 const {workspaceView,ui,sandbox}=setup();
 workspaceView.resetScope();Object.assign(ui.graph,{selected:'u1',alert:'old',edge:'old',severity:'高',associated:true,blast:true,index:2});
 sandbox.location.hash='#/cases/17421/attack';workspaceView.resetScope();
 assert.equal(ui.graph.scope,'cases:17421');for(const k of ['selected','alert','edge'])assert.equal(ui.graph[k],null);
 assert.equal(ui.graph.severity,'');assert.equal(ui.graph.associated,false);assert.equal(ui.graph.blast,false);assert.equal(ui.graph.index,99);
});
test('task creation and completion save only the current Case and its activity',()=>{
 const {store,sandbox}=setup(),c=store.cases[0],alerts=JSON.stringify(store.alerts);let saves=0;const logs=[];
 sandbox.FormData=class{constructor(form){return Object.entries(form);}};
 const view=sandbox.window.createReferenceWorkspace({store,ui:{graph:{}},currentCase:()=>c,save:()=>saves++,render(){},toast(){},logActivity:(...args)=>logs.push(args)});
 view.submitTask({title:' 核对授权范围 ',owner:'Alex Wilber',due:'2026-10-26T12:00'});
 assert.equal(c.tasks[0].title,'核对授权范围');assert.equal(c.tasks[0].status,'New');
 view.changeTask(c.tasks[0].id,'Completed');assert.ok(c.tasks[0].completedAt);assert.equal(saves,2);assert.equal(logs.length,2);assert.equal(logs[1][4][0],c.id);assert.equal(JSON.stringify(store.alerts),alerts);assert.equal(store.cases[1].tasks,undefined);
});
