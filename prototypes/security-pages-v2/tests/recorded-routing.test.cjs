'use strict';
/* Boot the unmodified app entry and follow its real hashchange/render path. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function boot(route,{saved=false}={}){
 const handlers=new Map(),app={innerHTML:''},writes=[];
 const s={window:{addEventListener(name,fn){handlers.set(name,fn);},scrollTo(){}},document:{activeElement:null,addEventListener(){},querySelector(selector){return selector==='#app'?app:null;},getElementById(){return null;}},location:{hash:route,search:''},localStorage:{getItem:()=>null,setItem:(...args)=>writes.push(args)},structuredClone,URLSearchParams,clearInterval};
 vm.createContext(s);
 const index=fs.readFileSync(path.join(root,'index.html'),'utf8'),scripts=[...index.matchAll(/<script defer src="\.\/([^"?]+)(?:\?[^\"]*)?"/g)].map(m=>m[1]);
 for(const file of scripts){
  if(file==='app.js'&&saved){const store=s.window.makeDemoData();s.window.mergeSocai2RecordedData(store);store.alerts.find(a=>a.sourceAlertId==='c6d50ea3-ec31-52e0-a92a-be45b626311b').owner='preserved-local-owner';s.localStorage.getItem=()=>JSON.stringify(store);}
  vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),s,{filename:file});
 }
 return {s,app,writes,index,navigate(hash){const oldURL='http://local.invalid/'+s.location.hash;s.location.hash=hash;handlers.get('hashchange')({oldURL,newURL:'http://local.invalid/'+hash});return app.innerHTML;}};
}
const prefix='socai2!local-standalone!local-maintenance-20261105c!fbe17036-51e4-5d28-a3de-8c93d1f8d634!';
const alertId=prefix+'alert!c6d50ea3-ec31-52e0-a92a-be45b626311b',caseId=prefix+'case!35d3008d-eb54-5be5-998c-08059359a750';
test('real app boot and hashchange show the c alert source score, ATT&CK and actual A/I/C links',()=>{
 const x=boot(`#/alerts/${alertId}/response`),originalData=JSON.stringify(x.s.window.socai2RecordedDataSets);
 for(const label of ['已保存的关联调查','告警分诊 A','事件诊断 I','案件调查 C','本地执行记录 · 合成输入'])assert.ok(x.app.innerHTML.includes(label),label);
 assert.ok(!x.app.innerHTML.includes('暂无 Run 记录'));
 let html=x.navigate(`#/alerts/${alertId}/overview`);
 assert.ok(html.includes('来源检测置信度 28.2/100'));assert.ok(html.includes('检测评分来源'));assert.ok(html.includes('fusion'));assert.ok(html.includes('Execution'));assert.ok(html.includes('T1059.001'));assert.ok(!html.includes('置信度 —/100'));
 html=x.navigate(`#/alerts/${alertId}/raw`);assert.ok(html.includes('28.199999999999996'));assert.ok(html.includes('confidence_state'));assert.ok(html.includes('available'));
 html=x.navigate(`#/cases/${caseId}/case-info`);const coverage=html.slice(html.indexOf('aria-label="ATT&CK 阶段覆盖"'));assert.match(coverage,/Execution[\s\S]*?<b>2<\/b> 条告警/);assert.ok(!coverage.includes('>未分类<'));assert.ok(html.includes('尚未形成案件级判断'));
 const data=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105c');
 assert.ok(data.alerts.every(a=>a.sourceRecord.category===null));assert.equal(JSON.stringify(x.s.window.socai2RecordedDataSets),originalData);assert.equal(x.writes.length,0);
 for(const file of ['alert-detail','socai2-recorded-import','investigation-workspace','app'])assert.ok(x.index.includes(`${file}.js?v=20261105-detection-routing-r1`));
});
test('persisted local records follow the same app route without losing identity or overwriting local edits',()=>{
 const x=boot(`#/alerts/${alertId}/response`,{saved:true});
 assert.ok(x.app.innerHTML.includes('已保存的关联调查'));assert.ok(!x.app.innerHTML.includes('暂无 Run 记录'));
 const html=x.navigate(`#/alerts/${alertId}/overview`);assert.ok(html.includes('preserved-local-owner'));assert.ok(html.includes('来源检测置信度 28.2/100'));assert.equal(x.writes.length,0);
 assert.ok(x.navigate(`#/cases/${caseId}/attack`).includes('本轮已完成的关系整理（汇总未通过）'));
 assert.ok(!x.navigate(`#/cases/${caseId}/case-info`).includes('模型原答（格式校验未通过，未采用）'));
 assert.equal(x.writes.length,0);
});
test('source detection states never borrow model confidence or infer tactics from category',()=>{
 const x=boot(`#/alerts/${alertId}/overview`),api=x.s.window.socai2RecordedImport;
 const actual=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105c').alerts.find(a=>a.sourceAlertId==='c6d50ea3-ec31-52e0-a92a-be45b626311b'),a=structuredClone(actual),before=JSON.stringify(actual);
 a.category='Execution';a.confidence=0.99;a.detailMaterial.confidence.score=99;
 Object.assign(a.detailMaterial.raw.material.detection,{confidence_state:'not_computed',confidence_value:28.2,tactics:[],techniques:[],labels_provided:false});
 const value=api.detectionView(a);assert.equal(value.score,null);assert.equal(value.confidenceState,'not_computed');assert.equal(value.tactics.length,0);assert.equal(value.techniques.length,0);
 a.detailMaterial.raw.material.id='wrong-material';assert.equal(api.detectionView(a).score,null);assert.equal(api.detectionView(a).tactics.length,0);
 assert.equal(JSON.stringify(actual),before);
});
test('Case fields and published Result remain separate from rejected C6 replies in execution records',()=>{
 const x=boot(`#/cases/${caseId}/case-info`),api=x.s.window.socai2RecordedImport,M=x.s.window.investigationWorkspaceModel;
 const data=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105c'),raw=data.runs.find(r=>r.investigationKind==='baseline'),before=JSON.stringify(data),r=M.normalizeRun(raw),preview=r.modelReplyPreview;
 assert.ok(preview);assert.equal(preview.validationError,'delivery_shape_invalid');assert.equal(r.status,'failed');assert.equal(r.sourceResult.conclusion,null);assert.equal(data.cases[0].assessment,null);
 assert.equal(r.savedGraphStageCompleted,true);assert.equal(r.savedGraphContext.nodes.length,12);assert.equal(r.savedGraphContext.edges.length,8);assert.equal(M.latestGraph([r]).id,r.id);assert.equal(M.latestFinished([r]),null);
 const graphModel=x.s.window.investigationGraphModel.build(r,{alerts:data.alerts},r.savedGraphContext);assert.equal(graphModel.nodes.length,12);assert.equal(graphModel.edges.length,8);assert.equal(graphModel.nodes.filter(n=>n.kind==='alert').length,2);
 assert.ok(!x.app.innerHTML.includes(preview.analysis.summary));assert.ok(!x.app.innerHTML.includes(preview.label));assert.ok(x.app.innerHTML.includes('尚未形成案件级判断'));
 assert.equal(api.caseDescription({...data.cases[0],description:'数据库保存的案件摘要'},[raw]),'数据库保存的案件摘要');
 assert.equal(api.caseDescription(data.cases[0],[raw]),'');
 assert.equal(r.outcome.conclusion,raw.outcome.conclusion);assert.deepEqual(r.findings,raw.findings);
 const overview=x.navigate(`#/cases/${caseId}/investigations?run=${raw.id}&view=overview`);
 assert.ok(overview.includes('失败'));assert.ok(overview.includes('系统交接：'));
 const process=x.navigate(`#/cases/${caseId}/investigations?run=${raw.id}&view=process`);assert.ok(process.includes(r.initialAnalysisPreview.summary));assert.ok(process.includes(preview.text));
 const report=x.navigate(`#/cases/${caseId}/investigations?run=${raw.id}&view=report`);assert.ok(!report.includes('已保存的系统交接报告'));assert.ok(report.includes('本轮保留结论'));
 const ledger=x.navigate(`#/cases/${caseId}/investigations?run=${raw.id}&view=ledger`);assert.ok(ledger.includes('delivery_shape_invalid'));
 const graph=x.navigate(`#/cases/${caseId}/attack`);assert.ok(graph.includes('本轮已完成的关系整理（汇总未通过）'));assert.ok(graph.includes('候选关联不表示已确认因果'));assert.ok(graph.includes('失败'));assert.ok(graph.includes('结束时间'));assert.ok(!graph.includes('没有已完成调查的关系投影'));
 assert.equal(JSON.stringify(data),before);assert.equal(x.writes.length,0);
 const b=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105b').runs.find(r=>r.investigationKind==='baseline');assert.equal(api.runView(b).modelReplyPreview,null);
});
test('readback does not use another Run output, an unfinished response, or a graph without its completed receipt',()=>{
 const x=boot(`#/cases/${caseId}/case-info`),api=x.s.window.socai2RecordedImport,raw=x.s.window.socai2RecordedDataSets.find(d=>d.provenance.batch_id==='local-maintenance-20261105c').runs.find(r=>r.investigationKind==='baseline');
 function editModel(change){const r=structuredClone(raw),s=r.steps.find(s=>s.sourceKind==='model'&&s.payload.stage_code==='C6'),a=r.artifacts.find(a=>a.id===s.storedOutputArtifactId);change(r,s,a);return api.runView(r);}
 assert.equal(editModel((r,s,a)=>a.sourceRecord.run_id='another-run').modelReplyPreview,null);
 assert.equal(editModel((r,s,a)=>r.artifactBodies[a.id].content.payload.raw.status='incomplete').modelReplyPreview,null);
 assert.equal(editModel((r,s,a)=>r.artifactBodies[a.id].content.payload.raw.output[0].content=[{type:'refusal',refusal:'not available'}]).modelReplyPreview,null);
 const r=structuredClone(raw);r.steps.find(s=>s.sourceKind==='graph'&&s.payload.stage_code==='C5').payload.step_status='failed';assert.equal(api.runView(r).savedGraphStageCompleted,false);
 const adopted=structuredClone(raw);adopted.sourceResult.conclusion_origin='model';adopted.outcome.conclusion='已发布的原始结论';assert.equal(api.runView(adopted).modelReplyPreview,null);assert.equal(api.runView(adopted).outcome.conclusion,'已发布的原始结论');
});
