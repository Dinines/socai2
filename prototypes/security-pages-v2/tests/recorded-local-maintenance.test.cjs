'use strict';
/* Readback checks for the preserved actual failed local batch; never an acceptance-success fixture. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),file='socai2-recorded-local-maintenance-20261105a-r2.js';
function load(){
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/cases',search:''},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 const index=fs.readFileSync(path.join(root,'index.html'),'utf8'),scripts=[...index.matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(m=>m[1]);
 for(const f of scripts.filter(f=>f!=='app.js'))vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),s);
 const code=fs.readFileSync(path.join(root,'app.js'),'utf8').replace('readQueueLink();render();\n})();','window.api={store,casePage,caseQueueRows,fullAlert,investigationView,shell,scopeActivities,activitiesView,drawerMarkup,ui};\n})();');vm.runInContext(code,s);
 const data=s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105a');
 return {...s.window.api,s,data,M:s.window.investigationWorkspaceModel};
}
test('actual batch is the immutable 2-alert, 4-Run failed readback with 64 Run and 2 Fusion source artifacts',()=>{
 const x=load(),d=x.data,c=d.cases[0],r=d.runs.find(r=>r.investigationKind==='baseline');
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex'),'e588e96443ca9017053a961d272c2fdd0a990086e6d4c12ac882e8cea4f4bf37');
 assert.equal(d.provenance.source_sha256,'9094962fea7ab761761dbad11052fbe744e7a42a6f3a9961e7a76fdeec309bdf');
 assert.equal(d.alerts.length,2);assert.equal(d.incidents.length,1);assert.equal(d.runs.length,4);assert.equal(d.runs.reduce((n,r)=>n+r.calls,0),5);assert.equal(d.runs.reduce((n,r)=>n+r.artifacts.length,0),64);assert.equal(d.sourceArtifacts.length,2);
 assert.equal(c.assessment,null);assert.equal(c.tasks.length,0);assert.equal(r.status,'failed');assert.equal(r.completion,'partial');assert.equal(r.stop,'delivery_shape_invalid');assert.equal(r.sourceResult.conclusion,null);assert.equal(r.sourceResult.conclusion_origin,'system');assert.match(r.outcome.conclusion,/^系统交接：/);
 for(const a of d.alerts){assert.equal(a.detailMaterial.raw.source_artifacts.length,1);assert.equal(a.detailMaterial.raw.source_artifacts[0].run_id,null);}
 for(const other of d.runs.filter(row=>row.investigationKind!=='baseline'))assert.equal(other.status,'completed');
});
test('original index and five reading tabs expose failure, saved artifacts and absence of current judgment/H',()=>{
 const x=load(),d=x.data,c=x.store.cases.find(c=>c.id===d.cases[0].id),r=x.M.runs(x.store).find(r=>r.sourceRunId==='6c83b3d9-8428-4e15-ba8e-6b4dc22d80c6'),before=JSON.stringify(x.store);
 for(const run of d.runs)for(const view of ['overview','process','tools','graphs','report','ledger']){
  x.s.location.hash=`#/cases/${c.id}/investigations?run=${run.id}&view=${view}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html),run.sourceRunId+':'+view);
  for(const title of ['调查发现','AI 分析','查询与证据','调查关系图','报告与响应'])assert.ok(html.includes(title),title);
  if(run.id===r.id&&view==='overview'){assert.ok(html.includes('系统交接：'));assert.ok(html.includes('delivery_shape_invalid'));assert.ok(html.includes('失败'));assert.ok(html.includes('C5 关系整理'));assert.ok(html.includes('C6 最终汇总'));assert.ok(!html.includes('分析判断'))}
 }
 x.s.location.hash=`#/cases/${c.id}/case-info`;let html=x.casePage();assert.ok(html.includes('尚未形成案件级判断'));assert.ok(html.includes('2 条当前成员告警尚无有效调查结论覆盖'));assert.ok(!html.includes('尚未纳入已结束的调查'));assert.ok(html.slice(html.indexOf('Case 详细信息')).includes('9853f139-dade-5906-a4e4-b422ebc550c0'));assert.ok(!html.includes('本轮调查依据未变化'));
 x.s.location.hash=`#/cases/${c.id}/investigations`;html=x.casePage();assert.equal(x.M.forCase(x.store,c)[0].id,r.id);assert.ok(!html.includes('&quot;counterevidence&quot;'));assert.ok(html.includes('两成员共享主机'));
 x.s.location.hash=`#/cases/${c.id}/tasks`;html=x.casePage();assert.ok(html.includes('暂无人工任务事项'));assert.ok(!html.includes('cw-task-result'));
 x.s.location.hash=`#/cases/${c.id}/attack`;html=x.casePage();assert.ok(html.includes('本轮已完成的关系整理（汇总未通过）'));assert.ok(html.includes('C5 已保存投影'));assert.ok(!html.includes('cx-toolbar'));
 for(const a of d.alerts){x.s.location.hash=`#/alerts/${a.id}/raw`;html=x.fullAlert(x.store.alerts.find(row=>row.id===a.id));assert.ok(html.includes('fusion.first-result.v1'));}
 for(const [page,id] of [['cases',c.id],['alerts',d.alerts[0].id],['incidents',d.incidents[0].id],['investigations',r.id]]){x.s.location.hash=`#/${page}/${id}`;assert.ok(x.shell('').includes('本地执行记录 · 合成输入'));assert.ok(!x.shell('').includes('本地预览 · Contoso'));}
 x.s.location.hash=`#/cases/${x.store.cases.find(row=>!row.recordedImport).id}`;assert.ok(x.shell('').includes('本地预览 · Contoso'));
 assert.equal(JSON.stringify(x.store),before);assert.ok(x.store.cases.length>1);assert.equal(x.caseQueueRows().find(row=>row.id===c.id).status,'New');
});

test('actual b range rejection appends independently and explains why its proposed query did not execute',()=>{
 const x=load(),d=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105b'),c=x.store.cases.find(c=>c.id===d.cases[0].id),r=x.M.forCase(x.store,c).find(r=>r.investigationKind==='baseline');
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'socai2-recorded-local-maintenance-20261105b.js'))).digest('hex'),'39132934feb5c489a4f66bc44181fa5b734ed61350d4a5bf202683ef3768fa25');
 assert.equal(d.provenance.source_sha256,'a5fa1c0470150cbc7d8193c32b5be2db81ebd69c4dc6b47f9dd376a9f586882c');
 assert.equal(d.alerts.length,2);assert.equal(d.runs.length,4);assert.equal(d.runs.reduce((n,r)=>n+r.calls,0),4);assert.equal(d.runs.reduce((n,r)=>n+r.artifacts.length,0),54);assert.equal(d.sourceArtifacts.length,2);
 assert.equal(c.assessment,null);assert.equal(c.tasks.length,0);assert.equal(r.status,'failed');assert.equal(r.stop,'no_accepted_main_analysis');assert.equal(r.sourceResult.conclusion,null);assert.equal(r.sourceResult.conclusion_origin,'system');assert.ok(r.steps.some(s=>s.payload?.error?.code==='followup_binding_object_mismatch'));assert.ok(!r.steps.some(s=>s.sourceKind==='tool'&&String(s.payload.stage_code).startsWith('C4')));
 assert.ok(x.store.cases.some(c=>c.id===x.data.cases[0].id));assert.ok(!x.M.forCase(x.store,c).some(r=>x.data.runs.some(a=>a.id===r.id)));
 const before=JSON.stringify(x.store);
 for(const view of ['overview','process','tools','graphs','report','ledger']){x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=${view}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html),view);if(['overview','process'].includes(view))assert.ok(html.includes('模型建议的查询范围与允许范围不一致，未执行该建议的查询。'));if(view==='overview')assert.ok(html.includes('系统交接：'));if(view==='ledger')assert.ok(html.includes('followup_binding_object_mismatch'));}
 x.s.location.hash=`#/cases/${c.id}/case-info`;assert.ok(x.casePage().includes('尚未形成案件级判断'));x.s.location.hash=`#/cases/${c.id}/tasks`;assert.ok(x.casePage().includes('暂无人工任务事项'));
 assert.equal(JSON.stringify(x.store),before);
});

test('recorded material counts, merged activities and alert links keep their source meaning',()=>{
 const x=load(),before=JSON.stringify(x.store);
 for(const d of x.s.window.socai2RecordedDataSets){
  const c=x.store.cases.find(row=>row.id===d.cases[0].id);
  x.s.location.hash=`#/cases/${c.id}/case-info`;let html=x.casePage();
  assert.ok(html.includes('独立证据条目'));assert.ok(html.includes('2 份原始告警材料与 2 份来源快照'));
  x.s.location.hash=`#/cases/${c.id}/activities`;const rows=x.scopeActivities(),steps=d.runs.reduce((n,r)=>n+r.steps.length,0);
  assert.equal(rows.length,d.activities.length+steps+2);assert.equal(rows.filter(a=>a.recordedImport).length,d.activities.length);assert.equal(rows.filter(a=>a.runId).length,steps);
  html=x.activitiesView();assert.ok(html.includes(`${d.activities.length} 条数据库活动 + ${steps} 条调查步骤投影 + 2 条告警发生记录`));
  for(const row of rows.filter(a=>a.recordedImport)){
   assert.equal(row.status,'Recorded');assert.ok(row.performedBy!=='未记录');x.ui.drawer={type:'activity',id:row.id};html=x.drawerMarkup();assert.ok(html.includes('数据库活动原件'));assert.ok(html.includes(row.sourceRecord.id));
  }
  for(const asset of d.assets){x.ui.drawer={type:'entity',id:asset.id};html=x.drawerMarkup();assert.ok(html.includes('源对象尚未核对库存'));assert.ok(html.includes('去重对象的来源记录'));assert.ok(!html.includes('未关联库存'));}
  x.ui.drawer=null;
  for(const a of d.alerts){
   const alert=x.store.alerts.find(row=>row.id===a.id);
   x.s.location.hash=`#/alerts/${a.id}/response`;html=x.fullAlert(alert);assert.ok(!html.includes('暂无 Run'));for(const label of ['告警分诊 A','事件诊断 I','案件调查 C'])assert.ok(html.includes(label),label);
   x.s.location.hash=`#/alerts/${a.id}/overview`;html=x.fullAlert(alert);
   if(a.sourceRecord.latest_explanation_id){assert.ok(html.includes('已保存的告警解释'));assert.ok(html.includes('解释原件与来源引用'));assert.ok(!html.includes('暂无解释内容'));}
   else{assert.ok(!html.includes('已保存的告警解释'));assert.ok(html.includes('暂无解释内容'));}
   assert.ok(!html.includes('Contoso'));assert.ok(html.includes(a.sourceAlertId));assert.ok(!html.includes('data-detail-form="feedback"'));
  }
 }
 assert.equal(JSON.stringify(x.store),before);
});

test('actual c appends C3 completion, two saved lake queries and rejected C6 without adopting its intermediate analysis',()=>{
 const x=load(),d=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105c'),c=x.store.cases.find(c=>c.id===d.cases[0].id),r=x.M.forCase(x.store,c).find(r=>r.investigationKind==='baseline');
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'socai2-recorded-local-maintenance-20261105c.js'))).digest('hex'),'809d5212bcbd37b9029082507c4271524518a8bb0ad275bd245122766f812a4e');
 assert.equal(d.provenance.source_sha256,'0870161383dc891edf54319f629ecf972b09e83b48495fadb96470546ff46f3b');
 assert.equal(d.alerts.length,2);assert.equal(d.incidents.length,1);assert.equal(d.runs.length,4);assert.equal(d.runs.reduce((n,r)=>n+r.calls,0),5);assert.equal(d.runs.reduce((n,r)=>n+r.artifacts.length,0),67);assert.equal(d.sourceArtifacts.length,2);assert.equal(d.runs.reduce((n,r)=>n+r.steps.length,0),29);
 assert.equal(c.assessment,null);assert.equal(c.tasks.length,0);assert.equal(r.status,'failed');assert.equal(r.stop,'delivery_shape_invalid');assert.equal(r.sourceResult.conclusion,null);assert.equal(r.sourceResult.conclusion_origin,'system');
 assert.ok(r.steps.some(s=>s.payload.stage_code==='C3'&&s.sourceKind==='stage'&&s.payload.step_status==='completed'));
 assert.ok(r.steps.some(s=>s.payload.stage_code==='C6'&&s.sourceKind==='model'&&s.payload.error?.code==='delivery_shape_invalid'));
 const queries=r.tools.filter(t=>t.sourceRecord.stage_code==='C4.query');assert.equal(queries.length,2);assert.deepEqual(Array.from(queries.map(t=>t.name).sort()),['network_connections','process_activity']);for(const t of queries){assert.equal(t.sourceRecord.state,'completed');assert.equal(JSON.parse(t.result).returned_rows,1);assert.equal(t.args.scope.kind,'whole_case');}
 assert.ok(x.s.window.socai2RecordedDataSets.length>=3);for(const prior of x.s.window.socai2RecordedDataSets.filter(other=>other!==d)){assert.ok(x.store.cases.some(c=>c.id===prior.cases[0].id));assert.ok(!x.M.forCase(x.store,c).some(r=>prior.runs.some(p=>p.id===r.id)));}
 const before=JSON.stringify(x.store);
 for(const run of d.runs)for(const view of ['overview','process','tools','graphs','report','ledger']){x.s.location.hash=`#/cases/${c.id}/investigations?run=${run.id}&view=${view}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html),run.sourceRunId+':'+view);if(run.id===r.id&&['overview','process'].includes(view))assert.ok(html.includes('模型最终输出未通过格式校验，未形成可采用结论。'));if(run.id===r.id&&view==='overview')assert.ok(html.includes('系统交接：'));if(run.id===r.id&&view==='ledger')assert.ok(html.includes('delivery_shape_invalid'));}
 x.s.location.hash=`#/cases/${c.id}/case-info`;assert.ok(x.casePage().includes('尚未形成案件级判断'));x.s.location.hash=`#/cases/${c.id}/tasks`;assert.ok(x.casePage().includes('暂无人工任务事项'));assert.equal(JSON.stringify(x.store),before);
});

test('current Case reads persisted business fields while failure diagnostics and H remain in their own records',()=>{
 const x=load(),sets=x.s.window.socai2RecordedDataSets;
 const d=sets.find(row=>row.provenance.batch_id==='local-maintenance-20261105d'),dc=x.store.cases.find(c=>c.id===d.cases[0].id);
 assert.equal(dc.description,dc.sourceRecord.description);assert.equal(dc.assessment.conclusion,dc.assessment.sourceRecord.assessment.conclusion);
 assert.ok(dc.assessment.conclusion.startsWith('案件性质待核实。'));assert.ok(!dc.assessment.conclusion.includes('原因：'));assert.equal(dc.assessment.alertIds.length,0);
 assert.ok(d.runs.some(r=>r.stop==='delivery_shape_invalid'&&r.sourceResult?.conclusion.includes('原因：')));
 x.s.location.hash=`#/cases/${dc.id}/case-info`;assert.ok(!x.casePage().includes('模型回复未通过格式校验'));
 const g=sets.find(row=>row.provenance.batch_id==='local-maintenance-20261105g'),gc=x.store.cases.find(c=>c.id===g.cases[0].id);
 const accepted=g.runs.find(r=>r.sourceResult?.conclusion_origin==='model'),later=g.runs.find(r=>r.stop==='model_view_not_ready');
 assert.ok(accepted&&later);assert.equal(gc.assessment.conclusion,accepted.sourceResult.conclusion);assert.equal(gc.assessment.alertIds.length,2);
 assert.equal(gc.assessment.sourceRunIds[0],accepted.id);assert.notEqual(gc.assessment.inputFreshness.state,'current');
 assert.equal(gc.tasks.length,1);assert.equal(gc.tasks[0].status,'Completed');assert.equal(gc.tasks[0].referenceContext.alertIds.length,1);
 x.s.location.hash=`#/cases/${gc.id}/case-info`;const html=x.casePage();assert.ok(html.includes(gc.description));assert.ok(html.includes(gc.assessment.conclusion));assert.ok(!html.includes('汇总所需的材料视图尚不可用'));
 x.s.location.hash=`#/cases/${gc.id}/investigations?run=${later.id}&view=ledger`;assert.ok(x.casePage().includes('model_view_not_ready'));
});
