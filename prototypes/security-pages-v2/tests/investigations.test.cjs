const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function load(version='v2'){
 const root=path.resolve(__dirname,'../../security-pages-'+version);
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/alerts'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 const files=['icons','data','replayed-alerts','alert-detail','workspace-model','workspace-view'];if(version==='v2')files.push('investigation-data','investigation-graph','investigation-workspace');
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
test('all saved Runs and six views render; no Case is invented or state mutated',()=>{
 const x=load(),rows=x.M.runs(x.store),before=JSON.stringify(x.store);assert.equal(rows.length,8);
 for(const r of rows)for(const view of ['overview','process','tools','graphs','ledger','report']){
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
test('incident summaries keep saved sources and do not lazily generate missing material',()=>{
 const x=load(),before=JSON.stringify(x.store);x.s.location.hash='#/incidents/262144/summary';
 const html=x.incidentPage();assert.ok(html.includes('基础研判'));assert.ok(html.includes('INV-20261024-001'));
 x.s.location.hash='#/incidents/262144/triage?filter=unknown';assert.ok(x.incidentPage().includes('尚无判定'));
 assert.equal(JSON.stringify(x.store),before);
 const a=x.store.alerts.find(a=>a.persistedRecord),rows=x.M.assessments(x.store,[a]),r=rows[0];
 assert.equal(r.explanation.summary,a.detailMaterial.explanation.summary);assert.equal(r.decision,'true_positive');
 assert.equal(r.triages[0].triage.confidence,.85);assert.equal(r.linked[0].verdict,'needs_review');
 x.store.incidents.push({...x.store.incidents[0],id:a.incidentId}); // Test-only parent; no persisted Incident was exported.
 x.s.location.hash=`#/incidents/${a.incidentId}/triage`;const actual=x.incidentPage();assert.ok(actual.includes('分诊评分 85'));assert.ok(actual.includes('查看来源'));assert.ok(!actual.includes('分诊评分 75'));
});
test('coverage counts alerts once across multiple Runs and does not spread Run verdicts',()=>{
 const x=load(),members=x.store.alerts.filter(a=>a.incidentId==='262144'),first=members[0];
 x.s.window.savedInvestigationRuns.push({id:'multi',alertIds:[first.id,members[1].id],completion:'partial',verdict:'needs_review',triage:{verdict:'true_positive',confidence:1}});
 const rows=x.M.assessments(x.store,members),r=rows.find(r=>r.alert.id===first.id),c=x.M.coverage(rows);
 assert.equal(r.linked.length,2);assert.equal(r.decision,null);assert.equal(r.triages.length,0);assert.equal(r.needsReview,true);
 assert.equal(c.investigated,6);assert.equal(c.decided,0);assert.equal(c.unknown,members.length);
});
test('basic investigation filters retain only matching alert rows without mutations',()=>{
 const x=load(),members=x.store.alerts.filter(a=>a.incidentId==='262144'),decided=members[0];decided.disposition='false_positive';
 const before=JSON.stringify(x.store);x.s.location.hash='#/incidents/262144/triage?filter=decided';
 const html=x.investigationView.basicInvestigations();assert.ok(html.includes(`#/alerts/${decided.id}/overview`));
 assert.ok(!html.includes(`#/alerts/${members[1].id}/overview`));assert.equal(JSON.stringify(x.store),before);
 x.s.location.hash='#/incidents/262144/triage?filter=unknown';assert.ok(!x.investigationView.basicInvestigations().includes(`#/alerts/${decided.id}/overview`));
});
test('Case input evidence follows Run inputs rather than newly added members',()=>{
 const x=load(),r=x.M.runs(x.store)[0],before=JSON.stringify(r),ids=new Set(r.alertIds);
 const expected=x.store.evidence.filter(e=>ids.has(e.alertId)).map(e=>e.id).sort();
 x.store.cases[0].alertIds=x.store.alerts.map(a=>a.id);
 assert.deepEqual(x.M.inputEvidence(x.store,r).map(e=>e.id).sort(),expected);assert.equal(JSON.stringify(r),before);
 x.s.location.hash='#/cases/17420/overview';const html=x.casePage();assert.ok(html.includes('输入告警携带的证据'));assert.ok(!html.includes('AI 已采用证据'));
});
test('recorded stages and ledger filters expose existing work without inventing roles',()=>{
 const x=load(),r=x.s.window.savedInvestigationRuns[0];x.s.location.hash=`#/investigations/${r.id}/process`;
 const phases=x.investigationView.workbench();assert.ok(phases.includes('上下文补充'));assert.ok(phases.includes(r.depth.strategy_id));assert.ok(phases.includes('调查截断'));assert.ok(!phases.includes('取证分析 · Forensic'));
 x.s.location.hash=`#/investigations/${r.id}/ledger?kind=tool_call&agent=deep-investigator`;
 const html=x.investigationView.workbench(),bodies=html.slice(html.indexOf('<div class="iv-timeline">'));
 assert.equal((bodies.match(/class="iv-step"/g)||[]).length,r.steps.filter(s=>s.kind==='tool_call'&&s.name==='deep-investigator').length);
 assert.ok(bodies.includes('process_activity'));assert.ok(!bodies.includes("graph node &#39;triage&#39; completed"));
 x.s.location.hash=`#/investigations/${r.id}/ledger?kind=missing`;assert.ok(x.investigationView.workbench().includes('没有符合筛选条件的记录'));
});
test('switching Run keeps the detail section and graph filters keep distinct saved statuses',()=>{
 const x=load();x.s.location.hash='#/cases/17420/investigations?run=INV-20261024-001&view=process';
 x.investigationView.change({value:'INV-20261024-002',hasAttribute:k=>k==='data-iv-run'});
 assert.equal(x.s.location.hash,'#/cases/17420/investigations?run=INV-20261024-002&view=process');
 const r=x.s.window.savedInvestigationRuns[0];x.s.location.hash=`#/investigations/${r.id}/graphs?graph=attack_path`;
 const html=x.investigationView.workbench();assert.ok(html.includes('未关联 Case'));assert.ok(!html.includes('图可达实体'));
 x.s.location.hash=`#/investigations/${r.id}/ledger`;x.investigationView.change({value:'tool_call',hasAttribute:k=>k==='data-iv-kind'});
 assert.equal(x.s.location.hash,`#/investigations/${r.id}/ledger?kind=tool_call`);
});

test('event overview retains the original tactic, timeline and evidence summaries',()=>{
 const x=load();x.s.location.hash='#/incidents/262144/summary';assert.ok(x.incidentPage().includes('#/incidents/262144/context'));
 x.s.location.hash='#/incidents/262144/context';const html=x.incidentPage();for(const label of ['告警与攻击阶段','MITRE ATT&CK 阶段','告警时间线','事件信息','相关威胁与标签','查看证据'])assert.ok(html.includes(label));
});
