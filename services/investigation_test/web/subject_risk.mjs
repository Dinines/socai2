// Risk is read from saved subject attributes and the explicitly selected Run.
import {checkArtifact} from './frozen_sources.mjs';

export const riskLevel=v=>({info:'信息',low:'低',medium:'中',high:'高',critical:'严重'})[v]??'未记录';
export const riskSource=v=>({member_max:'成员规则',initial_policy:'规则初值，待分析',manual:'人工设置',manual_override:'人工设置',model:'模型上调',severity_mapping:'等级映射'})[v]??v??'未记录';
export const opinionReason=v=>({raised:'已自动上调',lower_not_applied:'降低建议，未自动采用',unchanged:'等级相同，当前值保持',manual_revision_changed:'人工等级已修改，本轮未应用',execution_unconfirmed:'执行未确认，仅保留候选',opinion_missing_or_invalid:'本轮缺少可用等级',frozen_scope_changed:'成员或材料已变，本轮未应用',local_scope_only:'局部范围意见，未改全案等级',scope_unavailable:'范围不可核对',input_changed:'输入已变，本轮未应用',newer_round_exists:'已有较新轮次，本轮未应用'})[v]??v??'处理结果未记录';
export function currentRisk(kind,detail) {
  const subject=(kind==='case'?detail.case:detail.facts)??{},risk=subject.risk;
  return {level:kind==='case'?subject.severity:detail.derived?.severity_effective,
    source:risk?.current?.source??subject.severity_source??detail.derived?.severity_source,
    priority:subject.priority_value,risk};
}
export function currentRiskCard(kind,detail,ui,{listOnly=false}={}) {
  const x=currentRisk(kind,detail),r=x.risk,c=ui.card(listOnly?'列表观察的风险属性':'当前风险属性（当前观察）');
  c.classList.add('subject-risk-current');
  c.append(ui.facts([['当前严重程度',riskLevel(x.level)],['等级来源',riskSource(x.source)],
    ['等级更新时间',r?.current?.updated_at],['当前等级理由',r?.current?.reason],
    ['当前优先级',x.priority],['系统优先级建议',r?.system_priority?.value],
    ['人工优先级',r?.priority_override?.value??'未设置'],['人工优先级理由',r?.priority_override?.reason],['人工优先级更新时间',r?.priority_override?.updated_at]]));
  c.append(ui.notice(listOnly?'主体详情读取失败；此处仅保留列表观察，可能已过期。':'这些值来自当前主体详情；历史轮次的意见在所选 Run 中单独展示。'));
  return c;
}
export async function readRoundRisk({mapping,run,artifacts,readBody}) {
  if(run.id!==mapping.run_id||run[`${mapping.subject_type}_id`]!==mapping.subject_id)throw Error('等级意见的轮次或主体不一致');
  const result={run,parts:{},refs:{},errors:[]};
  for(const ref of artifacts.filter(a=>a.schema_version==='socai2.severity-opinion.v1')) {
    try {
      if(ref.run_id!==run.id)throw Error('等级工件引用不属于所选轮次');
      const content=checkArtifact({...ref,subject_type:mapping.subject_type,subject_id:mapping.subject_id},(await readBody(ref.content_url)).data);
      if(content?.run_id!==run.id)throw Error('等级工件正文不属于所选轮次');
      if(!['severity_opinion_input','severity_opinion_candidate','severity_opinion_application'].includes(content.type)||result.parts[content.type])throw Error('等级工件类型不唯一');
      result.parts[content.type]=content;result.refs[content.type]=ref.id;
    } catch(error) {
      if(error.name==='AbortError')throw error;
      result.errors.push(error.message);
    }
  }
  const input=result.parts.severity_opinion_input,candidate=result.parts.severity_opinion_candidate,application=result.parts.severity_opinion_application;
  if(input&&(input.subject_type!==mapping.subject_type||input.subject_id!==mapping.subject_id))throw Error('等级冻结范围不属于所选主体');
  if(candidate&&input&&candidate.input_artifact_id!==result.refs.severity_opinion_input)throw Error('等级候选缺少同轮冻结引用');
  if(application&&candidate&&application.artifact_id!==result.refs.severity_opinion_candidate)throw Error('等级处理回执与意见引用不一致');
  return result;
}
export function roundRiskCard(part,ui) {
  const c=ui.card('所选轮次等级意见');c.classList.add('subject-risk-round');
  if(part?.error){c.append(ui.notice(`等级意见读取失败：${part.error}。未使用其他轮次替代。`,true));return c;}
  const data=part?.data,p=data?.parts??{},input=p.severity_opinion_input,opinion=p.severity_opinion_candidate?.unit?.value,a=p.severity_opinion_application;
  c.dataset.riskRun=data?.run?.id??'';
  c.append(ui.facts([['本轮建议等级',opinion?riskLevel(opinion.level):'本轮未提供可用等级'],
    ['处理结果',a?opinionReason(a.reason_code):'尚无处理回执'],['本轮依据',opinion?.reason],
    ['冻结时等级',input?riskLevel(input.current_level):'未记录'],['当轮处理后等级',a?riskLevel(a.after?.severity):'未记录'],
    ['处理时间',a?.processed_at],['冻结成员数',input?Object.keys(input.selected_members??{}).length:null]]));
  if(opinion)c.append(ui.facts([['已确认影响',(opinion.impact_basis?.confirmed??[]).join('；')||'未提供'],
    ['潜在影响',(opinion.impact_basis?.potential??[]).join('；')||'未提供'],['限制',(opinion.limitations??[]).join('；')||'未提供']]));
  for(const error of data?.errors??[])c.append(ui.notice(`部分等级工件读取失败：${error}。其余已读取内容保留。`,true));
  c.append(ui.notice('本轮意见与处理回执按当时保存展示；不代表当前主体值。'));
  if(data)c.append(ui.rawDetails(data.parts,'查看本轮等级工件'));
  return c;
}
export function riskActivities(kind,id,items) {
  const stamp=a=>Number.isFinite(Date.parse(a.occurred_at))?Date.parse(a.occurred_at):-Infinity;
  return items.flatMap(activity=>(activity.matching_targets??[]).filter(t=>t[`${kind}_id`]===id).map(target=>({activity,target})))
    .filter(({activity:a,target:t})=>['severity_raised','severity_lower_suggested'].includes(a.action)||
      t.before_value?.risk?.manual_severity_revision!==t.after_value?.risk?.manual_severity_revision||
      JSON.stringify(t.before_value?.risk?.priority_override)!==JSON.stringify(t.after_value?.risk?.priority_override))
    .sort((left,right)=>stamp(right.activity)-stamp(left.activity));
}
export function riskActivityList(mapping,items,ui,onRun) {
  const box=ui.node('div'),rows=riskActivities(mapping.subject_type,mapping.subject_id,items);
  for(const {activity:a,target:t} of rows) {
    const b=t.before_value??{},n=t.after_value??{},ref=n.severity_opinion;
    const title=({severity_raised:'自动上调',severity_lower_suggested:'本轮降低建议，未自动采用'})[a.action]??'人工属性修改';
    const c=ui.card(title),grade=v=>v.risk?.current?.level??v.severity;
    c.dataset.riskActivity=a.id;
    c.append(ui.facts([['时间',a.occurred_at],['操作者',a.actor?.name_snapshot??a.actor?.user_id??a.actor?.service_name],
      ['等级前值',riskLevel(grade(b))],['等级后值',riskLevel(grade(n))],['优先级前值',b.priority_value],['优先级后值',n.priority_value],['理由',t.reason??a.detail?.reason]]));
    for(const note of a.detail?.notes??[])c.append(ui.node('p',note));
    if(ref?.run_id)c.append(ui.button('查看来源轮次',()=>onRun(ref.run_id)));
    box.append(c);
  }
  if(!rows.length)box.append(ui.notice('已读取的活动中暂无该主体的风险属性变更；关联主体活动不作本主体变更。'));
  return box;
}
