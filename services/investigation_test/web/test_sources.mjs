// Display-only source classification. These settings never enter model requests.
import {checkArtifact} from './frozen_sources.mjs';

export function classifySources(alerts, expectedIds, prefixes) {
  if (!prefixes?.length) return {state:'disabled',total:0,matched:0,unknown:0};
  if (!Array.isArray(expectedIds) || !expectedIds.length || new Set(expectedIds).size!==expectedIds.length)
    throw new Error('本轮冻结成员缺失或重复');
  const rows=new Map();
  for (const alert of alerts) {
    if (!alert?.id || rows.has(alert.id) || !expectedIds.includes(alert.id))
      throw new Error('冻结来源包含缺失、重复或其他告警身份');
    rows.set(alert.id,alert);
  }
  let matched=0,unknown=0;
  for (const id of expectedIds) {
    const source=rows.get(id)?.connector_type;
    if (typeof source!=='string' || !source.length) unknown++;
    else if (prefixes.some(prefix=>source.startsWith(prefix))) matched++;
  }
  const total=expectedIds.length;
  return {state:matched===total?'test':matched?'mixed':unknown?'unknown':'none',total,matched,unknown};
}

export async function classifyRunSources({mapping,run,artifacts,context,readBody,prefixes}) {
  if (!prefixes?.length) return {state:'disabled',total:0,matched:0,unknown:0};
  try {
    if (run.id!==mapping.run_id || run[`${mapping.subject_type}_id`]!==mapping.subject_id)
      throw new Error('来源与所选主体或Run不一致');
    if (mapping.subject_type==='case') {
      if (!context || context.case_id!==mapping.subject_id) throw new Error('本轮C1来源未读到');
      const ids=context.scope?.alert_ids;
      return classifySources((ids??[]).flatMap(id=>context.alerts?.[id]?.alert?[context.alerts[id].alert]:[]),ids,prefixes);
    }
    const refs=artifacts.filter(a=>a.id===run.input_artifact_id && a.run_id===run.id);
    if (refs.length!==1) throw new Error('本轮输入工件缺失或不唯一');
    const input=checkArtifact({...refs[0],[`${mapping.subject_type}_id`]:mapping.subject_id},(await readBody(refs[0].content_url)).data);
    const kind=mapping.subject_type==='alert'?'alert_basic':'incident_diagnosis';
    if (input?.version!=='socai2.stage-result.v1' || input.kind!==kind || !Array.isArray(input.members))
      throw new Error('本轮输入结构不匹配');
    if (mapping.subject_type==='incident' && input.parent?.id!==mapping.subject_id)
      throw new Error('冻结事件身份不一致');
    const alerts=input.members.map(m=>m.alert);
    const ids=mapping.subject_type==='alert'?[mapping.subject_id]:input.input_selection?.selected_alert_ids??alerts.map(a=>a?.id);
    return classifySources(alerts,ids,prefixes);
  } catch(error) {
    if(error.name==='AbortError')throw error;
    return {state:'unknown',total:null,matched:0,unknown:null,reason:error.message};
  }
}

export function registeredRun(operations,mapping) {
  return Boolean(mapping.run_id && operations.some(op=>(op.mappings??[]).some(m=>
    m.subject_type===mapping.subject_type && m.subject_id===mapping.subject_id && m.run_id===mapping.run_id)));
}

export function sourceCaption(result,registered=false) {
  if(result?.state==='test')return `测试数据 · 本轮 ${result.total} 条告警均来自配置的测试来源`;
  if(result?.state==='mixed')return `含测试数据 · 本轮 ${result.matched}/${result.total} 条告警来自测试来源${result.unknown?`，${result.unknown} 条来源未确认`:''}`;
  return registered?'测试执行 · 本轮已登记测试批次':null;
}
