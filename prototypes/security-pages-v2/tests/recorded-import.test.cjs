'use strict';
/* Explicit unit-only records. These are never loaded by index.html or exported as acceptance data. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {adaptExport,merge}=require('../socai2-recorded-import.js');
const root=path.resolve(__dirname,'..');
const stamp='2026-11-05T03:00:00.123456Z';
const manifest={schema_version:'socai2.page-export.v1',batch_id:'unit-only',source_environment:'local-unit',exported_at:stamp,source_sha256:'a'.repeat(64),input_kind:'synthetic'};
function fixture(){
 const row=(id,rest={})=>({id,tenant_id:'tenant-unit',...rest});
 const alert=id=>row(id,{title:'Unit alert '+id,severity:id==='a1'?'critical':'high',handling_status:'new',assignment_state:'unassigned',event_time:stamp,ingested_at:stamp,tags:[]});
 const scope={kind:'whole_case',alert_ids:['a1'],object_keys:[],window_start:null,window_end:null,limitations:[]};
 const revision=(id,n,text)=>row(id,{task_id:'h1',case_id:'c1',revision:n,title:'Unit human '+n,state:'completed',result_text:text,result_scope:scope,completed_at:stamp,completed_by:'actual-completer',changed_at:stamp,changed_by:'metadata-editor'});
 const h1=revision('h-v1',1,'Earlier frozen statement'),h2=revision('h-v2',2,'Current human statement');
 const run=(id,kind,state='completed')=>row(id,{kind,state,case_id:kind==='baseline'?'c1':null,alert_id:kind==='alert_basic'?'a1':null,incident_id:kind==='incident_diagnosis'?'i1':null,title:'Unit Run '+id,started_at:state==='pending_update'?null:stamp,requested_at:stamp,ended_at:state==='completed'?stamp:null,delivery_state:state==='completed'?'partial':'none',input_artifact_id:id+'-input',purpose:'Unit check only'});
 const runs=[run('ra','alert_basic'),run('ri','incident_diagnosis'),run('rc','baseline'),run('ru','baseline','unknown'),run('rp','baseline','pending_update')];
 const artifact=(id,run_id,kind,content_json,schema_version='unit')=>row(id,{run_id,case_id:run_id==='rc'?'c1':null,kind,content_json,content_text:null,captured_at:stamp,sha256:'b'.repeat(64),size_bytes:42,schema_version});
 const frozenMember={alert:alert('a1'),material:null,objects:[],triage:null};
 const artifacts=runs.map(r=>artifact(r.id+'-input',r.id,'input_snapshot',r.kind==='baseline'?{scope:{alert_ids:['a1']}}:{members:[frozenMember]}));
 artifacts.push(artifact('context','rc','source_snapshot',{case_id:'c1',captured_at:stamp,alerts:{a1:frozenMember},tasks:{h1:{task_id:'h1',revision:h1,usable_feedback:true,limitations:[]}}},'socai2.baseline-context.v1'));
 artifacts.push(artifact('graph','rc','alert_graph',{nodes:[{id:'n1',type:'alert',label:'Frozen unit alert',alert_ids:['a1']},{id:'n2',type:'host',label:'Frozen unit host',alert_ids:['a1']}],edges:[{id:'e1',from:'n1',to:'n2',relation:'associated_with',strength:'candidate',source_refs:[]}],limitations:['Unit candidate only']},'socai2.baseline-graph.v1'));
 artifacts.push(artifact('tool-input','rc','tool_request',{tool_name:'unit_query'}));
 artifacts.push(artifact('tool-output','rc','tool_response',{tool_name:'unit_query',state:'unavailable',rows:[],reason:'Unit unavailable'}));
 artifacts.push(artifact('missing-body','rc','model_response',null));
 const result=row('res1',{case_id:'c1',source_run_id:'rc',kind:'baseline',conclusion_origin:'model',conclusion:'Unit saved conclusion',findings:[{state:'unresolved',statement:'Unit question remains'}],questions:[],recommendations:[{id:'rec',action_type:'unit-action',targets:[{object_key:'host:unit',display_name:'unit host'}],reason:'Unit reason',approval_requirement:'unknown'}],case_impact:{summary:'Unit saved impact',cannot_generalize:[]},delivery_state:'partial'});
 return {alerts:[alert('a1'),alert('a2')],alert_materials:[],alert_objects:[],alert_source_refs:[],alert_assessments:[row('triage1',{alert_id:'a1',kind:'triage',source_run_id:'ra',verdict:'needs_review',confidence:.4,rationale:'Unit A rationale'})],incidents:[row('i1',{title:'Unit incident',handling_status:'new',assignment_state:'assigned',owner_id:'owner',priority_state:'available',priority_value:'42.5',created_at:stamp,tags:[]})],incident_alerts:[row('ia1',{incident_id:'i1',alert_id:'a1'})],incident_diagnoses:[row('diag1',{incident_id:'i1',source_run_id:'ri',summary:'Unit I summary',diagnosis:{findings:[]}})],cases:[row('c1',{title:'Unit Case',severity:'critical',handling_status:'new',assignment_state:'unassigned',tags:[],scope_revision:1,current_assessment_id:'judge1',created_at:stamp,business_updated_at:stamp})],case_alerts:[row('ca1',{case_id:'c1',alert_id:'a1'}),row('ca2',{case_id:'c1',alert_id:'a2'})],case_incidents:[row('ci1',{case_id:'c1',incident_id:'i1'})],runs,run_members:[row('rm1',{run_id:'rc',case_id:'c1',alert_id:'a1'})],run_steps:[row('s1',{run_id:'rc',seq:1,kind:'stage',stage_code:'C1',name:'Freeze',state:'completed',started_at:stamp,ended_at:stamp}),row('m1',{run_id:'rc',seq:2,kind:'model',name:'C3',state:'completed',usage:{usage_state:'reported',total_tokens:12,cost_state:'unknown'},started_at:stamp,ended_at:stamp}),row('m2',{run_id:'ru',seq:1,kind:'model',name:'C3',state:'unknown',usage:{usage_state:'unknown'},started_at:stamp}),row('t1',{run_id:'rc',seq:3,kind:'tool',name:'Unit query',state:'completed',input_artifact_id:'tool-input',output_artifact_id:'tool-output',started_at:stamp,ended_at:stamp})],artifacts,results:[result],result_members:[row('rmem1',{case_id:'c1',result_id:'res1',run_id:'rc',alert_id:'a1',conclusion_covered:true})],tasks:[row('h1',{case_id:'c1',current_revision_id:'h-v2',created_at:stamp,origin_result_id:'res1'})],task_revisions:[h1,h2],case_assessments:[row('judge1',{case_id:'c1',conclusion:'Unit explicitly adopted judgment',formed_at:stamp,adopted_by:'actual-user'})],case_assessment_sources:[row('src1',{case_id:'c1',assessment_id:'judge1',result_id:'res1'}),row('src2',{case_id:'c1',assessment_id:'judge1',task_revision_id:'h-v1'})],case_assessment_members:[row('cov1',{case_id:'c1',assessment_id:'judge1',alert_id:'a1'})],activities:[]};
}
function responses(db,state='stale'){return [{method:'GET',path:'/api/v1/socai2/cases/c1',status:200,body:{case:{id:'c1',current_assessment_id:'judge1'},current_assessment:{value:{id:'judge1'},input_freshness:{state,reasons:['human_feedback_changed']}}}}];}
function adapted(){const db=fixture();return {db,data:adaptExport(db,manifest,responses(db))};}
function load(data){
 const s={window:{addEventListener(){}},document:{addEventListener(){}},location:{hash:'#/cases'},localStorage:{getItem:()=>null},structuredClone,URLSearchParams,clearInterval};vm.createContext(s);
 for(const name of ['icons','workspace-layout','data','replayed-alerts','alert-detail','workspace-model','workspace-view','investigation-data','alert-flow-workspace','investigation-graph','investigation-workspace','case-workflow','case-assistant','socai2-recorded-import'])vm.runInContext(fs.readFileSync(path.join(root,name+'.js'),'utf8'),s);
 s.window.socai2RecordedData=structuredClone(data);
 const code=fs.readFileSync(path.join(root,'app.js'),'utf8').replace('readQueueLink();render();\n})();','window.api={store,ui,casePage,incidentPage,fullAlert,investigationView,caseWorkflow,caseQueueRows,drawerMarkup};\n})();');
 vm.runInContext(code,s);return {...s.window.api,s,M:s.window.investigationWorkspaceModel};
}
test('persisted page-data examples retain zero, missing, sources and current judgments in the original views',()=>{
 const s={window:{}};vm.createContext(s);vm.runInContext(fs.readFileSync(path.join(root,'socai2-recorded-page-data-20261106.js'),'utf8'),s);
 const data=s.window.socai2RecordedData,x=load(data);
 for(const c of data.cases){
  const q=x.caseQueueRows().find(r=>r.id===c.id),v=c.pageData.evidence;
  assert.equal(q.threatCount,v.threat_count);assert.equal(q.determination,c.assessment?.conclusion||'未设置');
  x.ui.caseId=c.id;x.s.location.hash='#/cases/'+c.id+'/case-info';
  const html=x.casePage();assert.ok(html.includes('独立证据条目'));assert.ok(html.includes(c.assessment?.conclusion||'尚未形成案件级判断'));
  const es=x.store.evidence.filter(e=>e.caseId===c.id);assert.equal(es.length,v.entries.length);
  for(const e of es){assert.ok(e.sourceRefs.length);assert.equal(e.indexArtifactId,v.artifact_id);assert.ok(e.alertIds.every(a=>c.alertIds.includes(a)));}
 }
 assert.deepEqual(Array.from(data.cases,c=>c.pageData.evidence.threat_count),[0,1,0,null]);
 assert.equal(data.runs.length,0);
});
test('old exports use the adopted judgment and never inherit incident classification or invent threat counts',()=>{
 const {data}=adapted();data.incidents[0].classification='True positive';delete data.cases[0].determination;
 const x=load(data),row=x.caseQueueRows().find(c=>c.id===data.cases[0].id);
 assert.equal(row.determination,'Unit explicitly adopted judgment');assert.equal(row.classification,'Not set');assert.equal(row.threatCount,null);
});
test('page-data companions reject snapshot, pointer and current-judgment mismatches',()=>{
 const db=fixture(),cas=db.cases[0];cas.row_version=3;
 const page={tenant_id:cas.tenant_id,case_id:cas.id,case_row_version:3,current_assessment_id:cas.current_assessment_id,page_data:{schema_version:'socai2.case-page-data.v1',classification:null,due_at:null,determination:'Unit explicitly adopted judgment',evidence:{artifact_id:null,entries:[],evidence_count:null,threat_count:null,state:'not_recorded'}}};
 assert.equal(adaptExport(db,manifest,[],[page]).cases[0].pageData.determination,page.page_data.determination);
 for(const change of ['version','pointer','determination']){
  const wrong=structuredClone(page);
  if(change==='version')wrong.case_row_version=2;
  if(change==='pointer')wrong.page_data.evidence.artifact_id='other-index';
  if(change==='determination')wrong.page_data.determination='Not adopted';
  assert.throws(()=>adaptExport(db,manifest,[],[wrong]),/mismatch/);
 }
 cas.current_evidence_artifact_id='saved-index';assert.throws(()=>adaptExport(db,manifest),/case_evidence_projection_missing/);
});
test('unit export preserves identities, original values, critical/priority and unknown approval',()=>{
 const db=fixture(),before=JSON.stringify(db),d=adaptExport(db,manifest,responses(db));
 assert.equal(JSON.stringify(db),before);assert.equal(d.alerts[0].severity,'严重');assert.equal(d.incidents[0].priority,42.5);assert.equal(d.runs.find(r=>r.sourceRunId==='rc').actions[0].requires_approval,null);
 assert.equal(encodeURIComponent(d.cases[0].id),d.cases[0].id);assert.ok(d.cases[0].id.startsWith('socai2!'));
 const other=adaptExport(db,{...manifest,batch_id:'other'});assert.notEqual(other.cases[0].id,d.cases[0].id);assert.notEqual(other.runs[0].id,d.runs[0].id);
});
test('current judgment uses only explicitly adopted source and matched Case GET freshness',()=>{
 const {db,data:d}=adapted(),c=d.cases[0];assert.equal(c.assessment.conclusion,'Unit explicitly adopted judgment');assert.equal(c.assessment.inputFreshness.state,'stale');assert.equal(c.assessment.taskIds.length,1);assert.equal(c.assessment.sourceRunIds.length,1);
 db.case_input_freshness=[{tenant_id:'tenant-unit',case_id:'c1',state:'current',reasons:[]}];assert.equal(adaptExport(db,manifest).cases[0].assessment.inputFreshness,null);
 const bad=responses(db);bad[0].body.current_assessment.value.id='other';assert.throws(()=>adaptExport(db,manifest,bad),/case_api_assessment_mismatch/);
 db.cases[0].current_assessment_id=null;assert.equal(adaptExport(db,manifest).cases[0].assessment,null);
});
test('H current version and historical frozen statement are distinct and retain exact scope timestamps',()=>{
 const {data:d}=adapted(),t=d.cases[0].tasks[0],r=d.runs.find(r=>r.sourceRunId==='rc');assert.equal(t.result,'Current human statement');assert.equal(t.revisionHistory.length,2);assert.equal(r.referenceSnapshot.tasks[0].result,'Earlier frozen statement');
 assert.equal(t.completedAt,stamp);assert.equal(t.completedBy,'actual-completer');assert.equal(t.changedBy,'metadata-editor');assert.equal(t.resultScope.window_start,null);assert.deepEqual(t.resultScope.object_keys,[]);
 t.result='local edit';assert.equal(r.referenceSnapshot.tasks[0].result,'Earlier frozen statement');
});
test('system closing can link an unknown Run through its report artifact without claiming coverage',()=>{
 const db=fixture();db.case_assessment_members=[];
 db.case_assessments[0]={...db.case_assessments[0],origin:'system',validity:'system_only',conclusion:'系统收尾：调用状态待核，无法判定。'};
 db.artifacts.push({id:'closing',tenant_id:'tenant-unit',case_id:'c1',run_id:'ru',kind:'report_json',content_json:{conclusion:db.case_assessments[0].conclusion}});
 db.case_assessment_sources=[{id:'system-source',tenant_id:'tenant-unit',case_id:'c1',assessment_id:'judge1',artifact_id:'closing'}];
 const data=adaptExport(db,manifest,responses(db,'current')),judgment=data.cases[0].assessment;
 assert.equal(judgment.conclusion,db.case_assessments[0].conclusion);assert.deepEqual(judgment.alertIds,[]);
 assert.deepEqual(judgment.sourceRunIds,[data.runs.find(r=>r.sourceRunId==='ru').id]);
 assert.equal(data.runs.find(r=>r.sourceRunId==='ru').status,'unknown');
 db.artifacts.at(-1).case_id='another-case';assert.throws(()=>adaptExport(db,manifest),/case_assessment_source_mismatch/);
});
test('A/I/C remain distinct Runs; pending, unknown usage, partial and missing bodies stay honest',()=>{
 const {data:d}=adapted();assert.equal(d.runs.length,5);assert.equal(d.runs.find(r=>r.sourceRunId==='ri').alertIds.length,1);assert.equal(d.runs.find(r=>r.sourceRunId==='rc').completion,'partial');
 const unknown=d.runs.find(r=>r.sourceRunId==='ru'),pending=d.runs.find(r=>r.sourceRunId==='rp');assert.equal(unknown.tokens,null);assert.equal(unknown.unknownTokenCalls,1);assert.equal(pending.status,'pending_update');assert.equal(pending.started,null);
 const r=d.runs.find(r=>r.sourceRunId==='rc');assert.equal(r.tools[0].savedState,'unavailable');assert.equal(r.tools[0].success,false);assert.ok(Object.values(r.artifactBodies).some(b=>b.mode==='metadata'));assert.deepEqual(r.executed,[]);
});
test('cross-Run input, output and report artifacts are rejected and source records are not adopted',()=>{
 for(const key of ['input_artifact_id','output_artifact_id']){const db=fixture();db.run_steps[3][key]='ra-input';assert.throws(()=>adaptExport(db,manifest),/step_artifact_run_mismatch/);}
 const db=fixture();db.results[0].report_artifact_id='ra-input';assert.throws(()=>adaptExport(db,manifest),/report_artifact_run_mismatch/);
 assert.throws(()=>adaptExport({...fixture(),truth:{}},manifest),/audit_truth/);
});
test('merge is additive, idempotent and leaves existing local edits and old records intact',()=>{
 const {data:d}=adapted(),store={alerts:[{id:'old-alert'}],cases:[],assets:[],incidents:[],activities:[],evidence:[]};merge(store,d);store.cases[0].title='local edit';const before=JSON.stringify(store);merge(store,d);assert.equal(JSON.stringify(store),before);assert.equal(store.alerts[0].id,'old-alert');assert.equal(store.socai2RecordedRuns.length,5);
});
test('original five views, H history and missing-source states render without fabricating results or mutating records',()=>{
 const {data:d}=adapted(),x=load(d),c=x.store.cases.find(c=>c.recordedImport),r=x.M.runs(x.store).find(r=>r.sourceRunId==='rc'),before=JSON.stringify(x.store);
 assert.equal(x.store.incidents.find(i=>i.recordedImport).status,'New');assert.equal(x.caseQueueRows().find(row=>row.recordedImport).investigation,'执行状态待确认 · 有待启动调查');
 for(const view of ['overview','process','tools','graphs','report','ledger']){x.s.location.hash=`#/cases/${c.id}/investigations?run=${r.id}&view=${view}`;const html=x.casePage();assert.ok(!/Invalid Date|>undefined<|>null</.test(html),view);for(const title of ['调查发现','AI 分析','查询与证据','调查关系图','报告与响应'])assert.ok(html.includes(title),title);
  if(view==='tools')assert.ok(html.includes('资料不可用'));if(view==='process')assert.ok(html.includes('Earlier frozen statement'));if(view==='graphs'){assert.ok(html.includes('候选关联'));assert.ok(!html.includes('攻击路径 · Path'));}if(view==='report'){assert.ok(html.includes('未记录审批要求'));assert.ok(!html.includes('无需审批'));}
 }
 x.s.location.hash=`#/cases/${c.id}/tasks`;let html=x.casePage();assert.ok(html.includes('Current human statement'));assert.ok(html.includes('Earlier frozen statement'));assert.ok(html.includes('actual-completer'));assert.ok(html.includes('metadata-editor'));
 x.s.location.hash=`#/cases/${c.id}/case-info`;html=x.casePage();assert.ok(html.includes('调查依据已变化，需重新分析'));assert.ok(html.includes('当前判断未覆盖 1'));
 x.s.location.hash=`#/cases/${c.id}/overview`;html=x.casePage();assert.ok(html.includes('待启动，尚未执行'));assert.ok(html.includes('执行状态待确认'));assert.equal(JSON.stringify(x.store),before);
});
test('pending and A/I records never establish Case baseline coverage; graph reads frozen records',()=>{
 const {data:d}=adapted(),x=load(d),c=x.store.cases.find(c=>c.recordedImport),r=x.M.runs(x.store).find(r=>r.sourceRunId==='rc');
 const p=x.M.runs(x.store).find(r=>r.sourceRunId==='rp');assert.equal(x.M.activeStatuses.has(p.status),false);assert.equal(x.M.runOutcome(p).hasConclusion,false);assert.match(x.M.runOutcome(p).conclusion,/待启动/);
 x.store.socai2RecordedRuns=x.store.socai2RecordedRuns.filter(r=>r.investigationKind!=='baseline');assert.equal(x.M.caseAssessment(x.store,c).unanalysed.length,2);
 const graphBefore=JSON.stringify(x.s.window.investigationGraphModel.build(r,x.store,x.M.graphContext(x.store,r)));x.store.alerts.find(a=>a.id===r.alertIds[0]).title='edited current title';assert.equal(JSON.stringify(x.s.window.investigationGraphModel.build(r,x.store,x.M.graphContext(x.store,r))),graphBefore);
});

test('unknown and conflicting evidence detail labels are visible and neutral',()=>{
 const {data}=adapted();const x=load(data);
 for(const verdict of ['未判定','有冲突']){
  x.store.evidence.push({id:'unit-'+verdict,name:'Unit evidence',type:'log',alertId:data.cases[0].alertIds[0],verdict,remediation:'未记录',origin:'unit'});
  x.ui.drawer={type:'evidence',id:'unit-'+verdict};const html=x.drawerMarkup();
  assert.ok(html.includes(verdict));assert.ok(!html.includes('badge green'));
 }
});
