const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function load(version='v2'){
 const root=path.resolve(__dirname,'../../security-pages-'+version);
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/alerts'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 const files=['icons','data','replayed-alerts','alert-detail','workspace-model','workspace-view'];if(version==='v2')files.push('investigation-data','investigation-workspace');
 for(const n of files)vm.runInContext(fs.readFileSync(path.join(root,n+'.js'),'utf8'),s);
 const extras=version==='v2'?',investigationView,casePage,incidentPage':'';
 const code=fs.readFileSync(path.join(root,'app.js'),'utf8').replace('readQueueLink();render();\n})();',`window.api={store,ui,alertsPage,drawerMarkup,fullAlert${extras}};\n})();`);
 assert.ok(code.includes('window.api='));vm.runInContext(code,s);return {...s.window.api,s,M:s.window.investigationWorkspaceModel};
}
test('V1 and V2 retain all 291 alert renders for the same input',()=>{
 const a=load('v1'),b=load();assert.equal(a.alertsPage(),b.alertsPage());let n=1;
 for(const row of a.store.alerts){a.ui.drawer=b.ui.drawer={type:'alert',id:row.id};assert.equal(a.drawerMarkup(),b.drawerMarkup());n++;
  for(const tab of ['overview','timeline','raw','response']){a.s.location.hash=b.s.location.hash=`#/alerts/${row.id}/${tab}`;assert.equal(a.fullAlert(row),b.fullAlert(b.store.alerts.find(x=>x.id===row.id)));n++;}}
 assert.equal(n,291);
});
test('all saved Runs and five views render; no Case is invented or state mutated',()=>{
 const x=load(),rows=x.M.runs(x.store),before=JSON.stringify(x.store);assert.equal(rows.length,8);
 for(const r of rows)for(const view of ['overview','process','tools','graphs','report']){
  x.s.location.hash=`#/investigations/${r.id}/${view}`;const html=x.investigationView.workbench();assert.ok(html.includes(r.id));assert.ok(!html.includes('Invalid Date'));
 }
 assert.equal(JSON.stringify(x.store),before);assert.equal(x.store.cases.length,12);
 for(const r of rows.filter(x=>x.recorded))assert.ok(r.alertIds.every(id=>x.store.alerts.find(a=>a.id===id).caseId===null));
});
test('recorded graph statuses and IOC literals preserve source fields',()=>{
 const x=load(),r=x.M.runs(x.store).find(r=>r.id==='d141b0e3-16cc-5a0b-8d7f-35159342efe6');x.s.location.hash=`#/investigations/${r.id}/graphs`;
 assert.equal(r.graphs.attack_chain.status,'empty');assert.equal(r.graphs.attack_path.status,'not_linked');assert.equal(r.graphs.alert_graph.status,'success');
 const html=x.investigationView.workbench();for(const label of ['无候选关系','未关联 Case','已返回','图可达实体'])assert.ok(html.includes(label));
 const rows=x.M.runs(x.store).filter(r=>r.recorded);
 let iocs=0;for(const run of rows){x.s.location.hash=`#/investigations/${run.id}/graphs`;const h=x.investigationView.workbench();for(const n of run.graphs.alert_graph?.data?.neighbors?.neighbors||[]){if(n.properties?.indicator_value){iocs++;assert.ok(h.includes(n.properties.indicator_value));}if(n.rel_type)assert.ok(h.includes(n.rel_type));}}
 assert.ok(iocs>0);
});
test('Run state, completeness, verdict and tokens remain separate',()=>{
 const x=load(),r=x.M.runs(x.store).find(r=>r.id==='d141b0e3-16cc-5a0b-8d7f-35159342efe6');x.s.location.hash=`#/investigations/${r.id}/overview`;const html=x.investigationView.workbench();for(const value of ['已结束','部分交付','待复核','29,025','26922 of 20000'])assert.ok(html.includes(value));
});
test('Case membership filters Runs and invalid Run does not silently select another',()=>{
 const x=load();x.s.location.hash='#/cases/17420/investigations?run=does-not-exist';assert.ok(x.investigationView.workbench().includes('没有关联调查运行'));
 x.store.cases[0].alertIds=[];x.s.location.hash='#/cases/17420/overview';assert.ok(x.casePage().includes('没有关联调查运行'));
 x.s.location.hash='#/investigations/missing/overview';assert.ok(!x.investigationView.workbench().includes('身份与终端活动调查'));
});
test('Chain seed/window filtering does not alter members or create service scores',()=>{
 const x=load(),members=x.store.alerts.filter(a=>a.incidentId==='262144'),before=JSON.stringify(x.store);
 const one=x.M.chain(x.store,members,members[0].id,1),wide=x.M.chain(x.store,members,members[0].id,24);assert.ok(wide.rows.length>=one.rows.length);
 for(const row of wide.rows){assert.ok(row.shared.length);assert.equal(row.score,undefined);}assert.equal(JSON.stringify(x.store),before);
});
test('Case directory count and history include the same real Run when locally associated',()=>{
 const x=load(),actual=x.store.alerts.find(a=>a.persistedRecord);x.store.cases[0].alertIds=[actual.id];x.s.location.hash='#/cases/17420/investigations';
 const html=x.casePage();assert.match(html,/调查历史<span class="count">1<\/span>/);assert.ok(html.includes(actual.detailMaterial.runs[0].id));
});
test('stored result text is escaped and never rendered as executable HTML',()=>{
 const x=load(),r=x.s.window.savedInvestigationRuns[0];r.findings=['<img src=x onerror=alert(1)>'];x.s.location.hash=`#/investigations/${r.id}/overview`;const html=x.investigationView.workbench();assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img src=x'));
});
test('saved Run input is retained independently of the current Alert',()=>{
 const x=load(),r=x.s.window.savedInvestigationRuns[0],input=JSON.stringify(r.input);
 const alert=x.store.alerts.find(a=>a.id===r.alertIds[0]);alert.title='CURRENT ALERT CHANGED';
 x.s.location.hash=`#/investigations/${r.id}/overview`;
 const html=x.investigationView.workbench();assert.ok(html.includes('查看本次保存的输入'));assert.ok(html.includes(r.input.title));
 assert.equal(JSON.stringify(r.input),input);assert.notEqual(r.input.title,alert.title);
});
