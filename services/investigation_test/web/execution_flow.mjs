// The former execution-lane presentation, populated from the current HTTP records.
import {alertMaterialUrl, checkArtifact} from './frozen_sources.mjs';
const STATES = {completed:'已完成', saved:'已保存', running:'执行中', pending:'等待执行', accepted:'已接收',
  failed:'失败', timeout:'超时', unknown:'结果待确认', skipped:'已跳过', cancelled:'已取消',
  complete:'完整交付', partial:'部分交付', none:'无可用内容', uncertain:'待复核', current:'适用当前输入', stale:'输入已变化',
  deferred:'已记录，后续处理', finished:'已结束', live:'实时读取', saved_evidence:'已保存记录',
  live_execution:'真实执行记录', issues_recorded:'有待核问题', not_assessed:'质量未评估'};
const NAMES = {'C1.executor':'C1 · 准备执行计划', C2:'C2 · 补充背景信息',
  'C4.materials':'整理主分析材料', C3:'C3 · 初步分析', 'C4.routing':'C4 · 补查分派',
  'C4.deep':'C4 · 深查具体问题', 'C4.query':'C4 · 补充查询', C5:'C5 · 构建关系图',
  C6:'C6 · 最终结论与交付', 'C3.reanalysis':'补证后重新分析', A:'告警分诊', I:'事件诊断'};
const TOOLS = {knowledge:'知识库', assets:'资产信息', history:'历史告警', threat_intel:'威胁情报',
  ueba:'用户行为', graph:'身份关系', process_activity:'进程活动', network_connections:'网络连接',
  authentication_activity:'认证活动'};
export const stateLabel = value => STATES[value] ?? value ?? '未记录';
export const timeLabel = value => value ? new Date(value).toLocaleString('zh-CN',{hour12:false}) : '未记录时间';
export function stepTitle(step) {
  if (step.kind === 'tool') return TOOLS[step.actual_args?.tool_name ?? step.name] ?? step.name;
  const label = NAMES[step.stage_code] ?? step.stage_code ?? step.name;
  return step.kind === 'model' ? `${label} · 模型调用` : label;
}
export function executionTree(steps, runId) {
  const own = steps.filter(s => s.run_id === runId).sort((a,b) => a.seq-b.seq);
  const ids = new Set(own.map(s => s.id)), visited = new Set();
  const visit = step => {
    if (visited.has(step.id)) return null;
    visited.add(step.id);
    return {step, children:own.filter(s => s.parent_step_id === step.id).map(visit).filter(Boolean)};
  };
  const roots = own.filter(s => !ids.has(s.parent_step_id)).map(visit).filter(Boolean);
  // Retain malformed/orphan records visibly; never hide them or recurse forever.
  for (const step of own) if (!visited.has(step.id)) roots.push(visit(step));
  return roots;
}
export function originalChoices(content) {
  const raw=content?.raw??content?.payload?.raw;
  return Array.isArray(raw?.choices) ? raw.choices : null;
}
export function requestBody(content) {
  return content?.body ?? content?.request ?? content?.payload?.body ?? content?.payload ?? content;
}
export function stepReferences(step, artifacts, role) {
  const refs = (step.artifact_refs ?? []).filter(r => r.role === role);
  if (refs.length) return refs;
  const id = step[`${role}_artifact_id`];
  const found = artifacts.find(a => a.id === id && a.run_id === step.run_id);
  return found ? [{...found, artifact_id:found.id, role}] : [];
}
export function matchingExchange(exchanges, mapping, runId, taskId) {
  return exchanges.find(e => e.subject_type === mapping.subject_type && e.subject_id === mapping.subject_id &&
    e.run_id === runId && e.task_id === taskId) ?? null;
}
export function matchingAttempt(task, runId) { return task?.attempts?.find(a=>a.run_id===runId) ?? null; }
const COMPONENTS={domain_analysis:'领域分析',deep_analysis:'深查结果',alert_graph:'关系图',report_json:'结构化报告',report_markdown:'调查报告',case_evidence_index:'证据目录'};
const DOMAINS={identity:'身份',cloud:'云',phishing:'钓鱼',insider:'内部风险'};
export function domainLabel(data) {
  return `${DOMAINS[data?.domain]??data?.domain??'领域未记录'} · ${{applicable:'适用',not_applicable:'不适用',undetermined:'适用性待定'}[data?.applicability]??data?.applicability??'适用性未记录'}`;
}
export function stepReason(step) {
  const code=step.error?.code;
  return {source_not_connected:'数据源未接入',tool_budget_reserved_for_evidence:'工具额度预留给证据补查'}[code]??code??'';
}
const PURPOSES={'C1.executor':'冻结本轮范围、输入与执行计划。',C2:'补充本案需要的知识和对象背景。','C4.materials':'整理事实和来源，形成模型本轮输入。',C3:'结合材料形成初步判断与待核问题。','C4.deep':'针对尚未解决的问题进一步分析。','C4.query':'按本轮选定目标查询补充证据。','C4.routing':'汇总补查结果并记录后续处理。',C5:'整理告警和对象间的关系。',C6:'形成本轮结论、依据及交付内容。',A:'对单条告警进行分诊。',I:'综合当前选入成员，诊断事件。'};

export function executionFlow({run, steps, artifacts, result, context={}, upstream, readSource, readBody, current, onInspect, ui}) {
  const {node, button, facts, rawDetails, notice, resultCard, contentCard} = ui;
  const root = node('section',null,'execution-flow');
  root.append(node('h3','执行流程'),node('p','点击左侧阶段、模型或查询，在右侧查看这一步实际使用和产生的数据。','muted'));
  const grid = node('div',null,'flow-workspace'), nav = node('div',null,'flow-navigation');
  const inspector = node('aside',null,'node-inspector'); inspector.setAttribute('aria-label','执行节点详情');
  const heading = node('div',null,'inspector-heading'), tabs = node('div',null,'inspector-tabs');
  const body = node('div',null,'inspector-content'); body.setAttribute('aria-live','polite');
  inspector.append(heading,tabs,body); grid.append(nav,inspector); root.append(grid);
  let generation = 0, selectedStep = null;
  const buttons = [], cache = new Map();
  const own={run,artifacts,caption:'本轮执行'};
  async function content(ref) {
    if (!ref.content_url) throw new Error('未保存原件读取链接');
    if (!cache.has(ref.content_url)) cache.set(ref.content_url,readBody(ref.content_url).catch(error => {cache.delete(ref.content_url);throw error;}));
    const response = await cache.get(ref.content_url);
    if (response.data.artifact?.id && response.data.artifact.id !== (ref.artifact_id ?? ref.id)) throw new Error('原件身份与所选节点不一致');
    if(response.data.availability==='available')checkArtifact(ref,response.data);
    return response;
  }
  function focusInspector() {
    onInspect();
    if (window.matchMedia('(max-width:850px)').matches) requestAnimationFrame(()=>inspector.scrollIntoView({behavior:'smooth',block:'start'}));
  }
  function block(title, value, target=body) {
    target.append(node('h4',title),node('pre',typeof value === 'string' ? value : JSON.stringify(value,null,2)));
  }
  function selected(button) { for (const b of buttons) b.setAttribute('aria-current',String(b === button)); }
  const summary = button('本轮结论与执行概览',() => {
    generation++; focusInspector(); selected(summary); selectedStep=null; tabs.replaceChildren();
    heading.replaceChildren(node('h3','本轮结论与执行概览'));
    body.replaceChildren(resultCard(result), notice('执行完成与模型结论质量分别记录；引用和正文问题保留在“质量问题”中。'));
  });
  buttons.push(summary); nav.append(summary); summary.className='flow-summary';
  function recordNode(title, status, panels) {
    const li=node('li',null,'flow-lane'), b=button('',()=>recordView('overview'));
    b.className=`flow-node state-${status}`; b.append(node('span',title,'flow-label'),node('small',stateLabel(status)));
    buttons.push(b);li.append(b);
    function recordView(view) {
      generation++;focusInspector();selected(b);selectedStep=null;
      heading.replaceChildren(node('h3',title));tabs.replaceChildren();body.replaceChildren();
      for(const [key,label] of [['overview','概览与原因'],['input','输入'],['output','输出'],['records','原始记录']]) {
        if(!Object.hasOwn(panels,key))continue;
        const t=button(label,()=>recordView(key));t.setAttribute('aria-pressed',String(view===key));tabs.append(t);
      }
      const val=panels[view];if(typeof val==='function')body.append(val());else block(view==='input'?'实际请求/输入':view==='output'?'实际回执/输出':'实际记录',val);
    }
    return li;
  }
  function component(kind, refs) {
    const b=button(`${COMPONENTS[kind]}${refs.length>1?`（${refs.length}）`:''}`,async()=>{
      const ticket=++generation;focusInspector();selected(b);selectedStep=null;
      heading.replaceChildren(node('h3',COMPONENTS[kind]));tabs.replaceChildren();body.replaceChildren(node('p','正在读取组件保存的数据…'));
      try {
        const fragment=node('div');
        for(const ref of refs) {
          const response=await content(ref);if(!current()||ticket!==generation)return;
          if(response.data.availability!=='available')fragment.append(contentCard(response.data,response.raw,'组件原件不可用'));
          else if(kind==='domain_analysis') {
            const data=response.data.content_json;
            heading.replaceChildren(node('h3',domainLabel(data)));
            fragment.append(node('p','这是本阶段保存的领域分析结果；适用性与模型结论质量分别判断。','muted'));
            fragment.append(facts([['领域',DOMAINS[data.domain]??data.domain],['适用性',domainLabel(data).split(' · ').slice(1).join(' · ')]]));
            for(const finding of data.findings??[]) {
              fragment.append(node('h4',({observed:'已观察',inferred:'推测',unresolved:'待核实'})[finding.state]??finding.state),node('p',finding.statement,'prose'),rawDetails({scope:finding.scope,support:finding.support,counterevidence:finding.counterevidence,limitations:finding.limitations},'本项依据、范围与限制'));
            }
            for(const [key,label] of [['limitations','范围与限制'],['questions','待核问题'],['recommendations','建议']]) if(data[key]?.length) block(label,data[key],fragment);
            fragment.append(rawDetails(response.data,'完整领域原件与来源'));
          } else {block(`${COMPONENTS[kind]} · ${ref.id}`,response.data.content_json??response.data.content_text,fragment);fragment.append(rawDetails(response.data,'来源与完整原件记录'));}
        }
        if(current()&&ticket===generation)body.replaceChildren(fragment);
      } catch(error){if(current()&&ticket===generation)body.replaceChildren(notice(`读取失败：${error.message}`,true));}
    });
    b.className='component-node';buttons.push(b);return b;
  }
  function item(entry, child=false, scope=own) {
    const {step,children} = entry, li = node('li',null,'flow-lane');
    const b = button('',() => show(step,'overview',b,scope));
    b.className = `flow-node state-${step.state}${step.error ? ' has-issue' : ''}`;
    b.dataset.stepId=step.id;
    b.append(node('span',stepTitle(step),'flow-label'),node('small',`第${step.seq}步 · ${stateLabel(step.state)}`));
    if(step.error)b.append(node('small',stepReason(step),'node-reason'));
    buttons.push(b); li.append(b);
    const list=node('ol',null,'flow-branches');children.forEach(entry=>list.append(item(entry,true,scope)));
    if(!child) {
      const stepIds=new Set([step.id,...children.map(c=>c.step.id)]), groups=new Map();
      for(const a of scope.artifacts) if(a.run_id===scope.run.id && stepIds.has(a.step_id) && COMPONENTS[a.kind]) {
        if(!groups.has(a.kind))groups.set(a.kind,[]);groups.get(a.kind).push(a);
      }
      for(const [kind,refs] of groups) for(const part of kind==='domain_analysis'?refs.map(ref=>[ref]):[refs]) {
        const c=node('li',null,'flow-component'), b=component(kind,part);c.append(b);list.append(c);
        if(kind==='domain_analysis') {
          b.textContent='领域分析 · 正在读取';
          content(part[0]).then(response=>{
            if(!current())return;
            b.textContent=response.data.availability==='available'?domainLabel(response.data.content_json):'领域原件不可用';
          }).catch(()=>{if(current())b.textContent='领域名称读取失败 · 点击重试';});
        }
      }
    }
    if(list.children.length)li.append(list);
    return li;
  }
  function sourceNode(entry) {
    const li=node('li',null,'flow-lane upstream-source'), branch=node('ol',null,'source-execution');
    const b=button('',()=>sourceView('overview'));b.className='flow-node frozen-node';
    const material=entry.data?.analysis_material,receipt=material?.receipt;
    const usable=entry.kind==='alert' ? entry.data?.triage_usable : receipt?.use?.conclusion_available;
    const availability=entry.kind==='alert' ? (usable===true?'分诊可用':usable===false?'分诊不可用':'可用性未记录') : stateLabel(receipt?.delivery?.state);
    b.append(node('span',entry.title,'flow-label'),node('small',`${entry.relation} · ${availability}`));
    buttons.push(b);li.append(b,branch);branch.hidden=true;li.dataset.sourceRun=entry.runId??'';
    let loaded=null;
    const load=()=>loaded??=readSource(entry).catch(error=>{loaded=null;throw error;});
    async function sourceView(view) {
      const ticket=++generation;focusInspector();selected(b);selectedStep=null;
      heading.replaceChildren(node('h3',entry.title),node('p',`${entry.relation} · 本轮冻结来源，不计作Case内重新执行`));
      tabs.replaceChildren();body.replaceChildren();
      for(const [key,label] of [['overview','判断与范围'],['input','冻结输入'],['originals','来源执行与原件'],['records','冻结记录']]) {
        const t=button(label,()=>sourceView(key));t.setAttribute('aria-pressed',String(view===key));tabs.append(t);
      }
      if(view==='records') {body.append(rawDetails(entry.data,'本轮C1保存的完整来源',true));return;}
      if(view==='overview') {
        body.append(facts([['来源关系',entry.relation],['源Run',entry.runId],['所属主体',entry.id],['结论可用',usable===true?'是':usable===false?'否':'未记录']]));
        if(!entry.identityComplete)body.append(notice('来源身份不完整；不能据此确认沿用同一分析。'));
        if(entry.kind==='alert') {
          const t=entry.data?.triage;
          body.append(facts([['分诊判断',({needs_review:'待复核',malicious:'恶意',benign:'良性'})[t?.verdict]??t?.verdict],['材料版本',entry.data?.material?.revision],['分诊时间',timeLabel(t?.assessed_at)]]));
          body.append(node('p',t?.rationale??'未保存分诊判断正文。','prose'));
          if(entry.data?.limitations?.length)block('范围与限制',entry.data.limitations);
        } else {
          const c=entry.coverage;
          body.append(facts([['原事件成员',c.total],['诊断选入',c.selected],['选入与本案交集',c.caseSelectedIds?.length],['保留成员分析',c.retainedIds?.length],['成员分析与本案交集',c.caseRetainedIds?.length],['其中待核成员',c.unresolvedIds?.length],['交付情况',stateLabel(receipt?.delivery?.state)],['质量检查',receipt?.quality?.state==='checked'?'已检查（不等于通过）':receipt?.quality?.state]]));
          body.append(notice('选入数量与保留成员分析分开计数；成员待核不表示已经确定结论。跨成员发现保留其原始范围。'));
          const gaps={missing_units:receipt?.missing_units,invalid_units:receipt?.invalid_units};
          if(gaps.missing_units?.length||gaps.invalid_units?.length)body.append(rawDetails(gaps,'缺失或非法内容',true));
          if(receipt?.quality?.issues?.length)body.append(rawDetails(receipt.quality.issues,'原质量问题',true));
          if(!material)body.append(notice('本轮未保存事件分析材料，未查询当前诊断替代。'));
          else if(!Array.isArray(material.units))body.append(notice('未记录分析单元目录，保留数量未知；源执行和原件仍可查。'));
          else if(!material.units.length)body.append(notice('没有可用分析单元；源执行和原件仍可查。'));
          for(const unit of Array.isArray(material?.units)?material.units:[]) {
            const c=node('section',null,'frozen-unit');
            const title=/^\$\.members\[\d+\]$/.test(unit.path)?'成员分析':({'$.diagnosis.summary':'事件摘要','$.diagnosis.conclusion':'事件结论','$.diagnosis.limitations':'结论限制'})[unit.path]??({finding:'分析发现',question:'待核问题',incident:'事件结论'})[unit.kind]??unit.kind;
            c.append(node('h4',title),node('p',`原始范围：${unit.scope?.alert_ids?.length??'未记录'} 条告警`,'small muted'));
            const val=unit.value,statement=typeof val==='string'?val:val?.assessment??val?.statement??val?.text??val?.question??val?.summary;
            if(statement)c.append(node('p',statement,'prose'));else block('保存内容',val,c);
            c.append(rawDetails({path:unit.path,scope:unit.scope,value:unit.value,source_refs:unit.source_refs},'本项完整范围、内容与依据'));
            body.append(c);
          }
        }
        body.append(button('查看来源执行与原件',()=>sourceView('originals')));return;
      }
      if(view==='input') {
        if(entry.kind==='alert') {
          body.append(facts([['材料',entry.data?.material?.id],['分诊输入材料',entry.data?.triage?.input_material_id],['材料摘要',entry.data?.material?.sha256]]));
          const url=alertMaterialUrl(entry);
          if(url)body.append(button('读取本条原告警材料',async()=>{
            const t=++generation;body.replaceChildren(node('p','正在读取冻结材料…'));
            try {
              const response=await readBody(url);if(!current()||t!==generation)return;
              const meta=response.data.metadata,expected=entry.data.material;
              if(meta?.id!==expected.id || meta?.alert_id!==entry.id || meta?.sha256!==expected.sha256)throw new Error('告警材料身份或摘要与冻结来源不一致');
              body.replaceChildren();block('原告警材料（按冻结材料ID读取）',response.data);body.append(rawDetails(response.raw,'HTTP回执'));
            }catch(error){if(current()&&t===generation)body.replaceChildren(notice(`读取失败：${error.message}`,true));}
          }));
        } else body.append(rawDetails({input_selection:material?.input_selection,case_selected_alert_ids:material?.case_selected_alert_ids,input:material?.input},'冻结选入范围与源输入',true));
        body.append(button('打开源执行的输入与模型原件',()=>sourceView('originals')));return;
      }
      body.append(node('p','正在读取冻结源Run的步骤与原件…'));
      try {
        const source=await load();if(!current()||ticket!==generation)return;
        body.replaceChildren(facts([['源Run',source.run.id],['执行状态',stateLabel(source.run.state)],['开始',timeLabel(source.run.started_at)],['结束',timeLabel(source.run.ended_at)],['步骤',source.steps.length],['工件',source.artifacts.length]]));
        if(source.issues.length) {for(const issue of source.issues)body.append(notice(issue,true));return;}
        branch.replaceChildren(node('li',`${entry.kind==='alert'?'告警分诊':'事件诊断'}源执行 · ${source.run.id}`,'source-caption'));
        const scope={run:source.run,artifacts:source.artifacts,caption:`${entry.kind==='alert'?'告警分诊':'事件诊断'}来源`};
        for(const row of executionTree(source.steps,source.run.id))branch.append(item(row,false,scope));
        branch.hidden=false;
        body.append(notice('来源步骤已在左侧展开。点击模型节点查看提示词和原答；当前Case轮次保持不变。'));
        for(const binding of source.bindings) {
          const ref=source.artifacts.find(a=>a.id===binding.id);
          body.append(button(`读取 ${ref.kind} · ${ref.id.slice(0,8)}`,async()=>{
            const t=++generation;body.replaceChildren(node('p','正在读取来源原件…'));
            try {const response=await content(ref);if(current()&&t===generation)body.replaceChildren(contentCard(response.data,response.raw,'冻结来源原件'));}
            catch(error){if(current()&&t===generation)body.replaceChildren(notice(`读取失败：${error.message}`,true));}
          }));
        }
        body.append(rawDetails({run:source.run,result:source.result},'来源Run与保存结果'));
      }catch(error){if(current()&&ticket===generation)body.replaceChildren(notice(`来源读取失败：${error.message}。本轮Case流程仍可查看。`,true));}
    }
    return li;
  }
  const tree = node('ol',null,'flow-lanes'), task=context.task, attempt=matchingAttempt(task,run.id), exchange=context.exchange;
  const sourceLabels={user:'用户请求',periodic:'周期自动检查',ingress:'入站自动触发',incident_update:'事件更新触发',case_created:'建案触发'};
  if(exchange) tree.append(recordNode('HTTP 请求接入',exchange.response.status<400?'completed':'failed',{
    overview:()=>facts([['接口',`${exchange.request.method} ${exchange.request.path}`],['受理时间',timeLabel(exchange.observed_at)],['HTTP状态',exchange.response.status],['后续任务',exchange.task_id]]),input:exchange.request,output:exchange.response,records:exchange
  }));
  else tree.append(recordNode(task && task.source!=='user'?'自动触发':'请求接入',task?'saved':'unknown',{
    overview:()=>notice(task?`任务来源：${sourceLabels[task.source]??task.source}。${task.source==='user'?'本批未登记该次HTTP请求原件。':'本轮由自动任务进入，不是一次直接HTTP提交。'}`:'尚未关联到本轮任务或接入原件。'),records:task??{state:'not_recorded'}
  }));
  tree.append(recordNode('任务受理与执行',task?.status??'unknown',{
    overview:()=>facts([['任务来源',sourceLabels[task?.source]??task?.source],['执行意图',task?.intent],['受理时间',timeLabel(task?.submitted_at)],['开始执行',timeLabel(attempt?.started_at??task?.started_at)],['本轮尝试',attempt?.attempt_no],['状态',stateLabel(task?.status)]]),input:task?.request??{state:'not_recorded'},output:attempt??{state:'no_matching_attempt'},records:task??{state:'not_recorded'}
  }));
  if(upstream) {
    const group=node('li',null,'flow-section');
    group.append(node('h4','本轮使用的上游分析'),node('p','以下为冻结来源；展开可查看原分析过程。','small muted'));
    if(upstream.previous)group.append(node('p',`与前轮 ${upstream.previous.run.id} 比较`,'identity'));
    for(const issue of upstream.issues)group.append(notice(issue,true));
    if(!upstream.entries.length)group.append(notice('未取得本轮上游材料；Case自身记录如下。'));
    tree.append(group);
    for(const entry of upstream.entries)tree.append(sourceNode(entry));
    const caseHeading=node('li',null,'flow-section');caseHeading.append(node('h4','本次 Case 执行'));tree.append(caseHeading);
  }
  executionTree(steps,run.id).forEach(entry=>tree.append(item(entry)));
  tree.append(recordNode('保存本轮结果',result?'saved':'unknown',{overview:()=>resultCard(result),output:result??{state:'not_recorded'},records:{run_id:run.id,result_id:result?.id,source_run_id:result?.source_run_id}}));
  tree.append(recordNode('HTTP 读取执行与结果','completed',{overview:()=>facts([['读取时间',timeLabel(context.observedAt)],['执行详情',context.runUrl],['结果详情',context.resultUrl??'随执行详情返回'],['说明','这是本次页面读回，不是新增调查执行。']]),output:result??{state:'not_recorded'}}));
  nav.append(tree);
  if(!steps.length) nav.append(notice('这次执行尚未保存步骤。'));
  nav.append(node('p',`已读取 ${steps.length} 个步骤、${artifacts.length} 份原件目录。节点顺序取自真实执行记录。`,'muted small'));
  async function show(step, view, sourceButton, scope=own) {
    const artifacts=scope.artifacts;
    const ticket=++generation; focusInspector(); selectedStep=step;
    if(sourceButton) selected(sourceButton);
    heading.replaceChildren(node('h3',stepTitle(step)),node('p',`${scope.caption} · ${stateLabel(step.state)} · ${step.kind === 'model' ? '模型' : step.kind === 'tool' ? '查询' : '程序阶段'} · 第${step.seq}步`),node('p',`Run ${step.run_id}`,'identity'));
    tabs.replaceChildren();
    for (const [key,label] of [['overview','概览与错误'],['prompt','提示词'],['input','输入'],['output','输出'],['reply','模型原答'],['records','原始记录']]) {
      if (['prompt','reply'].includes(key) && step.kind !== 'model') continue;
      const t=button(label,()=>show(step,key,sourceButton,scope)); t.setAttribute('aria-pressed',String(key===view)); tabs.append(t);
    }
    body.replaceChildren();
    if(view==='overview') {
      if(PURPOSES[step.stage_code])body.append(node('p',PURPOSES[step.stage_code],'step-purpose'));
      body.append(facts([['执行状态',stateLabel(step.state)],['开始',timeLabel(step.started_at)],['结束',timeLabel(step.ended_at)],['查询返回行数',step.returned_rows]]));
      if(step.error) { body.append(notice(stepReason(step),['failed','timeout'].includes(step.state))); if(step.error.code==='tool_budget_reserved_for_evidence')body.append(node('p',`为后续证据补查预留 ${step.actual_args?.parameters?.reserved_tool_calls_for_evidence??'未记录'} 次工具调用，本项未查询。`)); block('原始原因记录',step.error); }
      if(step.usage) body.append(facts([['输入 tokens',step.usage.input_tokens],['输出 tokens',step.usage.output_tokens],['费用',step.usage.cost ?? '未知']]));
      body.append(node('p','选择上方“输入”或“输出”查看这一步的数据；模型节点还可查看提示词和未经程序改写的原答。','muted'),rawDetails(step,'步骤身份与完整执行记录'));
      return;
    }
    if(view==='records') { block('完整步骤记录',step); return; }
    body.append(node('p','正在读取这一步的原件…','muted'));
    try {
      const fragment=node('div');
      if(view==='reply') {
        const candidates=[...artifacts.filter(a=>a.run_id===step.run_id && a.step_id===step.id && a.kind==='source_snapshot'),...stepReferences(step,artifacts,'output')];
        let found=false;
        for(const ref of candidates) {
          const response=await content(ref), choices=originalChoices(response.data.content_json);
          if(!current() || ticket!==generation) return;
          if(choices) {
            fragment.append(node('p','以下是该次模型实际返回的正文，未用程序装配结果代替。','muted'));
            for(const choice of choices) {
              fragment.append(facts([['结束原因',choice.finish_reason],['原答序号',choice.index]]));
              block('模型原答',choice.message?.content ?? '未保存正文',fragment);
            }
            fragment.append(rawDetails(response.data,'来源、摘要与完整HTTP记录')); found=true; break;
          }
        }
        if(!found) fragment.append(notice('没有找到该次模型保存的原始正文；不能用解析输出代替原答。'));
      } else {
        const role=view==='prompt'?'input':view, refs=stepReferences(step,artifacts,role);
        if(!refs.length) {
          if(role==='input' && step.actual_args != null) block('实际查询参数',step.actual_args,fragment);
          else fragment.append(notice(`这一步没有保存独立${role==='input'?'输入':'输出'}原件。`));
        }
        for(const ref of refs) {
          const response=await content(ref), data=response.data;
          if(!current() || ticket!==generation) return;
          if(data.availability!=='available') { fragment.append(contentCard(data,response.raw,'原件当前不可用'));continue; }
          const saved=data.content_json ?? data.content_text;
          if(view==='prompt') {
            const request=requestBody(saved);
            if(Array.isArray(request?.messages)) for(const message of request.messages) block(`${message.role} · 提示/提交材料`,message.content,fragment);
            else fragment.append(notice('此请求未保存messages格式提示词。'),rawDetails(saved,'查看实际保存的请求'));
            if(request?.response_format) block('要求的输出格式',request.response_format,fragment);
          } else block(role==='input'?'实际输入':'实际输出',saved,fragment);
          fragment.append(rawDetails(data,'来源、摘要与完整HTTP记录'));
        }
      }
      if(current() && ticket===generation) body.replaceChildren(fragment);
    } catch(error) {
      if(current() && ticket===generation && error.name!=='AbortError') body.replaceChildren(notice(`读取失败：${error.message}`,true));
    }
  }
  heading.append(node('h3','本轮结论与执行概览')); selected(summary);
  body.append(resultCard(result),notice('选择左侧节点查看执行数据。执行状态、交付完整性和模型质量分别判断。'));
  return root;
}
