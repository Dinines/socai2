// Read the selected Case Run's frozen inputs. Never substitute current pointers.
import {runPath, subjectPath} from './viewer_state.mjs';

const C1_SCHEMA='socai2.baseline-context.v1';
const present=value=>typeof value==='string' && value.length>0;
const list=value=>Array.isArray(value)?value:[];
const unique=values=>[...new Set(values)];
const ownArtifact=(a,run)=>a.run_id===run.id;
function one(items,label) {
  if(items.length!==1) throw new Error(`${label}应唯一，实际匹配 ${items.length} 项`);
  return items[0];
}
export function checkArtifact(ref,data) {
  const a=data?.artifact??data?.metadata;
  if(!a || a.id!==(ref.id??ref.artifact_id)) throw new Error('原件身份不一致');
  for(const key of ['run_id','case_id','alert_id','incident_id','sha256','schema_version'])
    if(ref[key]!=null && ref[key]!==a[key]) throw new Error(`原件 ${key} 与冻结来源不一致`);
  if(ref.subject_type && a[`${ref.subject_type}_id`]!==ref.subject_id)throw new Error('原件主体与引用不一致');
  if(data.availability!=='available') throw new Error(`原件不可用：${data.availability??'未记录'}`);
  return data.content_json;
}
function sameComparison(left,right) {
  return ['previous_run_id','comparison_result_id'].every(key=>(left?.[key]??null)===(right?.[key]??null));
}
export async function loadFrozenCase(run,artifacts,readBody) {
  if(!run.case_id || !run.input_artifact_id) throw new Error('本轮未记录Case或冻结输入身份');
  const manifestRef=one(artifacts.filter(a=>a.id===run.input_artifact_id&&ownArtifact(a,run)),'本轮输入清单');
  const manifest=checkArtifact({...manifestRef,case_id:run.case_id},(await readBody(manifestRef.content_url)).data);
  if(!manifest || !Array.isArray(manifest.source_materials)) throw new Error('本轮输入清单缺少冻结来源');
  const ids=new Set(manifest.source_materials.filter(r=>r.type==='artifact').map(r=>r.id));
  const ref=one(artifacts.filter(a=>ids.has(a.id)&&ownArtifact(a,run)&&a.schema_version===C1_SCHEMA),'本轮C1冻结材料');
  const context=checkArtifact({...ref,case_id:run.case_id},(await readBody(ref.content_url)).data);
  if(context?.case_id!==run.case_id || context.schema_version!==C1_SCHEMA) throw new Error('C1与所选Case不一致');
  if(!sameComparison(run.comparison_context,manifest.comparison_context) ||
     !sameComparison(run.comparison_context,context.update_context?.comparison_context)) throw new Error('冻结材料与Run的前轮身份不一致');
  return {run,manifest,context,manifestRef,ref};
}
export async function loadCaseSources({run,artifacts,previousUrl,readBody,readPages}) {
  const output={entries:[],issues:[],current:null,previous:null,comparison:'initial'};
  try { output.current=await loadFrozenCase(run,artifacts,readBody); }
  catch(error) { if(error.name==='AbortError')throw error;output.issues.push(`本轮上游来源无法读取：${error.message}`);return output; }
  const previousId=run.comparison_context?.previous_run_id;
  if(!previousId && run.comparison_context?.state!=='initial') {
    output.comparison='unavailable';output.issues.push('未记录可核对的前轮身份，无法比较来源。');
  }
  if(previousId) {
    output.comparison='unavailable';
    try {
      if(previousId===run.id) throw new Error('前轮指向当前Run');
      const expected=runPath({subject_type:'case',subject_id:run.case_id,run_id:previousId});
      if(previousUrl!==expected) throw new Error('前轮读取链接缺失或与冻结身份不一致');
      const detail=(await readBody(previousUrl)).data;
      if(detail.run?.id!==previousId || detail.run?.case_id!==run.case_id) throw new Error('前轮不是本Case指定Run');
      output.previous=await loadFrozenCase(detail.run,await readPages(detail.artifacts_url,{subject_type:'case',subject_id:run.case_id,run_id:previousId}),readBody);
      output.comparison='available';
    } catch(error) { if(error.name==='AbortError')throw error;output.issues.push(`前轮来源无法比较：${error.message}`); }
  }
  output.entries=sourceEntries(output.current.context,output.previous?.context,output.comparison);
  return output;
}
function alertIdentity(id,data) {
  const t=data?.triage,parts=[id,data?.material?.id,t?.id,t?.source_run_id,t?.input_material_id];
  return parts.every(present) && t.alert_id===id && t.input_material_id===data.material.id ? parts : null;
}
export function incidentBindings(data) {
  const material=data?.analysis_material;
  return [material?.input,material?.response,material?.receipt_source,...list(material?.originals)].filter(Boolean);
}
function incidentIdentity(id,data) {
  const m=data?.analysis_material,refs=incidentBindings(data);
  if(!present(m?.source_run_id) || m.incident_id!==id || !m.input || !m.response || !m.receipt_source || !list(m.originals).length ||
     refs.some(r=>!present(r.id)||!present(r.sha256)))return null;
  return [id,m.source_run_id,...refs.map(r=>`${r.id}:${r.sha256}`).sort()];
}
function relation(identity,previousIdentity,exists,comparison) {
  if(comparison==='unavailable')return '无法比较';
  if(comparison==='initial')return '首轮使用';
  if(!exists)return '本轮新增';
  if(!identity || !previousIdentity)return '来源不完整，无法比较';
  return JSON.stringify(identity)===JSON.stringify(previousIdentity)?'沿用上一轮':'来源版本变化';
}
export function incidentCoverage(data,caseIds) {
  const m=data?.analysis_material,units=list(m?.units),selection=m?.input_selection,known=Array.isArray(m?.units);
  // Only retained per-member units count here. Cross-member findings/questions
  // keep their original scopes; they never stand in for member analysis coverage.
  const members=units.filter(u=>/^\$\.members\[\d+\]$/.test(u.path));
  const retained=unique(members.flatMap(u=>list(u.scope?.alert_ids)));
  return {total:selection?.total_member_count,selected:selection?.selected_count,
    selectedIds:selection?.selected_alert_ids??null,
    caseSelectedIds:m?.case_selected_alert_ids??null,
    retainedIds:known?retained:null,caseRetainedIds:known?retained.filter(id=>caseIds.includes(id)):null,
    unresolvedIds:known?unique(members.filter(u=>u.value?.state==='unresolved').flatMap(u=>list(u.scope?.alert_ids))):null,
    declared:data?.diagnosis_scope?.analysis_coverage??null};
}
export function sourceEntries(context,previous,comparison='initial') {
  const caseIds=list(context.scope?.alert_ids),entries=[];
  for(const [index,id] of caseIds.entries()) {
    const data=context.alerts?.[id]??null,old=previous?.alerts?.[id],identity=alertIdentity(id,data);
    entries.push({kind:'alert',id,title:`A${index+1} · ${data?.alert?.title??'告警材料未记录'}`,data,
      runId:data?.triage?.source_run_id??null,relation:relation(identity,alertIdentity(id,old),list(previous?.scope?.alert_ids).includes(id),comparison),
      identityComplete:Boolean(identity),caseIds});
  }
  for(const [id,data] of Object.entries(context.incidents??{})) {
    const old=previous?.incidents?.[id],identity=incidentIdentity(id,data);
    entries.push({kind:'incident',id,title:`I · ${data?.incident?.title??'事件诊断'}`,data,
      runId:data?.analysis_material?.source_run_id??null,relation:relation(identity,incidentIdentity(id,old),Boolean(old),comparison),
      identityComplete:Boolean(identity),caseIds,coverage:incidentCoverage(data,caseIds)});
  }
  return entries;
}
export async function readSourceExecution(entry,readBody,readPages) {
  if(!entry.runId)throw new Error('冻结材料未记录源Run；不能用当前分析替代');
  const mapping={subject_type:entry.kind,subject_id:entry.id,run_id:entry.runId},url=runPath(mapping);
  const detail=(await readBody(url)).data,trace=(await readBody(`${url}/trace`)).data;
  if(detail.run?.id!==entry.runId || trace.run?.id!==entry.runId ||
     trace.run[`${entry.kind}_id`]!==entry.id)throw new Error('来源执行身份不一致');
  const [steps,items]=await Promise.all([readPages(trace.steps_url,mapping),readPages(trace.artifacts_url,mapping)]);
  const artifacts=items.map(a=>({...a,[`${entry.kind}_id`]:entry.id}));
  const issues=[];
  if(steps.some(s=>s.run_id!==entry.runId) || artifacts.some(a=>a.run_id!==entry.runId))throw new Error('来源目录含其他Run');
  if(entry.kind==='alert') {
    const t=entry.data?.triage,r=detail.result;
    if(r?.id!==t?.id || r?.source_run_id!==entry.runId || r?.input_material_id!==t?.input_material_id)throw new Error('源Run分诊与冻结分诊身份不一致');
  }
  const bindings=entry.kind==='incident'?incidentBindings(entry.data):[];
  for(const ref of bindings) {
    const a=artifacts.find(a=>a.id===ref.id);
    if(!a || ['sha256','schema_version','kind'].some(k=>ref[k]!=null&&ref[k]!==a[k]))issues.push(`冻结工件 ${ref.id} 缺失或摘要不一致`);
  }
  if(entry.kind==='incident' && detail.run.input_artifact_id!==entry.data.analysis_material?.input?.id)throw new Error('源Run输入与冻结输入不一致');
  return {run:detail.run,steps,artifacts,result:detail.result,url,issues,bindings};
}
export function alertMaterialUrl(entry) {
  const id=entry.data?.material?.id;
  return id?`${subjectPath({subject_type:'alert',subject_id:entry.id})}/materials/${encodeURIComponent(id)}`:null;
}
