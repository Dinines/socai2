#!/usr/bin/env node
/* Read-only source/page comparison. The receipt contains counts, field paths and hashes, not payloads. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),repo=path.resolve(root,'../..');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const canonical=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
const same=(a,b)=>canonical(a)===canonical(b);
const batches=[
 {name:'local-maintenance-20261105a',stamp:'20261105T102314778605Z',page:'socai2-recorded-local-maintenance-20261105a-r2.js'},
 {name:'local-maintenance-20261105b',stamp:'20261105T104937427659Z',page:'socai2-recorded-local-maintenance-20261105b.js'},
 {name:'local-maintenance-20261105c',stamp:'20261105T110746110174Z',page:'socai2-recorded-local-maintenance-20261105c.js'},
];
function auditBatch(batch){
 const directory=path.join(repo,'.local/local-investigation/validation',batch.name,'exports',batch.stamp),read=file=>fs.readFileSync(path.join(directory,file));
 const manifestBytes=read('manifest.json'),manifest=JSON.parse(manifestBytes),database=JSON.parse(read('database.json'));
 const sourceHashes=manifest.sources.map(s=>{assert.equal(hash(read(s.file)),s.sha256,s.file);return {role:s.role,file:s.file,sha256:s.sha256};});
 assert.equal(hash(read('database.json')),manifest.source_sha256);
 const pageBytes=fs.readFileSync(path.join(root,batch.page)),sandbox={window:{}};vm.runInNewContext(pageBytes.toString(),sandbox);
 const data=sandbox.window.socai2RecordedData;assert.equal(data.provenance.source_sha256,manifest.source_sha256);
 const candidates=new Map();
 function visit(value){if(!value||typeof value!=='object')return;if(typeof value.id==='string'){if(!candidates.has(value.id))candidates.set(value.id,[]);candidates.get(value.id).push(value);}for(const child of Object.values(value))visit(child);}
 visit(data);
 const tableCoverage=Object.fromEntries(Object.entries(database).map(([table,rows])=>[table,{export_rows:rows.length,complete_raw_rows_embedded_in_page:table==='artifacts'?rows.length:rows.filter(row=>(candidates.get(row.id)||[]).some(candidate=>same(candidate,row))).length}]));
 const pageRuns=new Map(data.runs.map(r=>[r.sourceRunId,r]));
 for(const source of database.runs)assert.ok(same(pageRuns.get(source.id).sourceRecord.run,source),'run raw fields');
 for(const source of database.run_steps){const step=pageRuns.get(source.run_id).steps.find(s=>s.payload.source_step.id===source.id);assert.ok(same(step.payload.source_step,source),'step raw fields including usage/args');}
 for(const source of database.artifacts){
  if(!source.run_id){assert.ok(data.sourceArtifacts.some(a=>same(a.sourceRecord,source)));continue;}
  const run=pageRuns.get(source.run_id),artifact=run.artifacts.find(a=>a.sourceArtifactId===source.id),body=run.artifactBodies[artifact.id];
  const {content_json:sourceJson,content_text:sourceText,...sourceMetadata}=source;
  assert.ok(same(artifact.sourceRecord,sourceMetadata),'artifact metadata');
  if(sourceJson!==null)assert.ok(same(body.content,sourceJson),'artifact JSON');
  else if(sourceText!==null)assert.equal(body.content,sourceText,'artifact text');
  else assert.equal(body.mode,'metadata');
  assert.equal(artifact.sha256,source.sha256);
 }
 for(const table of ['alerts','alert_materials','alert_source_refs','alert_assessments','incident_diagnoses','cases','runs','run_steps','activities'])assert.equal(tableCoverage[table].complete_raw_rows_embedded_in_page,database[table].length,table);
 const toolSources=database.run_steps.filter(s=>s.kind==='tool').map(step=>{
  const artifact=database.artifacts.find(a=>a.id===step.output_artifact_id),body=artifact?.content_json;
  return {stage:step.stage_code,tool:body?.tool_name||step.actual_args?.tool_name||step.name,step_name:step.name,step_state:step.state,result_state:body?.state??null,returned_rows:step.returned_rows??body?.returned_rows??null,reason:body?.reason||body?.error?.code||null,request_saved:!!step.input_artifact_id,response_saved:!!step.output_artifact_id,returned_record_field_names:[...new Set((body?.rows||[]).flatMap(r=>Object.keys(r.record||{})))].sort()};
 });
 const api=JSON.parse(read('api-responses.json')),detail=api.find(x=>x.method==='GET'&&x.path==='/api/v1/socai2/cases/'+database.cases[0].id)?.body;
 assert.equal(detail.current_assessment,null);assert.equal(database.case_assessments.length,0);assert.equal(data.cases[0].assessment,null);assert.equal(database.tasks.length,0);assert.equal(data.cases[0].tasks.length,0);
 const modelSteps=database.run_steps.filter(s=>s.kind==='model'&&!['planned','skipped'].includes(s.state));
 const counts={alerts:data.alerts.length,raw_alert_materials:database.alert_materials.length,source_snapshots:data.sourceArtifacts.length,alert_object_rows:database.alert_objects.length,distinct_display_objects:data.assets.length,independent_evidence_entries:data.evidence.length,activities_table:database.activities.length,step_projections:database.run_steps.length,occurrence_projections:data.alerts.length,activity_list_total:database.activities.length+database.run_steps.length+data.alerts.length,runs:data.runs.length,artifacts:database.artifacts.length,run_bound_artifacts:data.runs.reduce((n,r)=>n+r.artifacts.length,0),model_calls:modelSteps.length,model_requests:database.artifacts.filter(a=>a.kind==='model_request').length,model_responses:database.artifacts.filter(a=>a.kind==='model_response').length,known_tokens:modelSteps.filter(s=>s.usage?.usage_state==='reported').reduce((n,s)=>n+(s.usage.total_tokens??0),0),unknown_usage_calls:modelSteps.filter(s=>s.usage?.usage_state!=='reported').length,unpriced_calls:modelSteps.filter(s=>s.usage?.cost_state!=='priced').length,case_assessments:database.case_assessments.length,human_tasks:database.tasks.length,human_revisions:database.task_revisions.length};
 for(const source of sourceHashes)assert.equal(hash(read(source.file)),source.sha256,'source unchanged');
 assert.equal(hash(fs.readFileSync(path.join(root,batch.page))),hash(pageBytes),'generated page data unchanged');
 return {batch:batch.name,export_directory:path.relative(repo,directory),source_hashes:sourceHashes,manifest_sha256:hash(manifestBytes),page_file:path.relative(repo,path.join(root,batch.page)),page_sha256:hash(pageBytes),counts,table_coverage:tableCoverage,tool_sources:toolSources,current_case_assessment_source:'api-responses.json: GET /cases/{id}.body.current_assessment = null; per-Run SQL freshness is not substituted',baseline:data.runs.filter(r=>r.investigationKind==='baseline').map(r=>({run_state:r.status,delivery:r.completion,stop:r.stop,result_origin:r.sourceResult?.conclusion_origin,conclusion:r.sourceResult?.conclusion,adopted:data.cases[0].assessment!==null})),source_bytes_unchanged:true};
}
function audit(){return {
 schema_version:'socai2.page-field-coverage.v1',checked_at:new Date().toISOString(),mode:'offline_readback',payloads_included:false,source_or_backend_mutations:false,
 presentation_sources:['index.html','socai2-recorded-import.js','app.js','alert-detail.js','alert-flow-workspace.js','case-workflow.js','investigation-workspace.js'].map(file=>({file:path.relative(repo,path.join(root,file)),sha256:hash(fs.readFileSync(path.join(root,file)))})),
 batches:batches.map(auditBatch),
 field_coverage:[
  {fields:'alerts.*, alert_materials.*, alert_source_refs.*, Fusion artifacts.*',source:'database.json',page:'告警 → 原始数据；保留 raw.alert/material/source_refs/source_artifacts 全字段',layer:'page_raw_and_summary'},
  {fields:'alert_objects.*',source:'database.json.alert_objects (5 rows per batch)',page:'对象与证据按 namespace/object_key 去重为 4 个对象；来源抽屉显示去重对象原行。完整逐告警对象行在冻结输入工件与原始导出核查。',layer:'deduplicated_page_and_export',limitation:'不可将去重对象数当对象来源行数；源对象 not_checked 不等于资产查询未命中'},
  {fields:'alert_materials.detection.confidence_state/confidence_value/score_source/tactics/techniques',source:'database.json.alert_materials.detection',page:'从匹配 latest_material_id 的保存材料只读显示来源检测置信度（0..100）及来源 fusion；告警 ATT&CK 和 Case/事件覆盖按真实 tactics/techniques；不回写 category，不借用模型分诊 confidence（0..1）',layer:'page_raw_and_read_only_projection',limitation:'显示保留一位小数；原件浮点值不改，缺失或不可用状态不回填分数或标签'},
  {fields:'alert_assessments.*, alert_explanation content_json.*',source:'database.json + artifacts',page:'告警概况按 latest_explanation_id 读保存解释；关联 A 调查的分诊与运行原始字段展示完整 assessment，解释原件保留引用/限制/建议',layer:'page_raw_and_summary'},
  {fields:'incidents.*, incident_diagnoses.*',source:'database.json',page:'事件概览及 I 调查；I 运行原始字段保留 diagnosis 完整原行',layer:'page_raw_and_summary'},
  {fields:'cases.*, case_alerts.*, case_incidents.*, incident_alerts.*',source:'database.json',page:'Case 状态、实际 ID、成员及关联事件投影；case_alerts 与 incident_alerts 原行可在冻结输入工件核查。case_incidents 完整关系行仅在原始导出。',layer:'page_summary_frozen_input_and_export',limitation:'事件关联行的关联时间、操作者未直接投影；页面不是完整数据库浏览器'},
  {fields:'runs.*, run_steps.*, artifacts model_request/model_response/tool_request/tool_response, usage',source:'database.json',page:'每轮五阅读页签；运行详情、执行记录、工件目录保存参数/返回/用量原值，费用未定价保持未知',layer:'page_raw_and_summary'},
  {fields:'activities.*, activity_targets.*',source:'database.json',page:'数据库活动 + 调查步骤 + 告警发生的合并时间线；活动抽屉保留 activities 原行，activity_targets 前后值/结果行在原始导出',layer:'page_projection_and_export',limitation:'列表 33/35/36 不是 activities 表行数；已记录不表示调查成功，activity_targets 11 行未直接投影'},
  {fields:'case_assessments, tasks, task_revisions',source:'database.json and Case GET',page:'三批均 0，页面无当前案件判断、无人工任务，不从模型中间建议创建 H',layer:'page_and_export_agree'},
  {fields:'knowledge/assets tool states, parameters, rows, provenance',source:'artifacts tool_request/tool_response + run_steps',page:'查询与证据完整返回：A assets 各 1 条；C2 knowledge/assets 受预算保留而跳过，knowledge 无检索结果可展示',layer:'page_raw_and_summary',limitation:'未导出独立知识库或资产库全表；仅展示真实查询返回，匹配不证明授权或身份'},
 ],
 checks:['manifest companion SHA256 matches','each Run and Step raw object equals source','every artifact body and declared SHA256 equals export','required raw source tables preserved','0 assessment/H agrees with Case GET','source files and generated data unchanged'],
 limitations:['此为固定导出只读核对，不是在线数据库刷新。','字段保留和页面可读不代表模型质量验收通过；三批 C 均失败且未采用。','页面格式修正经定向渲染测试；本轮未启动浏览器或服务。'],
};}
if(require.main===module){const output=process.argv[2];if(!output)throw Error('Provide a new receipt filename');const result=audit();fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});process.stdout.write(JSON.stringify({receipt:path.resolve(output),batches:result.batches.map(b=>({batch:b.batch,counts:b.counts}))})+'\n');}
module.exports={audit,auditBatch};
