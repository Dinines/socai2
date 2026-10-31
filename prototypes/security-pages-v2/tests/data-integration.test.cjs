const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function load(saved=null){
 const handlers={},nodes={'#app':{},'#toast':{classList:{add(){},remove(){}}}};
 const s={window:{addEventListener(){}},document:{addEventListener:(type,fn)=>(handlers[type]||=[]).push(fn),querySelector:selector=>nodes[selector]||null},location:{hash:'#/incidents'},localStorage:{getItem:()=>saved,setItem(){}},structuredClone,URLSearchParams,clearInterval,clearTimeout,setTimeout:()=>0,FormData:class{constructor(form){return Object.entries(form);}}};vm.createContext(s);
 const files=[...fs.readFileSync(path.join(root,'index.html'),'utf8').matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(x=>x[1]);
 for(const f of files){let code=fs.readFileSync(path.join(root,f),'utf8');if(f==='app.js')code=code.replace('readQueueLink();render();\n})();','window.api={store,ui,incidentPage,drawerMarkup,modalMarkup,investigationView,scopeActivities,readQueueLink,caseIncidents,alertsPage,casePage,caseQueueRows,tableState,filteredRows,workspaceView};\n})();');vm.runInContext(code,s);}
 return {...s.window.api,s,nodes,click:async action=>{for(const fn of handlers.click)await fn({target:{closest:selector=>selector==='[data-action]'?{dataset:{action}}:null},preventDefault(){}});},M:s.window.investigationWorkspaceModel,F:s.window.alertFlowWorkspace};
}

test('all data stays accessible, with saved Cases first and coherent filter metrics',()=>{
 const x=load(),rows=x.caseQueueRows();assert.equal(rows.length,21);assert.ok(rows.slice(0,7).every(c=>c.localCollection||c.recordedCase));assert.ok(rows.slice(7).every(c=>!c.localCollection&&!c.recordedCase));
 x.s.location.hash='#/cases?data=aisoc';x.readQueueLink();let html=x.casePage();assert.equal(x.filteredRows('cases',rows).length,21);assert.ok(!html.includes('案件数据来源'));assert.ok(!html.includes('AiSOC ·'));assert.ok(html.includes('11</b>'));
 x.tableState('cases').query='local-socai2';html=x.casePage();assert.equal(x.filteredRows('cases',rows).length,3);assert.ok(html.includes('5</b>'));assert.ok(!html.includes('11</b>'));
 x.s.location.hash='#/cases?data=all';x.readQueueLink();assert.equal(x.filteredRows('cases',rows).length,21);
 x.s.location.hash='#/cases?data=design';x.readQueueLink();assert.equal(x.filteredRows('cases',rows).length,21);
});
test('twenty-source incident groups use exact identities without assigning the unlinked sixth alert',()=>{
 const x=load(),d=x.s.window.aisoc20RecordedData,inc=x.store.incidents.filter(i=>i.sourceEnvironment==='aisoc20');assert.equal(inc.length,3);assert.deepEqual([...inc.map(i=>i.sourceAlertIds.length)].sort(),[1,2,2]);
 for(const i of inc){const members=x.store.alerts.filter(a=>a.incidentId===i.id);assert.ok(members.every(a=>a.sourceEnvironment===i.sourceEnvironment&&a.sourceTenantId===i.sourceTenantId));assert.equal(i.priority,null);assert.equal(i.status,'New');assert.equal(i.sourceHandlingStatus,'Not set');x.s.location.hash=`#/incidents/${i.id}/summary`;const html=x.incidentPage();assert.ok(html.includes('进入 Case'));assert.ok(x.caseIncidents(x.store.cases.find(c=>html.includes('#/cases/'+c.id+'/overview'))).some(row=>row.id===i.id));assert.ok(!html.includes('INV-20261024'));
 }
 assert.equal(d.alerts.filter(a=>!a.incidentId).length,1);assert.equal(x.caseIncidents(x.store.cases.find(c=>c.recordedCase)).length,0);
});
test('all seven saved Cases expose only their own Runs, artifacts, tools and source activity',()=>{
 const x=load(),cases=x.store.cases.filter(c=>c.localCollection||c.recordedCase),before=JSON.stringify(x.store),sum={runs:0,tools:0,artifacts:0,events:0};
 for(const c of cases){const rs=x.M.forCase(x.store,c);assert.ok(rs.length);assert.ok(rs.every(r=>r.sourceEnvironment===c.sourceEnvironment&&r.sourceTenantId===c.sourceTenantId));
  const st=x.F.caseStats(rs);for(const key of Object.keys(sum))sum[key]+=st[key];
  x.s.location.hash=`#/cases/${c.id}/evidence`;const html=x.casePage();assert.ok(html.includes('案件证据与调查材料'));for(const r of rs){assert.ok(html.includes(`run=${r.id}&view=tools`));assert.ok(html.includes(`run=${r.id}&view=report`));for(const a of r.artifacts)assert.ok(html.includes(a.kind));}
  for(const other of x.M.runs(x.store).filter(r=>!rs.some(s=>s.id===r.id)))assert.ok(!html.includes(`run=${other.id}&view=tools`));
  x.s.location.hash=`#/cases/${c.id}/activities`;assert.equal(x.scopeActivities().filter(a=>a.runId).length,st.events);
  x.s.location.hash=`#/cases/${c.id}/case-info`;const info=x.casePage();assert.ok(!/incidents\/(null|undefined)\//.test(info));assert.ok(!/Invalid Date|>undefined</.test(info));
 }
 assert.deepEqual(sum,{runs:13,tools:90,artifacts:108,events:192});assert.equal(JSON.stringify(x.store),before);
});
test('twenty-source collected Runs survive member edits and reject cross-tenant or cross-environment matches',()=>{
 const x=load(),c=x.store.cases.find(c=>c.id==='local-aisoc20-1'),original=x.M.forCase(x.store,c).map(r=>r.id);c.alertIds=[];assert.deepEqual(x.M.forCase(x.store,c).map(r=>r.id),original);
 c.alertIds=[x.store.alerts.find(a=>a.sourceEnvironment==='socai2-21').id];assert.deepEqual(x.M.forCase(x.store,c).map(r=>r.id),original);
 const y=load(JSON.stringify(x.store));assert.deepEqual([...y.M.forCase(y.store,y.store.cases.find(row=>row.id===c.id)).map(r=>r.id)],[...original]);assert.equal(y.store.cases.find(row=>row.id===c.id).alertIds.length,1);
 c.sourceTenantId='wrong-tenant';assert.equal(x.M.forCase(x.store,c).length,0);
});
test('unknown Case and incident routes never render the first design record',()=>{
 const x=load();for(const page of ['cases','incidents']){x.s.location.hash=`#/${page}/missing/overview`;const html=page==='cases'?x.casePage():x.incidentPage();assert.ok(html.includes('未找到'));assert.ok(!html.includes(x.store.cases[0].title));assert.ok(!html.includes(x.store.incidents[0].title));}
});

test('current-flow Cases and incidents link in both directions using exact source membership',()=>{
 const x=load();for(const c of x.store.cases.filter(c=>c.alertFlowCollection)){
  const linked=x.caseIncidents(c);assert.equal(linked.length,1);assert.equal(linked[0].id,c.incidentId);
  x.s.location.hash=`#/cases/${c.id}/overview`;assert.ok(x.casePage().includes(`href="#/incidents/${c.incidentId}/summary"`));
  x.s.location.hash=`#/incidents/${c.incidentId}/summary`;assert.ok(x.incidentPage().includes(`href="#/cases/${c.id}/overview"`));
  const original=c.sourceTenantId;c.sourceTenantId='other';assert.equal(x.caseIncidents(c).length,0);c.sourceTenantId=original;
  const alert=x.store.alerts.find(a=>c.alertIds.includes(a.id));alert.sourceTenantId='other';const remaining=c.alertIds;c.alertIds=[alert.id];assert.equal(x.caseIncidents(c).length,0);c.alertIds=remaining;
 }
});
