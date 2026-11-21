/* Service-only risk projections. All decisions and history come from saved HTTP data. */
'use strict';
window.socai2Risk = (() => {
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const level=v=>({info:'信息',low:'低',medium:'中',high:'高',critical:'严重'})[v]||'未记录';
  const source=v=>({member_max:'成员规则',initial_policy:'规则初值，待分析',manual:'人工设置',manual_override:'人工设置',model:'模型上调',severity_mapping:'等级映射',unknown:'来源未知'})[v]||v||'未记录';
  const reason=v=>({raised:'已自动上调',lower_not_applied:'降低建议，未自动采用',unchanged:'等级相同，当前值保持',manual_revision_changed:'人工等级已修改，本轮未应用',execution_unconfirmed:'执行未确认，仅保留候选',opinion_missing_or_invalid:'本轮缺少可用等级',frozen_scope_changed:'成员或材料已变，本轮未应用',local_scope_only:'局部范围意见，未改全案等级',scope_unavailable:'范围不可核对',input_changed:'输入已变，本轮未应用',newer_round_exists:'已有较新轮次，本轮未应用'})[v]||v||'处理结果未记录';
  const when=v=>v?new Date(v).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'}):'未记录';
  const fields=(pairs)=>`<dl class="risk-facts">${pairs.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v??'未记录')}</dd></div>`).join('')}</dl>`;
  const subject=(kind,d)=>kind==='case'?d.case:d.facts;
  const runHref=(kind,id,run)=>`#/${kind==='case'?'cases':'incidents'}/${encodeURIComponent(id)}/investigations?run=${encodeURIComponent(run)}`;
  function current(kind,d) {
    const f=subject(kind,d)||{},r=f.risk;
    return {id:f.id,version:f.row_version,risk:r,level:kind==='case'?f.severity:d.derived?.severity_effective,
      source:r?.current?.source||(kind==='case'?f.severity_source:d.derived?.severity_source),priority:f.priority_value};
  }
  function panel(kind,d) {
    const x=current(kind,d),r=x.risk,o=r?.latest_opinion;
    return `<section class="iv-card risk-panel" aria-label="当前风险属性"><h2>当前风险属性</h2>${fields([
      ['当前严重程度',level(x.level)],['等级来源',source(x.source)],['等级更新时间',when(r?.current?.updated_at)],
      ['当前优先级',x.priority],['系统优先级建议',r?.system_priority?.value],['人工优先级',r?.priority_override?.value??'未设置'],
      ['人工优先级理由',r?.priority_override?.reason],['人工优先级更新时间',when(r?.priority_override?.updated_at)],['当前等级理由',r?.current?.reason]])}
      ${!r?'<p class="muted">尚无完整风险记录；只展示已有保存值。</p>':''}
      ${o?`<p>最近处理意见：${esc(level(o.level))} · ${esc(reason(o.reason_code))} <a href="${runHref(kind,x.id,o.run_id)}">查看该轮意见</a></p>`:'<p class="muted">暂无已处理的等级意见。</p>'}
      <a href="#/${kind==='case'?'cases':'incidents'}/${encodeURIComponent(x.id)}/activities">查看等级与优先级变化</a></section>`;
  }
  function form(kind) {
    const option=(v,t)=>`<option value="${v}">${t}</option>`;
    return `<form data-svc-form="risk"><p>未选择修改的项目保持原值；人工等级确认后，之后的新轮仍可上调。</p>
      <label class="svc-field">等级操作<select name="level_action">${option('keep','保持当前等级')}${option('set','设置等级')}${kind==='incident'?option('restore','恢复当前成员规则等级'):''}</select></label>
      <label class="svc-field">新严重程度<select name="level">${option('','请选择')}${['info','low','medium','high','critical'].map(v=>option(v,level(v))).join('')}</select></label>
      <label class="svc-field">等级调整理由<textarea name="level_reason" maxlength="20000"></textarea></label>
      <label class="svc-field">优先级操作<select name="priority_action">${option('keep','保持当前优先级')}${option('set','设置人工优先级')}${option('clear','撤销人工覆盖，恢复当前系统建议')}</select></label>
      <label class="svc-field">人工优先级（0–100）<input name="priority" type="number" min="0" max="100" step="0.01"></label>
      <label class="svc-field">优先级调整理由<textarea name="priority_reason" maxlength="20000"></textarea></label>
      <div data-svc-form-error role="alert"></div><button class="button primary">明确保存属性</button><button type="button" class="button" data-svc="close">取消</button></form>`;
  }
  function payload(kind,v,version,operation) {
    const out={operation_key:operation,expected_row_version:version};
    if(!['keep','set',...(kind==='incident'?['restore']:[])].includes(v.level_action)||!['keep','set','clear'].includes(v.priority_action))throw Error('请选择有效操作。');
    if(v.level_action!=='keep'){
      if(!v.level_reason?.trim())throw Error('请填写等级调整理由。');
      if(v.level_action==='set'&&!['info','low','medium','high','critical'].includes(v.level))throw Error('请选择严重程度。');
      out[kind==='case'?'severity':'severity_override']=v.level_action==='restore'?null:v.level;
      out[kind==='case'?'severity_reason':'severity_override_reason']=v.level_reason;
    }
    if(v.priority_action!=='keep'){
      if(!v.priority_reason?.trim())throw Error('请填写优先级调整理由。');
      out.priority_reason=v.priority_reason;
      if(v.priority_action==='clear')out.clear_priority_override=true;
      else {
        const value=String(v.priority??'');
        if(!/^\d+(\.\d{1,2})?$/.test(value)||Number(value)>100)throw Error('优先级须为0–100，最多两位小数。');
        out.priority_value=Number(value);
      }
    }
    if(Object.keys(out).length===2)throw Error('请至少选择一项修改。');
    return out;
  }
  function timeline(kind,id,page) {
    const rows=(page?.items||[]).flatMap(a=>(a.matching_targets||[]).filter(t=>t[kind+'_id']===id).map(t=>({a,t})))
      .filter(({a,t})=>['severity_raised','severity_lower_suggested'].includes(a.action)||
        (t.before_value?.risk?.manual_severity_revision!==t.after_value?.risk?.manual_severity_revision)||
        JSON.stringify(t.before_value?.risk?.priority_override)!==JSON.stringify(t.after_value?.risk?.priority_override));
    const stamp=a=>Number.isFinite(Date.parse(a.occurred_at))?Date.parse(a.occurred_at):-Infinity;
    rows.sort((left,right)=>stamp(right.a)-stamp(left.a));
    return `<div class="risk-timeline">${rows.map(({a,t})=>{
      const b=t.before_value||{},n=t.after_value||{},link=n.severity_opinion;
      const grade=v=>v.risk?.current?.level??v.severity;
      const actor=a.actor?.name_snapshot||a.actor?.user_id||a.actor?.service_name||'未记录';
      const title=({severity_raised:'自动上调',severity_lower_suggested:'本轮降低建议，未自动采用'})[a.action]||'人工属性修改';
      return `<article class="svc-record" data-risk-activity="${esc(a.id)}"><h3>${title}</h3><p>${esc(when(a.occurred_at))} · ${esc(actor)}</p>${fields([
        ['等级前值',level(grade(b))],['等级后值',level(grade(n))],['优先级前值',b.priority_value],['优先级后值',n.priority_value],['理由',t.reason||a.detail?.reason]])}
        ${(a.detail?.notes||[]).map(v=>`<p>${esc(v)}</p>`).join('')}${link?`<a href="${runHref(kind,id,link.run_id)}">查看来源轮次</a>`:''}</article>`;
    }).join('')||'<p class="muted">本页尚无该主体的等级或优先级变化；关联主体活动不作为本主体变更。</p>'}</div>`;
  }
  const suffix=url=>{if(typeof url!=='string'||!url.startsWith('/api/v1/socai2/'))throw Error('本轮读取链接无效。');return url.slice('/api/v1/socai2'.length);};
  async function round(read,kind,id,runId,detail=null) {
    const base=`/${kind==='case'?'cases':'incidents'}/${encodeURIComponent(id)}/${kind==='case'?'':'analysis/'}runs/${encodeURIComponent(runId)}`;
    detail=detail||await read(base);
    const directory=kind==='case'?detail:await read(base+'/trace');
    if(detail.run?.id!==runId||directory.run?.id!==runId||directory.run?.[kind+'_id']!==id)throw Error('轮次或主体身份不匹配。');
    const result={run:detail.run,parts:{},refs:{},errors:[]},seen=new Set();let cursor=null,refs=[];
    do {
      const p=await read(suffix(directory.artifacts_url),{query:{cursor}});
      if(p.run_id!==runId||p.subject_type!==kind||p.subject_id!==id)throw Error('工件目录不属于所选轮次。');
      refs.push(...p.items);cursor=p.next_cursor;if(cursor&&seen.has(cursor))throw Error('工件目录分页重复。');seen.add(cursor);
    }while(cursor);
    for(const ref of refs.filter(a=>a.schema_version==='socai2.severity-opinion.v1')){
      try {
        const response=await read(suffix(ref.content_url)),meta=response.artifact||response.metadata,b=response.content_json;
        if(ref.run_id!==runId||meta?.id!==ref.id||meta.run_id!==runId||meta[kind+'_id']!==id||meta.sha256!==ref.sha256||meta.schema_version!==ref.schema_version||response.availability!=='available'||b?.run_id!==runId)throw Error('等级工件身份不一致或不可用。');
        if(!['severity_opinion_input','severity_opinion_candidate','severity_opinion_application'].includes(b.type)||result.parts[b.type])throw Error('等级工件类型不唯一。');
        result.parts[b.type]=b;result.refs[b.type]=ref.id;
      }catch(e){if(e.obsolete)throw e;result.errors.push(e.message);}
    }
    const input=result.parts.severity_opinion_input,candidate=result.parts.severity_opinion_candidate;
    if(input&&(input.subject_id!==id||input.subject_type!==kind))throw Error('等级冻结范围不属于当前主体。');
    if(candidate&&input&&candidate.input_artifact_id!==result.refs.severity_opinion_input)throw Error('等级候选缺少同轮冻结引用。');
    const application=result.parts.severity_opinion_application;
    if(application&&candidate&&application.artifact_id!==result.refs.severity_opinion_candidate)throw Error('处理回执引用的意见不一致。');
    return result;
  }
  function roundPanel(data,error='') {
    if(error)return `<section class="iv-card risk-round"><h2>所选轮次等级意见</h2><p role="alert">读取失败：${esc(error)}；未使用其他轮次替代。</p></section>`;
    const p=data?.parts||{},c=p.severity_opinion_candidate,o=c?.unit?.value,a=p.severity_opinion_application,i=p.severity_opinion_input;
    return `<section class="iv-card risk-round" data-risk-run="${esc(data?.run?.id)}"><h2>所选轮次等级意见</h2>${fields([
      ['本轮建议等级',o?level(o.level):'本轮未提供可用等级'],['处理结果',a?reason(a.reason_code):'尚无处理回执'],
      ['本轮依据',o?.reason],['冻结时等级',i?level(i.current_level):'未记录'],['当轮处理后等级',a?level(a.after?.severity):'未记录'],
      ['处理时间',when(a?.processed_at)],['冻结成员数',i?Object.keys(i.selected_members||{}).length:null]])}
      ${o?fields([['已确认影响',(o.impact_basis?.confirmed||[]).join('；')||'未提供'],['潜在影响',(o.impact_basis?.potential||[]).join('；')||'未提供'],['限制',(o.limitations||[]).join('；')||'未提供']]):''}
      ${(data?.errors||[]).map(e=>`<p role="alert">部分工件读取失败：${esc(e)}</p>`).join('')}<p class="muted">本轮意见和处理回执按当时保存展示；当前属性在主体详情查看。</p></section>`;
  }
  return {current,panel,form,payload,timeline,round,roundPanel,runHref,level,source,reason};
})();
